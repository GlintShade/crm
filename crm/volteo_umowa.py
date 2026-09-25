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

from crm.integrations.autenti.logika import SEND_BLOCKED_STATUSES
from crm.volteo_naming import code_for

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


def ppoz_wymagane(
	moc_nowa_kw: Any, moc_istniejaca_kw: Any, istniejaca_pv: Any, ppoz_kalkulator: Any = None
) -> bool:
	"""Czy wymagana jest zgoda PPOŻ.

	Zgodnie z umową próg dotyczy SUMY mocy nowej instalacji i ewentualnej
	instalacji istniejącej (przypadek rozbudowy) — pojedyncza instalacja może
	być poniżej progu, a suma już go przekracza. Próg jest wyłączny: dokładnie
	6,5 kW nie wymaga zgody, wymaga dopiero wartość ściśle większa.

	`moc_istniejaca_kw` liczy się do sumy TYLKO, gdy `istniejaca_pv == "Tak"`.
	Formularz chowa pole mocy istniejącej instalacji na ekranie, gdy
	przedstawiciel wybierze "Nie" (albo zostawi wybór pusty). Jawny wybór
	w Selecie musi wtedy wygrywać z ewentualną resztką liczby zostawioną w
	ukrytym polu (np. po zmianie zdania), inaczej sam wymóg zgody PPOŻ
	policzyłby się z danych, których formularz jawnie się wyparł. Patrz
	analogiczna zasada w `crm/volteo_umowa_pdf.py::zbuduj_kontekst` dla pól
	drukowanych na PDF-ie (ops#145).

	`ppoz_kalkulator` (ops#194, decyzja właściciela 2026-09-25) to odpowiedź
	kalkulatora OZE (`CRM Deal.custom_ppoz`), który już doliczył klientowi
	koszt uzgodnień PPOŻ do ceny w momencie wyceny. Gdy ta wartość to
	dokładnie `"Tak"`, wynik jest `True` NIEZALEŻNIE od sumy mocy: umowa nie
	ma prawa wyjść na "Nie", skoro klient już za to zapłacił. Każda inna
	wartość ("Nie", `None`, pusty string, coś nierozpoznanego) zostawia
	istniejącą regułę progu bez zmian. Dopasowanie jest dokładne (jak przy
	`istniejaca_pv == "Tak"` wyżej), same białe znaki albo inna wielkość
	liter ("tak") NIE są akceptowane. Parametr jest opcjonalny, żeby
	dotychczasowe trzyargumentowe wywołania (np. w istniejących testach)
	nadal działały bez zmian.
	"""
	if ppoz_kalkulator == "Tak":
		return True
	moc_istniejaca_liczona = moc_istniejaca_kw if istniejaca_pv == "Tak" else None
	suma = _decimal_lub_zero(moc_nowa_kw) + _decimal_lub_zero(moc_istniejaca_liczona)
	return suma > PROG_PPOZ_KW


def kwota_kredytu(brutto: Any, wklad_wlasny: Any, finansowanie: Any) -> Decimal:
	"""Kwota do sfinansowania kredytem, zależna od wybranego sposobu finansowania.

	- `"Gotówka 100%"`: kredytu nie ma, wynik zawsze `0`. Wkład własny z pola
	  warunkowego (ukrytego wtedy na ekranie) nie ma prawa na to wpłynąć.
	- `"Kredyt 100%"`: całe `brutto` idzie na kredyt, `wklad_wlasny` jest
	  ignorowany (pole też ukryte na ekranie dla tego wyboru).
	- `"Kredyt + gotówka"`: klasyczne `brutto - wklad_wlasny`, nigdy poniżej zera.
	- Inny/nierozpoznany/pusty wybór (formularz jeszcze niewypełniony): `0`.
	  Jawny wybór w Selecie musi istnieć, zanim dokument cokolwiek obiecuje
	  finansowo (ops#145, dokument prawny nie ma prawa sam sobie zaprzeczać).

	Wynik zawsze kwantyzowany do dwóch miejsc po przecinku (grosze), `ROUND_HALF_UP`.
	"""
	if finansowanie == "Kredyt 100%":
		roznica = _decimal_lub_zero(brutto)
	elif finansowanie == "Kredyt + gotówka":
		roznica = _decimal_lub_zero(brutto) - _decimal_lub_zero(wklad_wlasny)
	else:
		roznica = _ZERO
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


_ETYKIETA_IMIE_NAZWISKO = "Imię i nazwisko"
_ETYKIETA_PESEL = "PESEL"
_ETYKIETA_TELEFON = "Telefon"
_ETYKIETA_EMAIL = "E-mail"


def brakujace_dane_klienta(kontakt: dict[str, Any]) -> list[str]:
	"""Zwraca etykiety brakujących danych osobowych klienta (kontaktu) potrzebnych
	do umowy, w stałej kolejności: imię i nazwisko, PESEL, telefon, e-mail (ops#146).

	`brakujace_pola` powyżej waliduje wyłącznie pola samego dokumentu `Volteo
	Umowa`, dane osobowe klienta idą z osobnego dokumentu `Contact` i miały
	dotąd zerową walidację (świadomie ciche puste stringi w `_dane_kontaktu()`,
	`crm/api/umowa.py`), więc umowa mogła wyjść ze statusem „Kompletny” i bez
	ostrzeżenia mimo pustego PESEL-u/telefonu/e-maila w komparycji dokumentu
	prawnego. Ta funkcja jest tym brakującym mechanizmem, lustrzana do wzorca
	`_PREFILL_ETYKIETY`/`brakujace_prefill` z formularza kredytowego
	(`crm/api/kredyt.py`).

	Klucze wejściowe odpowiadają dokładnie kształtowi zwracanemu przez
	`_dane_kontaktu()` w `crm/api/umowa.py`: `first_name`, `last_name`,
	`custom_pesel`, `email`, `mobile_no`. Adres klienta (`custom_ulica` i inne
	pola adresowe kontaktu) celowo NIE jest tu sprawdzany. Adres zamieszkania
	na potrzeby umowy ma własną, niezależną ścieżkę walidacji przez pola
	`adres_zam_*` formularza umowy, już pokrytą przez `brakujace_pola`.

	Brak imienia LUB brak nazwiska daje jedną wspólną etykietę „Imię i
	nazwisko”, nigdy dwie osobne. Nie mutuje `kontakt`. Białe znaki liczą się
	jako brak, tak samo jak pusty string czy `None`.
	"""
	braki: list[str] = []
	if _tekst_pusty(kontakt.get("first_name")) or _tekst_pusty(kontakt.get("last_name")):
		braki.append(_ETYKIETA_IMIE_NAZWISKO)
	if _tekst_pusty(kontakt.get("custom_pesel")):
		braki.append(_ETYKIETA_PESEL)
	if _tekst_pusty(kontakt.get("mobile_no")):
		braki.append(_ETYKIETA_TELEFON)
	if _tekst_pusty(kontakt.get("email")):
		braki.append(_ETYKIETA_EMAIL)
	return braki


def _tekst_pusty(wartosc: Any) -> bool:
	"""`None`/pusty string/same białe znaki są puste; każda inna wartość nie jest.

	Dane kontaktu z `_dane_kontaktu()` są zawsze stringami albo `None` (nigdy
	liczbą), więc w odróżnieniu od `_jest_puste` nie ma tu wariantu
	zero-oznacza-puste.
	"""
	if wartosc is None:
		return True
	return isinstance(wartosc, str) and wartosc.strip() == ""


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


def czy_propagowac_zgody(autenti_status: str | None) -> bool:
	"""Czy `_propaguj_zgody` (`crm/api/umowa.py`) powinno nadpisać zgody na karcie(-ach) kontaktu.

	Fałsz dla `SEND_BLOCKED_STATUSES` (`crm.integrations.autenti.logika`, "Wysyłanie"/
	"Wysłana"/"Podpisana"; REVISIT.md A-3, ops#170): dokument, który już poszedł do
	podpisu albo został podpisany, nie powinien retroaktywnie zmieniać zgód na
	kartach kontaktów przy późniejszym zapisie formularza, konsentem wiążącym jest
	ten widoczny na podpisanym PDF-ie, nie ten ostatnio zaznaczony w formularzu.

	Prawda dla `None`/pustego stringu (dokument nigdy niewysłany) i dla dowolnego
	innego statusu, w tym terminalnych nie-sukcesu ("Błąd", "Odrzucona", "Wygasła",
	"Wycofana"): po nich formularz wraca do stanu roboczego, więc propagacja zgód
	ma taki sam sens jak przed pierwszą wysyłką.
	"""
	if not autenti_status:
		return True
	return autenti_status not in SEND_BLOCKED_STATUSES


def kod_szablonu(rodzaj_umowy: str | None, podwojna: bool) -> str:
	"""Zwraca kod wbudowanego szablonu PDF-u umowy (klucz w
	`crm.volteo_umowa_render.SZABLONY`) dla danego rodzaju umowy i obecności
	drugiego Zamawiającego (ops#167).

	Kod bazowy (`PV`/`PVME`/`ME`/`CP`/`XX`) jest DOKŁADNIE tym samym, co
	zwraca `crm.volteo_naming.code_for`. Ta funkcja świadomie go reużywa,
	zamiast duplikować mapowanie `custom_rodzaj_umowy` na kod, żeby nazewnictwo
	umowy (`PRO/<KOD>/<RR>/<NNNN>`) i wybór szablonu PDF-u nigdy nie mogły się
	rozjechać. `podwojna=True` dokleja `"_2"` (np. `"PV"` -> `"PV_2"`), dokładnie
	te trzy klucze, pod którymi warianty dwuosobowe są zarejestrowane w
	`SZABLONY` (`PV_2`/`PVME_2`/`ME_2`). `podwojna=False` zwraca kod bazowy bez
	żadnej zmiany: ŚCIEŻKA JEDNOOSOBOWA JEST NIEZMIENIONA.

	`CP` i `XX` nie mają wpisu w `SZABLONY` (ani w wariancie pojedynczym, ani
	podwójnym). Ta funkcja tego nie sprawdza, to rola wołającego
	(`crm/api/umowa.py`), tak jak już dziś sprawdza to dla kodu bazowego.
	"""
	kod = code_for(rodzaj_umowy)
	return f"{kod}_2" if podwojna else kod


def czy_umowa_podwojna(umowa: dict[str, Any]) -> bool:
	"""Czy umowa ma drugiego Zamawiającego (ops#167/#168): bool z pola
	`drugi_zamawiajacy` (Link do `Contact`, ustawiane przez `crm/api/umowa.py`).

	Pusty string i `None` dają `False`; dowolna niepusta nazwa dokumentu daje
	`True`. Nie mutuje `umowa`.
	"""
	return bool(umowa.get("drugi_zamawiajacy"))


def kontakty_do_zgod(podstawowy: str | None, drugi: str | None) -> list[str]:
	"""Lista nazw `Contact`, na które `_propaguj_zgody` ma zapisać zgody RODO/marketingowe.

	Podstawowy kontakt szansy zawsze pierwszy, gdy ustawiony; drugi Zamawiający
	(ops#168, `Volteo Umowa.drugi_zamawiajacy`) drugi, gdy ustawiony. Deduplikuje,
	żeby ten sam kontakt wybrany omyłkowo w obu rolach nie dostał dwóch identycznych
	zapisów. `None`/pusty string na dowolnej pozycji jest pomijany, nigdy nie
	trafia do wyniku jako pusty wpis.
	"""
	kandydaci = [podstawowy, drugi]
	wynik: list[str] = []
	for kontakt in kandydaci:
		if kontakt and kontakt not in wynik:
			wynik.append(kontakt)
	return wynik
