import urllib.parse
import urllib.request
import base64

from pathlib import Path


def _download_text(url):
	try:
		with urllib.request.urlopen(url + "?action=raw") as request:
			return request.read().decode("utf-8")
	except Exception as e:
		print(f"Error when trying to download {urllib.parse.unquote(url)}: ", e)
		return ""

def _url_to_cache_filename(url):
	return base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")

class Cache:
	def __init__(self):
		Path(".cache").mkdir(exist_ok = True)
		self._loaded = {}
	
	def __getitem__(self, url):
		if url in self._loaded:
			return self._loaded[url]
		else:
			try:
				with open(".cache/" + _url_to_cache_filename(url)) as f:
					self._loaded[url] = f.read()
			except FileNotFoundError:
					self._loaded[url] = _download_text(url)
					try:
						with open(".cache/" + _url_to_cache_filename(url), "w") as f:
							f.write(self._loaded[url])
					except Exception as e:
						print(f"Error when writing cache for {urllib.parse.unquote(url)}: ", e)
			except Exception as e:
				print(f"Error when reading cache for {urllib.parse.unquote(url)}: ", e)
				self._loaded[url] = ""
		return self._loaded[url]

_cache = Cache()

def download_texts(text_urls):
	return map(lambda i: _cache[i], text_urls)
