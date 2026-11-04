# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_sms import dlugosc_gsm7, liczba_czesci_sms, transliteruj_gsm7
from crm.volteo_sms_zaproszenie import (
	POLE_PRZELACZNIKA,
	TRESC_BEZ_ADRESU,
	czy_kanal_wlaczony,
	numer_zaproszonego,
	zbuduj_tresc_zaproszenia,
)


class TestPrzelacznik(unittest.TestCase):
	def test_brak_pola_to_wlaczony(self):
		self.assertTrue(czy_kanal_wlaczony({}))

	def test_pusta_wartosc_to_wlaczony(self):
		self.assertTrue(czy_kanal_wlaczony({POLE_PRZELACZNIKA: ""}))
		self.assertTrue(czy_kanal_wlaczony({POLE_PRZELACZNIKA: None}))

	def test_jawne_zero_wylacza(self):
		self.assertFalse(czy_kanal_wlaczony({POLE_PRZELACZNIKA: "0"}))
		self.assertFalse(czy_kanal_wlaczony({POLE_PRZELACZNIKA: 0}))

	def test_jedynka_wlacza(self):
		self.assertTrue(czy_kanal_wlaczony({POLE_PRZELACZNIKA: "1"}))


class TestNumer(unittest.TestCase):
	def test_rozne_zapisy_polskiego_numeru(self):
		for zapis in ("600100200", "600 100 200", "+48 600-100-200", "48600100200", "0048600100200"):
			with self.subTest(zapis=zapis):
				self.assertEqual(numer_zaproszonego(zapis), "48600100200")

	def test_niepoprawne_daja_none(self):
		for zapis in (None, "", "   ", "12345", "+49 600 100 200", "060010020", "(22) 123"):
			with self.subTest(zapis=zapis):
				self.assertIsNone(numer_zaproszonego(zapis))


class TestTresc(unittest.TestCase):
	def test_zawiera_adres_gdy_sie_miesci(self):
		tresc = zbuduj_tresc_zaproszenia("jan.kowalski@proenergy.pro")
		self.assertIn("jan.kowalski@proenergy.pro", tresc)
		self.assertEqual(liczba_czesci_sms(tresc), 1)

	def test_dlugi_adres_daje_wersje_bez_adresu(self):
		tresc = zbuduj_tresc_zaproszenia(
			"bardzo.dlugie.imie.i.nazwisko.handlowca@bardzo-dluga-domena-firmy.pl"
		)
		self.assertEqual(tresc, TRESC_BEZ_ADRESU)

	def test_brak_adresu(self):
		self.assertEqual(zbuduj_tresc_zaproszenia(None), TRESC_BEZ_ADRESU)
		self.assertEqual(zbuduj_tresc_zaproszenia("  "), TRESC_BEZ_ADRESU)

	def test_zawsze_jedna_czesc_i_czysty_gsm7(self):
		for email in ("a@b.pl", "x" * 30 + "@proenergy.pro", "x" * 200 + "@proenergy.pro", None):
			with self.subTest(email=email):
				tresc = zbuduj_tresc_zaproszenia(email)
				self.assertLessEqual(dlugosc_gsm7(tresc), 160)
				self.assertEqual(transliteruj_gsm7(tresc), tresc)

	def test_nie_niesie_linku(self):
		tresc = zbuduj_tresc_zaproszenia("a@b.pl")
		self.assertNotIn("http", tresc)
		self.assertNotIn("key=", tresc)


if __name__ == "__main__":
	unittest.main()
