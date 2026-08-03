"""Whitelisted API kalkulatora z rozdzieleniem dostępu do kosztów wewnętrznych.

Przeglądarka otrzymuje z katalogu wyłącznie dane potrzebne do wyrenderowania formularza.
Obliczenia i dane kosztowe są pobierane na serwerze, a blok ``wewnetrzne`` trafia tylko
do administratorów. Mapowanie traktuje limit równy zero jako ``None`` — przekazanie zera
do rdzenia oznaczałoby limit dotacji równy zero, a nie brak limitu.
"""

from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from crm.czyste_powietrze.mapowanie import (
	katalog_z_wierszy,
	limity_z_wierszy,
	stale_z_dokumentu,
)
from crm.czyste_powietrze.obliczenia import (
	CPDaneNiekompletne,
	CPNiedozwolonaKombinacja,
	CPPozycjaNieaktywna,
	oblicz_oferte,
)

KALKULATOR_ROLE = {"Volteo D2D Sales", "Volteo Backend", "Volteo Core Admin", "System Manager"}
ADMIN_ROLE = {"Volteo Core Admin", "System Manager"}

_POZYCJE_POLA = ["kod", "nazwa", "kategoria", "jednostka", "aktywny"]
_POZYCJE_POLA_KALKULATORA = [
	"kod",
	"nazwa",
	"kategoria",
	"jednostka",
	"cena_netto",
	"dotacja_podstawowy",
	"dotacja_podwyzszony",
	"dotacja_najwyzszy",
	"limit_podstawowy",
	"limit_podwyzszony",
	"limit_najwyzszy",
	"prowizja",
	"koszt_proenergy",
	"koszt_staly",
	"aktywny",
]
_LIMITY_POLA = ["poziom", "standard", "status_limitu", "limit_laczny"]


def _czy_admin(roles: set[str]) -> bool:
	"""Sprawdza osobno prawo do oglądania kosztów i marży."""
	return bool(ADMIN_ROLE & roles)


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo CP: błąd kalkulatora")
	frappe.throw(_("Wystąpił błąd podczas obliczania oferty."))


@frappe.whitelist()
def volteo_cp_pozycje() -> dict[str, Any]:
	"""Zwraca bezpieczne dane katalogu do wyświetlenia w formularzu."""
	wiersze = frappe.get_all(
		"Volteo CP Pozycja",
		fields=_POZYCJE_POLA,
		ignore_permissions=True,
	)
	pozycje = [
		{
			"kod": wiersz["kod"],
			"nazwa": wiersz["nazwa"],
			"kategoria": wiersz["kategoria"],
			"jednostka": wiersz["jednostka"],
			"aktywny": bool(wiersz["aktywny"]),
		}
		for wiersz in wiersze
	]
	return {"pozycje": pozycje}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_cp_calc(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Oblicza ofertę i usuwa dane kosztowe dla użytkowników niebędących adminami."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	try:
		pozycje = frappe.get_all(
			"Volteo CP Pozycja",
			fields=_POZYCJE_POLA_KALKULATORA,
			ignore_permissions=True,
		)
		limity = frappe.get_all(
			"Volteo CP Limity",
			fields=_LIMITY_POLA,
			ignore_permissions=True,
		)
		stale = frappe.db.get_singles_dict("Volteo CP Stale")
		wynik = oblicz_oferte(
			wejscie,
			katalog_z_wierszy(pozycje),
			limity_z_wierszy(limity),
			stale_z_dokumentu(stale),
		)

		czy_moze_widziec_koszty = _czy_admin(role_uzytkownika)
		if not czy_moze_widziec_koszty:
			wynik.pop("wewnetrzne", None)
		return wynik
	except (CPNiedozwolonaKombinacja, CPPozycjaNieaktywna, CPDaneNiekompletne) as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()
