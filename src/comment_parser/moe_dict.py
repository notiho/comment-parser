import sqlite3

_con = sqlite3.connect("data/moe_dict.sqlite3")
_cur = _con.cursor()

moe_entries = []
for entry in _cur.execute("SELECT title FROM entries"):
	moe_entries.append(entry[0])

moe_entries = frozenset(moe_entries)

_con.close()
