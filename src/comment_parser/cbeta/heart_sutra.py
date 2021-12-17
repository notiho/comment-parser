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
		clss = element.get("class", "")
		if clss == "juan" or clss == "byline":
			return None
		elif clss == "dharani":
			return Paragraph([Region("original", "dharani", element.text)])
		else:
			text = element.text
			if text == None:
				print(f"{etree.tostring(element)} has empty text")
				assert(False)
			if "　" in text:
				parts = text.split("　")
				original_region = Region("original", "", parts[0])
				comment_region = Region("comment", "", parts[1], [original_region])
				return Paragraph([original_region, comment_region])
			else:
				assert(last_preceeding_original_paragraph != None)
				return Paragraph([Region("comment", "", text, last_preceeding_original_paragraph.regions)])
	
	@staticmethod
	def from_div_element(element, last_preceeding_original_paragraph):
		clss = element.get("class")
		assert(clss == "div-orig" or clss == "div-commentary" or clss == "div-other" or clss == "div-xu")
		if clss == "div-xu":
			return []
		elif clss == "div-other":
			return [Paragraph.from_p_element(i, last_preceeding_original_paragraph) for i in element]
		else:
			typus = "original" if clss == "div-orig" else "comment"
			rst = []
			for i in element:
				subtype = "dharani" if "dharani" in i.get("class", "") else ""
				comments_on = last_preceeding_original_paragraph.regions if typus == "comment" else []
				rst.append(Paragraph([Region(typus, subtype, i.text, comments_on)]))
			return rst
	
	@staticmethod
	def from_xhtml(element, last_preceeding_original_paragraph):
		if element.tag == "{http://www.w3.org/1999/xhtml}div":
			return Paragraph.from_div_element(element, last_preceeding_original_paragraph)
		elif element.tag == "{http://www.w3.org/1999/xhtml}p":
			return [Paragraph.from_p_element(element, last_preceeding_original_paragraph)]
		else:
			print(f"Unexpected tag: {element}")
			assert(False)
	
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
	def from_xhtml(element, juan_index, cbeta_index):
		titles = element.findall(".//{http://www.w3.org/1999/xhtml}title")
		assert(len(titles) == 1)
		metadata = dict()
		metadata["title"] = titles[0].text
		metadata["juan_index"] = str(juan_index)
		metadata["section"] = ""
		metadata["cbeta"] = cbeta_index
		bodies = element.findall(".//{http://www.w3.org/1999/xhtml}div[@id='body']")
		assert(len(bodies) == 1)
		return Text(metadata, bodies[0])
	
	def __init__(self, metadata, body):
		self.metadata = metadata
		print(f"\nInfo: starting to parse body of {self.get_title_section()}")
		paragraphs = [Paragraph([Region("original", "title", self.metadata["title"])])]
		def last_original_paragraph():
				for i in paragraphs[::-1]:
					if i != None and i.contains_original():
						return i
				return None
		for i in body:
			paragraphs.extend(Paragraph.from_xhtml(i, last_original_paragraph()))
		self.paragraphs = [p for p in paragraphs if p != None]
	
	def to_xml(self):
		e = etree.Element("text")
		e.set("title", self.metadata["title"])
		e.set("section", self.metadata["section"])
		e.set("juan", self.metadata["juan_index"])
		e.set("original_title", "般若波羅蜜多心經")
		e.set("cbeta", self.metadata["cbeta"])
		for i, p in enumerate(self.paragraphs):
			p.to_xml(i, e)
		return e
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")

text_indices = ["T1714", "X0571"]

mydir = os.path.dirname(os.path.realpath(__file__))

texts = []
for t in text_indices:
	dir_name = os.path.join(mydir, "cbeta", t[0], t)
	files = glob.glob(os.path.join(dir_name, "[0-9][0-9][0-9].xhtml"))
	for f in files:
		print(f"\nReading {f}") 
		texts.append(Text.from_xhtml(etree.parse(f).getroot(), int(f[-9:-6]), t))

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
