# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Feed "Pliki" (zakładka szansy, issue GlintShade/proenergy-crm-ops#199):
KAŻDY załącznik powiązany z szansą, jednym zapytaniem, z etykietą źródła.

Frontend woła te endpointy WYŁĄCZNIE pełną kropkowaną ścieżką
(`crm.api.pliki.feed` / `crm.api.pliki.usun`) -- gołe nazwy metod dają HTTP
417 dla wywołań `call()`, pułapka udokumentowana przy innych whitelisted API
forka (`Volteo Umowa`/`Volteo Kredyt`/`crm.api.montaz`).

Cała klasyfikacja/dedup/sortowanie/flagi żyje w `crm.volteo_pliki`
(frappe-free, testowalne bez zainstalowanego `frappe`); ten moduł tylko
czyta bazę, sprawdza uprawnienia i składa kontekst.

Uprawnienia listy `File` są owner-based (`frappe.get_all("File", ...)` jako
handlowiec zwróci tylko WŁASNE pliki, mimo że `has_permission("File", "read",
doc=plik kolegi na tej samej szansie)` da `True` przez `attached_to`) -- patrz
`crm.api.montaz` i `crm.api.activities.get_attachments`, ten sam problem, to
samo rozwiązanie: `frappe.db.get_all` (pomija uprawnienia `File`), zawsze PO
jawnym `frappe.has_permission` na dokumencie nadrzędnym (szansa i, per
źródło, każdy dokument nadrzędny -- Volteo Umowa/Kredyt/Audyt/Audyt CP/
Faktura, CRM Lead). Brak uprawnienia do dokumentu nadrzędnego = jego pliki
SĄ POMIJANE, nigdy wyjątek -- każde źródło żyje we własnym `try/except` z
`frappe.log_error`, wzór `crm.api.activities.get_volteo_linked_activities`,
żeby jeden zepsuty JSON audytu (albo brakujący dokument) nie wywalał całego
feedu."""

from typing import Any

import frappe
from frappe import _

from crm.czyste_powietrze.audyt import etykieta_dla as etykieta_slotu_cp
from crm.czyste_powietrze.audyt import parsuj_liste, parsuj_mape
from crm.integrations.autenti.logika import nazwa_pliku_umowy, prefiks_pliku_kredytu
from crm.permissions.org_hierarchy import BYPASS_ROLES
from crm.volteo_pliki import (
	ZNACZNIK_ROBOCZY,
	czy_widoczne_robocze,
	etykieta_slotu_audytu_oze,
	flagi,
	klasyfikuj_plik_szansy,
	posortuj,
	scal_po_url,
	zbuduj_callable_systemowe,
	zbuduj_zrodla,
)

POLA_FILE = [
	"name",
	"file_name",
	"file_url",
	"file_size",
	"file_type",
	"is_private",
	"creation",
	"owner",
	"attached_to_doctype",
	"attached_to_name",
	"attached_to_field",
]


def _pliki_dla(attached_to_doctype: str, attached_to_name: str | list[str]) -> list[dict[str, Any]]:
	"""`frappe.db.get_all` na `File` (pomija uprawnienia `File`, patrz docstring
	modułu) dla jednego rodzica albo listy rodziców tego samego doctype'u."""
	if isinstance(attached_to_name, list) and not attached_to_name:
		return []
	filtry = {
		"attached_to_doctype": attached_to_doctype,
		"attached_to_name": ["in", attached_to_name] if isinstance(attached_to_name, list) else attached_to_name,
	}
	return frappe.db.get_all("File", filters=filtry, fields=POLA_FILE) or []


def _czy_plik_systemowy_umowy(deal: str):
	prefiks = nazwa_pliku_umowy(deal)[: -len(".pdf")]
	return lambda file_name: bool(file_name) and file_name.startswith(prefiks)


def _czy_plik_systemowy_kredytu(deal: str):
	prefiks = prefiks_pliku_kredytu(deal, deal)
	return lambda file_name: bool(file_name) and file_name.startswith(prefiks)


def _zbierz_faktury(deal: str) -> tuple[set, list[dict[str, Any]]]:
	"""Rekordy `Volteo Faktura` widoczne wołającemu (uprawnienia deal-scoped,
	`frappe.get_all` -- permission-aware, patrz `faktura_visibility.py`) plus
	pliki podpięte wprost pod nie."""
	fakturas = frappe.get_all("Volteo Faktura", filters={"deal": deal}, fields=["name", "plik"]) or []
	url_faktur = {f.plik for f in fakturas if f.plik}
	nazwy = [f.name for f in fakturas]
	return url_faktur, _pliki_dla("Volteo Faktura", nazwy)


def _zbierz_umowe(deal: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
	url_podpisanych: dict[str, str] = {}
	pliki: list[dict[str, Any]] = []
	if frappe.db.exists("Volteo Umowa", deal) and frappe.has_permission("Volteo Umowa", "read", deal):
		signed = frappe.db.get_value("Volteo Umowa", deal, "signed_pdf_file")
		if signed:
			url_podpisanych[signed] = "umowa_podpisana"
		pliki = _pliki_dla("Volteo Umowa", deal)
	return url_podpisanych, pliki


def _zbierz_kredyty(deal: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
	"""`Volteo Kredyt` jest N:1 z szansą (ops#159) -- `frappe.get_all` już
	respektuje `has_kredyt_permission` (deal-scoped, fail-closed), więc każdy
	niewidoczny formularz jest pominięty samym zapytaniem, bez dodatkowego
	sprawdzenia tutaj."""
	kredyty = frappe.get_all("Volteo Kredyt", filters={"deal": deal}, fields=["name", "signed_pdf_file"]) or []
	url_podpisanych = {k.signed_pdf_file: "kredyt_podpisany" for k in kredyty if k.signed_pdf_file}
	nazwy = [k.name for k in kredyty]
	return url_podpisanych, _pliki_dla("Volteo Kredyt", nazwy)


def _zbierz_audyt_oze(deal: str) -> tuple[dict[str, str], set, list[dict[str, Any]], bool]:
	"""Zwraca (url_slotow, url_dodatkowych, pliki, widoczny) -- `widoczny`
	mowi wprost, czy wolajacy ma odczyt na tym audycie (niezaleznie od tego,
	czy audyt ma jeszcze jakiekolwiek zdjecia), zeby `_zbierz_komentarze`
	nie musialo zgadywac tego po pustych/niepustych slownikach."""
	url_slotow: dict[str, str] = {}
	url_dodatkowych: set = set()
	pliki: list[dict[str, Any]] = []
	widoczny = bool(frappe.db.exists("Volteo Audyt", deal)) and bool(
		frappe.has_permission("Volteo Audyt", "read", deal)
	)
	if widoczny:
		wiersz = frappe.db.get_value(
			"Volteo Audyt", deal, ["zdjecia_json", "zdjecia_dodatkowe_json"], as_dict=True
		)
		zdjecia = parsuj_mape(wiersz.zdjecia_json if wiersz else None)
		url_slotow = {url: etykieta_slotu_audytu_oze(klucz) for klucz, url in zdjecia.items() if url}
		url_dodatkowych = set(parsuj_liste(wiersz.zdjecia_dodatkowe_json if wiersz else None))
		pliki = _pliki_dla("Volteo Audyt", deal)
	return url_slotow, url_dodatkowych, pliki, widoczny


def _zbierz_audyt_cp(deal: str) -> tuple[dict[str, str], set, list[dict[str, Any]], bool]:
	"""Jak `_zbierz_audyt_oze`, dla `Volteo Audyt CP`."""
	url_slotow: dict[str, str] = {}
	url_galerii: set = set()
	pliki: list[dict[str, Any]] = []
	widoczny = bool(frappe.db.exists("Volteo Audyt CP", deal)) and bool(
		frappe.has_permission("Volteo Audyt CP", "read", deal)
	)
	if widoczny:
		wiersz = frappe.db.get_value("Volteo Audyt CP", deal, ["dokumenty_json", "zdjecia_json"], as_dict=True)
		dokumenty = parsuj_mape(wiersz.dokumenty_json if wiersz else None)
		url_slotow = {url: etykieta_slotu_cp(klucz) for klucz, url in dokumenty.items() if url}
		url_galerii = set(parsuj_liste(wiersz.zdjecia_json if wiersz else None))
		pliki = _pliki_dla("Volteo Audyt CP", deal)
	return url_slotow, url_galerii, pliki, widoczny


def _zbierz_komentarze(deal: str, ma_audyt_oze: bool, ma_audyt_cp: bool) -> tuple[set, set, list[dict[str, Any]]]:
	"""Komentarze ogólne szansy PLUS komentarze obu audytów (widoczne tylko
	gdy wołający ma odczyt na odpowiednim audycie -- flagi `ma_audyt_*`
	przekazane przez wołającego, żeby nie sprawdzać uprawnień dwa razy)."""
	nazwy_ogolne = [
		c.name
		for c in (
			frappe.db.get_all(
				"Comment",
				filters={
					"reference_doctype": "CRM Deal",
					"reference_name": deal,
					"comment_type": "Comment",
				},
				fields=["name"],
			)
			or []
		)
	]

	nazwy_audytu: list[str] = []
	for dt, widoczny in (("Volteo Audyt", ma_audyt_oze), ("Volteo Audyt CP", ma_audyt_cp)):
		if not widoczny:
			continue
		nazwy_audytu.extend(
			c.name
			for c in (
				frappe.db.get_all(
					"Comment",
					filters={
						"reference_doctype": dt,
						"reference_name": deal,
						"comment_type": "Comment",
					},
					fields=["name"],
				)
				or []
			)
		)

	wszystkie_nazwy = nazwy_ogolne + nazwy_audytu
	pliki = _pliki_dla("Comment", wszystkie_nazwy) if wszystkie_nazwy else []

	nazwy_audytu_set = set(nazwy_audytu)
	url_komentarzy_audytu = {p["file_url"] for p in pliki if p["attached_to_name"] in nazwy_audytu_set}
	url_komentarzy = {p["file_url"] for p in pliki if p["attached_to_name"] not in nazwy_audytu_set}
	return url_komentarzy_audytu, url_komentarzy, pliki


def _zbierz_emaile(deal: str) -> list[dict[str, Any]]:
	komunikaty = (
		frappe.db.get_all(
			"Communication", filters={"reference_doctype": "CRM Deal", "reference_name": deal}, fields=["name"]
		)
		or []
	)
	nazwy = [c.name for c in komunikaty]
	return _pliki_dla("Communication", nazwy) if nazwy else []


def _zbierz_lead(deal_lead: str | None) -> list[dict[str, Any]]:
	"""Pliki leada źródłowego -- TYLKO gdy wołający ma odczyt na leadzie.
	Brak uprawnienia = pliki leada pominięte, NIE wyjątek (w odróżnieniu od
	`crm.api.activities.get_deal_activities`, które w tej sytuacji wywala
	całą Aktywność -- patrz treść issue #199)."""
	if not deal_lead:
		return []
	try:
		if not frappe.has_permission("CRM Lead", "read", deal_lead):
			return []
	except frappe.DoesNotExistError:
		return []
	return _pliki_dla("CRM Lead", deal_lead)


def _notatki_dla_szansy(deal: str) -> dict[str, str]:
	"""Mapa nazwa notatki -> kod zakładki, dla plików ze znacznikiem
	`notatka_<nazwa>` na `CRM Deal`. `Volteo Notatka` (issue W1/ops#198) może
	jeszcze nie istnieć na tym środowisku w chwili scalania tego chunka --
	wtedy zwraca pusty słownik, a `crm.volteo_pliki` i tak sklasyfikuje te
	pliki jako "notatka" po samym znaczniku (etykieta domyślna)."""
	if not frappe.db.exists("DocType", "Volteo Notatka"):
		return {}
	wiersze = frappe.db.get_all("Volteo Notatka", filters={"deal": deal}, fields=["name", "zakladka"]) or []
	return {w.name: w.zakladka for w in wiersze}


def _nazwiska_autorow(nazwy_userow: set) -> dict[str, str]:
	"""Nie mutuje `nazwy_userow` -- buduje wlasny, oczyszczony zbior."""
	oczyszczone = {nazwa for nazwa in nazwy_userow if nazwa}
	if not oczyszczone:
		return {}
	wiersze = frappe.db.get_all(
		"User", filters={"name": ["in", list(oczyszczone)]}, fields=["name", "full_name"]
	)
	return {w.name: (w.full_name or w.name) for w in wiersze}


@frappe.whitelist()
def feed(deal: str) -> dict[str, Any]:
	"""Kazdy zalacznik szansy `deal`, sklasyfikowany, zdeduplikowany po
	`file_url`, posortowany od najnowszych. Patrz docstring modulu dla modelu
	uprawnien."""
	if not frappe.has_permission("CRM Deal", "read", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	deal_lead = frappe.db.get_value("CRM Deal", deal, "lead")

	surowe: list[dict[str, Any]] = []

	# 1) Pliki podpiete wprost pod CRM Deal (Luzem/Notatka/Robocze/Montaz/
	#    Systemowe/reklasyfikacja duplikatow po URL) -- zawsze pierwsze, bo
	#    kontekst ponizej musi byc zbudowany PRZED ich klasyfikacja.
	try:
		pliki_deal = _pliki_dla("CRM Deal", deal)
	except Exception:
		frappe.log_error(title="Pliki: nie udalo sie wczytac plikow szansy", message=frappe.get_traceback())
		pliki_deal = []

	url_faktur: set = set()
	pliki_faktur: list[dict[str, Any]] = []
	try:
		url_faktur, pliki_faktur = _zbierz_faktury(deal)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo faktura nie powiodlo sie", message=frappe.get_traceback())

	url_podpisanych: dict[str, str] = {}
	pliki_umowy: list[dict[str, Any]] = []
	try:
		url_podpisanych_umowa, pliki_umowy = _zbierz_umowe(deal)
		url_podpisanych.update(url_podpisanych_umowa)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo umowa nie powiodlo sie", message=frappe.get_traceback())

	pliki_kredytow: list[dict[str, Any]] = []
	try:
		url_podpisanych_kredyt, pliki_kredytow = _zbierz_kredyty(deal)
		url_podpisanych.update(url_podpisanych_kredyt)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo kredyt nie powiodlo sie", message=frappe.get_traceback())

	url_slotow_audytu: dict[str, str] = {}
	url_dodatkowych: set = set()
	pliki_audytu: list[dict[str, Any]] = []
	ma_audyt_oze = False
	try:
		url_slotow_audytu, url_dodatkowych, pliki_audytu, ma_audyt_oze = _zbierz_audyt_oze(deal)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo audyt OZE nie powiodlo sie", message=frappe.get_traceback())

	url_slotow_cp: dict[str, str] = {}
	url_galerii_cp: set = set()
	pliki_audytu_cp: list[dict[str, Any]] = []
	ma_audyt_cp = False
	try:
		url_slotow_cp, url_galerii_cp, pliki_audytu_cp, ma_audyt_cp = _zbierz_audyt_cp(deal)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo audyt CP nie powiodlo sie", message=frappe.get_traceback())

	url_komentarzy_audytu: set = set()
	url_komentarzy: set = set()
	pliki_komentarzy: list[dict[str, Any]] = []
	try:
		url_komentarzy_audytu, url_komentarzy, pliki_komentarzy = _zbierz_komentarze(
			deal, ma_audyt_oze, ma_audyt_cp
		)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo komentarze nie powiodlo sie", message=frappe.get_traceback())

	pliki_emaili: list[dict[str, Any]] = []
	try:
		pliki_emaili = _zbierz_emaile(deal)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo e-mail nie powiodlo sie", message=frappe.get_traceback())

	pliki_leada: list[dict[str, Any]] = []
	try:
		pliki_leada = _zbierz_lead(deal_lead)
	except Exception:
		frappe.log_error(title="Pliki: zrodlo lead nie powiodlo sie", message=frappe.get_traceback())

	notatki: dict[str, str] = {}
	try:
		notatki = _notatki_dla_szansy(deal)
	except Exception:
		frappe.log_error(title="Pliki: mapa notatek nie powiodla sie", message=frappe.get_traceback())

	kontekst = {
		"url_faktur": url_faktur,
		"url_slotow_audytu": url_slotow_audytu,
		"url_dodatkowych": url_dodatkowych,
		"url_slotow_cp": url_slotow_cp,
		"url_galerii_cp": url_galerii_cp,
		"url_komentarzy_audytu": url_komentarzy_audytu,
		"url_komentarzy": url_komentarzy,
		"url_emaili": set(),
		"url_podpisanych": url_podpisanych,
		"notatki": notatki,
		"systemowe": zbuduj_callable_systemowe(_czy_plik_systemowy_umowy(deal), _czy_plik_systemowy_kredytu(deal)),
		"user": frappe.session.user,
	}

	# Robocze: widoczne wylacznie dla wlasciciela pliku -- odsiane PRZED
	# klasyfikacja, zeby nigdy nie trafily do wiersza innego uzytkownika.
	pliki_deal_widoczne = [
		p
		for p in pliki_deal
		if p.get("attached_to_field") != ZNACZNIK_ROBOCZY
		or czy_widoczne_robocze(p.get("owner"), frappe.session.user)
	]

	for plik in (
		pliki_deal_widoczne
		+ pliki_faktur
		+ pliki_umowy
		+ pliki_kredytow
		+ pliki_audytu
		+ pliki_audytu_cp
		+ pliki_komentarzy
		+ pliki_emaili
		+ pliki_leada
	):
		try:
			surowe.append(klasyfikuj_plik_szansy(plik, kontekst))
		except Exception:
			frappe.log_error(
				title="Pliki: klasyfikacja pojedynczego pliku nie powiodla sie",
				message=f"plik={plik.get('name')}\n{frappe.get_traceback()}",
			)

	zdeduplikowane = scal_po_url(surowe)

	can_write = bool(frappe.has_permission("CRM Deal", "write", deal))
	can_rename = frappe.session.user == "Administrator" or bool(set(frappe.get_roles()) & BYPASS_ROLES)

	nazwiska = _nazwiska_autorow({w.get("autor") for w in zdeduplikowane})
	wiersze = [
		{**flagi(w, can_write=can_write, can_rename=can_rename), "autor_nazwa": nazwiska.get(w.get("autor"), w.get("autor"))}
		for w in zdeduplikowane
	]
	wiersze = posortuj(wiersze, "desc")

	return {
		"wiersze": wiersze,
		"can_upload": can_write,
		"can_rename": can_rename,
		"zrodla": zbuduj_zrodla(wiersze),
	}


@frappe.whitelist(methods=["POST"])
def usun(deal: str, name: str) -> None:
	"""Kasuje jeden plik "luzem" (bez znacznika, niesystemowy) podpiety wprost
	pod szanse. Nigdy `frappe.client.delete` ani `crm.api.delete_attachment`
	z frontu -- wzor `crm.api.montaz.usun_zdjecie_montazu`."""
	if not frappe.has_permission("CRM Deal", "write", deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)

	plik = frappe.db.get_value(
		"File",
		name,
		["attached_to_doctype", "attached_to_name", "attached_to_field", "file_name"],
		as_dict=True,
	)
	if not plik or plik.attached_to_doctype != "CRM Deal" or plik.attached_to_name != deal:
		frappe.throw(_("Plik nie istnieje."), frappe.DoesNotExistError)

	if plik.attached_to_field:
		frappe.throw(_("Tego pliku nie można usunąć z tego miejsca."))

	systemowy_umowy = _czy_plik_systemowy_umowy(deal)
	systemowy_kredytu = _czy_plik_systemowy_kredytu(deal)
	if systemowy_umowy(plik.file_name) or systemowy_kredytu(plik.file_name):
		frappe.throw(_("Nie można usunąć pliku systemowego."))

	frappe.delete_doc("File", name, ignore_permissions=True)
