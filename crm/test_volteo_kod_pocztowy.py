# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy lookupu kodu pocztowego (ops#329), bez `frappe`:

python3 -m unittest crm.test_volteo_kod_pocztowy
"""

import copy
import unittest

from crm.volteo_kod_pocztowy import (
	jedyna_miejscowosc,
	normalizuj_kod,
	normalizuj_wojewodztwo_kodu,
	nowy_wiersz_cache,
	parsuj_odpowiedz_adresy,
	pola_do_uzupelnienia_cache,
	rozdziel_miejscowosci,
	scal_wynik,
	wiersz_kompletny,
)


def odpowiedz_adresy(match=None, lokalnosci=None, **poza_match):
	"""Ksztalt odpowiedzi Adresy.app `match`: results[0].match + extended_search."""
	wynik = {
		"match": {
			"miejscowosc": "Kościan",
			"gmina": "Kościan",
			"powiat": "kościański",
			"wojewodztwo": "wielkopolskie",
			**(match or {}),
		},
		**poza_match,
	}
	if lokalnosci is not None:
		wynik["extended_search"] = {"postal_localities": [{"miejscowosc": m} for m in lokalnosci]}
	return {"results": [wynik]}


class TestNormalizujKod(unittest.TestCase):
	def test_poprawne(self):
		for surowe, oczekiwane in [("64-000", "64-000"), (" 64-000 ", "64-000"), ("64000", "64-000")]:
			self.assertEqual(normalizuj_kod(surowe), oczekiwane)

	def test_niepoprawne(self):
		for surowe in ("", "6400", "64-0000", "64 000", "64-000 Kościan", "ab-cde", None, 64000):
			self.assertIsNone(normalizuj_kod(surowe), surowe)


class TestRozdzielMiejscowosci(unittest.TestCase):
	def test_tekst_z_nowymi_liniami(self):
		self.assertEqual(rozdziel_miejscowosci("Kościan\n Racot \n\nKościan"), ["Kościan", "Racot"])

	def test_lista(self):
		self.assertEqual(rozdziel_miejscowosci(["A", "", None, "B", "A"]), ["A", "B"])

	def test_puste(self):
		for surowe in (None, "", "\n \n", []):
			self.assertEqual(rozdziel_miejscowosci(surowe), [])


class TestWojewodztwo(unittest.TestCase):
	def test_kanon(self):
		for surowe, oczekiwane in [
			("DOLNOŚLĄSKIE", "dolnośląskie"),
			("województwo śląskie", "śląskie"),
			("woj. Mazowieckie", "mazowieckie"),
			("WOJ MAŁOPOLSKIE", "małopolskie"),
		]:
			self.assertEqual(normalizuj_wojewodztwo_kodu(surowe), oczekiwane)

	def test_spoza_kanonu(self):
		for surowe in ("Bawaria", "", None, "woj."):
			self.assertIsNone(normalizuj_wojewodztwo_kodu(surowe))


class TestWierszKompletny(unittest.TestCase):
	def test_geonames_bez_cities_i_gminy(self):
		self.assertFalse(wiersz_kompletny({"kod": "64-000", "miejscowosc": "Kościan", "lat": 52.0}))

	def test_brak_jednego_z_dwoch(self):
		self.assertFalse(wiersz_kompletny({"cities": "Kościan", "gmina": ""}))
		self.assertFalse(wiersz_kompletny({"cities": "\n", "gmina": "Kościan"}))

	def test_kompletny(self):
		self.assertTrue(wiersz_kompletny({"cities": "Kościan\nRacot", "gmina": "Kościan"}))

	def test_brak_wiersza(self):
		self.assertFalse(wiersz_kompletny(None))


class TestParsujOdpowiedzAdresy(unittest.TestCase):
	def test_lista_miejscowosci(self):
		wynik = parsuj_odpowiedz_adresy(
			odpowiedz_adresy(lokalnosci=["Kościan", "Racot", "Kościan"]), "64-000"
		)
		self.assertEqual(wynik["cities"], ["Kościan", "Racot"])
		self.assertEqual(wynik["gmina"], "Kościan")
		self.assertEqual(wynik["powiat"], "kościański")
		self.assertEqual(wynik["wojewodztwo"], "wielkopolskie")

	def test_pusta_lista_bierze_miejscowosc_z_match(self):
		for lokalnosci in ([], None):
			wynik = parsuj_odpowiedz_adresy(odpowiedz_adresy(lokalnosci=lokalnosci), "64-000")
			self.assertEqual(wynik["cities"], ["Kościan"])

	def test_zle_ksztalty(self):
		for odp in (None, [], "x", {}, {"results": []}, {"results": ["x"]}, {"results": [{"match": None}]}):
			self.assertIsNone(parsuj_odpowiedz_adresy(odp, "64-000"), odp)

	def test_pusty_match(self):
		odp = {"results": [{"match": {"miejscowosc": "", "gmina": None}}]}
		self.assertIsNone(parsuj_odpowiedz_adresy(odp, "64-000"))

	def test_inny_kod_w_dopasowaniu_odrzucony(self):
		odp = odpowiedz_adresy(match={"kod": "64-001"})
		self.assertIsNone(parsuj_odpowiedz_adresy(odp, "64-000"))

	def test_ten_sam_kod_w_dopasowaniu_przechodzi(self):
		odp = odpowiedz_adresy(match={"kod_pocztowy": "64000"})
		self.assertIsNotNone(parsuj_odpowiedz_adresy(odp, "64-000"))

	def test_lokalnosci_smieciowe_pomijane(self):
		odp = odpowiedz_adresy()
		odp["results"][0]["extended_search"] = {"postal_localities": ["x", {"miejscowosc": ""}, {"inne": 1}]}
		self.assertEqual(parsuj_odpowiedz_adresy(odp, "64-000")["cities"], ["Kościan"])

	def test_nie_mutuje(self):
		odp = odpowiedz_adresy(lokalnosci=["A"])
		kopia = copy.deepcopy(odp)
		parsuj_odpowiedz_adresy(odp, "64-000")
		self.assertEqual(odp, kopia)


ADRESY = {
	"miejscowosc": "Kościan",
	"gmina": "Kościan",
	"powiat": "kościański",
	"wojewodztwo": "WIELKOPOLSKIE",
	"cities": ["Kościan", "Racot"],
}


class TestScalWynik(unittest.TestCase):
	def test_nic(self):
		wynik = scal_wynik(None, None)
		self.assertFalse(wynik["found"])
		self.assertEqual(wynik["cities"], [])

	def test_wiersz_kompletny_bez_adresy(self):
		wiersz = {"wojewodztwo": "ŚLĄSKIE", "powiat": "gliwicki", "gmina": "Pyskowice", "cities": "A\nB"}
		wynik = scal_wynik(wiersz, None)
		self.assertTrue(wynik["found"])
		self.assertEqual(wynik["wojewodztwo"], "śląskie")
		self.assertEqual(wynik["cities"], ["A", "B"])

	def test_geonames_plus_adresy(self):
		wiersz = {
			"miejscowosc": "Inna",
			"powiat": "",
			"wojewodztwo": "wielkopolskie",
			"lat": 52.1,
			"lng": 16.6,
		}
		wynik = scal_wynik(wiersz, ADRESY)
		self.assertEqual(wynik["miejscowosc"], "Inna")
		self.assertEqual(wynik["powiat"], "kościański")
		self.assertEqual(wynik["gmina"], "Kościan")
		self.assertEqual(wynik["cities"], ["Kościan", "Racot"])
		self.assertEqual((wynik["lat"], wynik["lng"]), (52.1, 16.6))

	def test_tylko_adresy(self):
		wynik = scal_wynik(None, ADRESY)
		self.assertTrue(wynik["found"])
		self.assertEqual(wynik["wojewodztwo"], "wielkopolskie")
		self.assertNotIn("lat", wynik)

	def test_wojewodztwo_spoza_kanonu_puste(self):
		self.assertEqual(scal_wynik({"wojewodztwo": "Bawaria"}, None)["wojewodztwo"], "")

	def test_nie_mutuje(self):
		wiersz = {"cities": "A", "gmina": "G"}
		kopia_w, kopia_a = copy.deepcopy(wiersz), copy.deepcopy(ADRESY)
		scal_wynik(wiersz, ADRESY)
		self.assertEqual((wiersz, ADRESY), (kopia_w, kopia_a))


class TestCache(unittest.TestCase):
	def test_uzupelnia_tylko_puste(self):
		wiersz = {
			"miejscowosc": "Inna",
			"gmina": "",
			"powiat": "kościański",
			"wojewodztwo": "",
			"cities": None,
		}
		self.assertEqual(
			pola_do_uzupelnienia_cache(wiersz, ADRESY),
			{"gmina": "Kościan", "wojewodztwo": "wielkopolskie", "cities": "Kościan\nRacot"},
		)

	def test_kompletny_nic_do_zmiany(self):
		wiersz = {**ADRESY, "cities": "X"}
		self.assertEqual(pola_do_uzupelnienia_cache(wiersz, ADRESY), {})

	def test_wojewodztwo_spoza_kanonu_nie_zapisywane(self):
		zmiany = pola_do_uzupelnienia_cache({}, {**ADRESY, "wojewodztwo": "Bawaria"})
		self.assertNotIn("wojewodztwo", zmiany)

	def test_nowy_wiersz(self):
		self.assertEqual(
			nowy_wiersz_cache("64-000", ADRESY),
			{
				"kod": "64-000",
				"miejscowosc": "Kościan",
				"gmina": "Kościan",
				"powiat": "kościański",
				"wojewodztwo": "wielkopolskie",
				"cities": "Kościan\nRacot",
			},
		)


class TestJedynaMiejscowosc(unittest.TestCase):
	def test_jedna(self):
		self.assertEqual(jedyna_miejscowosc({"cities": ["Kościan"]}), "Kościan")
		self.assertEqual(jedyna_miejscowosc({"cities": "Kościan\n"}), "Kościan")

	def test_wiele_albo_brak(self):
		for wynik in ({"cities": ["A", "B"]}, {"cities": []}, {"miejscowosc": "GeoNames"}, None):
			self.assertEqual(jedyna_miejscowosc(wynik), "", wynik)


if __name__ == "__main__":
	unittest.main()
