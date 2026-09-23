# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy trzech nowych szablonów PDF-u umowy PODWÓJNEJ (dwóch Zamawiających)
i ich map-szkieletów (`crm/volteo_umowa_mapa_pv2.py`, `_me2.py`, `_pvme2.py`).

Ten plik jest CELOWO osobny od `crm/test_volteo_umowa_mapa.py`. Tamten plik
pętla się po `crm.volteo_umowa_render.SZABLONY` (trzy dotychczasowe, JEDNO-
osobowe warianty PV/PVME/ME) i sprawdza dwukierunkowy kontrakt między mapą a
`zbuduj_kontekst()` — ten kontrakt nie ma tu jeszcze żadnej treści do
sprawdzenia, bo mapy podwójne (`MAPA_PV2`/`MAPA_ME2`/`MAPA_PVME2`) są w tym
zadaniu (issue #165) świadomie PUSTE; ich faktyczny pomiar jest przedmiotem
issue #166, a rejestracja w `SZABLONY` — przedmiotem issue #167. Dopisywanie
tu asercji kluczy do pustej mapy nie miałoby sensu, dopóki mapa nie istnieje.

Zamiast tego ten plik sprawdza to, co JEST przedmiotem #165: (1) trzy nowe
pliki PDF istnieją w repo i są dokładnie tymi plikami, które podaje właściciel
(suma SHA-256 zgodna ze stałą `SHA256_SZABLONU_*2` w odpowiednim module mapy),
(2) liczba stron każdego pliku zgadza się ze stałą `LICZBA_STRON_*2`, (3) [SEC]
bezpiecznik zakresu zadania: żaden z trzech nowych wariantów NIE jest jeszcze
zarejestrowany w `SZABLONY` — ten test ma zacząć czerwienić się w chwili, gdy
ktoś (np. #166 albo #167) doda tam klucz przed faktycznym pomiarem mapy, co
pozwoliłoby wygenerować umowę bez naniesienia żadnych danych.
"""

import hashlib
import unittest
from pathlib import Path

from crm.volteo_umowa_mapa_me2 import LICZBA_STRON_ME2, SHA256_SZABLONU_ME2
from crm.volteo_umowa_mapa_pv2 import LICZBA_STRON_PV2, SHA256_SZABLONU_PV2
from crm.volteo_umowa_mapa_pvme2 import LICZBA_STRON_PVME2, SHA256_SZABLONU_PVME2
from crm.volteo_umowa_render import SZABLONY

try:
	from pypdf import PdfReader

	_PYPDF_DOSTEPNY = True
except ImportError:
	_PYPDF_DOSTEPNY = False


def _sciezka_szablonu(nazwa_pliku: str) -> Path:
	"""Zwraca ścieżkę do pliku w `crm/szablony/`, licząc od położenia TEGO modułu
	testowego — ten sam wzorzec co `crm.volteo_umowa_render.sciezka_wbudowanego_szablonu()`,
	powielony lokalnie (nie importowany stamtąd), bo te trzy pliki nie są jeszcze
	zarejestrowane w `SZABLONY` i `sciezka_wbudowanego_szablonu()` odmówiłaby ich
	rozpoznania."""
	return Path(__file__).resolve().parent / "szablony" / nazwa_pliku


def _sha256_pliku(sciezka: Path) -> str:
	"""Liczy SHA-256 pliku wskazanego przez `sciezka`, czytając go binarnie."""
	with open(sciezka, "rb") as f:
		return hashlib.sha256(f.read()).hexdigest()


class TestPlikiSzablonowIstnieja(unittest.TestCase):
	"""Trzy nowe pliki PDF istnieją dokładnie tam, gdzie mają."""

	def test_szablon_pv_podwojna_istnieje(self) -> None:
		self.assertTrue(_sciezka_szablonu("umowa_pv_podwojna.pdf").is_file())

	def test_szablon_me_podwojna_istnieje(self) -> None:
		self.assertTrue(_sciezka_szablonu("umowa_me_podwojna.pdf").is_file())

	def test_szablon_pv_me_podwojna_istnieje(self) -> None:
		self.assertTrue(_sciezka_szablonu("umowa_pv_me_podwojna.pdf").is_file())


class TestSumyKontrolneZgodneZMapami(unittest.TestCase):
	"""Suma SHA-256 każdego pliku w repo zgadza się ze stałą w odpowiednim module mapy.

	To jest ten sam bezpiecznik, który `zloz_umowe()` stosuje dla trzech
	dotychczasowych, jednoosobowych szablonów — sprawdzony tu wcześnie,
	zanim ktokolwiek zacznie mierzyć współrzędne na złym pliku."""

	def test_suma_kontrolna_pv_podwojna(self) -> None:
		self.assertEqual(_sha256_pliku(_sciezka_szablonu("umowa_pv_podwojna.pdf")), SHA256_SZABLONU_PV2)

	def test_suma_kontrolna_me_podwojna(self) -> None:
		self.assertEqual(_sha256_pliku(_sciezka_szablonu("umowa_me_podwojna.pdf")), SHA256_SZABLONU_ME2)

	def test_suma_kontrolna_pv_me_podwojna(self) -> None:
		self.assertEqual(_sha256_pliku(_sciezka_szablonu("umowa_pv_me_podwojna.pdf")), SHA256_SZABLONU_PVME2)


@unittest.skipUnless(_PYPDF_DOSTEPNY, "pypdf nie jest zainstalowany w tym środowisku")
class TestLiczbaStronZgodnaZMapami(unittest.TestCase):
	"""Liczba stron każdego pliku (czytana `pypdf.PdfReader`) zgadza się ze stałą
	`LICZBA_STRON_*2` w odpowiednim module mapy. Pomijany, gdy `pypdf` nie jest
	zainstalowany — ten sam wzorzec, co testy `crm/test_volteo_umowa_render.py`,
	które też zależą od `pypdf`/`reportlab` i nie są zawsze dostępne lokalnie."""

	def test_liczba_stron_pv_podwojna(self) -> None:
		czytnik = PdfReader(str(_sciezka_szablonu("umowa_pv_podwojna.pdf")))
		self.assertEqual(len(czytnik.pages), LICZBA_STRON_PV2)

	def test_liczba_stron_me_podwojna(self) -> None:
		czytnik = PdfReader(str(_sciezka_szablonu("umowa_me_podwojna.pdf")))
		self.assertEqual(len(czytnik.pages), LICZBA_STRON_ME2)

	def test_liczba_stron_pv_me_podwojna(self) -> None:
		czytnik = PdfReader(str(_sciezka_szablonu("umowa_pv_me_podwojna.pdf")))
		self.assertEqual(len(czytnik.pages), LICZBA_STRON_PVME2)


class TestWariantyPodwojneJeszczeNieZarejestrowane(unittest.TestCase):
	"""Bezpiecznik zakresu zadania #165: żaden z trzech nowych wariantów
	podwójnych nie ma jeszcze klucza w `SZABLONY`, i każdy zarejestrowany
	dziś szablon ma niepustą mapę.

	Ten test MA zacząć się czerwienić w chwili, gdy ktoś doda klucz PV2/ME2/
	PVME2 do `SZABLONY` (issue #167) przed faktycznym pomiarem mapy (issue
	#166) — to jest właśnie mechanizm, który ma to uniemożliwić: zarejestrowanie
	pustej mapy pozwoliłoby wygenerować umowę podwójną bez naniesienia żadnych
	danych, czyli po cichu wyprodukować pusty dokument prawny."""

	def test_zadna_zarejestrowana_mapa_nie_jest_pusta(self) -> None:
		for kod, szablon in SZABLONY.items():
			with self.subTest(kod=kod):
				self.assertGreater(len(szablon.mapa), 0)

	def test_klucze_wariantow_podwojnych_nieobecne_w_szablony(self) -> None:
		for domniemany_klucz in ("PV2", "ME2", "PVME2"):
			with self.subTest(klucz=domniemany_klucz):
				self.assertNotIn(domniemany_klucz, SZABLONY)


if __name__ == "__main__":
	unittest.main()
