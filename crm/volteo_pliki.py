# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Klasyfikacja, deduplikacja i sortowanie zalacznikow szansy dla feedu
"Pliki" (`crm.api.pliki.feed`, issue GlintShade/proenergy-crm-ops#199).

Modul celowo nie importuje ``frappe``: to jedyny sposob, zeby dalo sie go
przetestowac lokalnie (na tej maszynie ``frappe`` nie jest instalowalne).
Cala logika zalezna od frameworka (odczyt `File` przez `frappe.db.get_all`,
sprawdzanie `has_permission` na dokumentach nadrzednych, budowanie kontekstu
z bazy) mieszka w `crm.api.pliki`, ktore importuje stale i funkcje stad.

Modul `crm/volteo_notatki.py` (feed "Notatki", issue W1 / ops#198) powstaje
ROWNOLEGLE w innym worktree tego samego cyklu (b64) i moze jeszcze nie
istniec w tej kopii repo w chwili scalania. Dwie ponizsze stale
(`PREFIKS_ZNACZNIKA_NOTATKI`, `ZNACZNIK_ROBOCZY`) sa dlatego LUSTREM jego
planowanego ksztaltu, nie importem z niego -- gdy W1 wyladuje, warto
sprawdzic, czy nazwy/wartosci sie zgadzaja i docelowo zaimportowac
bezposrednio (`crm.volteo_notatki.PREFIKS_ZNACZNIKA` / `ZNACZNIK_ROBOCZY`)
zamiast duplikowac. To samo dotyczy mapy etykiet zakladek notatek nizej.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ---------------------------------------------------------------------------
# Znaczniki na CRM Deal.attached_to_field
# ---------------------------------------------------------------------------

PREFIKS_ZNACZNIKA_NOTATKI = "notatka_"
"""Lustro planowanego `crm.volteo_notatki.PREFIKS_ZNACZNIKA` (issue W1/ops#198,
jeszcze nie scalone w chwili pisania tego modulu). Kazdy zalacznik notatki
siedzi na `CRM Deal` ze znacznikiem `notatka_<nazwa notatki>`."""

ZNACZNIK_ROBOCZY = "notatka_robocza"
"""Lustro planowanego `crm.volteo_notatki.ZNACZNIK_ROBOCZY`. Pliki wgrane do
karty "Dodaj notatke", zanim notatka zostanie faktycznie zapisana -- widoczne
WYLACZNIE dla ich wlasciciela, nigdy dla innych uzytkownikow szansy."""

ZNACZNIK_ZDJEC_MONTAZU = "zdjecia_montaz"
"""Lustro `crm.api.montaz.ZNACZNIK_ZDJEC_MONTAZU` -- ten modul nie moze
zaimportowac tamtego pliku wprost (importuje `frappe`, wiec zepsulby test
lokalny bez zainstalowanego frameworka)."""


# ---------------------------------------------------------------------------
# Kategorie pliku (dokument / obraz / wideo / inny) -- decyzja wlasciciela
# 2026-09-28: feed pokazuje wszystko, przelacznik robi frontend.
# ---------------------------------------------------------------------------

KAT_DOKUMENT = "dokument"
KAT_OBRAZ = "obraz"
KAT_WIDEO = "wideo"
KAT_INNY = "inny"

KATEGORIE: tuple[str, ...] = (KAT_DOKUMENT, KAT_OBRAZ, KAT_WIDEO, KAT_INNY)

ROZSZERZENIA_WIDEO = frozenset({"mp4", "mov", "webm", "m4v"})
"""Lustro `frontend/src/utils/audytPodglad.js::ROZSZERZENIA_WIDEO`."""

ROZSZERZENIA_OBRAZOW = frozenset({"jpg", "jpeg", "png", "webp", "gif"})
"""Kanon rozszerzen obrazow -- skladnik `ROZSZERZENIA_MEDIOW_MONTAZU`/
`czy_media_montazu` nizej, uzywanych przez galerie "Zdjecia z realizacji"
w `crm.api.montaz` (dawniej lokalna `_ROZSZERZENIA_OBRAZOW` w tamtym
module, usunieta w b66 na rzecz tego jednego zbioru)."""

ROZSZERZENIA_MEDIOW_MONTAZU = ROZSZERZENIA_OBRAZOW | ROZSZERZENIA_WIDEO
"""Rozszerzenia dopuszczone w galerii "Zdjęcia z realizacji" (`crm.api.montaz`,
ops#191 + wideo w montażu): obrazy (`ROZSZERZENIA_OBRAZOW`) plus wideo
(`ROZSZERZENIA_WIDEO`, ten sam zbior co sloty Audytu z `allowVideo`, b63
ops#190). Nazwa celowo osobna od `ROZSZERZENIA_OBRAZOW`/`ROZSZERZENIA_WIDEO`,
zeby `crm.api.montaz` mogl zaimportowac jeden, gotowy zbior bez budowania go
po swojej stronie."""

ROZSZERZENIA_DOKUMENTOW = frozenset(
	{"pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "odt", "ods", "rtf"}
)
"""Rozszerzenia traktowane jako "dokument" w feedzie Pliki -- szerszy zbior niz
sama umowa/kredyt (PDF), bo Luzem moze dostac dowolny plik biurowy."""

TYPY_MIME_WIDEO_PREFIKS = "video/"
TYPY_MIME_OBRAZU_PREFIKS = "image/"


def _rozszerzenie(file_name: str | None) -> str:
	"""Rozszerzenie pliku (bez kropki, male litery), albo pusty string."""
	nazwa = (file_name or "").strip()
	if "." not in nazwa:
		return ""
	return nazwa.rsplit(".", 1)[-1].lower()


def czy_media_montazu(file_name: str | None) -> bool:
	"""Czy nazwa pliku ma jedno z rozszerzen dopuszczonych w galerii
	"Zdjecia z realizacji" (obraz albo wideo). Brak nazwy, pusta nazwa albo
	nazwa bez rozszerzenia -> False, nigdy wyjatek."""
	rozszerzenie = _rozszerzenie(file_name)
	return bool(rozszerzenie) and rozszerzenie in ROZSZERZENIA_MEDIOW_MONTAZU


def kategoria_pliku(file_name: str | None, file_type: str | None) -> str:
	"""Kategoria pliku dla przelacznika Dokumenty / Zdjecia i filmy / Wszystko.

	Rozszerzenie nazwy pliku ma PIERWSZENSTWO nad `file_type` -- `file_type`
	bywa puste (szczegolnie dla plikow wgranych z Androida, patrz
	`frontend/src/utils/audytPodglad.js`), a rozszerzenie zawsze jest znane,
	bo `File.file_name` zawsze je niesie w tym forku."""
	rozszerzenie = _rozszerzenie(file_name)
	if rozszerzenie in ROZSZERZENIA_WIDEO:
		return KAT_WIDEO
	if rozszerzenie in ROZSZERZENIA_OBRAZOW:
		return KAT_OBRAZ
	if rozszerzenie in ROZSZERZENIA_DOKUMENTOW:
		return KAT_DOKUMENT

	typ = (file_type or "").strip().lower()
	if typ:
		if typ.startswith(TYPY_MIME_WIDEO_PREFIKS):
			return KAT_WIDEO
		if typ.startswith(TYPY_MIME_OBRAZU_PREFIKS):
			return KAT_OBRAZ
		if typ == "application/pdf":
			return KAT_DOKUMENT

	return KAT_INNY


# ---------------------------------------------------------------------------
# Sloty Audytu OZE i CP -- lustro etykiet z kodu audytu (issue tresc,
# "zrodlo prawdy w kodzie audytu"). OZE: `ops/crm-audyt.py` (Server Script
# generuje macierz `volteo_audyt_requirements` w safe_exec, wiec nie da sie
# tego zaimportowac -- to jest LUSTRO, aktualizowac recznie przy zmianie
# slotow). CP: `crm.czyste_powietrze.audyt.SLOTY_DOKUMENTOW`/`etykieta_dla`
# (frappe-free, importowane wprost przez `crm.api.pliki`, WIEC ta mapa ponizej
# jest uzywana tylko jako fallback, gdyby import kiedys zawiodl).
# ---------------------------------------------------------------------------

ETYKIETY_SLOTOW_AUDYTU_OZE: dict[str, str] = {
	"rozdzielnica": "Rozdzielnica główna",
	"dach_polac": "Miejsce montażu paneli (dach / grunt)",
	"miejsce_magazynu": "Miejsce montażu magazynu",
	"faktura_energia": "Faktura za energię (PDF)",
}
"""Lustro `ops/crm-audyt.py::PHOTO_ROZDZIELNICA/PHOTO_DACH/PHOTO_MAGAZYN/PHOTO_FAKTURA`
(macierz `REQUIREMENTS`, b44). Zaktualizowac recznie, jesli macierz slotow
OZE kiedykolwiek sie zmieni."""


def etykieta_slotu_audytu_oze(klucz_slotu: str) -> str:
	"""Etykieta slotu Audytu OZE, albo sam klucz gdy nieznany (nowy slot
	dodany w macierzy, a ta mapa jeszcze nie zaktualizowana -- lepiej pokazac
	surowy klucz niz zgubic plik)."""
	return ETYKIETY_SLOTOW_AUDYTU_OZE.get(klucz_slotu, klucz_slotu)


# ---------------------------------------------------------------------------
# Zakladki notatek -- lustro planowanego `crm.volteo_notatki.ZAKLADKI` /
# `ETYKIETY_ZAKLADEK` (issue W1/ops#198). Uzywane tylko do wyswietlenia
# etykiety "Notatka: <etykieta zakladki>" i do hasha nawigacji.
# ---------------------------------------------------------------------------

ETYKIETY_ZAKLADEK_NOTATEK: dict[str, str] = {
	"Zestaw": "Zestaw",
	"Umowa": "Umowa",
	"Kredyt": "Kredyt",
	"Faktury": "Faktury",
	"Montaz": "Montaż",
	"OSD": "OSD",
	"Dotacja": "Dotacja",
	"Trify": "Trify",
}

HASH_ZAKLADEK_NOTATEK: dict[str, str] = {
	"Zestaw": "zestaw",
	"Umowa": "umowa",
	"Kredyt": "kredyt",
	"Faktury": "faktury",
	"Montaz": "montaz",
	"OSD": "osd",
	"Dotacja": "dotacja",
	"Trify": "trify",
}


def etykieta_zakladki_notatki(kod_zakladki: str | None) -> str | None:
	if not kod_zakladki:
		return None
	return ETYKIETY_ZAKLADEK_NOTATEK.get(kod_zakladki, kod_zakladki)


def hash_zakladki_notatki(kod_zakladki: str | None) -> str:
	if not kod_zakladki:
		return "notatki"
	return HASH_ZAKLADEK_NOTATEK.get(kod_zakladki, "notatki")


# ---------------------------------------------------------------------------
# Zrodla -- katalog kluczy, etykiet (ew. z placeholderem "{szczegol}") i
# priorytetu dedupu (KOLEJNOSC KROTKI = priorytet, indeks 0 wygrywa zawsze).
# ---------------------------------------------------------------------------

ZRODLO_AUDYT_SLOT = "audyt_slot"
ZRODLO_AUDYT_DODATKOWE = "audyt_dodatkowe"
ZRODLO_AUDYT_KOMENTARZ = "audyt_komentarz"
ZRODLO_AUDYT_CP_SLOT = "audyt_cp_slot"
ZRODLO_AUDYT_CP_GALERIA = "audyt_cp_galeria"
ZRODLO_FAKTURA = "faktura"
ZRODLO_UMOWA_PODPISANA = "umowa_podpisana"
ZRODLO_KREDYT_PODPISANY = "kredyt_podpisany"
ZRODLO_UMOWA_PDF = "umowa_pdf"
ZRODLO_KREDYT_PDF = "kredyt_pdf"
ZRODLO_NOTATKA = "notatka"
ZRODLO_MONTAZ_ZDJECIE = "montaz_zdjecie"
ZRODLO_KOMENTARZ = "komentarz"
ZRODLO_EMAIL = "email"
ZRODLO_LEAD = "lead"
ZRODLO_ROBOCZE = "robocze"
ZRODLO_LUZEM = "luzem"

# Kolejnosc ponizej JEST priorytetem dedupu (scal_po_url): im wczesniej w
# krotce, tym wyzszy priorytet (wygrywa przy tym samym file_url). Zgodne co
# do litery z kolejnoscia zrodel w tresci issue ops#199.
ZRODLA: tuple[dict[str, Any], ...] = (
	{"klucz": ZRODLO_AUDYT_SLOT, "etykieta": "Audyt: {szczegol}", "etykieta_domyslna": "Audyt: załącznik"},
	{"klucz": ZRODLO_AUDYT_DODATKOWE, "etykieta": "Audyt: zdjęcie dodatkowe"},
	{"klucz": ZRODLO_AUDYT_KOMENTARZ, "etykieta": "Audyt: komentarz"},
	{
		"klucz": ZRODLO_AUDYT_CP_SLOT,
		"etykieta": "Audyt CP: {szczegol}",
		"etykieta_domyslna": "Audyt CP: załącznik",
	},
	{"klucz": ZRODLO_AUDYT_CP_GALERIA, "etykieta": "Audyt CP: galeria"},
	{"klucz": ZRODLO_FAKTURA, "etykieta": "Faktura"},
	{"klucz": ZRODLO_UMOWA_PODPISANA, "etykieta": "Umowa podpisana"},
	{"klucz": ZRODLO_KREDYT_PODPISANY, "etykieta": "Kredyt podpisany"},
	{"klucz": ZRODLO_UMOWA_PDF, "etykieta": "Umowa PDF"},
	{"klucz": ZRODLO_KREDYT_PDF, "etykieta": "Kredyt PDF"},
	{"klucz": ZRODLO_NOTATKA, "etykieta": "Notatka: {szczegol}", "etykieta_domyslna": "Notatka"},
	{"klucz": ZRODLO_MONTAZ_ZDJECIE, "etykieta": "Montaż: zdjęcie"},
	{"klucz": ZRODLO_KOMENTARZ, "etykieta": "Komentarz"},
	{"klucz": ZRODLO_EMAIL, "etykieta": "E-mail"},
	{"klucz": ZRODLO_LEAD, "etykieta": "Lead"},
	{"klucz": ZRODLO_ROBOCZE, "etykieta": "Robocze"},
	{"klucz": ZRODLO_LUZEM, "etykieta": "Luzem"},
)

PRIORYTET_ZRODLA: dict[str, int] = {zrodlo["klucz"]: idx for idx, zrodlo in enumerate(ZRODLA)}
_ETYKIETA_ZRODLA: dict[str, str] = {zrodlo["klucz"]: zrodlo["etykieta"] for zrodlo in ZRODLA}
_ETYKIETA_DOMYSLNA_ZRODLA: dict[str, str] = {
	zrodlo["klucz"]: zrodlo.get("etykieta_domyslna", zrodlo["etykieta"]) for zrodlo in ZRODLA
}

# Zrodla, ktorych plik jest "systemowy" -- generowany/kontrolowany przez
# system (umowa/kredyt, niepodpisany albo podpisany przez Autenti). Nigdy nie
# wolno zmienic im nazwy ani usunac z feedu Pliki.
ZRODLA_SYSTEMOWE: frozenset[str] = frozenset(
	{ZRODLO_UMOWA_PDF, ZRODLO_KREDYT_PDF, ZRODLO_UMOWA_PODPISANA, ZRODLO_KREDYT_PODPISANY}
)

# Docelowa zakladka (hash nawigacji) dla kazdego zrodla. "attachments" =
# zostan na miejscu (zakladka Pliki), plik nie ma bardziej szczegolowego celu.
ZAKLADKA_DLA_ZRODLA: dict[str, str] = {
	ZRODLO_AUDYT_SLOT: "audyt",
	ZRODLO_AUDYT_DODATKOWE: "audyt",
	ZRODLO_AUDYT_KOMENTARZ: "audyt",
	ZRODLO_AUDYT_CP_SLOT: "audyt",
	ZRODLO_AUDYT_CP_GALERIA: "audyt",
	ZRODLO_FAKTURA: "faktury",
	ZRODLO_UMOWA_PODPISANA: "umowa",
	ZRODLO_KREDYT_PODPISANY: "kredyt",
	ZRODLO_UMOWA_PDF: "umowa",
	ZRODLO_KREDYT_PDF: "kredyt",
	ZRODLO_NOTATKA: "notatki",
	ZRODLO_MONTAZ_ZDJECIE: "montaz",
	ZRODLO_KOMENTARZ: "attachments",
	ZRODLO_EMAIL: "attachments",
	ZRODLO_LEAD: "attachments",
	ZRODLO_ROBOCZE: "notatki",
	ZRODLO_LUZEM: "attachments",
}


def etykieta_zrodla(klucz: str, szczegol: str | None = None) -> str:
	"""Etykieta widoczna w wierszu feedu dla `klucz` (jedno z `ZRODLA`).

	Gdy szablon niesie `{szczegol}` (np. "Audyt: {szczegol}"), wypelnia go
	`szczegol` (etykieta slotu / etykieta zakladki notatki); brak `szczegol`
	daje etykiete domyslna tego zrodla ("Audyt: załącznik", "Notatka")."""
	wzor = _ETYKIETA_ZRODLA.get(klucz, klucz)
	if "{szczegol}" in wzor:
		if szczegol:
			return wzor.format(szczegol=szczegol)
		return _ETYKIETA_DOMYSLNA_ZRODLA.get(klucz, klucz)
	return wzor


def zakladka_dla_zrodla(klucz: str, kod_zakladki_notatki: str | None = None) -> str:
	"""Hash zakladki, do ktorej wiersz "Pliki" powinien nawigowac po kliknieciu.

	Dla `notatka`/`robocze` uzywa `kod_zakladki_notatki` (zakladka WLASNA
	notatki, np. "Montaz"), gdy jest znany -- inaczej wraca do ogolnego
	feedu "Notatki"."""
	if klucz in (ZRODLO_NOTATKA, ZRODLO_ROBOCZE) and kod_zakladki_notatki:
		return hash_zakladki_notatki(kod_zakladki_notatki)
	return ZAKLADKA_DLA_ZRODLA.get(klucz, "attachments")


# ---------------------------------------------------------------------------
# Klasyfikacja pojedynczego pliku
# ---------------------------------------------------------------------------


def czy_widoczne_robocze(wlasciciel: str | None, user: str | None) -> bool:
	"""Plik roboczy notatki jest widoczny WYLACZNIE dla jego wlasciciela --
	nigdy dla innych uzytkownikow tej samej szansy, choc szansa jest wspolna."""
	return bool(wlasciciel) and wlasciciel == user


def _dopasuj_po_url(url: str | None, kontekst: dict[str, Any]) -> tuple[str, str | None] | None:
	"""Probuje dopasowac `url` do jednego ze slownikow kontekstu, w kolejnosci
	priorytetu `ZRODLA`. Zwraca (zrodlo, szczegol) albo None gdy nic nie
	pasuje -- wolajacy decyduje wtedy o domyslnym zrodle (zwykle "luzem").

	Uzywane dla plikow podpietych WPROST pod `CRM Deal` (bez wlasnego
	znacznika), ktore w praktyce sa duplikatami pliku podpietego tez pod
	dokument nadrzedny (Faktura/Umowa/Kredyt) -- patrz docstring modulu
	`crm.api.montaz` o dedupie `File` po `content_hash`."""
	if not url:
		return None

	url_slotow_audytu = kontekst.get("url_slotow_audytu") or {}
	if url in url_slotow_audytu:
		return ZRODLO_AUDYT_SLOT, url_slotow_audytu[url]

	url_dodatkowych = kontekst.get("url_dodatkowych") or ()
	if url in url_dodatkowych:
		return ZRODLO_AUDYT_DODATKOWE, None

	url_komentarzy_audytu = kontekst.get("url_komentarzy_audytu") or ()
	if url in url_komentarzy_audytu:
		return ZRODLO_AUDYT_KOMENTARZ, None

	url_slotow_cp = kontekst.get("url_slotow_cp") or {}
	if url in url_slotow_cp:
		return ZRODLO_AUDYT_CP_SLOT, url_slotow_cp[url]

	url_galerii_cp = kontekst.get("url_galerii_cp") or ()
	if url in url_galerii_cp:
		return ZRODLO_AUDYT_CP_GALERIA, None

	url_faktur = kontekst.get("url_faktur") or ()
	if url in url_faktur:
		return ZRODLO_FAKTURA, None

	url_podpisanych = kontekst.get("url_podpisanych") or {}
	if url in url_podpisanych:
		return url_podpisanych[url], None

	url_komentarzy = kontekst.get("url_komentarzy") or ()
	if url in url_komentarzy:
		return ZRODLO_KOMENTARZ, None

	url_emaili = kontekst.get("url_emaili") or ()
	if url in url_emaili:
		return ZRODLO_EMAIL, None

	return None


def klasyfikuj_plik_szansy(plik: dict[str, Any], kontekst: dict[str, Any]) -> dict[str, Any]:
	"""Klasyfikuje JEDEN wiersz `File` do jednego z `ZRODLA` i zwraca NOWY
	slownik (nigdy nie mutuje `plik`) gotowy do dedupu (`scal_po_url`) i
	sortowania (`posortuj`).

	`plik` niesie co najmniej: `name`, `file_name`, `file_url`, `file_size`,
	`file_type`, `creation`, `owner`, `is_private`, `attached_to_doctype`,
	`attached_to_name`, `attached_to_field`.

	`kontekst` niesie slowniki zbudowane przez `crm.api.pliki.feed` z bazy:
	`url_faktur`, `url_slotow_audytu` (url -> etykieta slotu),
	`url_dodatkowych`, `url_slotow_cp` (url -> etykieta slotu CP),
	`url_galerii_cp`, `url_komentarzy_audytu`, `url_komentarzy`,
	`url_emaili`, `url_podpisanych` (url -> "umowa_podpisana"/"kredyt_podpisany"),
	`notatki` (nazwa notatki -> kod zakladki), `systemowe` (callable
	`file_name -> "umowa_pdf" | "kredyt_pdf" | None`), `user` (biezacy
	uzytkownik, dla `robocze`)."""
	attached_to_doctype = plik.get("attached_to_doctype")
	attached_to_field = plik.get("attached_to_field") or ""
	url = plik.get("file_url")

	szczegol: str | None = None
	kod_zakladki_notatki: str | None = None

	if attached_to_doctype == "Volteo Audyt":
		dopasowanie = _dopasuj_po_url(url, {"url_slotow_audytu": kontekst.get("url_slotow_audytu"),
											"url_dodatkowych": kontekst.get("url_dodatkowych")})
		if dopasowanie:
			zrodlo, szczegol = dopasowanie
		else:
			zrodlo = ZRODLO_AUDYT_SLOT

	elif attached_to_doctype == "Volteo Audyt CP":
		dopasowanie = _dopasuj_po_url(url, {"url_slotow_cp": kontekst.get("url_slotow_cp"),
											"url_galerii_cp": kontekst.get("url_galerii_cp")})
		if dopasowanie:
			zrodlo, szczegol = dopasowanie
		else:
			zrodlo = ZRODLO_AUDYT_CP_SLOT

	elif attached_to_doctype == "Comment":
		url_komentarzy_audytu = kontekst.get("url_komentarzy_audytu") or ()
		url_komentarzy = kontekst.get("url_komentarzy") or ()
		if url in url_komentarzy_audytu:
			zrodlo = ZRODLO_AUDYT_KOMENTARZ
		elif url in url_komentarzy:
			zrodlo = ZRODLO_KOMENTARZ
		else:
			# Bezpieczny domyslny: kazdy plik podpiety pod Comment, ktorego
			# nie rozpoznajemy, traktujemy jak zwykly komentarz -- nigdy nie
			# gubimy pliku milczaco.
			zrodlo = ZRODLO_KOMENTARZ

	elif attached_to_doctype == "Communication":
		zrodlo = ZRODLO_EMAIL

	elif attached_to_doctype == "Volteo Faktura":
		zrodlo = ZRODLO_FAKTURA

	elif attached_to_doctype == "Volteo Umowa":
		zrodlo = ZRODLO_UMOWA_PODPISANA

	elif attached_to_doctype == "Volteo Kredyt":
		zrodlo = ZRODLO_KREDYT_PODPISANY

	elif attached_to_doctype == "CRM Lead":
		zrodlo = ZRODLO_LEAD

	elif attached_to_doctype == "CRM Deal":
		if attached_to_field == ZNACZNIK_ZDJEC_MONTAZU:
			zrodlo = ZRODLO_MONTAZ_ZDJECIE
		elif attached_to_field == ZNACZNIK_ROBOCZY:
			zrodlo = ZRODLO_ROBOCZE
		elif attached_to_field.startswith(PREFIKS_ZNACZNIKA_NOTATKI):
			zrodlo = ZRODLO_NOTATKA
			nazwa_notatki = attached_to_field[len(PREFIKS_ZNACZNIKA_NOTATKI):]
			kod_zakladki_notatki = (kontekst.get("notatki") or {}).get(nazwa_notatki)
			szczegol = etykieta_zakladki_notatki(kod_zakladki_notatki)
		else:
			systemowe = kontekst.get("systemowe")
			wynik_systemowy = systemowe(plik.get("file_name")) if callable(systemowe) else None
			if wynik_systemowy:
				zrodlo = wynik_systemowy
			else:
				dopasowanie = _dopasuj_po_url(url, kontekst)
				if dopasowanie:
					zrodlo, szczegol = dopasowanie
				else:
					zrodlo = ZRODLO_LUZEM

	else:
		# Rodzic nieznany temu modulowi -- bezpieczny domyslny "luzem", zeby
		# plik nigdy nie zgubil sie milczaco z feedu.
		zrodlo = ZRODLO_LUZEM

	kategoria = kategoria_pliku(plik.get("file_name"), plik.get("file_type"))

	return {
		"klucz": plik.get("name"),
		"file_name": plik.get("file_name"),
		"file_url": url,
		"file_size": plik.get("file_size"),
		"file_type": plik.get("file_type"),
		"kategoria": kategoria,
		"zrodlo": zrodlo,
		"zrodlo_etykieta": etykieta_zrodla(zrodlo, szczegol),
		"zrodlo_szczegol": szczegol,
		"zakladka": zakladka_dla_zrodla(zrodlo, kod_zakladki_notatki),
		"autor": plik.get("owner"),
		"data": plik.get("creation"),
		"is_private": plik.get("is_private"),
	}


# ---------------------------------------------------------------------------
# Dedup, agregacja zrodel, sortowanie, flagi
# ---------------------------------------------------------------------------


def scal_po_url(wiersze: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Deduplikuje wiersze juz sklasyfikowane przez `klasyfikuj_plik_szansy`
	po `file_url`, w obrebie szansy. Przy konflikcie wygrywa wiersz, ktorego
	zrodlo ma WYZSZY priorytet (nizszy indeks w `ZRODLA`) -- np. kopia na
	`Comment`/`Volteo Faktura`/audycie wygrywa nad "Luzem". Klucz wynikowego
	wiersza to `File.name` (`klucz`) zwyciezcy, nie zmienia sie.

	Wiersze bez `file_url` (nie powinno sie zdarzyc dla prawdziwego `File`,
	ale funkcja jest defensywna) traktowane sa jako WLASNA grupa kazdy, po
	`klucz` -- nigdy nie collapsuja sie ze soba.

	Zwraca NOWA liste, nie mutuje `wiersze` ani zadnego wiersza w niej."""
	najlepszy_dla_url: dict[str, dict[str, Any]] = {}
	kolejnosc_grup: list[str] = []

	for wiersz in wiersze:
		url = wiersz.get("file_url")
		klucz_grupy = url if url else f"__brak_url__:{wiersz.get('klucz')}"

		obecny = najlepszy_dla_url.get(klucz_grupy)
		if obecny is None:
			najlepszy_dla_url[klucz_grupy] = wiersz
			kolejnosc_grup.append(klucz_grupy)
			continue

		priorytet_nowego = PRIORYTET_ZRODLA.get(wiersz.get("zrodlo"), len(ZRODLA))
		priorytet_obecnego = PRIORYTET_ZRODLA.get(obecny.get("zrodlo"), len(ZRODLA))
		if priorytet_nowego < priorytet_obecnego:
			najlepszy_dla_url[klucz_grupy] = wiersz

	return [najlepszy_dla_url[klucz_grupy] for klucz_grupy in kolejnosc_grup]


def zbuduj_zrodla(wiersze: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Legenda/licznik zrodel obecnych w `wiersze`, w kolejnosci priorytetu
	`ZRODLA`; pomija zrodla z licznikiem 0. Etykieta jest ogolna (domyslna,
	bez wypelnionego `{szczegol}`) -- to zbiorcza pozycja filtra, nie
	pojedynczy wiersz."""
	liczniki: dict[str, int] = {}
	for wiersz in wiersze:
		klucz = wiersz.get("zrodlo")
		liczniki[klucz] = liczniki.get(klucz, 0) + 1

	wynik = []
	for zrodlo in ZRODLA:
		klucz = zrodlo["klucz"]
		liczba = liczniki.get(klucz, 0)
		if liczba:
			wynik.append(
				{
					"klucz": klucz,
					"etykieta": _ETYKIETA_DOMYSLNA_ZRODLA.get(klucz, zrodlo["etykieta"]),
					"liczba": liczba,
				}
			)
	return wynik


def posortuj(wiersze: list[dict[str, Any]], kierunek: str = "desc") -> list[dict[str, Any]]:
	"""Sortuje `wiersze` po `data` (creation). Domyslnie `desc` (najnowsze
	pierwsze), `asc` odwraca. Zwraca NOWA liste (posortowana kopia), nigdy
	nie mutuje wejscia. Nieznany `kierunek` traktowany jak "desc". Brak
	`data` traktowany jak "najstarsza mozliwa" -- w `desc` taki wiersz
	ladowany jest na koniec listy."""
	return sorted(wiersze, key=lambda w: w.get("data") or "", reverse=(kierunek != "asc"))


def flagi(wiersz: dict[str, Any], can_write: bool, can_rename: bool) -> dict[str, Any]:
	"""Zwraca NOWY slownik (kopia `wiersz` plus `mozna_zmienic_nazwe` i
	`mozna_usunac`) -- nigdy nie mutuje `wiersz`.

	`mozna_zmienic_nazwe` = `can_rename` (rownowaznik dzisiejszego "olowka",
	admin/backoffice) ORAZ plik nie jest systemowy (`ZRODLA_SYSTEMOWE`).
	`mozna_usunac` = `can_write` (prawo zapisu na szansie) ORAZ zrodlo to
	dokladnie "luzem" -- pliki notatek kasuje tylko notatka
	(`crm.api.notatki.usun_plik_roboczy`), a systemowe/z dokumentow
	nadrzednych nigdy nie znikaja z tego feedu."""
	zrodlo = wiersz.get("zrodlo")
	mozna_zmienic_nazwe = bool(can_rename) and zrodlo not in ZRODLA_SYSTEMOWE
	mozna_usunac = bool(can_write) and zrodlo == ZRODLO_LUZEM
	return {**wiersz, "mozna_zmienic_nazwe": mozna_zmienic_nazwe, "mozna_usunac": mozna_usunac}


def zbuduj_callable_systemowe(
	czy_plik_systemowy_umowy: Callable[[str], bool],
	czy_plik_systemowy_kredytu: Callable[[str], bool],
) -> Callable[[str | None], str | None]:
	"""Sklada dwa rozpoznawacze prefiksu (patrz `crm.volteo_zalaczniki`) w
	JEDEN callable do wstawienia w `kontekst["systemowe"]`. Umowa sprawdzana
	przed kredytem (kolejnosc bez znaczenia w praktyce, prefiksy sie nie
	pokrywaja, ale kolejnosc jest deterministyczna dla czytelnosci)."""

	def _systemowe(file_name: str | None) -> str | None:
		if not file_name:
			return None
		if czy_plik_systemowy_umowy(file_name):
			return ZRODLO_UMOWA_PDF
		if czy_plik_systemowy_kredytu(file_name):
			return ZRODLO_KREDYT_PDF
		return None

	return _systemowe
