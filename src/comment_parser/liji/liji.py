#!/usr/bin/python3

import os
import glob
import traceback
from pathlib import Path
from lxml import etree

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
	def from_p_element(element, last_preceeding_original_paragraph):
		if len(element) > 0:
			regions = []
			for child in element:
				assert(child.tag == "strong")
				regions.append(Region("original", "", child.text))
				if child.tail != None:
					regions.append(Region("comment", "注", child.tail, [regions[-1]]))
			return Paragraph(regions)
		else:
			assert(last_preceeding_original_paragraph != None)
			return Paragraph([Region("comment", "疏", element.text, last_preceeding_original_paragraph.regions)])
	
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
	def __init__(self, section, juan_index, paragraphs):
		self.metadata = dict()
		self.metadata["juan_index"] = str(juan_index)
		self.metadata["section"] = section
		self.metadata["title"] = "禮記注疏"
		self.paragraphs = paragraphs
	
	def to_xml(self):
		e = etree.Element("text")
		e.set("title", "禮記注疏")
		e.set("section", self.metadata["section"])
		e.set("juan", self.metadata["juan_index"])
		e.set("original_title", "禮記")
		for i, p in enumerate(self.paragraphs):
			p.to_xml(i, e)
		return e
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")


def chinese_number_to_int(c):
	digit_to_int = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
	if c.startswith("十"):
		return 10 + (0 if len(c) == 1 else digit_to_int[c[1]])
	elif "十" in c:
		return 10 * digit_to_int[c.split("十")[0]] + (0 if len(c) == 2 else digit_to_int[c.split("十")[1]])
	else:
		return digit_to_int[c]

mydir = os.path.dirname(os.path.realpath(__file__))

root = etree.parse(os.path.join(mydir, "Section1.xhtml")).getroot()
texts = []
cur_paragraphs = []
def last_original_paragraph():
	for i in cur_paragraphs[::-1]:
		if i != None and i.contains_original():
			return i
	return None
cur_section = ""
cur_juan_index = -1
for e in root:
	if e.tag == "h1":
		if cur_paragraphs != []:
			texts.append(Text(cur_section, cur_juan_index, cur_paragraphs))
			cur_paragraphs = []
		cur_section = e.text
		cur_juan_index = chinese_number_to_int(e.text.split("第")[1])
	else:
		assert(e.tag == "p")
		cur_paragraphs.append(Paragraph.from_p_element(e, last_original_paragraph()))

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
