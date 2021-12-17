import wikitextparser
import re
import html
import os
from pathlib import Path
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
	def parse(text, last_preceeding_original_paragraph):
		if len(text) == 0:
			return None
		elif text.startswith(":{{*|"):
			if not text.endswith("}}"):
				print(f"Paragraph '{text}' has unexpected ending")
				assert(False)
			return Paragraph([Region("comment", "", text[5:-2], last_preceeding_original_paragraph.regions)])
		elif text.startswith("{{footer}}") or text.startswith("[[") or text.startswith("{{PD-old}}"):
			return None
		else:
			return Paragraph([Region("original", "", text)])
	
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
				rst.append(new)
			return rst
	
	_text_header_pattern = re.compile(r"^=(?P<sectionname>[^=].+[^=])=$", flags = re.MULTILINE)
	_section_header_pattern = re.compile(r"^==(?P<sectionname>(·|‧|\w)+)==$", flags = re.MULTILINE)
	
	@staticmethod
	def parse_raw(raw, title):
		metadata = dict()
		metadata["title"] = title
		metadata["juan_index"] = "1"
		
		headers = list(Text._text_header_pattern.finditer(raw))
		if len(headers) == 0:
			print("Warning: could not find header")
		
		rst = []
		for i in range(len(headers)):
			if headers[i]["sectionname"] not in ["老子《道德經》上篇", "老子《道德經》下篇"]:
				continue
			t = ""
			if i + 1 < len(headers):
				t = raw[headers[i].end():headers[i + 1].start()]
			else:
				t = raw[headers[i].end():]
			headers2 = list(Text._section_header_pattern.finditer(t))
			if len(headers2) == 0:
				print("Warning: could not find inner header")
			for j in range(len(headers2)):
				section_text = ""
				if j + 1 < len(headers2):
					section_text = t[headers2[j].end():headers2[j + 1].start()]
				else:
					section_text = t[headers2[j].end():]
				
				section_metadata = metadata.copy()
				section_metadata["title"] += "上" if "上" in headers[i]["sectionname"] else "下"
				section_metadata["section"] = headers2[j]["sectionname"]
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
		e.set("original_title", "道德經")
		for i, p in enumerate(self.paragraphs):
			p.to_xml(i, e)
		return e
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")

text_urls = []
titles = []

text_urls.append("https://zh.wikisource.org/wiki/%E9%81%93%E5%BE%B7%E7%B6%93_(%E7%8E%8B%E5%BC%BC%E6%9C%AC)")
titles.append("老子道德經注")

raw_texts = list(download_texts(text_urls))

texts = [t for (i, r) in enumerate(raw_texts) for t in Text.parse_raw(r, titles[i])]

for t in texts:
	xml = t.to_xml()
	etree.indent(xml, space="\t")
	try:
		s = etree.tostring(xml, pretty_print = True, encoding = "UTF-8", xml_declaration = True)
		dirname = os.path.join("data", t.metadata["title"])
		Path(dirname).mkdir(exist_ok = True)
		with open(os.path.join(dirname, t.metadata["juan_index"] + t.metadata["section"] + ".xml"), "wb") as out:
			out.write(s)
	except Exception as e:
		print(f"Error when writing page for '{t.get_title_section()}'", e)
		traceback.print_exc()
	
