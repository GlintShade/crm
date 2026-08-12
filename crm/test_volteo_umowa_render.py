# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm/volteo_umowa_render.py` (`unittest`, NIE pytest — nie istnieje dla
Pythona 3.14 użytego lokalnie do tych testów).

`reportlab` i `pypdf` NIE są zainstalowane w systemowym Pythonie — do testów
użyj interpretera z osobnego wirtualnego środowiska, w którym obie biblioteki
są zainstalowane (zob. raport zadania po instrukcję instalacji).

Część testów potrzebuje PRAWDZIWEGO pliku TTF, żeby zweryfikować realne
renderowanie (w tym polskie znaki diakrytyczne) — `_zarejestruj_font()` w
module docelowym sprawdza wyłącznie ścieżki Debiana (`/usr/share/fonts/...`),
których na tej maszynie deweloperskiej (macOS) nie ma, więc testy renderujące
PODMIENIAJĄ `_SCIEZKA_LIBERATION`/`_SCIEZKA_DEJAVU` (`unittest.mock.patch.object`)
na pierwszy znaleziony font z `_KANDYDACI_FONTU_TESTOWEGO` poniżej — lista
zawiera zarówno docelowe ścieżki Debiana (na wypadek uruchomienia na Linuksie),
jak i standardowy font systemowy macOS (`Arial.ttf` z `/System/Library/Fonts/
Supplemental/`, obecny na każdym Macu, więc nie wymaga niczego poza systemem).
Gdy żaden kandydat nie istnieje, testy renderujące są pomijane (`skipTest`) —
nie fałszują wyniku podstawianiem niewalidnych bajtów jako TTF.

Od zadania „umowa-szablony-typy” `zloz_umowe()`/`sciezka_wbudowanego_szablonu()`
wymagają jawnego kodu rodzaju umowy (`"PV"`/`"PVME"`/`"ME"`) — testy end-to-end
pętlą się po `crm.volteo_umowa_render.SZABLONY` (rejestrowi, nie po nazwach
funkcji poszczególnych map), tak jak `crm/test_volteo_umowa_mapa.py`.
"""

import hashlib
import io
import unittest
import warnings
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

from pypdf import PdfReader

from crm import volteo_umowa_render as renderer
from crm.volteo_umowa_mapa import Pole
from crm.volteo_umowa_pdf import zbuduj_kontekst
from crm.volteo_umowa_render import (
	SZABLONY,
	_dopasuj_rozmiar,
	_narysuj_warstwe_strony,
	_przytnij,
	_zarejestruj_font,
	sciezka_wbudowanego_szablonu,
	zloz_umowe,
)

_KANDYDACI_FONTU_TESTOWEGO: tuple[Path, ...] = (
	# Ścieżki Debiana — te same, których szuka `_zarejestruj_font()` w module
	# docelowym; gdyby testy uruchomiono na obrazie/Linuksie z zainstalowanymi
	# pakietami, użyją dokładnie tego samego pliku co produkcja.
	Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
	Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
	# macOS deweloperski (zob. `CLAUDE.md` tego repo — środowisko lokalne to Mac):
	# font systemowy, obecny domyślnie na każdym Macu, z pełnym pokryciem
	# polskich znaków diakrytycznych — wystarczający do realnego testu
	# renderowania bez instalowania niczego dodatkowego.
	Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)


def _znajdz_font_testowy() -> Path | None:
	"""Zwraca pierwszy istniejący plik TTF z `_KANDYDACI_FONTU_TESTOWEGO`, albo `None`."""
	for kandydat in _KANDYDACI_FONTU_TESTOWEGO:
		if kandydat.is_file():
			return kandydat
	return None


def _umowa(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"adres_zam_jak_montaz": "Nie",
		"adres_zam_ulica": "Kwiatowa",
		"adres_zam_nr_domu": "5",
		"adres_zam_nr_mieszkania": "",
		"adres_zam_kod": "00-001",
		"adres_zam_miasto": "Warszawa",
		"adres_montaz_ulica": "Polna",
		"adres_montaz_nr_domu": "10",
		"adres_montaz_nr_mieszkania": "",
		"adres_montaz_kod": "02-002",
		"adres_montaz_miasto": "Kraków",
		"typ_budynku": "Jednorodzinny",
		"powierzchnia_prog": "powyżej 300 m²",
		"powierzchnia_m2": Decimal("350"),
		"finansowanie": "Kredyt + gotówka",
		"wklad_wlasny_pln": Decimal("5000"),
		"kwota_kredytu_pln": Decimal("35236"),
		"internet": "Wi-Fi",
		"instalacja_odgromowa": "Tak",
		"moc_przylaczeniowa_kw": Decimal("8.5"),
		"liczba_faz": "3",
		"przekop_gruntowy": "Tak",
		"dodatkowy_kabel_m": 12,
		"ppoz_wymagane": 1,
		"istniejaca_pv": "Tak",
		"istniejaca_pv_moc_inwertera_kw": Decimal("4.0"),
		"istniejaca_pv_moc_kwp": Decimal("3.5"),
		"istniejaca_pv_producent_inwertera": "Fronius",
		"zgoda_kontakt_telefoniczny": 1,
		"zgoda_dzialania_promocyjne": 1,
		"zgoda_realizacja_przed_odstapieniem": 1,
	}
	baza.update(nadpisania)
	return baza


def _deal(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"name": "PRO/PVME/26/1000",
		"deal_value": Decimal("43454.88"),
		"custom_netto": Decimal("40236.0"),
		"custom_pv_power_kwp": Decimal("5.0"),
		"custom_panele": 10,
		"custom_falownik": "Sigenergy TP2 6 kW",
		"custom_bateria": "Sigenergy 12 kWh (6+6)",
		"custom_pojemnosc_kwh": Decimal("12.0"),
		"custom_konstrukcja": "Dach skośny - blacha",
		"custom_install_address": "",
		"custom_install_city": "",
		"custom_install_postal_code": "",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		# Nazwisko dobrane celowo jako sztuczny test kompletności fontu — nie
		# jest prawdziwym polskim nazwiskiem, ale zawiera wszystkie 9 polskich
		# znaków diakrytycznych (ą ć ę ł ń ó ś ż ź) w jednym ciągu, więc jego
		# obecność w wyekstrahowanym tekście PDF-u jednoznacznie potwierdza,
		# że font poprawnie obsługuje kodowanie Unicode, nie tylko WinAnsi.
		"first_name": "Łukasz",
		"last_name": "Ążćęłńóśżź",
		"custom_pesel": "90010112345",
		"mobile_no": "500600700",
		"email": "lukasz@example.com",
	}
	baza.update(nadpisania)
	return baza


def _zestaw() -> list[dict[str, Any]]:
	return [
		{"typ": "Falownik", "nazwa": "Sigenergy TP2 6 kW", "ilosc": 1},
		{"typ": "Panele PV", "nazwa": "Panel PV", "ilosc": 10},
	]


def _komponenty() -> list[dict[str, Any]]:
	return [
		{
			"kategoria": "Falownik",
			"nazwa": "Sigenergy",
			"model": "TP2 6 kW",
			"producent": "Sigenergy",
			"moc_kw": Decimal("6.0"),
			"gwarancja_lat": 12,
		},
		{
			"kategoria": "Magazyn energii",
			"nazwa": "Sigenergy",
			"model": "12 kWh (6+6)",
			"producent": "Sigenergy",
			"moc_kw": Decimal("6.0"),
			"pojemnosc_kwh": Decimal("12"),
			"gwarancja_lat": 10,
		},
	]


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"panel_producent": "Longi",
		"panel_model": "Hi-MO 6",
		"panel_moc_wp": 440,
		"panel_gwarancja_lat": 25,
	}
	baza.update(nadpisania)
	return baza


def _pelny_kontekst() -> dict[str, Any]:
	"""Kontekst z WSZYSTKIMI polami wypełnionymi — żaden klucz nie wypada jako
	pusty z powodu reguły "zero/brak = pustka" w `zbuduj_kontekst()`. Ten sam
	kontekst nadaje się do wszystkich trzech szablonów: `zbuduj_kontekst()` nie
	zna pojęcia "szablon", zawsze zwraca pełny zestaw kluczy."""
	return zbuduj_kontekst(
		_umowa(), _deal(), _kontakt(), _zestaw(), _komponenty(), _stale(), date(2026, 8, 6)
	)


class TestSumaKontrolna(unittest.TestCase):
	"""Bezpiecznik sprawdzany PRZED rejestracją fontu — te testy nie potrzebują
	prawdziwego pliku TTF, bo `zloz_umowe()` przerywa wcześniej."""

	def test_a_niezgodna_suma_rzuca_wyjatek_z_czytelnym_komunikatem(self: "TestSumaKontrolna") -> None:
		# Kod dowolny — bezpiecznik sumy kontrolnej działa identycznie dla
		# każdego wpisu `SZABLONY`; "PVME" wybrany jako reprezentatywny.
		szablon_niepoprawny = b"to nie jest prawdziwy PDF szablonu umowy"
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_umowe({}, szablon_niepoprawny, "PVME")
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("SHA-256", komunikat)
		self.assertIn("wymaga ponownego pomiaru", komunikat)

	def test_b_pusty_plik_tez_rzuca_ten_sam_czytelny_wyjatek(self: "TestSumaKontrolna") -> None:
		with self.assertRaises(ValueError):
			zloz_umowe({}, b"", "PVME")

	def test_c_kazdy_wbudowany_szablon_ma_zgodna_sume_ze_swoja_mapa(self: "TestSumaKontrolna") -> None:
		# Sanity check niezależny od reszty testów, dla WSZYSTKICH trzech
		# szablonów: gdyby ktoś podmienił plik w `crm/szablony/` bez przeliczenia
		# sumy w rejestrze `SZABLONY`, ten test czerwienieje jako pierwszy —
		# zanim jakikolwiek test renderujący zdąży się mylnie przepuścić przez
		# bezpiecznik.
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				zawartosc = sciezka_wbudowanego_szablonu(kod).read_bytes()
				self.assertEqual(hashlib.sha256(zawartosc).hexdigest(), szablon.sha256)

	def test_d_szablon_jednego_rodzaju_odrzucony_pod_kodem_innego_rodzaju(
		self: "TestSumaKontrolna",
	) -> None:
		# Regresja przeciw pomyleniu szablonów: bajty PV podane pod kodem "ME"
		# nie mogą przejść bezpiecznika tylko dlatego, że OBA są prawdziwymi,
		# poprawnymi plikami PDF — suma kontrolna musi się zgadzać z DOKŁADNIE
		# tym kodem, pod którym plik jest przekazywany. Komunikat ma nazwać
		# oczekiwany (nie podany) szablon, żeby dało się od razu zdiagnozować
		# pomyłkę.
		bajty_pv = sciezka_wbudowanego_szablonu("PV").read_bytes()
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_umowe({}, bajty_pv, "ME")
		komunikat = str(kontekst_bledu.exception)
		self.assertIn(SZABLONY["ME"].nazwa_pliku, komunikat)
		self.assertIn("ME", komunikat)


class TestSciezkaWbudowanegoSzablonu(unittest.TestCase):
	def test_a_nieznany_kod_rzuca_wyjatek(self: "TestSciezkaWbudowanegoSzablonu") -> None:
		with self.assertRaises(ValueError):
			sciezka_wbudowanego_szablonu("CP")

	def test_b_znane_kody_zwracaja_istniejace_pliki(self: "TestSciezkaWbudowanegoSzablonu") -> None:
		for kod in SZABLONY:
			with self.subTest(kod=kod):
				self.assertTrue(sciezka_wbudowanego_szablonu(kod).is_file())


class TestRejestracjaFontu(unittest.TestCase):
	"""Testuje `_zarejestruj_font()` w izolacji, podmieniając ścieżki modułu —
	bez wołania `zloz_umowe()`, więc te testy nie zależą od poprawności mapy
	ani szablonu."""

	def setUp(self: "TestRejestracjaFontu") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest(
				"Brak lokalnego pliku TTF do testów rejestracji fontu — sprawdzeni "
				f"kandydaci: {[str(p) for p in _KANDYDACI_FONTU_TESTOWEGO]}"
			)
		self._font_testowy = font

	def test_a_liberation_obecny_uzywany_bez_ostrzezenia(self: "TestRejestracjaFontu") -> None:
		with (
			mock.patch.object(renderer, "_SCIEZKA_LIBERATION", self._font_testowy),
			warnings.catch_warnings(record=True) as zlapane,
		):
			warnings.simplefilter("always")
			nazwa = _zarejestruj_font()
		self.assertEqual(nazwa, renderer._NAZWA_FONTU)
		self.assertEqual(len(zlapane), 0, "Liberation Sans obecny — nie powinno być żadnego ostrzeżenia")

	def test_b_liberation_brak_dejavu_obecny_jawne_ostrzezenie(self: "TestRejestracjaFontu") -> None:
		sciezka_nieistniejaca = Path("/nie/istnieje/LiberationSans-Regular.ttf")
		with (
			mock.patch.object(renderer, "_SCIEZKA_LIBERATION", sciezka_nieistniejaca),
			mock.patch.object(renderer, "_SCIEZKA_DEJAVU", self._font_testowy),
			self.assertWarns(RuntimeWarning) as zlapane,
		):
			nazwa = _zarejestruj_font()
		self.assertEqual(nazwa, renderer._NAZWA_FONTU)
		komunikat = str(zlapane.warning)
		self.assertIn("Liberation Sans nie znaleziono", komunikat)
		self.assertIn("DejaVu Sans", komunikat)

	def test_c_zaden_font_niedostepny_rzuca_wyjatek(self: "TestRejestracjaFontu") -> None:
		sciezka_nieistniejaca_1 = Path("/nie/istnieje/LiberationSans-Regular.ttf")
		sciezka_nieistniejaca_2 = Path("/nie/istnieje/DejaVuSans.ttf")
		with (
			mock.patch.object(renderer, "_SCIEZKA_LIBERATION", sciezka_nieistniejaca_1),
			mock.patch.object(renderer, "_SCIEZKA_DEJAVU", sciezka_nieistniejaca_2),
			self.assertRaises(RuntimeError) as kontekst_bledu,
		):
			_zarejestruj_font()
		self.assertIn("Nie znaleziono ani Liberation Sans", str(kontekst_bledu.exception))


class TestDopasowanieRozmiaruIPrzycinanie(unittest.TestCase):
	"""Testuje `_dopasuj_rozmiar()`/`_przytnij()` jako czyste funkcje (bez
	tworzenia żadnego PDF-u) — wymagają tylko zarejestrowanego fontu, żeby
	`pdfmetrics.stringWidth()` miał czym mierzyć."""

	def setUp(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest("Brak lokalnego pliku TTF do testów dopasowania rozmiaru fontu")
		with mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font):
			self._nazwa_fontu = _zarejestruj_font()

	def test_a_tekst_mieszczacy_sie_nie_zmienia_rozmiaru(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		rozmiar = _dopasuj_rozmiar("ABC", self._nazwa_fontu, 10.0, maks_szerokosc=1000.0)
		self.assertEqual(rozmiar, 10.0)

	def test_b_zbyt_szeroki_tekst_zmniejsza_rozmiar(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		tekst_dlugi = "Bardzo długi tekst, który na pewno nie zmieści się w wąskiej rubryce"
		rozmiar = _dopasuj_rozmiar(tekst_dlugi, self._nazwa_fontu, 10.0, maks_szerokosc=60.0)
		self.assertLess(rozmiar, 10.0)
		self.assertGreaterEqual(rozmiar, renderer._MIN_ROZMIAR_FONTU_PT)

	def test_c_rozmiar_nigdy_nie_spada_ponizej_minimum(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		tekst_ekstremalnie_dlugi = "X" * 500
		rozmiar = _dopasuj_rozmiar(tekst_ekstremalnie_dlugi, self._nazwa_fontu, 10.0, maks_szerokosc=20.0)
		self.assertEqual(rozmiar, renderer._MIN_ROZMIAR_FONTU_PT)

	def test_d_brak_maks_szerokosci_zwraca_rozmiar_bazowy(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		rozmiar = _dopasuj_rozmiar("cokolwiek", self._nazwa_fontu, 10.0, maks_szerokosc=None)
		self.assertEqual(rozmiar, 10.0)

	def test_e_mieszczacy_sie_tekst_nie_jest_przycinany(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		tekst = _przytnij("ABC", self._nazwa_fontu, 10.0, maks_szerokosc=1000.0)
		self.assertEqual(tekst, "ABC")

	def test_f_niemieszczacy_sie_nawet_przy_minimum_jest_przycinany_z_wielokropkiem(
		self: "TestDopasowanieRozmiaruIPrzycinanie",
	) -> None:
		tekst_ekstremalnie_dlugi = "X" * 500
		rozmiar = renderer._MIN_ROZMIAR_FONTU_PT
		wynik = _przytnij(tekst_ekstremalnie_dlugi, self._nazwa_fontu, rozmiar, maks_szerokosc=20.0)
		self.assertTrue(wynik.endswith("…"))
		self.assertLess(len(wynik), len(tekst_ekstremalnie_dlugi))

	def test_g_brak_maks_szerokosci_nigdy_nie_przycina(self: "TestDopasowanieRozmiaruIPrzycinanie") -> None:
		tekst_ekstremalnie_dlugi = "X" * 500
		wynik = _przytnij(tekst_ekstremalnie_dlugi, self._nazwa_fontu, 10.0, maks_szerokosc=None)
		self.assertEqual(wynik, tekst_ekstremalnie_dlugi)


class TestRysowanieWarstwy(unittest.TestCase):
	"""Testuje `_narysuj_warstwe_strony()` w izolacji: wynikowy jednostronicowy
	PDF zawiera WYŁĄCZNIE to, co narysowaliśmy (żadnej treści oryginału), więc
	sprawdzenie wyekstrahowanego tekstu jest jednoznaczne — bez szumu z reszty
	dokumentu."""

	def setUp(self: "TestRysowanieWarstwy") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest("Brak lokalnego pliku TTF do testów rysowania warstwy")
		with mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font):
			self._nazwa_fontu = _zarejestruj_font()

	def _tekst_warstwy(self: "TestRysowanieWarstwy", kontekst: dict[str, Any], pozycje: tuple[Pole, ...]) -> str:
		pdf_bajty = _narysuj_warstwe_strony(kontekst, pozycje, 596.0, 842.0, self._nazwa_fontu)
		return PdfReader(io.BytesIO(pdf_bajty)).pages[0].extract_text()

	def test_a_pusty_string_nie_rysuje_niczego(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("pole_testowe", 0, 100.0, 100.0, "tekst"),)
		tekst = self._tekst_warstwy({"pole_testowe": ""}, pozycje)
		self.assertEqual(tekst.strip(), "")

	def test_b_brakujacy_klucz_nie_rysuje_niczego(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("pole_testowe", 0, 100.0, 100.0, "tekst"),)
		tekst = self._tekst_warstwy({}, pozycje)
		self.assertEqual(tekst.strip(), "")

	def test_c_niepusty_string_jest_rysowany(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("pole_testowe", 0, 100.0, 100.0, "tekst"),)
		tekst = self._tekst_warstwy({"pole_testowe": "Kowalski"}, pozycje)
		self.assertIn("Kowalski", tekst)

	def test_d_kratka_true_rysuje_x(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("zgoda", 0, 100.0, 100.0, "kratka", wyrownanie="srodek"),)
		tekst = self._tekst_warstwy({"zgoda": True}, pozycje)
		self.assertIn("X", tekst)

	def test_e_kratka_false_nie_rysuje_x(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("zgoda", 0, 100.0, 100.0, "kratka", wyrownanie="srodek"),)
		tekst = self._tekst_warstwy({"zgoda": False}, pozycje)
		self.assertEqual(tekst.strip(), "")

	def test_f_kratka_brak_klucza_nie_rysuje_x(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("zgoda", 0, 100.0, 100.0, "kratka", wyrownanie="srodek"),)
		tekst = self._tekst_warstwy({}, pozycje)
		self.assertEqual(tekst.strip(), "")

	def test_g_polskie_znaki_diakrytyczne_przechodza_i_sa_odczytywalne(self: "TestRysowanieWarstwy") -> None:
		pozycje = (Pole("nazwisko", 0, 100.0, 100.0, "tekst", maks_szerokosc=400.0),)
		wartosc = "ąćęłńóśżź ĄĆĘŁŃÓŚŻŹ"
		tekst = self._tekst_warstwy({"nazwisko": wartosc}, pozycje)
		self.assertIn(wartosc, tekst)

	def test_h_strona_bez_pozycji_jest_pusta(self: "TestRysowanieWarstwy") -> None:
		tekst = self._tekst_warstwy({"cokolwiek": "wartosc"}, ())
		self.assertEqual(tekst.strip(), "")


class TestZlozUmowePelnyPipeline(unittest.TestCase):
	"""Testy end-to-end przez publiczne `zloz_umowe()`, na prawdziwych szablonach
	z `crm/szablony/`. Wymagają prawdziwego pliku TTF (podmienianego przez
	`_SCIEZKA_LIBERATION`) — bez niego pomijane."""

	def setUp(self: "TestZlozUmowePelnyPipeline") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest("Brak lokalnego pliku TTF do testów end-to-end")
		self._patch_fontu = mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font)
		self._patch_fontu.start()
		self.addCleanup(self._patch_fontu.stop)
		# Szablon PVME jest ścieżką "na żywo" (jedyna dotąd wdrożona w produkcji)
		# — testy specyficzne dla PVME (test_a/b/c niżej) trzymają się go
		# bezpośrednio, tak jak przed wprowadzeniem trzech szablonów; test
		# pełnego pipeline'u dla WSZYSTKICH trzech (`test_d`) czyta swój
		# szablon per-kod z `SZABLONY` w pętli.
		self._szablon_pvme = sciezka_wbudowanego_szablonu("PVME").read_bytes()

	def test_a_pusty_kontekst_ma_tyle_samo_stron_i_zero_naniesionego_tekstu(
		self: "TestZlozUmowePelnyPipeline",
	) -> None:
		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon_pvme))
		tekst_oryginalu = [strona.extract_text() for strona in czytnik_oryginalu.pages]

		wynik_bajty = zloz_umowe({}, self._szablon_pvme, "PVME")
		czytnik_wyniku = PdfReader(io.BytesIO(wynik_bajty))

		self.assertEqual(len(czytnik_wyniku.pages), SZABLONY["PVME"].liczba_stron)
		self.assertEqual(len(czytnik_oryginalu.pages), SZABLONY["PVME"].liczba_stron)
		for indeks, (strona_oryg, strona_wynik) in enumerate(
			zip(tekst_oryginalu, czytnik_wyniku.pages, strict=True)
		):
			self.assertEqual(
				strona_oryg,
				strona_wynik.extract_text(),
				f"Strona {indeks + 1}: pusty kontekst nie powinien zmieniać wyekstrahowanego tekstu",
			)

	def test_b_pelny_kontekst_ma_wartosci_na_wlasciwych_stronach_pvme(
		self: "TestZlozUmowePelnyPipeline",
	) -> None:
		kontekst = _pelny_kontekst()
		wynik_bajty = zloz_umowe(kontekst, self._szablon_pvme, "PVME")
		strony = PdfReader(io.BytesIO(wynik_bajty)).pages
		tekst_wg_strony = [strona.extract_text() for strona in strony]

		# Strona 1 (indeks 0): komparycja — PESEL i nazwisko klienta.
		self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[0])
		self.assertIn(kontekst["klient_imie_nazwisko"], tekst_wg_strony[0])

		# Strona 2 (indeks 1): wynagrodzenie brutto. `_kwota()` w `crm/volteo_umowa_pdf.py`
		# grupuje tysiące spacją NIEROZDZIELAJĄCĄ (U+00A0) — ekstrakcja tekstu przez
		# `pypdf` normalizuje ją do zwykłej spacji, więc porównujemy po normalizacji
		# obu stron zamiast zakładać, że ekstrakcja zachowuje dokładny znak NBSP.
		self.assertIn(
			kontekst["wynagrodzenie_brutto"].replace("\xa0", " "),
			tekst_wg_strony[1].replace("\xa0", " "),
		)

		# Strona 5 (indeks 4): Załącznik 1a — producent/model modułów PV.
		self.assertIn(kontekst["panel_producent_model"], tekst_wg_strony[4])

		# Strona 6 (indeks 5): Załącznik 1b — producent/model baterii.
		self.assertIn(kontekst["bateria_producent_model"], tekst_wg_strony[5])

		# Strona 9 (indeks 8): koniec Załącznika nr 4 (RODO) — linia podpisu klienta.
		self.assertIn(kontekst["rodo_data_imie_nazwisko"], tekst_wg_strony[8])

		# Strona 18 (indeks 17): Pełnomocnictwo OSD — PESEL i nazwisko ponownie.
		self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[17])
		self.assertIn(kontekst["klient_imie_nazwisko"], tekst_wg_strony[17])

	def test_c_niezgodna_suma_kontrolna_nadal_dziala_z_prawdziwym_fontem(
		self: "TestZlozUmowePelnyPipeline",
	) -> None:
		# Regresja: upewnia się, że bezpiecznik sumy kontrolnej nie jest
		# przypadkiem ominięty, gdy font JEST dostępny (w przeciwieństwie do
		# `TestSumaKontrolna`, gdzie font nigdy nie wchodzi w grę).
		with self.assertRaises(ValueError):
			zloz_umowe(_pelny_kontekst(), b"nieprawidlowy szablon", "PVME")

	def test_d_pelny_pipeline_dla_kazdego_szablonu(self: "TestZlozUmowePelnyPipeline") -> None:
		# Test end-to-end dla WSZYSTKICH trzech szablonów: liczba stron wyniku,
		# wartości kontekstu na oczekiwanych stronach (per szablon — treść i
		# układ różnią się), i — kluczowe dla PV/ME — że wartość istotna
		# wyłącznie dla DRUGIEGO produktu (bateria dla PV, panele dla ME) NIE
		# pojawia się NIGDZIE w wyniku, bo dany szablon nie ma dla niej miejsca.
		kontekst = _pelny_kontekst()
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				szablon_bajty = sciezka_wbudowanego_szablonu(kod).read_bytes()
				wynik_bajty = zloz_umowe(kontekst, szablon_bajty, kod)
				strony = PdfReader(io.BytesIO(wynik_bajty)).pages
				self.assertEqual(len(strony), szablon.liczba_stron)
				tekst_wg_strony = [strona.extract_text() for strona in strony]
				pelny_tekst = "\n".join(tekst_wg_strony)

				if kod == "PVME":
					self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[0])
					self.assertIn(
						kontekst["wynagrodzenie_brutto"].replace("\xa0", " "),
						tekst_wg_strony[1].replace("\xa0", " "),
					)
					self.assertIn(kontekst["panel_producent_model"], tekst_wg_strony[4])
					self.assertIn(kontekst["bateria_producent_model"], tekst_wg_strony[5])
					self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[17])
				elif kod == "PV":
					self.assertIn(
						kontekst["wynagrodzenie_brutto"].replace("\xa0", " "),
						tekst_wg_strony[0].replace("\xa0", " "),
					)
					self.assertIn(kontekst["powierzchnia_m2"], tekst_wg_strony[1])
					self.assertIn(kontekst["panel_producent_model"], tekst_wg_strony[4])
					self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[13])
					# Szablon PV nie ma Załącznika magazynu — wartość baterii nie
					# ma gdzie się wydrukować, nigdzie na żadnej stronie.
					self.assertNotIn(kontekst["bateria_producent_model"], pelny_tekst)
				elif kod == "ME":
					self.assertIn(
						kontekst["wynagrodzenie_brutto"].replace("\xa0", " "),
						tekst_wg_strony[1].replace("\xa0", " "),
					)
					self.assertIn(kontekst["bateria_producent_model"], tekst_wg_strony[4])
					self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[13])
					# Szablon ME nie ma sekcji fotowoltaicznej — wartość panelu
					# nie ma gdzie się wydrukować, nigdzie na żadnej stronie.
					self.assertNotIn(kontekst["panel_producent_model"], pelny_tekst)
				else:
					self.fail(f"Nieoczekiwany kod w rejestrze SZABLONY: {kod!r}")


if __name__ == "__main__":
	unittest.main()
