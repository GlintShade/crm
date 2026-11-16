# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Edycja komentarza na leadzie i szansie, frappe-free (ops#364).

Komentarz leada (`CRM Lead`) i szansy (`CRM Deal`) to zwykly `Comment` Frappe
(`comment_type = "Comment"`). Autor edytuje wlasny wpis przez
`crm.api.komentarze.edytuj`; historia zmian tresci to wiersze `Version`
(`Comment.track_changes`), czytane tymi samymi funkcjami co rozmowa zadania
(`zmiany_tresci`, `liczba_zmian_tresci` z `crm.volteo_zadania_rozmowa`).

Ten modul ma dwie dodatkowe, czyste funkcje: wybor wzmianek (`@osoba`), ktore sa
NOWE po edycji (`nowe_wzmianki`), zeby edycja nie powiadamiala ponownie osob
wzmiankowanych juz wczesniej, oraz regule, ktore komentarze wolno edytowac
(`czy_komentarz_edytowalny`). Nie importuje `frappe` ani `bs4` (na tej maszynie
nie sa instalowalne), wiec da sie go przetestowac lokalnie; zaleznosc od
frameworka (bramka odczytu rodzica, `Version`, `User`) mieszka w
`crm.api.komentarze`.
"""

from html.parser import HTMLParser

from crm.volteo_zadania_rozmowa import liczba_zmian_tresci, zmiany_tresci

__all__ = [
	"DOCTYPES_EDYCJI",
	"czy_komentarz_edytowalny",
	"liczba_zmian_tresci",
	"nowe_wzmianki",
	"wzmianki",
	"zmiany_tresci",
]

# Dokumenty, ktorych komentarze edytuje `crm.api.komentarze`. Rozmowa zadania ma
# wlasny endpoint, komentarze audytu nie sa edytowalne.
DOCTYPES_EDYCJI = ("CRM Lead", "CRM Deal")


class _ZbieraczWzmianek(HTMLParser):
	"""Zbiera znaczniki `<span data-type="mention" data-id=".." data-label="..">`
	(edytor TipTap), w kolejnosci wystapienia."""

	def __init__(self: "_ZbieraczWzmianek") -> None:
		super().__init__(convert_charrefs=True)
		self.wynik: list[dict] = []

	def handle_starttag(self: "_ZbieraczWzmianek", tag: str, attrs: list) -> None:
		if tag != "span":
			return
		atrybuty = dict(attrs)
		if atrybuty.get("data-type") != "mention":
			return
		self.wynik.append({"email": atrybuty.get("data-id"), "full_name": atrybuty.get("data-label")})


def wzmianki(tresc: str | None) -> list[dict]:
	"""Wzmianki w tresci HTML: lista `{"email", "full_name"}` (bez deduplikacji,
	jak `crm.api.comment.extract_mentions`). Pusta tresc daje pusta liste."""
	if not tresc:
		return []
	zbieracz = _ZbieraczWzmianek()
	zbieracz.feed(tresc)
	return zbieracz.wynik


def nowe_wzmianki(przed: str | None, po: str | None) -> list[dict]:
	"""Wzmianki z `po`, ktorych adresu (`data-id`) nie bylo w `przed` -- tylko te
	wymagaja powiadomienia po edycji. Wzmianki bez adresu sa pomijane, a ten sam
	adres wzmiankowany w `po` kilka razy daje jeden wpis (pierwsze wystapienie)."""
	juz_byli = {wzmianka["email"] for wzmianka in wzmianki(przed) if wzmianka["email"]}
	wynik: list[dict] = []
	widziani: set[str] = set()
	for wzmianka in wzmianki(po):
		email = wzmianka["email"]
		if not email or email in juz_byli or email in widziani:
			continue
		widziani.add(email)
		wynik.append(wzmianka)
	return wynik


def czy_komentarz_edytowalny(reference_doctype: str | None, comment_type: str | None) -> bool:
	"""Czy komentarz wolno edytowac przez `crm.api.komentarze`: tylko zwykly
	komentarz (`Comment`) na `CRM Lead` albo `CRM Deal`."""
	return comment_type == "Comment" and reference_doctype in DOCTYPES_EDYCJI
