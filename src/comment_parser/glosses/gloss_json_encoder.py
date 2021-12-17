from json import JSONEncoder

from .glosses import Match
from .outer_structure import Gloss

class GlossJSONEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Gloss):
			glossed_sentences = dict.fromkeys(obj.glossed_sentences()).keys()
			return {
				"glossed": obj.glossed,
				"glossed_sentences": list(glossed_sentences),
				"glossed_sentences_with_glossed_replaced_by_tilde": 
					[s.replace(obj.glossed_value(), len(obj.glossed_value()) * "~") for s in glossed_sentences],
				"content": obj.content,
				"glossed_in_content_index": obj.glossed_in_content_index,
				"content_with_glossed_replaced_by_tilde": obj.content_with_glossed_replaced_by_tilde(),
				"quoting": obj.quoting,
				"text_id": id(obj.content.region.paragraph.text),
				"text_title": obj.content.region.paragraph.text.metadata["title"],
				"text_section": obj.content.region.paragraph.text.metadata["section"],
				"repetitions": obj.repetitions,
				"potentially_spurious": obj.potentially_spurious}
		elif isinstance(obj, Match):
			return {
				"start": obj.start,
				"end": obj.end,
				"value": obj.value,
				"region_id": obj.region.id}
		else:
			return JSONEncoder().default(obj)
