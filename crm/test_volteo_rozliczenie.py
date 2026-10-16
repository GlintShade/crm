# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import datetime
import json
import unittest
from decimal import Decimal
from typing import ClassVar

from crm.volteo_rozliczenie import (
	STANY_SZANSY,
	STATUSY_WIERSZA,
	ZNACZNIK_ROZLICZENIE,
	ZRODLA_KWOTY,
	data_podpisania,
	formatuj_kwote,
	kwoty_odbiorcow,
	licznik,
	parsuj_tokeny,
	pola_szansy,
	stan_zbiorczy,
	sumy,
	tekst_sladu,
	tokeny_odbiorcow,
	waliduj_kwote,
	waliduj_unikalnosc,
	waliduj_wyplate,
	warunek_naliczenia,
	zakres_okresu,
)

D = datetime.date


def w(rola, status, kwota="100", data=None, name=None):
	return {"rola": rola, "status": status, "kwota": kwota, "data_wyplaty": data, "name": name}


class TestStale(unittest.TestCase):
	def test_stale(self):
		self.assertEqual(STATUSY_WIERSZA, ("Do wypłaty", "Wypłacone", "Wstrzymane", "Nie dotyczy"))
		self.assertEqual(ZRODLA_KWOTY, ("Snapshot", "Ręcznie", "Automat"))
		self.assertEqual(ZNACZNIK_ROZLICZENIE, "[volteo:rozliczenie]")
		self.assertIn("", STANY_SZANSY)
		self.assertEqual(len(STANY_SZANSY), 6)


class TestStanZbiorczy(unittest.TestCase):
	def test_brak_wierszy(self):
		self.assertEqual(stan_zbiorczy([]), "")

	def test_wszystkie_nie_dotyczy(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Nie dotyczy"), w("Manager", "Nie dotyczy")]), "Nie dotyczy"
		)

	def test_wstrzymane_bez_do_wyplaty(self):
		self.assertEqual(stan_zbiorczy([w("Handlowiec", "Wstrzymane")]), "Wstrzymane")

	def test_wstrzymane_z_wyplaconym_bez_do_wyplaty(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Wypłacone"), w("Manager", "Wstrzymane")]), "Wstrzymane"
		)

	def test_wstrzymane_z_do_wyplaty_to_nierozliczone(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Wstrzymane"), w("Manager", "Do wypłaty")]), "Nierozliczone"
		)

	def test_wszystkie_wyplacone(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Wypłacone"), w("Manager", "Wypłacone")]), "Rozliczone"
		)

	def test_wyplacone_plus_nie_dotyczy_to_rozliczone(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Wypłacone"), w("Partner", "Nie dotyczy")]), "Rozliczone"
		)

	def test_zaden_wyplacony(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Do wypłaty"), w("Manager", "Do wypłaty")]), "Nierozliczone"
		)

	def test_czesciowo(self):
		self.assertEqual(
			stan_zbiorczy([w("Handlowiec", "Wypłacone"), w("Manager", "Do wypłaty")]), "Częściowo rozliczone"
		)

	def test_generator_na_wejsciu(self):
		self.assertEqual(stan_zbiorczy(x for x in [w("Handlowiec", "Wypłacone")]), "Rozliczone")


class TestLicznik(unittest.TestCase):
	def test_brak_wierszy(self):
		self.assertEqual(licznik([]), "")

	def test_sam_handlowiec(self):
		self.assertEqual(licznik([w("Handlowiec", "Do wypłaty")]), "0/1")
		self.assertEqual(licznik([w("Handlowiec", "Wypłacone")]), "1/1")

	def test_nie_dotyczy_pominiete(self):
		wiersze = [w("Handlowiec", "Wypłacone"), w("Manager", "Do wypłaty"), w("Partner", "Nie dotyczy")]
		self.assertEqual(licznik(wiersze), "1/2")

	def test_trzy_role(self):
		wiersze = [w("Handlowiec", "Wypłacone"), w("Manager", "Wypłacone"), w("Partner", "Wypłacone")]
		self.assertEqual(licznik(wiersze), "3/3")

	def test_same_nie_dotyczy(self):
		self.assertEqual(licznik([w("Handlowiec", "Nie dotyczy")]), "")

	def test_wstrzymane_liczy_sie_do_mianownika(self):
		self.assertEqual(licznik([w("Handlowiec", "Wstrzymane"), w("Manager", "Wypłacone")]), "1/2")


class TestTokeny(unittest.TestCase):
	def test_kolejnosc_h_m_p_niezaleznie_od_wejscia(self):
		wiersze = [w("Partner", "Wstrzymane"), w("Handlowiec", "Wypłacone"), w("Manager", "Do wypłaty")]
		self.assertEqual(tokeny_odbiorcow(wiersze), "H:W;M:D;P:S")

	def test_tylko_istniejace_wiersze(self):
		self.assertEqual(tokeny_odbiorcow([w("Handlowiec", "Nie dotyczy")]), "H:N")
		self.assertEqual(tokeny_odbiorcow([]), "")

	def test_parsuj_odwrotnosc(self):
		self.assertEqual(
			parsuj_tokeny("H:W;M:D;P:S"),
			{"Handlowiec": "Wypłacone", "Manager": "Do wypłaty", "Partner": "Wstrzymane"},
		)

	def test_parsuj_tolerancyjnie(self):
		self.assertEqual(
			parsuj_tokeny(" h:w ; X:Y ;;M:q; garbage ; P:n "),
			{"Handlowiec": "Wypłacone", "Partner": "Nie dotyczy"},
		)

	def test_parsuj_puste(self):
		self.assertEqual(parsuj_tokeny(""), {})
		self.assertEqual(parsuj_tokeny(None), {})

	def test_round_trip(self):
		wiersze = [w("Handlowiec", "Wypłacone"), w("Partner", "Nie dotyczy")]
		self.assertEqual(
			parsuj_tokeny(tokeny_odbiorcow(wiersze)), {"Handlowiec": "Wypłacone", "Partner": "Nie dotyczy"}
		)


class TestSumy(unittest.TestCase):
	def test_puste(self):
		s = sumy([])
		self.assertEqual(s["do_wyplaty"], Decimal("0"))
		self.assertEqual(s["wyplacono"], Decimal("0"))
		self.assertEqual(s["lacznie"], Decimal("0"))
		self.assertIsNone(s["ostatnia_wyplata"])

	def test_sumy_i_ostatnia_wyplata(self):
		wiersze = [
			w("Handlowiec", "Wypłacone", "2400.50", "2026-10-06"),
			w("Manager", "Wypłacone", Decimal("100"), D(2026, 10, 9)),
			w("Partner", "Wstrzymane", "50,25"),
		]
		s = sumy(wiersze)
		self.assertEqual(s["wyplacono"], Decimal("2500.50"))
		self.assertEqual(s["do_wyplaty"], Decimal("50.25"))
		self.assertEqual(s["lacznie"], Decimal("2550.75"))
		self.assertEqual(s["ostatnia_wyplata"], D(2026, 10, 9))

	def test_nie_dotyczy_nie_wchodzi_do_sum(self):
		s = sumy([w("Handlowiec", "Nie dotyczy", "999"), w("Manager", "Do wypłaty", "10")])
		self.assertEqual(s["lacznie"], Decimal("10.00"))

	def test_kwota_none_lub_smiec_to_zero(self):
		s = sumy([w("Handlowiec", "Do wypłaty", None), w("Manager", "Do wypłaty", "abc")])
		self.assertEqual(s["do_wyplaty"], Decimal("0"))

	def test_wyplacone_bez_daty(self):
		s = sumy([w("Handlowiec", "Wypłacone", "10", None)])
		self.assertIsNone(s["ostatnia_wyplata"])
		self.assertEqual(s["wyplacono"], Decimal("10.00"))

	def test_zaokraglenie_half_up(self):
		s = sumy([w("Handlowiec", "Do wypłaty", "0.005"), w("Manager", "Do wypłaty", "0.015")])
		self.assertEqual(s["do_wyplaty"], Decimal("0.03"))


class TestPolaSzansy(unittest.TestCase):
	def test_brak_wierszy(self):
		p = pola_szansy([])
		self.assertEqual(p["status"], "")
		self.assertEqual(p["odbiorcy"], "")
		self.assertEqual(p["licznik"], "")
		self.assertIsNone(p["ostatnia_wyplata"])
		self.assertEqual(p["do_wyplaty"], Decimal("0"))
		self.assertEqual(p["wyplacono"], Decimal("0"))

	def test_sesc_kluczy(self):
		p = pola_szansy([w("Handlowiec", "Wypłacone", "10", "2026-10-01"), w("Manager", "Do wypłaty", "5")])
		self.assertEqual(
			set(p), {"status", "odbiorcy", "licznik", "ostatnia_wyplata", "do_wyplaty", "wyplacono"}
		)
		self.assertEqual(p["status"], "Częściowo rozliczone")
		self.assertEqual(p["odbiorcy"], "H:W;M:D")
		self.assertEqual(p["licznik"], "1/2")
		self.assertEqual(p["ostatnia_wyplata"], D(2026, 10, 1))


class TestWalidacje(unittest.TestCase):
	def test_wyplata_bez_daty(self):
		self.assertIn("daty", waliduj_wyplate("Wypłacone", None))
		self.assertIsNotNone(waliduj_wyplate("Wypłacone", ""))

	def test_wyplata_z_data(self):
		self.assertIsNone(waliduj_wyplate("Wypłacone", "2026-10-06"))
		self.assertIsNone(waliduj_wyplate("Wypłacone", D(2026, 10, 6)))

	def test_inny_status_bez_daty_ok(self):
		self.assertIsNone(waliduj_wyplate("Do wypłaty", None))

	def test_kwota_ujemna(self):
		self.assertIn("ujemna", waliduj_kwote("-1"))

	def test_kwota_zero_i_dodatnia_ok(self):
		self.assertIsNone(waliduj_kwote(0))
		self.assertIsNone(waliduj_kwote("2 400,50"))
		self.assertIsNone(waliduj_kwote(Decimal("10")))

	def test_kwota_smiec(self):
		self.assertIsNotNone(waliduj_kwote("abc"))
		self.assertIsNotNone(waliduj_kwote(None))
		self.assertIsNotNone(waliduj_kwote(float("nan")))

	def test_unikalnosc_duplikat(self):
		istniejace = [w("Handlowiec", "Do wypłaty", name="a")]
		self.assertIn("Handlowiec", waliduj_unikalnosc(istniejace, {"rola": "Handlowiec", "name": "b"}))

	def test_unikalnosc_ta_sama_pozycja_ok(self):
		istniejace = [w("Handlowiec", "Do wypłaty", name="a")]
		self.assertIsNone(waliduj_unikalnosc(istniejace, {"rola": "Handlowiec", "name": "a"}))

	def test_unikalnosc_inna_rola_ok(self):
		istniejace = [w("Handlowiec", "Do wypłaty", name="a")]
		self.assertIsNone(waliduj_unikalnosc(istniejace, {"rola": "Manager"}))

	def test_unikalnosc_nowy_bez_nazwy_koliduje(self):
		istniejace = [w("Manager", "Do wypłaty", name="a")]
		self.assertIsNotNone(waliduj_unikalnosc(istniejace, {"rola": "Manager"}))

	def test_unikalnosc_nieznana_rola(self):
		self.assertIsNotNone(waliduj_unikalnosc([], {"rola": "Szef"}))


class TestKwotyOdbiorcow(unittest.TestCase):
	CP: ClassVar[dict] = {
		"custom_cp_prowizja_handlowa": "2400.00",
		"custom_cp_nadprowizja_manager": Decimal("300"),
		"custom_cp_nadprowizja_partner": 150,
	}

	def test_cp_trzy_role(self):
		k = kwoty_odbiorcow("Czyste Powietrze", None, self.CP, "h@x.pl", "m@x.pl")
		self.assertEqual(set(k), {"Handlowiec", "Manager", "Partner"})
		self.assertEqual(
			k["Handlowiec"], {"kwota": Decimal("2400.00"), "zrodlo": "Snapshot", "odbiorca": "h@x.pl"}
		)
		self.assertEqual(k["Manager"]["kwota"], Decimal("300.00"))
		self.assertEqual(k["Manager"]["odbiorca"], "m@x.pl")
		self.assertEqual(k["Partner"]["kwota"], Decimal("150.00"))
		self.assertIsNone(k["Partner"]["odbiorca"])

	def test_cp_zera_bez_wiersza_managera_i_partnera(self):
		pola = {**self.CP, "custom_cp_nadprowizja_manager": 0, "custom_cp_nadprowizja_partner": None}
		k = kwoty_odbiorcow("Czyste Powietrze", None, pola, "h@x.pl", None)
		self.assertEqual(set(k), {"Handlowiec"})

	def test_cp_brak_pol_handlowiec_reczny(self):
		k = kwoty_odbiorcow("Czyste Powietrze", None, None, "h@x.pl", None)
		self.assertIsNone(k["Handlowiec"]["kwota"])
		self.assertEqual(k["Handlowiec"]["zrodlo"], "Ręcznie")

	def test_cp_manager_bez_wezla(self):
		k = kwoty_odbiorcow("Czyste Powietrze", None, self.CP, "h@x.pl", None)
		self.assertIsNone(k["Manager"]["odbiorca"])

	def test_oze_narzut_ze_snapshotu_dict(self):
		snap = {"skladniki_marzy": [{"klucz": "marza", "kwota": "1"}, {"klucz": "narzut", "kwota": "1234.5"}]}
		k = kwoty_odbiorcow("Fotowoltaika", snap, None, "h@x.pl", "m@x.pl")
		self.assertEqual(set(k), {"Handlowiec"})
		self.assertEqual(
			k["Handlowiec"], {"kwota": Decimal("1234.50"), "zrodlo": "Snapshot", "odbiorca": "h@x.pl"}
		)

	def test_oze_snapshot_jako_json_string(self):
		snap = json.dumps({"skladniki_marzy": [{"klucz": "narzut", "kwota": "700.00"}]})
		k = kwoty_odbiorcow("Magazyn energii", snap, None, "h@x.pl", None)
		self.assertEqual(k["Handlowiec"]["kwota"], Decimal("700.00"))

	def test_oze_snapshot_zagniezdzony_w_podsumowaniu(self):
		snap = {"podsumowanie": {"skladniki_marzy": [{"klucz": "narzut", "kwota": "5"}]}}
		self.assertEqual(
			kwoty_odbiorcow("Fotowoltaika", snap, None, "h", None)["Handlowiec"]["kwota"], Decimal("5.00")
		)

	def test_oze_brak_narzutu_lub_snapshotu(self):
		for snap in (None, "", "{zepsuty", {}, {"skladniki_marzy": [{"klucz": "marza", "kwota": "1"}]}):
			k = kwoty_odbiorcow("Fotowoltaika", snap, None, "h@x.pl", None)
			self.assertIsNone(k["Handlowiec"]["kwota"])
			self.assertEqual(k["Handlowiec"]["zrodlo"], "Ręcznie")

	def test_nieznany_rodzaj_to_oze(self):
		k = kwoty_odbiorcow(None, None, None, "h@x.pl", None)
		self.assertEqual(set(k), {"Handlowiec"})


class TestWarunekNaliczenia(unittest.TestCase):
	def test_dzis_zawsze_false(self):
		self.assertFalse(warunek_naliczenia({}))
		self.assertFalse(warunek_naliczenia({"oplacone": True, "zamontowane": True}))


class TestDataPodpisania(unittest.TestCase):
	def test_brak_wpisu(self):
		self.assertIsNone(data_podpisania([]))
		self.assertIsNone(data_podpisania([{"to": "Lead", "to_date": "2026-10-01"}]))

	def test_najpozniejszy_wpis(self):
		wpisy = [
			{"to": "Umowa Podpisana", "to_date": "2026-10-01 10:00:00"},
			{"to": "Umowa Podpisana", "to_date": datetime.datetime(2026, 10, 5, 8, 0)},
			{"to": "Finansowanie", "to_date": "2026-10-09"},
		]
		self.assertEqual(data_podpisania(wpisy), D(2026, 10, 5))


class TestZakresOkresu(unittest.TestCase):
	def test_dzisiaj(self):
		self.assertEqual(zakres_okresu("dzisiaj", D(2026, 10, 16)), (D(2026, 10, 16), D(2026, 10, 16)))

	def test_tydzien_od_poniedzialku(self):
		# 2026-10-16 to piątek
		self.assertEqual(zakres_okresu("ten_tydzien", D(2026, 10, 16)), (D(2026, 10, 12), D(2026, 10, 18)))
		self.assertEqual(zakres_okresu("ten_tydzien", D(2026, 10, 12)), (D(2026, 10, 12), D(2026, 10, 18)))
		self.assertEqual(zakres_okresu("ten_tydzien", D(2026, 10, 18)), (D(2026, 10, 12), D(2026, 10, 18)))

	def test_poprzedni_tydzien_na_granicy_miesiaca(self):
		self.assertEqual(zakres_okresu("poprzedni_tydzien", D(2026, 10, 1)), (D(2026, 9, 21), D(2026, 9, 27)))

	def test_miesiac_i_koniec_roku(self):
		self.assertEqual(zakres_okresu("ten_miesiac", D(2026, 12, 15)), (D(2026, 12, 1), D(2026, 12, 31)))
		self.assertEqual(zakres_okresu("ten_miesiac", D(2026, 2, 10)), (D(2026, 2, 1), D(2026, 2, 28)))
		self.assertEqual(zakres_okresu("ten_miesiac", D(2028, 2, 29)), (D(2028, 2, 1), D(2028, 2, 29)))

	def test_poprzedni_miesiac_przez_granice_roku(self):
		self.assertEqual(zakres_okresu("poprzedni_miesiac", D(2026, 1, 5)), (D(2025, 12, 1), D(2025, 12, 31)))
		self.assertEqual(zakres_okresu("poprzedni_miesiac", D(2026, 3, 31)), (D(2026, 2, 1), D(2026, 2, 28)))

	def test_kwartal(self):
		self.assertEqual(zakres_okresu("ten_kwartal", D(2026, 10, 16)), (D(2026, 10, 1), D(2026, 12, 31)))
		self.assertEqual(zakres_okresu("ten_kwartal", D(2026, 3, 31)), (D(2026, 1, 1), D(2026, 3, 31)))
		self.assertEqual(zakres_okresu("ten_kwartal", D(2026, 6, 30)), (D(2026, 4, 1), D(2026, 6, 30)))

	def test_poprzedni_kwartal(self):
		self.assertEqual(zakres_okresu("poprzedni_kwartal", D(2026, 10, 16)), (D(2026, 7, 1), D(2026, 9, 30)))
		self.assertEqual(zakres_okresu("poprzedni_kwartal", D(2026, 2, 1)), (D(2025, 10, 1), D(2025, 12, 31)))

	def test_rok(self):
		self.assertEqual(zakres_okresu("ten_rok", D(2026, 10, 16)), (D(2026, 1, 1), D(2026, 12, 31)))

	def test_ostatnie_n_dni_wlacznie(self):
		od, do = zakres_okresu("ostatnie_30_dni", D(2026, 10, 16))
		self.assertEqual((od, do), (D(2026, 9, 17), D(2026, 10, 16)))
		self.assertEqual((do - od).days + 1, 30)
		od, do = zakres_okresu("ostatnie_90_dni", D(2026, 10, 16))
		self.assertEqual((do - od).days + 1, 90)

	def test_wlasny(self):
		self.assertEqual(
			zakres_okresu("wlasny", D(2026, 10, 16), D(2026, 1, 1), D(2026, 1, 1)),
			(D(2026, 1, 1), D(2026, 1, 1)),
		)

	def test_wlasny_odwrocony(self):
		with self.assertRaises(ValueError):
			zakres_okresu("wlasny", D(2026, 10, 16), D(2026, 2, 1), D(2026, 1, 1))

	def test_wlasny_bez_konca(self):
		with self.assertRaises(ValueError):
			zakres_okresu("wlasny", D(2026, 10, 16), D(2026, 1, 1), None)
		with self.assertRaises(ValueError):
			zakres_okresu("wlasny", D(2026, 10, 16))

	def test_nieznany_preset(self):
		with self.assertRaises(ValueError):
			zakres_okresu("jutro", D(2026, 10, 16))


class TestTekstSladu(unittest.TestCase):
	def test_przyklad_z_planu(self):
		tekst = tekst_sladu("wyplata", "Handlowiec", "Marek Nowak", "2400", "2026-10-06", "Leszek Furmann", 4)
		self.assertEqual(
			tekst,
			"[volteo:rozliczenie] Leszek Furmann oznaczył wypłatę dla Handlowca "
			"(Marek Nowak, 2 400,00 zł), data 2026-10-06, z rejestru prowizji razem z 4 innymi pozycjami",
		)

	def test_pojedyncza_akcja_bez_dopisku(self):
		tekst = tekst_sladu("wyplata", "Manager", "Anna Kowal", Decimal("10"), D(2026, 10, 6), "Jan")
		self.assertTrue(tekst.startswith(ZNACZNIK_ROZLICZENIE))
		self.assertNotIn("z rejestru", tekst)
		self.assertIn("dla Managera", tekst)

	def test_jedna_inna_pozycja(self):
		tekst = tekst_sladu("wyplata", "Partner", None, None, None, "Jan", 1)
		self.assertTrue(tekst.endswith("razem z 1 inną pozycją"))
		self.assertNotIn("(", tekst)
		self.assertNotIn("data", tekst)

	def test_dodanie_uzywa_nazwy_roli(self):
		tekst = tekst_sladu("dodanie", "Partner", "Piotr", "50", None, "Jan")
		self.assertIn("dodał odbiorcę rozliczenia: Partner (Piotr, 50,00 zł)", tekst)

	def test_wszystkie_akcje_dzialaja(self):
		for akcja in (
			"wyplata",
			"cofniecie",
			"wstrzymanie",
			"nie_dotyczy",
			"do_wyplaty",
			"zmiana_kwoty",
			"dodanie",
			"naliczenie",
		):
			self.assertTrue(
				tekst_sladu(akcja, "Handlowiec", "X", "1", None, "Jan").startswith(ZNACZNIK_ROZLICZENIE)
			)

	def test_nieznana_akcja(self):
		with self.assertRaises(ValueError):
			tekst_sladu("skasuj", "Handlowiec", "X", "1", None, "Jan")

	def test_bez_myslnikow_em_en(self):
		tekst = tekst_sladu("wyplata", "Handlowiec", "X", "1", "2026-10-06", "Jan", 3)
		self.assertNotIn("—", tekst)
		self.assertNotIn("–", tekst)


class TestFormatujKwote(unittest.TestCase):
	def test_formaty(self):
		self.assertEqual(formatuj_kwote("2400"), "2 400,00 zł")
		self.assertEqual(formatuj_kwote(0), "0,00 zł")
		self.assertEqual(formatuj_kwote(Decimal("1234567.891")), "1 234 567,89 zł")
		self.assertEqual(formatuj_kwote("-5"), "-5,00 zł")


if __name__ == "__main__":
	unittest.main()
