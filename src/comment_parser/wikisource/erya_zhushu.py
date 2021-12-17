import wikitextparser
import re
import html
import os
import traceback
from lxml import etree

from .downloader import download_texts
from ..util import to_normalized_matching_form

class Region:
	next_id = 0
	
	def __init__(self, typus, subtype, text, explains = []):
		self.typus = typus
		self.subtype = subtype
		self.text = text.strip()
		self.explains = explains
		self.id = Region.next_id
		Region.next_id += 1
		
		if typus == "comment" and "prefix" not in subtype and explains == []:
			print(f"Warning: comment region {self.short_form()} created with empty explains")
	
	def to_xml(self, parent_element):
		e = etree.SubElement(parent_element, "region")
		e.set("typus", self.typus)
		e.set("subtype", self.subtype)
		e.set("id", str(self.id))
		e.set("explains", ",".join([str(i.id) for i in self.explains]))
		e.text = "\n" + self.text + "\n\t\t"		
	
	def short_form(self):
		if len(self.text) <= 16:
			return "'" + self.text + "'"
		else:
			return f"'{self.text[:8]}...{self.text[-8:]}'"
	
	def __repr__(self):
		return f"Region {self.typus} {self.subtype} {self.text}"
		

class Paragraph:
	@staticmethod
	def _parse_summary(text):
		return Paragraph([Region("summary", "", text)])
	
	@staticmethod
	def _parse_original(text):
		text = text.strip()
		if text[-3:] != "===" and text[-3:] != "'''":
			print(f"Warning: '{text}' is not formatted correctly")
		text = text[3:-3]
		regions = []
		for r in re.split("(?=\(|（)|(?<=\)|）)", text):
			if len(r) == 0:
				continue
			elif r[0] == "(" or r[0] == "（":
				assert(r[-1] == ")" or r[-1] == "）")
				regions.append(Region("comment", "", r[1:-1], [regions[-1]]))
			else:
				regions.append(Region("original", "", r))
		return Paragraph(regions)
	
	@staticmethod
	def _parse_comment(text, last_preceeding_original_paragraph):
		assert(last_preceeding_original_paragraph != None)
		assert(len(text) > 1)
		if text[0] == "○":
			text = text[1:]
		
		subtype = text[0]
		
		if subtype == "【":
			subtype = text[1]
		
		prefix_begin = 3 if text[2] == "】" else 1
		prefix_end = Paragraph._prefix_end_delimiter_pattern.search(text)
		if not prefix_end:
			if len(last_preceeding_original_paragraph.regions) == 1 and last_preceeding_original_paragraph.regions[0].subtype == "title":
				return Paragraph([Region("comment", subtype + "_prefix", text[0:prefix_begin]),
					Region("comment", subtype + "_body", text[prefix_begin:], last_preceeding_original_paragraph.regions[:])])
			else:
				print(f"Warning: could not find end of prefix in paragraph '{text}'")
				return None
		else:
			explains = []
			explains_prefix = text[prefix_begin:prefix_end.start()]
			if explains_prefix.strip() == "":
				explains = last_preceeding_original_paragraph.regions
			else:
				typus = "original" if subtype == "疏" else "comment"
				explains = last_preceeding_original_paragraph.get_regions_from_explains_prefix(explains_prefix, typus)
			return Paragraph([Region("comment", subtype + "_prefix", "【" + subtype + "】" + text[prefix_begin:prefix_end.start()]),
				Region("comment", subtype + "_body", text[prefix_end.start():], explains)])
	
	
	@staticmethod
	def parse(text, last_preceeding_original_paragraph):
		if len(text) == 0:
			return None
		if text.startswith("{{footer}}"):
			return None
		elif text[0:3] == "===" or text[0:3] == "'''":
			return Paragraph._parse_original(text)
		elif text[0] == "疏" or text[0:2] == "○注" or text[0] == "【":
			text = text.replace("{", "").replace("}", "")
			if last_preceeding_original_paragraph == None:
				print(f"Warning: comment paragraph '{text[0:10]}...' without preceeding original paragraph")
				return None
			else:
				rst = Paragraph._parse_comment(text, last_preceeding_original_paragraph)
				return rst
		else:
			assert(last_preceeding_original_paragraph != None)
			last_preceeding_original_paragraph.regions.append(Region("comment", "", text, last_preceeding_original_paragraph.regions[:]))
			return None 
	
	def __init__(self, regions):
		self.regions = regions
	
	def text(self):
		return "".join(map(lambda r: r.text, self.regions))
	
	_a_zhi_b_explains_prefix_pattern = re.compile("傳?「(.+)」\s?至「(.+)」。?")
	_a_zhi_pian_mo_explains_prefix_pattern = re.compile("「(.+)」\s?至篇末。?")
	_full_region_explains_prefix_pattern = re.compile("(?:子?曰：?)?傳?「([^」]+)」?。?")
	_double_full_region_explains_prefix_pattern = re.compile("(?:曰：)?「([^」]+)」，「([^」]+)」?。?")
	_prefix_end_delimiter_pattern = re.compile(r"(○?\s?(?=(釋曰)))|(○云)|(釋在上。)|(者，)|(。案)")
	
	def _get_regions_from_a_zhi_b_explains_prefix(self, a, b, typus):
		a = to_normalized_matching_form(a)
		b = to_normalized_matching_form(b) if b != None else a
		
		start_index = None
		
		for r in range(len(self.regions)):
			reduced = to_normalized_matching_form(self.regions[r].text)
			if self.regions[r].typus == typus and start_index == None and reduced.startswith(a):
				start_index = r
				break
		
		if start_index == None:
			# Make second, less strict pass
			for r in range(len(self.regions)):
				reduced = to_normalized_matching_form(self.regions[r].text)
				if self.regions[r].typus == typus and start_index == None and a in reduced:
					start_index = r
					break
		
		if start_index == None:
			print(f"Warning: failed to detect '{a}' from 「{a}」至「{b}」 pattern in paragraph '{self.text()[0:10]}...'")
			return []
		
		end_index = None
		
		if b == None:
			end_index = len(self.regions)
		else:
			for r in range(len(self.regions) - 1, -1, -1):
				reduced = to_normalized_matching_form(self.regions[r].text)
				if self.regions[r].typus == typus and reduced.endswith(b):
					end_index = r + 1
					break
			
			if end_index == None:
				# Make second, less strict pass
				for r in range(len(self.regions) - 1, -1, -1):
					reduced = to_normalized_matching_form(self.regions[r].text)
					if self.regions[r].typus == typus and b in reduced:
						end_index = r + 1
						break
			
		if end_index == None:
			print(f"Warning: failed to detect '{b}' from 「{a}」至「{b}」 pattern in paragraph '{self.text()[0:10]}...'")
			return []
		
		rst = []
		for r in range(len(self.regions)):
			if start_index <= r and r < end_index and self.regions[r].typus == typus:
				rst.append(self.regions[r])
		
		return rst
	
	def _get_regions_from_full_explains_prefix(self, a, typus):
		a = to_normalized_matching_form(a)
		
		rst = []
		
		for r in self.regions:
			if r.typus == typus:
				reduced = to_normalized_matching_form(r.text)
				if a in reduced:
					rst.append(r)
					return rst
				elif a.startswith(reduced):
					rst.append(r)
					a = a[len(reduced):]
				elif reduced.endswith(a[:6]):
					rst.append(r)
					a = a[6:]
					
		
		print(f"Warning: failed to find '{a}' in paragraph '{self.text()[0:10]}...'")
		return []
		
	def get_regions_from_explains_prefix(self, prefix, typus):
		prefix = prefix.strip()
		a_zhi_b_match = self._a_zhi_b_explains_prefix_pattern.fullmatch(prefix)
		if a_zhi_b_match != None:
			return self._get_regions_from_a_zhi_b_explains_prefix(a_zhi_b_match.group(1), a_zhi_b_match.group(2), typus)
		
		a_zhi_pian_mo_match = self._a_zhi_pian_mo_explains_prefix_pattern.fullmatch(prefix)
		if a_zhi_pian_mo_match != None:
			return self._get_regions_from_a_zhi_b_explains_prefix(a_zhi_pian_mo_match.group(1), None, typus)
		
		full_match = self._full_region_explains_prefix_pattern.fullmatch(prefix)
		if full_match != None:
			regions = self._get_regions_from_full_explains_prefix(full_match.group(1), typus)
			return regions
		
		double_full_match = self._double_full_region_explains_prefix_pattern.fullmatch(prefix)
		if double_full_match != None:
			return self._get_regions_from_full_explains_prefix(double_full_match.group(1), typus) + self._get_regions_from_full_explains_prefix(double_full_match.group(2), typus)
			
		print(f"Warning: could not parse explains prefix '{prefix}'")
		return []
	
	def contains_original(self):
		return any(map(lambda r: r.typus == "original", self.regions))
	
	def to_xml(self, index, parent_element):
		e = etree.SubElement(parent_element, "paragraph")
		e.set("index", str(index))
		for i in self.regions:
			i.to_xml(e)
	
	def join(self, other):
		self.regions.extend(other.regions)


class Text:
	@staticmethod
	def _normalize(raw):
		rst = raw.replace("“", "「").replace("”", "」").replace("‘", "『")
		rst = rst.replace("’", "』").replace("○注", "\n○注").replace("【疏】", "\n【疏】")
		rst = rst.replace("[[", "").replace("]]", "")
		rst = rst.replace("[疏]", "\n【疏】").replace("︰", "：")
		rst = re.sub("注「(?P<a>(《|》|。|，|；|：|\w)+)」至「(?P<b>(《|》|。|，|；|：|\w)+)」。",
			r"\n【注】「\g<a>」至「\g<b>」。", rst)
		rst = re.sub("注「(?P<a>(《|》|。|，|；|：|\w)+)」(?P<c>。|者)",
			r"\n【注】「\g<a>」\g<c>", rst)
		return rst
	
	@staticmethod
	def _parse_header(header):
		if len(header.templates) == 0:
			print("Warning: could not find header template")
			return {}
		else:
			t = header.templates[0]
			if t.name != "Header":
				print(f"Warning: excepted header to have name 'Header' but got '{t.name}' instead")
			rst = {}
			for a in t.arguments:
				rst[a.name] = a.value
			return rst
	
	@staticmethod
	def _parse_body(body, title_paragraph): 
		paragraphs = [p.strip() for p in body.split("\n")]
		if len(paragraphs) == 0:
			print("Warning: body is empty")
			return []
		else:
			rst = [title_paragraph]
			
			def last_original_paragraph():
				for i in rst[::-1]:
					if i != None and i.contains_original():
						return i
				return None
			
			for p in paragraphs:
				new = Paragraph.parse(p, last_original_paragraph())
				if new == None:
					continue
				if len(rst) > 1 and rst[-1].contains_original() and new.contains_original():
					rst[-1].join(new)
				else:
					rst.append(new)
			
			return list(filter(lambda i: i != None, rst))
	
	_section_header_pattern = re.compile(r"^={1,2}(?P<sectionname>(·|‧|\w)+)={1,2}$", flags = re.MULTILINE)
	
	@staticmethod
	def parse_raw(raw, juan_index):
		raw = Text._normalize(raw)
		wikitext = wikitextparser.parse(raw)
		metadata = Text._parse_header(wikitext.sections[0])
		metadata["title"] = "爾雅註疏"
		metadata["juan_index"] = str(juan_index)
		metadata["section"] = metadata["section"]
		
		headers = list(Text._section_header_pattern.finditer(raw))
		if len(headers) == 0:
			print("Warning: could not find header")
		
		rst = []
		for i in range(len(headers)):
			if headers[i]["sectionname"] == "爾雅序":
				continue
			section_text = ""
			if i + 1 < len(headers):
				section_text = raw[headers[i].end():headers[i + 1].start()]
			else:
				section_text = raw[headers[i].end():]
			section_metadata = metadata.copy()
			section_metadata["section"] = headers[i]["sectionname"][3:]
			rst.append(Text(section_metadata, section_text))
		return rst
	
	def __init__(self, metadata, body):
		self.metadata = metadata
		print(f"\nInfo: starting to parse body of {self.get_title_section()}")
		title_paragraph = Paragraph([Region("original", "title", self.get_title_section())])
		self.paragraphs = Text._parse_body(body, title_paragraph)
	
	def to_xml(self):
		e = etree.Element("text")
		e.set("title", self.metadata["title"])
		e.set("section", self.metadata["section"])
		e.set("juan", self.metadata["juan_index"])
		e.set("original_title", "爾雅")
		for i, p in enumerate(self.paragraphs):
			p.to_xml(i, e)
		return e
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")

text_urls = []
for i in range(1, 6):
	text_urls.append("https://zh.wikisource.org/wiki/%E7%88%BE%E9%9B%85%E8%A8%BB%E7%96%8F/%E5%8D%B7" + str(i).zfill(2))

raw_texts = list(download_texts(text_urls))

texts = [t for (i, r) in enumerate(raw_texts) for t in Text.parse_raw(r, i + 1)]

for t in texts:
	xml = t.to_xml()
	etree.indent(xml, space="\t")
	try:
		s = etree.tostring(xml, pretty_print = True, encoding = "UTF-8", xml_declaration = True)
		with open(os.path.join("data", "爾雅註疏", t.metadata["juan_index"] + t.metadata["section"] + ".xml"), "wb") as out:
			out.write(s)
	except Exception as e:
		print(f"Error when writing page for '{t.get_title_section()}'", e)
		traceback.print_exc()
	
