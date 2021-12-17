

_kangxi_html_by_char = dict()

with open("data/kangxizidian-v3e.txt") as f:
	has_started = False
	for line in f:
		if not has_started:
			if line.startswith("https:"):
				has_started = True
		else:
			head_char_and_rest = line.split("\t")
			assert(len(head_char_and_rest) == 3)
			html = ""
			for meaning_group in head_char_and_rest[2].split("　"):
				html += '<div class="k1">'
				for part in meaning_group.split(""):
					if part != "":
						html += '<div>'
						html += part.strip()
						html += '</div>'
				html += "</div>"
			_kangxi_html_by_char[head_char_and_rest[0]] = html

def get_kangxi_html_by_char():
	return _kangxi_html_by_char
		
		
