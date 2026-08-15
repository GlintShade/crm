# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm/volteo_kredyt_render.py` (`unittest`, NIE pytest — nie istnieje dla
Pythona 3.14 użytego lokalnie do tych testów).

Mirror struktury `crm/test_volteo_umowa_render.py` — przeczytaj tamten
docstring dla pełnego uzasadnienia podejścia (venv z `reportlab`/`pypdf`,
podmiana ścieżek fontu przez `unittest.mock.patch.object`, `skipTest` gdy
brak lokalnego TTF). `zloz_kredyt()` deleguje do `_zloz_dokument()` w
`crm.volteo_umowa_render`, więc rejestracja fontu nadal czyta moduł-globalne
`_SCIEZKA_LIBERATION`/`_SCIEZKA_DEJAVU` z TAMTEGO modułu — testy tutaj
podmieniają je identycznie jak testy umowy, nie ścieżki w `volteo_kredyt_render`
(ten moduł ich w ogóle nie ma).
"""

import hashlib
import io
import unittest
import warnings
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

from pypdf import PdfReader

from crm import volteo_umowa_render as renderer
from crm.volteo_kredyt_pdf import zbuduj_kontekst_kredytu
from crm.volteo_kredyt_render import SZABLON_KREDYT, sciezka_szablonu_kredytu, zloz_kredyt
from crm.volteo_umowa_render import sciezka_wbudowanego_szablonu

_KANDYDACI_FONTU_TESTOWEGO: tuple[Path, ...] = (
	# Ścieżki Debiana — te same, których szuka `_zarejestruj_font()` w
	# `crm.volteo_umowa_render`; gdyby testy uruchomiono na obrazie/Linuksie z
	# zainstalowanymi pakietami, użyją dokładnie tego samego pliku co produkcja.
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


def _kredyt_pusty() -> dict[str, Any]:
	"""Pusty rekord źródłowy — `zbuduj_kontekst_kredytu({}, {}, dzis)` na tym
	zwraca same puste stringi/`False` (zob. `crm/test_volteo_kredyt_pdf.py`),
	poza `podpis_data`, która liczy się zawsze z parametru `dzis`, nie z
	rekordu."""
	return {}


def _kredyt_pelny(**nadpisania: Any) -> dict[str, Any]:
	"""Kompletny wniosek kredytowy z WSZYSTKIMI grupami dochodu włączonymi —
	realistyczne polskie wartości z polskimi znakami diakrytycznymi, żeby
	pokryć każdą stronę mapy (`crm.volteo_kredyt_mapa.MAPA_KREDYT`)."""
	baza: dict[str, Any] = {
		"miejsce_urodzenia": "Wrocław",
		"rodzaj_seria_numer_dokumentu": "Dowód osobisty XYZ654321",
		"data_wydania_dokumentu": "2019-03-10",
		"data_waznosci_dokumentu": "2029-03-10",
		"adres_zameldowania_taki_sam": "Nie",
		"adres_zameldowania": "ul. Świętokrzyska 14/3, 25-406 Kielce",
		"adres_korespondencji_taki_sam": "Nie",
		"adres_korespondencji": "ul. Żeromskiego 9, 25-370 Kielce",
		"wyksztalcenie": "wyższe",
		"stan_cywilny": "W związku małżeńskim wspólnota majątkowa",
		"liczba_osob_na_utrzymaniu": "2",
		"kwota_800_plus": "1600",
		"dochod_wspolmalzonka": "4500",
		"zrodlo_dochodu_malzonka": "Umowa o pracę",
		"oplaty_miesieczne": "1800",
		"suma_zobowiazan": "12000",
		"numer_rachunku": "PL61109010140000071219812874",
		"praca_wlaczone": 1,
		"praca_forma": "Umowa o pracę",
		"praca_data_zatrudnienia": "2015-06-01",
		"praca_okres": "Czas nieokreślony",
		"praca_okres_od": "2015-06-01",
		"praca_okres_do": "",
		"praca_nip": "6551234567",
		"praca_nazwa_zakladu": "Elektrownia Świętokrzyska Sp. z o.o.",
		"praca_adres_telefon": "Kielce, ul. Żelazna 3, 41 555 44 33",
		"praca_kwota_dochodu": "7200",
		"emerytura_wlaczone": 1,
		"emerytura_numer_swiadczenia": "EMK/998877",
		"emerytura_od_kiedy": "2010-02-01",
		"emerytura_kwota_dochodu": "2100",
		"renta_wlaczone": 1,
		"renta_numer_swiadczenia": "REN/112233",
		"renta_od_kiedy": "2012-09-15",
		"renta_kwota_dochodu": "1500",
		"dzialalnosc_wlaczone": 1,
		"dzialalnosc_forma_opodatkowania": "ryczałt",
		"dzialalnosc_forma_inna": "",
		"dzialalnosc_nip": "6559998877",
		"dzialalnosc_nazwa": "Usługi Elektryczne Żółć-Jaśkiewicz",
		"dzialalnosc_adres_telefon": "Kielce, ul. Ogrodowa 8, 41 222 11 00",
		"dzialalnosc_od_kiedy": "2018-04-01",
		"dzialalnosc_kwota_dochodu": "3600",
		"gospodarstwo_wlaczone": 1,
		"gospodarstwo_nip": "6551122334",
		"gospodarstwo_od_kiedy": "2005-01-01",
		"gospodarstwo_kwota_dochodu": "900",
		"inne_wlaczone": 1,
		"inne_1_typ": "Alimenty",
		"inne_1_kwota": "600",
		"inne_2_typ": "Najem lokalu",
		"inne_2_kwota": "1200",
	}
	baza.update(nadpisania)
	return baza


def _kontakt_pelny(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"custom_pesel": "85030112345",
		"first_name": "Łukasz",
		# Nazwisko dobrane celowo (jak w `_kontakt()` w `test_volteo_umowa_render.py`)
		# jako sztuczny test kompletności fontu: zawiera kilka polskich znaków
		# diakrytycznych naraz (Ż ó ł ć ś), więc jego obecność w wyekstrahowanym
		# tekście PDF-u potwierdza poprawną obsługę kodowania Unicode.
		"last_name": "Żółć-Jaśkiewicz",
		"mobile_no": "600700800",
		"email": "lukasz@example.com",
		"custom_kod_pocztowy": "25-406",
		"custom_miasto": "Kielce",
		"custom_ulica": "Sienkiewicza",
		"custom_nr_domu": "22",
		"custom_nr_mieszkania": "4",
	}
	baza.update(nadpisania)
	return baza


class TestSumaKontrolna(unittest.TestCase):
	"""Bezpiecznik sprawdzany PRZED rejestracją fontu — te testy nie potrzebują
	prawdziwego pliku TTF, bo `zloz_kredyt()` przerywa wcześniej."""

	def test_a_niezgodna_suma_rzuca_wyjatek_z_czytelnym_komunikatem(self: "TestSumaKontrolna") -> None:
		szablon_niepoprawny = b"to nie jest prawdziwy PDF formularza kredytowego"
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_kredyt({}, szablon_niepoprawny)
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("SHA-256", komunikat)
		self.assertIn("wymaga ponownego pomiaru", komunikat)
		self.assertIn(SZABLON_KREDYT.sha256, komunikat)
		self.assertIn(hashlib.sha256(szablon_niepoprawny).hexdigest(), komunikat)

	def test_b_pusty_plik_tez_rzuca_ten_sam_czytelny_wyjatek(self: "TestSumaKontrolna") -> None:
		with self.assertRaises(ValueError):
			zloz_kredyt({}, b"")

	def test_c_wbudowany_szablon_ma_zgodna_sume_ze_swoja_mapa(self: "TestSumaKontrolna") -> None:
		zawartosc = sciezka_szablonu_kredytu().read_bytes()
		self.assertEqual(hashlib.sha256(zawartosc).hexdigest(), SZABLON_KREDYT.sha256)

	def test_d_szablon_umowy_jest_odrzucony_przez_bramke_kredytu(self: "TestSumaKontrolna") -> None:
		# Regresja przeciw pomyleniu szablonów: PV/ME/PVME są też prawdziwymi,
		# poprawnymi plikami PDF, ale nie tym jednym, dla którego zmierzono
		# `MAPA_KREDYT` — bezpiecznik musi je odrzucić tak samo jak losowe bajty.
		bajty_umowy_pv = sciezka_wbudowanego_szablonu("PV").read_bytes()
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_kredyt({}, bajty_umowy_pv)
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("SHA-256", komunikat)
		self.assertIn(SZABLON_KREDYT.nazwa_pliku, komunikat)


class TestSciezkaSzablonuKredytu(unittest.TestCase):
	def test_a_wskazuje_na_istniejacy_plik(self: "TestSciezkaSzablonuKredytu") -> None:
		self.assertTrue(sciezka_szablonu_kredytu().is_file())

	def test_b_nazwa_pliku_zgodna_z_szablonem(self: "TestSciezkaSzablonuKredytu") -> None:
		self.assertEqual(sciezka_szablonu_kredytu().name, SZABLON_KREDYT.nazwa_pliku)


class TestZlozKredytPelnyPipeline(unittest.TestCase):
	"""Testy end-to-end przez publiczne `zloz_kredyt()`, na prawdziwym szablonie
	z `crm/szablony/formularz_kredytowy.pdf`. Wymagają prawdziwego pliku TTF
	(podmienianego przez `_SCIEZKA_LIBERATION` w `crm.volteo_umowa_render`,
	bo tam mieszka `_zarejestruj_font()`) — bez niego pomijane."""

	def setUp(self: "TestZlozKredytPelnyPipeline") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest(
				"Brak lokalnego pliku TTF do testów renderu formularza kredytowego — "
				f"sprawdzeni kandydaci: {[str(p) for p in _KANDYDACI_FONTU_TESTOWEGO]}"
			)
		self._patch_fontu = mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font)
		self._patch_fontu.start()
		self.addCleanup(self._patch_fontu.stop)
		self._szablon = sciezka_szablonu_kredytu().read_bytes()

	def test_a_pusty_kontekst_zmienia_tylko_strony_z_podpisem(
		self: "TestZlozKredytPelnyPipeline",
	) -> None:
		# `zbuduj_kontekst_kredytu({}, {}, dzis)` zwraca same puste stringi/`False`
		# — JEDYNA wartość, która mimo to się drukuje, to `podpis_data` (liczona
		# zawsze z parametru `dzis`, niezależnie od rekordu, zob.
		# `crm/volteo_kredyt_pdf.py::zbuduj_kontekst_kredytu`), obecna na stronach
		# z indeksem 2 i 4 (`MAPA_KREDYT` ma tam po jednej pozycji `podpis_data`).
		# Strony 0, 1, 3, 5 nie mają więc żadnej zmiany wobec oryginału.
		dzis = date(2026, 8, 15)
		kontekst = zbuduj_kontekst_kredytu(_kredyt_pusty(), {}, dzis)

		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon))
		tekst_oryginalu = [strona.extract_text() for strona in czytnik_oryginalu.pages]

		wynik_bajty = zloz_kredyt(kontekst, self._szablon)
		czytnik_wyniku = PdfReader(io.BytesIO(wynik_bajty))

		self.assertEqual(len(czytnik_wyniku.pages), 6)
		self.assertEqual(len(czytnik_oryginalu.pages), 6)

		for indeks in (0, 1, 3, 5):
			self.assertEqual(
				tekst_oryginalu[indeks],
				czytnik_wyniku.pages[indeks].extract_text(),
				f"Strona {indeks + 1}: pusty kontekst (poza podpis_data) nie powinien "
				"zmieniać wyekstrahowanego tekstu",
			)

		for indeks in (2, 4):
			tekst_strony = czytnik_wyniku.pages[indeks].extract_text()
			self.assertNotEqual(
				tekst_oryginalu[indeks],
				tekst_strony,
				f"Strona {indeks + 1}: podpis_data powinna była się narysować",
			)
			self.assertIn(kontekst["podpis_data"], tekst_strony)

	def test_b_pelny_kontekst_ma_wartosci_na_wlasciwych_stronach(
		self: "TestZlozKredytPelnyPipeline",
	) -> None:
		dzis = date(2026, 8, 15)
		kontekst = zbuduj_kontekst_kredytu(_kredyt_pelny(), _kontakt_pelny(), dzis)
		wynik_bajty = zloz_kredyt(kontekst, self._szablon)
		strony = PdfReader(io.BytesIO(wynik_bajty)).pages
		self.assertEqual(len(strony), 6)
		tekst_wg_strony = [strona.extract_text() for strona in strony]

		# Strona 1 (indeks 0): dane podstawowe — PESEL i nazwisko z diakrytykami.
		self.assertIn(kontekst["pesel"], tekst_wg_strony[0])
		self.assertIn(kontekst["nazwisko"], tekst_wg_strony[0])
		self.assertIn("Żółć-Jaśkiewicz", tekst_wg_strony[0])

		# Strona 2 (indeks 1): §4 UMOWA O PRACĘ — nazwa zakładu pracy.
		self.assertIn(kontekst["praca_nazwa_zakladu"], tekst_wg_strony[1])

		# Strona 3 (indeks 2): §8 GOSPODARSTWO ROLNE + pierwsza linia podpisu.
		self.assertIn(kontekst["gospodarstwo_nip"], tekst_wg_strony[2])
		self.assertIn(kontekst["podpis_imie_nazwisko"], tekst_wg_strony[2])

		# Strona 5 (indeks 4): druga, osobna linia podpisu — te same klucze
		# `podpis_data`/`podpis_imie_nazwisko`, druga pozycja w mapie.
		self.assertIn(kontekst["podpis_imie_nazwisko"], tekst_wg_strony[4])

		# Strony 4 i 6 (indeksy 3 i 5): czysty tekst prawny bez pól formularza
		# (`_STRONA_4`/`_STRONA_6` w `MAPA_KREDYT` są puste) — więc żadna wartość
		# kontekstu z resztek innych stron nie mogła się tam wydrukować, i tekst
		# jest identyczny z oryginałem.
		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon))
		tekst_oryginalu = [strona.extract_text() for strona in czytnik_oryginalu.pages]
		for indeks in (3, 5):
			self.assertEqual(
				tekst_oryginalu[indeks],
				tekst_wg_strony[indeks],
				f"Strona {indeks + 1}: brak pozycji w mapie, więc brak jakiegokolwiek narzutu",
			)

	def test_c_niezgodna_suma_kontrolna_nadal_dziala_z_prawdziwym_fontem(
		self: "TestZlozKredytPelnyPipeline",
	) -> None:
		# Regresja: bezpiecznik sumy kontrolnej nie jest przypadkiem ominięty,
		# gdy font JEST dostępny (w przeciwieństwie do `TestSumaKontrolna`, gdzie
		# font nigdy nie wchodzi w grę).
		kontekst = zbuduj_kontekst_kredytu(_kredyt_pelny(), _kontakt_pelny(), date(2026, 8, 15))
		with self.assertRaises(ValueError):
			zloz_kredyt(kontekst, b"nieprawidlowy szablon")


class TestOstrzezenieBrakuFontuNieWymagaTtf(unittest.TestCase):
	"""Sanity: `_narysuj_warstwe_strony` woła się przez `_zloz_dokument`
	niezależnie od modułu wywołującego — sam import `volteo_kredyt_render` nie
	powinien wymagać obecności żadnego fontu ani rzucać ostrzeżeń."""

	def test_a_sam_import_nie_ostrzega(self: "TestOstrzezenieBrakuFontuNieWymagaTtf") -> None:
		with warnings.catch_warnings(record=True) as zlapane:
			warnings.simplefilter("always")
			import importlib

			import crm.volteo_kredyt_render as modul

			importlib.reload(modul)
		self.assertEqual(len(zlapane), 0)


if __name__ == "__main__":
	unittest.main()
