import sys
import re
from hanziconv import HanziConv

from .downloader import download_texts

juan_number = int(sys.argv[1])

juan_string = str(juan_number).zfill(3)

original, comment = download_texts(["https://zh.wikisource.org/wiki/%E5%8F%B2%E8%A8%98/%E5%8D%B7" + juan_string,
	"https://zh.wikisource.org/wiki/%E5%8F%B2%E8%A8%98%E4%B8%89%E5%AE%B6%E8%A8%BB/%E5%8D%B7" + juan_string])

def preprocess_original_paragraph(s):
	rst = re.sub("(（\w+）)|(［\w+］)", "", s).replace("《", "").replace("》", "").strip()
	rst = re.sub(r"{{PUA\|(.)}}", r"\1", rst)
	rst = re.sub(r"{{!\|(.)\|(左|上)「.」(右|下)「.」}}", r"\1", rst)
	rst = re.sub("{{!\|(.)\|...}}", r"\1", rst)
	rst = rst.replace("{{quote|", "")
	rst = rst.replace("}}", "")
	rst = re.sub("-{(.)}-", r"\1", rst)
	return rst

original_paragraphs = [preprocess_original_paragraph(i) for i in original.split("\n")]

interchangeable_sets = ["逾踰", "並并", "喜憙", "巿市", "間閒問", "后後", "陝陜",
	"願原", "築筑", "脩修", "樑梁", "奔餎", "鐘鍾", "台臺", "馕饟", "愈癒", "碧固",
	"汜氾", "遊游", "瑯琅", "勢埶", "恒恆", "憨戇", "彊僄", "裏里", "爲為", "獸兽",
	"肃肅" , "锡錫", "报報", "蓋盖", "柏栢", "强彊", "鬬斗", "髯胡", "龍龙", "髯珣",
	"屣鵕", "俎爼", "屑箓", "採采", "籓藩", "弦絃", "苟茍", "慾欲", "膏班", "儛舞",
	"昚暤", "窪洼", "嚼噍", "麤粗", "奸姦", "怗惉", "盪蕩", "暖煖", "塤壎", "醻酳",
	"槀槁", "羣群", "疎疏", "溢鎰", "獘弊", "擊击", "锺鐘", "疋匹", "姦柬", "饟饢",
	"郁鬱", "岪茀", "岩巖", "紘陁", "附坿", "萩瑌", "菱蓤", "玳瑇", "棻柟", "蘗",
	"猿猨", "玄元", "槅蹵", "湜𨎥", "雷靁", "胸胷", "眾衆", "櫜襍", "吸噏", "彷仿",
	"彿佛", "䴊璘", "磻𪀁", "蠨䳘", "𪁉𪂴", "䴋鴂", "醁𪆫", "澥𪇅", "昉䳄", "氾泛",
	"嵯嵳", "峩峨", "紘陀", "崛崫", "岧嵔", "嶮𡾋", "𡾊鵾", "皋臯", "肸肹", "餔䁆",
	"虛墟", "盼盻", "𤛑偁", "敠獏", "湲𧤗", "扆駞", "璸瑸", "𣗶濛", "崒䝯", "曆歷",
	"嫵娬", "兼相", "弒弑", "提褆", "魌𧯆", "𧯋谺", "伯北", "句勾", "雰氛", "歴歷",
	"沖𧘂", "嚬崫", "䃶靺", "涉渉", "薆", "回囘", "鱇皬", "餐飱", "讬託"]

def same_character(a, b):
	if a == b:
		return True
	elif any((a in i and b in i for i in interchangeable_sets)):
		return True
	elif HanziConv.toSimplified(a) == HanziConv.toSimplified(b):
		return True
	else:
		return False

def can_transform_into_by_deletion(a, b):
	i = 0
	j = 0
	a = re.sub(r"{{PUA\|(.)}}", r"\1", a)
	a = re.sub("(.)々", r"\1\1", a)
	while i < len(b):
		if j >= len(a):
			return False
		if same_character(a[j], b[i]):
			i += 1
			j += 1
		else:
			j += 1
	return True

def can_transform_into_by_deletion_debug(a, b):
	i = 0
	j = 0
	a = re.sub(r"{{PUA\|(.)}}", r"\1", a)
	a = re.sub("(.)々", r"\1\1", a)
	while i < len(b):
		if j >= len(a):
			print(f"remainder: '{b[i:]}'")
			return False
		if same_character(a[j], b[i]):
			i += 1
			j += 1
		else:
			j += 1
	return True

a = "厥之有章，不必諄諄。【集解】徐廣曰：「諄，止純反。告之丁寧。」駰案：漢書音義曰「天之所命，表以符瑞，章明其德，不必諄諄然有語言也。依類託寓，諭以封巒。厥之有章，不必諄諄。依類託寓，諭以封巒。【集解】漢書音義曰：「寓，寄也。巒，山也。言依事類託寄，以喻封禪者。」 "
b = " 厥之有章，不必諄諄。依類讬寓，諭以封巒。 "
b = preprocess_original_paragraph(b)
can_transform_into_by_deletion_debug(a, b)


def find_corresponding_original_paragraph(c):
	rst = ""
	for i in original_paragraphs:
		if len(i) > 0 and can_transform_into_by_deletion(c, rst + i):
			rst += i
		elif len(i) > len(rst) and can_transform_into_by_deletion(c, i) :
			rst = i
	if rst == "":
		print(f"Did not find corresponding original paragraph for '{c[:20]}'")
		return None
	else:
		return rst

def remove_markup(s):
	return s.replace("{", "").replace("}", "").replace("|", "").replace("*", "")

def next_common_run_of_length_n(a, b, n):
	for i in range(0, len(a) - n + 1):
		is_common = True
		for j in range(n):
			if not same_character(a[i + j], b[j]):
				is_common = False
				break
		if is_common:
			return i
	return None

def highlight_according_to_original(p, o):
	i = 0
	j = 0
	rst = ""
	while j < len(p) and p[j].isspace():
		rst += p[j]
		j += 1
	while j < len(p):
		if i < len(o) and same_character(p[j], o[i]) or \
			(p[j] == "々" and j > 0 and same_character(p[j - 1], o[i])):
			rst += p[j]
			j += 1 
			i += 1
		elif re.match(r"{{PUA\|.}}", p[j:]) != None and p[j + 6] == o[i]:
			rst += p[j:j + 9]
			j += 9
			i += 1
		else:
			if not (p[j] == "【"):
				print("Error: unexpected beginning for comment region")
				print("'" + p[j:] + "'")
				print(f"Remaining original: '{o[i:]}'")
				print(f"Complete original: '{o}'")
				assert(False)
			rst += "{{*|"
			start = j
			if i == len(o):
				j = len(p)
			else:
				next_j = None
				for run_length in range(1, len(o[i:]) + 1):
					common_run_start = next_common_run_of_length_n(p[j:], o[i:], run_length)
					if common_run_start == None:
						break
					else:
						assert(common_run_start > 0)
						next_j = j + common_run_start
				if next_j != None:
					j = next_j
				else:
					print("Error: could not detect remainder of original")
					print(f"Remainder: '{o[i:]}'")
					assert(False)
			rst += p[start:j] + "}}"
	if(i != len(o)):
		print("Error: did not finish original paragraph")
		print(f"Remainder: '{o[i:]}'")
		assert(False)
	assert(remove_markup(rst) == remove_markup(p))
	return rst

with open(juan_string + ".txt", "w") as out:
	for p in comment.split("\n"):
		if "=" in p or "{{*|" in p or "header" in p or p == "}}" or p == "{{PD-old}}" or "與其窮極倦𧮬" in p:
			out.write(p)
		elif p == "":
			pass
		else:
			o = find_corresponding_original_paragraph(p)
			if o == None:
				out.write(p)
			else:
				out.write(highlight_according_to_original(p, o))
		out.write("\n")
