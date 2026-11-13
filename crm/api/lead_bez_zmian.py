# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Alert "lead bez zmian przez X godzin" (ops#352): adapter Frappe.

Zadanie harmonogramu (co godzine miedzy 08:00 a 21:00, wpis w `crm/hooks.py`) szuka
leadow z webhooka Make, ktore maja wiek w oknie [X, X + 24 h], nie maja zadnej zmiany
zrobionej przez czlowieka i nie dostaly jeszcze alertu, po czym wysyla dzwonek
`CRM Notification` (typ `Assignment`, dokument `CRM Lead`: panel powiadomien otwiera
leada trasa `Lead`) odbiorcom reguly `lead_bez_zmian` z `Volteo Automatyzacja`.

Aktywnosc czlowieka to wiersze `Version`, `Comment` (typ Comment), `FCRM Note`, `CRM Task`
i `CRM Call Log` wskazujace na leada, ktorych wlascicielem jest konto inne niz
`Administrator`, `Guest` i konta z rola `Volteo Integracja`. Kazdy typ to jedno zapytanie
zbiorcze (`in` po nazwach kandydatow).

Logika decyzyjna zyje w `crm.volteo_lead_bez_zmian` (bez Frappe). Nigdy nie rzuca na zewnatrz;
tozsamosc osoby CC nie jest czytana ani zapisywana.
"""

import frappe
from frappe.utils import cint, now_datetime

from crm.volteo_lead_bez_zmian import (
	KLUCZ_REGULY,
	LIMIT_LEADOW_NA_PRZEBIEG,
	ROLA_INTEGRACJI,
	ZAKRES_Z_HANDLOWCEM,
	ZAKRES_Z_REGULY,
	czy_lead_w_zakresie,
	czy_w_oknie,
	czy_wyslac_alert,
	leady_z_aktywnoscia_czlowieka,
	normalizuj_prog,
	normalizuj_zakres,
	ogranicz_przebieg,
	okno_utworzenia,
	tresc_powiadomienia,
	zbierz_odbiorcow,
)
from crm.volteo_leady_kontakt import czy_lead_z_webhooka

DOCTYPE_REGULY = "Volteo Automatyzacja"
POLE_ZNACZNIKA = "custom_alert_bez_zmian"
POLE_PRZYDZIALU = "custom_przydzial_bezposredni"

# Typ dokumentu -> (pole doctype wskazujace na leada, pole z nazwa leada, dodatkowe filtry).
_ZRODLA_AKTYWNOSCI: tuple[tuple[str, str, str, dict], ...] = (
	("Version", "ref_doctype", "docname", {}),
	("Comment", "reference_doctype", "reference_name", {"comment_type": "Comment"}),
	("FCRM Note", "reference_doctype", "reference_docname", {}),
	("CRM Task", "reference_doctype", "reference_docname", {}),
	("CRM Call Log", "reference_doctype", "reference_docname", {}),
)


def sprawdz_leady_bez_zmian() -> None:
	"""Wejscie dla harmonogramu: dziala jako Administrator, commit na koncu, nigdy nie rzuca."""
	poprzedni = frappe.session.user
	try:
		frappe.set_user("Administrator")
		_przetworz()
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Volteo: alert leadow bez zmian nie powiodl sie")
	finally:
		try:
			frappe.set_user(poprzedni)
		except Exception:
			pass


def _regula() -> dict | None:
	"""Regula `lead_bez_zmian` albo None, gdy brak doctype, wiersza albo jest wylaczona."""
	if not frappe.db.table_exists(DOCTYPE_REGULY):
		return None
	meta = frappe.get_meta(DOCTYPE_REGULY)
	pola = ["wlaczona", "odbiorca_handlowiec", "kanal_bell"]
	pola += [p for p in ("prog_godzin", "zakres_leadow") if meta.has_field(p)]
	regula = frappe.db.get_value(DOCTYPE_REGULY, KLUCZ_REGULY, pola, as_dict=True)
	if not regula or not cint(regula.get("wlaczona")):
		return None
	return regula


def _konta_integracji(autorzy: set[str]) -> set[str]:
	"""Spomiedzy `autorzy` te konta, ktore maja role integracji (jedno zapytanie)."""
	if not autorzy:
		return set()
	return set(
		frappe.get_all(
			"Has Role",
			filters={"role": ROLA_INTEGRACJI, "parenttype": "User", "parent": ["in", list(autorzy)]},
			pluck="parent",
		)
	)


def _leady_z_aktywnoscia(nazwy: list[str]) -> set[str]:
	"""Nazwy leadow z `nazwy`, na ktorych jest zmiana albo notatka czlowieka (po jednym zapytaniu na typ)."""
	wiersze: list[tuple[str | None, str | None]] = []
	for doctype, pole_typu, pole_nazwy, dodatkowe in _ZRODLA_AKTYWNOSCI:
		filtry = {pole_typu: "CRM Lead", pole_nazwy: ["in", nazwy], **dodatkowe}
		for w in frappe.get_all(doctype, filters=filtry, fields=[f"{pole_nazwy} as lead", "owner"]):
			wiersze.append((w.lead, w.owner))
	konta = _konta_integracji({a for _, a in wiersze if a})
	return leady_z_aktywnoscia_czlowieka(wiersze, konta)


def _aktywni(uzytkownicy: set[str]) -> set[str]:
	if not uzytkownicy:
		return set()
	return set(
		frappe.get_all("User", filters={"name": ["in", list(uzytkownicy)], "enabled": 1}, pluck="name")
	)


def _dzwonek_lead(odbiorca: str, lead: str, tekst: str) -> bool:
	"""Dzwonek `CRM Notification` dla leada (wzor: `crm.api.pipeline._bell_notification`), z deduplikacja.
	Typ `Assignment` z `reference_doctype = CRM Lead`: `crm.api.notifications` zwraca trase `Lead`,
	wiec klikniecie w panelu powiadomien otwiera leada. Zwraca True, gdy utworzono nowy wiersz."""
	wartosci = frappe._dict(
		doctype="CRM Notification",
		from_user=frappe.session.user,
		to_user=odbiorca,
		type="Assignment",
		message=tekst,
		notification_text=tekst,
		notification_type_doctype="CRM Lead",
		notification_type_doc=lead,
		reference_doctype="CRM Lead",
		reference_name=lead,
	)
	if frappe.db.exists("CRM Notification", wartosci):
		return False
	frappe.get_doc(wartosci).insert(ignore_permissions=True)
	return True


def _kandydaci(teraz, prog: int, zakres: str) -> list[dict]:
	od, do = okno_utworzenia(teraz, prog)
	meta = frappe.get_meta("CRM Lead")
	ma_przydzial = meta.has_field(POLE_PRZYDZIALU)
	pola = [
		"name",
		"lead_name",
		"creation",
		"lead_owner",
		"source",
		"custom_import_source",
		"custom_install_postal_code",
	]
	if ma_przydzial:
		pola.append(POLE_PRZYDZIALU)
	filtry: dict = {"creation": ["between", [od, do]], POLE_ZNACZNIKA: ["is", "not set"]}
	if zakres == ZAKRES_Z_HANDLOWCEM:
		filtry["lead_owner"] = ["is", "set"]
	if zakres == ZAKRES_Z_REGULY:
		if not ma_przydzial:
			return []
		filtry[POLE_PRZYDZIALU] = 1
	wiersze = frappe.get_all(
		"CRM Lead",
		filters=filtry,
		or_filters=[["source", "=", "Facebook"], ["custom_import_source", "like", "%FB%"]],
		fields=pola,
		order_by="creation asc",
		limit_page_length=0,
	)
	wynik = []
	for w in wiersze:
		if not czy_w_oknie(w.creation, teraz, prog):
			continue
		if not czy_lead_z_webhooka(w.source, w.custom_import_source):
			continue
		if not czy_lead_w_zakresie(zakres, w.lead_owner, w.get(POLE_PRZYDZIALU), ma_przydzial):
			continue
		wynik.append(w)
	return wynik


def _przetworz(teraz=None) -> dict:
	"""Jeden przebieg zadania, BEZ commita (sondy robia rollback). Zwraca liczniki."""
	wynik = {"alerty": 0, "powiadomienia": 0, "pominiete_nadmiar": 0}
	regula = _regula()
	if not regula or not cint(regula.get("kanal_bell")):
		return wynik
	if not frappe.get_meta("CRM Lead").has_field(POLE_ZNACZNIKA):
		return wynik

	teraz = teraz or now_datetime()
	prog = normalizuj_prog(regula.get("prog_godzin"))
	zakres = normalizuj_zakres(regula.get("zakres_leadow"))
	handlowiec_wlaczony = cint(regula.get("odbiorca_handlowiec"))

	kandydaci = _kandydaci(teraz, prog, zakres)
	if not kandydaci:
		return wynik

	z_aktywnoscia = _leady_z_aktywnoscia([k.name for k in kandydaci])
	z_tabeli = frappe.get_all(
		"Volteo Automatyzacja Odbiorca",
		filters={"parent": KLUCZ_REGULY, "parenttype": DOCTYPE_REGULY},
		pluck="uzytkownik",
	)
	wlasciciele = {k.lead_owner for k in kandydaci if k.lead_owner} if handlowiec_wlaczony else set()
	aktywni = _aktywni({u for u in z_tabeli if u} | wlasciciele)

	do_wyslania = []
	for k in kandydaci:
		if not czy_wyslac_alert(True, True, True, k.name in z_aktywnoscia, None):
			continue
		odbiorcy = zbierz_odbiorcow(z_tabeli, k.lead_owner, handlowiec_wlaczony, aktywni)
		if odbiorcy:
			do_wyslania.append((k, odbiorcy))

	do_wyslania, nadmiar = ogranicz_przebieg(do_wyslania, LIMIT_LEADOW_NA_PRZEBIEG)
	if nadmiar:
		wynik["pominiete_nadmiar"] = nadmiar
		frappe.log_error(
			f"Alert leadow bez zmian: limit {LIMIT_LEADOW_NA_PRZEBIEG} na przebieg, "
			f"pominieto {nadmiar} leadow (wroca w kolejnym przebiegu, jesli nadal w oknie).",
			"Volteo: alert leadow bez zmian, limit przebiegu",
		)

	for k, odbiorcy in do_wyslania:
		try:
			handlowiec = (
				frappe.db.get_value("User", k.lead_owner, "full_name") or k.lead_owner
				if k.lead_owner
				else None
			)
			tekst = tresc_powiadomienia(prog, k.lead_name or k.name, k.custom_install_postal_code, handlowiec)
			for odbiorca in odbiorcy:
				if _dzwonek_lead(odbiorca, k.name, tekst):
					wynik["powiadomienia"] += 1
			frappe.db.set_value("CRM Lead", k.name, POLE_ZNACZNIKA, teraz, update_modified=False)
			wynik["alerty"] += 1
		except Exception:
			frappe.log_error(
				frappe.get_traceback(), f"Volteo: alert leada bez zmian {k.name} nie powiodl sie"
			)
	return wynik
