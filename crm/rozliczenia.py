# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Adapter Frappe dla rozliczeń prowizji (ops#280): hooki doctype'u `Volteo Rozliczenie`,
synchronizacja pól zbiorczych szansy i ręczne naliczanie odbiorców.

Cała logika decyzyjna siedzi w frappe-free `crm/volteo_rozliczenie.py`; tu jest wyłącznie
dostęp do bazy. Widoczność (tylko `System Manager` i `Volteo Core Admin`) egzekwuje
DocPerm doctype'u i bramka `ADMIN_ROLE` w `crm/api/rozliczenia.py`; hooki tutaj pracują
celowo bez sprawdzania uprawnień, bo biegną jako skutek zapisu wiersza.
"""

import frappe
from frappe.utils import get_fullname

from crm.volteo_rozliczenie import (
	STATUS_DO_WYPLATY,
	STATUS_WYPLACONE,
	data_podpisania,
	kwoty_odbiorcow,
	pola_szansy,
	waliduj_kwote,
	waliduj_unikalnosc,
	waliduj_wyplate,
	warunek_naliczenia,
)

DOCTYPE = "Volteo Rozliczenie"
POLE_KONTROLNE = "custom_rozliczenie_status"
POLA_WIERSZA = [
	"name",
	"deal",
	"rola",
	"odbiorca",
	"odbiorca_nazwa",
	"kwota",
	"status",
	"data_wyplaty",
	"oznaczyl",
	"oznaczono",
	"uwaga",
	"zrodlo_kwoty",
	"partia",
	"data_podpisania",
]
POLA_CP = (
	"custom_cp_prowizja_handlowa",
	"custom_cp_nadprowizja_manager",
	"custom_cp_nadprowizja_partner",
)


def wiersze_szansy(deal: str, pomin: str | None = None) -> list[dict]:
	"""Wiersze rozliczenia szansy. `get_all` celowo ignoruje uprawnienia (to ścieżka hooków).
	`pomin` to nazwa wiersza do wykluczenia (np. właśnie usuwany)."""
	filtry = {"deal": deal}
	if pomin:
		filtry["name"] = ("!=", pomin)
	return frappe.get_all(DOCTYPE, filters=filtry, fields=POLA_WIERSZA, order_by="creation asc")


def synchronizuj_szanse(deal: str, pomin: str | None = None) -> None:
	"""Przelicza sześć pól `custom_rozliczenie_*` szansy z jej wierszy. Idempotentna.
	`db.set_value` bez `save()`: bez walidacji i bez zmiany `modified`."""
	if not deal or not frappe.get_meta("CRM Deal").has_field(POLE_KONTROLNE):
		return
	if not frappe.db.exists("CRM Deal", deal):
		return
	pola = pola_szansy(wiersze_szansy(deal, pomin))
	frappe.db.set_value(
		"CRM Deal",
		deal,
		{f"custom_rozliczenie_{klucz}": wartosc for klucz, wartosc in pola.items()},
		update_modified=False,
	)


def po_zmianie_wiersza(doc, method: str | None = None) -> None:
	"""Hook `after_insert`, `on_update` i `on_trash` na `Volteo Rozliczenie`."""
	pomin = doc.name if method == "on_trash" else None
	synchronizuj_szanse(doc.deal, pomin)


def waliduj_wiersz(doc, method: str | None = None) -> None:
	"""Hook `validate` na `Volteo Rozliczenie`: unikalność (deal, rola), kwota, data wypłaty,
	oraz pola `oznaczyl`/`oznaczono` (ustawiane przy przejściu na Wypłacone, czyszczone przy
	cofnięciu)."""
	inne = [w for w in wiersze_szansy(doc.deal) if w["name"] != doc.name]
	komunikat = (
		waliduj_unikalnosc(inne, {"rola": doc.rola, "name": doc.name})
		or waliduj_kwote(doc.kwota if doc.kwota is not None else 0)
		or waliduj_wyplate(doc.status, doc.data_wyplaty)
	)
	if komunikat:
		frappe.throw(komunikat)

	if doc.status == STATUS_WYPLACONE:
		if not doc.oznaczyl:
			doc.oznaczyl = frappe.session.user
		if not doc.oznaczono:
			doc.oznaczono = frappe.utils.now_datetime()
	elif doc.oznaczyl or doc.oznaczono:
		doc.oznaczyl = None
		doc.oznaczono = None


def _manager_szansy(deal_owner: str | None) -> str | None:
	"""Manager = `user` węzła `reports_to` węzła `CRM Sales Hierarchy` handlowca; brak węzła
	lub przełożonego to `None`."""
	if not deal_owner:
		return None
	przelozony = frappe.db.get_value("CRM Sales Hierarchy", {"user": deal_owner}, "reports_to")
	if not przelozony:
		return None
	return frappe.db.get_value("CRM Sales Hierarchy", przelozony, "user") or None


def nalicz(deal: str, kto: str | None = None) -> list[str]:
	"""Tworzy brakujące wiersze rozliczenia szansy (idempotentnie: istniejąca rola jest
	pomijana). Zwraca nazwy nowych wierszy. Wołający odpowiada za bramkę ról."""
	doc = frappe.get_doc("CRM Deal", deal)
	rodzaj = doc.get("custom_rodzaj_umowy")
	manager = _manager_szansy(doc.deal_owner)
	kwoty = kwoty_odbiorcow(
		rodzaj,
		doc.get("custom_koszty_json"),
		{pole: doc.get(pole) for pole in POLA_CP},
		doc.deal_owner,
		manager,
	)
	istniejace = {w["rola"] for w in wiersze_szansy(deal)}
	podpisanie = data_podpisania(
		[{"to": w.to, "to_date": w.to_date} for w in (doc.get("status_change_log") or [])]
	)
	nowe: list[str] = []
	for rola, dane in kwoty.items():
		if rola in istniejace:
			continue
		wiersz = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"deal": deal,
				"rola": rola,
				"odbiorca": dane["odbiorca"],
				"odbiorca_nazwa": get_fullname(dane["odbiorca"]) if dane["odbiorca"] else None,
				"kwota": dane["kwota"] if dane["kwota"] is not None else 0,
				"status": STATUS_DO_WYPLATY,
				"zrodlo_kwoty": dane["zrodlo"],
				"data_podpisania": podpisanie,
			}
		)
		wiersz.insert(ignore_permissions=True)
		nowe.append(wiersz.name)
	return nowe


def nalicz_jesli_spelnione(deal_doc) -> None:
	"""Punkt rozszerzenia automatycznego naliczania, wołany z `CRMDeal.validate()`. Dziś
	no-op, bo `warunek_naliczenia` zawsze zwraca False. Nigdy nie blokuje zapisu szansy."""
	try:
		dane = {
			"status": deal_doc.get("status"),
			"rodzaj": deal_doc.get("custom_rodzaj_umowy"),
			"deal": deal_doc.name,
		}
		if warunek_naliczenia(dane) and not deal_doc.is_new():
			nalicz(deal_doc.name)
	except Exception:
		frappe.log_error(title="Rozliczenia: automatyczne naliczanie nie powiodło się")
