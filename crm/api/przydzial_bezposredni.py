# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Przydział leada z webhooka wg reguł obszaru (ops#347): adapter bez `whitelist`.

Wołane z `crm.api.leady_webhook.przyjmij` jako konto integracji (rola `Volteo
Integracja`, bez DocPerm na leadach), więc wszystkie odczyty idą przez `get_all` i
`db.get_value`, a zapisy z `ignore_permissions=True` robi wołający.

Przydział wybieramy PRZED insertem leada: `CRMLead.after_insert` dla leada z
`lead_owner` (różnym od konta integracji) sam robi `share_with_agent` (DocShare) i
`assign_agent` (ToDo), czyli jeden zapis daje właściciela, przypisanie i udostępnienie.
Dlatego `przydziel_wg_reguly` nie zapisuje nic, tylko zwraca pola do wstawienia i dane
do śladu. Ślad w Aktywności zapisuje `zapisz_slad_przydzialu` już po insercie.

Funkcje nie rzucają przy braku schematu: bez pola `custom_przydzial_bezposredni`,
bez doctype reguł albo bez aktywnej reguły wynik to `None` (zachowanie jak dotąd).
Tożsamość osoby CC nie wchodzi do wyniku ani do śladu.
"""

from typing import Any

import frappe

from crm.api.reguly_przydzialu import dozwoleni_handlowcy, wczytaj_reguly
from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_reguly_przydzialu import (
	POLE_ZNACZNIKA,
	dopasuj_regule,
	ma_wspolrzedne,
	tekst_sladu_przydzialu,
)


def przydziel_wg_reguly(dane: dict[str, Any]) -> dict[str, Any] | None:
	"""Dopasowuje regułę do danych nowego leada (słownik pól z `custom_lat`/`custom_lng`).

	Zwraca `{"pola": {"lead_owner", "custom_przydzial_bezposredni"}, "handlowiec",
	"srodek_nazwa", "promien_km", "odleglosc_km"}` albo `None` (brak pola schematu,
	brak współrzędnych, brak reguł, brak dopasowania). Niczego nie zapisuje.
	"""
	if not frappe.get_meta("CRM Lead").has_field(POLE_ZNACZNIKA):
		return None
	lat, lng = dane.get("custom_lat"), dane.get("custom_lng")
	if not ma_wspolrzedne(lat, lng):
		return None
	reguly = wczytaj_reguly()
	if not any(r.aktywna for r in reguly):
		return None
	dopasowanie = dopasuj_regule(lat, lng, reguly, dozwoleni_handlowcy())
	if dopasowanie is None:
		return None
	regula = dopasowanie.regula
	return {
		"pola": {"lead_owner": regula.handlowiec, POLE_ZNACZNIKA: 1},
		"handlowiec": regula.handlowiec,
		"srodek_nazwa": regula.srodek_nazwa,
		"promien_km": regula.promien_km,
		"odleglosc_km": dopasowanie.odleglosc_km,
	}


def zapisz_slad_przydzialu(lead: str, przydzial: dict[str, Any]) -> None:
	"""Ślad "Lead przydzielony bezpośrednio" w Aktywności leada (widoczny też dla handlowca)."""
	nazwa = frappe.db.get_value("User", przydzial["handlowiec"], "full_name") or przydzial["handlowiec"]
	zapisz_slad(
		lead,
		tekst_sladu_przydzialu(
			nazwa, przydzial["srodek_nazwa"], przydzial["promien_km"], przydzial["odleglosc_km"]
		),
		doctype="CRM Lead",
	)
