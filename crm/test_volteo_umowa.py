import unittest
from decimal import Decimal

from crm.volteo_umowa import (
	KONSTRUKCJA_MONTAZ,
	PROG_PPOZ_KW,
	brakujace_dane_klienta,
	brakujace_pola,
	czy_propagowac_zgody,
	czy_umowa_podwojna,
	kod_szablonu,
	kontakty_do_zgod,
	kwota_kredytu,
	miejsce_i_pokrycie,
	ppoz_wymagane,
)


def _pelny_kontakt() -> dict[str, str]:
	"""Kompletne dane kontaktu w kształcie `_dane_kontaktu()` z `crm/api/umowa.py`."""
	return {
		"first_name": "Jan",
		"last_name": "Kowalski",
		"custom_pesel": "12345678901",
		"custom_ulica": "Polna",
		"custom_nr_domu": "5",
		"custom_nr_mieszkania": "",
		"custom_kod_pocztowy": "00-001",
		"custom_miasto": "Warszawa",
		"custom_wojewodztwo": "mazowieckie",
		"email": "jan@example.com",
		"mobile_no": "500600700",
	}


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
	# Wszystkie testy tej klasy przekazują trzeci argument (`istniejaca_pv`)
	# wprost dobrany tak, żeby zachować pierwotną intencję każdego przypadku:
	# "Tak", gdy `moc_istniejaca_kw` niesie realną (choćby zerową) wartość do
	# zsumowania, "Nie" gdy drugi argument i tak jest pusty/nieistotny dla
	# testowanego zachowania. Bramka istniejaca_pv sama w sobie ma osobną
	# klasę testów niżej: `TestPpozWymaganeIstniejacaPvBramka` (ops#145 Z2).
	def test_a_ponizej_progu(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(Decimal("5.0"), None, "Nie"))

	def test_b_dokladnie_prog_nie_wymaga(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(PROG_PPOZ_KW, None, "Nie"))
		self.assertFalse(ppoz_wymagane("6.5", "0", "Tak"))

	def test_c_powyzej_progu(self: "TestPpozWymagane") -> None:
		self.assertTrue(ppoz_wymagane(Decimal("6.51"), None, "Nie"))
		self.assertTrue(ppoz_wymagane("10", None, "Nie"))

	def test_d_rozbudowa_suma_przekracza_prog(self: "TestPpozWymagane") -> None:
		# Ani nowa (4.0), ani istniejąca (3.0) instalacja osobno nie przekracza 6.5,
		# ale ich suma (7.0) tak — to reguła najłatwiejsza do przypadkowego złamania.
		self.assertTrue(ppoz_wymagane(Decimal("4.0"), Decimal("3.0"), "Tak"))

	def test_e_rozbudowa_suma_nie_przekracza_progu(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(Decimal("3.0"), Decimal("3.0"), "Tak"))

	def test_f_brakujace_wartosci_traktowane_jako_zero(self: "TestPpozWymagane") -> None:
		self.assertFalse(ppoz_wymagane(None, None, "Nie"))
		self.assertFalse(ppoz_wymagane("", "", "Nie"))
		# Bramka otwarta ("Tak"), a suma dokładnie na progu (0 + 6.5): wciąż
		# nie wymaga zgody, próg jest wyłączny.
		self.assertFalse(ppoz_wymagane(None, "6.5", "Tak"))

	def test_g_rozne_typy_wejsciowe(self: "TestPpozWymagane") -> None:
		self.assertTrue(ppoz_wymagane(7, 0, "Tak"))
		self.assertTrue(ppoz_wymagane(7.0, 0.0, "Tak"))


class TestPpozWymaganeIstniejacaPvBramka(unittest.TestCase):
	"""Z2 (ops#145): moc istniejącej instalacji PV liczy się do progu PPOŻ
	TYLKO, gdy przełącznik `istniejaca_pv` jest jawnie "Tak". W przeciwnym
	razie (w tym formularz niespójny, gdzie stara moc została w polu po
	zmianie wyboru na "Nie") moc istniejąca jest ignorowana."""

	def test_a_nie_ignoruje_moc_mimo_wypelnionej(self: "TestPpozWymaganeIstniejacaPvBramka") -> None:
		# Formularz niespójny: "Nie" wybrane, ale stara moc (4.0) zostala w polu.
		self.assertFalse(ppoz_wymagane(Decimal("3.0"), Decimal("4.0"), "Nie"))

	def test_b_tak_liczy_moc_do_sumy(self: "TestPpozWymaganeIstniejacaPvBramka") -> None:
		self.assertTrue(ppoz_wymagane(Decimal("3.0"), Decimal("4.0"), "Tak"))

	def test_c_nieznany_wybor_ignoruje_moc(self: "TestPpozWymaganeIstniejacaPvBramka") -> None:
		for wybor in (None, "", "Coś innego"):
			with self.subTest(wybor=wybor):
				self.assertFalse(ppoz_wymagane(Decimal("3.0"), Decimal("4.0"), wybor))

	def test_d_bramka_nie_wplywa_na_moc_nowej_instalacji(
		self: "TestPpozWymaganeIstniejacaPvBramka",
	) -> None:
		# Moc nowej instalacji liczy się zawsze, niezależnie od bramki.
		self.assertTrue(ppoz_wymagane(Decimal("10.0"), Decimal("4.0"), "Nie"))


class TestPpozWymaganeKalkulator(unittest.TestCase):
	"""ops#194 (decyzja właściciela 2026-09-25): kalkulator OZE dolicza koszt
	uzgodnień PPOŻ do ceny klienta w momencie wyceny, więc gdy `custom_ppoz`
	szansy to "Tak", umowa nie ma prawa wyjść na "Nie": czwarty argument
	wygrywa z sumą mocy niezależnie od jej wartości."""

	def test_a_tak_wygrywa_ponizej_progu(self: "TestPpozWymaganeKalkulator") -> None:
		# Suma (3.0) daleko poniżej progu (6.5), ale kalkulator już doliczył PPOŻ.
		self.assertTrue(ppoz_wymagane(Decimal("3.0"), None, "Nie", "Tak"))

	def test_b_tak_wygrywa_mimo_istniejaca_pv_nie(self: "TestPpozWymaganeKalkulator") -> None:
		self.assertTrue(ppoz_wymagane(Decimal("2.0"), Decimal("1.0"), "Nie", "Tak"))

	def test_c_nie_z_kalkulatora_nie_zmienia_istniejacej_reguly(
		self: "TestPpozWymaganeKalkulator",
	) -> None:
		# "Nie" z kalkulatora to no-op: reguła progowa liczy się jak dotychczas,
		# zarówno poniżej, jak i powyżej progu.
		self.assertFalse(ppoz_wymagane(Decimal("3.0"), None, "Nie", "Nie"))
		self.assertTrue(ppoz_wymagane(Decimal("10.0"), None, "Nie", "Nie"))

	def test_d_brak_wartosci_zachowuje_sie_jak_wywolanie_trzyargumentowe(
		self: "TestPpozWymaganeKalkulator",
	) -> None:
		for wybor in (None, "", "coś nierozpoznanego"):
			with self.subTest(wybor=wybor):
				self.assertEqual(
					ppoz_wymagane(Decimal("3.0"), Decimal("4.0"), "Tak", wybor),
					ppoz_wymagane(Decimal("3.0"), Decimal("4.0"), "Tak"),
				)
				self.assertEqual(
					ppoz_wymagane(Decimal("10.0"), None, "Nie", wybor),
					ppoz_wymagane(Decimal("10.0"), None, "Nie"),
				)

	def test_e_dopasowanie_scisle_bez_bialych_znakow_i_wielkosci_liter(
		self: "TestPpozWymaganeKalkulator",
	) -> None:
		# Suma (3.0) poniżej progu: gdyby dopasowanie nie było ścisłe, te warianty
		# błędnie przełączyłyby wynik na True.
		for wybor in (" Tak", "Tak ", "tak", "TAK"):
			with self.subTest(wybor=wybor):
				self.assertFalse(ppoz_wymagane(Decimal("3.0"), None, "Nie", wybor))


class TestKwotaKredytu(unittest.TestCase):
	# Wszystkie testy tej klasy przekazują trzeci argument jako
	# "Kredyt + gotówka": to gałąź, która zachowuje klasyczną arytmetykę
	# `brutto - wklad_wlasny` testowaną tu od zawsze. Zachowanie zależne od
	# samego wyboru finansowania ma osobną klasę niżej:
	# `TestKwotaKredytuFinansowanieBramka` (ops#145 Z1).
	def test_a_zwykly_przypadek(self: "TestKwotaKredytu") -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("50000"), Decimal("10000"), "Kredyt + gotówka"), Decimal("40000.00")
		)

	def test_b_zerowy_wklad_wlasny(self: "TestKwotaKredytu") -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("50000"), Decimal("0"), "Kredyt + gotówka"), Decimal("50000.00")
		)
		self.assertEqual(kwota_kredytu(Decimal("50000"), None, "Kredyt + gotówka"), Decimal("50000.00"))

	def test_c_wklad_wiekszy_niz_brutto_przycina_do_zera(self: "TestKwotaKredytu") -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("10000"), Decimal("15000"), "Kredyt + gotówka"), Decimal("0.00")
		)

	def test_d_wejscia_tekstowe(self: "TestKwotaKredytu") -> None:
		self.assertEqual(
			kwota_kredytu("50000", "10000.50", "Kredyt + gotówka"), Decimal("39999.50")
		)

	def test_e_kwantyzacja_do_dwoch_miejsc(self: "TestKwotaKredytu") -> None:
		wynik = kwota_kredytu(Decimal("100.005"), Decimal("0"), "Kredyt + gotówka")
		self.assertEqual(wynik, Decimal("100.01"))
		self.assertEqual(wynik.as_tuple().exponent, -2)


class TestKwotaKredytuFinansowanieBramka(unittest.TestCase):
	"""Z1 (ops#145, CRITICAL): kwota kredytu zależy od wybranego sposobu
	finansowania, nie tylko od arytmetyki brutto minus wkład."""

	def test_a_gotowka_100_zawsze_zero(self: "TestKwotaKredytuFinansowanieBramka") -> None:
		# Nawet gdy w polu wklad_wlasny_pln zostala jakas stara wartosc,
		# "Gotówka 100%" nie generuje kredytu.
		self.assertEqual(
			kwota_kredytu(Decimal("50000"), Decimal("10000"), "Gotówka 100%"), Decimal("0.00")
		)
		self.assertEqual(kwota_kredytu(Decimal("50000"), Decimal("0"), "Gotówka 100%"), Decimal("0.00"))

	def test_b_kredyt_100_caly_brutto_wklad_ignorowany(
		self: "TestKwotaKredytuFinansowanieBramka",
	) -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("50000"), Decimal("10000"), "Kredyt 100%"), Decimal("50000.00")
		)
		self.assertEqual(kwota_kredytu(Decimal("50000"), Decimal("0"), "Kredyt 100%"), Decimal("50000.00"))

	def test_c_kredyt_i_gotowka_odejmuje_wklad(self: "TestKwotaKredytuFinansowanieBramka") -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("50000"), Decimal("10000"), "Kredyt + gotówka"), Decimal("40000.00")
		)

	def test_d_kredyt_i_gotowka_wklad_wiekszy_od_brutto_przycina_do_zera(
		self: "TestKwotaKredytuFinansowanieBramka",
	) -> None:
		self.assertEqual(
			kwota_kredytu(Decimal("10000"), Decimal("15000"), "Kredyt + gotówka"), Decimal("0.00")
		)

	def test_e_nieznany_lub_pusty_wybor_zero(self: "TestKwotaKredytuFinansowanieBramka") -> None:
		for wybor in (None, "", "Coś innego"):
			with self.subTest(wybor=wybor):
				self.assertEqual(
					kwota_kredytu(Decimal("50000"), Decimal("10000"), wybor), Decimal("0.00")
				)

	def test_f_kredyt_100_ujemny_brutto_przycina_do_zera(
		self: "TestKwotaKredytuFinansowanieBramka",
	) -> None:
		self.assertEqual(kwota_kredytu(Decimal("-100"), Decimal("0"), "Kredyt 100%"), Decimal("0.00"))


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


class TestBrakujaceDaneKlienta(unittest.TestCase):
	"""ops#146 (Z4): dane osobowe klienta idą z `Contact`, nie z `Volteo Umowa`,
	więc mają własną walidację, osobną od `brakujace_pola`. Adres kontaktu
	celowo NIE jest tu sprawdzany, patrz `test_m_adres_kontaktu_nie_wplywa`."""

	def test_a_pelny_kontakt_bez_brakow(self: "TestBrakujaceDaneKlienta") -> None:
		self.assertEqual(brakujace_dane_klienta(_pelny_kontakt()), [])

	def test_b_brak_imienia(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["first_name"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["Imię i nazwisko"])

	def test_c_brak_nazwiska(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["last_name"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["Imię i nazwisko"])

	def test_d_brak_obojga_imienia_i_nazwiska_jedna_etykieta(
		self: "TestBrakujaceDaneKlienta",
	) -> None:
		dane = _pelny_kontakt()
		dane["first_name"] = ""
		dane["last_name"] = None
		self.assertEqual(brakujace_dane_klienta(dane), ["Imię i nazwisko"])

	def test_e_brak_pesel(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["custom_pesel"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["PESEL"])

	def test_f_brak_telefonu(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["mobile_no"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["Telefon"])

	def test_g_brak_email(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["email"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["E-mail"])

	def test_h_biale_znaki_traktowane_jako_brak(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["custom_pesel"] = "   "
		self.assertEqual(brakujace_dane_klienta(dane), ["PESEL"])

	def test_i_none_traktowany_jako_brak(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["email"] = None
		self.assertEqual(brakujace_dane_klienta(dane), ["E-mail"])

	def test_j_stabilna_kolejnosc_wielu_brakow(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		dane["custom_pesel"] = ""
		dane["email"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), ["PESEL", "E-mail"])

	def test_k_wszystko_puste(self: "TestBrakujaceDaneKlienta") -> None:
		dane = {pole: "" for pole in ("first_name", "last_name", "custom_pesel", "email", "mobile_no")}
		self.assertEqual(
			brakujace_dane_klienta(dane),
			["Imię i nazwisko", "PESEL", "Telefon", "E-mail"],
		)

	def test_l_pusty_slownik_wszystko_brakuje(self: "TestBrakujaceDaneKlienta") -> None:
		self.assertEqual(
			brakujace_dane_klienta({}),
			["Imię i nazwisko", "PESEL", "Telefon", "E-mail"],
		)

	def test_m_adres_kontaktu_nie_wplywa(self: "TestBrakujaceDaneKlienta") -> None:
		# Adres zamieszkania klienta ma własną ścieżkę walidacji w `brakujace_pola`
		# (pola `adres_zam_*` formularza umowy), tu celowo bez wpływu.
		dane = _pelny_kontakt()
		dane["custom_ulica"] = ""
		dane["custom_nr_domu"] = ""
		dane["custom_kod_pocztowy"] = ""
		dane["custom_miasto"] = ""
		dane["custom_wojewodztwo"] = ""
		self.assertEqual(brakujace_dane_klienta(dane), [])

	def test_n_nie_mutuje_wejsciowego_slownika(self: "TestBrakujaceDaneKlienta") -> None:
		dane = _pelny_kontakt()
		przed = dict(dane)
		brakujace_dane_klienta(dane)
		self.assertEqual(dane, przed)


class TestDecimalLubZeroIKwotaKredytuNaSurowychDanych(unittest.TestCase):
	"""Wartości z formularza klienta (stringi) nie mogą podnosić wyjątku w kalkulatorze cenowym."""

	def test_a_sama_spacja_nie_podnosi_wyjatku(self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych") -> None:
		self.assertEqual(kwota_kredytu(" ", " ", "Kredyt + gotówka"), Decimal("0.00"))

	def test_b_niepoprawny_tekst_nie_podnosi_wyjatku(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertEqual(kwota_kredytu("abc", "def", "Kredyt + gotówka"), Decimal("0.00"))

	def test_c_niepoprawny_tekst_w_ppoz_wymagane_nie_podnosi_wyjatku(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertFalse(ppoz_wymagane("abc", " ", "Tak"))

	def test_d_poprawna_wartosc_z_niepoprawnym_wkladem_liczy_sie_normalnie(
		self: "TestDecimalLubZeroIKwotaKredytuNaSurowychDanych",
	) -> None:
		self.assertEqual(kwota_kredytu("50000", "abc", "Kredyt + gotówka"), Decimal("50000.00"))


class TestCzyPropagowacZgody(unittest.TestCase):
	"""ops#170 / REVISIT.md A-3: propagacja zgod wylaczona po wyslaniu/podpisaniu dokumentu."""

	def test_a_brak_statusu_none_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertTrue(czy_propagowac_zgody(None))

	def test_b_pusty_string_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertTrue(czy_propagowac_zgody(""))

	def test_c_wysylanie_nie_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertFalse(czy_propagowac_zgody("Wysyłanie"))

	def test_d_wyslana_nie_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertFalse(czy_propagowac_zgody("Wysłana"))

	def test_e_podpisana_nie_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertFalse(czy_propagowac_zgody("Podpisana"))

	def test_f_nierozpoznany_status_propaguje(self: "TestCzyPropagowacZgody") -> None:
		# Terminalne statusy nie-sukcesu ("Błąd" i inne spoza SEND_BLOCKED_STATUSES)
		# wracaja formularz do stanu roboczego, propagacja ma wtedy sens tak samo
		# jak przed pierwsza wysylka.
		self.assertTrue(czy_propagowac_zgody("Błąd"))

	def test_g_odrzucona_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertTrue(czy_propagowac_zgody("Odrzucona"))

	def test_h_wygasla_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertTrue(czy_propagowac_zgody("Wygasła"))

	def test_i_wycofana_propaguje(self: "TestCzyPropagowacZgody") -> None:
		self.assertTrue(czy_propagowac_zgody("Wycofana"))


class TestKontaktyDoZgod(unittest.TestCase):
	"""ops#170: lista kontaktow do stemplowania zgod, podstawowy pierwszy, drugi Zamawiajacy drugi."""

	def test_a_oba_puste_daje_pusta_liste(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod(None, None), [])

	def test_b_oba_puste_string_daje_pusta_liste(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod("", ""), [])

	def test_c_tylko_podstawowy(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod("CONT-0001", None), ["CONT-0001"])

	def test_d_tylko_drugi_bez_podstawowego(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod(None, "CONT-0002"), ["CONT-0002"])

	def test_e_oba_ustawione_podstawowy_pierwszy(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod("CONT-0001", "CONT-0002"), ["CONT-0001", "CONT-0002"])

	def test_f_duplikat_zwraca_jeden_wpis(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod("CONT-0001", "CONT-0001"), ["CONT-0001"])

	def test_g_pusty_string_podstawowy_z_drugim_ustawionym(self: "TestKontaktyDoZgod") -> None:
		self.assertEqual(kontakty_do_zgod("", "CONT-0002"), ["CONT-0002"])

	def test_h_nie_mutuje_wejscia(self: "TestKontaktyDoZgod") -> None:
		podstawowy = "CONT-0001"
		drugi = "CONT-0002"
		kontakty_do_zgod(podstawowy, drugi)
		self.assertEqual(podstawowy, "CONT-0001")
		self.assertEqual(drugi, "CONT-0002")


class TestKodSzablonu(unittest.TestCase):
	"""ops#167: wybór kodu wbudowanego szablonu PDF-u umowy (klucz w
	`crm.volteo_umowa_render.SZABLONY`), zależny od rodzaju umowy i obecności
	drugiego Zamawiającego."""

	def test_a_pojedyncza_pv(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Fotowoltaika", False), "PV")

	def test_b_pojedyncza_pvme(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Fotowoltaika + Magazyn", False), "PVME")

	def test_c_pojedyncza_me(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Magazyn energii", False), "ME")

	def test_d_podwojna_pv(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Fotowoltaika", True), "PV_2")

	def test_e_podwojna_pvme(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Fotowoltaika + Magazyn", True), "PVME_2")

	def test_f_podwojna_me(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Magazyn energii", True), "ME_2")

	def test_g_czyste_powietrze_pojedyncza(self: "TestKodSzablonu") -> None:
		# "CP" nie ma wpisu w SZABLONY (ani pojedynczego, ani podwójnego).
		# Ta funkcja to tylko oblicza kod, weryfikacja obecności w rejestrze
		# jest rolą wołającego (`crm/api/umowa.py`).
		self.assertEqual(kod_szablonu("Czyste Powietrze", False), "CP")

	def test_h_czyste_powietrze_podwojna(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("Czyste Powietrze", True), "CP_2")

	def test_i_nieznany_rodzaj_pojedyncza(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("cokolwiek nierozpoznanego", False), "XX")

	def test_j_nieznany_rodzaj_podwojna(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu("cokolwiek nierozpoznanego", True), "XX_2")

	def test_k_pusty_rodzaj_pojedyncza(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu(None, False), "XX")

	def test_l_pusty_rodzaj_podwojna(self: "TestKodSzablonu") -> None:
		self.assertEqual(kod_szablonu(None, True), "XX_2")


class TestCzyUmowaPodwojna(unittest.TestCase):
	"""ops#167: `czy_umowa_podwojna` = bool `drugi_zamawiajacy`."""

	def test_a_brak_klucza_daje_falsz(self: "TestCzyUmowaPodwojna") -> None:
		self.assertFalse(czy_umowa_podwojna({}))

	def test_b_none_daje_falsz(self: "TestCzyUmowaPodwojna") -> None:
		self.assertFalse(czy_umowa_podwojna({"drugi_zamawiajacy": None}))

	def test_c_pusty_string_daje_falsz(self: "TestCzyUmowaPodwojna") -> None:
		self.assertFalse(czy_umowa_podwojna({"drugi_zamawiajacy": ""}))

	def test_d_ustawiona_nazwa_kontaktu_daje_prawde(self: "TestCzyUmowaPodwojna") -> None:
		self.assertTrue(czy_umowa_podwojna({"drugi_zamawiajacy": "CONT-0002"}))

	def test_e_nie_mutuje_wejscia(self: "TestCzyUmowaPodwojna") -> None:
		umowa = {"drugi_zamawiajacy": "CONT-0002", "inne_pole": "x"}
		czy_umowa_podwojna(umowa)
		self.assertEqual(umowa, {"drugi_zamawiajacy": "CONT-0002", "inne_pole": "x"})


if __name__ == "__main__":
	unittest.main()
