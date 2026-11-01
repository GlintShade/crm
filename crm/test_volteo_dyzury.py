# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import datetime, time, timedelta
from typing import ClassVar

from crm.volteo_dyzury import (
	DANE_PRZYKLADOWE_DYZUR,
	DNI_TYGODNIA,
	PLACEHOLDERY_DYZUR,
	TRESC_DYZUR_DOMYSLNA,
	czy_wyjatek_dnia,
	dyzurni_w_chwili,
	dzien_tygodnia,
	dzien_z_daty,
	klucz_licznika_dnia,
	normalizuj_numer_pl,
	opis_chwili,
	opis_daty,
	parsuj_czas,
	parsuj_date,
	waliduj_limit_dyzur,
	waliduj_tresc_dyzur,
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


class TestTrescIPodglad(unittest.TestCase):
	def test_pusta_tresc(self):
		self.assertEqual(waliduj_tresc_dyzur("   "), "Treść SMS nie może być pusta.")
		self.assertEqual(waliduj_tresc_dyzur(None), "Treść SMS nie może być pusta.")

	def test_nieznany_placeholder(self):
		komunikat = waliduj_tresc_dyzur("Lead {klient} {xxx}")
		self.assertIn("Nieznany placeholder {xxx}", komunikat)
		self.assertIn("{miejscowosc}", komunikat)

	def test_poprawna_tresc(self):
		self.assertIsNone(waliduj_tresc_dyzur(TRESC_DYZUR_DOMYSLNA))

	def test_wszystkie_znane_placeholdery_przechodza(self):
		tresc = " ".join("{" + p + "}" for p in PLACEHOLDERY_DYZUR)
		self.assertIsNone(waliduj_tresc_dyzur(tresc))

	def test_limit(self):
		self.assertIsNone(waliduj_limit_dyzur(0))
		self.assertIsNone(waliduj_limit_dyzur("1000"))
		self.assertIsNotNone(waliduj_limit_dyzur(1001))
		self.assertIsNotNone(waliduj_limit_dyzur(-1))
		self.assertIsNotNone(waliduj_limit_dyzur("abc"))

	def test_dane_przykladowe_daja_tekst_bez_polskich_znakow(self):
		tresc, _ostrzezenie = zbuduj_tresc_dyzur(
			"Nowy lead FB: {klient}, {miejscowosc}, tel. {telefon}, {kod}. {link}",
			{**DANE_PRZYKLADOWE_DYZUR, "link": "https://crm.example/crm/leads/X"},
		)
		self.assertIn("Jan Testowy", tresc)
		self.assertTrue(tresc.isascii())
		self.assertNotIn("{", tresc)


def wyjatek(data, od, do, uzytkownik, aktywny=1, bez_dyzuru=0):
	return {
		"dzien_tygodnia": dzien_z_daty(data),
		"data": data,
		"od": od,
		"do": do,
		"uzytkownik": uzytkownik,
		"aktywny": aktywny,
		"bez_dyzuru": bez_dyzuru,
	}


# 2026-11-03 to wtorek (normalnie dyżur ma A)
WT_DATA = "2026-11-03"


class TestParsujDate(unittest.TestCase):
	def test_string_date_datetime(self):
		from datetime import date

		self.assertEqual(parsuj_date("2026-11-03"), date(2026, 11, 3))
		self.assertEqual(parsuj_date(date(2026, 11, 3)), date(2026, 11, 3))
		self.assertEqual(parsuj_date(datetime(2026, 11, 3, 12, 30)), date(2026, 11, 3))

	def test_zle_wartosci(self):
		for zle in (None, "", "03.11.2026", "2026-13-01", "2026-02-30", 5):
			self.assertIsNone(parsuj_date(zle))

	def test_opis_i_dzien(self):
		self.assertEqual(opis_daty("2026-11-11"), "11.11.2026")
		self.assertEqual(dzien_z_daty(WT_DATA), "Wtorek")
		self.assertIsNone(dzien_z_daty("x"))


class TestWyjatki(unittest.TestCase):
	def test_wyjatek_z_osoba_zastepuje_grafik(self):
		g = [*GRAFIK, wyjatek(WT_DATA, "09:00:00", "12:00:00", R)]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [R])
		# poza godzinami wyjatku grafik tygodniowy A tez nie dziala
		self.assertEqual(dyzurni_w_chwili(g, o(1, 14)), [])

	def test_bez_dyzuru_daje_pusto_mimo_wiersza_tygodniowego(self):
		g = [*GRAFIK, wyjatek(WT_DATA, None, None, None, bez_dyzuru=1)]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [])
		self.assertTrue(czy_wyjatek_dnia(g, o(1, 10)))

	def test_wyjatek_innej_daty_ignorowany(self):
		g = [*GRAFIK, wyjatek("2026-11-10", "09:00:00", "12:00:00", R)]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [A])
		self.assertFalse(czy_wyjatek_dnia(g, o(1, 10)))

	def test_wyjatek_nieaktywny_ignorowany(self):
		g = [*GRAFIK, wyjatek(WT_DATA, None, None, None, aktywny=0, bez_dyzuru=1)]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [A])
		self.assertFalse(czy_wyjatek_dnia(g, o(1, 10)))

	def test_dwie_zmiany_jednej_daty(self):
		g = [
			*GRAFIK,
			wyjatek(WT_DATA, "08:00:00", "12:00:00", R),
			wyjatek(WT_DATA, "12:00:00", "18:00:00", A),
		]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 11, 59)), [R])
		self.assertEqual(dyzurni_w_chwili(g, o(1, 12)), [A])
		self.assertEqual(dyzurni_w_chwili(g, o(1, 18)), [])

	def test_granice_od_do(self):
		g = [wyjatek(WT_DATA, "09:00:00", "10:00:00", R)]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 9)), [R])
		self.assertEqual(dyzurni_w_chwili(g, o(1, 8, 59)), [])
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [])

	def test_data_jako_date_i_datetime(self):
		from datetime import date

		for d in (date(2026, 11, 3), datetime(2026, 11, 3)):
			g = [{**wyjatek(WT_DATA, "09:00:00", "12:00:00", R), "data": d}]
			self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [R])

	def test_bez_dyzuru_i_osoba_tej_samej_daty(self):
		# wiersz bez_dyzuru sam nic nie dodaje, ale inny wyjatek tej daty nadal obowiazuje
		g = [
			wyjatek(WT_DATA, None, None, None, bez_dyzuru=1),
			wyjatek(WT_DATA, "09:00:00", "12:00:00", R),
		]
		self.assertEqual(dyzurni_w_chwili(g, o(1, 10)), [R])

	def test_wiersz_tygodniowy_bez_klucza_data_dziala_jak_dawniej(self):
		self.assertEqual(dyzurni_w_chwili(GRAFIK, o(1, 10)), [A])

	def test_slad_z_wyjatkiem(self):
		d = zdecyduj_wysylke_dyzur(
			wlaczone=True, token_ustawiony=True, chwila=o(1, 10, 5), dyzurni=[], wyjatek_dnia=True
		)
		self.assertEqual(d.slad, "SMS dyżurowy: brak dyżuru (wtorek 10:05, wyjątek od grafiku na 03.11.2026)")

	def test_slad_bez_wyjatku_bez_zmian(self):
		d = zdecyduj_wysylke_dyzur(wlaczone=True, token_ustawiony=True, chwila=o(1, 10, 5), dyzurni=[])
		self.assertEqual(d.slad, "SMS dyżurowy: brak dyżuru (wtorek 10:05)")


class TestWalidujWyjatek(unittest.TestCase):
	def test_stare_wywolanie_trzyargumentowe(self):
		self.assertIsNone(waliduj_wiersz("Wtorek", "08:00", "18:00"))
		self.assertIn("Dzień tygodnia", waliduj_wiersz("x", "08:00", "18:00"))
		self.assertIn("wcześniejsza", waliduj_wiersz("Wtorek", "18:00", "08:00"))

	def test_bez_dyzuru_wymaga_daty(self):
		self.assertEqual(
			waliduj_wiersz("Wtorek", "08:00", "18:00", bez_dyzuru=1),
			"Opcja 'nikt nie ma dyżuru' dotyczy tylko wyjątku z datą.",
		)

	def test_zla_data(self):
		self.assertEqual(
			waliduj_wiersz(None, "08:00", "18:00", data="03.11.2026"),
			"Data wyjątku musi mieć format RRRR-MM-DD.",
		)

	def test_wyjatek_bez_dyzuru_przyjmuje_puste_reszte(self):
		self.assertIsNone(waliduj_wiersz("", None, None, data=WT_DATA, bez_dyzuru=1, uzytkownik=""))

	def test_wyjatek_z_osoba_wymaga_godzin_i_uzytkownika(self):
		self.assertIsNone(waliduj_wiersz("", "09:00", "12:00", data=WT_DATA, uzytkownik=R))
		self.assertIn("GG:MM", waliduj_wiersz("", None, "12:00", data=WT_DATA, uzytkownik=R))
		self.assertIn("wcześniejsza", waliduj_wiersz("", "12:00", "09:00", data=WT_DATA, uzytkownik=R))
		self.assertEqual(
			waliduj_wiersz("", "09:00", "12:00", data=WT_DATA, uzytkownik=""), "Wybierz użytkownika."
		)

	def test_wiersz_tygodniowy_z_uzytkownikiem(self):
		self.assertEqual(waliduj_wiersz("Wtorek", "08:00", "18:00", uzytkownik=None), "Wybierz użytkownika.")
		self.assertIsNone(waliduj_wiersz("Wtorek", "08:00", "18:00", uzytkownik=R))
