# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Automatyczne uzupelnianie `CRM Lead.custom_czas_do_kontaktu` z PIERWSZEJ
notatki CC/backoffice na leadzie (Zadanie H, decyzja wlasciciela 2026-11-05).

Hook: `Comment.after_insert` (patrz `crm/hooks.py`), rownolegle do
istniejacego `crm.utils.on_comment_insert` - ten modul go nie zmienia ani nie
zastepuje, oba sa wpisane obok siebie na liscie `after_insert` tego samego
zdarzenia.

Czysta decyzja/liczenie czasu zyje w `crm.volteo_leady_kontakt`
(frappe-free, testowalne bez Frappe - patrz `crm/test_volteo_leady_kontakt.py`).
Ten modul niesie WYLACZNIE warstwe frappe-owa:
  - odczyt roli autora notatki (`frappe.get_roles`),
  - odczyt reguly `Volteo Automatyzacja` (klucz `KLUCZ_REGULY`) - brak wiersza
    (doctype jeszcze nie zasiany skryptem ops) jest traktowany jako WLACZONA
    (decyzja wlasciciela: ta automatyzacja jest domyslnie wlaczona), jawne
    `wlaczona = 0` jako wylaczona,
  - zapis pola przez `frappe.db.set_value` zamiast `doc.save()`: pole ma
    permlevel 3, autor notatki (Call Center/Backend) ma tam DocPerm
    read+write (ops#312), ale pelny zapis dokumentu przez ORM odpalilby
    walidacje i efekty uboczne kontrolera `CRMLead` niezwiazane z tym polem,
    `frappe.db.set_value` omija to bezpiecznie (zostaje zwykla aktualizacja
    `modified`/`modified_by` - to realna zmiana danych leada, ma wygladac
    jak kazda inna aktualizacja pola, nie jak cicha zmiana w tle),
  - slad w Aktywnosci przez `crm.volteo_aktywnosc.zapisz_slad`, oznaczony
    `ZNACZNIK_D2D_UKRYTY` (patrz tamten modul) - widoczny dla wszystkich poza
    handlowcem (D2D), ktory i tak nie czyta samego pola (permlevel 3),
  - sygnal realtime (Zadanie J) po udanym zapisie: `frappe.db.set_value` (w
    przeciwienstwie do `doc.save()`) nie publikuje nic do socketu, wiec bez
    tego otwarty widok leada (prawy panel, zakladka Szczegoly, szybki
    podglad na mapie) pokazywal stary, pusty czas do odswiezenia strony.
    `_powiadom_realtime` wysyla DOKLADNIE te same zdarzenia co
    `frappe.model.document.Document.notify_update()` przy zwyklym zapisie
    dokumentu (`doc_update` do pokoju dokumentu, `list_update` do pokoju
    doctype'u) - front (`frontend/src/data/document.js` ->
    `useDocument()` -> `createDocumentResource` z pakietu `frappe-ui`,
    `realtime: true`) juz nasluchuje `list_update` (dokladnie tak samo jak na
    zwykly zapis dokumentu) i na pasujace `{doctype, name}` sam dociaga caly
    dokument przez API z pelnym sprawdzeniem uprawnien wywolujacego -
    zdarzenie nie niesie wiec WARTOSCI pola permlevel 3, tylko sygnal "ten
    dokument sie zmienil". Lista leadow (`frontend/src/pages/Leads.vue` ->
    `ViewControls.vue`) nie korzysta z tego mechanizmu frappe-ui (wlasny
    zasob przez `crm.api.doc.get_data`, bez `realtime`) - jej odswiezanie na
    zywo to osobny zakres, poza tym modulem.

Nigdy nie wolno mu rzucic wyjatkiem: zapisanie notatki (komentarza) ma sie
udac zawsze, niezaleznie od tego, czy ta automatyzacja sie powiedzie - stad
cale dzialanie w try/except z `frappe.log_error`.
"""

import frappe
from frappe.core.doctype.comment.comment import Comment
from frappe.utils import cint

from crm.volteo_aktywnosc import ZNACZNIK_D2D_UKRYTY, tekst_sladu, zapisz_slad
from crm.volteo_leady_kontakt import (
	czy_uzupelnic_czas_kontaktu,
	formatuj_gg_mm,
	sekundy_do_pierwszego_kontaktu,
)

KLUCZ_REGULY = "czas_kontaktu_z_notatki"
"""Klucz wiersza `Volteo Automatyzacja` (typ "Pole") sterujacego ta
automatyzacja; zasiewany przez ops/crm-automatyzacja-czas-kontaktu.py."""


def on_comment_insert(doc: Comment, method: str | None = None) -> None:
	"""Hook `Comment.after_insert` - patrz docstring modulu."""
	try:
		_uzupelnij(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Volteo: automatyczny czas do pierwszego kontaktu nie powiodl sie",
		)


def _regula_wlaczona() -> bool:
	"""Czy regula `KLUCZ_REGULY` jest wlaczona. Brak wiersza (doctype jeszcze
	nie istnieje albo jeszcze nie zasiany skryptem ops) oznacza WLACZONA
	(decyzja wlasciciela: ta automatyzacja jest domyslnie wlaczona), jawne
	`wlaczona = 0` oznacza wylaczona."""
	if not frappe.db.table_exists("Volteo Automatyzacja"):
		return True
	wartosc = frappe.db.get_value("Volteo Automatyzacja", KLUCZ_REGULY, "wlaczona")
	if wartosc is None:
		return True
	return bool(cint(wartosc))


def _uzupelnij(doc: Comment) -> None:
	if doc.comment_type != "Comment":
		return
	if doc.reference_doctype != "CRM Lead" or not doc.reference_name:
		return

	# Administrator dostaje z frappe.get_roles WSZYSTKIE role (takze CC), wiec
	# jawnie go pomijamy: jego notatki nie sa kontaktem call center.
	if not doc.owner or doc.owner == "Administrator":
		return
	role_autora = frappe.get_roles(doc.owner)
	wlaczona = _regula_wlaczona()

	obecna_wartosc = frappe.db.get_value("CRM Lead", doc.reference_name, "custom_czas_do_kontaktu")
	if not czy_uzupelnic_czas_kontaktu(obecna_wartosc, role_autora, wlaczona):
		return

	creation_leada = frappe.db.get_value("CRM Lead", doc.reference_name, "creation")
	if not creation_leada:
		return

	sekundy = sekundy_do_pierwszego_kontaktu(creation_leada, doc.creation)

	# Druga, "swieza" kontrola tuz przed zapisem - minimalizuje okno wyscigu
	# dwoch rownoleglych notatek na tym samym leadzie (rola autora i flaga
	# `wlaczona` nie zmieniaja sie w trakcie jednego zadania, wiec powtarzamy
	# tylko kontrole pustego pola).
	swiezo = frappe.db.get_value("CRM Lead", doc.reference_name, "custom_czas_do_kontaktu")
	if not czy_uzupelnic_czas_kontaktu(swiezo, role_autora, wlaczona):
		return

	frappe.db.set_value("CRM Lead", doc.reference_name, "custom_czas_do_kontaktu", sekundy)

	try:
		_powiadom_realtime(doc.reference_name)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Volteo: sygnal realtime czasu do pierwszego kontaktu nie powiodl sie",
		)

	try:
		zapisz_slad(
			doc.reference_name,
			f"{ZNACZNIK_D2D_UKRYTY} " + tekst_sladu("czas_kontaktu_auto", gg_mm=formatuj_gg_mm(sekundy)),
			doctype="CRM Lead",
		)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Volteo: slad automatycznego czasu do pierwszego kontaktu nie powiodl sie",
		)


def _powiadom_realtime(lead: str) -> None:
	"""Po udanym `frappe.db.set_value` - sygnal realtime jak przy `doc.save()`
	(patrz docstring modulu). Zadnych wartosci pol w payloadzie, wylacznie
	identyfikacja dokumentu: front dociaga dane sam, przez API z uprawnieniami
	wywolujacego (handlowiec D2D, ktory nie widzi pola permlevel 3, dostanie z
	API ten sam dokument bez tego pola - zdarzenie samo w sobie nic nie
	ujawnia)."""
	modified = frappe.db.get_value("CRM Lead", lead, "modified")

	# Jak `Document.notify_update()`: pokoj konkretnego dokumentu (front tego
	# akurat nie subskrybuje, ale to dokladnie ten sam sygnal co przy zwyklym
	# zapisie, wiec wysylamy oba, gdyby inny klient Frappe na niego czekal).
	frappe.publish_realtime(
		"doc_update",
		{"doctype": "CRM Lead", "name": lead, "modified": modified},
		doctype="CRM Lead",
		docname=lead,
		after_commit=True,
	)
	# Pokoj doctype'u (`doctype_subscribe`) - tego nasluchuje
	# `createDocumentResource`/`createListResource` z `frappe-ui`
	# (`realtime: true`), zeby odswiezyc otwarty dokument/wiersz listy.
	frappe.publish_realtime(
		"list_update",
		{"doctype": "CRM Lead", "name": lead},
		doctype="CRM Lead",
		after_commit=True,
	)
