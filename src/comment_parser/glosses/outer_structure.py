import wikitextparser
import re
import html

from .glosses import find_glosses, Gloss, Match
from ..util import to_normalized_matching_form

class Region:
	def __init__(self, element, paragraph):
		self.paragraph = paragraph
		
		self.typus = element.get("typus")
		self.subtype = element.get("subtype")
		self.id = int(element.get("id"))
		self.text = element.text.strip()
		
		# the paragraph that is currently constructed and that contains 
		# this region might not be in paragraph.text.paragraphs yet
		def region_by_id(i):
			rst = paragraph.text.region_by_id(int(i))
			if rst != None:
				return rst
			else:
				return paragraph.region_by_id(int(i))
		
		self.explains = [region_by_id(int(i)) for i in element.get("explains").split(",") if i != ""]
		
		self.glosses = []
		self.glossed = []
		
		if self.typus == "comment" and "prefix" not in self.subtype and self.explains == []:
			print(f"Warning: comment region {self.short_form()} created with empty explains")
		
		if self.typus == "comment" and "prefix" not in self.subtype:
			raw_glosses = find_glosses("".join((i.text for i in self.explains)), self.text)
			raw_glosses.sort(key = lambda i: i.content.start)
			
			for i in raw_glosses:
				i.content.region = self
				
				glossed_regions = []
				for j in i.glossed: 
					if j.text == self.text:
						if self not in glossed_regions:
							glossed_regions.append(self)
						j.region = self
					else:
						glossed_region_index = 0
						offset = 0
						while offset + len(self.explains[glossed_region_index].text) <= j.start:
							offset += len(self.explains[glossed_region_index].text)
							glossed_region_index += 1
						glossed_region = self.explains[glossed_region_index]
						if glossed_region not in glossed_regions:
							glossed_regions.append(glossed_region)
						
						j.text = glossed_region.text
						j.start -= offset
						j.end -= offset
						j.region = glossed_region
				
				self.glosses.append(i)
				for r in glossed_regions:
					r.glossed.append(i)
		
		i = 0
		while i < len(self.glosses):
			g = self.glosses[i]
			is_repetition = False
			for p in self.paragraph.text.paragraphs:
				for r in p.regions:
					for j in r.glosses:
						if j.glossed == g.glossed and j.content.value == g.content.value:
							j.repetitions.append(g.content)
							is_repetition = True
			if is_repetition:
				del self.glosses[i]
			else:
				i += 1
						
	
	def _filter_unique_glossed_value_content(self, gs):
		unfiltered = gs
		filtered = []
		while unfiltered != []:
			filtered.append(unfiltered[0])
			unfiltered = [i for i in unfiltered[1:] 
				if unfiltered[0].content != i.content or unfiltered[0].glossed_value() != i.glossed_value()]
		return filtered
	
	def glosses_with_unique_glossed_value_content(self):
		return self._filter_unique_glossed_value_content(self.glosses)
	
	def glossed_with_unique_glossed_value_content(self):
		return self._filter_unique_glossed_value_content(self.glossed)
	
	def _number_of_glosses_starting_at(self, index):
		rst = 0
		for i in self.glosses:
			if i.content.start == index:
				rst += 1
		return rst
	
	def _number_of_glosses_ending_at(self, index):
		rst = 0
		for i in self.glosses:
			if i.content.end == index:
				rst += 1
		return rst
	
	def _number_of_glossed_starting_at(self, index):
		rst = 0
		for i in self.glossed:
			for g in i.glossed:
				if g.text == self.text and g.start == index:
					rst += 1
		return rst
	
	def _number_of_glossed_ending_at(self, index):
		rst = 0
		for i in self.glossed:
			for g in i.glossed:
				if g.text == self.text and g.end == index:
					rst += 1
		return rst
	
	def __html__(self):
		html_text = ""
		gloss_level = 0
		glossed_level = 0
		has_open_span = False
		for i in range(len(self.text)):
			old_gloss_level = gloss_level
			old_glossed_level = glossed_level
			
			gloss_level += self._number_of_glosses_starting_at(i) 
			gloss_level -= self._number_of_glosses_ending_at(i)
			
			glossed_level += self._number_of_glossed_starting_at(i) 
			glossed_level -= self._number_of_glossed_ending_at(i)
			
			if gloss_level != old_gloss_level or glossed_level != old_glossed_level:
				if has_open_span:
					html_text += '</span>'
					has_open_span = False
				if gloss_level > 0 or glossed_level > 0:
					html_text += '<span class="' +\
						("gloss" if gloss_level > 0 else "") + " " + ("glossed" if glossed_level > 0 else "") + '">'
					has_open_span = True
			html_text += html.escape(self.text[i])
		
		if has_open_span:
			html_text += "</span>"
		
		return f'<span class="{self.typus} {self.subtype}" id="{self.id}"> {html_text} </span>'
	
	def plain_html(self):
		return f'<span class="{self.typus} {self.subtype}" id="region-{self.id}">{self.text}</span>'
	
	def short_form(self):
		if len(self.text) <= 30:
			return "'" + self.text + "'"
		else:
			return f"'{self.text[:15]}...{self.text[-15:]}'"
	
	def _metadata_line_or_empty(self, name, value):
		if value == "":
			return ""
		else:
			return f"""
				<div class="metadata-line">
					<span class="metadata-category">{name}: </span><span class="metadata">{value}</span>
				</div>
				""".strip().replace("\t", "")
	
	def metadata_html(self):
		return self._metadata_line_or_empty("Type", self.typus) \
			+ self._metadata_line_or_empty("Subtype", self.subtype[:1])\
			+ self._metadata_line_or_empty("Explains", ", ".join(map(lambda i: i.short_form(), self.explains)))\
			+ self._metadata_line_or_empty("Glosses", "; ".join(map(lambda i: f"for '{i.glossed_value()}': '{i.content.value}'", self.glosses_with_unique_glossed_value_content())))\
			+ self._metadata_line_or_empty("Glossed", "; ".join(map(lambda i: f"for '{i.glossed_value()}': '{i.content.value}'", self.glossed_with_unique_glossed_value_content())))


class Paragraph:
	def __init__(self, element, text):
		self.text = text
		self.regions = []
		for i in element:
			assert(i.tag == "region")
			self.regions.append(Region(i, self))
	
	def fulltext(self):
		return "".join(map(lambda r: r.text, self.regions))
	
	def contains_original(self):
		return any(map(lambda r: r.typus == "original", self.regions))
	
	def __html__(self):
		return "<p>" + "".join(map(lambda r: r.__html__(), self.regions)) + "</p>"
	
	def plain_html(self):
		return "<p>" + "".join(map(lambda r: r.plain_html(), self.regions)) + "</p>"
	
	def all_glosses(self):
		return [g for r in self.regions for g in r.glosses]
	
	def region_by_id(self, i):
		return next((r for r in self.regions if r.id == i), None)

def memoize(f):
    memo = {}
    def helper(x):
        if x not in memo:            
            memo[x] = f(x)
        return memo[x]
    return helper

class Text:
	def __init__(self, element):
		self.metadata = dict()
		self.metadata["title"] = element.get("title")
		self.metadata["section"] = element.get("section")
		self.metadata["original_title"] = element.get("original_title")
		if self.metadata["original_title"] == None:
			print(self.get_title_section() + ": No original title set")
		self.metadata["juan"] = int(element.get("juan"))
		self.paragraphs = []
		for i in element:
			assert(i.tag == "paragraph")
			self.paragraphs.append(Paragraph(i, self))
	
	def __html__(self):
		return "".join(map(lambda p: p.__html__(), self.paragraphs))
	
	def plain_html(self):
		return "".join(map(lambda p: p.plain_html(), self.paragraphs))
	
	def get_title_section(self):
		return self.metadata.get("title", "unkown title") + " " + self.metadata.get("section", "unkown section")
	
	def all_glosses(self):
		return [g for p in self.paragraphs for g in p.all_glosses()]
	
	def region_by_id(self, i):
		return next((r for p in self.paragraphs for r in p.regions if r.id == i), None)
	
	@memoize
	def text(self):
		return "".join((p.fulltext() for p in self.paragraphs))
	
	def num_comment_chars(self):
		return sum((len(r.text) for p in self.paragraphs for r in p.regions if r.typus == "comment"))
