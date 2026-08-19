# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm/volteo_oswiadczenie.py` (`unittest`, NIE pytest — nie istnieje dla
Pythona 3.14 użytego lokalnie do tych testów).

`reportlab` i `pypdf` SĄ dostępne w systemowym Pythonie tej maszyny — testy
uruchamia się zwykłym `python3 -m unittest crm.test_volteo_oswiadczenie`, bez
osobnego wirtualnego środowiska (to samo dotyczy `crm/test_volteo_umowa_render.py`).

Testy generujące PDF potrzebują PRAWDZIWEGO pliku TTF, żeby zweryfikować
realne renderowanie (w tym polskie znaki diakrytyczne) — `_zarejestruj_font()`
w `crm/volteo_umowa_render.py` (reużytej stąd) sprawdza wyłącznie ścieżki
Debiana, których na tej maszynie deweloperskiej (macOS) nie ma, więc — dokładnie
jak w `crm/test_volteo_umowa_render.py` — testy renderujące PODMIENIAJĄ
`_SCIEZKA_LIBERATION` (`unittest.mock.patch.object` na module `renderer`) na
pierwszy znaleziony font z `_KANDYDACI_FONTU_TESTOWEGO`. Gdy żaden kandydat
nie istnieje, testy renderujące są pomijane (`skipTest`) — nie fałszują
wyniku podstawianiem niewalidnych bajtów jako TTF.

Ekstrakcja tekstu polskich znaków diakrytycznych przez `pypdf` działa tu
niezawodnie (zweryfikowane ręcznie przed napisaniem tych testów: nazwisko
z wszystkimi 9 polskimi znakami diakrytycznymi wraca z `extract_text()`
bez zniekształceń), więc testy PDF-u asercjonują na wyekstrahowanym tekście
wprost — bez osłabiania do samej długości bajtów.
"""

import io
import unittest
from pathlib import Path
from unittest import mock

from pypdf import PdfReader

from crm import volteo_umowa_render as renderer
from crm.volteo_oswiadczenie import (
	TRESC_OSWIADCZENIA,
	imiona_zgodne,
	normalizuj_imie,
	wersja_tresci,
	zbuduj_pdf,
	zbuduj_tresc,
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


class TestWersjaTresci(unittest.TestCase):
	def test_a_hash_stabilny_miedzy_wywolaniami(self: "TestWersjaTresci") -> None:
		self.assertEqual(wersja_tresci(), wersja_tresci())

	def test_b_hash_ma_64_znaki_szesnastkowe(self: "TestWersjaTresci") -> None:
		hash_wartosc = wersja_tresci()
		self.assertEqual(len(hash_wartosc), 64)
		int(hash_wartosc, 16)  # rzuca ValueError, jeśli to nie hex — sam brak wyjątku jest asercją

	def test_c_hashuje_szablon_nie_spersonalizowany_render(self: "TestWersjaTresci") -> None:
		import hashlib

		oczekiwany = hashlib.sha256(TRESC_OSWIADCZENIA.encode("utf-8")).hexdigest()
		self.assertEqual(wersja_tresci(), oczekiwany)


class TestZbudujTresc(unittest.TestCase):
	def test_a_oba_placeholdery_podstawione(self: "TestZbudujTresc") -> None:
		tresc = zbuduj_tresc("Jan Kowalski", "2026-08-19")
		self.assertIn("Jan Kowalski", tresc)
		self.assertIn("2026-08-19", tresc)
		self.assertNotIn("{imie_nazwisko}", tresc)
		self.assertNotIn("{data}", tresc)

	def test_b_puste_imie_rzuca_value_error(self: "TestZbudujTresc") -> None:
		with self.assertRaises(ValueError):
			zbuduj_tresc("", "2026-08-19")

	def test_c_imie_z_samych_bialych_znakow_rzuca_value_error(self: "TestZbudujTresc") -> None:
		with self.assertRaises(ValueError):
			zbuduj_tresc("   ", "2026-08-19")

	def test_d_komunikat_bledu_jest_czytelny(self: "TestZbudujTresc") -> None:
		with self.assertRaises(ValueError) as kontekst_bledu:
			zbuduj_tresc("", "2026-08-19")
		komunikat = str(kontekst_bledu.exception)
		self.assertIn("imienia", komunikat.lower())


class TestTrescSzablonu(unittest.TestCase):
	"""Sprawdza sam surowy szablon `TRESC_OSWIADCZENIA` — niezależnie od
	`zbuduj_tresc()` — żeby regresja w treści dokumentu (np. przypadkowe
	usunięcie klauzuli przy edycji) czerwieniła się nawet bez podstawiania
	placeholderów."""

	def test_a_oba_placeholdery_obecne_w_surowym_szablonie(self: "TestTrescSzablonu") -> None:
		self.assertIn("{imie_nazwisko}", TRESC_OSWIADCZENIA)
		self.assertIn("{data}", TRESC_OSWIADCZENIA)

	def test_b_nowa_klauzula_rzetelnosci_informacji_obecna(self: "TestTrescSzablonu") -> None:
		self.assertIn("realnego terminu realizacji montażu", TRESC_OSWIADCZENIA)

	def test_c_kara_umowna_obecna(self: "TestTrescSzablonu") -> None:
		self.assertIn("kary umownej", TRESC_OSWIADCZENIA)
		self.assertIn("5.000,00", TRESC_OSWIADCZENIA)

	def test_d_pieciu_punktow_numerowanych_obecnych(self: "TestTrescSzablonu") -> None:
		for numer in ("1.", "2.", "3.", "4.", "5."):
			with self.subTest(numer=numer):
				self.assertIn(numer, TRESC_OSWIADCZENIA)


class TestNormalizujImie(unittest.TestCase):
	def test_a_zwija_wielokrotne_spacje(self: "TestNormalizujImie") -> None:
		self.assertEqual(normalizuj_imie("Jan   Kowalski"), normalizuj_imie("Jan Kowalski"))

	def test_b_ignoruje_wielkosc_liter(self: "TestNormalizujImie") -> None:
		self.assertEqual(normalizuj_imie("Jan Kowalski"), normalizuj_imie("JAN KOWALSKI"))

	def test_c_przycina_brzegowe_biale_znaki(self: "TestNormalizujImie") -> None:
		self.assertEqual(normalizuj_imie("  Jan Kowalski  "), normalizuj_imie("Jan Kowalski"))

	def test_d_nie_transliteruje_znakow_diakrytycznych(self: "TestNormalizujImie") -> None:
		self.assertNotEqual(normalizuj_imie("Jozef Nowak"), normalizuj_imie("Józef Nowak"))


class TestImionaZgodne(unittest.TestCase):
	def test_a_dokladnie_ten_sam_string_zgodny(self: "TestImionaZgodne") -> None:
		self.assertTrue(imiona_zgodne("Jan Kowalski", "Jan Kowalski"))

	def test_b_rozna_wielkosc_liter_zgodna(self: "TestImionaZgodne") -> None:
		self.assertTrue(imiona_zgodne("jan kowalski", "Jan Kowalski"))

	def test_c_dodatkowe_i_wielokrotne_spacje_zgodne(self: "TestImionaZgodne") -> None:
		self.assertTrue(imiona_zgodne("  Jan   Kowalski ", "Jan Kowalski"))

	def test_d_niezgodne_znaki_diakrytyczne_nie_sa_zgodne(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("Jozef Nowak", "Józef Nowak"))

	def test_e_rozne_nazwiska_nie_sa_zgodne(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("Jan Kowalski", "Jan Nowak"))

	def test_f_puste_wpisane_nie_jest_zgodne(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("", "Jan Kowalski"))

	def test_g_puste_oczekiwane_nie_jest_zgodne(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("Jan Kowalski", ""))

	def test_h_oba_puste_nie_sa_zgodne(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("", ""))

	def test_i_same_biale_znaki_traktowane_jak_puste(self: "TestImionaZgodne") -> None:
		self.assertFalse(imiona_zgodne("   ", "Jan Kowalski"))


class TestZbudujPdf(unittest.TestCase):
	"""Testy end-to-end generatora PDF-u. Wymagają prawdziwego pliku TTF
	(podmienianego przez `_SCIEZKA_LIBERATION` na module `renderer`, dokładnie
	jak w `crm/test_volteo_umowa_render.py`) — bez niego pomijane."""

	def setUp(self: "TestZbudujPdf") -> None:
		font = _znajdz_font_testowy()
		if font is None:
			self.skipTest(
				"Brak lokalnego pliku TTF do testów generowania PDF-u — sprawdzeni "
				f"kandydaci: {[str(p) for p in _KANDYDACI_FONTU_TESTOWEGO]}"
			)
		self._patch_fontu = mock.patch.object(renderer, "_SCIEZKA_LIBERATION", font)
		self._patch_fontu.start()
		self.addCleanup(self._patch_fontu.stop)

	def test_a_zwraca_bajty_zaczynajace_sie_od_naglowka_pdf(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		self.assertIsInstance(pdf, bytes)
		self.assertTrue(pdf.startswith(b"%PDF"))

	def test_b_dlugosc_wieksza_niz_2000_bajtow(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		self.assertGreater(len(pdf), 2000)

	def test_c_tytul_obecny_w_wyekstrahowanym_tekscie(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn("Oświadczenie", tekst)

	def test_d_imie_z_polskimi_znakami_diakrytycznymi_odczytywalne(self: "TestZbudujPdf") -> None:
		# Nazwisko dobrane celowo jako sztuczny test kompletności fontu (zob.
		# ten sam wzorzec w `crm/test_volteo_umowa_render.py`) — zawiera
		# wystarczająco dużo polskich znaków diakrytycznych, żeby jego obecność
		# w wyekstrahowanym tekście jednoznacznie potwierdziła poprawne
		# kodowanie Unicode.
		imie_testowe = "Żaneta Łódźka"
		pdf = zbuduj_pdf(imie_testowe, "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn(imie_testowe, tekst)

	def test_e_data_obecna_w_wyekstrahowanym_tekscie(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn("2026-08-19", tekst)

	def test_f_nowa_klauzula_rzetelnosci_informacji_obecna_w_pdf(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn("realnego terminu realizacji montażu", tekst)

	def test_g_kara_umowna_obecna_w_pdf(self: "TestZbudujPdf") -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn("5.000,00", tekst)

	def test_h_puste_imie_rzuca_value_error_przed_generowaniem(self: "TestZbudujPdf") -> None:
		with self.assertRaises(ValueError):
			zbuduj_pdf("", "2026-08-19")

	def test_i_dokument_moze_rozlac_sie_na_wiecej_niz_jedna_strone(self: "TestZbudujPdf") -> None:
		# Pełna treść (5 punktów + wstęp + podpis) jest zbyt długa na jedną
		# stronę A4 przy czcionce 10pt — dokument MA prawo rozlać się na 2
		# strony; funkcja nigdy nie przycina treści, żeby wymusić jedną stronę.
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		liczba_stron = len(PdfReader(io.BytesIO(pdf)).pages)
		self.assertGreaterEqual(liczba_stron, 2)

	def test_j_caly_tekst_widoczny_na_wszystkich_stronach_zawiera_wszystkie_punkty(
		self: "TestZbudujPdf",
	) -> None:
		pdf = zbuduj_pdf("Jan Kowalski", "2026-08-19")
		tekst = _wyodrebnij_tekst(pdf)
		self.assertIn("Utrzymywania w tajemnicy", tekst)
		self.assertIn("wyłączną własność", tekst)
		self.assertIn("bezpiecznego przechowywania", tekst)
		self.assertIn("Podpisano elektronicznie", tekst)


def _wyodrebnij_tekst(pdf: bytes) -> str:
	"""Ekstraktuje i skleja tekst wszystkich stron `pdf` (bajty) przez `pypdf` —
	wspólny helper testów PDF-u, żeby nie powtarzać tego samego trzywierszowego
	wzorca w każdym teście."""
	czytnik = PdfReader(io.BytesIO(pdf))
	return "\n".join(strona.extract_text() for strona in czytnik.pages)


if __name__ == "__main__":
	unittest.main()
