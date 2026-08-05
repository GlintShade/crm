"""Whitelisted API formularza „Informacje do umowy” (doctype `Volteo Umowa`).

`Volteo Umowa` jest 1:1 z `CRM Deal` (`autoname: "field:deal"` — nazwa dokumentu
to nazwa szansy). Przeglądarka nigdy nie ustala kwoty kredytu ani wymogu zgody
przeciwpożarowej (PPOŻ) — obie wartości liczy wyłącznie serwer, przez wspólny,
bezstanowy rdzeń `crm.volteo_umowa`, i nadpisuje przy każdym zapisie niezależnie
od tego, co przyszło od klienta. Formularz jest wypełniany stopniowo przez
przedstawiciela, więc niekompletny zapis to poprawny stan roboczy (draft-save),
a nie błąd — brakujące pola są zwracane w wyniku, nigdy nie rzucamy wyjątku
z powodu samej niekompletności.
"""

from decimal import Decimal
from typing import Any, NoReturn

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from crm.api.czyste_powietrze import KALKULATOR_ROLE
from crm.volteo_umowa import (
	brakujace_pola,
	kwota_kredytu,
	miejsce_i_pokrycie,
	ppoz_wymagane,
)

DOCTYPE = "Volteo Umowa"

_DEAL_POLA_PREFILL = [
	"name",
	"deal_value",
	"custom_netto",
	"custom_pv_power_kwp",
	"custom_panele",
	"custom_falownik",
	"custom_bateria",
	"custom_pojemnosc_kwh",
	"custom_konstrukcja",
	"custom_kabel_m",
	"custom_wplata_wlasna",
	"custom_install_address",
	"custom_install_city",
	"custom_install_postal_code",
	"custom_voivodeship",
	"custom_rodzaj_umowy",
]
"""Pola `CRM Deal` kopiowane bez zmian do bloku `prefill`."""

_KONTAKT_POLA = [
	"first_name",
	"last_name",
	"custom_pesel",
	"custom_ulica",
	"custom_nr_domu",
	"custom_nr_mieszkania",
	"custom_kod_pocztowy",
	"custom_miasto",
	"custom_wojewodztwo",
]
"""Pola podstawowego `Contact` szansy kopiowane do `prefill`; adres domowy kontaktu."""

_PREFILL_MAPOWANIE: dict[str, str] = {
	"custom_ulica": "adres_zam_ulica",
	"custom_nr_domu": "adres_zam_nr_domu",
	"custom_nr_mieszkania": "adres_zam_nr_mieszkania",
	"custom_kod_pocztowy": "adres_zam_kod",
	"custom_miasto": "adres_zam_miasto",
	"custom_install_address": "adres_montaz_ulica",
	"custom_install_postal_code": "adres_montaz_kod",
	"custom_install_city": "adres_montaz_miasto",
	"custom_kabel_m": "dodatkowy_kabel_m",
	"custom_wplata_wlasna": "wklad_wlasny_pln",
}
"""Mapowanie pole źródłowe (Deal/Contact) → pole `Volteo Umowa`, dopisywane do `prefill`.

Frontend hydratuje formularz kluczami `Volteo Umowa` (`form[fn] = valueOr(record[fn],
prefill[fn])`), nie surowymi nazwami pól CRM Deal/Contact — bez tego mapowania prefill
jest cichym no-opem: każdy lookup zwraca `undefined`, nic nie się wywala, pole po prostu
zostaje puste. Surowe klucze źródłowe (`_DEAL_POLA_PREFILL`, `_KONTAKT_POLA`) zostają
w `prefill` OBOK wpisów zmapowanych — przydatne do wyświetlania i późniejszego kroku PDF.

Celowo BEZ mapowania: `adres_montaz_nr_domu` i `adres_montaz_nr_mieszkania`. Deal
przechowuje adres montażu jako jedno pole tekstowe (`custom_install_address`) bez
wydzielonego numeru domu/mieszkania — NIE wyciągać ich regexem z tego stringa. Te dwa
pola formularza zostają puste, do ręcznego wypełnienia przez przedstawiciela.
"""

_DANE_POLA_DOZWOLONE = [
	"adres_zam_jak_montaz",
	"typ_budynku",
	"powierzchnia_prog",
	"powierzchnia_m2",
	"finansowanie",
	"wklad_wlasny_pln",
	"internet",
	"instalacja_odgromowa",
	"moc_przylaczeniowa_kw",
	"liczba_faz",
	"osd",
	"przekop_gruntowy",
	"istniejaca_pv",
	"istniejaca_pv_moc_inwertera_kw",
	"istniejaca_pv_moc_kwp",
	"istniejaca_pv_producent_inwertera",
	"adres_zam_ulica",
	"adres_zam_nr_domu",
	"adres_zam_nr_mieszkania",
	"adres_zam_kod",
	"adres_zam_miasto",
	"adres_montaz_ulica",
	"adres_montaz_nr_domu",
	"adres_montaz_nr_mieszkania",
	"adres_montaz_kod",
	"adres_montaz_miasto",
	"dodatkowy_kabel_m",
	"zgoda_kontakt_telefoniczny",
	"zgoda_dzialania_promocyjne",
]
"""Jedyne pola `Volteo Umowa`, jakie `volteo_umowa_save` przyjmuje od klienta.

Nigdy nie robimy ślepego ``doc.update(dane)`` z danych przesłanych przez przeglądarkę —
wszystko spoza tej listy jest po cichu odrzucane. `kwota_kredytu_pln` i `ppoz_wymagane`
celowo NIE są tu wymienione: są liczone wyłącznie na serwerze (patrz `_wyliczenia`).
`adres_montaz_nr_mieszkania` jest tu celowo, mimo że instalacja zwykle dotyczy domu
jednorodzinnego: `typ_budynku` dopuszcza „Wielorodzinny” (§1.2 umowy — „Mieszkaniu w
budynku wielorodzinnym”), więc adres montażu czasem wymaga numeru mieszkania.
`zgoda_kontakt_telefoniczny` i `zgoda_dzialania_promocyjne` to zgody RODO/marketingowe
z Załącznika 2 — mają wagę prawną, patrz `_POLA_CHECKBOX` dla ich koercji.
"""

_POLA_KWOTOWE = frozenset({"wklad_wlasny_pln"})
"""Pola kwotowe wymagające konwersji przez `Decimal` zamiast surowego przypisania."""

_POLA_CHECKBOX = frozenset({"zgoda_kontakt_telefoniczny", "zgoda_dzialania_promocyjne"})
"""Pola Check (0/1 Int) wymagające jawnej koercji przez `cint`, nigdy `bool()`.

Pułapka: `bool("0")` daje `True` w Pythonie, więc string ``"0"`` przepuszczony bez
koercji zapisałby się jako zgoda udzielona, mimo że przedstawiciel jej nie zaznaczył.
`cint` poprawnie sprowadza do 0/1 zarówno booleany JSON (`True`/`False`), jak i stringi
liczbowe (``"0"``/``"1"``); nieparsowalne wejście pada na bezpieczne domyślne 0.
"""

_UMOWA_POLA_WYJSCIOWE = [*_DANE_POLA_DOZWOLONE, "kwota_kredytu_pln", "ppoz_wymagane"]
"""Pola `Volteo Umowa` zwracane w bloku `umowa` odpowiedzi — dane formularza plus
serwerowo przeliczone `kwota_kredytu_pln`/`ppoz_wymagane`, których wartości są
zawsze te ostatnio zapisane (świeże przeliczenie na żądanie jest w `wyliczenia`)."""


def _sprawdz_role() -> None:
	"""Sprawdza rolę uprawnioną do korzystania z formularza — ten sam gate co kalkulator."""
	role_uzytkownika = set(frappe.get_roles(frappe.session.user))
	if not KALKULATOR_ROLE & role_uzytkownika:
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)


def _sprawdz_dostep_do_szansy(deal: str, tryb: str) -> None:
	"""Sprawdza istnienie szansy i uprawnienie `read`/`write` wywołującego do niej."""
	if not deal or not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Szansa sprzedaży nie istnieje."), frappe.DoesNotExistError)
	if not frappe.has_permission("CRM Deal", tryb, deal):
		frappe.throw(_("Brak uprawnień do tej szansy sprzedaży."), frappe.PermissionError)


def _blad_ogolny() -> NoReturn:
	frappe.log_error(frappe.get_traceback(), "Volteo Umowa: błąd formularza")
	frappe.throw(_("Wystąpił błąd podczas zapisu formularza umowy."))


def _pobierz_umowe(deal: str) -> "frappe.model.document.Document | None":
	"""Zwraca dokument `Volteo Umowa` dla szansy, jeśli istnieje — inaczej `None`.

	Nazwa dokumentu jest tożsama z nazwą szansy (`autoname: field:deal`), więc
	sprawdzenie istnienia i pobranie odbywa się po tym samym kluczu.
	"""
	if frappe.db.exists(DOCTYPE, deal):
		return frappe.get_doc(DOCTYPE, deal)
	return None


def _podstawowy_kontakt(deal_doc: "frappe.model.document.Document") -> str | None:
	"""Zwraca nazwę podstawowego kontaktu (`is_primary`) szansy albo `None`, gdy go brak."""
	for wiersz in deal_doc.contacts:
		if wiersz.is_primary:
			return wiersz.contact
	return None


def _dane_kontaktu(kontakt: str | None) -> dict[str, Any]:
	"""Dane podstawowego kontaktu do `prefill`; puste stringi, gdy kontakt nie istnieje.

	Świadomie nigdy nie rzuca — brak podstawowego kontaktu na szansie jest normalnym,
	niekompletnym stanem, a nie błędem formularza.
	"""
	puste = {pole: "" for pole in _KONTAKT_POLA} | {"email": "", "mobile_no": ""}
	if not kontakt:
		return puste

	dane = frappe.db.get_value("Contact", kontakt, _KONTAKT_POLA, as_dict=True)
	if not dane:
		return puste

	wynik = {pole: dane.get(pole) or "" for pole in _KONTAKT_POLA}
	wynik["email"] = (
		frappe.db.get_value("Contact Email", {"parent": kontakt, "is_primary": 1}, "email_id") or ""
	)
	wynik["mobile_no"] = (
		frappe.db.get_value("Contact Phone", {"parent": kontakt, "is_primary_mobile_no": 1}, "phone") or ""
	)
	return wynik


def _prefill(deal_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Składa blok `prefill`: surowe pola szansy/kontaktu PLUS wpisy zmapowane na
	fieldnames `Volteo Umowa` (`_PREFILL_MAPOWANIE`), których frontend faktycznie
	szuka podczas hydratacji formularza. Brakujące/`None` źródło daje pusty string,
	nigdy `None` — żeby `None` nie wyciekło do pola tekstowego w formularzu.
	"""
	dane = {pole: deal_doc.get(pole) for pole in _DEAL_POLA_PREFILL}
	kontakt = _podstawowy_kontakt(deal_doc)
	dane.update(_dane_kontaktu(kontakt))
	for zrodlo, cel in _PREFILL_MAPOWANIE.items():
		# Jawne None-check, NIE `or ""`: `wklad_wlasny_pln` to kwota, gdzie 0 jest
		# poprawną wartością (brak wkładu własnego) i `0 or ""` zgubiłoby to zero.
		wartosc = dane.get(zrodlo)
		dane[cel] = wartosc if wartosc is not None else ""
	return dane


def _wyliczenia(
	deal_doc: "frappe.model.document.Document",
	umowa_doc: "frappe.model.document.Document | None",
) -> dict[str, Any]:
	"""Wartości liczone na żądanie: miejsce montażu, pokrycie dachowe, wymóg PPOŻ,
	kwota kredytu i lista brakujących pól. Zawsze przeliczane od nowa z bieżącego
	stanu szansy i umowy — nigdy nie ufamy wcześniej zapisanym wartościom.
	"""
	miejsce, pokrycie = miejsce_i_pokrycie(deal_doc.get("custom_konstrukcja"))
	moc_istniejaca = umowa_doc.get("istniejaca_pv_moc_kwp") if umowa_doc else None
	wklad = umowa_doc.get("wklad_wlasny_pln") if umowa_doc else None
	dane_do_walidacji = {pole: umowa_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE} if umowa_doc else {}

	return {
		"miejsce_montazu": miejsce,
		"pokrycie_dachowe": pokrycie,
		"ppoz_wymagane": ppoz_wymagane(deal_doc.get("custom_pv_power_kwp"), moc_istniejaca),
		"kwota_kredytu_pln": kwota_kredytu(deal_doc.get("deal_value"), wklad),
		"brakujace_pola": brakujace_pola(dane_do_walidacji),
	}


def _umowa_do_dict(umowa_doc: "frappe.model.document.Document") -> dict[str, Any]:
	"""Spłaszcza dokument `Volteo Umowa` do bloku `umowa` odpowiedzi."""
	wynik = {pole: umowa_doc.get(pole) for pole in _UMOWA_POLA_WYJSCIOWE}
	wynik["name"] = umowa_doc.name
	wynik["deal"] = umowa_doc.deal
	wynik["status"] = umowa_doc.status
	return wynik


def _decimal_lub_none(wartosc: Any) -> Decimal | None:
	"""Konwertuje kwotę na `Decimal` przez `str()` (nigdy `Decimal(float)`); puste wejście → `None`."""
	if wartosc is None or wartosc == "":
		return None
	try:
		return Decimal(str(wartosc))
	except (ArithmeticError, ValueError, TypeError):
		frappe.throw(_("Nieprawidłowa wartość kwoty."))


def _propaguj_zgody(
	deal_doc: "frappe.model.document.Document",
	umowa_doc: "frappe.model.document.Document",
) -> None:
	"""Kopiuje zgody `zgoda_kontakt_telefoniczny`/`zgoda_dzialania_promocyjne` z `Volteo
	Umowa` na podstawowy `Contact` szansy, żeby dało się filtrować/budować listę
	kontaktów po zgodach — `Volteo Umowa` jest 1:1 z umową, więc bez tej kopii nie ma
	na czym takiej listy zbudować. Najnowsza deklaracja nadpisuje poprzednią: nawet
	gdy przedstawiciel odznaczy obie zgody, nadpisujemy nimi `Contact` — historyczny
	fakt, że zgoda kiedyś była udzielona, zostaje zachowany na tym konkretnym
	rekordzie `Volteo Umowa` i nie jest tu retroaktywnie zmieniany. Data i źródło
	zgody są stemplowane WYŁĄCZNIE gdy przynajmniej jedna zgoda jest udzielona.
	"""
	try:
		kontakt = _podstawowy_kontakt(deal_doc)
		if not kontakt:
			return

		telefon = umowa_doc.get("zgoda_kontakt_telefoniczny")
		marketing = umowa_doc.get("zgoda_dzialania_promocyjne")

		aktualizacja: dict[str, Any] = {
			"custom_zgoda_telefon": telefon,
			"custom_zgoda_marketing": marketing,
		}
		if telefon or marketing:
			aktualizacja["custom_zgoda_data"] = frappe.utils.nowdate()
			aktualizacja["custom_zgoda_zrodlo"] = umowa_doc.name

		# `Contact.custom_pesel` jest polem wymaganym (reqd=1), a wiele istniejących
		# kontaktów powstało przed jego dodaniem i ma je puste — `.save()` na takim
		# kontakcie wywaliłoby walidację pola wymaganego i zepsuło zapis CAŁEGO
		# formularza umowy z powodu zupełnie niepowiązanego efektu ubocznego.
		# `db.set_value` omija walidację dokumentu, więc jest tu bezpieczne.
		frappe.db.set_value("Contact", kontakt, aktualizacja, update_modified=False)
	except Exception:
		# Utrata wypełnionego formularza umowy przez błąd w efekcie ubocznym (kopii
		# zgód na Contact) byłaby gorszym skutkiem niż samo zalogowanie i pominięcie
		# propagacji — zapis umowy musi się powieść niezależnie od jej wyniku.
		frappe.log_error(frappe.get_traceback(), "Volteo Umowa: propagacja zgód do Contact")


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_umowa_get(deal: str) -> dict[str, Any]:
	"""Zwraca istniejący rekord `Volteo Umowa` (jeśli jest), dane `prefill` i `wyliczenia`."""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "read")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)

	return {
		"umowa": _umowa_do_dict(umowa_doc) if umowa_doc else None,
		"prefill": _prefill(deal_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def volteo_umowa_create(deal: str) -> dict[str, Any]:
	"""Tworzy `Volteo Umowa` dla szansy. Idempotentne: jeśli rekord już istnieje
	(np. podwójne kliknięcie „Wygeneruj umowę”), zwraca istniejący zamiast rzucać
	`DuplicateEntryError` — nazwa dokumentu jest nazwą szansy, więc naiwny `insert()`
	wybuchłby przy powtórnym wywołaniu.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)

	if umowa_doc is None:
		try:
			umowa_doc = frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"deal": deal,
					"status": "Roboczy",
					"dodatkowy_kabel_m": deal_doc.get("custom_kabel_m"),
					"wklad_wlasny_pln": deal_doc.get("custom_wplata_wlasna"),
				}
			)
			umowa_doc.insert()
		except frappe.DuplicateEntryError:
			# Wyścig: inna sesja/kliknięcie zdążyło wstawić rekord między sprawdzeniem a insertem.
			umowa_doc = frappe.get_doc(DOCTYPE, deal)
		except Exception:
			_blad_ogolny()

	return {
		"umowa": _umowa_do_dict(umowa_doc),
		"prefill": _prefill(deal_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def volteo_umowa_save(deal: str, dane: dict[str, Any]) -> dict[str, Any]:
	"""Zapisuje formularz umowy z allowlistą pól i serwerowym przeliczeniem.

	Niekompletny zapis jest poprawnym stanem roboczym (przedstawiciel wypełnia
	formularz stopniowo) — brakujące wymagane pola NIE blokują zapisu, tylko
	ustawiają `status="Roboczy"` i trafiają do `wyliczenia.brakujace_pola`, żeby
	UI mógł je podświetlić. Dopiero komplet danych daje `status="Kompletny"`.
	`kwota_kredytu_pln` i `ppoz_wymagane` przesłane przez klienta są ignorowane —
	liczy je wyłącznie serwer.
	"""
	_sprawdz_role()
	_sprawdz_dostep_do_szansy(deal, "write")

	if not isinstance(dane, dict):
		frappe.throw(_("Nieprawidłowy format danych formularza."))

	deal_doc = frappe.get_doc("CRM Deal", deal)
	umowa_doc = _pobierz_umowe(deal)
	if umowa_doc is None:
		frappe.throw(_("Najpierw wygeneruj umowę dla tej szansy sprzedaży."))

	for pole in _DANE_POLA_DOZWOLONE:
		if pole not in dane:
			continue
		wartosc = dane[pole]
		if pole in _POLA_KWOTOWE:
			wartosc = _decimal_lub_none(wartosc)
		elif pole in _POLA_CHECKBOX:
			# Jawna koercja przez cint — NIGDY bool(), bo bool("0") == True w Pythonie.
			wartosc = cint(wartosc)
		umowa_doc.set(pole, wartosc)

	braki = brakujace_pola({pole: umowa_doc.get(pole) for pole in _DANE_POLA_DOZWOLONE})
	umowa_doc.status = "Roboczy" if braki else "Kompletny"

	# Kwota kredytu i wymóg PPOŻ liczone są WYŁĄCZNIE na serwerze i nadpisują cokolwiek
	# przesłał klient — klient nie może ustawić kwoty kredytu ani ominąć wymogu PPOŻ.
	umowa_doc.kwota_kredytu_pln = kwota_kredytu(deal_doc.get("deal_value"), umowa_doc.get("wklad_wlasny_pln"))
	umowa_doc.ppoz_wymagane = ppoz_wymagane(
		deal_doc.get("custom_pv_power_kwp"), umowa_doc.get("istniejaca_pv_moc_kwp")
	)

	try:
		umowa_doc.save()
	except Exception:
		_blad_ogolny()

	_propaguj_zgody(deal_doc, umowa_doc)

	return {
		"umowa": _umowa_do_dict(umowa_doc),
		"prefill": _prefill(deal_doc),
		"wyliczenia": _wyliczenia(deal_doc, umowa_doc),
	}
