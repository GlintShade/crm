"""Whitelisted API kalkulatora z rozdzieleniem dostępu do kosztów wewnętrznych.

Przeglądarka otrzymuje z katalogu wyłącznie dane potrzebne do wyrenderowania formularza.
Obliczenia i dane kosztowe są pobierane na serwerze, a blok ``wewnetrzne`` trafia tylko
do administratorów. Mapowanie traktuje limit równy zero jako ``None`` — przekazanie zera
do rdzenia oznaczałoby limit dotacji równy zero, a nie brak limitu.
"""

from decimal import Decimal
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
	stale = frappe.db.get_singles_dict("Volteo CP Stale")
	# Udostępniamy wyłącznie heurystyki formularza, aby nie ujawnić prowizji ani innych stałych.
	# None oznacza brak automatycznego obliczania i umożliwia ręczne wprowadzenie.
	return {
		"pozycje": pozycje,
		"mnozniki": {
			"elewacja": stale.get("mnoznik_elewacja"),
			"strop": stale.get("mnoznik_strop"),
			"dach": stale.get("mnoznik_dach"),
			"okna": stale.get("mnoznik_okna"),
		},
		"m2_na_drzwi": stale.get("m2_na_drzwi"),
	}


def _wynik_kalkulatora(
	wejscie: dict[str, Any],
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
	"""Pobiera katalog/limity/stałe i liczy ofertę przez wspólny rdzeń.

	Wspólna ścieżka dla ``volteo_cp_calc`` i ``volteo_cp_create_deal``, żeby oba
	wywołania liczyły identycznie. Zwraca surowy wynik (z blokiem ``wewnetrzne``)
	oraz zmapowane limity termomodernizacji, aby wywołujący mógł sprawdzić status
	limitu bez ponownego odpytywania bazy.
	"""
	pozycje = frappe.get_all(
		"Volteo CP Pozycja",
		fields=_POZYCJE_POLA_KALKULATORA,
		ignore_permissions=True,
	)
	limity_wiersze = frappe.get_all(
		"Volteo CP Limity",
		fields=_LIMITY_POLA,
		ignore_permissions=True,
	)
	stale = frappe.db.get_singles_dict("Volteo CP Stale")
	limity = limity_z_wierszy(limity_wiersze)
	wynik = oblicz_oferte(
		wejscie,
		katalog_z_wierszy(pozycje),
		limity,
		stale_z_dokumentu(stale),
	)
	return wynik, limity


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_cp_calc(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Oblicza ofertę i usuwa dane kosztowe dla użytkowników niebędących adminami."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	try:
		wynik, _limity = _wynik_kalkulatora(wejscie)
		czy_moze_widziec_koszty = _czy_admin(role_uzytkownika)
		if not czy_moze_widziec_koszty:
			wynik.pop("wewnetrzne", None)
		return wynik
	except (CPNiedozwolonaKombinacja, CPPozycjaNieaktywna, CPDaneNiekompletne) as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()


def _imie_nazwisko_kontaktu(kontakt: str) -> str:
	"""Pobiera imię i nazwisko z kontaktu; rzuca czytelny błąd, gdy kontakt nie istnieje."""
	dane = frappe.db.get_value("Contact", kontakt, ["first_name", "last_name"], as_dict=True)
	if not dane:
		frappe.throw(_("Wybrany kontakt nie istnieje."))
	imie_nazwisko = " ".join(filter(None, [dane.first_name, dane.last_name])).strip()
	if not imie_nazwisko:
		frappe.throw(_("Wybrany kontakt nie ma podanego imienia i nazwiska."))
	return imie_nazwisko


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_cp_create_deal(wejscie: dict[str, Any], contact: str) -> dict[str, Any]:
	"""Przelicza ofertę Czyste Powietrze na serwerze i zapisuje wyłącznie ``CRM Deal``.

	Kwoty klienta nigdy nie są przyjmowane — wycena jest liczona od nowa przez ten
	sam rdzeń, którego używa ``volteo_cp_calc``. Nie tworzy ``Volteo CP Oferta``,
	PDF-a ani żadnego innego rekordu — to świadomie odroczone.
	"""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)

	kontakt = (contact or "").strip()
	if not kontakt:
		frappe.throw(_("Wybierz kontakt, aby utworzyć szansę."))

	try:
		wynik, limity = _wynik_kalkulatora(wejscie)
	except (CPNiedozwolonaKombinacja, CPPozycjaNieaktywna, CPDaneNiekompletne) as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()

	if not wynik.get("linie"):
		frappe.throw(
			_("Formularz kalkulatora jest pusty — wybierz źródło ciepła, dodatki lub prace termomodernizacyjne.")
		)

	poziom = wejscie.get("poziom")
	standard = wejscie.get("standard")
	limit_termo = limity.get((poziom, standard)) or {}
	if limit_termo.get("status") == "brak_dotacji" and wynik["dotacja_laczna"] == Decimal("0.00"):
		frappe.throw(
			_(
				"Wybrana konfiguracja nie kwalifikuje się do żadnej dotacji w programie "
				"Czyste Powietrze. Nie można utworzyć szansy bez dotacji."
			)
		)

	imie_nazwisko = _imie_nazwisko_kontaktu(kontakt)
	koszt_calkowity = sum((Decimal(str(linia["brutto"])) for linia in wynik["linie"]), Decimal("0.00"))

	deal_status_wiersze = frappe.get_all(
		"CRM Deal Status", fields=["name"], order_by="position asc", limit_page_length=1
	)
	deal_status = deal_status_wiersze[0]["name"] if deal_status_wiersze else None
	if not deal_status:
		frappe.log_error(title="Volteo CP: brak statusu szansy")
		frappe.throw(_("Nie można utworzyć szansy: brak skonfigurowanego statusu szansy."))

	try:
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"status": deal_status,
				"lead_name": imie_nazwisko,
				"deal_value": koszt_calkowity,
				"custom_rodzaj_umowy": "Czyste Powietrze",
				"custom_estimated_subsidy_pln": wynik["dotacja_laczna"],
			}
		)
		deal.insert()
		deal.append("contacts", {"contact": kontakt, "is_primary": 1})
		deal.save()
		deal.db_set("deal_owner", frappe.session.user)
	except Exception:
		_blad_ogolny()

	return {"deal": deal.name}
