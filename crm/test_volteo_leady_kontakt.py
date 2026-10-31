# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_leady_kontakt import (
	MAKS_CZAS_DO_KONTAKTU_S,
	PROBY_KONTAKTU_OPCJE,
	formatuj_gg_mm,
	parsuj_gg_mm,
	waliduj_czas_do_kontaktu,
	waliduj_proby_kontaktu,
)


class TestWalidujCzas(unittest.TestCase):
	def test_puste_ok(self):
		for v in (None, 0, "", "0", 0.0):
			self.assertIsNone(waliduj_czas_do_kontaktu(v), v)

	def test_poprawne(self):
		for v in (60, 5400, 86400, "5400", 86400.0):
			self.assertIsNone(waliduj_czas_do_kontaktu(v), v)

	def test_ponad_limit(self):
		self.assertIn("24:00", waliduj_czas_do_kontaktu(86401))
		self.assertIn("24:00", waliduj_czas_do_kontaktu(90000))

	def test_ujemne(self):
		self.assertIn("ujemny", waliduj_czas_do_kontaktu(-1))

	def test_nieliczba(self):
		self.assertIsNotNone(waliduj_czas_do_kontaktu("abc"))
		self.assertIsNotNone(waliduj_czas_do_kontaktu(True))

	def test_stala(self):
		self.assertEqual(MAKS_CZAS_DO_KONTAKTU_S, 86400)


class TestWalidujProby(unittest.TestCase):
	def test_opcje(self):
		self.assertEqual(PROBY_KONTAKTU_OPCJE, ("0", "1", "2", "3", "4", "5"))

	def test_poprawne(self):
		for v in ("0", "3", "5", 0, 5, 2.0, None, ""):
			self.assertIsNone(waliduj_proby_kontaktu(v), v)

	def test_niepoprawne(self):
		for v in ("7", "6", 7, -1, "abc", 2.5, True):
			self.assertIsNotNone(waliduj_proby_kontaktu(v), v)


class TestFormatuj(unittest.TestCase):
	def test_puste(self):
		for v in (0, None, "", -5):
			self.assertEqual(formatuj_gg_mm(v), "")

	def test_wartosci(self):
		self.assertEqual(formatuj_gg_mm(5400), "01:30")
		self.assertEqual(formatuj_gg_mm(60), "00:01")
		self.assertEqual(formatuj_gg_mm(86400), "24:00")
		self.assertEqual(formatuj_gg_mm(3600), "01:00")
		self.assertEqual(formatuj_gg_mm("5400"), "01:30")


class TestParsuj(unittest.TestCase):
	def test_dwukropek(self):
		self.assertEqual(parsuj_gg_mm("1:30"), 5400)
		self.assertEqual(parsuj_gg_mm("01:30"), 5400)
		self.assertEqual(parsuj_gg_mm("24:00"), 86400)
		self.assertEqual(parsuj_gg_mm(" 0:05 "), 300)

	def test_cyfry(self):
		self.assertEqual(parsuj_gg_mm("0130"), 5400)
		self.assertEqual(parsuj_gg_mm("130"), 5400)
		self.assertEqual(parsuj_gg_mm("2"), 7200)
		self.assertEqual(parsuj_gg_mm("12"), 43200)

	def test_niepoprawne(self):
		for v in ("abc", "1:60", "", None, "1:2:3", "12345", "-1:00", "1,5"):
			self.assertIsNone(parsuj_gg_mm(v), v)

	def test_ponad_24_parsuje_sie(self):
		self.assertEqual(parsuj_gg_mm("25:00"), 90000)

	def test_roundtrip(self):
		for s in (60, 5400, 86400):
			self.assertEqual(parsuj_gg_mm(formatuj_gg_mm(s)), s)


if __name__ == "__main__":
	unittest.main()
