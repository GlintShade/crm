# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_kalendarz import (
	granice_czasu,
	normalizuj_handlowcow,
	normalizuj_termin,
	pogrupuj_spotkania,
	przetnij_handlowcow,
	waliduj_zakres_dat,
	zakres_dnia,
	zakres_kalendarza,
	zakres_tygodnia,
)


class TestZakresKalendarza(unittest.TestCase):
	def test_administrator(self):
		self.assertEqual(zakres_kalendarza("Administrator", []), "wszyscy")

	def test_system_manager(self):
		self.assertEqual(zakres_kalendarza("a@x.pl", ["System Manager"]), "wszyscy")

	def test_core_admin(self):
		self.assertEqual(zakres_kalendarza("a@x.pl", ["Volteo Core Admin"]), "wszyscy")

	def test_backend(self):
		self.assertEqual(zakres_kalendarza("a@x.pl", ["Volteo Backend"]), "wszyscy")

	def test_call_center(self):
		self.assertEqual(zakres_kalendarza("a@x.pl", ["Volteo Call Center"]), "wszyscy")

	def test_czysty_handlowiec(self):
		self.assertEqual(zakres_kalendarza("h@x.pl", ["Volteo D2D Sales", "Sales User"]), "wlasny")

	def test_handlowiec_z_cc_widzi_wszystkich(self):
		self.assertEqual(zakres_kalendarza("h@x.pl", ["Volteo D2D Sales", "Volteo Call Center"]), "wszyscy")

	def test_handlowiec_z_backendem_widzi_wszystkich(self):
		self.assertEqual(zakres_kalendarza("h@x.pl", ["Volteo D2D Sales", "Volteo Backend"]), "wszyscy")

	def test_inna_rola_brak_dostepu(self):
		self.assertIsNone(zakres_kalendarza("m@x.pl", ["Sales Manager"]))

	def test_brak_rol(self):
		self.assertIsNone(zakres_kalendarza("m@x.pl", []))

	def test_roles_none(self):
		self.assertIsNone(zakres_kalendarza("m@x.pl", None))

	def test_guest(self):
		self.assertIsNone(zakres_kalendarza("Guest", ["Guest"]))


class TestZakresTygodnia(unittest.TestCase):
	def test_srodek_tygodnia(self):
		# 2026-11-04 to sroda
		self.assertEqual(zakres_tygodnia("2026-11-04"), ("2026-11-02", "2026-11-08"))

	def test_poniedzialek(self):
		self.assertEqual(zakres_tygodnia("2026-11-02"), ("2026-11-02", "2026-11-08"))

	def test_niedziela(self):
		self.assertEqual(zakres_tygodnia("2026-11-08"), ("2026-11-02", "2026-11-08"))

	def test_przelom_roku(self):
		self.assertEqual(zakres_tygodnia("2026-12-31"), ("2026-12-28", "2027-01-03"))

	def test_przelom_miesiaca_wstecz(self):
		self.assertEqual(zakres_tygodnia("2026-09-01"), ("2026-08-31", "2026-09-06"))

	def test_z_godzina(self):
		self.assertEqual(zakres_tygodnia("2026-11-04 10:30:00"), ("2026-11-02", "2026-11-08"))

	def test_zly_format(self):
		with self.assertRaises(ValueError):
			zakres_tygodnia("04.11.2026")

	def test_nieistniejaca_data(self):
		with self.assertRaises(ValueError):
			zakres_tygodnia("2026-02-30")

	def test_none(self):
		with self.assertRaises(ValueError):
			zakres_tygodnia(None)


class TestZakresDnia(unittest.TestCase):
	def test_dzien(self):
		self.assertEqual(zakres_dnia("2026-11-04"), ("2026-11-04", "2026-11-04"))

	def test_dzien_z_godzina(self):
		self.assertEqual(zakres_dnia("2026-11-04 08:00"), ("2026-11-04", "2026-11-04"))

	def test_zly(self):
		with self.assertRaises(ValueError):
			zakres_dnia("jutro")


class TestWalidujZakresDat(unittest.TestCase):
	def test_poprawny_tydzien(self):
		waliduj_zakres_dat("2026-11-02", "2026-11-08")

	def test_jeden_dzien(self):
		waliduj_zakres_dat("2026-11-02", "2026-11-02")

	def test_od_pozniej_niz_do(self):
		with self.assertRaises(ValueError):
			waliduj_zakres_dat("2026-11-09", "2026-11-02")

	def test_zly_format(self):
		with self.assertRaises(ValueError):
			waliduj_zakres_dat("abc", "2026-11-02")

	def test_ponad_limit(self):
		with self.assertRaises(ValueError):
			waliduj_zakres_dat("2026-01-01", "2026-12-31")

	def test_dokladnie_limit(self):
		# 62 dni wlacznie
		waliduj_zakres_dat("2026-01-01", "2026-03-03")

	def test_limit_plus_jeden(self):
		with self.assertRaises(ValueError):
			waliduj_zakres_dat("2026-01-01", "2026-03-04")

	def test_wlasny_limit(self):
		with self.assertRaises(ValueError):
			waliduj_zakres_dat("2026-11-01", "2026-11-10", max_dni=7)


class TestGraniceCzasu(unittest.TestCase):
	def test_granice(self):
		self.assertEqual(
			granice_czasu("2026-11-02", "2026-11-08"),
			("2026-11-02 00:00:00", "2026-11-08 23:59:59"),
		)


class TestNormalizujTermin(unittest.TestCase):
	def test_spacja_bez_sekund(self):
		self.assertEqual(normalizuj_termin("2026-11-04 10:30"), "2026-11-04 10:30:00")

	def test_t_z_sekundami(self):
		self.assertEqual(normalizuj_termin("2026-11-04T10:30:15"), "2026-11-04 10:30:15")

	def test_pusty_string(self):
		self.assertIsNone(normalizuj_termin("  "))

	def test_none(self):
		self.assertIsNone(normalizuj_termin(None))

	def test_zly_format(self):
		with self.assertRaises(ValueError):
			normalizuj_termin("04.11.2026 10:30")

	def test_zla_godzina(self):
		with self.assertRaises(ValueError):
			normalizuj_termin("2026-11-04 25:00")

	def test_liczba(self):
		with self.assertRaises(ValueError):
			normalizuj_termin(123)


class TestNormalizujHandlowcow(unittest.TestCase):
	def test_none(self):
		self.assertEqual(normalizuj_handlowcow(None), [])

	def test_pusty_string(self):
		self.assertEqual(normalizuj_handlowcow(""), [])

	def test_json_string(self):
		self.assertEqual(normalizuj_handlowcow('["a@x.pl", "b@x.pl"]'), ["a@x.pl", "b@x.pl"])

	def test_lista(self):
		self.assertEqual(normalizuj_handlowcow(["a@x.pl", "b@x.pl"]), ["a@x.pl", "b@x.pl"])

	def test_pojedynczy_string(self):
		self.assertEqual(normalizuj_handlowcow("a@x.pl"), ["a@x.pl"])

	def test_duplikaty_i_puste(self):
		self.assertEqual(normalizuj_handlowcow(["a@x.pl", "a@x.pl", "", None, 5]), ["a@x.pl"])

	def test_json_nie_lista(self):
		self.assertEqual(normalizuj_handlowcow('{"a": 1}'), [])

	def test_json_string_w_stringu(self):
		self.assertEqual(normalizuj_handlowcow('"a@x.pl"'), ["a@x.pl"])


class TestPrzetnijHandlowcow(unittest.TestCase):
	def test_puste_zadanie_to_wszyscy(self):
		self.assertEqual(przetnij_handlowcow([], ["a", "b"]), ["a", "b"])

	def test_przeciecie_zachowuje_kolejnosc_dostepnych(self):
		self.assertEqual(przetnij_handlowcow(["b", "a"], ["a", "b", "c"]), ["a", "b"])

	def test_nieznane_pomijane(self):
		self.assertEqual(przetnij_handlowcow(["x@x.pl", "b"], ["a", "b"]), ["b"])

	def test_same_nieznane_daja_pusta(self):
		self.assertEqual(przetnij_handlowcow(["x"], ["a", "b"]), [])

	def test_regula_tylko_handlowcy_z_dostepem_do_leadow(self):
		# `dostepni` to wynik `_aktywni_d2d_reprezentanci()` (enabled, D2D, linia
		# Leady). Konto spoza tej listy (np. D2D bez linii Leady, CC, admin) nigdy
		# nie trafia na tablice, nawet gdy klient jawnie o nie poprosi.
		dostepni = ["h1@x.pl", "h2@x.pl"]
		zadani = ["h1@x.pl", "d2d-bez-linii-leady@x.pl", "cc@x.pl", "Administrator"]
		self.assertEqual(przetnij_handlowcow(zadani, dostepni), ["h1@x.pl"])
		self.assertEqual(przetnij_handlowcow([], dostepni), dostepni)


class TestPogrupujSpotkania(unittest.TestCase):
	def _w(self, owner, termin, name="L"):
		return {"name": name, "lead_owner": owner, "custom_termin_spotkania": termin}

	def test_kazdy_handlowiec_ma_klucz(self):
		wynik = pogrupuj_spotkania([], ["a", "b"])
		self.assertEqual(wynik, {"a": [], "b": []})

	def test_kolejnosc_handlowcow(self):
		wynik = pogrupuj_spotkania([], [{"user": "b"}, {"user": "a"}])
		self.assertEqual(list(wynik.keys()), ["b", "a"])

	def test_sortowanie_po_terminie(self):
		w = [self._w("a", "2026-11-03 12:00:00", "2"), self._w("a", "2026-11-02 09:00:00", "1")]
		wynik = pogrupuj_spotkania(w, ["a"])
		self.assertEqual([x["name"] for x in wynik["a"]], ["1", "2"])

	def test_pomija_bez_terminu(self):
		wynik = pogrupuj_spotkania([self._w("a", None)], ["a"])
		self.assertEqual(wynik["a"], [])

	def test_pomija_obcego_wlasciciela(self):
		wynik = pogrupuj_spotkania([self._w("z", "2026-11-02 09:00:00")], ["a"])
		self.assertEqual(wynik, {"a": []})

	def test_rozdzielenie_po_handlowcach(self):
		w = [self._w("a", "2026-11-02 09:00:00", "1"), self._w("b", "2026-11-02 10:00:00", "2")]
		wynik = pogrupuj_spotkania(w, ["a", "b"])
		self.assertEqual([x["name"] for x in wynik["a"]], ["1"])
		self.assertEqual([x["name"] for x in wynik["b"]], ["2"])

	def test_none_wejscia(self):
		self.assertEqual(pogrupuj_spotkania(None, None), {})

	def test_termin_jako_datetime(self):
		from datetime import datetime

		w = [self._w("a", datetime(2026, 11, 3, 8, 0), "2"), self._w("a", datetime(2026, 11, 2, 8, 0), "1")]
		wynik = pogrupuj_spotkania(w, ["a"])
		self.assertEqual([x["name"] for x in wynik["a"]], ["1", "2"])


if __name__ == "__main__":
	unittest.main()
