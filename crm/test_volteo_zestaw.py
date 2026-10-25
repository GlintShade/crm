# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm.volteo_zestaw` (ops#269): straznik rol, walidacja, roznice, lancuch ceny,
propozycja konfiguracji, tekst sladu. Bez frappe."""

import unittest
from decimal import Decimal as D
from typing import ClassVar

from crm import volteo_zestaw as z

STALE = {"pmt_oprocentowanie_mies": 1}


def wiersz(typ="Panele PV", nazwa="JA Solar 440", ilosc=12, jednostka="", netto=0, brutto=0, name=None):
	w = {"typ": typ, "nazwa": nazwa, "ilosc": ilosc, "jednostka": jednostka, "netto": netto, "brutto": brutto}
	if name:
		w["name"] = name
	return w


def wejscie(**kw):
	baza = {
		"netto": 41780,
		"vat_pct": 8,
		"dotacja": 9421.92,
		"ulga_pct": "12",
		"okres_lat": 10,
		"wplata_wlasna": 0,
		"typ_klienta": "indywidualny",
		"dodatki_bez_ulgi_brutto": 0,
	}
	baza.update(kw)
	return baza


class TestStraznikRol(unittest.TestCase):
	def test_system_manager(self):
		self.assertTrue(z.czy_moze_edytowac_zestaw(["System Manager"]))

	def test_core_admin(self):
		self.assertTrue(z.czy_moze_edytowac_zestaw(["Volteo Core Admin", "Sales User"]))

	def test_backoffice_nie(self):
		self.assertFalse(z.czy_moze_edytowac_zestaw(["Volteo Backend", "Sales User"]))

	def test_handlowiec_nie(self):
		self.assertFalse(z.czy_moze_edytowac_zestaw(["Volteo D2D Sales"]))

	def test_puste_i_none(self):
		self.assertFalse(z.czy_moze_edytowac_zestaw([]))
		self.assertFalse(z.czy_moze_edytowac_zestaw(None))

	def test_role_to_frozenset(self):
		self.assertEqual(z.ROLE_EDYCJI_ZESTAWU, frozenset({"System Manager", "Volteo Core Admin"}))


class TestKwota(unittest.TestCase):
	def test_przecinek(self):
		self.assertEqual(z.kwota("12,5"), D("12.5"))

	def test_puste(self):
		self.assertEqual(z.kwota(""), D(0))
		self.assertEqual(z.kwota("  "), D(0))
		self.assertEqual(z.kwota(None), D(0))

	def test_spacje_tysiecy(self):
		self.assertEqual(z.kwota("48 200,50"), D("48200.50"))

	def test_float_przez_str(self):
		self.assertEqual(z.kwota(0.1), D("0.1"))

	def test_int_i_decimal(self):
		self.assertEqual(z.kwota(7), D(7))
		self.assertEqual(z.kwota(D("1.5")), D("1.5"))

	def test_smiec(self):
		with self.assertRaises(ValueError):
			z.kwota("abc")


class TestZmienionePolaChronione(unittest.TestCase):
	def test_brak_zmian(self):
		stare = {"custom_netto": 100, "custom_ulga_pct": "12"}
		self.assertEqual(z.zmienione_pola_chronione(stare, dict(stare), [], []), frozenset())

	def test_none_kontra_zero(self):
		self.assertEqual(
			z.zmienione_pola_chronione({"custom_netto": None}, {"custom_netto": 0}, [], []), frozenset()
		)

	def test_pusty_string_kontra_zero_string(self):
		self.assertEqual(
			z.zmienione_pola_chronione({"custom_dotacja": ""}, {"custom_dotacja": "0"}, [], []), frozenset()
		)

	def test_string_kontra_liczba(self):
		self.assertEqual(
			z.zmienione_pola_chronione({"custom_ulga_pct": "12"}, {"custom_ulga_pct": 12.0}, [], []),
			frozenset(),
		)

	def test_zmiana_netto(self):
		self.assertEqual(
			z.zmienione_pola_chronione({"custom_netto": 100}, {"custom_netto": 101}, [], []),
			frozenset({"custom_netto"}),
		)

	def test_zmiana_wielu_pol(self):
		wynik = z.zmienione_pola_chronione(
			{"custom_netto": 1, "deal_value": 1}, {"custom_netto": 2, "deal_value": 3}, [], []
		)
		self.assertEqual(wynik, frozenset({"custom_netto", "deal_value"}))

	def test_pole_spoza_listy_ignorowane(self):
		self.assertEqual(
			z.zmienione_pola_chronione(
				{"custom_kolejny_kontakt": "a"}, {"custom_kolejny_kontakt": "b"}, [], []
			),
			frozenset(),
		)

	def test_pola_dotacji_obie(self):
		wynik = z.zmienione_pola_chronione(
			{"custom_estimated_subsidy_pln": 0}, {"custom_estimated_subsidy_pln": 5}, [], []
		)
		self.assertEqual(wynik, frozenset({"custom_estimated_subsidy_pln"}))

	def test_nowy_wiersz(self):
		wynik = z.zmienione_pola_chronione(
			{}, {}, [wiersz()], [wiersz(), wiersz(typ="Kabel", nazwa="K", ilosc=3)]
		)
		self.assertEqual(wynik, frozenset({"custom_zestaw"}))

	def test_zmiana_ilosci_wiersza(self):
		wynik = z.zmienione_pola_chronione({}, {}, [wiersz(ilosc=12)], [wiersz(ilosc=14)])
		self.assertEqual(wynik, frozenset({"custom_zestaw"}))

	def test_wiersze_bez_zmian_rozne_name(self):
		wynik = z.zmienione_pola_chronione({}, {}, [wiersz(name="a1")], [wiersz(name="b2")])
		self.assertEqual(wynik, frozenset())

	def test_ilosc_float_kontra_int(self):
		wynik = z.zmienione_pola_chronione({}, {}, [wiersz(ilosc=12.0)], [wiersz(ilosc=12)])
		self.assertEqual(wynik, frozenset())

	def test_zmiana_kolejnosci_wierszy(self):
		a, b = wiersz(typ="Falownik", nazwa="F", ilosc=1), wiersz(typ="Kabel", nazwa="K", ilosc=2)
		self.assertEqual(z.zmienione_pola_chronione({}, {}, [a, b], [b, a]), frozenset({"custom_zestaw"}))

	def test_netto_wiersza_none_kontra_zero(self):
		self.assertEqual(
			z.zmienione_pola_chronione({}, {}, [wiersz(netto=None)], [wiersz(netto=0)]), frozenset()
		)

	def test_none_wiersze(self):
		self.assertEqual(z.zmienione_pola_chronione(None, None, None, None), frozenset())

	def test_niepoprawna_liczba_porownanie_tekstowe(self):
		self.assertEqual(
			z.zmienione_pola_chronione({"custom_netto": "x"}, {"custom_netto": "y"}, [], []),
			frozenset({"custom_netto"}),
		)


class TestWalidujWiersze(unittest.TestCase):
	def test_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(), wiersz(typ="Falownik", nazwa="Deye", ilosc=1)]), [])

	def test_pusta_lista(self):
		self.assertEqual(z.waliduj_wiersze([]), [z.MSG_BRAK_WIERSZY])

	def test_none(self):
		self.assertEqual(z.waliduj_wiersze(None), [z.MSG_BRAK_WIERSZY])

	def test_brak_typu(self):
		b = z.waliduj_wiersze([wiersz(typ="  ")])
		self.assertEqual(b, ["Pozycja 1: typ jest wymagany."])

	def test_brak_nazwy(self):
		b = z.waliduj_wiersze([wiersz(nazwa="")])
		self.assertEqual(b, ["Pozycja 1: nazwa jest wymagana."])

	def test_ilosc_zero(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(ilosc=0)]), ["Pozycja 1: ilość musi być większa od zera."])

	def test_ilosc_ujemna(self):
		self.assertEqual(
			z.waliduj_wiersze([wiersz(ilosc=-1)]), ["Pozycja 1: ilość musi być większa od zera."]
		)

	def test_ilosc_nie_liczba(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(ilosc="abc")]), ["Pozycja 1: ilość nie jest liczbą."])

	def test_ilosc_przecinek(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(ilosc="2,5")]), [])

	def test_jednostka_opcjonalna(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(jednostka=None)]), [])

	def test_oze_z_cena_netto(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(netto=10)]), [z.MSG_OZE_BEZ_CEN])

	def test_oze_z_cena_brutto(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(brutto="5,5")]), [z.MSG_OZE_BEZ_CEN])

	def test_oze_komunikat_cen_raz(self):
		b = z.waliduj_wiersze([wiersz(netto=1), wiersz(netto=2)])
		self.assertEqual(b.count(z.MSG_OZE_BEZ_CEN), 1)

	def test_oze_ceny_zerowe_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(netto=0, brutto="")]), [])

	def test_cp_z_cenami_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(netto=10, brutto=12, jednostka="szt")], linia="cp"), [])

	def test_cp_cena_ujemna(self):
		self.assertEqual(
			z.waliduj_wiersze([wiersz(netto=-1, jednostka="szt")], linia="cp"),
			["Pozycja 1: netto nie może być ujemne."],
		)

	def test_dwa_falowniki(self):
		w = [wiersz(typ="Falownik", nazwa="A", ilosc=1), wiersz(typ="Falownik", nazwa="B", ilosc=1)]
		self.assertEqual(z.waliduj_wiersze(w), [z.MSG_DWA_FALOWNIKI])

	def test_myslnik_en_w_nazwie_z_katalogu_przechodzi(self):
		nazwa = "Elewacja " + chr(0x2013) + " styropian + tynk"
		self.assertEqual(z.waliduj_wiersze([wiersz(nazwa=nazwa)]), [])

	def test_zwykly_myslnik_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(nazwa="Dach skośny - blacha")]), [])

	def test_numer_pozycji_w_komunikacie(self):
		b = z.waliduj_wiersze([wiersz(), wiersz(nazwa="")])
		self.assertEqual(b, ["Pozycja 2: nazwa jest wymagana."])

	def test_typ_spoza_listy_dozwolony(self):
		self.assertEqual(z.waliduj_wiersze([wiersz(typ="Cokolwiek")]), [])

	def test_typy_wierszy_zawieraja_wszystkie_znane(self):
		for t in ("Falownik", "Ladowarka EV", "Panele PV + mikro (dodatek)", "Rozbudowa", "CWU", "Kocioł"):
			self.assertIn(t, z.TYPY_WIERSZY_OZE)

	def test_typy_wierszy_zawieraja_skladniki_ops299(self):
		for t in ("Montaż", "Akcesoria", "Sterownik", "Zasilanie awaryjne"):
			self.assertIn(t, z.TYPY_WIERSZY_OZE)

	def test_wiersze_informacyjne_ops299_przechodza_walidacje(self):
		w = [
			wiersz(typ="Falownik", nazwa="Sigenergy SigenStor 8 kW", ilosc=1),
			wiersz(typ="Sterownik", nazwa="Sterownik systemu Sigenergy TP2", ilosc=1),
			wiersz(typ="Montaż", nazwa="Montaż instalacji fotowoltaicznej", ilosc=1),
			wiersz(typ="Montaż", nazwa="Montaż magazynu energii", ilosc=1),
			wiersz(typ="Akcesoria", nazwa="Akcesoria i osprzęt montażowy", ilosc=1),
			wiersz(typ="Zasilanie awaryjne", nazwa="Zasilanie awaryjne (backup)", ilosc=1),
		]
		self.assertEqual(z.waliduj_wiersze(w), [])


class TestRoznice(unittest.TestCase):
	def test_brak_zmian(self):
		s = [wiersz(name="a")]
		self.assertTrue(z.roznice_zestawu(s, [wiersz(name="a")]).puste)

	def test_dodane_bez_name(self):
		r = z.roznice_zestawu([wiersz(name="a")], [wiersz(name="a"), wiersz(typ="Kabel", nazwa="K", ilosc=3)])
		self.assertEqual(len(r.dodane), 1)
		self.assertEqual(r.dodane[0]["typ"], "Kabel")
		self.assertEqual(r.usuniete, ())

	def test_usuniete(self):
		r = z.roznice_zestawu(
			[wiersz(name="a"), wiersz(typ="Kabel", nazwa="K", ilosc=3, name="b")], [wiersz(name="a")]
		)
		self.assertEqual([w["name"] for w in r.usuniete], ["b"])

	def test_zmieniona_ilosc(self):
		r = z.roznice_zestawu([wiersz(ilosc=12, name="a")], [wiersz(ilosc=14, name="a")])
		self.assertEqual(len(r.zmienione), 1)
		stary, nowy, pola = r.zmienione[0]
		self.assertEqual(pola, ("ilosc",))
		self.assertEqual(stary["ilosc"], 12)
		self.assertEqual(nowy["ilosc"], 14)

	def test_zmienione_wiele_pol(self):
		r = z.roznice_zestawu([wiersz(name="a")], [wiersz(nazwa="Inny", ilosc=1, jednostka="szt", name="a")])
		self.assertEqual(r.zmienione[0][2], ("nazwa", "ilosc", "jednostka"))

	def test_ilosc_float_int_nie_jest_zmiana(self):
		r = z.roznice_zestawu([wiersz(ilosc=12.0, name="a")], [wiersz(ilosc=12, name="a")])
		self.assertTrue(r.puste)

	def test_nieznany_name_to_nowy(self):
		r = z.roznice_zestawu([wiersz(name="a")], [wiersz(name="zzz")])
		self.assertEqual(len(r.dodane), 1)
		self.assertEqual(len(r.usuniete), 1)

	def test_kolejnosc_nie_jest_roznica_po_name(self):
		a, b = wiersz(name="a"), wiersz(typ="Kabel", nazwa="K", ilosc=1, name="b")
		self.assertTrue(z.roznice_zestawu([a, b], [b, a]).puste)

	def test_kombinacja(self):
		stare = [wiersz(name="a", ilosc=1), wiersz(typ="Kabel", nazwa="K", ilosc=3, name="b")]
		nowe = [wiersz(name="a", ilosc=2), wiersz(typ="Falownik", nazwa="F", ilosc=1)]
		r = z.roznice_zestawu(stare, nowe)
		self.assertEqual((len(r.dodane), len(r.usuniete), len(r.zmienione)), (1, 1, 1))

	def test_nie_mutuje_wejscia(self):
		stare = [wiersz(name="a")]
		kopia = [dict(w) for w in stare]
		z.roznice_zestawu(stare, [wiersz(ilosc=99, name="a")])
		self.assertEqual(stare, kopia)

	def test_dataclass_zamrozona(self):
		with self.assertRaises(AttributeError):
			z.Roznice().dodane = ()


class TestPrzeliczCene(unittest.TestCase):
	def test_ulga_i_dotacja(self):
		o = z.przelicz_cene(wejscie(), STALE)
		self.assertEqual(o["brutto"], D("45122.40"))
		self.assertEqual(o["cena_po_dotacji"], D("35700.48"))
		self.assertEqual(o["ulga_kwota"], D("4284.06"))
		self.assertEqual(o["cena_po_uldze"], D("31416.42"))

	def test_wyniki_to_decimal_2_miejsca(self):
		o = z.przelicz_cene(wejscie(), STALE)
		for k, v in o.items():
			self.assertIsInstance(v, D, k)
		self.assertEqual(o["brutto"].as_tuple().exponent, -2)
		self.assertEqual(o["rata_brutto"].as_tuple().exponent, -2)

	def test_firma_bez_dotacji_ulgi_i_rat(self):
		o = z.przelicz_cene(
			wejscie(typ_klienta="firma", dotacja=0, ulga_pct=0, vat_pct=23, netto=10000), STALE
		)
		self.assertEqual(o["brutto"], D("12300.00"))
		self.assertEqual(o["cena_po_dotacji"], D("12300.00"))
		self.assertEqual(o["cena_po_uldze"], D("12300.00"))
		self.assertEqual(o["dotacja"], D(0))
		self.assertEqual(o["ulga_kwota"], D(0))
		self.assertEqual((o["rata_brutto"], o["rata_po_dotacji"], o["rata_po_uldze"]), (D(0), D(0), D(0)))

	def test_firma_z_dotacja_odrzucona(self):
		with self.assertRaises(ValueError):
			z.przelicz_cene(wejscie(typ_klienta="firma", dotacja=100), STALE)

	def test_firma_z_ulga_odrzucona(self):
		self.assertIn(
			"Dla klienta firmowego ulga musi wynosić 0.",
			z.waliduj_cene(wejscie(typ_klienta="firma", dotacja=0)),
		)

	def test_okres_zero_raty_zero(self):
		o = z.przelicz_cene(wejscie(okres_lat=0), STALE)
		self.assertEqual((o["rata_brutto"], o["rata_po_dotacji"], o["rata_po_uldze"]), (D(0), D(0), D(0)))

	def test_stopa_zero_rata_liniowa(self):
		o = z.przelicz_cene(
			wejscie(netto=12000, vat_pct=0, dotacja=0, ulga_pct=0, okres_lat=1),
			{"pmt_oprocentowanie_mies": 0},
		)
		self.assertEqual(o["rata_brutto"], D("1000.00"))

	def test_brak_stalej_to_stopa_zero(self):
		o = z.przelicz_cene(wejscie(netto=12000, vat_pct=0, dotacja=0, ulga_pct=0, okres_lat=1), {})
		self.assertEqual(o["rata_brutto"], D("1000.00"))

	def test_principal_nieujemny_rata_zero(self):
		o = z.przelicz_cene(wejscie(wplata_wlasna=100000), STALE)
		self.assertEqual(o["rata_brutto"], D(0))
		self.assertEqual(o["rata_po_uldze"], D(0))

	def test_wplata_wlasna_obniza_rate(self):
		bez = z.przelicz_cene(wejscie(), STALE)["rata_brutto"]
		z_wplata = z.przelicz_cene(wejscie(wplata_wlasna=10000), STALE)["rata_brutto"]
		self.assertLess(z_wplata, bez)

	def test_przecinek_dziesietny(self):
		a = z.przelicz_cene(wejscie(netto="41780,50", vat_pct="8", dotacja="9421,92"), STALE)
		b = z.przelicz_cene(wejscie(netto=41780.5, vat_pct=8, dotacja=9421.92), STALE)
		self.assertEqual(a, b)

	def test_puste_stringi_jako_zero(self):
		o = z.przelicz_cene(
			wejscie(dotacja="", wplata_wlasna="", ulga_pct="", dodatki_bez_ulgi_brutto=""), STALE
		)
		self.assertEqual(o["dotacja"], D(0))
		self.assertEqual(o["ulga_kwota"], D(0))
		self.assertEqual(o["cena_po_uldze"], o["cena_po_dotacji"])

	def test_dodatki_bez_ulgi_obnizaja_podstawe(self):
		bez = z.przelicz_cene(wejscie(), STALE)["ulga_kwota"]
		z_dod = z.przelicz_cene(wejscie(dodatki_bez_ulgi_brutto=5000), STALE)["ulga_kwota"]
		self.assertEqual(bez - z_dod, D("600.00"))

	def test_nie_mutuje_wejscia(self):
		w = wejscie()
		kopia = dict(w)
		z.przelicz_cene(w, STALE)
		self.assertEqual(w, kopia)

	def test_zaokraglenie_half_up(self):
		o = z.przelicz_cene(wejscie(netto="100.05", vat_pct=5, dotacja=0, ulga_pct=0), STALE)
		# 100.05 * 5% = 5.0025 -> 5.00, brutto 105.05
		self.assertEqual(o["brutto"], D("105.05"))
		o2 = z.przelicz_cene(wejscie(netto="100.10", vat_pct=5, dotacja=0, ulga_pct=0), STALE)
		# 100.10 * 5% = 5.005 -> 5.01 (half up)
		self.assertEqual(o2["brutto"], D("105.11"))

	def test_ulga_pct_w_wyniku(self):
		self.assertEqual(z.przelicz_cene(wejscie(ulga_pct="19"), STALE)["ulga_pct"], D("19.00"))

	def test_walidacja_netto_zero(self):
		self.assertIn("Netto musi być większe od zera.", z.waliduj_cene(wejscie(netto=0)))

	def test_walidacja_vat_poza_zakresem(self):
		self.assertTrue(z.waliduj_cene(wejscie(vat_pct=101)))
		self.assertTrue(z.waliduj_cene(wejscie(vat_pct=-1)))

	def test_walidacja_dotacja_ponad_brutto(self):
		self.assertIn("Dotacja nie może być większa od brutto.", z.waliduj_cene(wejscie(dotacja=999999)))

	def test_walidacja_ulga_poza_zakresem(self):
		self.assertTrue(z.waliduj_cene(wejscie(ulga_pct=101)))
		self.assertTrue(z.waliduj_cene(wejscie(ulga_pct=-1)))

	def test_walidacja_okres(self):
		self.assertTrue(z.waliduj_cene(wejscie(okres_lat=-1)))
		self.assertTrue(z.waliduj_cene(wejscie(okres_lat="2,5")))
		self.assertEqual(z.waliduj_cene(wejscie(okres_lat="10")), [])

	def test_walidacja_wplata_i_dodatki_ujemne(self):
		self.assertTrue(z.waliduj_cene(wejscie(wplata_wlasna=-1)))
		self.assertTrue(z.waliduj_cene(wejscie(dodatki_bez_ulgi_brutto=-1)))

	def test_walidacja_dodatki_ponad_cene_po_dotacji(self):
		self.assertTrue(z.waliduj_cene(wejscie(dodatki_bez_ulgi_brutto=10**6)))

	def test_walidacja_smiec(self):
		self.assertIn("Netto nie jest liczbą.", z.waliduj_cene(wejscie(netto="abc")))

	def test_walidacja_ok(self):
		self.assertEqual(z.waliduj_cene(wejscie()), [])


class TestOdtworzDodatki(unittest.TestCase):
	def test_ulga_zero_to_zero(self):
		self.assertEqual(z.odtworz_dodatki_bez_ulgi(1000, 0, 0), D(0))

	def test_bez_dodatkow(self):
		# 35700.48 * 12% = 4284.0576 -> 4284.06 (szansa ME Deye)
		self.assertEqual(z.odtworz_dodatki_bez_ulgi("35700.48", "4284.06", "12"), D(0))

	def test_z_dodatkami(self):
		# (50179.08 - X) * 12% = 4842.13 (szansa ME Sigenergy z klima i EV, X = 9100 netto * 1,08)
		self.assertEqual(z.odtworz_dodatki_bez_ulgi("50179.08", "4842.13", "12"), D("9828.00"))

	def test_wynik_ujemny_to_zero(self):
		self.assertEqual(z.odtworz_dodatki_bez_ulgi(100, 50, 12), D(0))

	def test_ulga_pct_string(self):
		self.assertEqual(z.odtworz_dodatki_bez_ulgi(1000, 120, "12"), D(0))


class TestGoldenZLokalnychSzans(unittest.TestCase):
	"""Wartosci odczytane read-only z `crm.localhost` (2026-10-15) z szans utworzonych
	silnikiem kalkulatora; `pmt_oprocentowanie_mies` = 1. Lancuch ma odtworzyc zapisane
	pola co do grosza. Dodatki bez ulgi odzyskane przez `odtworz_dodatki_bez_ulgi`."""

	def sprawdz(self, w, oczekiwane):
		dod = z.odtworz_dodatki_bez_ulgi(
			oczekiwane["cena_po_dotacji"], oczekiwane["ulga_kwota"], w["ulga_pct"]
		)
		o = z.przelicz_cene({**w, "dodatki_bez_ulgi_brutto": dod}, STALE)
		for klucz, wartosc in oczekiwane.items():
			self.assertEqual(o[klucz], D(wartosc), klucz)

	def test_me_deye_pro_me_26_1180(self):
		self.sprawdz(
			{"netto": 41780.0, "vat_pct": 8.0, "dotacja": 9421.92, "ulga_pct": "12", "okres_lat": 10,
			"wplata_wlasna": 0.0, "typ_klienta": "indywidualny"},
			{"brutto": "45122.40", "cena_po_dotacji": "35700.48", "ulga_kwota": "4284.06",
			"cena_po_uldze": "31416.42", "rata_brutto": "647.38", "rata_po_dotacji": "512.20",
			"rata_po_uldze": "450.73"},
		)  # fmt: skip

	def test_pvme_deye_pro_pvme_26_1114_z_klimatyzacja(self):
		self.sprawdz(
			{"netto": 39230.0, "vat_pct": 8.0, "dotacja": 9600.0, "ulga_pct": "12", "okres_lat": 10,
			"wplata_wlasna": 0.0, "typ_klienta": "indywidualny"},
			{"brutto": "42368.40", "cena_po_dotacji": "32768.40", "ulga_kwota": "3297.17",
			"cena_po_uldze": "29471.23", "rata_brutto": "607.86", "rata_po_dotacji": "470.13",
			"rata_po_uldze": "422.83"},
		)  # fmt: skip

	def test_pvme_sigenergy_pro_pvme_26_1176(self):
		self.sprawdz(
			{"netto": 51151.0, "vat_pct": 8.0, "dotacja": 9600.0, "ulga_pct": "12", "okres_lat": 10,
			"wplata_wlasna": 0.0, "typ_klienta": "indywidualny"},
			{"brutto": "55243.08", "cena_po_dotacji": "45643.08", "ulga_kwota": "5477.17",
			"cena_po_uldze": "40165.91", "rata_brutto": "792.58", "rata_po_dotacji": "654.85",
			"rata_po_uldze": "576.26"},
		)  # fmt: skip

	def test_me_sigenergy_pro_me_26_1183_klima_i_ev(self):
		self.sprawdz(
			{"netto": 55351.0, "vat_pct": 8.0, "dotacja": 9600.0, "ulga_pct": "12", "okres_lat": 10,
			"wplata_wlasna": 0.0, "typ_klienta": "indywidualny"},
			{"brutto": "59779.08", "cena_po_dotacji": "50179.08", "ulga_kwota": "4842.13",
			"cena_po_uldze": "45336.95", "rata_brutto": "857.66", "rata_po_dotacji": "719.92",
			"rata_po_uldze": "650.45"},
		)  # fmt: skip

	def test_pv_bez_magazynu_dotacja_zero_pro_pv_26_1188(self):
		self.sprawdz(
			{"netto": 36520.0, "vat_pct": 8.0, "dotacja": 0.0, "ulga_pct": "12", "okres_lat": 10,
			"wplata_wlasna": 0.0, "typ_klienta": "indywidualny"},
			{"brutto": "39441.60", "cena_po_dotacji": "39441.60", "ulga_kwota": "4732.99",
			"cena_po_uldze": "34708.61", "rata_brutto": "565.87", "rata_po_dotacji": "565.87",
			"rata_po_uldze": "497.97"},
		)  # fmt: skip


KOMPONENTY = [
	{"nazwa": "Deye", "model": "12 kWh", "kategoria": "Magazyn energii", "pojemnosc_kwh": 12},
	{"nazwa": "Sigenergy", "model": "12 kWh (6+6)", "kategoria": "Magazyn energii", "pojemnosc_kwh": 12},
	{"nazwa": "Deye", "model": "5 kW", "kategoria": "Falownik", "pojemnosc_kwh": 0},
]


def zestaw_pvme():
	return [
		wiersz("Falownik", "Deye 5 kW", 1),
		wiersz("Panele PV", "AIKO 500W", 6),
		wiersz("Konstrukcja", "Dach skośny - blacha", 6),
		wiersz("Magazyn energii", "Deye 12 kWh", 1),
		wiersz("Kabel", "Dodatkowy kabel", 30, "m"),
		wiersz("Licznik", "Dodatkowy licznik", 1),
		wiersz("Klimatyzacja", "Elis X 2,6 kW (Czarny)", 1),
		wiersz("EMS Breeze", "EMS Breeze", 1),
	]


class TestZaproponujKonfiguracje(unittest.TestCase):
	def test_pelny_zestaw(self):
		k = z.zaproponuj_konfiguracje(zestaw_pvme(), KOMPONENTY, {})
		self.assertEqual(k["custom_falownik"], "Deye 5 kW")
		self.assertEqual(k["custom_bateria"], "Deye 12 kWh")
		self.assertEqual(k["custom_pojemnosc_kwh"], D(12))
		self.assertEqual(k["custom_panel"], "AIKO 500W")
		self.assertEqual(k["custom_panele"], 6)
		self.assertEqual(k["custom_konstrukcja"], "Dach skośny - blacha")
		self.assertEqual(k["custom_kabel_m"], 30)
		self.assertEqual(k["custom_licznik_dodatkowy"], "Tak")
		self.assertEqual(k["custom_dod_klima"], "Elis X 2,6 kW (Czarny)")
		self.assertEqual(k["custom_ems_breeze"], "Tak")
		self.assertEqual(k["custom_pstryk"], "Nie")
		self.assertEqual(k["custom_ev_ladowarka"], "")
		self.assertEqual(k["_ostrzezenia"], [])

	def test_ems_zeronest_i_historyczny_breeze_daja_tak(self):
		nowy = [wiersz("EMS Zeronest", "EMS Zeronest", 1)]
		stary = [wiersz("EMS Breeze", "EMS Breeze", 1)]
		self.assertEqual(z.zaproponuj_konfiguracje(nowy, KOMPONENTY, {})["custom_ems_breeze"], "Tak")
		self.assertEqual(z.zaproponuj_konfiguracje(stary, KOMPONENTY, {})["custom_ems_breeze"], "Tak")
		self.assertEqual(z.zaproponuj_konfiguracje([], KOMPONENTY, {})["custom_ems_breeze"], "Nie")
		self.assertIn("EMS Zeronest", z.TYPY_WIERSZY_OZE)
		self.assertIn("EMS Breeze", z.TYPY_WIERSZY_OZE)

	def test_falownik_nazwa_rowna_wierszowi(self):
		k = z.zaproponuj_konfiguracje(zestaw_pvme(), KOMPONENTY, {})
		self.assertEqual(k["custom_falownik"], zestaw_pvme()[0]["nazwa"])

	def test_pojemnosc_razy_ilosc(self):
		w = [wiersz("Magazyn energii", "Deye 12 kWh", 2)]
		k = z.zaproponuj_konfiguracje(w, KOMPONENTY, {})
		self.assertEqual(k["custom_pojemnosc_kwh"], D(24))

	def test_dwie_baterie_laczone(self):
		w = [
			wiersz("Magazyn energii", "Deye 12 kWh", 1),
			wiersz("Magazyn energii", "Sigenergy 12 kWh (6+6)", 1),
		]
		k = z.zaproponuj_konfiguracje(w, KOMPONENTY, {})
		self.assertEqual(k["custom_bateria"], "Deye 12 kWh + Sigenergy 12 kWh (6+6)")
		self.assertEqual(k["custom_pojemnosc_kwh"], D(24))

	def test_bateria_bez_dopasowania_ostrzega(self):
		w = [wiersz("Magazyn energii", "Nieznany 99 kWh", 1)]
		k = z.zaproponuj_konfiguracje(w, KOMPONENTY, {"custom_pojemnosc_kwh": 7.5})
		self.assertEqual(k["custom_pojemnosc_kwh"], D("7.5"))
		self.assertEqual(len(k["_ostrzezenia"]), 1)
		self.assertIn("Nieznany 99 kWh", k["_ostrzezenia"][0])

	def test_dopasowanie_tylko_w_kategorii_magazynu(self):
		w = [wiersz("Magazyn energii", "Deye 5 kW", 1)]
		k = z.zaproponuj_konfiguracje(w, KOMPONENTY, {"custom_pojemnosc_kwh": 3})
		self.assertEqual(len(k["_ostrzezenia"]), 1)
		self.assertEqual(k["custom_pojemnosc_kwh"], D(3))

	def test_brak_wierszy_baterii_pojemnosc_zero(self):
		k = z.zaproponuj_konfiguracje([wiersz("Falownik", "F", 1)], KOMPONENTY, {"custom_pojemnosc_kwh": 12})
		self.assertEqual(k["custom_bateria"], "")
		self.assertEqual(k["custom_pojemnosc_kwh"], D(0))

	def test_brak_falownika(self):
		k = z.zaproponuj_konfiguracje([wiersz()], KOMPONENTY, {})
		self.assertEqual(k["custom_falownik"], "")

	def test_brak_kabla_to_zero(self):
		k = z.zaproponuj_konfiguracje([wiersz()], KOMPONENTY, {})
		self.assertEqual(k["custom_kabel_m"], 0)

	def test_licznik_nie(self):
		k = z.zaproponuj_konfiguracje([wiersz()], KOMPONENTY, {})
		self.assertEqual(k["custom_licznik_dodatkowy"], "Nie")

	def test_dodatki_paneli_ilosc_z_nazwy(self):
		w = [
			wiersz("Panele PV (dodatek)", "Panele PV x 3 (dodatek)", 1),
			wiersz("Panele PV + mikro (dodatek)", "Panele PV + mikro x 2 (dodatek)", 1),
			wiersz("Ladowarka EV", "Ładowarka EV AC 7 kW", 1),
			wiersz("Licznik Pstryk", "Pstryk", 1),
		]
		k = z.zaproponuj_konfiguracje(w, KOMPONENTY, {})
		self.assertEqual(k["custom_dod_panele"], 3)
		self.assertEqual(k["custom_dod_panele_mikro"], 2)
		self.assertEqual(k["custom_ev_ladowarka"], "Ładowarka EV AC 7 kW")
		self.assertEqual(k["custom_pstryk"], "Tak")

	def test_dodatek_paneli_bez_liczby_w_nazwie_uzywa_ilosci(self):
		k = z.zaproponuj_konfiguracje([wiersz("Panele PV (dodatek)", "Panele dodatkowe", 4)], KOMPONENTY, {})
		self.assertEqual(k["custom_dod_panele"], 4)

	def test_nowe_rodzaje_pusty_slownik(self):
		for rodzaj in ("Rozbudowa PV/ME", "Klimatyzacja", "Pompa ciepła", "Kocioł"):
			self.assertEqual(z.zaproponuj_konfiguracje(zestaw_pvme(), KOMPONENTY, {}, rodzaj=rodzaj), {})

	def test_rodzaj_pv_nie_pusty(self):
		self.assertTrue(
			z.zaproponuj_konfiguracje(zestaw_pvme(), KOMPONENTY, {}, rodzaj="Fotowoltaika + Magazyn")
		)

	def test_nie_wylicza_mocy_producenta_spoldzielni(self):
		k = z.zaproponuj_konfiguracje(zestaw_pvme(), KOMPONENTY, {})
		for pole in ("custom_pv_power_kwp", "custom_producent", "custom_spoldzielnia"):
			self.assertNotIn(pole, k)

	def test_nie_mutuje_wejscia(self):
		w = zestaw_pvme()
		kopia = [dict(x) for x in w]
		z.zaproponuj_konfiguracje(w, KOMPONENTY, {})
		self.assertEqual(w, kopia)


class TestTekstSladu(unittest.TestCase):
	ETYKIETY: ClassVar[dict] = {"custom_falownik": "Falownik", "custom_kabel_m": "Dodatkowy kabel (m)"}

	def roznice(self):
		return z.roznice_zestawu(
			[
				wiersz("Panele PV", "JA Solar 440", 12, name="p"),
				wiersz("Kabel", "Dodatkowy kabel", 30, "m", name="k"),
			],
			[
				wiersz("Panele PV", "JA Solar 440", 14, name="p"),
				wiersz("Magazyn energii", "Deye BOS-G 5.12 kWh", 2),
			],
		)

	def cena(self, netto, brutto, dotacja, po_uldze):
		return {"netto": netto, "brutto": brutto, "dotacja": dotacja, "cena_po_uldze": po_uldze}

	def test_pelny_tekst(self):
		t = z.tekst_sladu_zestawu(
			self.roznice(),
			self.cena(45000, 48600, 16000, 29000),
			self.cena("48200", "52056", 16000, 31000),
			["custom_falownik", "custom_kabel_m"],
			"aneks nr 1 z 20.10.2026",
			"Podpisana (Autenti), PDF z 12.10.2026 bez zmian",
			self.ETYKIETY,
			"podsumowanie przeliczone, linie kosztów bez zmian",
		)
		self.assertTrue(t.startswith("[volteo:zestaw] Edycja zestawu (powód: aneks nr 1 z 20.10.2026)."))
		self.assertIn('Dodano: Magazyn energii "Deye BOS-G 5.12 kWh" x 2.', t)
		self.assertIn('Usunięto: Kabel "Dodatkowy kabel" x 30 m.', t)
		self.assertIn('Zmieniono: Panele PV "JA Solar 440": ilość 12 -> 14.', t)
		self.assertIn(
			"Cena: netto 45 000,00 -> 48 200,00, brutto 48 600,00 -> 52 056,00, "
			"dotacja 16 000,00 -> 16 000,00, po uldze 29 000,00 -> 31 000,00 zł.",
			t,
		)
		self.assertIn("Konfiguracja: Falownik, Dodatkowy kabel (m).", t)
		self.assertIn("Umowa: Podpisana (Autenti), PDF z 12.10.2026 bez zmian.", t)
		self.assertIn("Snapshot kosztów: podsumowanie przeliczone, linie kosztów bez zmian.", t)

	def test_brak_powodu(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], None, None, {})
		self.assertTrue(t.startswith("[volteo:zestaw] Edycja zestawu. "))
		self.assertNotIn("powód", t)

	def test_pusty_powod_to_brak(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], "   ", None, {})
		self.assertNotIn("powód", t)

	def test_pomija_puste_czlony(self):
		t = z.tekst_sladu_zestawu(z.Roznice(), None, None, [], None, None, {})
		self.assertEqual(t, "[volteo:zestaw] Edycja zestawu.")

	def test_tylko_dodano(self):
		r = z.Roznice(dodane=(wiersz("Kabel", "K", 5, "m"),))
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None, {})
		self.assertIn('Dodano: Kabel "K" x 5 m.', t)
		self.assertNotIn("Usunięto", t)
		self.assertNotIn("Zmieniono", t)

	def test_cena_bez_zmian_pominieta(self):
		c = self.cena(100, 108, 0, 108)
		t = z.tekst_sladu_zestawu(z.Roznice(), c, dict(c), [], None, None, {})
		self.assertNotIn("Cena:", t)

	def test_cena_zmieniona_tylko_netto(self):
		t = z.tekst_sladu_zestawu(
			z.Roznice(), self.cena(100, 108, 0, 108), self.cena(110, 108, 0, 108), [], None, None, {}
		)
		self.assertIn("Cena: netto 100,00 -> 110,00, brutto", t)

	def test_etykieta_brakujaca_to_fieldname(self):
		t = z.tekst_sladu_zestawu(z.Roznice(), None, None, ["custom_pstryk"], None, None, {})
		self.assertIn("Konfiguracja: custom_pstryk.", t)

	def test_status_umowy_z_kropka_bez_dubla(self):
		t = z.tekst_sladu_zestawu(z.Roznice(), None, None, [], None, "Podpisana.", {})
		self.assertTrue(t.endswith("Umowa: Podpisana."))

	def test_zmiana_nazwy_wiersza(self):
		r = z.roznice_zestawu(
			[wiersz("Falownik", "Deye SUN-5K", 1, name="f")], [wiersz("Falownik", "Deye SUN-6K", 1, name="f")]
		)
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None, {})
		self.assertIn('Zmieniono: Falownik: nazwa "Deye SUN-5K" -> "Deye SUN-6K".', t)

	def test_wiele_pol_jednego_wiersza(self):
		r = z.roznice_zestawu(
			[wiersz("Panele PV", "A", 1, name="x")], [wiersz("Panele PV", "A", 2, "szt", name="x")]
		)
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None, {})
		self.assertIn('Panele PV "A": ilość 1 -> 2, jednostka "" -> "szt".', t)

	def test_cena_wiersza_cp_w_zmianie(self):
		r = z.roznice_zestawu(
			[wiersz("Okna", "O", 1, netto=100, name="x")], [wiersz("Okna", "O", 1, netto="150,5", name="x")]
		)
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None, {})
		self.assertIn("netto 100,00 -> 150,50", t)

	def test_ilosc_ulamkowa_z_przecinkiem(self):
		r = z.Roznice(dodane=(wiersz("Kabel", "K", "2.50", "m"),))
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None, {})
		self.assertIn("x 2,5 m", t)

	def test_zero_myslnikow_dlugich(self):
		t = z.tekst_sladu_zestawu(
			self.roznice(),
			self.cena(1, 2, 3, 4),
			self.cena(5, 6, 7, 8),
			["custom_falownik"],
			"p",
			"s",
			self.ETYKIETY,
			"x",
		)
		for d in (chr(0x2014), chr(0x2013), chr(0x2192)):
			self.assertNotIn(d, t)


def wiersz_cp(
	typ="Źródło ciepła", nazwa="Pompa ciepła", ilosc=1, jednostka="szt", netto=0, brutto=0, name=None
):
	return wiersz(typ, nazwa, ilosc, jednostka, netto, brutto, name)


STALE_CP = {"oprocentowanie_mies": "1", "trify_udzial": "0.65", "trify_stawka_za_1000": "25"}

# Golden: wynik oblicz_oferte (fixture test_obliczenia: pompa ciepla + 10 grzejnikow +
# elewacja 50 m2, poziom najwyzszy, powyzej140, finansowanie 5 lat, wplata 1000).
# Lokalna baza nie ma zadnej szansy CP, wiec liczby pochodza z rdzenia, nie z szansy.
WIERSZE_GOLDEN_CP = [
	wiersz_cp("Źródło ciepła", "pompa_ciepla", 1, "szt", "35200.00", "38016.00"),
	wiersz_cp("Centralne Ogrzewanie i Ciepła Woda Użytkowa", "grzejnik", 10, "szt", "18000.00", "19440.00"),
	wiersz_cp("Termomodernizacja", "elewacja", 50, "m2", "15000.00", "16200.00"),
]
DOTACJE_GOLDEN_CP = {"zrodlo": "35200.00", "co": "18000.00", "termo": "12375.00"}


class TestWalidacjaWierszyCP(unittest.TestCase):
	def test_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz_cp(netto=10, brutto=10.8)], "cp"), [])

	def test_netto_wieksze_od_brutto(self):
		self.assertEqual(
			z.waliduj_wiersze([wiersz_cp(netto=12, brutto=10)], "cp"),
			["Pozycja 1: netto nie może być większe od brutto."],
		)

	def test_netto_rowne_brutto_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz_cp(netto=10, brutto=10)], "cp"), [])

	def test_zera_ok(self):
		self.assertEqual(z.waliduj_wiersze([wiersz_cp()], "cp"), [])

	def test_brak_jednostki(self):
		self.assertEqual(
			z.waliduj_wiersze([wiersz_cp(jednostka="  ")], "cp"), ["Pozycja 1: jednostka jest wymagana."]
		)

	def test_brutto_ujemne(self):
		b = z.waliduj_wiersze([wiersz_cp(netto=-5, brutto=-1)], "cp")
		self.assertIn("Pozycja 1: netto nie może być ujemne.", b)
		self.assertIn("Pozycja 1: brutto nie może być ujemne.", b)

	def test_cp_nie_zglasza_oze_bez_cen(self):
		self.assertNotIn(z.MSG_OZE_BEZ_CEN, z.waliduj_wiersze([wiersz_cp(netto=1, brutto=2)], "cp"))

	def test_cp_dwa_falowniki_dozwolone(self):
		w = [wiersz_cp("Falownik", "A"), wiersz_cp("Falownik", "B")]
		self.assertEqual(z.waliduj_wiersze(w, "cp"), [])

	def test_typy_cp(self):
		self.assertEqual(len(z.TYPY_WIERSZY_CP), 3)
		self.assertIn("Termomodernizacja", z.TYPY_WIERSZY_CP)

	def test_oze_nadal_nie_wymaga_jednostki(self):
		self.assertEqual(z.waliduj_wiersze([wiersz()], "oze"), [])


class TestCenaCP(unittest.TestCase):
	def policz(self, wiersze=None, dotacje=None, fin=None, stale=STALE_CP):
		return z.przelicz_cene_cp(
			WIERSZE_GOLDEN_CP if wiersze is None else wiersze,
			DOTACJE_GOLDEN_CP if dotacje is None else dotacje,
			{"okres_lat": 0, "wplata_gotowka": 0} if fin is None else fin,
			stale,
		)

	def test_deal_value_to_suma_brutto(self):
		self.assertEqual(self.policz()["deal_value"], D("73656.00"))

	def test_netto_suma(self):
		self.assertEqual(self.policz()["netto_suma"], D("68200.00"))

	def test_dotacja_laczna(self):
		self.assertEqual(self.policz()["dotacja_laczna"], D("65575.00"))

	def test_wklad_wlasny(self):
		self.assertEqual(self.policz()["wklad_wlasny"], D("8081.00"))

	def test_wklad_nie_ponizej_zera(self):
		w = [wiersz_cp(netto=100, brutto=108)]
		r = self.policz(w, {"zrodlo": 108}, None)
		self.assertEqual(r["wklad_wlasny"], D("0.00"))

	def test_brakujaca_dotacja_to_zero(self):
		r = self.policz(dotacje={"zrodlo": "1000"})
		self.assertEqual(r["dotacje"], {"zrodlo": D("1000.00"), "co": D("0.00"), "termo": D("0.00")})
		self.assertEqual(r["dotacja_laczna"], D("1000.00"))

	def test_dotacja_przecinek(self):
		self.assertEqual(self.policz(dotacje={"zrodlo": "1000,5"})["dotacja_laczna"], D("1000.50"))

	def test_dotacja_ujemna(self):
		with self.assertRaises(ValueError):
			self.policz(dotacje={"zrodlo": -1})

	def test_dotacja_wieksza_od_brutto(self):
		with self.assertRaises(ValueError) as e:
			self.policz(dotacje={"zrodlo": "80000"})
		self.assertIn("większa od sumy brutto", str(e.exception))

	def test_bez_kredytu_pola_kredytu_none(self):
		r = self.policz()
		self.assertIsNone(r["kwota_kredytu"])
		self.assertIsNone(r["rata_wkladu"])

	def test_trify_zawsze_nawet_bez_kredytu(self):
		r = self.policz()
		self.assertEqual(r["podstawa_trify"], D("42623.75"))
		self.assertEqual(r["rata_trify"], D("1065.59"))

	def test_kredyt_5_lat(self):
		r = self.policz(fin={"okres_lat": 5, "wplata_gotowka": 1000})
		self.assertEqual(r["kwota_kredytu"], D("7081.00"))
		self.assertEqual(r["rata_wkladu"], D("157.51"))
		self.assertEqual(r["okres_lat"], 5)
		self.assertEqual(r["wplata_gotowka"], D("1000.00"))

	def test_wplata_wieksza_od_wkladu_daje_zero_kredytu(self):
		r = self.policz(fin={"okres_lat": 5, "wplata_gotowka": 20000})
		self.assertEqual(r["kwota_kredytu"], D("0.00"))
		self.assertEqual(r["rata_wkladu"], D("0.00"))

	def test_okres_nie_wplywa_na_trify(self):
		a = self.policz(fin={"okres_lat": 1, "wplata_gotowka": 0})
		b = self.policz(fin={"okres_lat": 10, "wplata_gotowka": 0})
		self.assertEqual(a["rata_trify"], b["rata_trify"])

	def test_okres_poza_zakresem(self):
		for okres in (-1, 11, "2,5"):
			with self.assertRaises(ValueError):
				self.policz(fin={"okres_lat": okres, "wplata_gotowka": 0})

	def test_wplata_ujemna(self):
		with self.assertRaises(ValueError):
			self.policz(fin={"okres_lat": 5, "wplata_gotowka": -1})

	def test_stale_none_trify_none(self):
		r = self.policz(
			stale={"oprocentowanie_mies": None, "trify_udzial": None, "trify_stawka_za_1000": None}
		)
		self.assertIsNone(r["podstawa_trify"])
		self.assertIsNone(r["rata_trify"])

	def test_stale_puste_trify_none(self):
		self.assertIsNone(self.policz(stale=None)["rata_trify"])

	def test_stale_none_z_kredytem_blad(self):
		with self.assertRaises(ValueError) as e:
			self.policz(fin={"okres_lat": 5, "wplata_gotowka": 0}, stale={"trify_udzial": None})
		self.assertEqual(str(e.exception), z.MSG_CP_BRAK_STALYCH_KREDYTU)

	def test_brak_oprocentowania_z_kredytem_blad(self):
		stale = {**STALE_CP, "oprocentowanie_mies": None}
		with self.assertRaises(ValueError):
			self.policz(fin={"okres_lat": 5, "wplata_gotowka": 0}, stale=stale)

	def test_wejscia_nie_sa_mutowane(self):
		wiersze = [dict(w) for w in WIERSZE_GOLDEN_CP]
		dotacje = dict(DOTACJE_GOLDEN_CP)
		self.policz(wiersze, dotacje)
		self.assertEqual(wiersze, WIERSZE_GOLDEN_CP)
		self.assertEqual(dotacje, DOTACJE_GOLDEN_CP)

	def test_golden_komplet(self):
		"""Golden co do grosza (patrz komentarz przy WIERSZE_GOLDEN_CP)."""
		r = self.policz(fin={"okres_lat": 5, "wplata_gotowka": 1000})
		self.assertEqual(
			(
				r["deal_value"],
				r["dotacja_laczna"],
				r["wklad_wlasny"],
				r["kwota_kredytu"],
				r["rata_wkladu"],
				r["podstawa_trify"],
				r["rata_trify"],
			),
			(
				D("73656.00"),
				D("65575.00"),
				D("8081.00"),
				D("7081.00"),
				D("157.51"),
				D("42623.75"),
				D("1065.59"),
			),
		)

	def test_zaokraglenie_brutto_wierszy_half_up(self):
		w = [wiersz_cp(netto="0.004", brutto="0.005")]
		self.assertEqual(self.policz(w, {}, None)["deal_value"], D("0.01"))

	def test_roznice_cp_wykrywaja_zmiane_ceny(self):
		stare = [wiersz_cp(netto=10, brutto=12, name="a")]
		nowe = [wiersz_cp(netto=10, brutto=13, name="a")]
		r = z.roznice_zestawu(stare, nowe)
		self.assertEqual(r.zmienione[0][2], ("brutto",))


class TestSladCP(unittest.TestCase):
	CP: ClassVar[dict] = {
		"przed": {"deal_value": "73656", "dotacja_laczna": "65575", "wklad_wlasny": "8081"},
		"po": {"deal_value": "74656", "dotacja_laczna": "65575", "wklad_wlasny": "9081"},
	}

	def roznice(self):
		return z.roznice_zestawu([], [wiersz_cp("Termomodernizacja", "okna", 4, "m2", 1000, 1080)])

	def test_czlony_cp(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], "korekta", None, cp=self.CP)
		self.assertIn(
			"Cena CP: wartość szansy 73 656,00 -> 74 656,00, dotacja łączna 65 575,00 -> 65 575,00, "
			"wkład własny 8 081,00 -> 9 081,00 zł.",
			t,
		)
		self.assertIn("Prowizje CP bez zmian.", t)
		self.assertIn("Wejście kalkulatora (custom_cp_wejscie_json) nie odpowiada już zestawowi.", t)

	def test_kwoty_wierszy_cp(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], None, None, cp=self.CP)
		self.assertIn('Dodano: Termomodernizacja "okna" x 4 m2 (netto 1 000,00, brutto 1 080,00).', t)

	def test_bez_cp_brak_czlonow(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], None, None)
		self.assertNotIn("Prowizje CP", t)
		self.assertNotIn("(netto", t)

	def test_nazwa_z_katalogu_z_pauza_w_slad(self):
		nazwa = "Dach " + chr(0x2013) + " piana PUR"
		r = z.Roznice(dodane=(wiersz("Termomodernizacja", nazwa, "4", "m2"),))
		t = z.tekst_sladu_zestawu(r, None, None, [], None, None)
		self.assertIn(nazwa, t)

	def test_znacznik_i_brak_myslnikow(self):
		t = z.tekst_sladu_zestawu(self.roznice(), None, None, [], "x", None, cp=self.CP)
		self.assertTrue(t.startswith(z.ZNACZNIK_ZESTAW))
		self.assertFalse(any(d in t for d in (chr(0x2014), chr(0x2013))))


class TestGoldenSzansCPZLokalnejBazy(unittest.TestCase):
	"""Golden z lokalnych szans CP (odczyt 2026-10-15, stale 1 / 0.65 / 25). Szansa
	PRO/CP/26/1032 wskazana przez koordynatora nie istnieje w lokalnej bazie (brak szansy
	z rata Trify 1357.57), wiec dla kredytu uzyto PRO/CP/26/1026 (5 lat)."""

	def policz(self, wiersze, dotacje, fin):
		return z.przelicz_cene_cp(wiersze, dotacje, fin, STALE_CP)

	def test_szansa_1031_bez_kredytu(self):
		# PRO/CP/26/1031, utworzona 2026-09-04, okres_lat 0
		wiersze = [
			wiersz_cp("Źródło ciepła", "Piec zgazowujący drewno", 1, "szt", "35000", "37800"),
			wiersz_cp(
				"Centralne Ogrzewanie i Ciepła Woda Użytkowa",
				"Pompa ciepła do CWU",
				1,
				"szt",
				"20500",
				"22140",
			),
			wiersz_cp("Termomodernizacja", "Elewacja", 130, "m2", "39000", "42120"),
			wiersz_cp("Termomodernizacja", "Okna", 13, "m2", "19500", "21060"),
		]
		r = self.policz(wiersze, {"zrodlo": "20500", "co": "20500", "termo": "49335"}, {"okres_lat": 0})
		self.assertEqual(r["deal_value"], D("123120.00"))
		self.assertEqual(r["netto_suma"], D("114000.00"))
		self.assertEqual(r["dotacja_laczna"], D("90335.00"))
		self.assertEqual(r["wklad_wlasny"], D("32785.00"))
		self.assertIsNone(r["kwota_kredytu"])
		self.assertIsNone(r["rata_wkladu"])
		self.assertEqual(r["podstawa_trify"], D("58717.75"))
		self.assertEqual(r["rata_trify"], D("1467.94"))

	def test_szansa_1026_z_kredytem_5_lat(self):
		# PRO/CP/26/1026, utworzona 2026-09-04, okres_lat 5, wplata 8000
		wiersze = [
			wiersz_cp("Źródło ciepła", "Piec zgazowujący drewno", 1, "szt", "35000", "37800"),
			wiersz_cp(
				"Centralne Ogrzewanie i Ciepła Woda Użytkowa",
				"Pompa ciepła do CWU",
				1,
				"szt",
				"20500",
				"22140",
			),
			wiersz_cp("Termomodernizacja", "Elewacja", 117, "m2", "35100", "37908"),
			wiersz_cp("Termomodernizacja", "Strop", 81, "m2", "17820", "19245.6"),
		]
		r = self.policz(
			wiersze,
			{"zrodlo": "20500", "co": "20500", "termo": "46777.5"},
			{"okres_lat": 5, "wplata_gotowka": "8000"},
		)
		self.assertEqual(r["deal_value"], D("117093.60"))
		self.assertEqual(r["netto_suma"], D("108420.00"))
		self.assertEqual(r["dotacja_laczna"], D("87777.50"))
		self.assertEqual(r["wklad_wlasny"], D("29316.10"))
		self.assertEqual(r["kwota_kredytu"], D("21316.10"))
		self.assertEqual(r["rata_wkladu"], D("474.16"))
		self.assertEqual(r["podstawa_trify"], D("57055.38"))
		self.assertEqual(r["rata_trify"], D("1426.38"))


class TestMapaZestawProducent(unittest.TestCase):
	def test_mapa_po_ops_298(self):
		self.assertEqual(
			z.ZESTAW_PRODUCENT,
			{"COMFORT": "Hoymiles", "COMFORT PREMIUM": "Solax", "PREMIUM +": "Sigenergy"},
		)

	def test_zestawy_oze_kolejnosc_z_mapy(self):
		self.assertEqual(z.ZESTAWY_OZE, ("COMFORT", "COMFORT PREMIUM", "PREMIUM +"))

	def test_zaden_zestaw_nie_ma_starej_nazwy(self):
		self.assertNotIn("COMFORT +", z.ZESTAW_PRODUCENT)


class TestZestawDlaProducenta(unittest.TestCase):
	def test_trzy_zestawy_z_magazynem(self):
		for rodzaj in ("Fotowoltaika + Magazyn", "Magazyn energii"):
			self.assertEqual(z.zestaw_dla_producenta("Hoymiles", rodzaj), "COMFORT")
			self.assertEqual(z.zestaw_dla_producenta("Solax", rodzaj), "COMFORT PREMIUM")
			self.assertEqual(z.zestaw_dla_producenta("Sigenergy", rodzaj), "PREMIUM +")

	def test_foxess_deye_i_brak_to_pusty(self):
		for producent in ("FoxESS", "Deye", "", None, "Inny"):
			self.assertEqual(z.zestaw_dla_producenta(producent, "Fotowoltaika + Magazyn"), "")

	def test_sama_pv_i_nowe_rodzaje_to_pusty(self):
		for rodzaj in ("Fotowoltaika", "Rozbudowa PV/ME", "Klimatyzacja", "", None):
			self.assertEqual(z.zestaw_dla_producenta("Sigenergy", rodzaj), "")

	def test_spacje_sa_obciete(self):
		self.assertEqual(z.zestaw_dla_producenta(" Hoymiles ", "Magazyn energii"), "COMFORT")


class TestProducenciDlaRodzaju(unittest.TestCase):
	def test_pv_tylko_foxess(self):
		self.assertEqual(z.producenci_dla_rodzaju("Fotowoltaika"), ("FoxESS",))

	def test_magazyn_cztery_bez_deye(self):
		for rodzaj in ("Fotowoltaika + Magazyn", "Magazyn energii"):
			self.assertEqual(z.producenci_dla_rodzaju(rodzaj), ("FoxESS", "Sigenergy", "Hoymiles", "Solax"))
		self.assertNotIn("Deye", z.PRODUCENCI_WYBIERALNI)


KATALOG = [
	{"nazwa": "Hoymiles", "model": "HIT-15L-G3S 15 kW", "kategoria": "Falownik", "producent": "Hoymiles"},
	{
		"nazwa": "Hoymiles",
		"model": "45 kWh (15+15+15)",
		"kategoria": "Magazyn energii",
		"producent": "Hoymiles",
	},
	{"nazwa": "Sigenergy", "model": "TP2 8 kW", "kategoria": "Falownik", "producent": "Sigenergy"},
	{"nazwa": "Sigenergy", "model": "12 kWh (6+6)", "kategoria": "Magazyn energii", "producent": "Sigenergy"},
	{"nazwa": "Solax", "model": "X3-NEO 10 kW", "kategoria": "Falownik", "producent": "Solax"},
	{"nazwa": "Deye", "model": "5 kW", "kategoria": "Falownik", "producent": "Deye"},
	{"nazwa": "Bez", "model": "Producenta", "kategoria": "Falownik", "producent": ""},
]


def wiersze_hoymiles():
	return [
		wiersz("Falownik", "Hoymiles HIT-15L-G3S 15 kW", 1),
		wiersz("Magazyn energii", "Hoymiles 45 kWh (15+15+15)", 1),
		wiersz("Panele PV", "AIKO 500W", 12),
	]


MAG = "Fotowoltaika + Magazyn"


class TestWalidujProducenta(unittest.TestCase):
	def waliduj(self, producent, nowe, stare=None, rodzaj=MAG, obecny="Sigenergy"):
		stare = wiersze_hoymiles() if stare is None else stare
		return z.waliduj_producenta(producent, rodzaj, nowe, stare, KATALOG, obecny)

	def test_zmiana_sigenergy_na_hoymiles_przy_falowniku_hoymiles_przechodzi(self):
		w = self.waliduj("Hoymiles", wiersze_hoymiles())
		self.assertEqual(w.bledy, ())

	def test_producent_niezgodny_z_falownikiem_blokuje(self):
		w = self.waliduj("Solax", wiersze_hoymiles())
		self.assertEqual(len(w.bledy), 2)
		self.assertIn('Falownik "Hoymiles HIT-15L-G3S 15 kW"', w.bledy[0])
		self.assertIn("producenta Hoymiles", w.bledy[0])
		self.assertIn("wybrany producent to Solax", w.bledy[0])
		self.assertIn("Magazyn energii", w.bledy[1])

	def test_niezgodny_magazyn_blokuje_zmiane_wierszy(self):
		nowe = [
			wiersz("Falownik", "Sigenergy TP2 8 kW", 1),
			wiersz("Magazyn energii", "Hoymiles 45 kWh (15+15+15)", 1),
		]
		stare = [
			wiersz("Falownik", "Sigenergy TP2 8 kW", 1),
			wiersz("Magazyn energii", "Sigenergy 12 kWh (6+6)", 1),
		]
		w = self.waliduj("Sigenergy", nowe, stare)
		self.assertEqual(len(w.bledy), 1)
		self.assertIn("Magazyn energii", w.bledy[0])

	def test_stara_niespojna_szansa_przy_samej_cenie_to_ostrzezenie(self):
		# Producent Sigenergy, falownik i magazyn Hoymiles, wiersze bez zmian.
		w = self.waliduj("Sigenergy", wiersze_hoymiles())
		self.assertEqual(w.bledy, ())
		self.assertEqual(len(w.ostrzezenia), 2)
		self.assertIn("jest producenta Hoymiles", w.ostrzezenia[0])

	def test_zmiana_ilosci_nie_uruchamia_blokady(self):
		nowe = wiersze_hoymiles()
		nowe[0] = wiersz("Falownik", "Hoymiles HIT-15L-G3S 15 kW", 2)
		w = self.waliduj("Sigenergy", nowe)
		self.assertEqual(w.bledy, ())

	def test_zmiana_kolejnosci_wierszy_nie_uruchamia_blokady(self):
		nowe = list(reversed(wiersze_hoymiles()))
		w = self.waliduj("Sigenergy", nowe)
		self.assertEqual(w.bledy, ())

	def test_zmiana_innego_wiersza_nie_uruchamia_blokady(self):
		nowe = wiersze_hoymiles()
		nowe[2] = wiersz("Panele PV", "AIKO 550W", 12)
		w = self.waliduj("Sigenergy", nowe)
		self.assertEqual(w.bledy, ())

	def test_niedopasowany_do_katalogu_to_zawsze_ostrzezenie(self):
		nowe = [wiersz("Falownik", "Nieznany falownik 9 kW", 1)]
		w = self.waliduj("Hoymiles", nowe, stare=[])
		self.assertEqual(w.bledy, ())
		self.assertEqual(len(w.ostrzezenia), 1)
		self.assertIn("nie została znaleziona w katalogu", w.ostrzezenia[0])

	def test_komponent_bez_producenta_to_ostrzezenie(self):
		nowe = [wiersz("Falownik", "Bez Producenta", 1)]
		w = self.waliduj("Hoymiles", nowe, stare=[])
		self.assertEqual(w.bledy, ())
		self.assertEqual(len(w.ostrzezenia), 1)

	def test_dopasowanie_po_kategorii(self):
		# "Hoymiles 45 kWh (15+15+15)" to magazyn, nie falownik.
		nowe = [wiersz("Falownik", "Hoymiles 45 kWh (15+15+15)", 1)]
		w = self.waliduj("Hoymiles", nowe, stare=[])
		self.assertIn("nie została znaleziona", w.ostrzezenia[0])

	def test_deye_historyczny_bez_zmian_przechodzi(self):
		wiersze = [wiersz("Falownik", "Deye 5 kW", 1)]
		w = z.waliduj_producenta("Deye", MAG, wiersze, wiersze, KATALOG, "Deye")
		self.assertEqual((w.bledy, w.ostrzezenia), ((), ()))

	def test_nowy_wybor_deye_jest_zablokowany(self):
		w = self.waliduj("Deye", [], stare=[])
		self.assertEqual(w.bledy, ('Producent "Deye" nie jest dostępny do wyboru.',))

	def test_pv_dopuszcza_tylko_foxess_przy_zmianie(self):
		w = self.waliduj("Hoymiles", [], stare=[], rodzaj="Fotowoltaika", obecny="FoxESS")
		self.assertEqual(w.bledy, ("Dla rodzaju Fotowoltaika dostępny jest tylko producent FoxESS.",))
		ok = self.waliduj("FoxESS", [], stare=[], rodzaj="Fotowoltaika", obecny="FoxESS")
		self.assertEqual(ok.bledy, ())

	def test_pv_z_historycznym_producentem_bez_zmiany_nie_blokuje(self):
		w = self.waliduj("Sigenergy", [], stare=[], rodzaj="Fotowoltaika", obecny="Sigenergy")
		self.assertEqual(w.bledy, ())

	def test_zmiana_na_pusty_producent_blokuje(self):
		w = self.waliduj("", [], stare=[], obecny="Sigenergy")
		self.assertEqual(w.bledy, (z.MSG_PRODUCENT_PUSTY,))

	def test_pusty_producent_bez_zmiany_nic_nie_sprawdza(self):
		w = self.waliduj("", wiersze_hoymiles(), obecny="")
		self.assertEqual((w.bledy, w.ostrzezenia), ((), ()))

	def test_pstryk_i_ladowarka_poza_sigenergy_ostrzezenia(self):
		nowe = [
			*wiersze_hoymiles(),
			wiersz("Licznik Pstryk", "Pstryk", 1),
			wiersz("Ladowarka EV", "AC 7 kW", 1),
		]
		w = self.waliduj("Hoymiles", nowe)
		self.assertEqual(w.bledy, ())
		self.assertIn("Licznik Pstryk jest dostępny tylko z producentem Sigenergy.", w.ostrzezenia)
		self.assertIn("Ładowarka EV jest dostępna tylko z producentem Sigenergy.", w.ostrzezenia)

	def test_pstryk_przy_sigenergy_bez_ostrzezenia(self):
		nowe = [wiersz("Falownik", "Sigenergy TP2 8 kW", 1), wiersz("Licznik Pstryk", "Pstryk", 1)]
		w = z.waliduj_producenta("Sigenergy", MAG, nowe, nowe, KATALOG, "Sigenergy")
		self.assertEqual(w.ostrzezenia, ())

	def test_ems_przy_sigenergy_i_foxess_ostrzezenie(self):
		for producent in ("Sigenergy", "FoxESS"):
			nowe = [wiersz("EMS Zeronest", "EMS Zeronest", 1)]
			w = z.waliduj_producenta(producent, MAG, nowe, nowe, KATALOG, producent)
			self.assertEqual(w.ostrzezenia, (f"EMS Zeronest nie jest dostępny z producentem {producent}.",))

	def test_ems_breeze_historyczny_liczy_sie_jak_zeronest(self):
		nowe = [wiersz("EMS Breeze", "EMS Breeze", 1)]
		w = z.waliduj_producenta("Sigenergy", MAG, nowe, nowe, KATALOG, "Sigenergy")
		self.assertEqual(len(w.ostrzezenia), 1)

	def test_solax_z_magazynem_bez_ems_ostrzezenie(self):
		nowe = [wiersz("Falownik", "Solax X3-NEO 10 kW", 1)]
		w = z.waliduj_producenta("Solax", MAG, nowe, nowe, KATALOG, "Solax")
		self.assertEqual(w.ostrzezenia, ("Producent Solax z magazynem wymaga pozycji EMS Zeronest.",))

	def test_solax_z_ems_bez_ostrzezenia(self):
		nowe = [wiersz("Falownik", "Solax X3-NEO 10 kW", 1), wiersz("EMS Zeronest", "EMS Zeronest", 1)]
		w = z.waliduj_producenta("Solax", MAG, nowe, nowe, KATALOG, "Solax")
		self.assertEqual(w.ostrzezenia, ())

	def test_solax_sama_pv_bez_ostrzezenia_o_ems(self):
		nowe = [wiersz("Falownik", "Solax X3-NEO 10 kW", 1)]
		w = z.waliduj_producenta("Solax", "Fotowoltaika", nowe, nowe, KATALOG, "Solax")
		self.assertEqual(w.ostrzezenia, ())

	def test_licznik_przy_foxess_ostrzezenie(self):
		nowe = [wiersz("Licznik", "Dodatkowy licznik", 1)]
		w = z.waliduj_producenta("FoxESS", "Fotowoltaika", nowe, nowe, KATALOG, "FoxESS")
		self.assertEqual(w.ostrzezenia, ("Dodatkowy licznik nie jest dostępny z producentem FoxESS.",))

	def test_nie_mutuje_wejscia(self):
		nowe = wiersze_hoymiles()
		stare = wiersze_hoymiles()
		kopia = [dict(x) for x in nowe]
		katalog = [dict(x) for x in KATALOG]
		z.waliduj_producenta("Solax", MAG, nowe, stare, KATALOG, "Sigenergy")
		self.assertEqual(nowe, kopia)
		self.assertEqual(KATALOG, katalog)

	def test_komunikaty_bez_pauz(self):
		nowe = [*wiersze_hoymiles(), wiersz("Licznik Pstryk", "Pstryk", 1)]
		w = self.waliduj("Solax", nowe)
		for tekst in (*w.bledy, *w.ostrzezenia):
			self.assertNotIn("\u2014", tekst)
			self.assertNotIn("\u2013", tekst)


class TestFormatuj(unittest.TestCase):
	def test_tysiace(self):
		self.assertEqual(z.formatuj_kwote(48200), "48 200,00")

	def test_miliony(self):
		self.assertEqual(z.formatuj_kwote("1234567.8"), "1 234 567,80")

	def test_male(self):
		self.assertEqual(z.formatuj_kwote(0), "0,00")
		self.assertEqual(z.formatuj_kwote("999,5"), "999,50")

	def test_ujemne(self):
		self.assertEqual(z.formatuj_kwote(-1500), "-1 500,00")


if __name__ == "__main__":
	unittest.main()
