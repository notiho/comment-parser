import re

_chars_omitted_in_normalized_matching_form_pattern = re.compile("[ ：:「」『』？！。，（）；、《》{}]")

def _normalize_interchangeable_characters(s):
	return s.replace("己", "已")

_cache = dict()
def to_normalized_matching_form(s):
	if s in _cache:
		return _cache[s]
	else:
		rst =  _normalize_interchangeable_characters(_chars_omitted_in_normalized_matching_form_pattern.sub("", s).strip())
		_cache[s] = rst
		return rst

def enumerate_matches_in_normalized_matching_form(string, target):
	normalized_target = to_normalized_matching_form(target)
	cur_starts = []
	for i in range(len(string)):
		normalized_char = to_normalized_matching_form(string[i])
		if len(normalized_char) == 0:
			continue
		else:
			cur_starts.append((i, 0))
			next_starts = []
			for (start, length) in cur_starts:
				if normalized_char == normalized_target[length]:
					if length == len(normalized_target) - 1:
						yield (start, i + 1)
					else:
						next_starts.append((start, length + 1))
			cur_starts = next_starts
