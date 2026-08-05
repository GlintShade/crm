import unittest
from decimal import Decimal

from crm.volteo_umowa import (
	KONSTRUKCJA_MONTAZ,
	PROG_PPOZ_KW,
	brakujace_pola,
	kwota_kredytu,
	miejsce_i_pokrycie,
	ppoz_wymagane,
)


def _pelny_formularz() -> dict[str, object]:
	"""Kompletny, poprawny formularz — wariant bazowy do modyfikowania w testach."""
	return {
		"adres_zam_jak_montaz": "Tak",
		"typ_budynku": "Jednorodzinny",
		"powierzchnia_prog": "do 300 m²",
		"finansowanie": "Gotówka",
		"internet": "Tak",
		"instalacja_odgromowa": "Nie",
		"moc_przylaczeniowa_kw": Decimal("8.5"),
		"liczba_faz": "3",
		"osd": "PGE",
		"przekop_gruntowy": "Nie",
		"istniejaca_pv": "Nie",
	}


class TestMiejsceIPokrycie(unittest.TestCase):
	def test_a_wszystkie_znane_konstrukcje(self: "TestMiejsceIPokrycie") -> None:
		self.assertEqual(miejsce_i_pokrycie("Dach skośny - blacha"), ("Dach", "Blacha"))
		self.assertEqual(miejsce_i_pokrycie("Dach skośny - dachówka"), ("Dach", "Dachówka"))
		self.assertEqual(miejsce_i_pokrycie("Dach płaski - inwazyjnie"), ("Dach", "Płaski"))
		self.assertEqual(miejsce_i_pokrycie("Dach płaski - balast"), ("Dach", "Płaski"))
		self.assertEqual(miejsce_i_pokrycie("Konstrukcja gruntowa"), ("Grunt", None))

	def test_b_nieznana_konstrukcja(self: "TestMiejsceIPokrycie") -> None:
		self.assertEqual(miejsce_i_pokrycie("Coś nieznanego"), (None, None))

	def test_c_brak_konstrukcji(self: "TestMiejsceIPokrycie") -> None:
		self.assertEqual(miejsce_i_pokrycie(None), (None, None))
		self.assertEqual(miejsce_i_pokrycie(""), (None, None))

	def test_d_biale_znaki_na_brzegach(self: "TestMiejsceIPokrycie") -> None:
		self.assertEqual(miejsce_i_pokrycie("  Konstrukcja gruntowa  "), ("Grunt", None))
		self.assertEqual(miejsce_i_pokrycie("\tDach skośny - blacha\n"), ("Dach", "Blacha"))

	def test_e_nie_mutuje_slownika_modulowego(self: "TestMiejsceIPokrycie") -> None:
		przed = dict(KONSTRUKCJA_MONTAZ)
		miejsce_i_pokrycie("Dach skośny - blacha")
		miejsce_i_pokrycie("nieznana")
		miejsce_i_pokrycie(None)
		self.assertEqual(KONSTRUKCJA_MONTAZ, przed)


class TestPpozWymagane(unittest.TestCase):
	def test_a_ponizej_progu(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(Decimal("5.0"), None))

	def test_b_dokladnie_prog_nie_wymaga(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(PROG_PPOZ_KW, None))
		self.assertFalse(ppoz_wymagane("6.5", "0"))

	def test_c_powyzej_progu(self: "TestPpozWymagane") -> None:
		self.assertTrue(ppoz_wymagane(Decimal("6.51"), None))
		self.assertTrue(ppoz_wymagane("10", None))

	def test_d_rozbudowa_suma_przekracza_prog(self: "TestPpozWymagane") -> None:
		# Ani nowa (4.0), ani istniejąca (3.0) instalacja osobno nie przekracza 6.5,
		# ale ich suma (7.0) tak — to reguła najłatwiejsza do przypadkowego złamania.
		self.assertTrue(ppoz_wymagane(Decimal("4.0"), Decimal("3.0")))

	def test_e_rozbudowa_suma_nie_przekracza_progu(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(Decimal("3.0"), Decimal("3.0")))

	def test_f_brakujace_wartosci_traktowane_jako_zero(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(None, None))
		self.assertFalse(ppoz_wymagane("", ""))
		self.assertFalse(ppoz_wymagane(None, "6.5"))

	def test_g_rozne_typy_wejsciowe(self: "TestPpozWymagane") -> None:
		self.assertTrue(ppoz_wymagane(7, 0))
		self.assertTrue(ppoz_wymagane(7.0, 0.0))


class TestKwotaKredytu(unittest.TestCase):
	def test_a_zwykly_przypadek(self: "TestKwotaKredytu") -> None:
		self.assertEqual(kwota_kredytu(Decimal("50000"), Decimal("10000")), Decimal("40000.00"))

	def test_b_zerowy_wklad_wlasny(self: "TestKwotaKredytu") -> None:
		self.assertEqual(kwota_kredytu(Decimal("50000"), Decimal("0")), Decimal("50000.00"))
		self.assertEqual(kwota_kredytu(Decimal("50000"), None), Decimal("50000.00"))

	def test_c_wklad_wiekszy_niz_brutto_przycina_do_zera(self: "TestKwotaKredytu") -> None:
		self.assertEqual(kwota_kredytu(Decimal("10000"), Decimal("15000")), Decimal("0.00"))

	def test_d_wejscia_tekstowe(self: "TestKwotaKredytu") -> None:
		self.assertEqual(kwota_kredytu("50000", "10000.50"), Decimal("39999.50"))

	def test_e_kwantyzacja_do_dwoch_miejsc(self: "TestKwotaKredytu") -> None:
		wynik = kwota_kredytu(Decimal("100.005"), Decimal("0"))
		self.assertEqual(wynik, Decimal("100.01"))
		self.assertEqual(wynik.as_tuple().exponent, -2)


class TestBrakujacePola(unittest.TestCase):
	def test_a_pelny_formularz_bez_brakow(self: "TestBrakujacePola") -> None:
		self.assertEqual(brakujace_pola(_pelny_formularz()), [])

	def test_b_brak_pol_zawsze_wymaganych(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["typ_budynku"] = ""
		dane["osd"] = None
		self.assertEqual(brakujace_pola(dane), ["typ_budynku", "osd"])

	def test_c_inny_adres_wlaczony(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["adres_zam_jak_montaz"] = "Nie"
		brakujace = brakujace_pola(dane)
		self.assertEqual(
			brakujace,
			[
				"adres_zam_ulica",
				"adres_zam_nr_domu",
				"adres_zam_kod",
				"adres_zam_miasto",
				"adres_montaz_ulica",
				"adres_montaz_nr_domu",
				"adres_montaz_kod",
				"adres_montaz_miasto",
			],
		)
		self.assertNotIn("adres_zam_nr_mieszkania", brakujace)

	def test_d_inny_adres_wylaczony_nie_wymaga_adresow(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["adres_zam_jak_montaz"] = "Tak"
		self.assertEqual(brakujace_pola(dane), [])

	def test_e_duza_powierzchnia_wlaczona(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["powierzchnia_prog"] = "powyżej 300 m²"
		self.assertEqual(brakujace_pola(dane), ["powierzchnia_m2"])

	def test_f_duza_powierzchnia_wypelniona(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["powierzchnia_prog"] = "powyżej 300 m²"
		dane["powierzchnia_m2"] = Decimal("350")
		self.assertEqual(brakujace_pola(dane), [])

	def test_g_kredyt_gotowka_wlaczony(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["finansowanie"] = "Kredyt + gotówka"
		self.assertEqual(brakujace_pola(dane), ["wklad_wlasny_pln"])

	def test_h_kredyt_gotowka_zero_jest_wypelnione(self: "TestBrakujacePola") -> None:
		# Asymetria: 0 zł własnego wkładu to legalna, kompletna odpowiedź.
		dane = _pelny_formularz()
		dane["finansowanie"] = "Kredyt + gotówka"
		dane["wklad_wlasny_pln"] = Decimal("0")
		self.assertEqual(brakujace_pola(dane), [])

	def test_i_istniejaca_pv_wlaczona(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["istniejaca_pv"] = "Tak"
		self.assertEqual(
			brakujace_pola(dane),
			[
				"istniejaca_pv_moc_inwertera_kw",
				"istniejaca_pv_moc_kwp",
				"istniejaca_pv_producent_inwertera",
			],
		)

	def test_j_istniejaca_pv_wypelniona(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["istniejaca_pv"] = "Tak"
		dane["istniejaca_pv_moc_inwertera_kw"] = Decimal("5")
		dane["istniejaca_pv_moc_kwp"] = Decimal("6")
		dane["istniejaca_pv_producent_inwertera"] = "Huawei"
		self.assertEqual(brakujace_pola(dane), [])

	def test_k_moc_przylaczeniowa_zero_jest_puste(self: "TestBrakujacePola") -> None:
		# Kontrast z testem h: dla mocy przyłączeniowej 0 NIE jest wartością legalną.
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = Decimal("0")
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_l_moc_przylaczeniowa_zero_int_i_float(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = 0
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])
		dane["moc_przylaczeniowa_kw"] = 0.0
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_m_biale_znaki_traktowane_jako_puste(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["typ_budynku"] = "   "
		self.assertEqual(brakujace_pola(dane), ["typ_budynku"])

	def test_n_stabilna_kolejnosc_wielu_brakow(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["adres_zam_jak_montaz"] = "Nie"
		dane["osd"] = None
		dane["moc_przylaczeniowa_kw"] = None
		brakujace = brakujace_pola(dane)
		self.assertEqual(
			brakujace,
			[
				"moc_przylaczeniowa_kw",
				"osd",
				"adres_zam_ulica",
				"adres_zam_nr_domu",
				"adres_zam_kod",
				"adres_zam_miasto",
				"adres_montaz_ulica",
				"adres_montaz_nr_domu",
				"adres_montaz_kod",
				"adres_montaz_miasto",
			],
		)

	def test_o_nie_mutuje_wejsciowego_slownika(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		przed = dict(dane)
		brakujace_pola(dane)
		self.assertEqual(dane, przed)

	def test_p_moc_przylaczeniowa_jako_string_zero(self: "TestBrakujacePola") -> None:
		# Frappe dostarcza wartości formularza jako stringi z klienta — "0" musi
		# liczyć się identycznie jak Decimal("0")/int 0/float 0.0.
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = "0"
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_q_moc_przylaczeniowa_jako_string_zero_kropka(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = "0.0"
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_r_moc_przylaczeniowa_jako_sama_spacja(self: "TestBrakujacePola") -> None:
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = " "
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_s_moc_przylaczeniowa_niepoprawny_tekst_jest_pusta(self: "TestBrakujacePola") -> None:
		# Tekstu nie da się odczytać jako liczby, więc nigdy nie może być poprawną
		# mocą — traktujemy go jak pole puste, nie podnosimy wyjątku.
		dane = _pelny_formularz()
		dane["moc_przylaczeniowa_kw"] = "abc"
		self.assertEqual(brakujace_pola(dane), ["moc_przylaczeniowa_kw"])

	def test_t_wklad_wlasny_jako_string_zero_pozostaje_wypelniony(self: "TestBrakujacePola") -> None:
		# Asymetria musi przetrwać naprawę: "0" jako string dla pola spoza
		# `_ZERO_OZNACZA_PUSTE` to nadal legalna, kompletna wartość.
		dane = _pelny_formularz()
		dane["finansowanie"] = "Kredyt + gotówka"
		dane["wklad_wlasny_pln"] = "0"
		self.assertEqual(brakujace_pola(dane), [])


class TestDecimalLubZeroIKwotaKredytuNaSurowychDanych(unittest.TestCase):
	"""Wartości z formularza klienta (stringi) nie mogą podnosić wyjątku w kalkulatorze cenowym."""

	def test_a_sama_spacja_nie_podnosi_wyjatku(self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych") -> None:
		self.assertEqual(kwota_kredytu(" ", " "), Decimal("0.00"))

	def test_b_niepoprawny_tekst_nie_podnosi_wyjatku(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertEqual(kwota_kredytu("abc", "def"), Decimal("0.00"))

	def test_c_niepoprawny_tekst_w_ppoz_wymagane_nie_podnosi_wyjatku(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertFalse(ppoz_wymagane("abc", " "))

	def test_d_poprawna_wartosc_z_niepoprawnym_wkladem_liczy_sie_normalnie(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertEqual(kwota_kredytu("50000", "abc"), Decimal("50000.00"))


if __name__ == "__main__":
	unittest.main()
