import copy
import unittest
from datetime import date

from crm.volteo_kredyt import (
	POLA_WNIOSKODAWCY,
	brakujace_dane_wnioskodawcy,
	kontakt_z_wnioskodawcy,
	prefill_z_wnioskodawcy,
)
from crm.volteo_kredyt_pdf import zbuduj_kontekst_kredytu

_DZIS = date(2026, 9, 23)

_WNIOSKODAWCA_PELNY = {
	"wnioskodawca_pesel": "85010112345",
	"wnioskodawca_imiona": "Jan Piotr",
	"wnioskodawca_nazwisko": "Kowalski",
	"wnioskodawca_telefon": "600100200",
	"wnioskodawca_email": "jan.kowalski@example.com",
	"wnioskodawca_kod_pocztowy": "00-001",
	"wnioskodawca_miejscowosc": "Warszawa",
	"wnioskodawca_ulica": "Marszałkowska",
	"wnioskodawca_nr_domu": "12",
	"wnioskodawca_nr_lokalu": "34",
}


class TestKontaktZWnioskodawcy(unittest.TestCase):
	def test_a_pelny_rekord(self: "TestKontaktZWnioskodawcy") -> None:
		wynik = kontakt_z_wnioskodawcy(_WNIOSKODAWCA_PELNY)
		self.assertEqual(
			wynik,
			{
				"first_name": "Jan Piotr",
				"last_name": "Kowalski",
				"custom_pesel": "85010112345",
				"mobile_no": "600100200",
				"email": "jan.kowalski@example.com",
				"custom_ulica": "Marszałkowska",
				"custom_nr_domu": "12",
				"custom_nr_mieszkania": "34",
				"custom_kod_pocztowy": "00-001",
				"custom_miasto": "Warszawa",
			},
		)

	def test_b_pusty_slownik(self: "TestKontaktZWnioskodawcy") -> None:
		wynik = kontakt_z_wnioskodawcy({})
		self.assertEqual(
			wynik,
			{
				"first_name": "",
				"last_name": "",
				"custom_pesel": "",
				"mobile_no": "",
				"email": "",
				"custom_ulica": "",
				"custom_nr_domu": "",
				"custom_nr_mieszkania": "",
				"custom_kod_pocztowy": "",
				"custom_miasto": "",
			},
		)

	def test_c_wszystkie_pola_jako_puste_stringi(self: "TestKontaktZWnioskodawcy") -> None:
		dane = {pole: "" for pole in POLA_WNIOSKODAWCY}
		wynik = kontakt_z_wnioskodawcy(dane)
		self.assertTrue(all(wartosc == "" for wartosc in wynik.values()))

	def test_d_wartosci_none(self: "TestKontaktZWnioskodawcy") -> None:
		dane = {pole: None for pole in POLA_WNIOSKODAWCY}
		wynik = kontakt_z_wnioskodawcy(dane)
		self.assertTrue(all(wartosc == "" for wartosc in wynik.values()))

	def test_e_niektore_pola_none_niektore_wypelnione(self: "TestKontaktZWnioskodawcy") -> None:
		dane = {
			"wnioskodawca_pesel": "85010112345",
			"wnioskodawca_imiona": None,
			"wnioskodawca_nazwisko": "Kowalski",
			"wnioskodawca_email": None,
		}
		wynik = kontakt_z_wnioskodawcy(dane)
		self.assertEqual(wynik["custom_pesel"], "85010112345")
		self.assertEqual(wynik["first_name"], "")
		self.assertEqual(wynik["last_name"], "Kowalski")
		self.assertEqual(wynik["email"], "")

	def test_f_nie_mutuje_wejscia(self: "TestKontaktZWnioskodawcy") -> None:
		dane = copy.deepcopy(_WNIOSKODAWCA_PELNY)
		przed = copy.deepcopy(dane)
		kontakt_z_wnioskodawcy(dane)
		self.assertEqual(dane, przed)


class TestPrefillZWnioskodawcy(unittest.TestCase):
	def test_a_pelny_rekord(self: "TestPrefillZWnioskodawcy") -> None:
		wynik = prefill_z_wnioskodawcy(_WNIOSKODAWCA_PELNY)
		self.assertEqual(
			wynik,
			{
				"pesel": "85010112345",
				"imiona": "Jan Piotr",
				"nazwisko": "Kowalski",
				"telefon": "600100200",
				"email": "jan.kowalski@example.com",
				"kod_pocztowy": "00-001",
				"miejscowosc": "Warszawa",
				"ulica": "Marszałkowska",
				"nr_domu": "12",
				"nr_lokalu": "34",
			},
		)

	def test_b_pusty_slownik(self: "TestPrefillZWnioskodawcy") -> None:
		wynik = prefill_z_wnioskodawcy({})
		self.assertTrue(all(wartosc == "" for wartosc in wynik.values()))
		self.assertEqual(set(wynik.keys()), {"pesel", "imiona", "nazwisko", "telefon", "email", "kod_pocztowy", "miejscowosc", "ulica", "nr_domu", "nr_lokalu"})

	def test_c_wszystkie_pola_jako_puste_stringi(self: "TestPrefillZWnioskodawcy") -> None:
		dane = {pole: "" for pole in POLA_WNIOSKODAWCY}
		wynik = prefill_z_wnioskodawcy(dane)
		self.assertTrue(all(wartosc == "" for wartosc in wynik.values()))

	def test_d_wartosci_none(self: "TestPrefillZWnioskodawcy") -> None:
		dane = {pole: None for pole in POLA_WNIOSKODAWCY}
		wynik = prefill_z_wnioskodawcy(dane)
		self.assertTrue(all(wartosc == "" for wartosc in wynik.values()))

	def test_e_niektore_pola_none_niektore_wypelnione(self: "TestPrefillZWnioskodawcy") -> None:
		dane = {
			"wnioskodawca_ulica": "Długa",
			"wnioskodawca_nr_domu": None,
			"wnioskodawca_miejscowosc": "Gdańsk",
		}
		wynik = prefill_z_wnioskodawcy(dane)
		self.assertEqual(wynik["ulica"], "Długa")
		self.assertEqual(wynik["nr_domu"], "")
		self.assertEqual(wynik["miejscowosc"], "Gdańsk")

	def test_f_nie_mutuje_wejscia(self: "TestPrefillZWnioskodawcy") -> None:
		dane = copy.deepcopy(_WNIOSKODAWCA_PELNY)
		przed = copy.deepcopy(dane)
		prefill_z_wnioskodawcy(dane)
		self.assertEqual(dane, przed)

	def test_g_ksztalt_przekluczony_rozny_od_surowego(self: "TestPrefillZWnioskodawcy") -> None:
		# Dokumentuje w teście dokładnie tę klasę błędu (2026-08-05, 2026-08-15):
		# prefill nie ma żadnego klucza stylu Contact poza `email`, wspólnym
		# dla obu kształtów.
		prefill = prefill_z_wnioskodawcy(_WNIOSKODAWCA_PELNY)
		kontakt = kontakt_z_wnioskodawcy(_WNIOSKODAWCA_PELNY)
		wspolne_klucze = set(prefill.keys()) & set(kontakt.keys())
		self.assertEqual(wspolne_klucze, {"email"})


class TestBrakujaceDaneWnioskodawcy(unittest.TestCase):
	def test_a_wszystko_wypelnione_nic_nie_brakuje(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		self.assertEqual(brakujace_dane_wnioskodawcy(_WNIOSKODAWCA_PELNY), [])

	def test_b_pusty_slownik_brakuje_9_wymaganych(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		wynik = brakujace_dane_wnioskodawcy({})
		self.assertEqual(len(wynik), 9)
		self.assertNotIn("wnioskodawca_nr_lokalu", wynik)

	def test_c_nr_lokalu_pusty_nie_trafia_na_liste(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		dane = dict(_WNIOSKODAWCA_PELNY)
		dane["wnioskodawca_nr_lokalu"] = ""
		self.assertEqual(brakujace_dane_wnioskodawcy(dane), [])

	def test_d_nr_lokalu_biale_znaki_tez_nie_trafia_na_liste(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		dane = dict(_WNIOSKODAWCA_PELNY)
		dane["wnioskodawca_nr_lokalu"] = "   "
		self.assertEqual(brakujace_dane_wnioskodawcy(dane), [])

	def test_e_kazde_z_9_wymaganych_pol_pojedynczo_pusty(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		for pole in POLA_WNIOSKODAWCY:
			if pole == "wnioskodawca_nr_lokalu":
				continue
			with self.subTest(pole=pole):
				dane = dict(_WNIOSKODAWCA_PELNY)
				dane[pole] = ""
				self.assertIn(pole, brakujace_dane_wnioskodawcy(dane))

	def test_f_kazde_z_9_wymaganych_pol_pojedynczo_none(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		for pole in POLA_WNIOSKODAWCY:
			if pole == "wnioskodawca_nr_lokalu":
				continue
			with self.subTest(pole=pole):
				dane = dict(_WNIOSKODAWCA_PELNY)
				dane[pole] = None
				self.assertIn(pole, brakujace_dane_wnioskodawcy(dane))

	def test_g_kolejnosc_wg_pola_wnioskodawcy(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		dane = dict(_WNIOSKODAWCA_PELNY)
		dane["wnioskodawca_ulica"] = ""
		dane["wnioskodawca_pesel"] = ""
		dane["wnioskodawca_nazwisko"] = ""
		wynik = brakujace_dane_wnioskodawcy(dane)
		self.assertEqual(wynik, ["wnioskodawca_pesel", "wnioskodawca_nazwisko", "wnioskodawca_ulica"])

	def test_h_zero_jako_string_nie_jest_puste(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		dane = dict(_WNIOSKODAWCA_PELNY)
		dane["wnioskodawca_nr_domu"] = "0"
		self.assertNotIn("wnioskodawca_nr_domu", brakujace_dane_wnioskodawcy(dane))

	def test_i_nie_mutuje_wejscia(self: "TestBrakujaceDaneWnioskodawcy") -> None:
		dane = {}
		przed = dict(dane)
		brakujace_dane_wnioskodawcy(dane)
		self.assertEqual(dane, przed)


class TestIntegracjaZBudujKontekstKredytu(unittest.TestCase):
	def test_a_dane_wnioskodawcy_wypelniaja_kontekst_pdf(self: "TestIntegracjaZBudujKontekstKredytu") -> None:
		kontekst = zbuduj_kontekst_kredytu({}, kontakt_z_wnioskodawcy(_WNIOSKODAWCA_PELNY), _DZIS)
		self.assertEqual(kontekst["pesel"], "85010112345")
		self.assertEqual(kontekst["imiona"], "Jan Piotr")
		self.assertEqual(kontekst["nazwisko"], "Kowalski")
		self.assertEqual(kontekst["telefon"], "600100200")
		self.assertEqual(kontekst["email"], "jan.kowalski@example.com")
		self.assertEqual(kontekst["kod_pocztowy"], "00-001")
		self.assertEqual(kontekst["miejscowosc"], "Warszawa")
		self.assertEqual(kontekst["ulica"], "Marszałkowska")
		self.assertEqual(kontekst["nr_domu"], "12")
		self.assertEqual(kontekst["nr_lokalu"], "34")

	def test_b_prefill_zamiast_kontaktu_daje_pusty_blok_poza_email(self: "TestIntegracjaZBudujKontekstKredytu") -> None:
		# Sonda dokumentująca klasę błędu z 2026-08-05/2026-08-15: podanie
		# ksztaltu przekluczonego tam, gdzie oczekiwany jest surowy, daje
		# pusty blok danych klienta poza `email`.
		prefill_zle_uzyty = prefill_z_wnioskodawcy(_WNIOSKODAWCA_PELNY)
		kontekst = zbuduj_kontekst_kredytu({}, prefill_zle_uzyty, _DZIS)
		self.assertEqual(kontekst["pesel"], "")
		self.assertEqual(kontekst["imiona"], "")
		self.assertEqual(kontekst["nazwisko"], "")
		self.assertEqual(kontekst["telefon"], "")
		self.assertEqual(kontekst["ulica"], "")
		self.assertEqual(kontekst["nr_domu"], "")
		self.assertEqual(kontekst["nr_lokalu"], "")
		self.assertEqual(kontekst["kod_pocztowy"], "")
		self.assertEqual(kontekst["miejscowosc"], "")


if __name__ == "__main__":
	unittest.main()
