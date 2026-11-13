# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import dataclasses
import unittest
from datetime import date, datetime

from crm.volteo_reguly_przydzialu import (
	DANE_PRZYKLADOWE_LEAD_BEZPOSREDNI,
	KLUCZ_ODROCZONYCH,
	PLACEHOLDERY_LEAD_BEZPOSREDNI,
	POLE_LIMITU,
	POLE_TRESCI,
	PREFIKS_KLUCZA,
	PREFIKS_PONOWNE,
	TRESC_LEAD_BEZPOSREDNI_DOMYSLNA,
	Regula,
	czy_ponowne_do_handlowca,
	czy_wyslac_odroczone,
	dopasuj_regule,
	grupuj_kandydatow_srodka,
	klucz_alertu_limitu,
	klucz_licznika_dnia,
	klucz_rezerwacji,
	limit_dzienny_lead,
	link_mapy,
	ma_wspolrzedne,
	najblizsza_regula,
	odkoduj_odroczenie_lead,
	odleglosc_km,
	opis_obszaru,
	ostrzezenia_reguly,
	policz_leady_w_promieniu,
	regula_z_wiersza,
	szablon_lead_bezposredni,
	tekst_sladu_przydzialu,
	tekst_sladu_sms,
	uporzadkuj,
	waliduj_regule,
	zakoduj_odroczenie_lead,
	zbuduj_wynik_sprawdzenia,
	zdecyduj_sms,
)
from crm.volteo_sms import liczba_czesci_sms, waliduj_szablon, wypelnij_szablon

GORZOW = (52.7368, 15.2288)
ZIELONA = (51.9356, 15.5062)
MIEDZYRZECZ = (52.4447, 15.5780)
SWIEBODZIN = (52.2474, 15.5336)
PILA = (53.1510, 16.7383)


def reg(name, handlowiec, srodek, promien, kolejnosc=0, aktywna=1, nazwa="X"):
	return Regula(
		name=name,
		handlowiec=handlowiec,
		srodek_nazwa=nazwa,
		srodek_kod="",
		srodek_lat=srodek[0],
		srodek_lng=srodek[1],
		promien_km=promien,
		aktywna=bool(aktywna),
		kolejnosc=kolejnosc,
	)


G = reg("R1", "g@x", GORZOW, 70, 1, nazwa="Gorzów Wielkopolski")
Z = reg("R2", "z@x", ZIELONA, 60, 2, nazwa="Zielona Góra")


class TestOdleglosc(unittest.TestCase):
	def test_zero(self):
		self.assertEqual(odleglosc_km(*GORZOW, *GORZOW), 0.0)

	def test_miedzyrzecz_gorzow(self):
		self.assertAlmostEqual(odleglosc_km(*MIEDZYRZECZ, *GORZOW), 40, delta=1)

	def test_miedzyrzecz_zielona(self):
		self.assertAlmostEqual(odleglosc_km(*MIEDZYRZECZ, *ZIELONA), 57, delta=1)

	def test_swiebodzin_gorzow(self):
		self.assertAlmostEqual(odleglosc_km(*SWIEBODZIN, *GORZOW), 58, delta=1)

	def test_swiebodzin_zielona(self):
		self.assertAlmostEqual(odleglosc_km(*SWIEBODZIN, *ZIELONA), 35, delta=1)

	def test_pila_gorzow(self):
		self.assertAlmostEqual(odleglosc_km(*PILA, *GORZOW), 111, delta=1)

	def test_symetria(self):
		self.assertAlmostEqual(odleglosc_km(*PILA, *GORZOW), odleglosc_km(*GORZOW, *PILA))


class TestMaWspolrzedne(unittest.TestCase):
	def test_poprawne(self):
		self.assertTrue(ma_wspolrzedne(52.4, 15.5))

	def test_napisy_liczbowe(self):
		self.assertTrue(ma_wspolrzedne("52.4", "15,5"))

	def test_none(self):
		self.assertFalse(ma_wspolrzedne(None, 15.5))
		self.assertFalse(ma_wspolrzedne(52.4, None))

	def test_puste(self):
		self.assertFalse(ma_wspolrzedne("", ""))

	def test_nieliczbowe(self):
		self.assertFalse(ma_wspolrzedne("abc", 15.5))

	def test_zero_zero(self):
		self.assertFalse(ma_wspolrzedne(0, 0))
		self.assertFalse(ma_wspolrzedne(0.0, "0"))

	def test_nan_inf(self):
		self.assertFalse(ma_wspolrzedne(float("nan"), 15))
		self.assertFalse(ma_wspolrzedne(float("inf"), 15))


class TestRegulaZWiersza(unittest.TestCase):
	def test_stringi(self):
		r = regula_z_wiersza(
			{
				"name": " R1 ",
				"handlowiec": "g@x",
				"srodek_nazwa": "Gorzów",
				"srodek_lat": "52.7368",
				"srodek_lng": "15.2288",
				"promien_km": "70",
				"aktywna": "1",
				"kolejnosc": "3",
			}
		)
		self.assertEqual((r.name, r.promien_km, r.kolejnosc, r.aktywna), ("R1", 70, 3, True))
		self.assertEqual(r.srodek_lat, 52.7368)

	def test_none_i_braki(self):
		r = regula_z_wiersza({"name": None, "aktywna": None, "promien_km": None})
		self.assertEqual((r.name, r.handlowiec, r.promien_km, r.kolejnosc), ("", "", 0, 0))
		self.assertFalse(r.aktywna)
		self.assertIsNone(r.srodek_lat)

	def test_aktywna_zero_string(self):
		self.assertFalse(regula_z_wiersza({"aktywna": "0"}).aktywna)
		self.assertFalse(regula_z_wiersza({"aktywna": 0}).aktywna)
		self.assertTrue(regula_z_wiersza({"aktywna": 1}).aktywna)

	def test_frozen(self):
		with self.assertRaises(dataclasses.FrozenInstanceError):
			G.name = "inna"  # type: ignore[misc]


class TestUporzadkuj(unittest.TestCase):
	def test_po_kolejnosci(self):
		self.assertEqual([r.name for r in uporzadkuj([Z, G])], ["R1", "R2"])

	def test_remis_po_name(self):
		a, b = reg("B", "x", GORZOW, 10, 1), reg("A", "x", GORZOW, 10, 1)
		self.assertEqual([r.name for r in uporzadkuj([a, b])], ["A", "B"])

	def test_nie_mutuje(self):
		wejscie = [Z, G]
		uporzadkuj(wejscie)
		self.assertEqual(wejscie, [Z, G])


class TestDopasuj(unittest.TestCase):
	def test_jedna(self):
		d = dopasuj_regule(*PILA, [G, Z])
		self.assertIsNone(d)

	def test_miedzyrzecz_pierwsza_wg_kolejnosci(self):
		d = dopasuj_regule(*MIEDZYRZECZ, [Z, G])
		self.assertEqual(d.regula.name, "R1")
		self.assertAlmostEqual(d.odleglosc_km, 40, delta=1)
		self.assertEqual([r.name for r, _ in d.inne_pasujace], ["R2"])
		self.assertAlmostEqual(d.inne_pasujace[0][1], 57, delta=1)

	def test_swiebodzin_tylko_zielona(self):
		d = dopasuj_regule(*SWIEBODZIN, [G, Z])
		self.assertEqual(d.regula.name, "R1")  # 58 km <= 70 km Gorzowa
		d2 = dopasuj_regule(*SWIEBODZIN, [reg("R1", "g@x", GORZOW, 50, 1), Z])
		self.assertEqual(d2.regula.name, "R2")
		self.assertEqual(d2.inne_pasujace, [])

	def test_granica_rowna_promieniowi(self):
		odl = odleglosc_km(*MIEDZYRZECZ, *GORZOW)
		r = reg("R", "x", GORZOW, 1)
		r = dataclasses.replace(r, promien_km=int(odl) + 1)
		self.assertIsNotNone(dopasuj_regule(*MIEDZYRZECZ, [r]))
		r2 = dataclasses.replace(r, promien_km=int(odl) - 1)
		self.assertIsNone(dopasuj_regule(*MIEDZYRZECZ, [r2]))

	def test_nieaktywna(self):
		self.assertIsNone(dopasuj_regule(*MIEDZYRZECZ, [reg("R", "x", GORZOW, 70, aktywna=0)]))

	def test_promien_zero(self):
		self.assertIsNone(dopasuj_regule(*GORZOW, [reg("R", "x", GORZOW, 0)]))

	def test_regula_bez_wspolrzednych(self):
		r = dataclasses.replace(G, srodek_lat=None, srodek_lng=None)
		self.assertIsNone(dopasuj_regule(*GORZOW, [r]))
		r0 = dataclasses.replace(G, srodek_lat=0.0, srodek_lng=0.0)
		self.assertIsNone(dopasuj_regule(*GORZOW, [r0]))

	def test_dozwoleni_handlowcy(self):
		d = dopasuj_regule(*MIEDZYRZECZ, [G, Z], dozwoleni_handlowcy={"z@x"})
		self.assertEqual(d.regula.name, "R2")
		self.assertIsNone(dopasuj_regule(*MIEDZYRZECZ, [G, Z], dozwoleni_handlowcy=set()))

	def test_dozwoleni_none_nie_filtruje(self):
		self.assertIsNotNone(dopasuj_regule(*MIEDZYRZECZ, [G], dozwoleni_handlowcy=None))

	def test_brak_wspolrzednych_leada(self):
		self.assertIsNone(dopasuj_regule(None, None, [G]))
		self.assertIsNone(dopasuj_regule(0, 0, [G]))

	def test_pusta_lista(self):
		self.assertIsNone(dopasuj_regule(*GORZOW, []))

	def test_nie_mutuje_wejscia(self):
		wejscie = [Z, G]
		dopasuj_regule(*MIEDZYRZECZ, wejscie)
		self.assertEqual(wejscie, [Z, G])

	def test_dopasowanie_frozen(self):
		d = dopasuj_regule(*GORZOW, [G])
		with self.assertRaises(dataclasses.FrozenInstanceError):
			d.odleglosc_km = 1.0  # type: ignore[misc]


class TestNajblizsza(unittest.TestCase):
	def test_najblizsza(self):
		r, odl = najblizsza_regula(*SWIEBODZIN, [G, Z])
		self.assertEqual(r.name, "R2")
		self.assertAlmostEqual(odl, 35, delta=1)

	def test_pomija_nieaktywne(self):
		r, _ = najblizsza_regula(*SWIEBODZIN, [G, dataclasses.replace(Z, aktywna=False)])
		self.assertEqual(r.name, "R1")

	def test_brak(self):
		self.assertIsNone(najblizsza_regula(*PILA, []))
		self.assertIsNone(najblizsza_regula(None, None, [G]))

	def test_ignoruje_promien(self):
		r, odl = najblizsza_regula(*PILA, [G])
		self.assertEqual(r.name, "R1")
		self.assertAlmostEqual(odl, 111, delta=1)


class TestWaliduj(unittest.TestCase):
	def dane(self, **zmiany):
		d = {"handlowiec": "g@x", "promien_km": 70, "srodek_lat": 52.7, "srodek_lng": 15.2}
		d.update(zmiany)
		return d

	def test_poprawna(self):
		self.assertEqual(waliduj_regule(self.dane()), [])

	def test_brak_handlowca(self):
		self.assertEqual(len(waliduj_regule(self.dane(handlowiec="  "))), 1)

	def test_promien_granice(self):
		self.assertEqual(waliduj_regule(self.dane(promien_km=1)), [])
		self.assertEqual(waliduj_regule(self.dane(promien_km=300)), [])
		self.assertEqual(len(waliduj_regule(self.dane(promien_km=0))), 1)
		self.assertEqual(len(waliduj_regule(self.dane(promien_km=301))), 1)

	def test_promien_niecalkowity_lub_pusty(self):
		self.assertEqual(len(waliduj_regule(self.dane(promien_km=70.5))), 1)
		self.assertEqual(len(waliduj_regule(self.dane(promien_km=None))), 1)
		self.assertEqual(len(waliduj_regule(self.dane(promien_km="abc"))), 1)

	def test_promien_string_calkowity(self):
		self.assertEqual(waliduj_regule(self.dane(promien_km="70")), [])

	def test_brak_wspolrzednych(self):
		self.assertIn("współrzędnych", waliduj_regule(self.dane(srodek_lat=None))[0])
		self.assertIn("współrzędnych", waliduj_regule(self.dane(srodek_lat=0, srodek_lng=0))[0])

	def test_poza_polska(self):
		self.assertIn("poza Polską", waliduj_regule(self.dane(srodek_lat=48.0))[0])
		self.assertIn("poza Polską", waliduj_regule(self.dane(srodek_lat=56.0))[0])
		self.assertIn("poza Polską", waliduj_regule(self.dane(srodek_lng=13.0))[0])
		self.assertIn("poza Polską", waliduj_regule(self.dane(srodek_lng=25.0))[0])

	def test_wiele_bledow(self):
		self.assertEqual(len(waliduj_regule({})), 3)


class TestOpisILink(unittest.TestCase):
	def test_opis(self):
		self.assertEqual(opis_obszaru(G), "70 km, środek: Gorzów Wielkopolski")

	def test_link(self):
		self.assertEqual(link_mapy(52.4447, 15.5780), "https://maps.google.com/?q=52.4447,15.5780")

	def test_link_cztery_miejsca(self):
		self.assertEqual(link_mapy(52.4447, 15.578), "https://maps.google.com/?q=52.4447,15.5780")
		self.assertEqual(link_mapy("52,4", "15.5"), "https://maps.google.com/?q=52.4000,15.5000")

	def test_link_pusty(self):
		self.assertEqual(link_mapy(None, None), "")
		self.assertEqual(link_mapy(0, 0), "")


class TestStaleSms(unittest.TestCase):
	def test_tresc_domyslna_znak_w_znak(self):
		self.assertEqual(
			TRESC_LEAD_BEZPOSREDNI_DOMYSLNA,
			"Nowy lead dla Ciebie: {klient}, tel. {telefon}, {kod}, PV: {ma_pv}. Mapa: {mapa}",
		)

	def test_tresc_przechodzi_walidacje(self):
		self.assertIsNone(waliduj_szablon(TRESC_LEAD_BEZPOSREDNI_DOMYSLNA, PLACEHOLDERY_LEAD_BEZPOSREDNI))

	def test_wzorcowy_117_znakow_1_czesc(self):
		tresc, _ = wypelnij_szablon(
			TRESC_LEAD_BEZPOSREDNI_DOMYSLNA,
			DANE_PRZYKLADOWE_LEAD_BEZPOSREDNI,
			PLACEHOLDERY_LEAD_BEZPOSREDNI,
		)
		self.assertEqual(len(tresc), 117)
		self.assertEqual(liczba_czesci_sms(tresc), 1)

	def test_dane_przykladowe_obejmuja_placeholdery(self):
		self.assertEqual(set(DANE_PRZYKLADOWE_LEAD_BEZPOSREDNI), set(PLACEHOLDERY_LEAD_BEZPOSREDNI))

	def test_ponowne(self):
		self.assertEqual(PREFIKS_PONOWNE, "Ponownie: ")

	def test_klucze(self):
		self.assertEqual(klucz_licznika_dnia(date(2026, 11, 13)), f"{PREFIKS_KLUCZA}2026-11-13")
		self.assertEqual(klucz_licznika_dnia(datetime(2026, 11, 13, 23, 59)), f"{PREFIKS_KLUCZA}2026-11-13")
		self.assertEqual(klucz_rezerwacji("CRM-LEAD-1"), f"{PREFIKS_KLUCZA}rezerwacja:CRM-LEAD-1")
		self.assertTrue(KLUCZ_ODROCZONYCH.startswith(PREFIKS_KLUCZA))


class TestZdecydujSms(unittest.TestCase):
	def test_wyslij(self):
		self.assertEqual(zdecyduj_sms(True, True, False, 0, 100), "wyslij")

	def test_wylaczone_pierwsze(self):
		self.assertEqual(zdecyduj_sms(False, False, True, 999, 0), "wylaczone")

	def test_brak_numeru_przed_limitem_i_cisza(self):
		self.assertEqual(zdecyduj_sms(True, False, True, 999, 0), "brak_numeru")

	def test_limit_przed_cisza(self):
		self.assertEqual(zdecyduj_sms(True, True, True, 100, 100), "limit")

	def test_limit_zero_blokuje(self):
		self.assertEqual(zdecyduj_sms(True, True, False, 0, 0), "limit")

	def test_ostatni_w_limicie(self):
		self.assertEqual(zdecyduj_sms(True, True, False, 99, 100), "wyslij")

	def test_cisza(self):
		self.assertEqual(zdecyduj_sms(True, True, True, 0, 100), "odloz")


class TestSlady(unittest.TestCase):
	def test_przydzial(self):
		self.assertEqual(
			tekst_sladu_przydzialu("Grzegorz Furmann", "Gorzów Wielkopolski", 70, 58.3),
			"Lead przydzielony bezpośrednio: Grzegorz Furmann "
			"(reguła: 70 km, środek: Gorzów Wielkopolski; odległość 58 km)",
		)

	def test_sms_wszystkie_wyniki(self):
		for wynik in ("wyslij", "wylaczone", "brak_numeru", "odloz", "limit", "blad"):
			tekst = tekst_sladu_sms(wynik, "Jan Handlowiec")
			self.assertIn("Jan Handlowiec", tekst)
			self.assertNotIn("CC", tekst)

	def test_sms_rozne_teksty(self):
		teksty = {
			tekst_sladu_sms(w, "X") for w in ("wyslij", "wylaczone", "brak_numeru", "odloz", "limit", "blad")
		}
		self.assertEqual(len(teksty), 6)

	def test_sms_nieznany_wynik_nie_rzuca(self):
		self.assertIn("dziwny", tekst_sladu_sms("dziwny", "X"))

	def test_brak_myslnikow(self):
		import crm.volteo_reguly_przydzialu as modul

		with open(modul.__file__, encoding="utf-8") as f:
			zrodlo = f.read()
		self.assertNotIn(chr(0x2014), zrodlo)
		self.assertNotIn(chr(0x2013), zrodlo)


def _r(name, handlowiec, lat, lng, promien, kolejnosc=1, aktywna=True):
	return Regula(name, handlowiec, "Srodek " + name, "00-000", lat, lng, promien, aktywna, kolejnosc)


class TestApiRegul(unittest.TestCase):
	def test_grupowanie_kandydatow(self):
		wiersze = [
			{
				"kod": "66-401",
				"miejscowosc": "Gorzów",
				"powiat": "gorzowski",
				"wojewodztwo": "lubuskie",
				"lat": 52.7,
				"lng": 15.2,
			},
			{
				"kod": "66-400",
				"miejscowosc": "gorzów",
				"powiat": "Gorzowski",
				"wojewodztwo": "lubuskie",
				"lat": 52.7,
				"lng": 15.2,
			},
			{
				"kod": "66-500",
				"miejscowosc": "Gorzów",
				"powiat": "inny",
				"wojewodztwo": "x",
				"lat": 52.6,
				"lng": 15.1,
			},
			{"kod": "00-001", "miejscowosc": "Bez", "powiat": "p", "wojewodztwo": "x", "lat": 0, "lng": 0},
			{"kod": "00-002", "miejscowosc": "", "powiat": "p", "wojewodztwo": "x", "lat": 52, "lng": 20},
		]
		wynik = grupuj_kandydatow_srodka(wiersze)
		self.assertEqual([w["kod"] for w in wynik], ["66-400", "66-500"])
		self.assertEqual(len(grupuj_kandydatow_srodka(wiersze, limit=1)), 1)
		self.assertEqual(grupuj_kandydatow_srodka([]), [])

	def test_liczenie_leadow(self):
		r1 = _r("a", "u1", 52.0, 20.0, 10)
		r2 = _r("b", "u2", None, None, 10)
		r3 = _r("c", "u3", 52.0, 20.0, 0)
		punkty = [(52.0, 20.0), (52.01, 20.0), (53.5, 20.0), (0, 0), (None, 1)]
		self.assertEqual(policz_leady_w_promieniu([r1, r2, r3], punkty), {"a": 2, "b": 0, "c": 0})

	def test_ostrzezenia(self):
		self.assertEqual(ostrzezenia_reguly(None, False, False, False), ["Konto nie istnieje"])
		self.assertEqual(ostrzezenia_reguly({"enabled": 1}, True, True, True), [])
		self.assertEqual(
			ostrzezenia_reguly({"enabled": 0}, False, False, False),
			["Konto wyłączone", "Brak roli handlowca", "Brak dostępu do Leadów", "Brak numeru telefonu"],
		)

	def test_wynik_regula(self):
		r1 = _r("a", "u1", 52.0, 20.0, 50, 1)
		r2 = _r("b", "u2", 52.1, 20.0, 50, 2)
		dop = dopasuj_regule(52.0, 20.0, [r1, r2])
		w = zbuduj_wynik_sprawdzenia(
			"00-001", {"miejscowosc": "X", "wojewodztwo": "y"}, dop, None, {"u1": "Jan K", "u2": "Ola M"}
		)
		self.assertTrue(w["znany"])
		self.assertEqual(w["wynik"], "regula")
		self.assertEqual(w["regula"]["handlowiec_nazwa"], "Jan K")
		self.assertEqual(w["regula"]["promien_km"], 50)
		self.assertEqual(w["odleglosc_km"], 0)
		self.assertEqual(w["inne_pasujace"][0]["handlowiec_nazwa"], "Ola M")
		self.assertEqual(w["inne_pasujace"][0]["odleglosc_km"], 11)
		self.assertIsNone(w["najblizsza"])

	def test_wynik_cc_z_najblizsza(self):
		r1 = _r("a", "u1", 52.0, 20.0, 5, 3)
		najb = najblizsza_regula(52.5, 20.0, [r1])
		w = zbuduj_wynik_sprawdzenia("00-001", {"miejscowosc": "X", "wojewodztwo": "y"}, None, najb, {})
		self.assertEqual(w["wynik"], "cc")
		self.assertIsNone(w["regula"])
		self.assertEqual(w["najblizsza"], {"kolejnosc": 3, "srodek_nazwa": "Srodek a", "odleglosc_km": 56})

	def test_wynik_kod_nieznany(self):
		w = zbuduj_wynik_sprawdzenia("99-999", None, None, None, {})
		self.assertFalse(w["znany"])
		self.assertEqual(w["wynik"], "cc")
		self.assertEqual(w["miejscowosc"], "")
		self.assertEqual(
			set(w),
			{
				"kod",
				"znany",
				"miejscowosc",
				"wojewodztwo",
				"wynik",
				"regula",
				"odleglosc_km",
				"inne_pasujace",
				"najblizsza",
			},
		)


class TestWebhookISmsLead(unittest.TestCase):
	def test_ponowne_do_handlowca_tylko_ze_znacznikiem_i_wlascicielem(self):
		self.assertTrue(czy_ponowne_do_handlowca(1, "a@x.pl"))
		self.assertTrue(czy_ponowne_do_handlowca("1", "a@x.pl"))
		self.assertFalse(czy_ponowne_do_handlowca(0, "a@x.pl"))
		self.assertFalse(czy_ponowne_do_handlowca("0", "a@x.pl"))
		self.assertFalse(czy_ponowne_do_handlowca(None, "a@x.pl"))
		self.assertFalse(czy_ponowne_do_handlowca(1, ""))
		self.assertFalse(czy_ponowne_do_handlowca(1, None))

	def test_odroczone_wymaga_tego_samego_wlasciciela_i_znacznika(self):
		self.assertTrue(czy_wyslac_odroczone("a@x.pl", "a@x.pl", 1))
		self.assertFalse(czy_wyslac_odroczone("a@x.pl", "b@x.pl", 1))
		self.assertFalse(czy_wyslac_odroczone("a@x.pl", "", 1))
		self.assertFalse(czy_wyslac_odroczone("a@x.pl", "a@x.pl", 0))
		self.assertFalse(czy_wyslac_odroczone("", "a@x.pl", 1))

	def test_limit_dzienny_lead(self):
		self.assertEqual(limit_dzienny_lead({}), 100)
		self.assertEqual(limit_dzienny_lead({POLE_LIMITU: ""}), 100)
		self.assertEqual(limit_dzienny_lead({POLE_LIMITU: "0"}), 0)
		self.assertEqual(limit_dzienny_lead({POLE_LIMITU: "25"}), 25)
		self.assertEqual(limit_dzienny_lead({POLE_LIMITU: -3}), 0)
		self.assertEqual(limit_dzienny_lead({POLE_LIMITU: "abc"}), 100)

	def test_szablon_domyslny_zapisany_i_ponowny(self):
		self.assertEqual(szablon_lead_bezposredni({}), TRESC_LEAD_BEZPOSREDNI_DOMYSLNA)
		self.assertEqual(szablon_lead_bezposredni({POLE_TRESCI: "  "}), TRESC_LEAD_BEZPOSREDNI_DOMYSLNA)
		self.assertEqual(szablon_lead_bezposredni({POLE_TRESCI: "Lead {klient}"}), "Lead {klient}")
		self.assertEqual(
			szablon_lead_bezposredni({POLE_TRESCI: "Lead {klient}"}, ponowne=True),
			PREFIKS_PONOWNE + "Lead {klient}",
		)
		self.assertTrue(szablon_lead_bezposredni({}, True).startswith(PREFIKS_PONOWNE))

	def test_kodowanie_odroczenia(self):
		tekst = zakoduj_odroczenie_lead(True, "a@x.pl")
		self.assertEqual(odkoduj_odroczenie_lead(tekst), (True, "a@x.pl"))
		self.assertEqual(odkoduj_odroczenie_lead(tekst.encode()), (True, "a@x.pl"))
		self.assertEqual(odkoduj_odroczenie_lead(zakoduj_odroczenie_lead(False, "")), (False, ""))
		for zle in (None, "", "nie json", "[]", '{"ponowne": "tak"}', "{}"):
			self.assertIsNone(odkoduj_odroczenie_lead(zle), zle)

	def test_klucz_alertu_ma_prefiks_i_dzien(self):
		klucz = klucz_alertu_limitu(date(2026, 11, 13))
		self.assertTrue(klucz.startswith(PREFIKS_KLUCZA))
		self.assertIn("2026-11-13", klucz)
		self.assertNotEqual(klucz, klucz_licznika_dnia(date(2026, 11, 13)))


if __name__ == "__main__":
	unittest.main()
