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

from decimal import Decimal, InvalidOperation
from typing import Any

GRUPY_DOCHODU: dict[str, tuple[str, ...]] = {
	"praca_wlaczone": (
		"praca_forma",
		"praca_data_zatrudnienia",
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
	"numer_rachunku",
)
"""Pola wymagane niezależnie od pozostałych odpowiedzi w formularzu (decyzja właściciela, 2026-08-15)."""


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
