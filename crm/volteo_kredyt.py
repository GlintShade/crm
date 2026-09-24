# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Logika formularza wniosku kredytowego (grupy dochodu, wymagane pola, walidacja kwot).

Moduł celowo nie importuje ``frappe`` — z tego samego powodu co
`crm/volteo_umowa.py`: na tej maszynie ``frappe`` nie jest instalowalne, więc
to jedyny sposób na lokalną, silną bramkę testową (`crm/test_volteo_kredyt_pdf.py`
importuje pośrednio przez `crm/volteo_kredyt_pdf.py`). Cała logika zależna od
frameworka (zapis do dokumentu, whitelisted API) mieszka gdzie indziej — tu
tylko czyste funkcje.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from crm.integrations.autenti.logika import czy_legacy_kredyt

GRUPY_DOCHODU: dict[str, tuple[str, ...]] = {
	"praca_wlaczone": (
		"praca_forma",
		"praca_okres",
		"praca_okres_od",
		"praca_okres_do",
		"praca_nip",
		"praca_nazwa_zakladu",
		"praca_adres_telefon",
		"praca_kwota_dochodu",
	),
	"emerytura_wlaczone": (
		"emerytura_numer_swiadczenia",
		"emerytura_od_kiedy",
		"emerytura_kwota_dochodu",
	),
	"renta_wlaczone": (
		"renta_numer_swiadczenia",
		"renta_od_kiedy",
		"renta_kwota_dochodu",
	),
	"dzialalnosc_wlaczone": (
		"dzialalnosc_forma_opodatkowania",
		"dzialalnosc_forma_inna",
		"dzialalnosc_nip",
		"dzialalnosc_nazwa",
		"dzialalnosc_adres",
		"dzialalnosc_telefon",
		"dzialalnosc_od_kiedy",
		"dzialalnosc_kwota_dochodu",
	),
	"gospodarstwo_wlaczone": (
		"gospodarstwo_nip",
		"gospodarstwo_od_kiedy",
		"gospodarstwo_kwota_dochodu",
	),
	"inne_wlaczone": (
		"inne_1_typ",
		"inne_1_kwota",
		"inne_2_typ",
		"inne_2_kwota",
	),
}
"""Mapowanie przełącznika (`*_wlaczone`) źródła dochodu na jego pola danych.

Kolejność kluczy jest deklaratywna i odpowiada kolejności, w jakiej
`brakujace_pola()` dopisuje pola poszczególnych grup do wyniku."""

POLA_WNIOSKODAWCY: tuple[str, ...] = (
	"wnioskodawca_pesel",
	"wnioskodawca_imiona",
	"wnioskodawca_nazwisko",
	"wnioskodawca_telefon",
	"wnioskodawca_email",
	"wnioskodawca_kod_pocztowy",
	"wnioskodawca_miejscowosc",
	"wnioskodawca_ulica",
	"wnioskodawca_nr_domu",
	"wnioskodawca_nr_lokalu",
)
"""Kanon 10 pól wnioskodawcy formularza kredytowego (ops#157), w kolejności
wiążącej dla `ETYKIETY_WNIOSKODAWCY`, `brakujace_dane_wnioskodawcy()` i
konsumentów w ops/backend/frontend."""

ETYKIETY_WNIOSKODAWCY: dict[str, str] = {
	"wnioskodawca_pesel": "PESEL",
	"wnioskodawca_imiona": "Imiona",
	"wnioskodawca_nazwisko": "Nazwisko",
	"wnioskodawca_telefon": "Telefon",
	"wnioskodawca_email": "E-mail",
	"wnioskodawca_kod_pocztowy": "Kod pocztowy",
	"wnioskodawca_miejscowosc": "Miejscowość",
	"wnioskodawca_ulica": "Ulica",
	"wnioskodawca_nr_domu": "Nr domu",
	"wnioskodawca_nr_lokalu": "Nr lokalu",
}
"""Etykiety PL kanonu wnioskodawcy, jeden do jednego z `POLA_WNIOSKODAWCY`.
Te same 10 wpisów są też domieszane do `ETYKIETY_POL` niżej, żeby istniejący
test kanonu etykiet (`crm/test_volteo_kredyt_etykiety.py`) automatycznie
obejmował i te pola, zamiast utrzymywać osobny test kanonu."""

_ETYKIETY_KREDYT_POL: dict[str, str] = {
	"miejsce_urodzenia": "Miejsce urodzenia",
	"rodzaj_dokumentu": "Rodzaj dokumentu tożsamości",
	"seria_numer_dokumentu": "Seria i numer dokumentu tożsamości",
	"data_wydania_dokumentu": "Data wydania dokumentu tożsamości",
	"data_waznosci_dokumentu": "Data ważności dokumentu tożsamości",
	"adres_zameldowania_taki_sam": "Czy adres zamieszkania jest taki sam, jak adres zameldowania?",
	"adres_zameldowania": "Adres zamieszkania",
	"adres_korespondencji_taki_sam": "Czy adres do korespondencji jest taki sam, jak adres zameldowania?",
	"adres_korespondencji": "Adres do korespondencji",
	"wyksztalcenie": "Wykształcenie",
	"stan_cywilny": "Stan cywilny",
	"liczba_osob_na_utrzymaniu": "Liczba osób w gospodarstwie domowym na utrzymaniu",
	"kwota_800_plus": "Kwota świadczenia 800+",
	"dochod_wspolmalzonka": "Deklarowany dochód współmałżonka",
	"zrodlo_dochodu_malzonka": "Źródło dochodu małżonka",
	"oplaty_miesieczne": "Opłaty miesięczne",
	"suma_zobowiazan": "Suma miesięcznych zobowiązań kredytowych i finansowych",
	"numer_rachunku": "Numer rachunku bankowego",
	"praca_wlaczone": "Dochód: umowa o pracę / zlecenie / dzieło",
	"praca_forma": "Forma zatrudnienia",
	"praca_okres": "Okres zatrudnienia",
	"praca_okres_od": "Zatrudnienie od",
	"praca_okres_do": "Zatrudnienie do",
	"praca_nip": "NIP zakładu pracy",
	"praca_nazwa_zakladu": "Nazwa zakładu pracy",
	"praca_adres_telefon": "Adres i numer telefonu zakładu pracy",
	"praca_kwota_dochodu": "Kwota dochodu",
	"emerytura_wlaczone": "Dochód: emerytura",
	"emerytura_numer_swiadczenia": "Numer świadczenia",
	"emerytura_od_kiedy": "Od kiedy przyznane jest świadczenie",
	"emerytura_kwota_dochodu": "Kwota dochodu",
	"renta_wlaczone": "Dochód: renta",
	"renta_numer_swiadczenia": "Numer świadczenia",
	"renta_od_kiedy": "Od kiedy przyznane jest świadczenie",
	"renta_kwota_dochodu": "Kwota dochodu",
	"dzialalnosc_wlaczone": "Dochód: działalność gospodarcza",
	"dzialalnosc_forma_opodatkowania": "Forma opodatkowania",
	"dzialalnosc_forma_inna": "Inna forma opodatkowania: jaka?",
	"dzialalnosc_nip": "NIP firmy",
	"dzialalnosc_nazwa": "Nazwa firmy",
	"dzialalnosc_adres": "Adres firmy",
	"dzialalnosc_telefon": "Numer telefonu do firmy",
	"dzialalnosc_od_kiedy": "Od kiedy prowadzona jest działalność?",
	"dzialalnosc_kwota_dochodu": "Kwota dochodu",
	"gospodarstwo_wlaczone": "Dochód: gospodarstwo rolne",
	"gospodarstwo_nip": "NIP gospodarstwa",
	"gospodarstwo_od_kiedy": "Od kiedy prowadzone jest gospodarstwo?",
	"gospodarstwo_kwota_dochodu": "Kwota dochodu",
	"inne_wlaczone": "Dochód: inne",
	"inne_1_typ": "Typ dochodu (1)",
	"inne_1_kwota": "Kwota dochodu (1)",
	"inne_2_typ": "Typ dochodu (2)",
	"inne_2_kwota": "Kwota dochodu (2)",
}
"""Etykiety PL dla 53 pól danych formularza `Volteo Kredyt`
(`_DANE_POLA_DOZWOLONE` w `crm/api/kredyt.py`): przepisane 1:1 z etykiet
doctype'u (`ops/crm-kredyt.py`, sekcja `KREDYT_FIELDS`), które są zgodne z
oryginalnym szablonem PDF-u (ops#148: front, komunikat blokujący PDF i Desk
dryfowały, doctype był zgodny z papierem od początku).

Baza prywatna, złożona z `ETYKIETY_WNIOSKODAWCY` w publiczny kanon
`ETYKIETY_POL` niżej, zamiast być konsumowana wprost."""

ETYKIETY_POL: dict[str, str] = {**_ETYKIETY_KREDYT_POL, **ETYKIETY_WNIOSKODAWCY}
"""Jedyny kanon etykiet PL dla wszystkich 63 pól danych formularza kredytowego:
53 pola `Volteo Kredyt` (`_ETYKIETY_KREDYT_POL` wyżej) plus 10 pól
wnioskodawcy (`ETYKIETY_WNIOSKODAWCY`, ops#157).

Ta sama etykieta ma się pojawić w banerze braków, w komunikacie serwera
blokującym PDF (`crm/api/kredyt.py::_ETYKIETY_POL`, alias importu stąd) i w
polu formularza (`frontend/src/utils/kredytForm.js::ETYKIETY_POL`, jego 1:1
odpowiednik po stronie JS). Jedyny dopuszczalny wyjątek: etykieta ekranowa w
JS krótsza niż kanon, gdy kanon nie mieści się w kolumnie formularza. Wtedy
JS ma osobny słownik `ETYKIETY_PELNE` z pełnym kanonem, używanym w banerze i
w tooltipie pola (patrz `kredytForm.js`).

JEDNO celowe odstępstwo od `ops/crm-kredyt.py`: `dzialalnosc_forma_inna` ma
tam etykietę łączoną myślnikiem (kończy się słowami "jaka?" po myślniku).
Reguła projektu zabrania myślników w kodzie/testach/komentarzach, więc kanon
tutaj używa dwukropka ("Inna forma opodatkowania: jaka?"). Wyrównanie
etykiety w `ops/crm-kredyt.py` do tego brzmienia jest osobną, świadomie
odłożoną zmianą (NIE częścią ops#148). `ops/crm-kredyt.py` nie jest tu
ruszane.
"""

_BAZA_WYMAGANE: tuple[str, ...] = (
	"miejsce_urodzenia",
	"rodzaj_dokumentu",
	"seria_numer_dokumentu",
	"data_wydania_dokumentu",
	"data_waznosci_dokumentu",
	"adres_zameldowania_taki_sam",
	"adres_korespondencji_taki_sam",
	"wyksztalcenie",
	"stan_cywilny",
	"liczba_osob_na_utrzymaniu",
	"kwota_800_plus",
	"dochod_wspolmalzonka",
	"zrodlo_dochodu_malzonka",
	"oplaty_miesieczne",
	"suma_zobowiazan",
)
"""Pola wymagane niezależnie od pozostałych odpowiedzi w formularzu (decyzja właściciela, 2026-08-15).
`numer_rachunku` usunięte z wymaganych decyzją właściciela z 2026-08-17 — pole nadal istnieje i trafia na PDF, jeśli podane."""


def kwota_poprawna(tekst: Any) -> bool:
	"""Sprawdza, czy `tekst` da się odczytać jako `Decimal` — bramka formatu kwoty.

	Akceptuje polskie formy zapisu ("1234,56", "1 234,56" ze zwykłą spacją albo
	NBSP jako separatorem tysięcy) oraz formę kropkową ("1234.56"). Nie
	sprawdza obecności pola — to rola `brakujace_pola()` (`""`/`None` daje tu
	`False`, nie wyjątek). Nigdy nie rzuca.
	"""
	if tekst is None:
		return False
	if not isinstance(tekst, str):
		tekst = str(tekst)
	oczyszczony = tekst.strip()
	if oczyszczony == "":
		return False
	oczyszczony = oczyszczony.replace("\xa0", "").replace(" ", "").replace(",", ".")
	try:
		Decimal(oczyszczony)
	except InvalidOperation:
		return False
	return True


def brakujace_pola(dane: dict[str, Any]) -> list[str]:
	"""Zwraca listę nazw pól wymaganych a pustych, w stałej (deklaracyjnej) kolejności.

	Nie mutuje `dane`. Reguły (decyzja właściciela, 2026-08-15):

	- Pola bazowe (`_BAZA_WYMAGANE`) są wymagane zawsze.
	- `adres_zameldowania` jest wymagany tylko, gdy `adres_zameldowania_taki_sam
	  == "Nie"`; analogicznie `adres_korespondencji` dla `adres_korespondencji_taki_sam`.
	- Żadna grupa dochodu (`GRUPY_DOCHODU`) nie jest sama w sobie wymagana —
	  zero włączonych grup daje komplet. Dla KAŻDEJ włączonej grupy jej pola
	  stają się wymagane, z wyjątkami: `praca_okres_do` tylko gdy
	  `praca_okres == "Czas określony"` (ale `praca_okres_od` zawsze, gdy praca
	  włączona); `dzialalnosc_forma_inna` tylko gdy
	  `dzialalnosc_forma_opodatkowania == "inne"` (dokładna, transkrybowana z
	  PDF-u pisownia, WIELKĄ literą tylko `Inne` z `praca_okres` się różni — to
	  osobny, nasz własny Select); w grupie `inne` tylko `inne_1_typ`/`inne_1_kwota`
	  (druga para jest opcjonalna).

	Pustość: `None`/`""`/sam biały znak są puste. Kwoty są celowo polami
	tekstowymi (Data) właśnie po to, żeby jawne zero ("0") dało się odróżnić od
	nietkniętego pola — `"0"` liczy się jako wypełnione.
	"""
	wymagane: list[str] = list(_BAZA_WYMAGANE)

	if dane.get("adres_zameldowania_taki_sam") == "Nie":
		wymagane.append("adres_zameldowania")
	if dane.get("adres_korespondencji_taki_sam") == "Nie":
		wymagane.append("adres_korespondencji")

	for przelacznik, pola in GRUPY_DOCHODU.items():
		if not _wlaczone(dane.get(przelacznik)):
			continue
		wymagane.extend(_pola_grupy(przelacznik, pola, dane))

	return [pole for pole in wymagane if _jest_puste(dane.get(pole))]


def _pola_grupy(przelacznik: str, pola: tuple[str, ...], dane: dict[str, Any]) -> list[str]:
	"""Filtruje pola danej grupy dochodu wg wyjątków opisanych w `brakujace_pola()`.

	Zachowuje kolejność zadeklarowaną w `GRUPY_DOCHODU` — warunkowo pomija
	pole zamiast dopisywać je na końcu, żeby kolejność wyniku była stabilna
	niezależnie od tego, które pola akurat są warunkowe.
	"""
	if przelacznik == "praca_wlaczone":
		wynik = []
		for pole in pola:
			if pole == "praca_okres_do":
				if dane.get("praca_okres") == "Czas określony":
					wynik.append(pole)
				continue
			wynik.append(pole)
		return wynik

	if przelacznik == "dzialalnosc_wlaczone":
		# Pisownia "inne" (małą literą) jest tu celowa — dokładna transkrypcja
		# opcji Select z PDF-u (`crm/volteo_kredyt_mapa.py`, `ops/crm-kredyt.py`),
		# w odróżnieniu od "Czas określony" w `praca_okres`, który jest naszym
		# własnym, niezależnym od PDF-u polem.
		wynik = []
		for pole in pola:
			if pole == "dzialalnosc_forma_inna":
				if dane.get("dzialalnosc_forma_opodatkowania") == "inne":
					wynik.append(pole)
				continue
			wynik.append(pole)
		return wynik

	if przelacznik == "inne_wlaczone":
		return [pole for pole in pola if pole in ("inne_1_typ", "inne_1_kwota")]

	return list(pola)


def _wlaczone(wartosc: Any) -> bool:
	"""Parsuje przełącznik grupy dochodu (Check: 0/1, `bool`, albo string z klienta).

	`None`, `False`, `0`, `"0"` i pusty/sam-biały-znak string są wyłączone;
	wszystko inne jest włączone. Nigdy nie rzuca.
	"""
	if isinstance(wartosc, bool):
		return wartosc
	if wartosc is None:
		return False
	if isinstance(wartosc, str):
		tekst = wartosc.strip()
		return tekst not in ("", "0")
	return bool(wartosc)


def _jest_puste(wartosc: Any) -> bool:
	"""Reguła pustości: `None`/`""`/sam biały znak są puste; wszystko inne (w tym `"0"`) jest wypełnione."""
	if wartosc is None:
		return True
	if isinstance(wartosc, str):
		return wartosc.strip() == ""
	return False


def _tekst_wnioskodawcy(kredyt: dict[str, Any], pole: str) -> str:
	"""Odczytuje `kredyt[pole]`, zamieniając brak klucza albo `None` na `""`
	i ucinając białe znaki na brzegach, tak samo jak `_tekst()` w
	`crm/volteo_kredyt_pdf.py` (nie importowana stąd, żeby nie odwracać
	kierunku zależności między tymi dwoma modułami)."""
	wartosc = kredyt.get(pole)
	if wartosc is None:
		return ""
	return str(wartosc).strip()


def kontakt_z_wnioskodawcy(kredyt: dict[str, Any]) -> dict[str, str]:
	"""Mapuje pola wnioskodawcy formularza kredytowego (`wnioskodawca_*`, patrz
	`POLA_WNIOSKODAWCY`) na kształt SUROWY, którego dziś oczekuje
	`crm.volteo_kredyt_pdf.zbuduj_kontekst_kredytu` jako argument `kontakt`:
	klucze stylu `Contact` (`first_name`, `last_name`, `custom_pesel`,
	`mobile_no`, `email`, `custom_ulica`, `custom_nr_domu`,
	`custom_nr_mieszkania`, `custom_kod_pocztowy`, `custom_miasto`).

	Nie mutuje `kredyt`: buduje i zwraca nowy słownik. Brakujący klucz albo
	`None` w `kredyt` staje się `""` w wyniku.

	UWAGA (udokumentowana klasa błędu z 2026-08-05 i 2026-08-15,
	`crm/api/kredyt.py:268-305`): to kształt SUROWY, różny od kształtu
	PRZEKLUCZONEGO zwracanego przez `prefill_z_wnioskodawcy`. Podanie wyniku
	`prefill_z_wnioskodawcy` tam, gdzie oczekiwany jest ten kształt, daje
	pusty blok danych klienta w PDF-ie poza polem e-mail, jedynym kluczem o
	tej samej nazwie w obu kształtach. Ten błąd jest widoczny dopiero na
	wydruku, nigdy w teście typów ani w konsoli przeglądarki.
	"""
	return {
		"first_name": _tekst_wnioskodawcy(kredyt, "wnioskodawca_imiona"),
		"last_name": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nazwisko"),
		"custom_pesel": _tekst_wnioskodawcy(kredyt, "wnioskodawca_pesel"),
		"mobile_no": _tekst_wnioskodawcy(kredyt, "wnioskodawca_telefon"),
		"email": _tekst_wnioskodawcy(kredyt, "wnioskodawca_email"),
		"custom_ulica": _tekst_wnioskodawcy(kredyt, "wnioskodawca_ulica"),
		"custom_nr_domu": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nr_domu"),
		"custom_nr_mieszkania": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nr_lokalu"),
		"custom_kod_pocztowy": _tekst_wnioskodawcy(kredyt, "wnioskodawca_kod_pocztowy"),
		"custom_miasto": _tekst_wnioskodawcy(kredyt, "wnioskodawca_miejscowosc"),
	}


def prefill_z_wnioskodawcy(kredyt: dict[str, Any]) -> dict[str, str]:
	"""Mapuje pola wnioskodawcy formularza kredytowego (`wnioskodawca_*`, patrz
	`POLA_WNIOSKODAWCY`) na kształt PRZEKLUCZONY, używany przez przeglądarkę:
	krótkie klucze bez przedrostka `wnioskodawca_` i bez nazewnictwa stylu
	`Contact` (`pesel`, `imiona`, `nazwisko`, `telefon`, `email`,
	`kod_pocztowy`, `miejscowosc`, `ulica`, `nr_domu`, `nr_lokalu`) -
	odpowiednik dzisiejszego `prefill` liczonego z `Contact`
	(`crm/api/kredyt.py::_kontakt_surowy_i_prefill`).

	Nie mutuje `kredyt`: buduje i zwraca nowy słownik. Brakujący klucz albo
	`None` w `kredyt` staje się `""` w wyniku.

	UWAGA: to kształt PRZEKLUCZONY, różny od kształtu SUROWEGO zwracanego
	przez `kontakt_z_wnioskodawcy`. Podanie wyniku tej funkcji tam, gdzie
	`crm.volteo_kredyt_pdf.zbuduj_kontekst_kredytu` oczekuje argumentu
	`kontakt`, daje pusty blok danych klienta w PDF-ie poza polem e-mail -
	patrz docstring `kontakt_z_wnioskodawcy` dla pełnego opisu tej klasy
	błędu (incydenty 2026-08-05, 2026-08-15).
	"""
	return {
		"pesel": _tekst_wnioskodawcy(kredyt, "wnioskodawca_pesel"),
		"imiona": _tekst_wnioskodawcy(kredyt, "wnioskodawca_imiona"),
		"nazwisko": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nazwisko"),
		"telefon": _tekst_wnioskodawcy(kredyt, "wnioskodawca_telefon"),
		"email": _tekst_wnioskodawcy(kredyt, "wnioskodawca_email"),
		"kod_pocztowy": _tekst_wnioskodawcy(kredyt, "wnioskodawca_kod_pocztowy"),
		"miejscowosc": _tekst_wnioskodawcy(kredyt, "wnioskodawca_miejscowosc"),
		"ulica": _tekst_wnioskodawcy(kredyt, "wnioskodawca_ulica"),
		"nr_domu": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nr_domu"),
		"nr_lokalu": _tekst_wnioskodawcy(kredyt, "wnioskodawca_nr_lokalu"),
	}


def brakujace_dane_wnioskodawcy(kredyt: dict[str, Any]) -> list[str]:
	"""Zwraca podzbiór `POLA_WNIOSKODAWCY` (w tej samej kolejności), który jest
	wymagany a pusty. Wymagane są wszystkie pola wnioskodawcy poza
	`wnioskodawca_nr_lokalu` (numer lokalu jest opcjonalny, to numer
	mieszkania). Pustość jak w `brakujace_pola()`: `_jest_puste` (`None`/`""`/
	sam biały znak są puste, wszystko inne, w tym `"0"`, jest wypełnione).

	Nie mutuje `kredyt`."""
	return [
		pole
		for pole in POLA_WNIOSKODAWCY
		if pole != "wnioskodawca_nr_lokalu" and _jest_puste(kredyt.get(pole))
	]


def pasuje_plik_kredytu(file_name: str, prefiks: str, kredyt_name: str, deal: str) -> bool:
	"""Czy `file_name` to plik PDF formularza kredytowego wygenerowany DOKŁADNIE dla
	rekordu `kredyt_name` tej szansy, nie dla żadnego INNEGO formularza `Volteo
	Kredyt` tej samej szansy (ops#158, sprzątanie starych PDF-ów po wielu
	formularzach na szansę wprowadzonych przez ops#159).

	Pułapka, dla której ta funkcja istnieje: `prefiks` oczekiwany jest tutaj
	jako BAZOWY prefiks szansy (`prefiks_pliku_kredytu(deal, deal)`, czyli
	wariant legacy bez żadnego sufiksu rekordu), ten sam string, którego
	wołający używa do pobrania kandydatów z bazy przez `LIKE 'prefiks%.pdf'`.
	Ten prefiks bazowy jest jednocześnie ścisłym prefiksem STRINGA nazwy pliku
	KAŻDEGO rodzeństwa tej szansy, także rekordów hashowych (prefiks hashowy to
	zawsze prefiks bazowy plus doklejony sufiks). Samo dopasowanie LIKE
	złapałoby więc pliki WSZYSTKICH formularzy tej szansy naraz. Ta funkcja
	jest drugim, precyzyjnym sitem, wołanym w Pythonie PO takim LIKE:

	- dla rekordu legacy (`czy_legacy_kredyt(deal, kredyt_name)` prawdziwe,
	  czyli `kredyt_name == deal`) wymaga kształtu BEZ żadnego sufiksu
	  hashowego: `<prefiks>-YYYYMMDD-HHMMSS.pdf` albo
	  `<prefiks>-YYYYMMDD-HHMMSS-podpisany.pdf`;
	- dla rekordu hashowego wymaga kształtu z DOKŁADNIE JEGO WŁASNYM
	  8-znakowym sufiksem (`kredyt_name[:8]`, literalnie, nie wzorcem
	  dowolnych znaków alfanumerycznych), nigdy z sufiksem żadnego INNEGO
	  rekordu tej samej szansy.

	Nigdy nie rzuca; pusty/`None` `file_name` daje `False`.
	"""
	if czy_legacy_kredyt(deal, kredyt_name):
		wzorzec = "^" + re.escape(prefiks) + r"-\d{8}-\d{6}(-podpisany)?\.pdf$"
	else:
		wzorzec = (
			"^"
			+ re.escape(prefiks)
			+ "-"
			+ re.escape(kredyt_name[:8])
			+ r"-\d{8}-\d{6}(-podpisany)?\.pdf$"
		)
	return bool(re.match(wzorzec, file_name or ""))
