# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import datetime, time, timedelta
from typing import ClassVar

from crm.volteo_dyzury import (
	DNI_TYGODNIA,
	TRESC_DYZUR_DOMYSLNA,
	dyzurni_w_chwili,
	dzien_tygodnia,
	klucz_licznika_dnia,
	normalizuj_numer_pl,
	opis_chwili,
	parsuj_czas,
	waliduj_wiersz,
	zbuduj_tresc_dyzur,
	zdecyduj_wysylke_dyzur,
)

R = "r.rzepecki@proenergy.pro"
A = "a.rzysko@proenergy.pro"


def wiersz(dzien, od, do, uzytkownik, aktywny=1):
	return {"dzien_tygodnia": dzien, "od": od, "do": do, "uzytkownik": uzytkownik, "aktywny": aktywny}


GRAFIK = [
	*(wiersz(d, "08:00:00", "18:00:00", R) for d in ("Poniedziałek", "Środa", "Piątek")),
	*(wiersz(d, "08:00:00", "18:00:00", A) for d in ("Wtorek", "Czwartek")),
]
# 2026-11-02 to poniedziałek
PON = datetime(2026, 11, 2)


def o(dzien_offset, g, m=0):
	return PON + timedelta(days=dzien_offset, hours=g, minutes=m)


class TestDzien(unittest.TestCase):
	def test_siedem_dni(self):
		self.assertEqual(len(DNI_TYGODNIA), 7)

	def test_poniedzialek(self):
		self.assertEqual(dzien_tygodnia(PON), "Poniedziałek")

	def test_niedziela(self):
		self.assertEqual(dzien_tygodnia(o(6, 12)), "Niedziela")

	def test_sroda(self):
		self.assertEqual(dzien_tygodnia(o(2, 1)), "Środa")


class TestParsujCzas(unittest.TestCase):
	def test_string_hms(self):
		self.assertEqual(parsuj_czas("08:00:00"), time(8, 0))

	def test_string_hm(self):
		self.assertEqual(parsuj_czas("8:30"), time(8, 30))

	def test_timedelta(self):
		self.assertEqual(parsuj_czas(timedelta(hours=18)), time(18, 0))

	def test_time(self):
		self.assertEqual(parsuj_czas(time(7, 5, 3)), time(7, 5, 3))

	def test_smiec(self):
		self.assertIsNone(parsuj_czas("abc"))
		self.assertIsNone(parsuj_czas("25:00"))
		self.assertIsNone(parsuj_czas(None))
		self.assertIsNone(parsuj_czas(timedelta(hours=30)))


class TestDyzurni(unittest.TestCase):
	def test_pon_9(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(0, 9)), [R])

	def test_wt_9(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(1, 9)), [A])

	def test_sobota_12(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(5, 12)), [])

	def test_niedziela(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(6, 12)), [])

	def test_do_wylacznie(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(0, 18)), [])

	def test_od_wlacznie(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(0, 8)), [R])

	def test_przed_od(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(0, 7, 59)), [])

	def test_ostatnia_minuta(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(0, 17, 59)), [R])

	def test_timedelty_z_frappe(self):
		g = [wiersz("Poniedziałek", timedelta(hours=8), timedelta(hours=18), R)]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 12)), [R])

	def test_nieaktywny(self):
		g = [wiersz("Poniedziałek", "08:00:00", "18:00:00", R, aktywny=0)]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 12)), [])

	def test_aktywny_string_zero(self):
		g = [wiersz("Poniedziałek", "08:00:00", "18:00:00", R, aktywny="0")]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 12)), [])

	def test_nakladanie_dwoch_osob(self):
		g = [
			wiersz("Poniedziałek", "10:00:00", "14:00:00", A),
			wiersz("Poniedziałek", "08:00:00", "18:00:00", R),
		]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 11)), [R, A])

	def test_ten_sam_uzytkownik_raz(self):
		g = [
			wiersz("Poniedziałek", "08:00:00", "12:00:00", R),
			wiersz("Poniedziałek", "09:00:00", "18:00:00", R),
		]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 10)), [R])

	def test_bledny_czas_pomijany(self):
		g = [wiersz("Poniedziałek", "zle", "18:00:00", R)]
		self.assertEqual(dyzurni_w_chwili(g, o(0, 10)), [])

	def test_pusty_grafik(self):
		self.assertEqual(dyzurni_w_chwili([], o(0, 10)), [])


class TestWaliduj(unittest.TestCase):
	def test_ok(self):
		self.assertIsNone(waliduj_wiersz("Wtorek", "08:00:00", "18:00:00"))

	def test_zly_dzien(self):
		self.assertIn("Dzień", waliduj_wiersz("Monday", "08:00", "18:00"))

	def test_od_rowne_do(self):
		self.assertIn("wcześniejsza", waliduj_wiersz("Wtorek", "08:00", "08:00"))

	def test_od_pozniej(self):
		self.assertIn("wcześniejsza", waliduj_wiersz("Wtorek", "19:00", "08:00"))

	def test_zly_format(self):
		self.assertIn("GG:MM", waliduj_wiersz("Wtorek", "xx", "08:00"))


class TestTresc(unittest.TestCase):
	DANE: ClassVar[dict] = {
		"klient": "Zażółć Gęślą",
		"telefon": "+48500100200",
		"kod": "64-000",
		"miejscowosc": "Kościan",
		"link": "https://crm.proenergy.pro/crm/leads/L1",
	}

	def test_domyslna(self):
		tresc, ostrz = zbuduj_tresc_dyzur(TRESC_DYZUR_DOMYSLNA, self.DANE)
		self.assertEqual(
			tresc,
			"Nowy lead FB: Zazolc Gesla, tel. +48500100200, 64-000. https://crm.proenergy.pro/crm/leads/L1",
		)
		self.assertIsNone(ostrz)

	def test_brak_klucza_pusty(self):
		tresc, _ = zbuduj_tresc_dyzur("A {kod} B {miejscowosc}", {"klient": "x"})
		self.assertEqual(tresc, "A B")

	def test_brak_kodu_nie_zostawia_przecinka(self):
		tresc, _ = zbuduj_tresc_dyzur(TRESC_DYZUR_DOMYSLNA, {**self.DANE, "kod": ""})
		self.assertNotIn(", .", tresc)
		self.assertNotIn(",.", tresc)

	def test_nieznany_placeholder_zostaje(self):
		tresc, _ = zbuduj_tresc_dyzur("X {nieznany} {klient}", {"klient": "Jan"})
		self.assertEqual(tresc, "X {nieznany} Jan")

	def test_ostrzezenie_dlugiej(self):
		_, ostrz = zbuduj_tresc_dyzur("a" * 200, {})
		self.assertIsNotNone(ostrz)

	def test_none_wartosc(self):
		tresc, _ = zbuduj_tresc_dyzur("{klient}!", {"klient": None})
		self.assertEqual(tresc, "!")

	def test_pusty_szablon(self):
		self.assertEqual(zbuduj_tresc_dyzur("", {})[0], "")


class TestNumerPl(unittest.TestCase):
	def test_akceptowane(self):
		for wej in (
			"+48500100200",
			"48500100200",
			"0048500100200",
			"500100200",
			"500 100 200",
			"500-100-200",
			"+48 500 100 200",
			"500.100.200",
			" 500100200 ",
		):
			self.assertEqual(normalizuj_numer_pl(wej), "+48500100200", wej)

	def test_odrzucone(self):
		for wej in (
			"50010020",
			"5001002000",
			"abc500100200",
			"+49500100200",
			"049500100200",
			"012345678",
			"+4850010020",
		):
			self.assertIsNone(normalizuj_numer_pl(wej), wej)

	def test_puste(self):
		for wej in (None, "", "   "):
			self.assertIsNone(normalizuj_numer_pl(wej))


class TestKlucz(unittest.TestCase):
	def test_klucz(self):
		self.assertEqual(klucz_licznika_dnia(datetime(2026, 11, 2, 23, 59)), "volteo:sms_dyzur:2026-11-02")

	def test_opis_chwili(self):
		self.assertEqual(opis_chwili(o(5, 14, 5)), "sobota 14:05")


class TestDecyzja(unittest.TestCase):
	BAZA: ClassVar[dict] = dict(
		wlaczone=True,
		token_ustawiony=True,
		chwila=o(0, 9),
		dyzurni=[R],
		imie_dyzurnego="Remigiusz Rzepecki",
		numer="48500100200",
	)

	def d(self, **zm):
		return zdecyduj_wysylke_dyzur(**{**self.BAZA, **zm})

	def test_wysylaj(self):
		self.assertTrue(self.d().wyslij)

	def test_wylaczone_bez_sladu(self):
		r = self.d(wlaczone=False)
		self.assertFalse(r.wyslij)
		self.assertFalse(r.zapisz_slad)

	def test_brak_dyzuru(self):
		r = self.d(dyzurni=[], chwila=o(5, 14, 5))
		self.assertFalse(r.wyslij)
		self.assertEqual(r.slad, "SMS dyżurowy: brak dyżuru (sobota 14:05)")

	def test_brak_numeru(self):
		r = self.d(numer=None)
		self.assertFalse(r.wyslij)
		self.assertIn("bez numeru telefonu", r.slad)
		self.assertIn("Remigiusz Rzepecki", r.slad)

	def test_brak_tokenu(self):
		r = self.d(token_ustawiony=False)
		self.assertFalse(r.wyslij)
		self.assertIn("brak tokenu", r.slad)

	def test_limit(self):
		r = self.d(limit_dzienny=3, wyslane_dzis=3)
		self.assertFalse(r.wyslij)
		self.assertTrue(r.limit_wyczerpany)

	def test_limit_zero_blokuje(self):
		self.assertFalse(self.d(limit_dzienny=0, wyslane_dzis=0).wyslij)

	def test_limit_nie_wyczerpany(self):
		self.assertTrue(self.d(limit_dzienny=3, wyslane_dzis=2).wyslij)

	def test_slad_bez_numeru(self):
		r = self.d(numer=None)
		self.assertNotIn("48500", r.slad)


if __name__ == "__main__":
	unittest.main()
