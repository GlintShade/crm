# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Test kontraktu dwukierunkowego mapa↔kontekst dla formularza kredytowego
(`crm/volteo_kredyt_mapa.py` ↔ `crm/volteo_kredyt_pdf.py`).

Odpowiednik `crm/test_volteo_umowa_mapa.py` dla CZWARTEGO dokumentu — „Ankieta
danych do wniosku kredytowego". W odróżnieniu od umowy (trzy szablony w
rejestrze `SZABLONY`) formularz kredytowy ma JEDEN szablon i JEDNĄ mapę
(`MAPA_KREDYT`), więc testy niżej nie pętlą się po żadnym rejestrze — operują
bezpośrednio na `MAPA_KREDYT` i na kontekście zwracanym przez
`zbuduj_kontekst_kredytu`.
"""

import unittest
from datetime import date
from typing import Any

from crm.volteo_kredyt_mapa import LICZBA_STRON_KREDYT, MAPA_KREDYT
from crm.volteo_kredyt_pdf import (
	ADRES_NIE,
	ADRES_TAK,
	FORMA_INNE,
	FORMA_KPIR,
	FORMA_RYCZALT,
	FORMA_UMOWA_DZIELO,
	FORMA_UMOWA_O_PRACE,
	FORMA_UMOWA_ZLECENIE,
	OKRES_CZAS_NIEOKRESLONY,
	OKRES_CZAS_OKRESLONY,
	STAN_KAWALER_PANNA,
	STAN_MALZENSTWO_ROZDZIELNOSC,
	STAN_MALZENSTWO_WSPOLNOTA,
	STAN_ROZWIEDZIONY,
	STAN_SEPARACJA,
	STAN_WDOWIEC_WDOWA,
	WYKSZTALCENIE_PODSTAWOWE,
	WYKSZTALCENIE_SREDNIE,
	WYKSZTALCENIE_WYZSZE,
	WYKSZTALCENIE_ZAWODOWE,
	zbuduj_kontekst_kredytu,
)
from crm.volteo_umowa_mapa import SZEROKOSC_STRONY_PT, WYSOKOSC_STRONY_PT, Pole

# ---------------------------------------------------------------------------
# Wyjątki kontraktu dwukierunkowego.
#
# Klucz kontekstu, którego fizycznie nie ma gdzie wydrukować na formularzu,
# byłby tu jawnie wymieniony z uzasadnieniem. Formularz kredytowy ma DOKŁADNIE
# jeden szablon (w odróżnieniu od trzech szablonów umowy) i mapa pokrywa
# każdy z 72 kluczy `KLUCZE_KONTEKSTU` — nie ma tu żadnego pola, które nie
# miałoby gdzie się wydrukować, więc zbiór wyjątków jest pusty.
# ---------------------------------------------------------------------------

WYJATKI_KREDYT: frozenset[str] = frozenset()
"""Formularz kredytowy ma jeden szablon obejmujący wszystkie 72 klucze
kontekstu — brak kluczy bez pozycji w mapie, więc zbiór jest pusty."""

# Strony (indeksy 0-based) na których każdy z dwóch kluczy podpisu ma DOKŁADNIE
# jedną pozycję — strona 3 (indeks 2, koniec §9) i strona 5 (indeks 4, koniec
# zgody RODO). Patrz komentarze przy `_STRONA_3`/`_STRONA_5` w
# `crm/volteo_kredyt_mapa.py`.
_STRONY_PODPISU: frozenset[int] = frozenset({2, 4})

# Strony celowo bez żadnej pozycji — czysty tekst prawny/informacyjny, bez
# pól formularza (zweryfikowane w `crm/volteo_kredyt_mapa.py`: brak glifu
# kratki/linii kropkowanej/podpisu na obu stronach).
_STRONY_PUSTE: frozenset[int] = frozenset({3, 5})


def _klucze_mapy() -> frozenset[str]:
	"""Zbiór unikalnych kluczy kontekstu obecnych w `MAPA_KREDYT` (bez duplikatów)."""
	return frozenset(pole.klucz for pole in MAPA_KREDYT)


def _pozycje(klucz: str) -> tuple[Pole, ...]:
	"""Wszystkie pozycje `Pole` w `MAPA_KREDYT` dla danego klucza kontekstu, w kolejności mapy."""
	return tuple(pole for pole in MAPA_KREDYT if pole.klucz == klucz)


def _kredyt_wszystko_wlaczone(**nadpisania: Any) -> dict[str, Any]:
	"""Wniosek kredytowy z KAŻDYM przełącznikiem grupy dochodu włączonym i KAŻDYM
	polem wypełnionym poprawną, niepustą wartością (w tym oba warianty adresu
	inne-niż-zamieszkania, żeby `adres_zameldowania`/`adres_korespondencji`
	też wyszły niepuste) — żadna wartość kontekstu nie wypadnie pusta z powodu
	reguły "brak danych = pustka", więc test kluczy-bez-pozycji nie pomyli
	"brak pozycji w mapie" z "wartość akurat pusta w tym fixture".

	Pola tu wypełnione muszą być OBECNYMI polami `Volteo Kredyt` (patrz
	`ops/crm-kredyt.py::KREDYT_FIELDS`), nie wycofanymi 2026-08-15
	(`ops/crm-kredyt.py::POLA_DO_USUNIECIA`: `rodzaj_seria_numer_dokumentu`,
	`dzialalnosc_adres_telefon`): te dwa stare pola nie istnieją w
	`zbuduj_kontekst_kredytu()`, więc gdyby fixture je niosła zamiast
	`rodzaj_dokumentu`+`seria_numer_dokumentu`/`dzialalnosc_adres`+
	`dzialalnosc_telefon`, kontekst po prostu by je zignorował i odpowiednie
	klucze kontekstu (`rodzaj_seria_numer_dokumentu`,
	`dzialalnosc_adres_telefon`) wyszłyby puste (K11: fałszywie zielony test
	pustości). `stan_cywilny` musi być jedną z kanonicznych stałych `STAN_*`
	(pisownia z wielkiej litery, patrz `crm/volteo_kredyt_pdf.py`), nie
	surową transkrypcją PDF-u sprzed 2026-08-15, inaczej żadna z sześciu
	kratek stanu cywilnego się nie zapala i wszystkie sześć wychodzi `False`.

	Waliduje `praca_okres == "Czas określony"`, więc `praca_nieokreslony_od`
	wychodzi jako pusty string w tym konkretnym fixture, to nie przeszkadza
	kontraktowi kluczy (klucz jest zawsze obecny w kontekście, niezależnie od
	wartości), tylko oznacza, że test wartości-str-lub-bool i tak przechodzi
	(pusty string to wciąż `str`). Test pustości (`TestPelnyFixtureBezPustychKluczy`
	niżej) sprawdza to wprost, wraz z jawnymi wyjątkami dla wzajemnie
	wykluczających się kratek (wykształcenie, stan cywilny, forma
	zatrudnienia, forma opodatkowania, adresy) i dla routingu
	`praca_okres_od`. Drugi wariant fixture (`praca_okres = "Czas
	nieokreślony"`) sprawdza symetryczny przypadek."""
	baza: dict[str, Any] = {
		"miejsce_urodzenia": "Warszawa",
		"rodzaj_dokumentu": "Dowód osobisty",
		"seria_numer_dokumentu": "ABC123456",
		"data_wydania_dokumentu": "2020-01-15",
		"data_waznosci_dokumentu": "2030-01-15",
		"adres_zameldowania_taki_sam": "Nie",
		"adres_zameldowania": "ul. Testowa 1, 00-002 Warszawa",
		"adres_korespondencji_taki_sam": "Nie",
		"adres_korespondencji": "ul. Kolejowa 2, 00-003 Warszawa",
		"wyksztalcenie": "wyższe",
		"stan_cywilny": STAN_KAWALER_PANNA,
		"liczba_osob_na_utrzymaniu": "2",
		"kwota_800_plus": "800",
		"dochod_wspolmalzonka": "3000",
		"zrodlo_dochodu_malzonka": "Umowa o pracę",
		"oplaty_miesieczne": "500",
		"suma_zobowiazan": "1000",
		"numer_rachunku": "PL61109010140000071219812874",
		"praca_wlaczone": 1,
		"praca_forma": "Umowa o pracę",
		"praca_data_zatrudnienia": "2019-05-01",
		"praca_okres": "Czas określony",
		"praca_okres_od": "2019-05-01",
		"praca_okres_do": "2026-05-01",
		"praca_nip": "1234567890",
		"praca_nazwa_zakladu": "ACME sp. z o.o.",
		"praca_adres_telefon": "Warszawa, 500600700",
		"praca_kwota_dochodu": "6000",
		"emerytura_wlaczone": 1,
		"emerytura_numer_swiadczenia": "EM123456",
		"emerytura_od_kiedy": "2015-01-01",
		"emerytura_kwota_dochodu": "2500",
		"renta_wlaczone": 1,
		"renta_numer_swiadczenia": "REN123456",
		"renta_od_kiedy": "2016-01-01",
		"renta_kwota_dochodu": "1800",
		"dzialalnosc_wlaczone": 1,
		"dzialalnosc_forma_opodatkowania": "inne",
		"dzialalnosc_forma_inna": "Podatek liniowy",
		"dzialalnosc_nip": "9876543210",
		"dzialalnosc_nazwa": "Firma Testowa",
		"dzialalnosc_adres": "Kraków",
		"dzialalnosc_telefon": "500700800",
		"dzialalnosc_od_kiedy": "2018-01-01",
		"dzialalnosc_kwota_dochodu": "4000",
		"gospodarstwo_wlaczone": 1,
		"gospodarstwo_nip": "1112223330",
		"gospodarstwo_od_kiedy": "2017-01-01",
		"gospodarstwo_kwota_dochodu": "1500",
		"inne_wlaczone": 1,
		"inne_1_typ": "Alimenty",
		"inne_1_kwota": "1000",
		"inne_2_typ": "Wynajem",
		"inne_2_kwota": "800",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"custom_pesel": "90010112345",
		"first_name": "Jan",
		"last_name": "Kowalski",
		"mobile_no": "500600700",
		"email": "jan@example.com",
		"custom_kod_pocztowy": "00-001",
		"custom_miasto": "Warszawa",
		"custom_ulica": "Kwiatowa",
		"custom_nr_domu": "5",
		"custom_nr_mieszkania": "12",
	}
	baza.update(nadpisania)
	return baza


def _pelny_kontekst() -> dict[str, Any]:
	"""Referencyjny kontekst — WSZYSTKIE grupy dochodu włączone, WSZYSTKIE pola
	wypełnione. Ten sam kontekst służy wszystkim testom niżej."""
	return zbuduj_kontekst_kredytu(_kredyt_wszystko_wlaczone(), _kontakt(), date(2026, 8, 15))


# ---------------------------------------------------------------------------
# K11: wyjątki od "w pełnym fixture nic nie jest puste" (patrz
# `TestPelnyFixtureBezPustychKluczy` niżej). Każda z grup poniżej to jeden
# Select z zestawem wzajemnie wykluczających się kratek w kontekście PDF-u:
# skoro Select ma zawsze DOKŁADNIE jedną wybraną wartość, wszystkie kratki
# poza tą jedną muszą wyjść `False` nawet w fixture, gdzie "wszystko jest
# włączone". `_wyjatki_checkboxow_selecta` liczy ten zbiór z mapowania
# opcja -> klucz kontekstu, nigdy nie jest wpisywany ręcznie dla
# konkretnego fixture.
# ---------------------------------------------------------------------------

_WYKSZTALCENIE_KLUCZE: dict[str, str] = {
	WYKSZTALCENIE_WYZSZE: "wyksztalcenie_wyzsze",
	WYKSZTALCENIE_SREDNIE: "wyksztalcenie_srednie",
	WYKSZTALCENIE_ZAWODOWE: "wyksztalcenie_zawodowe",
	WYKSZTALCENIE_PODSTAWOWE: "wyksztalcenie_podstawowe",
}

_STAN_CYWILNY_KLUCZE: dict[str, str] = {
	STAN_KAWALER_PANNA: "stan_kawaler_panna",
	STAN_ROZWIEDZIONY: "stan_rozwiedziony",
	STAN_MALZENSTWO_ROZDZIELNOSC: "stan_malzenstwo_rozdzielnosc",
	STAN_MALZENSTWO_WSPOLNOTA: "stan_malzenstwo_wspolnota",
	STAN_WDOWIEC_WDOWA: "stan_wdowiec_wdowa",
	STAN_SEPARACJA: "stan_separacja",
}

_PRACA_FORMA_KLUCZE: dict[str, str] = {
	FORMA_UMOWA_O_PRACE: "praca_umowa_o_prace",
	FORMA_UMOWA_ZLECENIE: "praca_zlecenie",
	FORMA_UMOWA_DZIELO: "praca_dzielo",
}

_DZIALALNOSC_FORMA_KLUCZE: dict[str, str] = {
	FORMA_RYCZALT: "dzialalnosc_ryczalt",
	FORMA_KPIR: "dzialalnosc_kpir",
	FORMA_INNE: "dzialalnosc_inne",
}

_ADRES_ZAMELDOWANIA_KLUCZE: dict[str, str] = {
	ADRES_TAK: "adres_zameldowania_tak",
	ADRES_NIE: "adres_zameldowania_nie",
}

_ADRES_KORESPONDENCJI_KLUCZE: dict[str, str] = {
	ADRES_TAK: "adres_korespondencji_tak",
	ADRES_NIE: "adres_korespondencji_nie",
}


def _wyjatki_checkboxow_selecta(mapowanie: dict[str, str], wybrana_opcja: Any) -> set[str]:
	"""Dla grupy wzajemnie wykluczających się kratek jednego Selecta
	(mapowanie wartość-opcji -> klucz kontekstu kratki) zwraca klucze
	WSZYSTKICH kratek poza tą odpowiadającą `wybrana_opcja`, te pozostają
	`False` w pełnym fixture nawet gdy "wszystko jest włączone", bo Select ma
	zawsze dokładnie jedną wybraną wartość. Wyliczone z `mapowanie`, nie
	wpisane ręcznie dla konkretnego fixture."""
	return {klucz for opcja, klucz in mapowanie.items() if opcja != wybrana_opcja}


def _wyjatki_pustych_wartosci(dane: dict[str, Any]) -> frozenset[str]:
	"""Jawna lista kluczy kontekstu, które w pełnym fixture (`_kredyt_wszystko_wlaczone`,
	w dowolnym wariancie `praca_okres`) legalnie wychodzą puste/`False` mimo
	że "wszystko jest włączone", bo są wzajemnie wykluczającym się wyborem w
	obrębie jednego Selecta, a Select ma zawsze dokładnie jedną wybraną
	wartość. Wyliczona programowo z opcji przez `_wyjatki_checkboxow_selecta`,
	nie wpisana ręcznie tam, gdzie się da.

	Jedyny ręczny wyjątek to routing `praca_okreslony_od`/`_do` vs
	`praca_nieokreslony_od`: to nie jest grupa kratek jednego Selecta, tylko
	przekierowanie JEDNEGO surowego pola (`praca_okres_od`) do jednego z
	dwóch kluczy kontekstu zależnie od `praca_okres`, patrz `_blok_praca` w
	`crm/volteo_kredyt_pdf.py`. Nie da się tego wyliczyć z listy opcji tak
	jak kratek, bo klucze docelowe różnią się nazwą, nie tylko wartością
	bool."""
	wyjatki: set[str] = set()
	wyjatki |= _wyjatki_checkboxow_selecta(_WYKSZTALCENIE_KLUCZE, dane.get("wyksztalcenie"))
	wyjatki |= _wyjatki_checkboxow_selecta(_STAN_CYWILNY_KLUCZE, dane.get("stan_cywilny"))
	wyjatki |= _wyjatki_checkboxow_selecta(_PRACA_FORMA_KLUCZE, dane.get("praca_forma"))
	wyjatki |= _wyjatki_checkboxow_selecta(
		_DZIALALNOSC_FORMA_KLUCZE, dane.get("dzialalnosc_forma_opodatkowania")
	)
	wyjatki |= _wyjatki_checkboxow_selecta(
		_ADRES_ZAMELDOWANIA_KLUCZE, dane.get("adres_zameldowania_taki_sam")
	)
	wyjatki |= _wyjatki_checkboxow_selecta(
		_ADRES_KORESPONDENCJI_KLUCZE, dane.get("adres_korespondencji_taki_sam")
	)

	if dane.get("praca_okres") == OKRES_CZAS_OKRESLONY:
		wyjatki.add("praca_nieokreslony_od")
	elif dane.get("praca_okres") == OKRES_CZAS_NIEOKRESLONY:
		wyjatki.add("praca_okreslony_od")
		wyjatki.add("praca_okreslony_do")

	return frozenset(wyjatki)


class TestPelnyFixtureBezPustychKluczy(unittest.TestCase):
	"""K11: `TestWartosciKontekstu.test_a_kazda_wartosc_referencyjnego_kontekstu_jest_str_albo_bool`
	sprawdza tylko TYP wartości, nigdy jej pustość: fixture z wycofanymi
	polami (`rodzaj_seria_numer_dokumentu`, `dzialalnosc_adres_telefon`) i
	nierozpoznawaną wartością `stan_cywilny` ("kawaler/panna" zamiast
	kanonicznego `STAN_KAWALER_PANNA`) przechodziła tamten test na zielono
	mimo ośmiu pustych kluczy kontekstu (dwa złożone pola dokumentu/firmy plus
	sześć kratek stanu cywilnego). Te testy sprawdzają pustość wprost, na obu
	wariantach `praca_okres`, z jawną listą wyjątków wyliczaną programowo
	przez `_wyjatki_pustych_wartosci`."""

	def _sprawdz_bez_pustych(
		self: "TestPelnyFixtureBezPustychKluczy",
		kontekst: dict[str, Any],
		wyjatki: frozenset[str],
	) -> None:
		for klucz, wartosc in kontekst.items():
			if klucz in wyjatki:
				continue
			with self.subTest(klucz=klucz):
				if isinstance(wartosc, bool):
					self.assertTrue(
						wartosc, f"{klucz!r} jest False mimo braku w jawnych wyjątkach"
					)
				else:
					self.assertNotEqual(
						wartosc.strip(),
						"",
						f"{klucz!r} jest puste mimo braku w jawnych wyjątkach",
					)

	def test_a_czas_okreslony_bez_pustych_kluczy_poza_wyjatkami(
		self: "TestPelnyFixtureBezPustychKluczy",
	) -> None:
		dane = _kredyt_wszystko_wlaczone()
		kontekst = zbuduj_kontekst_kredytu(dane, _kontakt(), date(2026, 8, 15))
		wyjatki = _wyjatki_pustych_wartosci(dane)
		# Bezpiecznik testu: dla tego wariantu fixture liczba wyjątków jest
		# znana i zamrożona: 3 (wykształcenie) + 5 (stan cywilny) + 2 (forma
		# zatrudnienia) + 2 (forma opodatkowania) + 1 (adres zameldowania) + 1
		# (adres korespondencji) + 1 (praca_nieokreslony_od) = 15. Gdyby
		# `_wyjatki_pustych_wartosci` kiedyś przypadkiem zwróciło pusty zbiór
		# (np. literówka w kluczu `dane.get(...)`), poniższe `assertEqual`
		# złapałoby to, zanim `_sprawdz_bez_pustych` zdążyłoby cokolwiek
		# przetestować.
		self.assertEqual(len(wyjatki), 15)
		self._sprawdz_bez_pustych(kontekst, wyjatki)

	def test_b_czas_nieokreslony_bez_pustych_kluczy_poza_wyjatkami(
		self: "TestPelnyFixtureBezPustychKluczy",
	) -> None:
		# Regresja K2/#139: przy "Czas nieokreślony" `praca_nieokreslony_od`
		# musi wyjść NIEPUSTE (martwa linia wydruku, historycznie zerowana),
		# a `praca_okreslony_od`/`_do` muszą wyjść puste, bo teraz to one są
		# wzajemnie wykluczone.
		dane = _kredyt_wszystko_wlaczone(praca_okres=OKRES_CZAS_NIEOKRESLONY)
		kontekst = zbuduj_kontekst_kredytu(dane, _kontakt(), date(2026, 8, 15))
		wyjatki = _wyjatki_pustych_wartosci(dane)
		self.assertNotIn("praca_nieokreslony_od", wyjatki)
		self.assertIn("praca_okreslony_od", wyjatki)
		self.assertIn("praca_okreslony_do", wyjatki)
		self.assertNotEqual(kontekst["praca_nieokreslony_od"].strip(), "")
		self.assertEqual(kontekst["praca_okreslony_od"], "")
		self.assertEqual(kontekst["praca_okreslony_do"], "")
		self._sprawdz_bez_pustych(kontekst, wyjatki)


class TestKlucze(unittest.TestCase):
	def test_a_kazdy_klucz_mapy_istnieje_w_kontekscie(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_kontekstu = set(kontekst.keys())
		for pole in MAPA_KREDYT:
			with self.subTest(klucz=pole.klucz):
				self.assertIn(
					pole.klucz,
					klucze_kontekstu,
					f"MAPA_KREDYT odwołuje się do klucza {pole.klucz!r}, którego nie ma "
					"w zbuduj_kontekst_kredytu()",
				)

	def test_b_kazdy_klucz_kontekstu_ma_pozycje_albo_jawny_wyjatek(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		klucze_mapy = _klucze_mapy()
		for klucz in kontekst:
			if klucz in WYJATKI_KREDYT:
				continue
			with self.subTest(klucz=klucz):
				self.assertIn(
					klucz,
					klucze_mapy,
					f"Klucz {klucz!r} nie ma żadnej pozycji w MAPA_KREDYT i nie jest w "
					"WYJATKI_KREDYT — dana po cichu zniknęłaby z wydrukowanego formularza.",
				)

	def test_c_wyjatki_i_mapa_sie_nie_pokrywaja(self: "TestKlucze") -> None:
		# Klucz nie może być jednocześnie "świadomie pominięty" i obecny w mapie —
		# to by znaczyło, że komentarz uzasadniający wyjątek jest nieaktualny.
		self.assertEqual(WYJATKI_KREDYT & _klucze_mapy(), frozenset())

	def test_d_wszystkie_wyjatki_sa_prawdziwymi_kluczami_kontekstu(self: "TestKlucze") -> None:
		kontekst = _pelny_kontekst()
		for klucz in WYJATKI_KREDYT:
			with self.subTest(klucz=klucz):
				self.assertIn(klucz, kontekst)


class TestGeometria(unittest.TestCase):
	def test_a_strona_w_zakresie(self: "TestGeometria") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.strona, 0, pole)
				self.assertLess(pole.strona, LICZBA_STRON_KREDYT, pole)

	def test_b_x_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.x, 0.0, pole)
				self.assertLessEqual(pole.x, SZEROKOSC_STRONY_PT, pole)

	def test_c_y_w_granicach_strony(self: "TestGeometria") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertGreaterEqual(pole.y, 0.0, pole)
				self.assertLessEqual(pole.y, WYSOKOSC_STRONY_PT, pole)

	def test_d_maks_szerokosc_nie_wychodzi_poza_strone(self: "TestGeometria") -> None:
		for pole in MAPA_KREDYT:
			if pole.maks_szerokosc is None:
				continue
			with self.subTest(pole=pole):
				self.assertGreater(pole.maks_szerokosc, 0.0, pole)
				self.assertLessEqual(pole.x + pole.maks_szerokosc, SZEROKOSC_STRONY_PT + 1.0, pole)

	def test_e_rozmiar_fontu_dodatni_i_sensowny(self: "TestGeometria") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertGreater(pole.rozmiar, 0.0, pole)
				self.assertLess(pole.rozmiar, 24.0, pole)


class TestStrony(unittest.TestCase):
	def test_a_puste_strony_bez_pozycji(self: "TestStrony") -> None:
		# Strony 3 i 5 (indeksy 0-based) są czystym tekstem prawnym/informacyjnym
		# — żadna pozycja `Pole` nie ma prawa tam wylądować.
		strony_z_pozycjami = {pole.strona for pole in MAPA_KREDYT}
		for strona in _STRONY_PUSTE:
			with self.subTest(strona=strona):
				self.assertNotIn(strona, strony_z_pozycjami)

	def test_b_liczba_pozycji_wg_strony(self: "TestStrony") -> None:
		# Rozkład zamrożony w docstringu `MAPA_KREDYT`: 37 + 26 + 9 na stronach
		# 0/1/2, 2 na stronie 4 (drugi podpis), zero na stronach 3 i 5.
		oczekiwane = {0: 37, 1: 26, 2: 9, 3: 0, 4: 2, 5: 0}
		for strona, liczba in oczekiwane.items():
			with self.subTest(strona=strona):
				self.assertEqual(
					len([pole for pole in MAPA_KREDYT if pole.strona == strona]), liczba
				)

	def test_c_podpis_data_dokladnie_jedna_pozycja_na_kazdej_ze_stron_podpisu(
		self: "TestStrony",
	) -> None:
		strony = {pole.strona for pole in _pozycje("podpis_data")}
		self.assertEqual(strony, _STRONY_PODPISU)
		for strona in _STRONY_PODPISU:
			with self.subTest(strona=strona):
				pozycje_na_stronie = [pole for pole in _pozycje("podpis_data") if pole.strona == strona]
				self.assertEqual(len(pozycje_na_stronie), 1)

	def test_d_podpis_imie_nazwisko_dokladnie_jedna_pozycja_na_kazdej_ze_stron_podpisu(
		self: "TestStrony",
	) -> None:
		strony = {pole.strona for pole in _pozycje("podpis_imie_nazwisko")}
		self.assertEqual(strony, _STRONY_PODPISU)
		for strona in _STRONY_PODPISU:
			with self.subTest(strona=strona):
				pozycje_na_stronie = [
					pole for pole in _pozycje("podpis_imie_nazwisko") if pole.strona == strona
				]
				self.assertEqual(len(pozycje_na_stronie), 1)


class TestRodzajIWyrownanie(unittest.TestCase):
	def test_a_rodzaj_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertIn(pole.rodzaj, ("tekst", "kratka"), pole)

	def test_b_wyrownanie_dozwolona_wartosc(self: "TestRodzajIWyrownanie") -> None:
		for pole in MAPA_KREDYT:
			with self.subTest(pole=pole):
				self.assertIn(pole.wyrownanie, ("lewo", "srodek", "prawo"), pole)

	def test_c_kratki_sa_wyrownane_do_srodka(self: "TestRodzajIWyrownanie") -> None:
		# Kratka to pojedynczy znak "X" rysowany w środku glifu kratki — mapa
		# zawsze podaje jego środek, więc wyrównanie musi być "srodek".
		for pole in MAPA_KREDYT:
			if pole.rodzaj == "kratka":
				with self.subTest(pole=pole):
					self.assertEqual(pole.wyrownanie, "srodek", pole)

	def test_d_kratki_nie_maja_maks_szerokosci(self: "TestRodzajIWyrownanie") -> None:
		# maks_szerokosc słuzy do przycinania/zawijania długich wartości tekstowych
		# — nie ma zastosowania do pojedynczego znaku "X" w kratce.
		for pole in MAPA_KREDYT:
			if pole.rodzaj == "kratka":
				with self.subTest(pole=pole):
					self.assertIsNone(pole.maks_szerokosc, pole)

	def test_e_klucze_logiczne_kontekstu_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, bool):
				continue
			for pole in _pozycje(klucz):
				with self.subTest(klucz=klucz, strona=pole.strona):
					self.assertEqual(
						pole.rodzaj,
						"kratka",
						f"{klucz!r} zwraca bool w zbuduj_kontekst_kredytu(), ale mapa oznacza go "
						f"jako {pole.rodzaj!r} na stronie {pole.strona}",
					)

	def test_f_klucze_tekstowe_kontekstu_nie_sa_kratkami_w_mapie(self: "TestRodzajIWyrownanie") -> None:
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			if not isinstance(wartosc, str):
				continue
			for pole in _pozycje(klucz):
				with self.subTest(klucz=klucz, strona=pole.strona):
					self.assertEqual(
						pole.rodzaj,
						"tekst",
						f"{klucz!r} zwraca str w zbuduj_kontekst_kredytu(), ale mapa oznacza go "
						f"jako {pole.rodzaj!r} na stronie {pole.strona}",
					)


class TestWielokrotnePozycjeIDuplikaty(unittest.TestCase):
	def test_a_zero_duplikatow_tej_samej_pozycji(self: "TestWielokrotnePozycjeIDuplikaty") -> None:
		widziane: set[tuple[str, int, float, float]] = set()
		for pole in MAPA_KREDYT:
			klucz_pozycji = (pole.klucz, pole.strona, pole.x, pole.y)
			with self.subTest(pole=pole):
				self.assertNotIn(klucz_pozycji, widziane, f"Zduplikowana pozycja: {pole}")
			widziane.add(klucz_pozycji)

	def test_b_tylko_podpisy_wystepuja_wiecej_niz_raz(self: "TestWielokrotnePozycjeIDuplikaty") -> None:
		# Jedyne dwa klucze z powtórzoną pozycją (raz na stronie 2, raz na
		# stronie 4) to `podpis_data`/`podpis_imie_nazwisko` — każdy inny klucz
		# formularza występuje dokładnie raz (formularz tabelaryczny, bez
		# powtórzonych sekcji jak w umowie).
		liczniki: dict[str, int] = {}
		for pole in MAPA_KREDYT:
			liczniki[pole.klucz] = liczniki.get(pole.klucz, 0) + 1
		wielokrotne = {klucz for klucz, ile in liczniki.items() if ile > 1}
		self.assertEqual(wielokrotne, {"podpis_data", "podpis_imie_nazwisko"})


class TestPoleDataclass(unittest.TestCase):
	def test_a_pole_jest_niemutowalny(self: "TestPoleDataclass") -> None:
		pole = Pole("test_klucz", 0, 10.0, 10.0, "tekst")
		with self.assertRaises(Exception):
			pole.x = 20.0  # type: ignore[misc]

	def test_b_mapa_nie_jest_pusta(self: "TestPoleDataclass") -> None:
		self.assertGreater(len(MAPA_KREDYT), 50)

	def test_c_liczba_pozycji_zgodna_z_dokumentacja_modulu(self: "TestPoleDataclass") -> None:
		# 74 pozycje łącznie: 37 (str. 0) + 26 (str. 1) + 9 (str. 2) + 2 (str. 4).
		self.assertEqual(len(MAPA_KREDYT), 74)


class TestWartosciKontekstu(unittest.TestCase):
	def test_a_kazda_wartosc_referencyjnego_kontekstu_jest_str_albo_bool(
		self: "TestWartosciKontekstu",
	) -> None:
		# Bramka pasa-i-szelek — pełniejsza wersja tego kontraktu żyje w
		# `crm/test_volteo_kredyt_pdf.py`; tutaj sprawdzamy to tanim kosztem na
		# tym samym referencyjnym kontekście używanym przez testy mapy.
		kontekst = _pelny_kontekst()
		for klucz, wartosc in kontekst.items():
			with self.subTest(klucz=klucz):
				self.assertIsInstance(wartosc, (str, bool))
				self.assertIsNotNone(wartosc)


if __name__ == "__main__":
	unittest.main()
