import copy
import unittest
from datetime import date
from typing import Any

from crm.volteo_kredyt import brakujace_pola, kwota_poprawna
from crm.volteo_kredyt_pdf import KLUCZE_KONTEKSTU, zbuduj_kontekst_kredytu

_DZIS = date(2026, 8, 15)

# Zestaw kluczy zamrożony niezależnie od `KLUCZE_KONTEKSTU` w module produkcyjnym
# — gdyby ktoś przypadkiem usunął/dodał klucz w obu miejscach naraz, ten test
# nadal by się nie zgadzał z faktycznym wynikiem `zbuduj_kontekst_kredytu()`.
_OCZEKIWANE_KLUCZE = frozenset(
	{
		"pesel",
		"imiona",
		"nazwisko",
		"telefon",
		"email",
		"kod_pocztowy",
		"miejscowosc",
		"ulica",
		"nr_domu",
		"nr_lokalu",
		"miejsce_urodzenia",
		"rodzaj_seria_numer_dokumentu",
		"data_wydania_dokumentu",
		"data_waznosci_dokumentu",
		"adres_zameldowania",
		"adres_korespondencji",
		"liczba_osob_na_utrzymaniu",
		"kwota_800_plus",
		"dochod_wspolmalzonka",
		"zrodlo_dochodu_malzonka",
		"oplaty_miesieczne",
		"suma_zobowiazan",
		"numer_rachunku",
		"adres_zameldowania_tak",
		"adres_zameldowania_nie",
		"adres_korespondencji_tak",
		"adres_korespondencji_nie",
		"wyksztalcenie_wyzsze",
		"wyksztalcenie_srednie",
		"wyksztalcenie_zawodowe",
		"wyksztalcenie_podstawowe",
		"stan_kawaler_panna",
		"stan_rozwiedziony",
		"stan_malzenstwo_rozdzielnosc",
		"stan_malzenstwo_wspolnota",
		"stan_wdowiec_wdowa",
		"stan_separacja",
		"praca_data_zatrudnienia",
		"praca_okreslony_od",
		"praca_okreslony_do",
		"praca_nieokreslony_od",
		"praca_nip",
		"praca_nazwa_zakladu",
		"praca_adres_telefon",
		"praca_kwota_dochodu",
		"praca_umowa_o_prace",
		"praca_zlecenie",
		"praca_dzielo",
		"emerytura_numer_swiadczenia",
		"emerytura_od_kiedy",
		"emerytura_kwota_dochodu",
		"renta_numer_swiadczenia",
		"renta_od_kiedy",
		"renta_kwota_dochodu",
		"gospodarstwo_nip",
		"gospodarstwo_od_kiedy",
		"gospodarstwo_kwota_dochodu",
		"dzialalnosc_ryczalt",
		"dzialalnosc_kpir",
		"dzialalnosc_inne",
		"dzialalnosc_forma_inna",
		"dzialalnosc_nip",
		"dzialalnosc_nazwa",
		"dzialalnosc_adres_telefon",
		"dzialalnosc_od_kiedy",
		"dzialalnosc_kwota_dochodu",
		"inne_1_typ",
		"inne_2_typ",
		"inne_1_kwota",
		"inne_2_kwota",
		"podpis_data",
		"podpis_imie_nazwisko",
	}
)


def _kredyt(**nadpisania: Any) -> dict[str, Any]:
	"""Kompletny, "roboczo wypełniony" wniosek kredytowy — baza do modyfikacji w testach.

	Wszystkie grupy dochodu są domyślnie WYŁĄCZONE (0) — testy, które chcą
	sprawdzić konkretną grupę, włączają ją jawnie przez `nadpisania`.
	"""
	baza: dict[str, Any] = {
		"miejsce_urodzenia": "Warszawa",
		"rodzaj_dokumentu": "Dowód osobisty",
		"seria_numer_dokumentu": "ABC123456",
		"data_wydania_dokumentu": "2020-01-15",
		"data_waznosci_dokumentu": "2030-01-15",
		"adres_zameldowania_taki_sam": "Tak",
		"adres_zameldowania": "",
		"adres_korespondencji_taki_sam": "Tak",
		"adres_korespondencji": "",
		"wyksztalcenie": "wyższe",
		"stan_cywilny": "Kawaler/panna",
		"liczba_osob_na_utrzymaniu": "0",
		"kwota_800_plus": "0",
		"dochod_wspolmalzonka": "0",
		"zrodlo_dochodu_malzonka": "Emerytura",
		"oplaty_miesieczne": "500",
		"suma_zobowiazan": "0",
		"numer_rachunku": "PL61109010140000071219812874",
		"praca_wlaczone": 0,
		"praca_forma": "",
		"praca_data_zatrudnienia": "",
		"praca_okres": "",
		"praca_okres_od": "",
		"praca_okres_do": "",
		"praca_nip": "",
		"praca_nazwa_zakladu": "",
		"praca_adres_telefon": "",
		"praca_kwota_dochodu": "",
		"emerytura_wlaczone": 0,
		"emerytura_numer_swiadczenia": "",
		"emerytura_od_kiedy": "",
		"emerytura_kwota_dochodu": "",
		"renta_wlaczone": 0,
		"renta_numer_swiadczenia": "",
		"renta_od_kiedy": "",
		"renta_kwota_dochodu": "",
		"dzialalnosc_wlaczone": 0,
		"dzialalnosc_forma_opodatkowania": "",
		"dzialalnosc_forma_inna": "",
		"dzialalnosc_nip": "",
		"dzialalnosc_nazwa": "",
		"dzialalnosc_adres": "",
		"dzialalnosc_telefon": "",
		"dzialalnosc_od_kiedy": "",
		"dzialalnosc_kwota_dochodu": "",
		"gospodarstwo_wlaczone": 0,
		"gospodarstwo_nip": "",
		"gospodarstwo_od_kiedy": "",
		"gospodarstwo_kwota_dochodu": "",
		"inne_wlaczone": 0,
		"inne_1_typ": "",
		"inne_1_kwota": "",
		"inne_2_typ": "",
		"inne_2_kwota": "",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"custom_pesel": "90010112345",
		"first_name": "Jan",
		"last_name": "Kowalski",
		"mobile_no": "500600700",
		"email": "jan@example.com",
		"custom_kod_pocztowy": "00-001",
		"custom_miasto": "Warszawa",
		"custom_ulica": "Kwiatowa",
		"custom_nr_domu": "5",
		"custom_nr_mieszkania": "12",
	}
	baza.update(nadpisania)
	return baza


def _kontekst(**nadpisania_kredyt: Any) -> dict[str, Any]:
	"""Skrót: buduje kontekst z bazowych fixture'ów, z opcjonalnymi nadpisaniami `kredyt`."""
	return zbuduj_kontekst_kredytu(_kredyt(**nadpisania_kredyt), _kontakt(), _DZIS)


class TestKontraktKluczy(unittest.TestCase):
	def test_a_zestaw_kluczy_dokladnie_zgodny(self: "TestKontraktKluczy") -> None:
		self.assertEqual(set(_kontekst().keys()), _OCZEKIWANE_KLUCZE)

	def test_b_klucze_exportowane_zgadzaja_sie_z_oczekiwanymi(self: "TestKontraktKluczy") -> None:
		self.assertEqual(KLUCZE_KONTEKSTU, _OCZEKIWANE_KLUCZE)

	def test_c_wszystkie_wartosci_str_lub_bool_nigdy_none(self: "TestKontraktKluczy") -> None:
		kontekst = _kontekst()
		for klucz, wartosc in kontekst.items():
			with self.subTest(klucz=klucz):
				self.assertIsInstance(wartosc, (str, bool))
				self.assertIsNotNone(wartosc)

	def test_d_wartosci_str_lub_bool_takze_gdy_wszystkie_grupy_wlaczone(self: "TestKontraktKluczy") -> None:
		kontekst = _kontekst(
			praca_wlaczone=1,
			praca_forma="Umowa o pracę",
			praca_okres="Czas określony",
			praca_okres_od="2020-01-01",
			praca_okres_do="2026-01-01",
			emerytura_wlaczone=1,
			renta_wlaczone=1,
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="inne",
			gospodarstwo_wlaczone=1,
			inne_wlaczone=1,
			inne_1_typ="Alimenty",
			inne_1_kwota="1000",
		)
		for klucz, wartosc in kontekst.items():
			with self.subTest(klucz=klucz):
				self.assertIsInstance(wartosc, (str, bool))
				self.assertIsNotNone(wartosc)


class TestNieMutuje(unittest.TestCase):
	def test_a_kredyt_i_kontakt_nietkniete(self: "TestNieMutuje") -> None:
		kredyt = _kredyt(praca_wlaczone=1, praca_forma="Umowa o pracę")
		kontakt = _kontakt()
		kredyt_kopia = copy.deepcopy(kredyt)
		kontakt_kopia = copy.deepcopy(kontakt)

		zbuduj_kontekst_kredytu(kredyt, kontakt, _DZIS)

		self.assertEqual(kredyt, kredyt_kopia)
		self.assertEqual(kontakt, kontakt_kopia)


class TestKontaktBlok(unittest.TestCase):
	def test_a_pola_kontaktowe_przechodza_wprost(self: "TestKontaktBlok") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["pesel"], "90010112345")
		self.assertEqual(kontekst["imiona"], "Jan")
		self.assertEqual(kontekst["nazwisko"], "Kowalski")
		self.assertEqual(kontekst["telefon"], "500600700")
		self.assertEqual(kontekst["email"], "jan@example.com")
		self.assertEqual(kontekst["kod_pocztowy"], "00-001")
		self.assertEqual(kontekst["miejscowosc"], "Warszawa")
		self.assertEqual(kontekst["ulica"], "Kwiatowa")
		self.assertEqual(kontekst["nr_domu"], "5")
		self.assertEqual(kontekst["nr_lokalu"], "12")

	def test_b_brakujace_pola_kontaktu_dajapuste_stringi(self: "TestKontaktBlok") -> None:
		kontakt = _kontakt(custom_pesel=None, mobile_no=None, email=None)
		kontekst = zbuduj_kontekst_kredytu(_kredyt(), kontakt, _DZIS)
		self.assertEqual(kontekst["pesel"], "")
		self.assertEqual(kontekst["telefon"], "")
		self.assertEqual(kontekst["email"], "")


class TestFormatowanieKwoty(unittest.TestCase):
	def test_a_forma_kropkowa(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne="41236.5")
		self.assertEqual(kontekst["oplaty_miesieczne"], "41\xa0236,50")

	def test_b_forma_polska_ze_spacja_tysiecy(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne="41 236,50")
		self.assertEqual(kontekst["oplaty_miesieczne"], "41\xa0236,50")

	def test_c_forma_polska_z_nbsp_tysiecy(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne="41\xa0236,50")
		self.assertEqual(kontekst["oplaty_miesieczne"], "41\xa0236,50")

	def test_d_puste_daje_pusty_string(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne="")
		self.assertEqual(kontekst["oplaty_miesieczne"], "")

	def test_e_none_daje_pusty_string(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne=None)
		self.assertEqual(kontekst["oplaty_miesieczne"], "")

	def test_f_niesparsowalne_daje_pusty_string(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(oplaty_miesieczne="nie wiem ile")
		self.assertEqual(kontekst["oplaty_miesieczne"], "")

	def test_g_zero_jest_wypelnione_nie_puste(self: "TestFormatowanieKwoty") -> None:
		# W odróżnieniu od `volteo_umowa_pdf.py`: tu 0 zł jest realną,
		# poprawną odpowiedzią (np. brak dochodu współmałżonka), więc drukuje
		# się jako "0,00", nie jako pustka.
		kontekst = _kontekst(dochod_wspolmalzonka="0")
		self.assertEqual(kontekst["dochod_wspolmalzonka"], "0,00")

	def test_h_kwota_bez_grosza_dopelnia_zerami(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(suma_zobowiazan="1234")
		self.assertEqual(kontekst["suma_zobowiazan"], "1\xa0234,00")

	def test_i_miliony_dwie_grupy_separatora(self: "TestFormatowanieKwoty") -> None:
		kontekst = _kontekst(suma_zobowiazan="1234567,89")
		self.assertEqual(kontekst["suma_zobowiazan"], "1\xa0234\xa0567,89")


class TestGrupaWylaczonaZerujePola(unittest.TestCase):
	"""Wyłączony przełącznik grupy zeruje WSZYSTKIE jej klucze kontekstu, nawet
	jeśli surowe pola rekordu są nadal wypełnione (np. użytkownik odznaczył
	grupę po jej wypełnieniu) — i nie mutuje wejścia przy tym."""

	def test_a_praca_wylaczona_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kredyt = _kredyt(
			praca_wlaczone=0,
			praca_forma="Umowa o pracę",
			praca_data_zatrudnienia="2020-01-01",
			praca_okres="Czas określony",
			praca_okres_od="2020-01-01",
			praca_okres_do="2026-01-01",
			praca_nip="1234567890",
			praca_nazwa_zakladu="Firma Sp. z o.o.",
			praca_adres_telefon="Warszawa, 500600700",
			praca_kwota_dochodu="5000",
		)
		kredyt_kopia = copy.deepcopy(kredyt)
		kontekst = zbuduj_kontekst_kredytu(kredyt, _kontakt(), _DZIS)

		self.assertEqual(kontekst["praca_data_zatrudnienia"], "")
		self.assertEqual(kontekst["praca_okreslony_od"], "")
		self.assertEqual(kontekst["praca_okreslony_do"], "")
		self.assertEqual(kontekst["praca_nieokreslony_od"], "")
		self.assertEqual(kontekst["praca_nip"], "")
		self.assertEqual(kontekst["praca_nazwa_zakladu"], "")
		self.assertEqual(kontekst["praca_adres_telefon"], "")
		self.assertEqual(kontekst["praca_kwota_dochodu"], "")
		self.assertFalse(kontekst["praca_umowa_o_prace"])
		self.assertFalse(kontekst["praca_zlecenie"])
		self.assertFalse(kontekst["praca_dzielo"])
		self.assertEqual(kredyt, kredyt_kopia)

	def test_b_emerytura_wylaczona_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kontekst = _kontekst(
			emerytura_wlaczone=0,
			emerytura_numer_swiadczenia="ABC123",
			emerytura_od_kiedy="2020-01-01",
			emerytura_kwota_dochodu="3000",
		)
		self.assertEqual(kontekst["emerytura_numer_swiadczenia"], "")
		self.assertEqual(kontekst["emerytura_od_kiedy"], "")
		self.assertEqual(kontekst["emerytura_kwota_dochodu"], "")

	def test_c_renta_wylaczona_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kontekst = _kontekst(
			renta_wlaczone=0,
			renta_numer_swiadczenia="XYZ987",
			renta_od_kiedy="2021-05-05",
			renta_kwota_dochodu="2000",
		)
		self.assertEqual(kontekst["renta_numer_swiadczenia"], "")
		self.assertEqual(kontekst["renta_od_kiedy"], "")
		self.assertEqual(kontekst["renta_kwota_dochodu"], "")

	def test_d_gospodarstwo_wylaczone_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kontekst = _kontekst(
			gospodarstwo_wlaczone=0,
			gospodarstwo_nip="9998887776",
			gospodarstwo_od_kiedy="2019-03-03",
			gospodarstwo_kwota_dochodu="1500",
		)
		self.assertEqual(kontekst["gospodarstwo_nip"], "")
		self.assertEqual(kontekst["gospodarstwo_od_kiedy"], "")
		self.assertEqual(kontekst["gospodarstwo_kwota_dochodu"], "")

	def test_e_dzialalnosc_wylaczona_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=0,
			dzialalnosc_forma_opodatkowania="inne",
			dzialalnosc_forma_inna="Karta podatkowa",
			dzialalnosc_nip="1112223334",
			dzialalnosc_nazwa="Firma Jan Kowalski",
			dzialalnosc_adres="Warszawa",
			dzialalnosc_telefon="500600700",
			dzialalnosc_od_kiedy="2018-01-01",
			dzialalnosc_kwota_dochodu="7000",
		)
		self.assertFalse(kontekst["dzialalnosc_ryczalt"])
		self.assertFalse(kontekst["dzialalnosc_kpir"])
		self.assertFalse(kontekst["dzialalnosc_inne"])
		self.assertEqual(kontekst["dzialalnosc_forma_inna"], "")
		self.assertEqual(kontekst["dzialalnosc_nip"], "")
		self.assertEqual(kontekst["dzialalnosc_nazwa"], "")
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "")
		self.assertEqual(kontekst["dzialalnosc_od_kiedy"], "")
		self.assertEqual(kontekst["dzialalnosc_kwota_dochodu"], "")

	def test_f_inne_wylaczone_mimo_wypelnionych_pol(self: "TestGrupaWylaczonaZerujePola") -> None:
		kontekst = _kontekst(
			inne_wlaczone=0,
			inne_1_typ="Alimenty",
			inne_1_kwota="1000",
			inne_2_typ="Wynajem",
			inne_2_kwota="2000",
		)
		self.assertEqual(kontekst["inne_1_typ"], "")
		self.assertEqual(kontekst["inne_1_kwota"], "")
		self.assertEqual(kontekst["inne_2_typ"], "")
		self.assertEqual(kontekst["inne_2_kwota"], "")


class TestPracaOkresRouting(unittest.TestCase):
	def test_a_czas_okreslony(self: "TestPracaOkresRouting") -> None:
		kontekst = _kontekst(
			praca_wlaczone=1,
			praca_okres="Czas określony",
			praca_okres_od="2020-01-15",
			praca_okres_do="2026-01-15",
		)
		self.assertEqual(kontekst["praca_okreslony_od"], "15.01.2020")
		self.assertEqual(kontekst["praca_okreslony_do"], "15.01.2026")
		self.assertEqual(kontekst["praca_nieokreslony_od"], "")

	def test_b_czas_nieokreslony(self: "TestPracaOkresRouting") -> None:
		kontekst = _kontekst(
			praca_wlaczone=1,
			praca_okres="Czas nieokreślony",
			praca_okres_od="2020-01-15",
			praca_okres_do="2026-01-15",
		)
		self.assertEqual(kontekst["praca_nieokreslony_od"], "15.01.2020")
		self.assertEqual(kontekst["praca_okreslony_od"], "")
		self.assertEqual(kontekst["praca_okreslony_do"], "")

	def test_c_okres_nieznany_wszystkie_puste(self: "TestPracaOkresRouting") -> None:
		kontekst = _kontekst(
			praca_wlaczone=1,
			praca_okres="Coś innego",
			praca_okres_od="2020-01-15",
			praca_okres_do="2026-01-15",
		)
		self.assertEqual(kontekst["praca_okreslony_od"], "")
		self.assertEqual(kontekst["praca_okreslony_do"], "")
		self.assertEqual(kontekst["praca_nieokreslony_od"], "")


class TestPracaFormaKratki(unittest.TestCase):
	def test_a_umowa_o_prace(self: "TestPracaFormaKratki") -> None:
		kontekst = _kontekst(praca_wlaczone=1, praca_forma="Umowa o pracę")
		self.assertTrue(kontekst["praca_umowa_o_prace"])
		self.assertFalse(kontekst["praca_zlecenie"])
		self.assertFalse(kontekst["praca_dzielo"])

	def test_b_umowa_zlecenie(self: "TestPracaFormaKratki") -> None:
		kontekst = _kontekst(praca_wlaczone=1, praca_forma="Umowa zlecenie")
		self.assertFalse(kontekst["praca_umowa_o_prace"])
		self.assertTrue(kontekst["praca_zlecenie"])
		self.assertFalse(kontekst["praca_dzielo"])

	def test_c_umowa_o_dzielo(self: "TestPracaFormaKratki") -> None:
		kontekst = _kontekst(praca_wlaczone=1, praca_forma="Umowa o dzieło")
		self.assertFalse(kontekst["praca_umowa_o_prace"])
		self.assertFalse(kontekst["praca_zlecenie"])
		self.assertTrue(kontekst["praca_dzielo"])

	def test_d_forma_nieznana_wszystkie_false(self: "TestPracaFormaKratki") -> None:
		kontekst = _kontekst(praca_wlaczone=1, praca_forma="Coś innego")
		self.assertFalse(kontekst["praca_umowa_o_prace"])
		self.assertFalse(kontekst["praca_zlecenie"])
		self.assertFalse(kontekst["praca_dzielo"])


class TestDzialalnoscFormaKratki(unittest.TestCase):
	def test_a_ryczalt(self: "TestDzialalnoscFormaKratki") -> None:
		kontekst = _kontekst(dzialalnosc_wlaczone=1, dzialalnosc_forma_opodatkowania="ryczałt")
		self.assertTrue(kontekst["dzialalnosc_ryczalt"])
		self.assertFalse(kontekst["dzialalnosc_kpir"])
		self.assertFalse(kontekst["dzialalnosc_inne"])
		self.assertEqual(kontekst["dzialalnosc_forma_inna"], "")

	def test_b_kpir(self: "TestDzialalnoscFormaKratki") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1, dzialalnosc_forma_opodatkowania="księga przychodów i rozchodów (KPiR)"
		)
		self.assertFalse(kontekst["dzialalnosc_ryczalt"])
		self.assertTrue(kontekst["dzialalnosc_kpir"])
		self.assertFalse(kontekst["dzialalnosc_inne"])

	def test_c_inne_z_opisem(self: "TestDzialalnoscFormaKratki") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="inne",
			dzialalnosc_forma_inna="Karta podatkowa",
		)
		self.assertFalse(kontekst["dzialalnosc_ryczalt"])
		self.assertFalse(kontekst["dzialalnosc_kpir"])
		self.assertTrue(kontekst["dzialalnosc_inne"])
		self.assertEqual(kontekst["dzialalnosc_forma_inna"], "Karta podatkowa")

	def test_d_forma_inna_pomijana_gdy_forma_nie_jest_inne(self: "TestDzialalnoscFormaKratki") -> None:
		# Nawet gdyby `dzialalnosc_forma_inna` zawierał resztkowe dane po
		# wcześniejszej zmianie odpowiedzi, ma nie trafić na wydruk.
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="ryczałt",
			dzialalnosc_forma_inna="Resztka po zmianie odpowiedzi",
		)
		self.assertEqual(kontekst["dzialalnosc_forma_inna"], "")

	def test_e_wielka_litera_inne_nie_pasuje(self: "TestDzialalnoscFormaKratki") -> None:
		# Transkrypcja PDF-u jest małą literą ("inne") — "Inne" (wielką) NIE
		# jest tą samą wartością, porównanie jest case-sensitive.
		kontekst = _kontekst(dzialalnosc_wlaczone=1, dzialalnosc_forma_opodatkowania="Inne")
		self.assertFalse(kontekst["dzialalnosc_inne"])


class TestAdresyKratkiIPassthrough(unittest.TestCase):
	def test_a_taki_sam_tak_adres_pusty(self: "TestAdresyKratkiIPassthrough") -> None:
		kontekst = _kontekst(
			adres_zameldowania_taki_sam="Tak",
			adres_zameldowania="ul. Resztkowa 1, Gdańsk",
		)
		self.assertTrue(kontekst["adres_zameldowania_tak"])
		self.assertFalse(kontekst["adres_zameldowania_nie"])
		self.assertEqual(kontekst["adres_zameldowania"], "")

	def test_b_taki_sam_nie_adres_przechodzi(self: "TestAdresyKratkiIPassthrough") -> None:
		kontekst = _kontekst(
			adres_zameldowania_taki_sam="Nie",
			adres_zameldowania="ul. Polna 10, Kraków",
		)
		self.assertFalse(kontekst["adres_zameldowania_tak"])
		self.assertTrue(kontekst["adres_zameldowania_nie"])
		self.assertEqual(kontekst["adres_zameldowania"], "ul. Polna 10, Kraków")

	def test_c_korespondencji_analogicznie(self: "TestAdresyKratkiIPassthrough") -> None:
		kontekst = _kontekst(
			adres_korespondencji_taki_sam="Nie",
			adres_korespondencji="ul. Inna 3, Poznań",
		)
		self.assertFalse(kontekst["adres_korespondencji_tak"])
		self.assertTrue(kontekst["adres_korespondencji_nie"])
		self.assertEqual(kontekst["adres_korespondencji"], "ul. Inna 3, Poznań")

	def test_d_nieznana_wartosc_oba_puste(self: "TestAdresyKratkiIPassthrough") -> None:
		kontekst = _kontekst(adres_zameldowania_taki_sam=None)
		self.assertFalse(kontekst["adres_zameldowania_tak"])
		self.assertFalse(kontekst["adres_zameldowania_nie"])
		self.assertEqual(kontekst["adres_zameldowania"], "")


class TestWyksztalcenieKratki(unittest.TestCase):
	def test_a_wyzsze(self: "TestWyksztalcenieKratki") -> None:
		kontekst = _kontekst(wyksztalcenie="wyższe")
		self.assertTrue(kontekst["wyksztalcenie_wyzsze"])
		self.assertFalse(kontekst["wyksztalcenie_srednie"])
		self.assertFalse(kontekst["wyksztalcenie_zawodowe"])
		self.assertFalse(kontekst["wyksztalcenie_podstawowe"])

	def test_b_srednie(self: "TestWyksztalcenieKratki") -> None:
		kontekst = _kontekst(wyksztalcenie="średnie")
		self.assertTrue(kontekst["wyksztalcenie_srednie"])
		self.assertEqual(
			sum(
				kontekst[k]
				for k in (
					"wyksztalcenie_wyzsze",
					"wyksztalcenie_srednie",
					"wyksztalcenie_zawodowe",
					"wyksztalcenie_podstawowe",
				)
			),
			1,
		)

	def test_c_zawodowe(self: "TestWyksztalcenieKratki") -> None:
		kontekst = _kontekst(wyksztalcenie="zawodowe")
		self.assertTrue(kontekst["wyksztalcenie_zawodowe"])

	def test_d_podstawowe_gimnazjalne(self: "TestWyksztalcenieKratki") -> None:
		kontekst = _kontekst(wyksztalcenie="podstawowe/gimnazjalne")
		self.assertTrue(kontekst["wyksztalcenie_podstawowe"])

	def test_e_nieznane_wszystkie_false(self: "TestWyksztalcenieKratki") -> None:
		kontekst = _kontekst(wyksztalcenie=None)
		self.assertFalse(kontekst["wyksztalcenie_wyzsze"])
		self.assertFalse(kontekst["wyksztalcenie_srednie"])
		self.assertFalse(kontekst["wyksztalcenie_zawodowe"])
		self.assertFalse(kontekst["wyksztalcenie_podstawowe"])


class TestStanCywilnyKratki(unittest.TestCase):
	def test_a_kawaler_panna(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Kawaler/panna")
		self.assertTrue(kontekst["stan_kawaler_panna"])
		for inny in (
			"stan_rozwiedziony",
			"stan_malzenstwo_rozdzielnosc",
			"stan_malzenstwo_wspolnota",
			"stan_wdowiec_wdowa",
			"stan_separacja",
		):
			self.assertFalse(kontekst[inny])

	def test_b_rozwiedziony(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Rozwiedziony/a")
		self.assertTrue(kontekst["stan_rozwiedziony"])

	def test_c_malzenstwo_rozdzielnosc(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Małżeństwo - rozdzielność majątkowa")
		self.assertTrue(kontekst["stan_malzenstwo_rozdzielnosc"])

	def test_d_malzenstwo_wspolnota(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Małżeństwo - wspólnota majątkowa")
		self.assertTrue(kontekst["stan_malzenstwo_wspolnota"])

	def test_e_wdowiec_wdowa(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Wdowiec/wdowa")
		self.assertTrue(kontekst["stan_wdowiec_wdowa"])

	def test_f_separacja(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Separacja")
		self.assertTrue(kontekst["stan_separacja"])

	def test_g_dokladnie_jedna_prawdziwa_gdy_ustawione(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="Separacja")
		klucze = (
			"stan_kawaler_panna",
			"stan_rozwiedziony",
			"stan_malzenstwo_rozdzielnosc",
			"stan_malzenstwo_wspolnota",
			"stan_wdowiec_wdowa",
			"stan_separacja",
		)
		self.assertEqual(sum(1 for k in klucze if kontekst[k]), 1)

	def test_h_nieznane_wszystkie_false(self: "TestStanCywilnyKratki") -> None:
		kontekst = _kontekst(stan_cywilny="")
		for k in (
			"stan_kawaler_panna",
			"stan_rozwiedziony",
			"stan_malzenstwo_rozdzielnosc",
			"stan_malzenstwo_wspolnota",
			"stan_wdowiec_wdowa",
			"stan_separacja",
		):
			self.assertFalse(kontekst[k])

	def test_i_stare_wartosci_sprzed_2026_08_15_juz_nie_pasuja(self: "TestStanCywilnyKratki") -> None:
		# Owner override 2026-08-15: dawne stored value'y ("kawaler/panna" małą
		# literą, "W związku małżeńskim ..." zamiast "Małżeństwo - ...") nie
		# powinny już trafiać w żadną kratkę — inaczej cichy regres wsteczny
		# odczytałby stary rekord jako "stan cywilny nieznany", nie jako błąd.
		klucze = (
			"stan_kawaler_panna",
			"stan_rozwiedziony",
			"stan_malzenstwo_rozdzielnosc",
			"stan_malzenstwo_wspolnota",
			"stan_wdowiec_wdowa",
			"stan_separacja",
		)
		for stara_wartosc in (
			"kawaler/panna",
			"W związku małżeńskim rozdzielność majątkowa",
			"W związku małżeńskim wspólnota majątkowa",
		):
			with self.subTest(stara_wartosc=stara_wartosc):
				kontekst = _kontekst(stan_cywilny=stara_wartosc)
				for k in klucze:
					self.assertFalse(kontekst[k])


class TestDaty(unittest.TestCase):
	def test_a_data_iso_string(self: "TestDaty") -> None:
		kontekst = _kontekst(data_wydania_dokumentu="2020-01-15")
		self.assertEqual(kontekst["data_wydania_dokumentu"], "15.01.2020")

	def test_b_data_puste(self: "TestDaty") -> None:
		kontekst = _kontekst(data_wydania_dokumentu="")
		self.assertEqual(kontekst["data_wydania_dokumentu"], "")

	def test_c_data_none(self: "TestDaty") -> None:
		kontekst = _kontekst(data_wydania_dokumentu=None)
		self.assertEqual(kontekst["data_wydania_dokumentu"], "")

	def test_d_data_niesparsowalna(self: "TestDaty") -> None:
		kontekst = _kontekst(data_wydania_dokumentu="nie wiem kiedy")
		self.assertEqual(kontekst["data_wydania_dokumentu"], "")

	def test_e_data_jako_obiekt_date(self: "TestDaty") -> None:
		kontekst = _kontekst(data_wydania_dokumentu=date(2020, 1, 15))
		self.assertEqual(kontekst["data_wydania_dokumentu"], "15.01.2020")


class TestPodpis(unittest.TestCase):
	def test_a_data_i_imie_nazwisko(self: "TestPodpis") -> None:
		kontekst = _kontekst()
		self.assertEqual(kontekst["podpis_data"], "15.08.2026")
		self.assertEqual(kontekst["podpis_imie_nazwisko"], "Jan Kowalski")

	def test_b_brak_imienia_bez_podwojnej_spacji(self: "TestPodpis") -> None:
		kontakt = _kontakt(first_name="", last_name="Kowalski")
		kontekst = zbuduj_kontekst_kredytu(_kredyt(), kontakt, _DZIS)
		self.assertEqual(kontekst["podpis_imie_nazwisko"], "Kowalski")

	def test_c_brak_obu_pusty_string(self: "TestPodpis") -> None:
		kontakt = _kontakt(first_name="", last_name="")
		kontekst = zbuduj_kontekst_kredytu(_kredyt(), kontakt, _DZIS)
		self.assertEqual(kontekst["podpis_imie_nazwisko"], "")


class TestBrakujacePolaBazowe(unittest.TestCase):
	def test_a_pusty_rekord_daje_liste_bazowa(self: "TestBrakujacePolaBazowe") -> None:
		wynik = brakujace_pola({})
		self.assertEqual(
			wynik,
			[
				"miejsce_urodzenia",
				"rodzaj_dokumentu",
				"seria_numer_dokumentu",
				"data_wydania_dokumentu",
				"data_waznosci_dokumentu",
				"adres_zameldowania_taki_sam",
				"adres_korespondencji_taki_sam",
				"wyksztalcenie",
				"stan_cywilny",
				"liczba_osob_na_utrzymaniu",
				"kwota_800_plus",
				"dochod_wspolmalzonka",
				"zrodlo_dochodu_malzonka",
				"oplaty_miesieczne",
				"suma_zobowiazan",
			],
		)

	def test_b_kompletny_rekord_bez_grup_dochodu_nic_nie_brakuje(self: "TestBrakujacePolaBazowe") -> None:
		self.assertEqual(brakujace_pola(_kredyt()), [])

	def test_c_zero_amount_licza_sie_jako_wypelnione(self: "TestBrakujacePolaBazowe") -> None:
		dane = _kredyt(kwota_800_plus="0", dochod_wspolmalzonka="0", suma_zobowiazan="0")
		self.assertNotIn("kwota_800_plus", brakujace_pola(dane))
		self.assertNotIn("dochod_wspolmalzonka", brakujace_pola(dane))
		self.assertNotIn("suma_zobowiazan", brakujace_pola(dane))

	def test_d_bialy_znak_jest_brakujacy(self: "TestBrakujacePolaBazowe") -> None:
		dane = _kredyt(miejsce_urodzenia="   ")
		self.assertIn("miejsce_urodzenia", brakujace_pola(dane))

	def test_e_nie_mutuje_wejscia(self: "TestBrakujacePolaBazowe") -> None:
		dane = _kredyt()
		kopia = copy.deepcopy(dane)
		brakujace_pola(dane)
		self.assertEqual(dane, kopia)

	def test_f_numer_rachunku_pusty_nie_jest_brakujacy(self: "TestBrakujacePolaBazowe") -> None:
		dane = _kredyt(numer_rachunku="")
		self.assertNotIn("numer_rachunku", brakujace_pola(dane))


class TestBrakujacePolaWarunkoweAdresy(unittest.TestCase):
	def test_a_adres_zameldowania_wymagany_gdy_nie(self: "TestBrakujacePolaWarunkoweAdresy") -> None:
		dane = _kredyt(adres_zameldowania_taki_sam="Nie", adres_zameldowania="")
		self.assertIn("adres_zameldowania", brakujace_pola(dane))

	def test_b_adres_zameldowania_niewymagany_gdy_tak(self: "TestBrakujacePolaWarunkoweAdresy") -> None:
		dane = _kredyt(adres_zameldowania_taki_sam="Tak", adres_zameldowania="")
		self.assertNotIn("adres_zameldowania", brakujace_pola(dane))

	def test_c_adres_zameldowania_wypelniony_wystarcza(self: "TestBrakujacePolaWarunkoweAdresy") -> None:
		dane = _kredyt(adres_zameldowania_taki_sam="Nie", adres_zameldowania="ul. Polna 10")
		self.assertNotIn("adres_zameldowania", brakujace_pola(dane))

	def test_d_adres_korespondencji_analogicznie(self: "TestBrakujacePolaWarunkoweAdresy") -> None:
		dane = _kredyt(adres_korespondencji_taki_sam="Nie", adres_korespondencji="")
		self.assertIn("adres_korespondencji", brakujace_pola(dane))
		dane2 = _kredyt(adres_korespondencji_taki_sam="Nie", adres_korespondencji="ul. Inna 3")
		self.assertNotIn("adres_korespondencji", brakujace_pola(dane2))


class TestBrakujacePolaGrupyDochodu(unittest.TestCase):
	def test_a_zero_grup_wlaczonych_kompletne(self: "TestBrakujacePolaGrupyDochodu") -> None:
		self.assertEqual(brakujace_pola(_kredyt()), [])

	def test_b_praca_wlaczona_dodaje_jej_pola(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(praca_wlaczone=1)
		wynik = brakujace_pola(dane)
		for pole in ("praca_forma", "praca_data_zatrudnienia", "praca_okres", "praca_okres_od"):
			self.assertIn(pole, wynik)
		# praca_okres_do NIE jest wymagane, bo praca_okres nie jest "Czas określony".
		self.assertNotIn("praca_okres_do", wynik)

	def test_c_praca_okres_do_wymagany_tylko_dla_czas_okreslony(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane_okreslony = _kredyt(
			praca_wlaczone=1,
			praca_forma="Umowa o pracę",
			praca_data_zatrudnienia="2020-01-01",
			praca_okres="Czas określony",
			praca_okres_od="2020-01-01",
			praca_nip="123",
			praca_nazwa_zakladu="Firma",
			praca_adres_telefon="tel",
			praca_kwota_dochodu="5000",
		)
		self.assertIn("praca_okres_do", brakujace_pola(dane_okreslony))

		dane_nieokreslony = dict(dane_okreslony)
		dane_nieokreslony["praca_okres"] = "Czas nieokreślony"
		self.assertNotIn("praca_okres_do", brakujace_pola(dane_nieokreslony))

	def test_d_praca_okres_od_zawsze_wymagany_gdy_praca_wlaczona(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(praca_wlaczone=1, praca_okres="Czas nieokreślony", praca_okres_od="")
		self.assertIn("praca_okres_od", brakujace_pola(dane))

	def test_e_emerytura_wlaczona_dodaje_jej_pola(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(emerytura_wlaczone=1)
		wynik = brakujace_pola(dane)
		self.assertIn("emerytura_numer_swiadczenia", wynik)
		self.assertIn("emerytura_od_kiedy", wynik)
		self.assertIn("emerytura_kwota_dochodu", wynik)

	def test_f_renta_wlaczona_dodaje_jej_pola(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(renta_wlaczone=1)
		wynik = brakujace_pola(dane)
		self.assertIn("renta_numer_swiadczenia", wynik)
		self.assertIn("renta_od_kiedy", wynik)
		self.assertIn("renta_kwota_dochodu", wynik)

	def test_g_gospodarstwo_wlaczone_dodaje_jego_pola(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(gospodarstwo_wlaczone=1)
		wynik = brakujace_pola(dane)
		self.assertIn("gospodarstwo_nip", wynik)
		self.assertIn("gospodarstwo_od_kiedy", wynik)
		self.assertIn("gospodarstwo_kwota_dochodu", wynik)

	def test_h_dzialalnosc_wlaczona_bez_formy_inna_nie_wymaga_opisu(
		self: "TestBrakujacePolaGrupyDochodu",
	) -> None:
		dane = _kredyt(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="ryczałt",
			dzialalnosc_nip="123",
			dzialalnosc_nazwa="Firma",
			dzialalnosc_adres="adres",
			dzialalnosc_telefon="tel",
			dzialalnosc_od_kiedy="2020-01-01",
			dzialalnosc_kwota_dochodu="5000",
		)
		self.assertEqual(brakujace_pola(dane), [])

	def test_i_dzialalnosc_forma_inne_wymaga_opisu(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="inne",
			dzialalnosc_forma_inna="",
			dzialalnosc_nip="123",
			dzialalnosc_nazwa="Firma",
			dzialalnosc_adres="adres",
			dzialalnosc_telefon="tel",
			dzialalnosc_od_kiedy="2020-01-01",
			dzialalnosc_kwota_dochodu="5000",
		)
		self.assertIn("dzialalnosc_forma_inna", brakujace_pola(dane))

	def test_j_inne_druga_para_opcjonalna(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(inne_wlaczone=1, inne_1_typ="Alimenty", inne_1_kwota="1000")
		self.assertEqual(brakujace_pola(dane), [])

	def test_k_inne_pierwsza_para_wymagana(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(inne_wlaczone=1, inne_1_typ="", inne_1_kwota="")
		wynik = brakujace_pola(dane)
		self.assertIn("inne_1_typ", wynik)
		self.assertIn("inne_1_kwota", wynik)
		self.assertNotIn("inne_2_typ", wynik)
		self.assertNotIn("inne_2_kwota", wynik)

	def test_l_wiele_grup_naraz(self: "TestBrakujacePolaGrupyDochodu") -> None:
		dane = _kredyt(praca_wlaczone=1, gospodarstwo_wlaczone=1)
		wynik = brakujace_pola(dane)
		self.assertIn("praca_forma", wynik)
		self.assertIn("gospodarstwo_nip", wynik)
		self.assertNotIn("emerytura_numer_swiadczenia", wynik)
		self.assertNotIn("renta_numer_swiadczenia", wynik)


class TestJoinRodzajSeriaNumerDokumentu(unittest.TestCase):
	"""`rodzaj_seria_numer_dokumentu` (klucz kontekstu PDF-u, niezmieniony) jest od
	2026-08-15 składany z dwóch osobnych pól rekordu — `rodzaj_dokumentu` i
	`seria_numer_dokumentu` — spacją, przez `_polacz`."""

	def test_a_oba_obecne_laczy_spacja(self: "TestJoinRodzajSeriaNumerDokumentu") -> None:
		kontekst = _kontekst(rodzaj_dokumentu="Dowód osobisty", seria_numer_dokumentu="ABC123456")
		self.assertEqual(kontekst["rodzaj_seria_numer_dokumentu"], "Dowód osobisty ABC123456")

	def test_b_tylko_rodzaj_obecny(self: "TestJoinRodzajSeriaNumerDokumentu") -> None:
		kontekst = _kontekst(rodzaj_dokumentu="Paszport", seria_numer_dokumentu="")
		self.assertEqual(kontekst["rodzaj_seria_numer_dokumentu"], "Paszport")

	def test_c_tylko_seria_numer_obecny(self: "TestJoinRodzajSeriaNumerDokumentu") -> None:
		kontekst = _kontekst(rodzaj_dokumentu="", seria_numer_dokumentu="XYZ999888")
		self.assertEqual(kontekst["rodzaj_seria_numer_dokumentu"], "XYZ999888")

	def test_d_oba_puste_daje_pusty_string(self: "TestJoinRodzajSeriaNumerDokumentu") -> None:
		kontekst = _kontekst(rodzaj_dokumentu="", seria_numer_dokumentu="")
		self.assertEqual(kontekst["rodzaj_seria_numer_dokumentu"], "")

	def test_e_oba_none_daje_pusty_string(self: "TestJoinRodzajSeriaNumerDokumentu") -> None:
		kontekst = _kontekst(rodzaj_dokumentu=None, seria_numer_dokumentu=None)
		self.assertEqual(kontekst["rodzaj_seria_numer_dokumentu"], "")


class TestJoinDzialalnoscAdresTelefon(unittest.TestCase):
	"""`dzialalnosc_adres_telefon` (klucz kontekstu PDF-u, niezmieniony) jest od
	2026-08-15 składany z dwóch osobnych pól rekordu — `dzialalnosc_adres` i
	`dzialalnosc_telefon` — w formacie `"<adres>, tel. <telefon>"`, przez
	`_polacz_adres_telefon`. Wciąż bramkowany `dzialalnosc_wlaczone` jak
	dotychczas."""

	def test_a_oba_obecne_format_z_etykieta_tel(self: "TestJoinDzialalnoscAdresTelefon") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1,
			dzialalnosc_adres="ul. Firmowa 1, Warszawa",
			dzialalnosc_telefon="500600700",
		)
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "ul. Firmowa 1, Warszawa, tel. 500600700")

	def test_b_tylko_adres_obecny_bez_etykiety(self: "TestJoinDzialalnoscAdresTelefon") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1,
			dzialalnosc_adres="ul. Firmowa 1, Warszawa",
			dzialalnosc_telefon="",
		)
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "ul. Firmowa 1, Warszawa")

	def test_c_tylko_telefon_obecny_bez_etykiety(self: "TestJoinDzialalnoscAdresTelefon") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=1,
			dzialalnosc_adres="",
			dzialalnosc_telefon="500600700",
		)
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "500600700")

	def test_d_oba_puste_daje_pusty_string(self: "TestJoinDzialalnoscAdresTelefon") -> None:
		kontekst = _kontekst(dzialalnosc_wlaczone=1, dzialalnosc_adres="", dzialalnosc_telefon="")
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "")

	def test_e_grupa_wylaczona_zeruje_mimo_wypelnionych_pol(self: "TestJoinDzialalnoscAdresTelefon") -> None:
		kontekst = _kontekst(
			dzialalnosc_wlaczone=0,
			dzialalnosc_adres="ul. Firmowa 1, Warszawa",
			dzialalnosc_telefon="500600700",
		)
		self.assertEqual(kontekst["dzialalnosc_adres_telefon"], "")


class TestBrakujacePolaNoweNazwyPol(unittest.TestCase):
	"""`brakujace_pola` po rozbiciu pól dokumentu i adresu firmy (feedback
	właściciela 2026-08-15) — cztery nowe nazwy pól w miejsce dwóch starych."""

	def test_a_rodzaj_dokumentu_i_seria_numer_puste_sa_brakujace(
		self: "TestBrakujacePolaNoweNazwyPol",
	) -> None:
		dane = _kredyt(rodzaj_dokumentu="", seria_numer_dokumentu="")
		wynik = brakujace_pola(dane)
		self.assertIn("rodzaj_dokumentu", wynik)
		self.assertIn("seria_numer_dokumentu", wynik)

	def test_b_rodzaj_dokumentu_i_seria_numer_wypelnione_wystarcza(
		self: "TestBrakujacePolaNoweNazwyPol",
	) -> None:
		dane = _kredyt(rodzaj_dokumentu="Dowód osobisty", seria_numer_dokumentu="ABC123456")
		wynik = brakujace_pola(dane)
		self.assertNotIn("rodzaj_dokumentu", wynik)
		self.assertNotIn("seria_numer_dokumentu", wynik)

	def test_c_jedno_z_pary_puste_nadal_brakujace(self: "TestBrakujacePolaNoweNazwyPol") -> None:
		dane = _kredyt(rodzaj_dokumentu="Dowód osobisty", seria_numer_dokumentu="")
		wynik = brakujace_pola(dane)
		self.assertNotIn("rodzaj_dokumentu", wynik)
		self.assertIn("seria_numer_dokumentu", wynik)

	def test_d_dzialalnosc_adres_i_telefon_wymagane_gdy_grupa_wlaczona(
		self: "TestBrakujacePolaNoweNazwyPol",
	) -> None:
		dane = _kredyt(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="ryczałt",
			dzialalnosc_nip="123",
			dzialalnosc_nazwa="Firma",
			dzialalnosc_adres="",
			dzialalnosc_telefon="",
			dzialalnosc_od_kiedy="2020-01-01",
			dzialalnosc_kwota_dochodu="5000",
		)
		wynik = brakujace_pola(dane)
		self.assertIn("dzialalnosc_adres", wynik)
		self.assertIn("dzialalnosc_telefon", wynik)

	def test_e_dzialalnosc_adres_i_telefon_wypelnione_wystarcza(
		self: "TestBrakujacePolaNoweNazwyPol",
	) -> None:
		dane = _kredyt(
			dzialalnosc_wlaczone=1,
			dzialalnosc_forma_opodatkowania="ryczałt",
			dzialalnosc_nip="123",
			dzialalnosc_nazwa="Firma",
			dzialalnosc_adres="ul. Firmowa 1",
			dzialalnosc_telefon="500600700",
			dzialalnosc_od_kiedy="2020-01-01",
			dzialalnosc_kwota_dochodu="5000",
		)
		self.assertEqual(brakujace_pola(dane), [])

	def test_f_dzialalnosc_wylaczona_nie_wymaga_adresu_ani_telefonu(
		self: "TestBrakujacePolaNoweNazwyPol",
	) -> None:
		dane = _kredyt(dzialalnosc_wlaczone=0, dzialalnosc_adres="", dzialalnosc_telefon="")
		wynik = brakujace_pola(dane)
		self.assertNotIn("dzialalnosc_adres", wynik)
		self.assertNotIn("dzialalnosc_telefon", wynik)


class TestKwotaPoprawna(unittest.TestCase):
	def test_a_forma_kropkowa(self: "TestKwotaPoprawna") -> None:
		self.assertTrue(kwota_poprawna("1234.56"))

	def test_b_forma_przecinkowa(self: "TestKwotaPoprawna") -> None:
		self.assertTrue(kwota_poprawna("1234,56"))

	def test_c_forma_przecinkowa_z_tysiacami_spacja(self: "TestKwotaPoprawna") -> None:
		self.assertTrue(kwota_poprawna("1 234,56"))

	def test_d_forma_przecinkowa_z_tysiacami_nbsp(self: "TestKwotaPoprawna") -> None:
		self.assertTrue(kwota_poprawna("1\xa0234,56"))

	def test_e_liczba_calkowita(self: "TestKwotaPoprawna") -> None:
		self.assertTrue(kwota_poprawna("0"))

	def test_f_puste_nie_jest_poprawne(self: "TestKwotaPoprawna") -> None:
		self.assertFalse(kwota_poprawna(""))
		self.assertFalse(kwota_poprawna("   "))

	def test_g_none_nie_jest_poprawne(self: "TestKwotaPoprawna") -> None:
		self.assertFalse(kwota_poprawna(None))

	def test_h_tekst_nie_jest_poprawny(self: "TestKwotaPoprawna") -> None:
		self.assertFalse(kwota_poprawna("nie wiem ile"))

	def test_i_nie_rzuca_na_dowolnym_smieciu(self: "TestKwotaPoprawna") -> None:
		for smiec in ("12,34,56", "--12", "12..34", "abc,def"):
			with self.subTest(smiec=smiec):
				self.assertFalse(kwota_poprawna(smiec))


if __name__ == "__main__":
	unittest.main()
