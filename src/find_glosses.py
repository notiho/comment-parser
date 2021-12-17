#!/usr/bin/env python3

import os
import glob
from pathlib import Path
from lxml import etree
from chameleon import PageTemplateLoader
from multiprocessing import Pool

from comment_parser.kangxi import get_kangxi_html_by_char
from comment_parser.glosses.outer_structure import Text

templates = PageTemplateLoader(os.path.join(os.path.dirname(__file__), "templates"))
html_dir = "./html"	

def process_text(fn):
	t = Text(etree.parse(fn).getroot())
	
	text_template = templates["text.pt"]

	html = text_template.render(text = t)
	
	sub_dir = os.path.join(html_dir, t.metadata["title"])
	Path(sub_dir).mkdir(exist_ok = True)
	
	try:
		with open(os.path.join(sub_dir, str(t.metadata["juan"]) + t.metadata["section"] + ".html"), "w") as out:
			out.write(html)
	except Exception as e:
		print(f"Error when writing page for '{t.get_title_section()}'")
		raise e
	return t

def _word_statistics(w, all_glosses, texts):
	num_glosses = sum([1 for g in all_glosses if not g.potentially_spurious and g.glossed_value() == w])
	num_fulltext = sum([t.text().count(w) for t in texts])
	return (w, num_glosses, num_fulltext)

def main():
	xml_files = glob.glob("./data/*/*.xml")
	xml_files.sort()
	texts = []
	
	html_dir = "./html"
	Path(html_dir).mkdir(exist_ok = True)
	
	with Pool(12) as pool:
		texts = pool.map(process_text, xml_files)
	
	total_num_chars = sum((len(t.text()) for t in texts))
	total_comment_chars = sum((t.num_comment_chars() for t in texts))
	print(f"Texts contain {total_num_chars} chars, of which {total_comment_chars} belong to comment regions")

	all_glosses = [g for t in texts for g in t.all_glosses()]
	num_spurious = sum((1 for g in all_glosses if g.potentially_spurious))
	num_words = len(set([g.glossed_value() for g in all_glosses]))
	
	print(f"Found {len(all_glosses)} glosses ({num_spurious} of which are potentially spurious) for {num_words} words.")
	
	"""print(f"Total gloss length: {sum((len(g.content.value) for g in all_glosses))}")
	
	non_spurious_words_statistics = []
	non_spurious_words = set([g.glossed_value() for g in all_glosses if not g.potentially_spurious])
	with Pool(8) as pool:
		non_spurious_words_statistics = pool.starmap(_word_statistics, ((w, all_glosses, texts) for w in non_spurious_words))
	
	non_spurious_words_statistics = sorted(non_spurious_words_statistics, key = lambda i: i[2])
	print("top ten with most full-text hits:")
	for i in non_spurious_words_statistics[-10:]:
		print(i)
	
	print(f"total non spurious words: {len(non_spurious_words_statistics)}")
	print(f"avg num of glosses: {(len(all_glosses) - num_spurious) / len(non_spurious_words)}")
	print(f"avg num of full-text hits: {sum([i[2] for i in non_spurious_words_statistics]) / len(non_spurious_words)}")
	
	fulltext_median = non_spurious_words_statistics[len(non_spurious_words) // 2][2]
	non_spurious_words_statistics = sorted(non_spurious_words_statistics, key = lambda i: i[1])
	gloss_median = non_spurious_words_statistics[len(non_spurious_words) // 2][1]
	print(f"median num of glosses: {gloss_median}")
	print(f"median num of full-text hits: {fulltext_median}")
	
	print("top ten with most glosses:")
	for i in non_spurious_words_statistics[-15:]:
		print(i)"""
	
	dict_html = templates["dict.pt"].render(texts = texts, glosses = all_glosses,
		kangxi = get_kangxi_html_by_char())
	
	try:
		with open(os.path.join(html_dir, "dict.html"), "w") as out:
			out.write(dict_html)
	except Exception as e:
			print("Error when writing dict", e)
	
	random_text_html = templates["random_text.pt"].render(texts = texts)
	
	try:
		with open(os.path.join(html_dir, "random_text.html"), "w") as out:
			out.write(random_text_html)
	except Exception as e:
			print("Error when writing random text", e)

if __name__ == "__main__":
	main()
