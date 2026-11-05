# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import datetime
import unittest

from crm.volteo_leady_kontakt import (
	PROBY_KONTAKTU_OPCJE,
	ROLE_AUTOMATYCZNEGO_CZASU,
	czy_lead_z_webhooka,
	czy_uzupelnic_czas_kontaktu,
	formatuj_gg_mm,
	parsuj_gg_mm,
	sekundy_do_pierwszego_kontaktu,
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

	def test_ponad_24h_przyjete(self):
		for v in (86401, 90000, 138000, 3599940, "138000"):
			self.assertIsNone(waliduj_czas_do_kontaktu(v), v)

	def test_ujemne(self):
		self.assertIn("ujemny", waliduj_czas_do_kontaktu(-1))

	def test_nieliczba(self):
		self.assertIsNotNone(waliduj_czas_do_kontaktu("abc"))
		self.assertIsNotNone(waliduj_czas_do_kontaktu(True))

	def test_formatowanie_ponad_24h(self):
		self.assertEqual(formatuj_gg_mm(138000), "38:20")
		self.assertEqual(formatuj_gg_mm(3599940), "999:59")
		self.assertEqual(parsuj_gg_mm("38:20"), 138000)
		self.assertEqual(parsuj_gg_mm("999:59"), 3599940)


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


class TestCzyLeadZWebhooka(unittest.TestCase):
	def test_source_facebook_tak(self):
		self.assertTrue(czy_lead_z_webhooka("Facebook", None))
		self.assertTrue(czy_lead_z_webhooka("Facebook", ""))
		self.assertTrue(czy_lead_z_webhooka("Facebook", "ARG"))

	def test_token_fb_sam_tak(self):
		self.assertTrue(czy_lead_z_webhooka(None, "FB"))
		self.assertTrue(czy_lead_z_webhooka("", "FB"))

	def test_token_fb_w_zlozeniu_tak(self):
		self.assertTrue(czy_lead_z_webhooka(None, "PV+FB"))
		self.assertTrue(czy_lead_z_webhooka(None, "FB+PV"))
		self.assertTrue(czy_lead_z_webhooka(None, "PV+FB+ME"))

	def test_podciag_fbx_nie(self):
		self.assertFalse(czy_lead_z_webhooka(None, "FBX"))
		self.assertFalse(czy_lead_z_webhooka(None, "PV+FBX"))

	def test_inne_zrodlo_nie(self):
		self.assertFalse(czy_lead_z_webhooka(None, "ARG"))
		self.assertFalse(czy_lead_z_webhooka("Arkusz", "ARG"))

	def test_puste_nie(self):
		self.assertFalse(czy_lead_z_webhooka(None, None))
		self.assertFalse(czy_lead_z_webhooka("", ""))
		self.assertFalse(czy_lead_z_webhooka(None, ""))


class TestCzyUzupelnicCzasKontaktu(unittest.TestCase):
	def test_stala_rol(self):
		self.assertEqual(ROLE_AUTOMATYCZNEGO_CZASU, ("Volteo Call Center", "Volteo Backend"))

	def test_rola_cc_tak(self):
		self.assertTrue(czy_uzupelnic_czas_kontaktu(None, ["Volteo Call Center"], True, True))

	def test_rola_backend_tak(self):
		self.assertTrue(czy_uzupelnic_czas_kontaktu(0, ["Volteo Backend"], True, True))

	def test_rola_d2d_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(None, ["Volteo D2D Sales"], True, True))

	def test_administrator_bez_roli_cc_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(None, ["Administrator"], True, True))

	def test_system_manager_bez_roli_cc_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(None, ["System Manager"], True, True))

	def test_system_manager_z_rola_cc_tak(self):
		self.assertTrue(
			czy_uzupelnic_czas_kontaktu(None, ["System Manager", "Volteo Call Center"], True, True)
		)

	def test_pole_wypelnione_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(60, ["Volteo Call Center"], True, True))
		self.assertFalse(czy_uzupelnic_czas_kontaktu("3600", ["Volteo Backend"], True, True))

	def test_pole_puste_warianty_tak(self):
		for wartosc in (None, 0, "", "0", 0.0):
			self.assertTrue(
				czy_uzupelnic_czas_kontaktu(wartosc, ["Volteo Call Center"], True, True), wartosc
			)

	def test_wylaczona_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(None, ["Volteo Call Center"], False, True))

	def test_nie_z_webhooka_nie(self):
		self.assertFalse(czy_uzupelnic_czas_kontaktu(None, ["Volteo Call Center"], True, False))
		self.assertFalse(czy_uzupelnic_czas_kontaktu(0, ["Volteo Backend"], True, False))


class TestSekundyDoPierwszegoKontaktu(unittest.TestCase):
	def test_roznica_zero(self):
		self.assertEqual(sekundy_do_pierwszego_kontaktu("2026-01-01 10:00:00", "2026-01-01 10:00:00"), 0)

	def test_59_sekund_daje_zero(self):
		self.assertEqual(sekundy_do_pierwszego_kontaktu("2026-01-01 10:00:00", "2026-01-01 10:00:59"), 0)

	def test_61_sekunda_daje_minute(self):
		self.assertEqual(sekundy_do_pierwszego_kontaktu("2026-01-01 10:00:00", "2026-01-01 10:01:01"), 60)

	def test_ponad_24h(self):
		self.assertEqual(
			sekundy_do_pierwszego_kontaktu("2026-01-01 10:00:00", "2026-01-02 12:30:00"),
			26 * 3600 + 30 * 60,
		)

	def test_string_z_mikrosekundami(self):
		self.assertEqual(
			sekundy_do_pierwszego_kontaktu(
				"2026-01-01 10:00:00.123456", "2026-01-01 10:05:00.654321"
			),
			300,
		)

	def test_ujemne_daje_zero(self):
		self.assertEqual(sekundy_do_pierwszego_kontaktu("2026-01-01 10:05:00", "2026-01-01 10:00:00"), 0)

	def test_przyjmuje_obiekty_datetime(self):
		poczatek = datetime.datetime(2026, 1, 1, 10, 0, 0)
		koniec = datetime.datetime(2026, 1, 1, 10, 2, 30)
		self.assertEqual(sekundy_do_pierwszego_kontaktu(poczatek, koniec), 120)


if __name__ == "__main__":
	unittest.main()
