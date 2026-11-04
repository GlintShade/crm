# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest

from crm.volteo_kalendarz import (
	DNI_TYGODNIA,
	dni_zakresu,
	dostepnosc_handlowcow,
	granice_czasu,
	moze_edytowac_grafik,
	normalizuj_handlowcow,
	normalizuj_okna,
	normalizuj_termin,
	normalizuj_tydzien,
	plan_zapisu,
	pogrupuj_spotkania,
	przetnij_handlowcow,
	rozwin_dostepnosc,
	waliduj_wiersz_dostepnosci,
	waliduj_zakres_dat,
	wiersze_dnia,
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


class TestGrafikUprawnienia(unittest.TestCase):
	def test_role_grafiku(self):
		for rola in ("System Manager", "Volteo Core Admin", "Volteo Backend"):
			self.assertTrue(moze_edytowac_grafik("a@x.pl", [rola]))

	def test_administrator(self):
		self.assertTrue(moze_edytowac_grafik("Administrator", []))

	def test_call_center_i_handlowiec_nie(self):
		self.assertFalse(moze_edytowac_grafik("a@x.pl", ["Volteo Call Center"]))
		self.assertFalse(moze_edytowac_grafik("a@x.pl", ["Volteo D2D Sales"]))
		self.assertFalse(moze_edytowac_grafik("a@x.pl", None))


class TestNormalizujOkna(unittest.TestCase):
	def test_puste_to_wolne(self):
		self.assertEqual(normalizuj_okna([]), [])
		self.assertEqual(normalizuj_okna(None), [])

	def test_sortuje_i_scala(self):
		self.assertEqual(normalizuj_okna([[14, 22], [8, 12], [12, 13]]), [[8, 13], [14, 22]])

	def test_nachodzace(self):
		self.assertEqual(normalizuj_okna([[8, 15], [10, 20]]), [[8, 20]])

	def test_godziny_jako_tekst_i_float(self):
		self.assertEqual(normalizuj_okna([["8", 14.0]]), [[8, 14]])

	def test_caly_dzien(self):
		self.assertEqual(normalizuj_okna([[0, 24]]), [[0, 24]])

	def test_bledy(self):
		for zle in (
			[[14, 8]],
			[[8, 8]],
			[[-1, 5]],
			[[20, 25]],
			[[8.5, 10]],
			[[True, 5]],
			[[8]],
			"8-14",
			[["a", 5]],
		):
			with self.assertRaises(ValueError, msg=repr(zle)):
				normalizuj_okna(zle)


class TestNormalizujTydzien(unittest.TestCase):
	def test_json(self):
		t = normalizuj_tydzien("[[[0,24]],[[0,24]],[[0,24]],[],[],[],[]]")
		self.assertEqual(t[0], [[0, 24]])
		self.assertEqual(t[6], [])

	def test_zla_liczba_dni(self):
		with self.assertRaises(ValueError):
			normalizuj_tydzien([[]] * 6)

	def test_zly_json(self):
		with self.assertRaises(ValueError):
			normalizuj_tydzien("{nie json")


class TestWalidujWierszDostepnosci(unittest.TestCase):
	def test_wzor_poprawny(self):
		self.assertIsNone(waliduj_wiersz_dostepnosci("Poniedziałek", None, 0, 8, 14))

	def test_zmiana_na_dzien(self):
		self.assertIsNone(waliduj_wiersz_dostepnosci("", "2026-11-06", 0, 14, 22))

	def test_wolne_bez_godzin(self):
		self.assertIsNone(waliduj_wiersz_dostepnosci("Piątek", None, 1, None, None))

	def test_brak_dnia_i_daty(self):
		self.assertIsNotNone(waliduj_wiersz_dostepnosci("", None, 0, 8, 14))

	def test_zla_data(self):
		self.assertIsNotNone(waliduj_wiersz_dostepnosci("", "2026-13-40", 0, 8, 14))

	def test_zle_godziny(self):
		self.assertIsNotNone(waliduj_wiersz_dostepnosci("Wtorek", None, 0, 14, 8))
		self.assertIsNotNone(waliduj_wiersz_dostepnosci("Wtorek", None, 0, None, None))


class TestDniZakresu(unittest.TestCase):
	def test_tydzien(self):
		dni = dni_zakresu("2026-11-02", "2026-11-08")
		self.assertEqual(len(dni), 7)
		self.assertEqual(dni[0], "2026-11-02")
		self.assertEqual(dni[-1], "2026-11-08")

	def test_przelom_miesiaca(self):
		self.assertEqual(dni_zakresu("2026-10-31", "2026-11-01"), ["2026-10-31", "2026-11-01"])


TYDZIEN = dni_zakresu("2026-11-02", "2026-11-08")


class TestRozwinDostepnosc(unittest.TestCase):
	def test_brak_wierszy_to_brak_grafiku(self):
		self.assertIsNone(rozwin_dostepnosc([], TYDZIEN))

	def test_wzor_tygodniowy(self):
		wiersze = [
			{"dzien_tygodnia": d, "data": None, "wolne": 0, "od": 0, "do": 24} for d in DNI_TYGODNIA[:3]
		] + [
			{"dzien_tygodnia": d, "data": None, "wolne": 1, "od": None, "do": None} for d in DNI_TYGODNIA[3:]
		]
		wynik = rozwin_dostepnosc(wiersze, TYDZIEN)
		self.assertEqual(wynik["2026-11-02"], [[0, 24]])
		self.assertEqual(wynik["2026-11-05"], [])
		self.assertEqual(wynik["2026-11-08"], [])

	def test_zmiana_zastepuje_wzor(self):
		wiersze = [
			{"dzien_tygodnia": "Piątek", "data": None, "wolne": 0, "od": 8, "do": 20},
			{"dzien_tygodnia": "", "data": "2026-11-06", "wolne": 1, "od": None, "do": None},
		]
		wynik = rozwin_dostepnosc(wiersze, TYDZIEN)
		self.assertEqual(wynik["2026-11-06"], [])

	def test_dzien_bez_wzoru_to_none(self):
		wiersze = [{"dzien_tygodnia": "Poniedziałek", "data": None, "wolne": 0, "od": 8, "do": 14}]
		wynik = rozwin_dostepnosc(wiersze, TYDZIEN)
		self.assertEqual(wynik["2026-11-02"], [[8, 14]])
		self.assertIsNone(wynik["2026-11-03"])

	def test_kilka_okien_dnia(self):
		wiersze = [
			{"dzien_tygodnia": "Wtorek", "data": None, "wolne": 0, "od": 14, "do": 18},
			{"dzien_tygodnia": "Wtorek", "data": None, "wolne": 0, "od": 8, "do": 12},
		]
		self.assertEqual(rozwin_dostepnosc(wiersze, TYDZIEN)["2026-11-03"], [[8, 12], [14, 18]])

	def test_zepsuty_wiersz_pominiety(self):
		wiersze = [
			{"dzien_tygodnia": "Wtorek", "data": None, "wolne": 0, "od": 18, "do": 10},
			{"dzien_tygodnia": "Wtorek", "data": None, "wolne": 0, "od": 8, "do": 12},
		]
		self.assertEqual(rozwin_dostepnosc(wiersze, TYDZIEN)["2026-11-03"], [[8, 12]])

	def test_data_jako_obiekt_date(self):
		from datetime import date

		wiersze = [{"dzien_tygodnia": "", "data": date(2026, 11, 4), "wolne": 0, "od": 9, "do": 10}]
		self.assertEqual(rozwin_dostepnosc(wiersze, TYDZIEN)["2026-11-04"], [[9, 10]])


class TestDostepnoscHandlowcow(unittest.TestCase):
	def test_kazdy_handlowiec_ma_klucz(self):
		wiersze = [
			{
				"handlowiec": "a@x.pl",
				"dzien_tygodnia": "Poniedziałek",
				"data": None,
				"wolne": 0,
				"od": 8,
				"do": 14,
			},
			{
				"handlowiec": "a@x.pl",
				"dzien_tygodnia": "",
				"data": "2026-11-03",
				"wolne": 1,
				"od": None,
				"do": None,
			},
			{"handlowiec": "obcy@x.pl", "dzien_tygodnia": "Poniedziałek", "data": None, "wolne": 1},
		]
		dost, zmiany = dostepnosc_handlowcow(wiersze, ["a@x.pl", "b@x.pl"], TYDZIEN)
		self.assertEqual(set(dost), {"a@x.pl", "b@x.pl"})
		self.assertIsNone(dost["b@x.pl"])
		self.assertEqual(dost["a@x.pl"]["2026-11-02"], [[8, 14]])
		self.assertEqual(zmiany["a@x.pl"], ["2026-11-03"])
		self.assertEqual(zmiany["b@x.pl"], [])

	def test_zmiana_spoza_zakresu_nie_w_liscie(self):
		wiersze = [{"handlowiec": "a@x.pl", "dzien_tygodnia": "", "data": "2026-12-01", "wolne": 1}]
		_, zmiany = dostepnosc_handlowcow(wiersze, ["a@x.pl"], TYDZIEN)
		self.assertEqual(zmiany["a@x.pl"], [])


class TestWierszeDnia(unittest.TestCase):
	def test_wolne(self):
		self.assertEqual(wiersze_dnia([]), [{"wolne": 1, "od": None, "do": None}])

	def test_okna(self):
		self.assertEqual(
			wiersze_dnia([[14, 22], [8, 12]]),
			[{"wolne": 0, "od": 8, "do": 12}, {"wolne": 0, "od": 14, "do": 22}],
		)


TYDZ_KAMILA = (((0, 24),), ((0, 24),), ((0, 24),), (), (), (), ())


class TestPlanZapisu(unittest.TestCase):
	TYDZ = [[list(o) for o in d] for d in TYDZ_KAMILA]  # noqa: RUF012

	def test_staly(self):
		plan = plan_zapisu(self.TYDZ, "staly", "2026-11-02", {})
		self.assertEqual(plan["wzor"], self.TYDZ)
		self.assertEqual(plan["zmiany"], {})
		self.assertEqual(plan["usun_zmiany"], TYDZIEN)

	def test_tydzien_tylko_rozne_dni(self):
		wzor = {d: [[0, 24]] for d in DNI_TYGODNIA[:3]}
		wzor.update({d: [] for d in DNI_TYGODNIA[3:]})
		tydz = [list(d) for d in self.TYDZ]
		tydz[4] = [[8, 12]]
		plan = plan_zapisu(tydz, "tydzien", "2026-11-02", wzor)
		self.assertIsNone(plan["wzor"])
		self.assertEqual(plan["zmiany"], {"2026-11-06": [[8, 12]]})
		self.assertEqual(plan["usun_zmiany"], TYDZIEN)

	def test_tydzien_bez_wzoru_wszystkie_dni(self):
		plan = plan_zapisu(self.TYDZ, "tydzien", "2026-11-02", {})
		self.assertEqual(len(plan["zmiany"]), 7)

	def test_nie_poniedzialek(self):
		with self.assertRaises(ValueError):
			plan_zapisu(self.TYDZ, "staly", "2026-11-03", {})

	def test_zly_zakres(self):
		with self.assertRaises(ValueError):
			plan_zapisu(self.TYDZ, "zawsze", "2026-11-02", {})


# --- Kalendarz na zywo (ops#331) ---------------------------------------------
# Osobny blok importow na koncu pliku: rownolegla sesja zmienia liste importow
# na gorze, a tak scalenie nie ma konfliktu.
from datetime import date as _date
from datetime import datetime as _datetime

from crm.volteo_kalendarz import (
	MAKS_DAT_SYGNALU,
	POLA_KALENDARZA_LEADA,
	polacz_daty,
	tresc_sygnalu,
	zmiana_dostepnosci,
	zmiana_kalendarza_leada,
)


def _lead(**nadpisz):
	stan = {
		"custom_termin_spotkania": _datetime(2026, 11, 5, 10, 0),
		"lead_owner": "jan@x.pl",
		"status": "Umówione",
		"converted": 0,
		"lead_name": "Anna Nowak",
		"custom_install_city": "Kraków",
		"mobile_no": "+48 600 000 000",
	}
	stan.update(nadpisz)
	return stan


class TestZmianaKalendarzaLeada(unittest.TestCase):
	def test_bez_zmian(self):
		self.assertIsNone(zmiana_kalendarza_leada(_lead(), _lead()))

	def test_zmiana_pola_spoza_kalendarza_nie_dotyczy(self):
		przed = _lead()
		po = dict(_lead(), custom_cc="cc@x.pl", email="a@b.pl")
		przed["custom_cc"] = "inny@x.pl"
		self.assertIsNone(zmiana_kalendarza_leada(przed, po))

	def test_lead_bez_terminu_nie_dotyczy(self):
		przed = _lead(custom_termin_spotkania=None)
		po = _lead(custom_termin_spotkania=None, status="Nowy")
		self.assertIsNone(zmiana_kalendarza_leada(przed, po))

	def test_przesuniecie_terminu_daje_obie_daty(self):
		po = _lead(custom_termin_spotkania="2026-11-07 12:00:00")
		self.assertEqual(zmiana_kalendarza_leada(_lead(), po), ["2026-11-05", "2026-11-07"])

	def test_zmiana_godziny_tego_samego_dnia(self):
		po = _lead(custom_termin_spotkania="2026-11-05 14:30:00")
		self.assertEqual(zmiana_kalendarza_leada(_lead(), po), ["2026-11-05"])

	def test_ustawienie_terminu(self):
		przed = _lead(custom_termin_spotkania=None)
		self.assertEqual(zmiana_kalendarza_leada(przed, _lead()), ["2026-11-05"])

	def test_wyczyszczenie_terminu(self):
		po = _lead(custom_termin_spotkania="")
		self.assertEqual(zmiana_kalendarza_leada(_lead(), po), ["2026-11-05"])

	def test_kazde_pole_kalendarza_jest_istotne(self):
		zmienione = {
			"lead_owner": "ola@x.pl",
			"status": "Stracony",
			"converted": 1,
			"lead_name": "Anna Kowalska",
			"custom_install_city": "Tarnów",
			"mobile_no": "+48 600 000 001",
		}
		for pole in POLA_KALENDARZA_LEADA:
			if pole == "custom_termin_spotkania":
				continue
			with self.subTest(pole=pole):
				po = _lead(**{pole: zmienione[pole]})
				self.assertEqual(zmiana_kalendarza_leada(_lead(), po), ["2026-11-05"])

	def test_ten_sam_termin_w_innym_formacie_to_brak_zmiany(self):
		for wartosc in ("2026-11-05 10:00:00", "2026-11-05T10:00", "2026-11-05 10:00:00.000000"):
			with self.subTest(wartosc=wartosc):
				po = _lead(custom_termin_spotkania=wartosc)
				self.assertIsNone(zmiana_kalendarza_leada(_lead(), po))

	def test_converted_liczba_i_tekst_to_brak_zmiany(self):
		self.assertIsNone(zmiana_kalendarza_leada(_lead(converted=0), _lead(converted="0")))
		self.assertIsNone(zmiana_kalendarza_leada(_lead(converted=False), _lead(converted=0)))

	def test_nowy_lead_z_terminem(self):
		self.assertEqual(zmiana_kalendarza_leada(None, _lead()), ["2026-11-05"])

	def test_nowy_lead_bez_terminu(self):
		self.assertIsNone(zmiana_kalendarza_leada(None, _lead(custom_termin_spotkania=None)))

	def test_usuniecie_leada_z_terminem(self):
		self.assertEqual(zmiana_kalendarza_leada(_lead(), None), ["2026-11-05"])

	def test_usuniecie_leada_bez_terminu(self):
		self.assertIsNone(zmiana_kalendarza_leada(_lead(custom_termin_spotkania=None), None))

	def test_zly_termin_ignorowany(self):
		po = _lead(custom_termin_spotkania="jutro")
		self.assertEqual(zmiana_kalendarza_leada(_lead(), po), ["2026-11-05"])


def _wiersz(**nadpisz):
	stan = {
		"handlowiec": "jan@x.pl",
		"dzien_tygodnia": "",
		"data": _date(2026, 11, 6),
		"wolne": 0,
		"od": 8,
		"do": 16,
	}
	stan.update(nadpisz)
	return stan


class TestZmianaDostepnosci(unittest.TestCase):
	def test_nowa_zmiana_na_dzien(self):
		self.assertEqual(zmiana_dostepnosci(None, _wiersz()), ["2026-11-06"])

	def test_usuniecie_zmiany_na_dzien(self):
		self.assertEqual(zmiana_dostepnosci(_wiersz(), None), ["2026-11-06"])

	def test_przeniesienie_zmiany_na_inny_dzien(self):
		po = _wiersz(data="2026-11-09")
		self.assertEqual(zmiana_dostepnosci(_wiersz(), po), ["2026-11-06", "2026-11-09"])

	def test_wzor_tygodniowy_dotyczy_wszystkich_dat(self):
		wzor = _wiersz(dzien_tygodnia="Poniedziałek", data=None)
		self.assertEqual(zmiana_dostepnosci(None, wzor), [])
		self.assertEqual(zmiana_dostepnosci(wzor, None), [])

	def test_zmiana_wzoru_na_dzien_dotyczy_wszystkich_dat(self):
		wzor = _wiersz(dzien_tygodnia="Poniedziałek", data=None)
		self.assertEqual(zmiana_dostepnosci(wzor, _wiersz()), [])

	def test_zapis_bez_zmian(self):
		self.assertIsNone(zmiana_dostepnosci(_wiersz(), _wiersz(data="2026-11-06")))

	def test_zmiana_godzin(self):
		self.assertEqual(zmiana_dostepnosci(_wiersz(), _wiersz(do=18)), ["2026-11-06"])

	def test_brak_stanow(self):
		self.assertIsNone(zmiana_dostepnosci(None, None))


class TestPolaczDaty(unittest.TestCase):
	def test_brak_zmian(self):
		self.assertIsNone(polacz_daty(None, None))

	def test_pierwsza_zmiana(self):
		self.assertEqual(polacz_daty(None, ["2026-11-06", "2026-11-05"]), ["2026-11-05", "2026-11-06"])

	def test_nowe_none_nie_zmienia(self):
		self.assertEqual(polacz_daty(["2026-11-05"], None), ["2026-11-05"])

	def test_suma_bez_duplikatow(self):
		self.assertEqual(
			polacz_daty(["2026-11-05", "2026-11-06"], ["2026-11-06", "2026-11-07"]),
			["2026-11-05", "2026-11-06", "2026-11-07"],
		)

	def test_wszystkie_pochlaniaja(self):
		self.assertEqual(polacz_daty([], ["2026-11-05"]), [])
		self.assertEqual(polacz_daty(["2026-11-05"], []), [])

	def test_za_duzo_dat_zwija_do_wszystkich(self):
		daty = [f"2026-12-{d:02d}" for d in range(1, MAKS_DAT_SYGNALU + 1)]
		self.assertEqual(len(polacz_daty(None, daty)), MAKS_DAT_SYGNALU)
		self.assertEqual(polacz_daty(daty, ["2027-01-01"]), [])

	def test_masowy_przydzial_jeden_sygnal(self):
		zebrane = None
		for dzien in (5, 5, 6, 5, 7):
			zebrane = polacz_daty(zebrane, [f"2026-11-{dzien:02d}"])
		self.assertEqual(zebrane, ["2026-11-05", "2026-11-06", "2026-11-07"])


class TestTrescSygnalu(unittest.TestCase):
	def test_tylko_daty(self):
		self.assertEqual(tresc_sygnalu(["2026-11-05"]), {"daty": ["2026-11-05"]})

	def test_wszystkie(self):
		self.assertEqual(tresc_sygnalu([]), {"daty": []})
		self.assertEqual(tresc_sygnalu(None), {"daty": []})
