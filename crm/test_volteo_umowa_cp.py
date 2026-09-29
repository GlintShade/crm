# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy `crm/volteo_umowa_cp.py` (reguły: wariant wynagrodzenia, walidacja,
tajemnica prowizji) i `crm/volteo_umowa_pdf_cp.py` (budowniczy kontekstu PDF-u
umowy obsługi dotacji CP) — `unittest`, NIE pytest (nie istnieje dla Pythona
3.14 użytego lokalnie do tych testów)."""

import unittest
from datetime import date
from decimal import Decimal
from typing import Any

from crm.volteo_umowa_cp import (
	ETYKIETY_POL_CP,
	WARIANTY_WYNAGRODZENIA,
	brakujace_dane_klienta,
	brakujace_pola_cp,
	kwoty_wariantu_cp,
	warianty_wynagrodzenia_cp,
)
from crm.volteo_umowa_pdf_cp import klient_do_wyswietlenia, zbuduj_kontekst_cp

_DZIS = date(2026, 9, 29)

_OCZEKIWANE_KLUCZE_KONTEKSTU: frozenset[str] = frozenset(
	{
		"umowa_nr",
		"data_zawarcia",
		"klient_imie_nazwisko",
		"klient_adres",
		"klient_pesel",
		"klient_telefon",
		"klient_email",
		"wynagrodzenie_netto",
		"wynagrodzenie_brutto",
		"zgoda_przetwarzanie_danych",
		"zgoda_telefon",
		"zgoda_promocja",
		"podpis_zamawiajacy",
		"podpis_wykonawca",
		"data_i_podpis_zamawiajacy",
	}
)


def _stale(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"umowa1_netto": "1600",
		"umowa1_brutto": "1968",
		"umowa2_netto": "2400",
		"umowa2_brutto": "2952",
		# Prowizja jaskrawo odróżnialna od wszystkich pozostałych wartości w tym
		# pliku (żaden inny test nie używa "777"/"888") — TestTajemnicaProwizji
		# niżej sprawdza jej nieobecność w wyniku, mimo że jest tu ustawiona.
		"umowa1_prowizja": "777",
		"umowa2_prowizja": "888",
	}
	baza.update(nadpisania)
	return baza


def _kontakt(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"first_name": "Anna",
		"last_name": "Kowalska",
		"custom_pesel": "90010112345",
		"custom_ulica": "Kwiatowa",
		"custom_nr_domu": "5",
		"custom_nr_mieszkania": "12",
		"custom_kod_pocztowy": "00-001",
		"custom_miasto": "Warszawa",
		"email": "anna@example.com",
		"mobile_no": "500600700",
	}
	baza.update(nadpisania)
	return baza


def _umowa(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {
		"wynagrodzenie_wariant": "2",
		"zgoda_przetwarzanie_danych": 1,
		"zgoda_kontakt_telefoniczny": 1,
		"zgoda_dzialania_promocyjne": 1,
	}
	baza.update(nadpisania)
	return baza


def _deal(**nadpisania: Any) -> dict[str, Any]:
	baza: dict[str, Any] = {"name": "PRO/CP/26/0001"}
	baza.update(nadpisania)
	return baza


class TestKwotyWariantu(unittest.TestCase):
	def test_a_wariant_1(self: "TestKwotyWariantu") -> None:
		netto, brutto = kwoty_wariantu_cp(_stale(), "1")
		self.assertEqual(netto, Decimal("1600"))
		self.assertEqual(brutto, Decimal("1968"))

	def test_b_wariant_2(self: "TestKwotyWariantu") -> None:
		netto, brutto = kwoty_wariantu_cp(_stale(), "2")
		self.assertEqual(netto, Decimal("2400"))
		self.assertEqual(brutto, Decimal("2952"))

	def test_c_wariant_niepoprawny_daje_none_none(self: "TestKwotyWariantu") -> None:
		for zly_wariant in ("3", "", "1 ", " 1", "jeden", "1.0"):
			with self.subTest(wariant=zly_wariant):
				self.assertEqual(kwoty_wariantu_cp(_stale(), zly_wariant), (None, None))

	def test_d_wariant_none_daje_none_none(self: "TestKwotyWariantu") -> None:
		self.assertEqual(kwoty_wariantu_cp(_stale(), None), (None, None))

	def test_e_stala_nieustawiona_daje_none_nigdy_zero(self: "TestKwotyWariantu") -> None:
		# `umowa1_netto` w ogóle nieobecna w `stale` (nie tylko pusta) —
		# `frappe.db.get_singles_dict` na kluczu, którego nigdy nie ustawiono,
		# nie zwraca go wcale (patrz brief: "wartości arrive from
		# get_singles_dict as STRINGS lub są nieobecne").
		stale = _stale()
		del stale["umowa1_netto"]
		netto, brutto = kwoty_wariantu_cp(stale, "1")
		self.assertIsNone(netto)
		self.assertNotEqual(netto, Decimal("0"))
		self.assertEqual(brutto, Decimal("1968"))

	def test_f_stala_pusty_string_daje_none(self: "TestKwotyWariantu") -> None:
		netto, _brutto = kwoty_wariantu_cp(_stale(umowa1_netto=""), "1")
		self.assertIsNone(netto)

	def test_g_stala_string_z_kropka_dziesietna(self: "TestKwotyWariantu") -> None:
		# Brief: wartości bywają "1600" albo "1600.0" — obie muszą się sparsować.
		netto, _ = kwoty_wariantu_cp(_stale(umowa1_netto="1600.0"), "1")
		self.assertEqual(netto, Decimal("1600.0"))

	def test_h_puste_stale_daja_none_dla_kazdego_wariantu(self: "TestKwotyWariantu") -> None:
		self.assertEqual(kwoty_wariantu_cp({}, "1"), (None, None))
		self.assertEqual(kwoty_wariantu_cp({}, "2"), (None, None))


class TestWariantyWynagrodzeniaCp(unittest.TestCase):
	def test_a_ksztalt_i_kolejnosc(self: "TestWariantyWynagrodzeniaCp") -> None:
		wynik = warianty_wynagrodzenia_cp(_stale())
		self.assertEqual(len(wynik), 2)
		self.assertEqual(wynik[0]["wariant"], "1")
		self.assertEqual(wynik[1]["wariant"], "2")
		for wpis in wynik:
			with self.subTest(wpis=wpis):
				self.assertEqual(set(wpis.keys()), {"wariant", "netto", "brutto"})

	def test_b_kwoty_jako_stringi_z_dwoma_miejscami(self: "TestWariantyWynagrodzeniaCp") -> None:
		wynik = warianty_wynagrodzenia_cp(_stale())
		self.assertEqual(wynik[0]["netto"], "1600.00")
		self.assertEqual(wynik[0]["brutto"], "1968.00")
		self.assertEqual(wynik[1]["netto"], "2400.00")
		self.assertEqual(wynik[1]["brutto"], "2952.00")

	def test_c_stala_nieustawiona_daje_none_nie_string(self: "TestWariantyWynagrodzeniaCp") -> None:
		stale = _stale()
		del stale["umowa2_brutto"]
		wynik = warianty_wynagrodzenia_cp(stale)
		self.assertIsNone(wynik[1]["brutto"])
		self.assertEqual(wynik[1]["netto"], "2400.00")

	def test_d_puste_stale_dwa_wpisy_wszystko_none(self: "TestWariantyWynagrodzeniaCp") -> None:
		wynik = warianty_wynagrodzenia_cp({})
		self.assertEqual(len(wynik), 2)
		for wpis in wynik:
			with self.subTest(wpis=wpis):
				self.assertIsNone(wpis["netto"])
				self.assertIsNone(wpis["brutto"])


class TestTajemnicaProwizji(unittest.TestCase):
	"""Reguła nadrzędna projektu (CLAUDE.md): żadna funkcja tego modułu nie może
	czytać ani zwracać `umowa1_prowizja`/`umowa2_prowizja`. `_stale()` powyżej
	zawsze ustawia je na jaskrawo odróżnialne wartości ("777"/"888"), żeby
	przypadkowy wyciek był łatwy do złapania w `repr()`."""

	def test_a_kwoty_wariantu_nie_zawiera_prowizji(self: "TestTajemnicaProwizji") -> None:
		wynik = kwoty_wariantu_cp(_stale(), "1")
		self.assertNotIn("777", repr(wynik))
		wynik2 = kwoty_wariantu_cp(_stale(), "2")
		self.assertNotIn("888", repr(wynik2))

	def test_b_warianty_wynagrodzenia_nie_zawiera_prowizji(self: "TestTajemnicaProwizji") -> None:
		wynik = warianty_wynagrodzenia_cp(_stale())
		self.assertNotIn("777", repr(wynik))
		self.assertNotIn("888", repr(wynik))
		for wpis in wynik:
			self.assertNotIn("prowizja", " ".join(wpis.keys()))

	def test_c_kontekst_pdf_nie_zawiera_prowizji(self: "TestTajemnicaProwizji") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertNotIn("777", repr(kontekst))
		self.assertNotIn("888", repr(kontekst))


class TestBrakujacePolaCp(unittest.TestCase):
	def test_a_brak_wariantu_daje_etykiete(self: "TestBrakujacePolaCp") -> None:
		self.assertEqual(brakujace_pola_cp({}), [ETYKIETY_POL_CP["wynagrodzenie_wariant"]])

	def test_b_wariant_pusty_string_daje_etykiete(self: "TestBrakujacePolaCp") -> None:
		self.assertEqual(
			brakujace_pola_cp({"wynagrodzenie_wariant": ""}),
			[ETYKIETY_POL_CP["wynagrodzenie_wariant"]],
		)

	def test_c_wariant_niepoprawny_daje_etykiete(self: "TestBrakujacePolaCp") -> None:
		self.assertEqual(
			brakujace_pola_cp({"wynagrodzenie_wariant": "3"}),
			[ETYKIETY_POL_CP["wynagrodzenie_wariant"]],
		)

	def test_d_wariant_1_brak_brakow(self: "TestBrakujacePolaCp") -> None:
		self.assertEqual(brakujace_pola_cp({"wynagrodzenie_wariant": "1"}), [])

	def test_e_wariant_2_brak_brakow(self: "TestBrakujacePolaCp") -> None:
		self.assertEqual(brakujace_pola_cp({"wynagrodzenie_wariant": "2"}), [])

	def test_f_zgody_nigdy_nie_czynia_umowy_niekompletna(self: "TestBrakujacePolaCp") -> None:
		# Zgody są dobrowolne (Załącznik nr 1 samego dokumentu to mówi wprost)
		# — brak żadnej z nich nie ma prawa pojawić się w brakach.
		dane = {
			"wynagrodzenie_wariant": "1",
			"zgoda_przetwarzanie_danych": 0,
			"zgoda_kontakt_telefoniczny": 0,
			"zgoda_dzialania_promocyjne": 0,
		}
		self.assertEqual(brakujace_pola_cp(dane), [])


class TestReeksportBrakujaceDaneKlienta(unittest.TestCase):
	def test_a_re_eksport_jest_ta_sama_funkcja(self: "TestReeksportBrakujaceDaneKlienta") -> None:
		from crm.volteo_umowa import brakujace_dane_klienta as oryginal

		self.assertIs(brakujace_dane_klienta, oryginal)

	def test_b_dziala_na_pelnym_kontakcie(self: "TestReeksportBrakujaceDaneKlienta") -> None:
		self.assertEqual(brakujace_dane_klienta(_kontakt()), [])

	def test_c_dziala_na_pustym_kontakcie(self: "TestReeksportBrakujaceDaneKlienta") -> None:
		self.assertTrue(len(brakujace_dane_klienta({})) > 0)


class TestKlientDoWyswietlenia(unittest.TestCase):
	def test_a_ksztalt(self: "TestKlientDoWyswietlenia") -> None:
		wynik = klient_do_wyswietlenia(_kontakt())
		self.assertEqual(set(wynik.keys()), {"imie_nazwisko", "adres", "pesel", "telefon", "email"})

	def test_b_wartosci(self: "TestKlientDoWyswietlenia") -> None:
		wynik = klient_do_wyswietlenia(_kontakt())
		self.assertEqual(wynik["imie_nazwisko"], "Anna Kowalska")
		self.assertEqual(wynik["adres"], "ul. Kwiatowa 5/12, 00-001 Warszawa")
		self.assertEqual(wynik["pesel"], "90010112345")
		self.assertEqual(wynik["telefon"], "500600700")
		self.assertEqual(wynik["email"], "anna@example.com")

	def test_c_pusty_kontakt_daje_puste_stringi(self: "TestKlientDoWyswietlenia") -> None:
		wynik = klient_do_wyswietlenia({})
		for wartosc in wynik.values():
			self.assertEqual(wartosc, "")

	def test_d_zgodny_z_kontekstem_pdf_ta_sama_funkcja_wewnatrz(
		self: "TestKlientDoWyswietlenia",
	) -> None:
		# `zbuduj_kontekst_cp` wywołuje `klient_do_wyswietlenia` wewnętrznie —
		# ten test sprawdza, że wynik faktycznie zgadza się z kontekstem PDF-u,
		# więc nie mogą się rozjechać przy przyszłej edycji.
		kontakt = _kontakt()
		podglad = klient_do_wyswietlenia(kontakt)
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), kontakt, _stale(), _DZIS)
		self.assertEqual(kontekst["klient_imie_nazwisko"], podglad["imie_nazwisko"])
		self.assertEqual(kontekst["klient_adres"], podglad["adres"])
		self.assertEqual(kontekst["klient_pesel"], podglad["pesel"])
		self.assertEqual(kontekst["klient_telefon"], podglad["telefon"])
		self.assertEqual(kontekst["klient_email"], podglad["email"])


class TestKontekstKlucze(unittest.TestCase):
	def test_a_dokladny_zestaw_kluczy(self: "TestKontekstKlucze") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(set(kontekst.keys()), _OCZEKIWANE_KLUCZE_KONTEKSTU)


class TestKontekstAdresZKontaktu(unittest.TestCase):
	def test_a_adres_zlozony_z_pol_kontaktu(self: "TestKontekstAdresZKontaktu") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["klient_adres"], "ul. Kwiatowa 5/12, 00-001 Warszawa")

	def test_b_pusty_kontakt_daje_pusty_adres(self: "TestKontekstAdresZKontaktu") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), {}, _stale(), _DZIS)
		self.assertEqual(kontekst["klient_adres"], "")


class TestKontekstZgodyScisleBool(unittest.TestCase):
	def test_a_wszystkie_wlaczone_sa_true(self: "TestKontekstZgodyScisleBool") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertIs(kontekst["zgoda_przetwarzanie_danych"], True)
		self.assertIs(kontekst["zgoda_telefon"], True)
		self.assertIs(kontekst["zgoda_promocja"], True)

	def test_b_wszystkie_wylaczone_sa_false(self: "TestKontekstZgodyScisleBool") -> None:
		umowa = _umowa(
			zgoda_przetwarzanie_danych=0,
			zgoda_kontakt_telefoniczny=0,
			zgoda_dzialania_promocyjne=0,
		)
		kontekst = zbuduj_kontekst_cp(umowa, _deal(), _kontakt(), _stale(), _DZIS)
		self.assertIs(kontekst["zgoda_przetwarzanie_danych"], False)
		self.assertIs(kontekst["zgoda_telefon"], False)
		self.assertIs(kontekst["zgoda_promocja"], False)

	def test_c_brak_wartosci_jest_false_nigdy_none(self: "TestKontekstZgodyScisleBool") -> None:
		# `_stan_bool(None)` zwraca `None` ("nieznane"); kontekst PDF-u musi
		# jednak zawsze wydrukować albo X albo nic — `is True` w
		# `zbuduj_kontekst_cp` sprowadza "nieznane" do `False` (kratka pusta).
		umowa = {"wynagrodzenie_wariant": "1"}
		kontekst = zbuduj_kontekst_cp(umowa, _deal(), _kontakt(), _stale(), _DZIS)
		self.assertIs(kontekst["zgoda_przetwarzanie_danych"], False)
		self.assertIs(kontekst["zgoda_telefon"], False)
		self.assertIs(kontekst["zgoda_promocja"], False)

	def test_d_wartosci_sa_zawsze_typu_bool(self: "TestKontekstZgodyScisleBool") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		for klucz in ("zgoda_przetwarzanie_danych", "zgoda_telefon", "zgoda_promocja"):
			with self.subTest(klucz=klucz):
				self.assertIsInstance(kontekst[klucz], bool)


class TestKontekstWynagrodzenie(unittest.TestCase):
	def test_a_wariant_1(self: "TestKontekstWynagrodzenie") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(wynagrodzenie_wariant="1"), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "1\N{NO-BREAK SPACE}600,00")
		self.assertEqual(kontekst["wynagrodzenie_brutto"], "1\N{NO-BREAK SPACE}968,00")

	def test_b_wariant_2(self: "TestKontekstWynagrodzenie") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(wynagrodzenie_wariant="2"), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "2\N{NO-BREAK SPACE}400,00")
		self.assertEqual(kontekst["wynagrodzenie_brutto"], "2\N{NO-BREAK SPACE}952,00")

	def test_c_brak_wariantu_daje_puste_kwoty(self: "TestKontekstWynagrodzenie") -> None:
		# Brief: "empty string when None, never 0,00".
		kontekst = zbuduj_kontekst_cp(_umowa(wynagrodzenie_wariant=""), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "")
		self.assertEqual(kontekst["wynagrodzenie_brutto"], "")

	def test_d_wariant_niepoprawny_daje_puste_kwoty(self: "TestKontekstWynagrodzenie") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(wynagrodzenie_wariant="9"), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "")
		self.assertEqual(kontekst["wynagrodzenie_brutto"], "")

	def test_e_stala_nieustawiona_daje_pusta_kwote_nie_zero(self: "TestKontekstWynagrodzenie") -> None:
		stale = _stale()
		del stale["umowa1_netto"]
		kontekst = zbuduj_kontekst_cp(_umowa(wynagrodzenie_wariant="1"), _deal(), _kontakt(), stale, _DZIS)
		self.assertEqual(kontekst["wynagrodzenie_netto"], "")
		self.assertNotIn("0,00", kontekst["wynagrodzenie_netto"])


class TestKontekstPodpisy(unittest.TestCase):
	def test_a_podpis_zamawiajacy_wielkimi_literami(self: "TestKontekstPodpisy") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["podpis_zamawiajacy"], "ANNA KOWALSKA")

	def test_b_podpis_wykonawca_stala_proenergy(self: "TestKontekstPodpisy") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["podpis_wykonawca"], "PROENERGY")

	def test_c_podpis_wykonawca_niezalezny_od_kontaktu(self: "TestKontekstPodpisy") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), {}, _stale(), _DZIS)
		self.assertEqual(kontekst["podpis_wykonawca"], "PROENERGY")


class TestKontekstDataIPodpis(unittest.TestCase):
	def test_a_z_imieniem_i_nazwiskiem(self: "TestKontekstDataIPodpis") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["data_i_podpis_zamawiajacy"], "29.09.2026, ANNA KOWALSKA")

	def test_b_bez_imienia_i_nazwiska_sama_data(self: "TestKontekstDataIPodpis") -> None:
		# Pusty kontakt: `klient_imie_nazwisko` wychodzi "", więc łączenie
		# `", ".join(...)` pomija pusty fragment zamiast zostawić wiszący
		# przecinek — dokładnie jak `rodo_data_imie_nazwisko` w
		# `crm/volteo_umowa_pdf.py`.
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), {}, _stale(), _DZIS)
		self.assertEqual(kontekst["data_i_podpis_zamawiajacy"], "29.09.2026")
		self.assertNotIn(",", kontekst["data_i_podpis_zamawiajacy"])


class TestKontekstUmowaNrIData(unittest.TestCase):
	def test_a_umowa_nr_z_nazwy_deala(self: "TestKontekstUmowaNrIData") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(name="PRO/CP/26/0099"), _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["umowa_nr"], "PRO/CP/26/0099")

	def test_b_data_zawarcia_formatowana_pl(self: "TestKontekstUmowaNrIData") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), _deal(), _kontakt(), _stale(), date(2026, 1, 5))
		self.assertEqual(kontekst["data_zawarcia"], "05.01.2026")

	def test_c_brak_deala_daje_pusty_numer(self: "TestKontekstUmowaNrIData") -> None:
		kontekst = zbuduj_kontekst_cp(_umowa(), {}, _kontakt(), _stale(), _DZIS)
		self.assertEqual(kontekst["umowa_nr"], "")


class TestWariantyStalaImportowana(unittest.TestCase):
	def test_a_dwa_warianty(self: "TestWariantyStalaImportowana") -> None:
		self.assertEqual(WARIANTY_WYNAGRODZENIA, ("1", "2"))


if __name__ == "__main__":
	unittest.main()
