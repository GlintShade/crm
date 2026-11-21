# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""API kategorii handlowców (ops#393): cienki adapter nad `crm.volteo_kategorie`.

Pola leżą na `User` z permlevel 2, więc odczyt idzie przez `frappe.get_all` (omija
uprawnienia), a bramką są role sprawdzane tutaj. Handlowiec nie widzi niczego.
"""

import frappe
from frappe import _

from crm.api.volteo_leady import _aktywni_d2d_reprezentanci
from crm.volteo_kategorie import (
	ROLE_ZAPISU,
	Teren,
	moze_widziec,
	moze_zapisac,
	teren_z_wiersza,
	waliduj_teren,
)

POLA_TERENU = [
	"name",
	"full_name",
	"custom_kategoria_handlowca",
	"custom_teren_nazwa",
	"custom_teren_lat",
	"custom_teren_lng",
	"custom_teren_promien_km",
	"custom_okreg_kampanii",
]


def _wiersze_handlowcow() -> list[dict]:
	nazwy = [h["name"] for h in _aktywni_d2d_reprezentanci()]
	if not nazwy:
		return []
	return frappe.get_all(
		"User", filters={"name": ["in", nazwy]}, fields=POLA_TERENU, order_by="full_name asc"
	)


def wczytaj_tereny() -> list[Teren]:
	"""Tereny aktywnych handlowców D2D, którzy mają kategorię (wewnętrzna, bez bramki ról)."""
	return [t for t in map(teren_z_wiersza, _wiersze_handlowcow()) if t is not None]


@frappe.whitelist()
def lista() -> list[dict]:
	"""Każdy aktywny handlowiec D2D z sześcioma polami ustawień. Tylko `ROLE_ZAPISU`."""
	frappe.only_for(list(ROLE_ZAPISU))
	return [
		{
			"user": w["name"],
			"full_name": w["full_name"],
			"kategoria": w["custom_kategoria_handlowca"] or "",
			"teren_nazwa": w["custom_teren_nazwa"] or "",
			"teren_lat": w["custom_teren_lat"] or 0,
			"teren_lng": w["custom_teren_lng"] or 0,
			"promien_km": w["custom_teren_promien_km"] or 0,
			"okreg": w["custom_okreg_kampanii"] or "",
		}
		for w in _wiersze_handlowcow()
	]


@frappe.whitelist()
def zapisz(
	uzytkownik: str,
	kategoria: str = "",
	teren_nazwa: str = "",
	teren_lat: float = 0,
	teren_lng: float = 0,
	promien_km: int = 0,
	okreg: str = "",
) -> dict:
	"""Zapisuje kategorię, teren i okręg handlowca. Tylko `ROLE_ZAPISU`."""
	if not moze_zapisac(frappe.get_roles()):
		frappe.throw(_("Brak uprawnień do zmiany kategorii handlowców."), frappe.PermissionError)
	if uzytkownik not in {h["name"] for h in _aktywni_d2d_reprezentanci()}:
		frappe.throw(_("Konto {0} nie jest aktywnym handlowcem.").format(uzytkownik))
	dane = {
		"kategoria": kategoria,
		"teren_lat": teren_lat,
		"teren_lng": teren_lng,
		"promien_km": promien_km,
		"okreg": okreg,
	}
	bledy = waliduj_teren(dane)
	if bledy:
		frappe.throw("<br>".join(_(b) for b in bledy))
	wartosci = {
		"custom_kategoria_handlowca": (kategoria or "").strip(),
		"custom_teren_nazwa": (teren_nazwa or "").strip(),
		"custom_teren_lat": teren_lat or 0,
		"custom_teren_lng": teren_lng or 0,
		"custom_teren_promien_km": promien_km or 0,
		"custom_okreg_kampanii": (okreg or "").strip(),
	}
	# Forma słownika: set_value z jedną wartością fałszywą zapisuje pusty napis.
	frappe.db.set_value("User", uzytkownik, wartosci, update_modified=False)
	return {"user": uzytkownik, **wartosci}


@frappe.whitelist()
def tereny() -> dict:
	"""Tereny handlowców z kategorią. Dla innych niż `ROLE_KATEGORII` pusty wynik (nie 403)."""
	if not moze_widziec(frappe.get_roles()):
		return {"widoczne": False, "tereny": []}
	return {
		"widoczne": True,
		"tereny": [
			{
				"user": t.handlowiec,
				"full_name": t.nazwa_handlowca,
				"kategoria": t.kategoria,
				"lat": t.lat,
				"lng": t.lng,
				"promien_km": t.promien_km,
				"okreg": t.okreg,
				"teren_nazwa": nazwa,
			}
			for t, nazwa in _tereny_z_nazwa()
		],
	}


def _tereny_z_nazwa() -> list[tuple[Teren, str]]:
	wynik = []
	for w in _wiersze_handlowcow():
		t = teren_z_wiersza(w)
		if t is not None:
			wynik.append((t, w["custom_teren_nazwa"] or ""))
	return wynik
