"""Skladanie warunkow SQL dla list dokumentow powiazanych (Comment) z dokumentem
odniesienia (ops#374). Modul bez `import frappe`: czyste skladanie napisow,
w pelni testowalne lokalnie.

Zasady: kazdy zagniezdzony warunek jest ujety w nawiasy (haki widocznosci
zwracaja warunki bez zewnetrznych nawiasow, z `OR` w srodku), a wygenerowany SQL
nie zawiera znaku procenta (db_query przepuszcza warunki przez formatowanie `%`),
stad `LOCATE` zamiast `LIKE`.
"""

from collections.abc import Iterable


def literal_sql(wartosc: str) -> str:
	"""Literal SQL w apostrofach. ValueError dla `%`, NUL i nowej linii."""
	if "%" in wartosc or "\x00" in wartosc or "\n" in wartosc or "\r" in wartosc:
		raise ValueError("niedozwolony znak w literale SQL")
	return "'" + wartosc.replace("\\", "\\\\").replace("'", "\\'") + "'"


def nazwa_tabeli(doctype: str) -> str:
	"""`tab<doctype>` w odwrotnych apostrofach. ValueError dla znakow specjalnych."""
	for znak in ("`", "%", "'", '"', "\\", "\x00", "\n", "\r"):
		if znak in doctype:
			raise ValueError("niedozwolony znak w nazwie doctype")
	return f"`tab{doctype}`"


def _kolumna(tabela: str, pole: str) -> str:
	if "`" in pole or "%" in pole or not pole:
		raise ValueError("niedozwolona nazwa pola")
	return f"{tabela}.`{pole}`"


def polacz_haki(warunki: Iterable[str | None]) -> str:
	"""Laczy warunki przez AND, kazdy w nawiasach; puste pomija."""
	czesci = []
	for w in warunki:
		if w is None:
			continue
		w = w.strip()
		if w:
			czesci.append(f"({w})")
	return " AND ".join(czesci)


def warunek_powiazania(
	tabela: str,
	pole_typu: str,
	pole_nazwy: str,
	warunki_typow: dict[str, str],
	galezie_dodatkowe: dict[str, str] | None = None,
) -> str:
	"""Warunek: wiersz `tabela` jest widoczny, gdy jego dokument odniesienia
	jest widoczny wg warunku swojego typu. Typy spoza zbioru nie sa ograniczane."""
	galezie_dodatkowe = galezie_dodatkowe or {}
	typy = sorted(set(warunki_typow) | set(galezie_dodatkowe))
	if not typy:
		return ""
	t = nazwa_tabeli(tabela)
	typ = _kolumna(t, pole_typu)
	nazwa = _kolumna(t, pole_nazwy)
	lista = ", ".join(literal_sql(x) for x in typy)
	galezie = [f"ifnull({typ}, '') = ''", f"{typ} NOT IN ({lista})"]
	for x in typy:
		if x in galezie_dodatkowe:
			galezie.append(f"({typ} = {literal_sql(x)} AND ({galezie_dodatkowe[x]}))")
		else:
			cel = nazwa_tabeli(x)
			galezie.append(
				f"({typ} = {literal_sql(x)} AND {nazwa} IN "
				f"(SELECT `name` FROM {cel} WHERE ({warunki_typow[x]})))"
			)
	return "(" + " OR ".join(galezie) + ")"


def warunek_bez_znacznikow(tabela: str, pole_tresci: str, znaczniki: Iterable[str]) -> str:
	"""Warunek: tresc nie zawiera zadnego ze znacznikow (LOCATE, bez `%`)."""
	lista = sorted(set(znaczniki))
	if not lista:
		return ""
	kol = _kolumna(nazwa_tabeli(tabela), pole_tresci)
	return "(" + " AND ".join(f"LOCATE({literal_sql(m)}, ifnull({kol}, '')) = 0" for m in lista) + ")"
