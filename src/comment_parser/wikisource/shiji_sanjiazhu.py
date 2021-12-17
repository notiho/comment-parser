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
		
		assert(all((i != None for i in explains)))
		
		if typus == "comment" and "prefix" not in subtype and explains == []:
			print(f"Warning: comment region {self.short_form()} created with empty explains")
		
		if typus == "original" and "【" in text:
			print(f"Warning: potentially comment in original region '{self.text[:5]}'")
	
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
		region_texts = re.split("{|}|○", text)
		regions = []
		
		def last_original_region():
			for i in regions[::-1]:
				if i.typus == "original":
					return i
			return None
		
		for i in region_texts:
			if i == "":
				continue
			elif not i.startswith("*|"):
				regions.append(Region("original", "", i))
			else:
				if last_original_region() == 0:
					print(f"Warning: comment in original paragraph witout preceeding original text '{text}'")
				else:
					if last_original_region() == None:
						print(text)
					regions.append(Region("comment", "", i[2:], [last_original_region()]))
		return Paragraph(regions)
	
	
	@staticmethod
	def parse(text, last_preceeding_original_paragraph):
		if len(text) == 0:
			return None
		elif text.startswith("{{*|"):
			if not text.endswith("}}"):
				print(f"Paragraph '{text}' has unexpected ending")
				assert(False)
			return Paragraph([Region("summary", "", text[5:-2])])
		elif text.startswith("{{footer}}") or text.startswith("[[") or text.startswith("{{PD-old}}"):
			return None
		else:
			return Paragraph._parse_original(text)
	
	def __init__(self, regions):
		self.regions = regions
	
	def text(self):
		return "".join(map(lambda r: r.text, self.regions))
	
	def contains_original(self):
		return any(map(lambda r: r.typus == "original", self.regions))
	
	def to_xml(self, index, parent_element):
		e = etree.SubElement(parent_element, "paragraph")
		e.set("index", str(index))
		for i in self.regions:
			i.to_xml(e)


class Text:
	@staticmethod
	def _normalize(raw):
		rst = raw.replace("“", "「").replace("”", "」")
		rst = rst.replace("‘", "『").replace("’", "』")
		rst = rst.replace("[[", "").replace("]]", "")
		rst = rst.replace("{{gap}}", "")
		rst = rst.replace("\n:", "\n")
		rst = rst.replace("-{", "").replace("}-", "")
		rst = re.sub(r"{{PUA\|(.)}}", r"\1", rst)
		rst = re.sub(r"{{!\|(.)\|左「.」右「.」}}", r"\1", rst)
		
		colors_removed = ""
		i = 0
		color_names = ("deepPink", "green", "DeepPink")
		in_colored = False
		while i < len(rst):
			cont = False
			for c in color_names:
				if rst[i:].startswith("{{" + c + "|"):
					in_colored = True
					cont = True
					i += len("{{" + c + "|")
			
			if cont:
				continue
			
			if in_colored and rst[i:].startswith("}}"):
				i += 2
				in_colored = False
			else:
				colors_removed += rst[i]
				i += 1
			
		return colors_removed
	
	@staticmethod
	def _parse_header(header):
		if len(header.templates) == 0:
			print("Warning: could not find header template")
			return {}
		else:
			t = header.templates[0]
			if t.name.strip() == "Textquality":
				t = header.templates[1]
			if t.name.strip() != "Header" and t.name.strip() != "header":
				print(f"Warning: excepted header to have name 'Header' but got '{t.name}' instead")
			rst = {}
			for a in t.arguments:
				rst[a.name.strip()] = a.value.strip()
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
			
			has_started = False
			for p in paragraphs:
				if not has_started and (p.startswith("{{*") or "【" in p):
					has_started = True
				if has_started:
					new = Paragraph.parse(p, last_original_paragraph())
					if new == None:
						continue
					rst.append(new)
			return rst
		
	@staticmethod
	def parse_raw(raw, juan_index):
		raw = Text._normalize(raw)
		wikitext = wikitextparser.parse(raw)
		metadata = Text._parse_header(wikitext)
		metadata["title"] = "史記三家注"
		metadata["juan_index"] = str(juan_index)
		
		if "<ref>" in metadata["section"]:
			metadata["section"] = metadata["section"][:metadata["section"].index("<ref>")] + \
				metadata["section"][metadata["section"].index("</ref>") + len("</ref>"):]
		
		return Text(metadata, raw)
	
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
		e.set("original_title", "史記")
		for i, p in enumerate(self.paragraphs):
			p.to_xml(i, e)
		return e
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")

text_urls = []
juan_indices = []
# leave out 表 (and 世家 for now)
for i in list(range(1, 13)) + list(range(23, 31)) + list(range(61, 131)):
	text_urls.append("https://zh.wikisource.org/wiki/%E5%8F%B2%E8%A8%98%E4%B8%89%E5%AE%B6%E8%A8%BB/%E5%8D%B7" + str(i).zfill(3))
	juan_indices.append(i)

raw_texts = list(download_texts(text_urls))

texts = [Text.parse_raw(r, juan_indices[i]) for (i, r) in enumerate(raw_texts)]

for t in texts:
	xml = t.to_xml()
	etree.indent(xml, space="\t")
	try:
		s = etree.tostring(xml, pretty_print = True, encoding = "UTF-8", xml_declaration = True)
		with open(os.path.join("data", "史記三家注", t.metadata["juan_index"] + t.metadata["section"] + ".xml"), "wb") as out:
			out.write(s)
	except Exception as e:
		print(f"Error when writing page for '{t.get_title_section()}'", e)
		traceback.print_exc()
	
