# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import datetime, timedelta

from crm.volteo_lead_bez_zmian import (
	AUTORZY_TECHNICZNI,
	KLUCZ_REGULY,
	LIMIT_LEADOW_NA_PRZEBIEG,
	PROG_DOMYSLNY_GODZIN,
	ROLA_INTEGRACJI,
	ZAKRES_WSZYSTKIE,
	ZAKRES_Z_HANDLOWCEM,
	ZAKRES_Z_REGULY,
	ZAKRESY,
	czy_autor_czlowiek,
	czy_lead_w_zakresie,
	czy_prog_poprawny,
	czy_w_oknie,
	czy_wyslac_alert,
	czy_zakres_poprawny,
	leady_z_aktywnoscia_czlowieka,
	normalizuj_prog,
	normalizuj_zakres,
	ogranicz_przebieg,
	okno_utworzenia,
	tresc_powiadomienia,
	zbierz_odbiorcow,
)

TERAZ = datetime(2026, 11, 13, 12, 0, 0)


class TestStale(unittest.TestCase):
	def test_klucz(self):
		self.assertEqual(KLUCZ_REGULY, "lead_bez_zmian")

	def test_zakresy_trzy_wartosci(self):
		self.assertEqual(
			ZAKRESY,
			("Wszystkie leady z Facebooka", "Leady z przypisanym handlowcem", "Leady z reguły bezpośredniej"),
		)

	def test_rola_integracji(self):
		self.assertEqual(ROLA_INTEGRACJI, "Volteo Integracja")

	def test_autorzy_techniczni(self):
		self.assertEqual(AUTORZY_TECHNICZNI, frozenset({"Administrator", "Guest"}))

	def test_limit_przebiegu(self):
		self.assertEqual(LIMIT_LEADOW_NA_PRZEBIEG, 50)


class TestProg(unittest.TestCase):
	def test_domyslny(self):
		self.assertEqual(PROG_DOMYSLNY_GODZIN, 48)

	def test_normalizacja_poprawnej(self):
		self.assertEqual(normalizuj_prog(72), 72)
		self.assertEqual(normalizuj_prog("24"), 24)

	def test_normalizacja_pustej_i_smieci(self):
		self.assertEqual(normalizuj_prog(None), 48)
		self.assertEqual(normalizuj_prog(""), 48)
		self.assertEqual(normalizuj_prog(0), 48)
		self.assertEqual(normalizuj_prog("abc"), 48)

	def test_normalizacja_przycina(self):
		self.assertEqual(normalizuj_prog(-5), 1)
		self.assertEqual(normalizuj_prog(5000), 720)

	def test_walidacja(self):
		self.assertTrue(czy_prog_poprawny(1))
		self.assertTrue(czy_prog_poprawny("720"))
		self.assertFalse(czy_prog_poprawny(0))
		self.assertFalse(czy_prog_poprawny(721))
		self.assertFalse(czy_prog_poprawny(None))
		self.assertFalse(czy_prog_poprawny(True))
		self.assertFalse(czy_prog_poprawny("x"))


class TestZakres(unittest.TestCase):
	def test_pusty_to_wszystkie(self):
		self.assertEqual(normalizuj_zakres(None), ZAKRES_WSZYSTKIE)
		self.assertEqual(normalizuj_zakres(""), ZAKRES_WSZYSTKIE)

	def test_nieznany_to_wszystkie(self):
		self.assertEqual(normalizuj_zakres("cos innego"), ZAKRES_WSZYSTKIE)

	def test_znane_bez_zmian(self):
		for z in ZAKRESY:
			self.assertEqual(normalizuj_zakres(z), z)

	def test_walidacja(self):
		self.assertTrue(czy_zakres_poprawny(ZAKRES_Z_REGULY))
		self.assertFalse(czy_zakres_poprawny(""))
		self.assertFalse(czy_zakres_poprawny(None))
		self.assertFalse(czy_zakres_poprawny("x"))


class TestOkno(unittest.TestCase):
	def test_okno(self):
		od, do = okno_utworzenia(TERAZ, 48)
		self.assertEqual(do, TERAZ - timedelta(hours=48))
		self.assertEqual(od, TERAZ - timedelta(hours=72))

	def test_w_oknie_granice(self):
		self.assertTrue(czy_w_oknie(TERAZ - timedelta(hours=48), TERAZ, 48))
		self.assertTrue(czy_w_oknie(TERAZ - timedelta(hours=72), TERAZ, 48))
		self.assertTrue(czy_w_oknie(TERAZ - timedelta(hours=49), TERAZ, 48))

	def test_za_mlody(self):
		self.assertFalse(czy_w_oknie(TERAZ - timedelta(hours=47), TERAZ, 48))

	def test_za_stary(self):
		self.assertFalse(czy_w_oknie(TERAZ - timedelta(hours=73), TERAZ, 48))

	def test_brak_creation(self):
		self.assertFalse(czy_w_oknie(None, TERAZ, 48))

	def test_inny_prog(self):
		self.assertTrue(czy_w_oknie(TERAZ - timedelta(hours=10), TERAZ, 6))
		self.assertFalse(czy_w_oknie(TERAZ - timedelta(hours=40), TERAZ, 6))


class TestAutor(unittest.TestCase):
	def test_czlowiek(self):
		self.assertTrue(czy_autor_czlowiek("r.rzepecki@proenergy.pro"))

	def test_administrator_guest(self):
		self.assertFalse(czy_autor_czlowiek("Administrator"))
		self.assertFalse(czy_autor_czlowiek("Guest"))

	def test_pusty(self):
		self.assertFalse(czy_autor_czlowiek(None))
		self.assertFalse(czy_autor_czlowiek(""))

	def test_konto_integracji(self):
		self.assertFalse(
			czy_autor_czlowiek("integracja.make@proenergy.pro", ["integracja.make@proenergy.pro"])
		)
		self.assertTrue(czy_autor_czlowiek("a@x.pl", ["integracja.make@proenergy.pro"]))

	def test_zbior_leadow_z_aktywnoscia(self):
		wiersze = [
			("L1", "Administrator"),
			("L1", "integracja@x.pl"),
			("L2", "jan@x.pl"),
			("L3", None),
			(None, "jan@x.pl"),
		]
		self.assertEqual(leady_z_aktywnoscia_czlowieka(wiersze, ["integracja@x.pl"]), {"L2"})

	def test_zbior_pusty(self):
		self.assertEqual(leady_z_aktywnoscia_czlowieka([]), set())


class TestZakresLeada(unittest.TestCase):
	def test_wszystkie(self):
		self.assertTrue(czy_lead_w_zakresie(ZAKRES_WSZYSTKIE, None, 0))
		self.assertTrue(czy_lead_w_zakresie("", None, None))

	def test_z_handlowcem(self):
		self.assertTrue(czy_lead_w_zakresie(ZAKRES_Z_HANDLOWCEM, "h@x.pl", 0))
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_HANDLOWCEM, None, 1))
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_HANDLOWCEM, "", 1))

	def test_z_reguly(self):
		self.assertTrue(czy_lead_w_zakresie(ZAKRES_Z_REGULY, "h@x.pl", 1))
		self.assertTrue(czy_lead_w_zakresie(ZAKRES_Z_REGULY, None, "1"))
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_REGULY, "h@x.pl", 0))
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_REGULY, "h@x.pl", None))

	def test_z_reguly_bez_pola(self):
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_REGULY, "h@x.pl", 1, pole_przydzialu_istnieje=False))

	def test_z_reguly_smieci(self):
		self.assertFalse(czy_lead_w_zakresie(ZAKRES_Z_REGULY, "h@x.pl", "abc"))


class TestDecyzja(unittest.TestCase):
	def test_komplet(self):
		self.assertTrue(czy_wyslac_alert(True, True, True, False, None))

	def test_kazdy_warunek_blokuje(self):
		self.assertFalse(czy_wyslac_alert(False, True, True, False, None))
		self.assertFalse(czy_wyslac_alert(True, False, True, False, None))
		self.assertFalse(czy_wyslac_alert(True, True, False, False, None))
		self.assertFalse(czy_wyslac_alert(True, True, True, True, None))
		self.assertFalse(czy_wyslac_alert(True, True, True, False, datetime(2026, 11, 13)))


class TestOdbiorcy(unittest.TestCase):
	AKTYWNI = frozenset({"a@x.pl", "b@x.pl", "h@x.pl"})

	def test_tabela(self):
		self.assertEqual(zbierz_odbiorcow(["b@x.pl", "a@x.pl"], None, 0, self.AKTYWNI), ["a@x.pl", "b@x.pl"])

	def test_handlowiec_wlaczony(self):
		self.assertEqual(zbierz_odbiorcow(["a@x.pl"], "h@x.pl", 1, self.AKTYWNI), ["a@x.pl", "h@x.pl"])

	def test_handlowiec_wylaczony(self):
		self.assertEqual(zbierz_odbiorcow(["a@x.pl"], "h@x.pl", 0, self.AKTYWNI), ["a@x.pl"])

	def test_tylko_aktywni(self):
		self.assertEqual(
			zbierz_odbiorcow(["a@x.pl", "zly@x.pl"], "nieaktywny@x.pl", 1, self.AKTYWNI), ["a@x.pl"]
		)

	def test_duplikat(self):
		self.assertEqual(zbierz_odbiorcow(["h@x.pl"], "h@x.pl", 1, self.AKTYWNI), ["h@x.pl"])

	def test_pusto(self):
		self.assertEqual(zbierz_odbiorcow([None, ""], None, 1, self.AKTYWNI), [])


class TestPrzebieg(unittest.TestCase):
	def test_ponizej_limitu(self):
		self.assertEqual(ogranicz_przebieg([1, 2, 3], 50), ([1, 2, 3], 0))

	def test_powyzej_limitu(self):
		wynik, nadmiar = ogranicz_przebieg(list(range(60)), 50)
		self.assertEqual(len(wynik), 50)
		self.assertEqual(nadmiar, 10)

	def test_domyslny_limit(self):
		wynik, nadmiar = ogranicz_przebieg(list(range(LIMIT_LEADOW_NA_PRZEBIEG + 1)))
		self.assertEqual((len(wynik), nadmiar), (LIMIT_LEADOW_NA_PRZEBIEG, 1))

	def test_limit_zero(self):
		self.assertEqual(ogranicz_przebieg([1, 2], 0), ([], 2))


class TestTresc(unittest.TestCase):
	def test_z_handlowcem(self):
		self.assertEqual(
			tresc_powiadomienia(48, "Jan Kowalski", "66-300", "Grzegorz Furmann"),
			"Lead bez zmian od 48 h: Jan Kowalski, 66-300. Handlowiec: Grzegorz Furmann.",
		)

	def test_bez_handlowca(self):
		self.assertEqual(
			tresc_powiadomienia(48, "Jan Kowalski", "66-300", None),
			"Lead bez zmian od 48 h: Jan Kowalski, 66-300. Bez handlowca, pula CC.",
		)

	def test_godziny_z_ustawienia(self):
		self.assertIn("od 72 h", tresc_powiadomienia(72, "A", "00-001", None))

	def test_brak_kodu(self):
		self.assertEqual(
			tresc_powiadomienia(48, "Jan", "", "H"), "Lead bez zmian od 48 h: Jan. Handlowiec: H."
		)

	def test_brak_nazwy(self):
		self.assertIn("bez nazwy", tresc_powiadomienia(48, None, "66-300", None))

	def test_escape_html(self):
		tresc = tresc_powiadomienia(48, "<b>x</b>", "66-300", "<i>h</i>")
		self.assertNotIn("<b>", tresc)
		self.assertNotIn("<i>", tresc)

	def test_bez_myslnikow(self):
		tresc = tresc_powiadomienia(48, "Jan", "66-300", None)
		self.assertNotIn(chr(0x2014), tresc)
		self.assertNotIn(chr(0x2013), tresc)


if __name__ == "__main__":
	unittest.main()
