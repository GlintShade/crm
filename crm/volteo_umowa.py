# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Logika formularza umowy instalacyjnej (miejsce montażu, próg PPOŻ, kredyt, wymagane pola).

Moduł celowo nie importuje ``frappe`` — to jedyny sposób, żeby dało się go
przetestować lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, więc
reszta backendu ma wyłącznie bramkę składniową, zob. `crm/volteo_naming.py`).
Cała logika zależna od frameworka (zapis do dokumentu, whitelisted API) mieszka
gdzie indziej — tu tylko czyste funkcje.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

KONSTRUKCJA_MONTAZ: dict[str, tuple[str, str | None]] = {
	"Dach skośny - blacha": ("Dach", "Blacha"),
	"Dach skośny - dachówka": ("Dach", "Dachówka"),
	"Dach płaski - inwazyjnie": ("Dach", "Płaski"),
	"Dach płaski - balast": ("Dach", "Płaski"),
	"Konstrukcja gruntowa": ("Grunt", None),
}
"""Mapowanie wartości pola `custom_konstrukcja` kalkulatora na (miejsce montażu, pokrycie dachowe)."""

PROG_PPOZ_KW: Decimal = Decimal("6.5")
"""Próg mocy [kW], powyżej którego wymagana jest zgoda przeciwpożarowa (PPOŻ)."""

_ZERO = Decimal("0")
"""Wartość zastępcza dla brakującej/pustej mocy w `ppoz_wymagane` i `kwota_kredytu`."""

_KWOTA_KWANT = Decimal("0.01")
"""Precyzja kwotowa (grosze) dla `kwota_kredytu`."""

_ZAWSZE_WYMAGANE: tuple[str, ...] = (
	"adres_zam_jak_montaz",
	"typ_budynku",
	"powierzchnia_prog",
	"finansowanie",
	"internet",
	"instalacja_odgromowa",
	"moc_przylaczeniowa_kw",
	"liczba_faz",
	"osd",
	"przekop_gruntowy",
	"istniejaca_pv",
)
"""Pola wymagane niezależnie od pozostałych odpowiedzi w formularzu."""

_WYMAGANE_INNY_ADRES: tuple[str, ...] = (
	"adres_zam_ulica",
	"adres_zam_nr_domu",
	"adres_zam_kod",
	"adres_zam_miasto",
	"adres_montaz_ulica",
	"adres_montaz_nr_domu",
	"adres_montaz_kod",
	"adres_montaz_miasto",
)
"""Wymagane, gdy `adres_zam_jak_montaz == "Nie"`. Numer mieszkania celowo pominięty — jest opcjonalny."""

_WYMAGANE_DUZA_POWIERZCHNIA: tuple[str, ...] = ("powierzchnia_m2",)
"""Wymagane, gdy `powierzchnia_prog == "powyżej 300 m²"`."""

_WYMAGANE_KREDYT_GOTOWKA: tuple[str, ...] = ("wklad_wlasny_pln",)
"""Wymagane, gdy `finansowanie == "Kredyt + gotówka"`."""

_WYMAGANE_ISTNIEJACA_PV: tuple[str, ...] = (
	"istniejaca_pv_moc_inwertera_kw",
	"istniejaca_pv_moc_kwp",
	"istniejaca_pv_producent_inwertera",
)
"""Wymagane, gdy `istniejaca_pv == "Tak"`."""

# Pułapka tego formularza: dla większości pól `0` to poprawna, wypełniona wartość
# (np. brak własnego wkładu jest legalny), ale dla pól mocy/powierzchni `0` oznacza
# w praktyce "nie podano" — instalacja o mocy 0 kW albo budynek o powierzchni 0 m²
# nie istnieje, więc traktujemy to tak samo jak pole puste.
_ZERO_OZNACZA_PUSTE: frozenset[str] = frozenset(
	{
		"moc_przylaczeniowa_kw",
		"istniejaca_pv_moc_inwertera_kw",
		"istniejaca_pv_moc_kwp",
		"powierzchnia_m2",
	}
)


def miejsce_i_pokrycie(konstrukcja: str | None) -> tuple[str | None, str | None]:
	"""Mapuje `custom_konstrukcja` na (miejsce montażu, pokrycie dachowe).

	Dopasowanie jest dokładne (bez fuzzy-matchingu), ale toleruje białe znaki na
	brzegach. Nieznana, pusta albo brakująca wartość zwraca `(None, None)`.
	"""
	if not konstrukcja:
		return None, None
	return KONSTRUKCJA_MONTAZ.get(konstrukcja.strip(), (None, None))


def ppoz_wymagane(moc_nowa_kw: Any, moc_istniejaca_kw: Any) -> bool:
	"""Czy wymagana jest zgoda PPOŻ.

	Zgodnie z umową próg dotyczy SUMY mocy nowej instalacji i ewentualnej
	instalacji istniejącej (przypadek rozbudowy) — pojedyncza instalacja może
	być poniżej progu, a suma już go przekracza. Próg jest wyłączny: dokładnie
	6,5 kW nie wymaga zgody, wymaga dopiero wartość ściśle większa.
	"""
	suma = _decimal_lub_zero(moc_nowa_kw) + _decimal_lub_zero(moc_istniejaca_kw)
	return suma > PROG_PPOZ_KW


def kwota_kredytu(brutto: Any, wklad_wlasny: Any) -> Decimal:
	"""Kwota do sfinansowania kredytem: `brutto - wklad_wlasny`, nigdy poniżej zera."""
	roznica = _decimal_lub_zero(brutto) - _decimal_lub_zero(wklad_wlasny)
	if roznica < _ZERO:
		roznica = _ZERO
	return roznica.quantize(_KWOTA_KWANT, rounding=ROUND_HALF_UP)


def brakujace_pola(dane: dict[str, Any]) -> list[str]:
	"""Zwraca listę nazw pól wymaganych a pustych, w stałej (deklaracyjnej) kolejności.

	Nie mutuje `dane`. Kolejność jest istotna — testy i komunikat błędu dla
	użytkownika zależą od determinizmu, dlatego zwracana jest lista, nie zbiór.
	"""
	wymagane = list(_ZAWSZE_WYMAGANE)

	if dane.get("adres_zam_jak_montaz") == "Nie":
		wymagane.extend(_WYMAGANE_INNY_ADRES)

	if dane.get("powierzchnia_prog") == "powyżej 300 m²":
		wymagane.extend(_WYMAGANE_DUZA_POWIERZCHNIA)

	if dane.get("finansowanie") == "Kredyt + gotówka":
		wymagane.extend(_WYMAGANE_KREDYT_GOTOWKA)

	if dane.get("istniejaca_pv") == "Tak":
		wymagane.extend(_WYMAGANE_ISTNIEJACA_PV)

	return [pole for pole in wymagane if _jest_puste(dane.get(pole), pole)]


def _sparsuj_decimal(wartosc: Any) -> Decimal | None:
	"""Próbuje sparsować wartość (w tym string z formularza klienta) jako `Decimal`.

	Konwertuje przez `str()` (nigdy `Decimal(float)`). Zwraca `None`, gdy wartość
	jest `None`, samymi białymi znakami, albo w ogóle nie da się jej odczytać jako
	liczby (np. tekst wpisany ręcznie) — nigdy nie podnosi wyjątku.
	"""
	if wartosc is None:
		return None
	tekst = str(wartosc).strip()
	if tekst == "":
		return None
	try:
		return Decimal(tekst)
	except InvalidOperation:
		return None


def _decimal_lub_zero(wartosc: Any) -> Decimal:
	"""Konwertuje na `Decimal`; `None`/pusty/niepoprawny (np. spacja, zły tekst) traktuje jako zero.

	Frappe dostarcza wartości formularza jako stringi z klienta — ta funkcja musi
	nigdy nie podnosić wyjątku wewnątrz kalkulatora cenowego (`ppoz_wymagane`,
	`kwota_kredytu`), więc każdy niesparsowalny wejściowy tekst cicho staje się zerem.
	"""
	wynik = _sparsuj_decimal(wartosc)
	return _ZERO if wynik is None else wynik


def _jest_puste(wartosc: Any, pole: str) -> bool:
	"""Reguła pustości: `None`/`""`/same białe znaki są puste zawsze; `0`/`0.0` puste tylko dla pól z `_ZERO_OZNACZA_PUSTE`.

	Dla pól z `_ZERO_OZNACZA_PUSTE` liczby mogą przyjść jako `int`/`float`/`Decimal`
	(wywołania lokalne) albo jako string (JSON z klienta Frappe) — obie postacie są
	tu parsowane tym samym `_sparsuj_decimal`, więc reguła zera mieszka w jednym
	miejscu. String, którego nie da się odczytać jako liczby (np. "abc"), nigdy nie
	może być poprawną mocą/powierzchnią, więc też liczy się jako puste.
	"""
	if wartosc is None:
		return True
	if isinstance(wartosc, str) and wartosc.strip() == "":
		return True
	if pole in _ZERO_OZNACZA_PUSTE:
		wynik = _sparsuj_decimal(wartosc)
		return wynik is None or wynik == _ZERO
	return False
