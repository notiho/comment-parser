import urllib.parse

_chinese_digits = { 0: "", 1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九" }

def _num_to_chinese(num):
	if num < 10:
		return _chinese_digits[num]
	elif num < 20:
		return "十" + _chinese_digits[num % 10]
	elif num < 100:
		return _chinese_digits[num // 10] + "十" + _chinese_digits[num % 10]
	else:
		assert(False)
		

text_urls = []

# 論語註疏
for i in range(1, 21):
#for i in range(1, 2):
	text_urls.append("https://zh.wikisource.org/zh-hant/%E8%AB%96%E8%AA%9E%E8%A8%BB%E7%96%8F/%E5%8D%B7" + str(i).zfill(2))


# 尚書正義
for i in range(1, 21):
	# As of May 2021, the wikisource version of juan 19 of the shangshu zhengyi 
	# is formated completely without indication of what is original and what is comment and hence unusable
	if i != 19:
		text_urls.append(urllib.parse.quote("https://zh.wikisource.org/wiki/尚書正義/卷" + _num_to_chinese(i), safe = "/:"))
