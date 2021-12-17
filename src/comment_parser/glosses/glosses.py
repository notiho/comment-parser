import re
import copy

from ..util import to_normalized_matching_form, enumerate_matches_in_normalized_matching_form
from ..moe_dict import moe_entries

_prefix = "(^|(?<=。|「|（|」|：|『|；|○|】)|(云?「(?P<subregion>(\w|：|。|，)+)」者，))"
_prefix_with_comma = f"({_prefix}|(?<=，))"

_raw_patterns = [
	r"~者?，(\w|，)+(。|(?=」)|；)",
	r"~者?。\w+。",
	r"(此言|然則)?「~」者?，(\w|，|《|》|、)+(。|(?=」))",
	
	r"「?~」?者?，(古文作\w，)?《(?P<quoting>(\w|‧)+)》云：(「(\w|。|，)+」|(\w|，)+。)",
	r"~者?，《(?P<quoting>(\w|‧)+)》作\w，(\w|，)+。",
	r"《(?P<quoting>(\w|‧)+)》云：「~者?，(\w|，|。|、)+」",
	r"《(?P<quoting>(\w|‧)+)》云：「(\w|，|。|、)*。~者?，(\w|，|。|、)+」",
	
	r"(\w|，)+，故(曰|謂之)~也?。",
	
	r"~者\w+也。?(華言\w+。)?",
	r"~者。梵語\w+。(華言\w+。)?",
	r"\w+。曰~。"]

_raw_patterns_that_can_start_after_comma = [
	r"\w+曰~(。|(?=」)|，)",
	r"(所謂)?~(即|謂|者)\w+。",
	r"\w+(謂之|乃是)~(，|。)",
	r"\w+為~(，|。)"]

_all_raw_patterns = [_prefix  + p for p in _raw_patterns] +\
	[_prefix_with_comma + p for p in _raw_patterns_that_can_start_after_comma]

_max_lookahead_for_glossed = 5

_max_glossed_length = 6

_patterns = list(map(lambda p: re.compile(
	p.replace("~", "(?P<glossed>\w{1," + str(_max_glossed_length) + "}?)")\
	.replace("_", "(?P<glossed2>\w{1," + str(_max_glossed_length) + "}?)")), _all_raw_patterns))

def _matches_which_pattern(s):
	rst = []
	for i in _raw_patterns + _raw_patterns_that_can_start_after_comma:
		if re.fullmatch(i.replace("~", "(?P<glossed>\w{1," + str(_max_glossed_length) + "}?)")\
			.replace("_", "(?P<glossed2>\w{1," + str(_max_glossed_length) + "}?)"), s):
			rst.append(i)
	return rst

print("Info: list of patterns that will be used:")
print("\n".join((i.pattern for i in _patterns))) 

class Match:
	def __init__(self, start, end, value, text, region = None):
		self.start = start
		self.end = end
		self.value = value
		self.text = text
		self.region = region
		assert(self.text[self.start : self.end] == self.value)
	
	@staticmethod
	def from_re_match(match):
		return Match(match.start(), match.end(), match[0], match.string)
	
	@staticmethod
	def from_start_end_string(start, end, string):
		return Match(start, end, string[start:end], string)
	
	def __eq__(self, other):
		return self.start == other.start and self.end == other.end and self.text == other.text
	
	def __copy__(self):
		return Match(self.start, self.end, self.value, self.text, self.region)
	
	def __str__(self):
		return f"Match({self.start}, {self.end}, '{self.value}')"

class Gloss:
	def __init__(self, glossed, content, glossed_in_content_index, quoting, subregion):
		self.glossed = glossed
		self.content = content
		self.glossed_in_content_index = glossed_in_content_index
		self.quoting = quoting
		self.subregion = subregion
		self.repetitions = []
		self.potentially_spurious = False
	
	def content_overlaps_with(self, other):
		return self.content.text == other.content.text and\
			not (self.content.start >= other.content.end or\
				 self.content.end <= other.content.start)
	
	def content_contains(self, other):
		return self.content.text == other.content.text and\
			self.content.start <= other.content.start and\
			self.content.end >= other.content.end
	
	def content_contains_strict(self, other):
		return self.content_contains(other) and\
			(self.content.start < other.content.start or\
			 self.content.end > other.content.end)
	
	def content_with_glossed_replaced_by_tilde(self):
		return self.content.value[:self.glossed_in_content_index] + ("~" * len(self.glossed_value())) + self.content.value[self.glossed_in_content_index + len(self.glossed_value()):]
	
	sentence_delimiters_pattern = re.compile("。|$|」") 
	
	def glossed_sentences(self):
		rst = []
		for i in self.glossed:
			sentence_begin = len(i.text) - self.sentence_delimiters_pattern.search(i.text[::-1], len(i.text) - i.start).start()
			if i.text[sentence_begin] in "」』":
				sentence_begin += 1
			
			sentence_end = self.sentence_delimiters_pattern.search(i.text, i.end).end()
			if sentence_end < len(i.text) and i.text[sentence_end] == "」":
				sentence_end += 1
			rst.append(i.text[sentence_begin:sentence_end])
		return rst
	
	def __str__(self):
		return f"Gloss('{self.glossed_value()}', '{self.content.value}')"
	
	def __repr__(self):
		return self.__str__()
	
	def __lt__(self, other):
		if self.content.region != None:
			t1 = self.content.region.paragraph.text
			t2 = other.content.region.paragraph.text
			return (t1.metadata["original_title"], t1.metadata["juan"],
				t1.metadata["section"], self.content.region.id,
				self.content.start, self.content.end) <\
				(t2.metadata["original_title"], t2.metadata["juan"],
				t2.metadata["section"], other.content.region.id,
				other.content.start, other.content.end)
		else:
			return (self.content.start, self.content.end) <\
				(other.content.start, other.content.end)
	
	def glossed_value(self):
		return self.glossed[0].value
	
	def content_before_glossed(self):
		return self.content.value[:self.glossed_in_content_index]
	
	def content_after_glossed(self):
		return self.content.value[self.glossed_in_content_index + len(self.glossed_value()):]
	
	def text_before_content(self):
		return self.content.text[:self.content.start]

def _filter_overlapping(glosses):
	assert(len(glosses) > 0)
	
	# filter out glosses that have as glossed a subregion of another gloss
	glosses = [g for g in glosses if not\
		any((i.subregion == g.glossed_value() for i in glosses))]
	
	# if two glosses have the same glossed value at the same position,
	# take the longer one
	glosses = [g for g in glosses if not\
		any((i.content_contains_strict(g) and\
			 i.content.start + i.glossed_in_content_index == g.content.start + g.glossed_in_content_index and\
			 i.glossed_value() == g.glossed_value() for i in glosses))]
	
	# filtered out glosses that have the exact same content and glossed
	filtered = []
	while glosses != []:
		filtered.append(glosses[0])
		glosses = [g for g in glosses[1:] 
			if not (g.content == glosses[0].content and g.glossed_value() == glosses[0].glossed_value())]
	glosses = filtered
	
	return glosses
	
# in contrast to finditer, consider overlapping matches
def _iterate_regex_matches(r, s):
	start = 0
	while start < len(s):
		match = r.search(s, start)
		if match == None:
			return
		else:
			yield match
			start = match.start(0) + 1
	

def find_glosses(original, comment):
	original_normalized = to_normalized_matching_form(original)
	comment_normalized = to_normalized_matching_form(comment)
	
	def is_bogus_zhe_gloss(gloss):
		return gloss.glossed[0].value == "者" and gloss.content.start > 0 and comment[gloss.content.start - 1] == "」"
	
	def is_bogus_ye_gloss(gloss):
		return gloss.glossed[0].value == "也" and gloss.content.start > 0 and comment[gloss.content.start - 1] == "」"
	
	def mark_potentially_spurious_wei_gloss(gloss):
		if gloss.content_before_glossed()[-1:] == "為":
			if "為" + gloss.glossed_value() in moe_entries:
				gloss.potentially_spurious = True
			elif gloss.glossed_value() in ["之", "然"]:
				gloss.potentially_spurious = True
			elif gloss.content_before_glossed().endswith("之為") or \
				gloss.content_before_glossed().endswith("以為"):
				gloss.potentially_spurious = True
	
	# mark glosses like 故曰X / 故謂之X / 又曰X
	def mark_potentially_spurious_gu_yue_type_gloss(gloss):
		if gloss.content_before_glossed() in ["故曰", "故謂之", "又曰", "是故曰"]:
			gloss.potentially_spurious = True
		elif gloss.glossed_value() == "故" and gloss.content_after_glossed().startswith("謂之"):
			gloss.potentially_spurious = True
		elif gloss.glossed_value() == "故" and gloss.glossed_in_content_index == 0 and gloss.text_before_content().endswith("，"):
			gloss.potentially_spurious = True
	
	rst = []
	
	def enumerate_occurences_of_glossed(glossed, match):
		occurs_in_original = False
		for i in enumerate_matches_in_normalized_matching_form(original, glossed):
			occurs_in_original = True
			yield (i[0], i[1], original)
				
		if not occurs_in_original: # prefer to match something in the original
			for i in enumerate_matches_in_normalized_matching_form(
				comment[0:match.end() + _max_lookahead_for_glossed], glossed):
				if match.start() >= i[1] or match.end() <= i[0]:
					yield (i[0], i[1], comment)
	
	for p in _patterns:
		for match in _iterate_regex_matches(p, comment):
			if not to_normalized_matching_form(match[0]) in original_normalized and\
				match.start() == comment.index(match[0]) and\
				not (match[0][-1] == "也" and match.start() != comment.index(match[0][:-1])):
				glossed = match["glossed"]
				glossed2 = match.groupdict().get("glossed2")
				quoting = match.groupdict().get("quoting")
				subregion = match["subregion"] if match["subregion"] != None else glossed
				
				if not glossed in subregion or (glossed2 != None and not glossed2 in subregion):
					continue
				
				glossed_instances = list(enumerate_occurences_of_glossed(subregion, match))
				if glossed2 != None and not "subregion" in match.groupdicht():
					glossed_instances.extend(enumerate_occurences_of_glossed(subregion2, match))
				
				glossed_matches = []
				for i in glossed_instances:
					m = Match.from_start_end_string(*i)
					if "subregion" in match.groupdict():
						m2 = copy.copy(match)
						if not glossed in m.value:
							# TODO: check if some of these are actually valid
							# especially interchangeable characters, e.g. 己　已
							continue
						offset = m.value.index(glossed)
						m.start += offset
						m.end = m.start + len(glossed)
						m.value = glossed
						if m.text[m.start:m.end] != glossed:
							print(m, m.text[m.start:m.end], subregion, glossed, offset)
							
						glossed_matches.append(m)
						if glossed2 != None:
							offset = subregion.index(glossed2)
							m2.start += offset
							m2.end = m2.start + len(glossed2)
							m2.value = glossed2
							glossed_matches.append(m2)
					else:
						glossed_matches.append(m)
					
				if len(glossed_matches) > 0:
					rst.append(Gloss(glossed_matches, Match.from_re_match(match),
						match.start("glossed") - match.start(), quoting,
						match.groupdict().get("subregion")))
	
	rst = list(filter(lambda i: not is_bogus_zhe_gloss(i), rst))
	rst = list(filter(lambda i: not is_bogus_ye_gloss(i), rst))
	for i in rst:
		mark_potentially_spurious_wei_gloss(i)
		mark_potentially_spurious_gu_yue_type_gloss(i)
	
	filtered = []
	while rst != []:
		overlapping_group = [rst[0]]
		changed = True
		while changed:
			changed = False
			for i in rst[1:]:
				if any((j.content_overlaps_with(i) for j in overlapping_group))\
					and not i in overlapping_group:
					overlapping_group.append(i)
					changed = True
		filtered.extend(_filter_overlapping(overlapping_group))
		for i in overlapping_group:
			rst.remove(i)
		
	return filtered
