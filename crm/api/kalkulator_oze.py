# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Whitelisted API kalkulatora OZE dla czterech nowych rodzajów instalacji (Rozbudowa PV/ME,
Klimatyzacja, Pompa ciepła, Kocioł; b68, issue ops#228) -- wzorzec `crm/api/czyste_powietrze.py`:
przeglądarka dostaje wyłącznie dane potrzebne do wyrenderowania formularza, cena jest zawsze
liczona od nowa na serwerze przez `crm.volteo_kalkulator_oze.oblicz_oferte`, a blok
`wynik["wewnetrzne"]` (koszt/marża/zysk) trafia wyłącznie do administratorów.

Trzy whitelisted funkcje, w kolejności kontraktu (plan "Wielki update kalkulatora OZE", sekcja 5):
`volteo_oze_pozycje` (katalog, bez cen/kosztów), `volteo_oze_calc` (wycena, `wewnetrzne` tylko dla
admina), `volteo_oze_create_deal` (jedyna ścieżka zapisu -- tworzy wyłącznie `CRM Deal`, tak jak
`volteo_cp_create_deal`: żadnego `Volteo Oferta`/PDF-a/innego rekordu).
"""

import json
from decimal import Decimal
from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.utils import cint, flt

from crm.api import volteo_ma_linie
from crm.api.limit_zadan import rate_limit
from crm.koszty.rdzen import zbuduj_snapshot_oze
from crm.volteo_aktywnosc import tekst_sladu, zapisz_slad
from crm.volteo_kalkulator_oze import (
	KLIMATYZACJA,
	KOCIOL,
	POMPA_CIEPLA,
	RODZAJE_NOWE,
	ROZBUDOWA,
	ZAPOTRZEBOWANIE,
	OZEBlad,
	cennik_z_wierszy,
	dobor_z_wierszy,
	oblicz_oferte,
	stale_z_singla,
	zloz_adres_montazu,
)

KALKULATOR_ROLE = {"Volteo D2D Sales", "Volteo Backend", "Volteo Core Admin", "System Manager"}
ADMIN_ROLE = {"Volteo Core Admin", "System Manager"}

# Pola pozycji katalogu zwracane do przeglądarki (`volteo_oze_pozycje`) -- celowo BEZ "aktywny"
# (filtrowane na poziomie zapytania, patrz `_RODZAJE_KATALOGU` niżej) i BEZ "skladowe"
# (kontrakt: "Bez składowych, bez kwot" -- `_POZYCJE_POLA_KALKULATORA` niżej jest osobną listą,
# dla silnika liczącego, gdzie "aktywny" JEST wymagane, bo `cennik_z_wierzy`/`_pozycja_wymagana`
# muszą wiedzieć, czy wybrana pozycja jest nadal sprzedawana).
_POZYCJE_POLA = [
	"kod",
	"nazwa",
	"rodzaj",
	"grupa",
	"producent",
	"model",
	"kolor",
	"moc_kw",
	"ilosc",
	"parametr",
	"opis",
	"sort",
]
# Zduplikowane z `crm.volteo_kalkulator_oze._POLA_POZYCJI_WYMAGANE` (ten moduł jest frappe-free i
# celowo nie eksportuje swoich stałych prywatnych) -- zmiana pól wymaganych przez `cennik_z_wierzy`
# wymaga zmiany TAKŻE tutaj, tak jak PROG_PPOZ_KW jest zduplikowane w trzech miejscach.
_POZYCJE_POLA_KALKULATORA = [*_POZYCJE_POLA, "aktywny"]

_SKLADOWE_POLA = ["parent", "klucz", "nazwa", "typ", "kwota", "wspolna"]

_DOBOR_POLA = ["producent", "typ", "ogrzewanie", "od_kw", "do_kw", "moc_kw"]
_DOBOR_POLA_KALKULATORA = [*_DOBOR_POLA, "aktywny"]

# Wartości pola Select `rodzaj` na `Volteo Cennik Pozycja` (`ops/crm-cennik-oze.py`) -- UWAGA:
# to NIE jest to samo słownictwo co `RODZAJE_NOWE` w `crm.volteo_kalkulator_oze` ("Rozbudowa"
# tutaj, "Rozbudowa PV/ME" tam): katalog cennikowy grupuje pozycje luźniej niż rodzaj instalacji
# na szansie. "Dodatek OZE" jest CELOWO pominięty -- te pozycje (dodatki do zestawów PV/PV+ME/ME)
# należą do silnika PV (`ops/crm-kalkulator-bom.py`), nie do tego modułu.
_RODZAJE_KATALOGU = ("Rozbudowa", "Klimatyzacja", "Pompa ciepła", "Kocioł", "Dodatek grzewczy")

_KLIMA_RODZAJ_LABEL = {
	"klima_chlodzenie": "Chłodzenie",
	"klima_dogrzewanie": "Chłodzenie + dogrzewanie",
	"klima_grzanie": "Chłodzenie + grzanie",
}
"""Etykieta czytelna dla człowieka dla pola `custom_oze_klima_rodzaj`, wyprowadzona z `grupa`
wybranej pozycji katalogowej klimatyzacji (`volteo_oze_pozycje` już zwraca `grupa`, ale
`wejscie["klimatyzacja"]` niesie wyłącznie `kod`, więc odczyt pozycji jest konieczny przy
tworzeniu szansy, patrz `_pola_rodzaju`)."""

_KOCIOL_RODZAJ_LABEL = {
	"kociol_pellet": "Pellet",
	"kociol_duo": "Drewno (DUO)",
}
"""Analogicznie do `_KLIMA_RODZAJ_LABEL`, dla pola `custom_oze_kociol_rodzaj`."""

_CWU_LABEL = {"": "", "200": "200 l", "300": "300 l"}
"""`wejscie["pompa"]["cwu"]`/`wejscie["kociol"]["cwu"]` niosą surowy kod ("", "200", "300",
zwalidowany już przez rdzeń), `custom_oze_cwu` (kontrakt) ma format "200 l"/"300 l"/""."""


def _etykieta_zapotrzebowania(kod: str) -> str:
	"""`"ponizej_4"` -> `"poniżej 4 kW"`; każda inna wartość (`"4.5"`, `"5"`, ..., `"14"`) ->
	`"<kod z przecinkiem zamiast kropki> kW"` (np. `"4,5 kW"`, `"5 kW"`)."""
	if kod == "ponizej_4":
		return "poniżej 4 kW"
	return f"{kod.replace('.', ',')} kW"


def _narzut_max_lub_brak(stale_dokument: dict[str, Any]) -> float | None:
	"""Odczyt informacyjny dla formularza (w odróżnieniu od `stale_z_singla`, który tu byłby
	zbyt surowy -- `volteo_oze_pozycje` nie powinien wywalać się błędem integralności tylko
	dlatego, że np. `vat_biznes` nie jest jeszcze wymagane na tym ekranie). Ten sam wariant
	0/None/"" = "brak limitu" co `crm.volteo_kalkulator_oze._narzut_max`, bez podnoszenia
	`OZEBladMapowania` dla brakującego klucza."""
	wartosc = stale_dokument.get("narzut_max")
	if wartosc in (None, ""):
		return None
	narzut = flt(wartosc)
	return None if narzut == 0 else narzut


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo OZE: błąd kalkulatora")
	frappe.throw(_("Wystąpił błąd podczas obliczania oferty."))


def _sprawdz_dostep() -> None:
	"""Bramka wspólna dla wszystkich trzech endpointów: rola kalkulatora ORAZ flaga linii
	produktowej OZE (`custom_linia_oze` -- `volteo_ma_linie` już obsługuje bypass dla
	System Manager/Volteo Core Admin/Volteo Backend, patrz `crm/api/__init__.py`)."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)
	if not volteo_ma_linie("OZE"):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)


@frappe.whitelist()
def volteo_oze_pozycje() -> dict[str, Any]:
	"""Zwraca bezpieczne dane katalogu (pozycje bez składowych/kwot, dobór mocy pompy ciepła,
	listę wartości zapotrzebowania budynku na moc) do wyrenderowania formularza."""
	_sprawdz_dostep()

	pozycje_wiersze = frappe.get_all(
		"Volteo Cennik Pozycja",
		filters={"aktywny": 1, "rodzaj": ["in", _RODZAJE_KATALOGU]},
		fields=_POZYCJE_POLA,
		order_by="sort asc, kod asc",
		ignore_permissions=True,
	)
	dobor_wiersze = frappe.get_all(
		"Volteo Dobor Mocy PC",
		filters={"aktywny": 1},
		fields=_DOBOR_POLA,
		order_by="producent asc, typ asc, ogrzewanie asc, od_kw asc",
		ignore_permissions=True,
	)
	zapotrzebowanie = [{"value": kod, "label": _etykieta_zapotrzebowania(kod)} for kod in ZAPOTRZEBOWANIE]
	stale_dokument = frappe.db.get_singles_dict("Volteo Kalkulator Stale")

	return {
		"pozycje": pozycje_wiersze,
		"dobor": dobor_wiersze,
		"zapotrzebowanie": zapotrzebowanie,
		"narzut_max": _narzut_max_lub_brak(stale_dokument),
		"ppoz": flt(stale_dokument.get("ppoz") or 0),
		"panel_moc_wp": flt(stale_dokument.get("panel_moc_wp") or 0),
	}


def _wynik_kalkulatora(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Pobiera cennik/dobór mocy/stałe i liczy ofertę przez wspólny rdzeń frappe-free
	(`crm.volteo_kalkulator_oze.oblicz_oferte`). Wspólna ścieżka dla `volteo_oze_calc` i
	`volteo_oze_create_deal`, żeby oba wywołania liczyły identycznie -- analogicznie do
	`_wynik_kalkulatora` w `crm/api/czyste_powietrze.py`. W odróżnieniu od
	`volteo_oze_pozycje` powyżej, `stale_z_singla` jest tu pełnym walidatorem (rzuca
	`OZEBladMapowania`, gdy brakuje którejkolwiek wymaganej stałej) -- silnik cenowy nie może
	po cichu doliczyć VAT 0% albo pominąć PPOŻ tylko dlatego, że ktoś zapomniał ustawić stałą.

	Pobiera WSZYSTKIE wiersze `Volteo Cennik Pozycja` (bez filtra `rodzaj`/`aktywny` -- `aktywny`
	jest sprawdzane PO stronie rdzenia, dla wybranej pozycji, nie tutaj), tak jak
	`crm.api.czyste_powietrze._wynik_kalkulatora` robi dla `Volteo CP Pozycja`: pozycje spoza
	czterech nowych rodzajów ("Dodatek OZE") trafiają do `cennik`, ale `pozycje_dla` nigdy ich
	nie wybiera, więc są nieszkodliwym nadmiarem.
	"""
	pozycje_wiersze = frappe.get_all(
		"Volteo Cennik Pozycja", fields=_POZYCJE_POLA_KALKULATORA, ignore_permissions=True
	)
	skladowe_wiersze = frappe.get_all(
		"Volteo Cennik Skladowa",
		filters={"parenttype": "Volteo Cennik Pozycja"},
		fields=_SKLADOWE_POLA,
		ignore_permissions=True,
	)
	dobor_wiersze = frappe.get_all(
		"Volteo Dobor Mocy PC", fields=_DOBOR_POLA_KALKULATORA, ignore_permissions=True
	)
	stale_dokument = frappe.db.get_singles_dict("Volteo Kalkulator Stale")

	cennik = cennik_z_wierszy(pozycje_wiersze, skladowe_wiersze)
	dobor = dobor_z_wierszy(dobor_wiersze)
	stale = stale_z_singla(stale_dokument)
	return oblicz_oferte(wejscie, cennik, dobor, stale)


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_oze_calc(wejscie: dict[str, Any]) -> dict[str, Any]:
	"""Oblicza ofertę dla jednego z czterech nowych rodzajów instalacji OZE i usuwa
	`wynik["wewnetrzne"]` dla użytkowników niebędących administratorami -- identyczny wzorzec
	co `volteo_cp_calc`."""
	_sprawdz_dostep()

	try:
		wynik = _wynik_kalkulatora(wejscie)
	except OZEBlad as blad:
		# Obejmuje też `OZEBladMapowania` (błąd integralności katalogu/stałych) -- kontrakt B5
		# żąda czytelnego `frappe.throw` dla KAŻDEGO `OZEBlad`, nie tylko błędów formularza
		# klienta; `OZEBrakDoboru` niesie dosłownie "Brak doboru" w treści, wymagane przez sondę.
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()

	if not ADMIN_ROLE & set(frappe.get_roles(frappe.session.user)):
		wynik.pop("wewnetrzne", None)
	return wynik


def _imie_nazwisko_kontaktu(kontakt: str) -> str:
	"""Pobiera imię i nazwisko z kontaktu; rzuca czytelny błąd, gdy kontakt nie istnieje albo
	nie ma imienia/nazwiska. Kopia `crm.api.czyste_powietrze._imie_nazwisko_kontaktu` -- moduł
	frappe-free-adjacent, ale ten jeden helper jest na tyle mały, że duplikacja jest tańsza niż
	sprzężenie dwóch modułów API."""
	if not frappe.has_permission("Contact", ptype="read", doc=kontakt):
		frappe.throw(_("Brak dostępu do wybranego kontaktu."), frappe.PermissionError)
	dane = frappe.db.get_value("Contact", kontakt, ["first_name", "last_name"], as_dict=True)
	if not dane:
		frappe.throw(_("Wybrany kontakt nie istnieje."))
	imie_nazwisko = " ".join(filter(None, [dane.first_name, dane.last_name])).strip()
	if not imie_nazwisko:
		frappe.throw(_("Wybrany kontakt nie ma podanego imienia i nazwiska."))
	return imie_nazwisko


def _adres_montazu_z_kontaktu(kontakt: str) -> dict[str, str]:
	"""Pola adresowe szansy dziedziczone z kontaktu, jak w kalkulatorze PV (tam składa je
	przeglądarka, `KalkulatorTab.vue`). Wywoływane PO `_imie_nazwisko_kontaktu`, które sprawdza
	prawo odczytu kontaktu. Kontakt bez adresu daje puste pola, bez wyjątku. Województwo
	celowo NIE jest ustawiane: lista województw istnieje wyłącznie we froncie (`VOIVODESHIPS`),
	a backend nie ma własnego źródła prawdy."""
	dane = frappe.db.get_value(
		"Contact",
		kontakt,
		["custom_ulica", "custom_nr_domu", "custom_nr_mieszkania", "custom_miasto", "custom_kod_pocztowy"],
		as_dict=True,
	)
	if not dane:
		return {"custom_install_address": "", "custom_install_city": "", "custom_install_postal_code": ""}
	return {
		"custom_install_address": zloz_adres_montazu(
			dane.get("custom_ulica"), dane.get("custom_nr_domu"), dane.get("custom_nr_mieszkania")
		),
		"custom_install_city": (dane.get("custom_miasto") or "").strip(),
		"custom_install_postal_code": (dane.get("custom_kod_pocztowy") or "").strip(),
	}


def _pola_rodzaju(rodzaj: str, wejscie: dict[str, Any], wynik: dict[str, Any]) -> tuple[dict[str, Any], str]:
	"""Buduje pola `custom_oze_*` specyficzne dla `rodzaj` (kontrakt, tabela pól `CRM Deal`) i
	zwraca je razem z "kodem głównym" pozycji (`custom_oze_kod_glowny`) -- pusty string dla
	Rozbudowy, bo ta nie ma JEDNEJ głównej pozycji katalogowej (może nieść panele + baterię
	naraz), w odróżnieniu od Klimatyzacji/Pompy ciepła/Kotła, gdzie wybór jest zawsze dokładnie
	jedną pozycją.

	Dla Klimatyzacji/Kotła odczytuje dodatkowo pozycję katalogową (`frappe.db.get_value`) --
	`wejscie` niesie tylko `kod` dla tych dwóch rodzajów, a pola szansy (model/moc/rodzaj
	czytelny dla człowieka) wymagają metadanych katalogowych, których `wynik` nie niesie.
	Dla Pompy ciepła producent/typ/ogrzewanie są czytane WPROST z `wejscie` (surowe, już
	zwalidowane przez rdzeń) zamiast ponownie odpytywać katalog -- `wynik["pompa"]` niesie
	tylko `moc_kw`/`kod`, nie producenta/typu.
	"""
	if rodzaj == ROZBUDOWA:
		rozbudowa = wejscie.get("rozbudowa") or {}
		istniejaca_moc = Decimal(str(rozbudowa.get("istniejaca_pv_moc_kwp") or 0))
		return (
			{
				"custom_oze_rozbudowa_panele": cint(rozbudowa.get("panele") or 0),
				"custom_oze_rozbudowa_panele_mikro": cint(rozbudowa.get("panele_mikro") or 0),
				"custom_oze_rozbudowa_bateria": cint(rozbudowa.get("bateria") or 0),
				# custom_istniejaca_pv/custom_istniejaca_pv_moc_kwp/custom_ppoz: pola reużyte z
				# kalkulatora PV (ops/crm-kalkulator-bom.py), ten sam format "Tak"/"Nie".
				# `wejscie["rozbudowa"]` nie niesie osobnej flagi "istniejaca_pv" Tak/Nie (w
				# odróżnieniu od formularza PV) -- wyprowadzona tu z mocy > 0, spójnie z tym, jak
				# PV zeruje moc, gdy flaga jest "Nie" (`istniejaca_pv_moc_kwp = 0.0`).
				"custom_istniejaca_pv": "Tak" if istniejaca_moc > 0 else "Nie",
				"custom_istniejaca_pv_moc_kwp": float(istniejaca_moc),
				"custom_ppoz": "Tak" if wynik["ppoz"] else "Nie",
			},
			"",
		)

	if rodzaj == KLIMATYZACJA:
		kod = (wejscie.get("klimatyzacja") or {}).get("kod")
		pozycja = (
			frappe.db.get_value(
				"Volteo Cennik Pozycja", kod, ["grupa", "producent", "model", "moc_kw"], as_dict=True
			)
			or {}
		)
		return (
			{
				"custom_oze_klima_rodzaj": _KLIMA_RODZAJ_LABEL.get(pozycja.get("grupa"), pozycja.get("grupa") or ""),
				"custom_oze_klima_model": " ".join(filter(None, [pozycja.get("producent"), pozycja.get("model")])),
				"custom_oze_klima_moc_kw": flt(pozycja.get("moc_kw") or 0, 1),
			},
			kod or "",
		)

	if rodzaj == POMPA_CIEPLA:
		pompa = wejscie.get("pompa") or {}
		grzejniki = pompa.get("grzejniki") or {}
		grzejniki_szt = 0
		for ilosc in grzejniki.values():
			ilosc_int = cint(ilosc)
			if ilosc_int > 0:
				grzejniki_szt += ilosc_int
		pompa_info = wynik.get("pompa") or {}
		return (
			{
				"custom_oze_pc_zapotrzebowanie": pompa.get("zapotrzebowanie") or "",
				"custom_oze_pc_producent": pompa.get("producent") or "",
				"custom_oze_pc_typ": pompa.get("typ") or "",
				"custom_oze_pc_ogrzewanie": pompa.get("ogrzewanie") or "",
				"custom_oze_pc_moc_kw": flt(pompa_info.get("moc_kw") or 0, 1),
				"custom_oze_cwu": _CWU_LABEL.get(pompa.get("cwu") or "", ""),
				"custom_oze_grzejniki_szt": grzejniki_szt,
				"custom_oze_grzejniki_json": json.dumps(grzejniki, ensure_ascii=False),
			},
			pompa_info.get("kod") or "",
		)

	if rodzaj == KOCIOL:
		kociol = wejscie.get("kociol") or {}
		kod = kociol.get("kod")
		pozycja = (
			frappe.db.get_value(
				"Volteo Cennik Pozycja", kod, ["grupa", "producent", "model", "moc_kw"], as_dict=True
			)
			or {}
		)
		return (
			{
				"custom_oze_kociol_rodzaj": _KOCIOL_RODZAJ_LABEL.get(pozycja.get("grupa"), pozycja.get("grupa") or ""),
				"custom_oze_kociol_model": " ".join(filter(None, [pozycja.get("producent"), pozycja.get("model")])),
				"custom_oze_kociol_moc_kw": flt(pozycja.get("moc_kw") or 0, 1),
				"custom_oze_cwu": _CWU_LABEL.get(kociol.get("cwu") or "", ""),
			},
			kod or "",
		)

	# Nieosiągalne: `rodzaj` jest już zwalidowane przeciw RODZAJE_NOWE przez wywołującego, zanim
	# ta funkcja zostanie wywołana -- patrz `volteo_oze_create_deal`.
	return {}, ""


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_oze_create_deal(wejscie: dict[str, Any], contact: str) -> dict[str, Any]:
	"""Przelicza ofertę jednego z czterech nowych rodzajów instalacji OZE na serwerze i zapisuje
	WYŁĄCZNIE `CRM Deal` -- kwoty klienta nigdy nie są przyjmowane z przeglądarki, wycena jest
	zawsze liczona od nowa przez ten sam rdzeń, którego używa `volteo_oze_calc`. Jedyna ścieżka
	zapisu dla tych czterech rodzajów (żadnego `Volteo Oferta`/PDF-a/innego rekordu -- identyczna
	konwencja co `volteo_cp_create_deal`)."""
	_sprawdz_dostep()

	kontakt = (contact or "").strip()
	if not kontakt:
		frappe.throw(_("Wybierz kontakt, aby utworzyć szansę."))

	rodzaj = wejscie.get("rodzaj") if isinstance(wejscie, dict) else None
	if rodzaj not in RODZAJE_NOWE:
		frappe.throw(_("Nieznany rodzaj instalacji."))

	try:
		wynik = _wynik_kalkulatora(wejscie)
	except OZEBlad as blad:
		frappe.throw(_(str(blad)))
	except Exception:
		_blad_ogolny()

	imie_nazwisko = _imie_nazwisko_kontaktu(kontakt)
	pola_adresu = _adres_montazu_z_kontaktu(kontakt)

	# Pierwszy etap procesu wg pozycji -- identyczny wzorzec co `volteo_cp_create_deal` i
	# `ops/crm-kalkulator-bom.py`: nowe rodzaje idą dokładnie etapami OZE (decyzja CEO), więc
	# nie ma potrzeby odczytywać `crm.volteo_pipeline` osobno -- "Lead"/pierwszy etap jest
	# pierwszym `CRM Deal Status` po `position` niezależnie od rodzaju umowy.
	deal_status_wiersze = frappe.get_all(
		"CRM Deal Status", fields=["name"], order_by="position asc", limit_page_length=1
	)
	deal_status = deal_status_wiersze[0]["name"] if deal_status_wiersze else None
	if not deal_status:
		frappe.log_error(title="Volteo OZE: brak statusu szansy")
		frappe.throw(_("Nie można utworzyć szansy: brak skonfigurowanego statusu szansy."))

	pola_rodzaju, kod_glowny = _pola_rodzaju(rodzaj, wejscie, wynik)

	try:
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"status": deal_status,
				"lead_name": imie_nazwisko,
				"deal_value": wynik["brutto"],
				# custom_rodzaj_umowy steruje autonamingiem (crm/volteo_naming.py, autoname() na
				# CRMDeal) -- nazwa szansy (np. "PRO/PC/26/0123") jest wyliczana automatycznie,
				# ten endpoint nie zarządza nią wprost.
				"custom_rodzaj_umowy": rodzaj,
				"custom_product_interest": rodzaj,
				"custom_typ_klienta": wynik["typ_klienta"],
				"custom_narzut": wynik["narzut"],
				"custom_netto": wynik["netto"],
				"custom_vat_pct": wynik["vat_rate"],
				"custom_dotacja": wynik["dotacja"],
				"custom_estimated_subsidy_pln": flt(wynik["dotacja"]),
				"custom_cena_po_dotacji": wynik["cena_po_dotacji"],
				"custom_ulga_pct": str(wejscie.get("ulga_pct", 0)),
				"custom_ulga_kwota": wynik["ulga"],
				"custom_cena_po_uldze": wynik["cena_po_uldze"],
				"custom_okres_lat": wejscie.get("okres_lat", 10),
				"custom_wplata_wlasna": flt(wejscie.get("wplata_wlasna", 0)),
				"custom_rata_brutto": wynik["raty"]["brutto"],
				"custom_rata_po_dotacji": wynik["raty"]["po_dotacji"],
				"custom_rata_po_uldze": wynik["raty"]["po_uldze"],
				"custom_oze_kod_glowny": kod_glowny,
				# Zapis dosłowny wejścia kalkulatora -- NIE jest źródłem prawdy dla wyceny (zawsze
				# liczonej od nowa po stronie serwera), tylko gwarancją odtworzenia formularza.
				"custom_oze_wejscie_json": json.dumps(wejscie, ensure_ascii=False),
				**pola_adresu,
				**pola_rodzaju,
			}
		)
		# custom_zestaw bez kwot per linia (decyzja CEO) -- wynik["linie"] już niesie dokładnie
		# {kod, typ, nazwa, ilosc, jednostka}, cztery pierwsze pola idą wprost do wiersza BOM.
		for linia in wynik["linie"]:
			deal.append(
				"custom_zestaw",
				{
					"typ": linia["typ"],
					"nazwa": linia["nazwa"],
					"ilosc": linia["ilosc"],
					"jednostka": linia["jednostka"],
				},
			)
		deal.insert()
		deal.append("contacts", {"contact": kontakt, "is_primary": 1})
		deal.save()
		deal.db_set("deal_owner", frappe.session.user)

		# Snapshot kosztów/marży (permlevel 2, custom_koszty_json/custom_koszty_zysk_plan) --
		# db_set() pomija brak prawa zapisu D2D na permlevel 2, identycznie jak
		# volteo_cp_create_deal. Zapisywany BEZWARUNKOWO: pochodzi z przeliczenia serwerowego
		# (wynik["wewnetrzne"]), nigdy od klienta, więc bramka "tylko admin widzi wewnetrzne" w
		# volteo_oze_calc tego nie dotyczy.
		snapshot = zbuduj_snapshot_oze(wynik["wewnetrzne"], frappe.utils.now())
		deal.db_set("custom_koszty_json", json.dumps(snapshot, ensure_ascii=False))
		deal.db_set("custom_koszty_zysk_plan", flt(snapshot["podsumowanie"]["zysk_plan"], 2))

		try:
			zapisz_slad(
				deal.name,
				tekst_sladu("kalkulator_oze_nowy", rodzaj_instalacji=rodzaj, pozycje=len(wynik["linie"])),
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Volteo OZE: błąd zapisu śladu aktywności")
	except Exception:
		_blad_ogolny()

	return {"deal": deal.name}
