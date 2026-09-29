# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm/volteo_umowa_render_cp.py` (`unittest`, NIE pytest — nie istnieje dla
Pythona 3.14 użytego lokalnie do tych testów).

Mirror struktury `crm/test_volteo_kredyt_render.py` — przeczytaj tamten
docstring dla pełnego uzasadnienia podejścia (venv z `reportlab`/`pypdf`,
podmiana ścieżek fontu przez `unittest.mock.patch.object`, `skipTest` gdy
brak lokalnego TTF). `zloz_umowe_cp()` deleguje do `_zloz_dokument()` w
`crm.volteo_umowa_render`, więc rejestracja fontu nadal czyta moduł-globalne
`_SCIEZKA_LIBERATION`/`_SCIEZKA_DEJAVU` z TAMTEGO modułu — testy tutaj
podmieniają je identycznie jak testy umowy/kredytu, nie ścieżki w
`volteo_umowa_render_cp` (ten moduł ich w ogóle nie ma)."""

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
from crm.volteo_umowa_pdf_cp import zbuduj_kontekst_cp
from crm.volteo_umowa_render import sciezka_wbudowanego_szablonu
from crm.volteo_umowa_render_cp import SZABLON_CP, sciezka_szablonu_cp, zloz_umowe_cp

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


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"umowa1_netto": "1600",
		"umowa1_brutto": "1968",
		"umowa2_netto": "2400",
		"umowa2_brutto": "2952",
	}
	baza.update(nadpisania)
	return baza


def _kontakt_pelny(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"custom_pesel": "85030112345",
		"first_name": "Małgorzata",
		# Nazwisko dobrane celowo (jak w `_kontakt_pelny()` w
		# `test_volteo_kredyt_render.py`) jako sztuczny test kompletności
		# fontu: zawiera kilka polskich znaków diakrytycznych naraz, więc jego
		# obecność w wyekstrahowanym tekście PDF-u potwierdza poprawną obsługę
		# kodowania Unicode.
		"last_name": "Żółkiewska-Brzęczyszczykiewicz",
		"mobile_no": "600700800",
		"email": "malgorzata@example.com",
		"custom_kod_pocztowy": "25-406",
		"custom_miasto": "Kielce",
		"custom_ulica": "Świętokrzyska",
		"custom_nr_domu": "14",
		"custom_nr_mieszkania": "3",
	}
	baza.update(nadpisania)
	return baza


def _umowa_pelna(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"wynagrodzenie_wariant": "2",
		"zgoda_przetwarzanie_danych": 1,
		"zgoda_kontakt_telefoniczny": 1,
		"zgoda_dzialania_promocyjne": 1,
	}
	baza.update(nadpisania)
	return baza


def _deal_pelny(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {"name": "PRO/CP/26/0042"}
	baza.update(nadpisania)
	return baza


class TestSumaKontrolna(unittest.TestCase):
	"""Bezpiecznik sprawdzany PRZED rejestracją fontu — te testy nie potrzebują
	prawdziwego pliku TTF, bo `zloz_umowe_cp()` przerywa wcześniej."""

	def test_a_niezgodna_suma_rzuca_wyjatek_z_czytelnym_komunikatem(self: "TestSumaKontrolna") -> None:
		szablon_niepoprawny = b"to nie jest prawdziwy PDF umowy obslugi dotacji"
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_umowe_cp({}, szablon_niepoprawny)
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("SHA-256", komunikat)
		self.assertIn("wymaga ponownego pomiaru", komunikat)
		self.assertIn(SZABLON_CP.sha256, komunikat)
		self.assertIn(hashlib.sha256(szablon_niepoprawny).hexdigest(), komunikat)

	def test_b_pusty_plik_tez_rzuca_ten_sam_czytelny_wyjatek(self: "TestSumaKontrolna") -> None:
		with self.assertRaises(ValueError):
			zloz_umowe_cp({}, b"")

	def test_c_wbudowany_szablon_ma_zgodna_sume_ze_swoja_mapa(self: "TestSumaKontrolna") -> None:
		zawartosc = sciezka_szablonu_cp().read_bytes()
		self.assertEqual(hashlib.sha256(zawartosc).hexdigest(), SZABLON_CP.sha256)

	def test_d_szablon_umowy_pv_jest_odrzucony_przez_bramke_cp(self: "TestSumaKontrolna") -> None:
		# Regresja przeciw pomyleniu szablonów: PV jest też prawdziwym,
		# poprawnym plikiem PDF, ale nie tym jednym, dla którego zmierzono
		# `MAPA_CP` — bezpiecznik musi go odrzucić tak samo jak losowe bajty.
		bajty_umowy_pv = sciezka_wbudowanego_szablonu("PV").read_bytes()
		with self.assertRaises(ValueError) as kontekst_bledu:
			zloz_umowe_cp({}, bajty_umowy_pv)
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("SHA-256", komunikat)
		self.assertIn(SZABLON_CP.nazwa_pliku, komunikat)


class TestSciezkaSzablonuCp(unittest.TestCase):
	def test_a_wskazuje_na_istniejacy_plik(self: "TestSciezkaSzablonuCp") -> None:
		self.assertTrue(sciezka_szablonu_cp().is_file())

	def test_b_nazwa_pliku_zgodna_z_szablonem(self: "TestSciezkaSzablonuCp") -> None:
		self.assertEqual(sciezka_szablonu_cp().name, SZABLON_CP.nazwa_pliku)


class TestZlozUmoweCpPelnyPipeline(unittest.TestCase):
	"""Testy end-to-end przez publiczne `zloz_umowe_cp()`, na prawdziwym
	szablonie z `crm/szablony/umowa_cp_obsluga_dotacji.pdf`. Wymagają
	prawdziwego pliku TTF (podmienianego przez `_SCIEZKA_LIBERATION` w
	`crm.volteo_umowa_render`, bo tam mieszka `_zarejestruj_font()`) — bez
	niego pomijane."""

	def setUp(self: "TestZlozUmoweCpPelnyPipeline") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest(
				"Brak lokalnego pliku TTF do testów renderu umowy CP — "
				f"sprawdzeni kandydaci: {[str(p) for p in _KANDYDACI_FONTU_TESTOWEGO]}"
			)
		self._patch_fontu = mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font)
		self._patch_fontu.start()
		self.addCleanup(self._patch_fontu.stop)
		self._szablon = sciezka_szablonu_cp().read_bytes()

	def test_a_pusty_kontekst_zmienia_tylko_strony_z_podpisem(
		self: "TestZlozUmoweCpPelnyPipeline",
	) -> None:
		# `zbuduj_kontekst_cp({}, {}, {}, {}, dzis)` zwraca same puste
		# stringi/`False` — JEDYNE wartości, które mimo to się drukują, to
		# `data_zawarcia` (liczona zawsze z parametru `dzis`) na str. 1
		# (indeks 0) oraz `podpis_wykonawca` (stała "PROENERGY", niezależna od
		# rekordu) na str. 4 (indeks 3). Strony 2, 3, 5, 6 (indeksy 1, 2, 4, 5)
		# nie mają więc żadnej zmiany wobec oryginału — na str. 5 (indeks 4)
		# `podpis_zamawiajacy` wypada pusty (klient_imie_nazwisko pusty), a na
		# str. 6 (indeks 5) `data_i_podpis_zamawiajacy` to sama data, niepusta.
		dzis = date(2026, 9, 29)
		kontekst = zbuduj_kontekst_cp({}, {}, {}, {}, dzis)

		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon))
		tekst_oryginalu = [strona.extract_text() for strona in czytnik_oryginalu.pages]

		wynik_bajty = zloz_umowe_cp(kontekst, self._szablon)
		czytnik_wyniku = PdfReader(io.BytesIO(wynik_bajty))

		self.assertEqual(len(czytnik_wyniku.pages), 6)
		self.assertEqual(len(czytnik_oryginalu.pages), 6)

		for indeks in (1, 2, 4):
			self.assertEqual(
				tekst_oryginalu[indeks],
				czytnik_wyniku.pages[indeks].extract_text(),
				f"Strona {indeks + 1}: pusty kontekst nie powinien zmieniać wyekstrahowanego tekstu",
			)

		tekst_strona_1 = czytnik_wyniku.pages[0].extract_text()
		self.assertNotEqual(tekst_oryginalu[0], tekst_strona_1, "Strona 1: data_zawarcia powinna się narysować")
		self.assertIn(kontekst["data_zawarcia"], tekst_strona_1)

		tekst_strona_4 = czytnik_wyniku.pages[3].extract_text()
		self.assertNotEqual(
			tekst_oryginalu[3], tekst_strona_4, "Strona 4: podpis_wykonawca powinien się narysować"
		)
		self.assertIn("PROENERGY", tekst_strona_4)

		tekst_strona_6 = czytnik_wyniku.pages[5].extract_text()
		self.assertNotEqual(
			tekst_oryginalu[5], tekst_strona_6, "Strona 6: data_i_podpis_zamawiajacy powinna się narysować"
		)
		self.assertIn(kontekst["data_zawarcia"], tekst_strona_6)

	def test_b_pelny_kontekst_ma_wartosci_na_wlasciwych_stronach(
		self: "TestZlozUmoweCpPelnyPipeline",
	) -> None:
		dzis = date(2026, 9, 29)
		kontekst = zbuduj_kontekst_cp(_umowa_pelna(), _deal_pelny(), _kontakt_pelny(), _stale(), dzis)
		wynik_bajty = zloz_umowe_cp(kontekst, self._szablon)
		strony = PdfReader(io.BytesIO(wynik_bajty)).pages
		self.assertEqual(len(strony), 6)
		tekst_wg_strony = [strona.extract_text() for strona in strony]

		# Strona 1 (indeks 0): komparycja — nr umowy, PESEL i nazwisko z diakrytykami.
		self.assertIn(kontekst["umowa_nr"], tekst_wg_strony[0])
		self.assertIn(kontekst["klient_pesel"], tekst_wg_strony[0])
		self.assertIn("Żółkiewska-Brzęczyszczykiewicz", tekst_wg_strony[0])

		# Strona 2 (indeks 1): §4 Wynagrodzenie, wariant "2" — kwota "2 400,00".
		# pypdf normalizuje NBSP (U+00A0) do zwykłej spacji przy ekstrakcji
		# tekstu (ten sam trik co `crm/test_volteo_umowa_render.py`) — porównanie
		# po `.replace("\xa0", " ")` obu stron zamiast zakładać, że ekstrakcja
		# zachowuje dokładny znak NBSP.
		self.assertIn(kontekst["wynagrodzenie_netto"].replace("\xa0", " "), tekst_wg_strony[1].replace("\xa0", " "))
		self.assertIn(kontekst["wynagrodzenie_brutto"].replace("\xa0", " "), tekst_wg_strony[1].replace("\xa0", " "))

		# Strona 3 (indeks 2): brak pozycji w mapie — tekst identyczny z oryginałem.
		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon))
		tekst_oryginalu = [strona.extract_text() for strona in czytnik_oryginalu.pages]
		self.assertEqual(
			tekst_oryginalu[2],
			tekst_wg_strony[2],
			"Strona 3: brak pozycji w mapie, więc brak jakiegokolwiek narzutu",
		)

		# Strona 4 (indeks 3): oba podpisy umowy głównej. Nazwisko jest długie
		# (test diakrytyków) i `maks_szerokosc` na str. 5 (indeks 4, węższa
		# kolumna) go przycina (`_przytnij` w `volteo_umowa_render.py`, poprawne
		# zachowanie generatora) — sprawdzamy więc niedwuznaczny PREFIKS
		# ("MAŁGORZATA"), nie cały string, żeby test nie zakładał, gdzie dokładnie
		# przycinanie zadziała.
		self.assertIn("MAŁGORZATA", tekst_wg_strony[3])
		self.assertIn(kontekst["podpis_wykonawca"], tekst_wg_strony[3])

		# Strona 5 (indeks 4): Załącznik nr 1 — trzy zgody (kratki) + podpis
		# Zamawiającego (druga pozycja tego klucza w mapie).
		self.assertIn("MAŁGORZATA", tekst_wg_strony[4])

		# Strona 6 (indeks 5): Załącznik nr 2 — data i podpis.
		self.assertIn(kontekst["data_i_podpis_zamawiajacy"].split(", ")[0], tekst_wg_strony[5])
		self.assertIn("MAŁGORZATA", tekst_wg_strony[5])

	def test_c_niezgodna_suma_kontrolna_nadal_dziala_z_prawdziwym_fontem(
		self: "TestZlozUmoweCpPelnyPipeline",
	) -> None:
		# Regresja: bezpiecznik sumy kontrolnej nie jest przypadkiem ominięty,
		# gdy font JEST dostępny.
		kontekst = zbuduj_kontekst_cp(_umowa_pelna(), _deal_pelny(), _kontakt_pelny(), _stale(), date(2026, 9, 29))
		with self.assertRaises(ValueError):
			zloz_umowe_cp(kontekst, b"nieprawidlowy szablon")

	def test_d_wszystkie_trzy_kratki_zgod_widoczne_przy_wlaczonych_zgodach(
		self: "TestZlozUmoweCpPelnyPipeline",
	) -> None:
		# Regresja geometrii kratek: str. 5 (indeks 4) z wszystkimi trzema
		# zgodami włączonymi musi różnić się od oryginału (trzy "X" narysowane
		# w środku glifów "☐"), a z wszystkimi wyłączonymi — być identyczna.
		dzis = date(2026, 9, 29)
		kontekst_wlaczone = zbuduj_kontekst_cp(_umowa_pelna(), _deal_pelny(), _kontakt_pelny(), _stale(), dzis)
		wynik_wlaczone = zloz_umowe_cp(kontekst_wlaczone, self._szablon)
		tekst_wlaczone = PdfReader(io.BytesIO(wynik_wlaczone)).pages[4].extract_text()

		kontekst_wylaczone = zbuduj_kontekst_cp(
			_umowa_pelna(
				zgoda_przetwarzanie_danych=0,
				zgoda_kontakt_telefoniczny=0,
				zgoda_dzialania_promocyjne=0,
			),
			_deal_pelny(),
			_kontakt_pelny(),
			_stale(),
			dzis,
		)
		wynik_wylaczone = zloz_umowe_cp(kontekst_wylaczone, self._szablon)
		tekst_wylaczone = PdfReader(io.BytesIO(wynik_wylaczone)).pages[4].extract_text()

		self.assertNotEqual(tekst_wlaczone, tekst_wylaczone)
		self.assertEqual(tekst_wlaczone.count("X"), tekst_wylaczone.count("X") + 3)

	def test_e_brak_wariantu_nie_drukuje_zadnej_kwoty(
		self: "TestZlozUmoweCpPelnyPipeline",
	) -> None:
		dzis = date(2026, 9, 29)
		kontekst = zbuduj_kontekst_cp(
			_umowa_pelna(wynagrodzenie_wariant=""), _deal_pelny(), _kontakt_pelny(), _stale(), dzis
		)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "")
		self.assertEqual(kontekst["wynagrodzenie_brutto"], "")
		wynik_bajty = zloz_umowe_cp(kontekst, self._szablon)
		tekst_strona_2 = PdfReader(io.BytesIO(wynik_bajty)).pages[1].extract_text()

		czytnik_oryginalu = PdfReader(io.BytesIO(self._szablon))
		tekst_oryginalu_strona_2 = czytnik_oryginalu.pages[1].extract_text()
		self.assertEqual(tekst_strona_2, tekst_oryginalu_strona_2)


class TestOstrzezenieBrakuFontuNieWymagaTtf(unittest.TestCase):
	"""Sanity: `_narysuj_warstwe_strony` woła się przez `_zloz_dokument`
	niezależnie od modułu wywołującego — sam import `volteo_umowa_render_cp`
	nie powinien wymagać obecności żadnego fontu ani rzucać ostrzeżeń."""

	def test_a_sam_import_nie_ostrzega(self: "TestOstrzezenieBrakuFontuNieWymagaTtf") -> None:
		with warnings.catch_warnings(record=True) as zlapane:
			warnings.simplefilter("always")
			import importlib

			import crm.volteo_umowa_render_cp as modul

			importlib.reload(modul)
		self.assertEqual(len(zlapane), 0)


if __name__ == "__main__":
	unittest.main()
