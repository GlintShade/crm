import datetime
import re
import unittest

from crm.volteo_powiadomienia import (
	AUTOR_ZASTEPCZY_CC,
	DNI_KROTKO,
	DNI_TYGODNIA,
	ETYKIETY_PRODUKTOW,
	MIESIACE_DOPELNIACZ,
	czy_zmienil_sie_termin,
	formatuj_date,
	formatuj_termin,
	link_do_mapy,
	nazwa_przydzielajacego,
	nazwy_produktow,
	sklej_adres,
	zbuduj_powiadomienie_odebrania,
	zbuduj_powiadomienie_przydzialu,
	zbuduj_powiadomienie_zmiany_terminu,
)

_DASH_RE = re.compile("[\u2013\u2014]")

# 2026-09-24 jest czwartkiem (`Today's date is 2026-09-24` w tej sesji, zweryfikowane
# `datetime.date(2026, 9, 24).weekday() == 3`); 2026-09-25 jest piątkiem, użyte tam, gdzie
# testowi zależy na dwóch kolejnych dniach o różnej nazwie.
CZWARTEK = datetime.datetime(2026, 9, 24, 14, 30, 0)
PIATEK = datetime.datetime(2026, 9, 25, 10, 0, 0)

LEAD_PELNY = {
	"lead_name": "Jan Kowalski",
	"mobile_no": "500600700",
	"custom_install_address": "Parkowa",
	"custom_nr_domu": "5",
	"custom_install_postal_code": "64-100",
	"custom_install_city": "Leszno",
	"custom_termin_spotkania": CZWARTEK,
	"custom_kolejny_kontakt": datetime.date(2026, 9, 30),
	"custom_posiadane_produkty": "PV+ME",
	"custom_uwagi_import": "Klient pytał o dofinansowanie i termin montażu.",
}

LEAD_MINIMALNY = {
	"lead_name": "Anna Nowak",
	"mobile_no": "",
	"custom_install_address": "",
	"custom_nr_domu": "",
	"custom_install_postal_code": "",
	"custom_install_city": "",
	"custom_termin_spotkania": None,
	"custom_kolejny_kontakt": None,
	"custom_posiadane_produkty": "",
	"custom_uwagi_import": "",
}

URL = "http://crm.localhost/crm/leads/CRM-LEAD-2026-00001"


class TestDniIMiesiace(unittest.TestCase):
	def test_a_siedem_dni_pelnych(self: "TestDniIMiesiace") -> None:
		self.assertEqual(len(DNI_TYGODNIA), 7)
		self.assertEqual(DNI_TYGODNIA[0], "poniedziałek")
		self.assertEqual(DNI_TYGODNIA[6], "niedziela")

	def test_b_siedem_dni_krotkich(self: "TestDniIMiesiace") -> None:
		self.assertEqual(len(DNI_KROTKO), 7)
		self.assertEqual(DNI_KROTKO[3], "czw.")
		self.assertEqual(DNI_KROTKO[4], "pt.")

	def test_c_dwanascie_miesiecy_dopelniacz(self: "TestDniIMiesiace") -> None:
		self.assertEqual(len(MIESIACE_DOPELNIACZ), 12)
		self.assertEqual(MIESIACE_DOPELNIACZ[8], "września")
		self.assertEqual(MIESIACE_DOPELNIACZ[0], "stycznia")


class TestFormatujTermin(unittest.TestCase):
	def test_a_datetime_czwartek(self: "TestFormatujTermin") -> None:
		pelna, godzina, krotko = formatuj_termin(CZWARTEK)
		self.assertEqual(pelna, "czwartek, 24 września 2026")
		self.assertEqual(godzina, "14:30")
		self.assertEqual(krotko, "czw. 24.09")

	def test_b_string_pelny_rowny_datetime(self: "TestFormatujTermin") -> None:
		self.assertEqual(formatuj_termin("2026-09-24 14:30:00"), formatuj_termin(CZWARTEK))

	def test_c_string_bez_sekund(self: "TestFormatujTermin") -> None:
		self.assertEqual(formatuj_termin("2026-09-24 14:30"), formatuj_termin(CZWARTEK))

	def test_d_string_sama_data_polnoc(self: "TestFormatujTermin") -> None:
		pelna, godzina, krotko = formatuj_termin("2026-09-24")
		self.assertEqual(pelna, "czwartek, 24 września 2026")
		self.assertEqual(godzina, "00:00")
		self.assertEqual(krotko, "czw. 24.09")

	def test_e_none_daje_trzy_puste(self: "TestFormatujTermin") -> None:
		self.assertEqual(formatuj_termin(None), ("", "", ""))

	def test_f_pusty_string_daje_trzy_puste(self: "TestFormatujTermin") -> None:
		self.assertEqual(formatuj_termin(""), ("", "", ""))

	def test_g_nierozpoznany_string_daje_trzy_puste(self: "TestFormatujTermin") -> None:
		self.assertEqual(formatuj_termin("nie termin"), ("", "", ""))

	def test_h_piatek_inny_dzien_niz_czwartek(self: "TestFormatujTermin") -> None:
		_pelna, _godzina, krotko = formatuj_termin(PIATEK)
		self.assertEqual(krotko, "pt. 25.09")


class TestFormatujDate(unittest.TestCase):
	def test_a_date_obiekt(self: "TestFormatujDate") -> None:
		self.assertEqual(formatuj_date(datetime.date(2026, 9, 30)), "środa, 30 września 2026")

	def test_b_string_data(self: "TestFormatujDate") -> None:
		self.assertEqual(formatuj_date("2026-09-30"), "środa, 30 września 2026")

	def test_c_none_daje_pusty_string(self: "TestFormatujDate") -> None:
		self.assertEqual(formatuj_date(None), "")

	def test_d_pusty_string_daje_pusty_string(self: "TestFormatujDate") -> None:
		self.assertEqual(formatuj_date(""), "")

	def test_e_datetime_obcina_do_daty(self: "TestFormatujDate") -> None:
		self.assertEqual(formatuj_date(datetime.datetime(2026, 9, 30, 8, 0)), "środa, 30 września 2026")


class TestCzyZmienilSieTermin(unittest.TestCase):
	def test_a_none_i_puste_string_rowne(self: "TestCzyZmienilSieTermin") -> None:
		self.assertFalse(czy_zmienil_sie_termin(None, ""))
		self.assertFalse(czy_zmienil_sie_termin("", None))
		self.assertFalse(czy_zmienil_sie_termin(None, None))

	def test_b_ta_sama_chwila_string_i_datetime_rowne(self: "TestCzyZmienilSieTermin") -> None:
		self.assertFalse(czy_zmienil_sie_termin("2026-09-24 14:30:00", CZWARTEK))
		self.assertFalse(czy_zmienil_sie_termin(CZWARTEK, "2026-09-24 14:30:00"))

	def test_c_rozne_godziny_to_zmiana(self: "TestCzyZmienilSieTermin") -> None:
		self.assertTrue(czy_zmienil_sie_termin(CZWARTEK, PIATEK))

	def test_d_z_pustego_na_termin_to_zmiana(self: "TestCzyZmienilSieTermin") -> None:
		self.assertTrue(czy_zmienil_sie_termin(None, CZWARTEK))

	def test_e_z_terminu_na_pusty_to_zmiana_odwolanie(self: "TestCzyZmienilSieTermin") -> None:
		self.assertTrue(czy_zmienil_sie_termin(CZWARTEK, None))

	def test_f_identyczny_string_nie_jest_zmiana(self: "TestCzyZmienilSieTermin") -> None:
		self.assertFalse(czy_zmienil_sie_termin("2026-09-24 14:30:00", "2026-09-24 14:30:00"))


class TestNazwyProduktow(unittest.TestCase):
	def test_a_dwa_znane_tokeny(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow("PV+ME"), "Fotowoltaika, magazyn energii")

	def test_b_jeden_znany_token_bez_zmiany_wielkosci(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow("PC"), "Pompa ciepła")

	def test_c_trzy_tokeny(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow("PV+ME+AUDYT"), "Fotowoltaika, magazyn energii, audyt")

	def test_d_pusty_string_daje_pusty_wynik(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow(""), "")

	def test_e_none_daje_pusty_wynik(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow(None), "")

	def test_f_nieznany_token_bez_zmian_jako_jedyny(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow("XYZ"), "XYZ")

	def test_g_wszystkie_tokeny_maja_etykiety(self: "TestNazwyProduktow") -> None:
		for token, etykieta in ETYKIETY_PRODUKTOW.items():
			self.assertEqual(nazwy_produktow(token), etykieta)

	def test_h_grunt_pod_farme(self: "TestNazwyProduktow") -> None:
		self.assertEqual(nazwy_produktow("GRUNT"), "Grunt pod farmę")


class TestLinkDoMapy(unittest.TestCase):
	def test_a_adres_z_polskimi_znakami_i_przecinkiem(self: "TestLinkDoMapy") -> None:
		link = link_do_mapy("Parkowa 5, 64-100 Leszno")
		self.assertTrue(link.startswith("https://www.google.com/maps/search/?api=1&query="))
		self.assertIn("Parkowa", link)
		self.assertNotIn(" ", link)

	def test_b_pusty_adres_daje_pusty_link(self: "TestLinkDoMapy") -> None:
		self.assertEqual(link_do_mapy(""), "")


class TestSklejAdres(unittest.TestCase):
	def test_a_pelny_adres(self: "TestSklejAdres") -> None:
		self.assertEqual(sklej_adres(LEAD_PELNY), "Parkowa 5, 64-100 Leszno")

	def test_b_bez_numeru_domu(self: "TestSklejAdres") -> None:
		lead = dict(LEAD_PELNY, custom_nr_domu="")
		self.assertEqual(sklej_adres(lead), "Parkowa, 64-100 Leszno")

	def test_c_bez_kodu_pocztowego(self: "TestSklejAdres") -> None:
		lead = dict(LEAD_PELNY, custom_install_postal_code="")
		self.assertEqual(sklej_adres(lead), "Parkowa 5, Leszno")

	def test_d_wszystko_puste_daje_pusty_string(self: "TestSklejAdres") -> None:
		self.assertEqual(sklej_adres(LEAD_MINIMALNY), "")

	def test_e_nie_mutuje_leada(self: "TestSklejAdres") -> None:
		lead = dict(LEAD_PELNY)
		kopia = dict(lead)
		sklej_adres(lead)
		self.assertEqual(lead, kopia)


class TestNazwaPrzydzielajacego(unittest.TestCase):
	def test_a_maskuj_daje_call_center(self: "TestNazwaPrzydzielajacego") -> None:
		self.assertEqual(nazwa_przydzielajacego("Jan Kowalski", maskuj=True), AUTOR_ZASTEPCZY_CC)
		self.assertEqual(nazwa_przydzielajacego("Jan Kowalski", maskuj=True), "Call center")

	def test_b_bez_maskowania_zwraca_pelne_nazwisko(self: "TestNazwaPrzydzielajacego") -> None:
		self.assertEqual(nazwa_przydzielajacego("Jan Kowalski", maskuj=False), "Jan Kowalski")

	def test_c_puste_nazwisko_bez_maskowania(self: "TestNazwaPrzydzielajacego") -> None:
		self.assertEqual(nazwa_przydzielajacego(None, maskuj=False), "")
		self.assertEqual(nazwa_przydzielajacego("", maskuj=False), "")


class TestZbudujPowiadomienieePrzydzialu(unittest.TestCase):
	def test_a_temat_ze_spotkaniem(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy=""
		)
		self.assertEqual(d["subject"], "Spotkanie: Jan Kowalski, czw. 24.09, godz. 14:30")
		self.assertEqual(d["title"], d["subject"])
		self.assertEqual(d["email_header"], "Nowe spotkanie z klientem")
		self.assertEqual(d["description"], d["email_content"])

	def test_b_temat_bez_spotkania(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_MINIMALNY, url=URL, pokaz_przekazujacego=False, przekazujacy=""
		)
		self.assertEqual(d["subject"], "Nowy klient do kontaktu: Anna Nowak")
		self.assertEqual(d["email_header"], "Nowy klient do kontaktu")

	def test_c_temat_bez_bloku_spotkania_nie_ma_slowa_spotkanie_w_tresci(
		self: "TestZbudujPowiadomienieePrzydzialu",
	) -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_MINIMALNY, url=URL, pokaz_przekazujacego=False, przekazujacy=""
		)
		self.assertNotIn("SPOTKANIE", d["email_content"])
		self.assertIn("Termin spotkania nie jest jeszcze ustalony.", d["email_content"])

	def test_d_pokaz_przekazujacego_wstawia_nazwisko(
		self: "TestZbudujPowiadomienieePrzydzialu",
	) -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_PELNY, url=URL, pokaz_przekazujacego=True, przekazujacy="Anna Wiśniewska"
		)
		self.assertIn("Anna Wiśniewska przekazał Ci klienta", d["email_content"])
		self.assertNotIn("call center umówiło", d["email_content"])

	def test_e_bez_pokaz_przekazujacego_tekst_generyczny(
		self: "TestZbudujPowiadomienieePrzydzialu",
	) -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="Anna Wiśniewska"
		)
		self.assertIn("call center umówiło dla Ciebie spotkanie", d["email_content"])
		self.assertNotIn("Anna Wiśniewska", d["email_content"])

	def test_f_escapuje_nazwisko_przekazujacego_ze_znacznikiem(
		self: "TestZbudujPowiadomienieePrzydzialu",
	) -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_PELNY, url=URL, pokaz_przekazujacego=True, przekazujacy="<b>Zły</b> Aktor"
		)
		self.assertNotIn("<b>Zły</b>", d["email_content"])
		self.assertIn("&lt;b&gt;Zły&lt;/b&gt;", d["email_content"])

	def test_g_escapuje_uwagi_z_ampersandem(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		lead = dict(LEAD_PELNY, custom_uwagi_import="Klient & żona pytali o rabat")
		d = zbuduj_powiadomienie_przydzialu(lead, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertIn("Klient &amp; żona pytali o rabat", d["email_content"])
		self.assertNotIn("Klient & żona", d["email_content"])

	def test_h_uwagi_skracane_do_600_znakow(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		lead = dict(LEAD_PELNY, custom_uwagi_import="a" * 700)
		d = zbuduj_powiadomienie_przydzialu(lead, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertIn("a" * 600 + "...", d["email_content"])
		self.assertNotIn("a" * 601, d["email_content"])

	def test_i_krotkie_uwagi_nie_sa_skracane(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertIn("Klient pytał o dofinansowanie i termin montażu.", d["email_content"])
		self.assertNotIn("...", d["email_content"])

	def test_j_puste_wiersze_pomijane(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(
			LEAD_MINIMALNY, url=URL, pokaz_przekazujacego=False, przekazujacy=""
		)
		self.assertNotIn("Telefon", d["email_content"])
		self.assertNotIn("Posiada już", d["email_content"])
		self.assertNotIn("Kolejny kontakt", d["email_content"])
		self.assertNotIn("Uwagi z rozmowy", d["email_content"])

	def test_k_zawiera_url_w_przycisku(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertIn(URL, d["email_content"])

	def test_l_zawiera_link_do_mapy_gdy_adres_znany(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertIn("Pokaż na mapie", d["email_content"])

	def test_m_bez_stylu_tag_nie_wystepuje(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		d = zbuduj_powiadomienie_przydzialu(LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertNotIn("<style", d["email_content"])
		self.assertNotIn("tel:", d["email_content"])

	def test_n_nie_mutuje_leada(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		lead = dict(LEAD_PELNY)
		kopia = dict(lead)
		zbuduj_powiadomienie_przydzialu(lead, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		self.assertEqual(lead, kopia)

	def test_o_zero_myslnikow_em_en(self: "TestZbudujPowiadomienieePrzydzialu") -> None:
		for przekazujacy in ("", "Ktoś Kowalski"):
			for pokaz in (True, False):
				d = zbuduj_powiadomienie_przydzialu(
					LEAD_PELNY, url=URL, pokaz_przekazujacego=pokaz, przekazujacy=przekazujacy
				)
				for wartosc in d.values():
					self.assertIsNone(_DASH_RE.search(wartosc), msg=wartosc)


class TestZbudujPowiadomienieOdebrania(unittest.TestCase):
	def test_a_temat_bez_bloku_spotkania(self: "TestZbudujPowiadomienieOdebrania") -> None:
		d = zbuduj_powiadomienie_odebrania(LEAD_PELNY, url=URL)
		self.assertEqual(d["subject"], "Klient Jan Kowalski został przekazany innemu handlowcowi")
		self.assertEqual(d["email_header"], "Zmiana przydziału")

	def test_b_tresc_bez_zadnych_nazwisk(self: "TestZbudujPowiadomienieOdebrania") -> None:
		d = zbuduj_powiadomienie_odebrania(LEAD_PELNY, url=URL)
		self.assertNotIn("Kowalski", d["email_content"])
		self.assertNotIn(AUTOR_ZASTEPCZY_CC, d["email_content"])

	def test_c_zawiera_url(self: "TestZbudujPowiadomienieOdebrania") -> None:
		d = zbuduj_powiadomienie_odebrania(LEAD_PELNY, url=URL)
		self.assertIn(URL, d["email_content"])

	def test_d_zero_myslnikow(self: "TestZbudujPowiadomienieOdebrania") -> None:
		d = zbuduj_powiadomienie_odebrania(LEAD_PELNY, url=URL)
		for wartosc in d.values():
			self.assertIsNone(_DASH_RE.search(wartosc), msg=wartosc)

	def test_e_nie_mutuje_leada(self: "TestZbudujPowiadomienieOdebrania") -> None:
		lead = dict(LEAD_PELNY)
		kopia = dict(lead)
		zbuduj_powiadomienie_odebrania(lead, url=URL)
		self.assertEqual(lead, kopia)


class TestZbudujPowiadomienieZmianyTerminu(unittest.TestCase):
	def test_a_temat_zmiany_terminu(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=PIATEK,
			pokaz_zmieniajacego=False,
			zmieniajacy="",
		)
		self.assertEqual(d["subject"], "Zmiana terminu: Jan Kowalski, pt. 25.09, godz. 10:00")
		self.assertEqual(d["email_header"], "Zmiana terminu spotkania")

	def test_b_temat_odwolanego_terminu(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=None,
			pokaz_zmieniajacego=False,
			zmieniajacy="",
		)
		self.assertEqual(d["subject"], "Odwołany termin: Jan Kowalski")
		self.assertIn("Termin spotkania został odwołany.", d["email_content"])

	def test_c_nowy_termin_z_pustego_starego(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=None,
			nowy=PIATEK,
			pokaz_zmieniajacego=False,
			zmieniajacy="",
		)
		self.assertEqual(d["subject"], "Zmiana terminu: Jan Kowalski, pt. 25.09, godz. 10:00")
		self.assertNotIn("Poprzedni termin", d["email_content"])

	def test_d_pokaz_zmieniajacego_wstawia_nazwisko(
		self: "TestZbudujPowiadomienieZmianyTerminu",
	) -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=PIATEK,
			pokaz_zmieniajacego=True,
			zmieniajacy="Ewa Zielińska",
		)
		self.assertIn("Ewa Zielińska zmienił termin spotkania z klientem.", d["email_content"])
		self.assertNotIn("call center zmieniło", d["email_content"])

	def test_e_bez_pokaz_zmieniajacego_tekst_generyczny(
		self: "TestZbudujPowiadomienieZmianyTerminu",
	) -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=PIATEK,
			pokaz_zmieniajacego=False,
			zmieniajacy="Ewa Zielińska",
		)
		self.assertIn("call center zmieniło termin spotkania z klientem.", d["email_content"])
		self.assertNotIn("Ewa Zielińska", d["email_content"])

	def test_f_poprzedni_termin_widoczny_w_tabeli(
		self: "TestZbudujPowiadomienieZmianyTerminu",
	) -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=PIATEK,
			pokaz_zmieniajacego=False,
			zmieniajacy="",
		)
		self.assertIn("Poprzedni termin", d["email_content"])
		self.assertIn("czwartek, 24 września 2026, godz. 14:30", d["email_content"])

	def test_g_zawiera_url(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY, url=URL, stary=CZWARTEK, nowy=PIATEK, pokaz_zmieniajacego=False, zmieniajacy=""
		)
		self.assertIn(URL, d["email_content"])

	def test_h_escapuje_nazwisko_zmieniajacego(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		d = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY,
			url=URL,
			stary=CZWARTEK,
			nowy=PIATEK,
			pokaz_zmieniajacego=True,
			zmieniajacy="<i>Zły</i>",
		)
		self.assertNotIn("<i>Zły</i>", d["email_content"])
		self.assertIn("&lt;i&gt;Zły&lt;/i&gt;", d["email_content"])

	def test_i_nie_mutuje_leada(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		lead = dict(LEAD_PELNY)
		kopia = dict(lead)
		zbuduj_powiadomienie_zmiany_terminu(
			lead, url=URL, stary=CZWARTEK, nowy=PIATEK, pokaz_zmieniajacego=False, zmieniajacy=""
		)
		self.assertEqual(lead, kopia)

	def test_j_zero_myslnikow_em_en(self: "TestZbudujPowiadomienieZmianyTerminu") -> None:
		warianty = [
			(CZWARTEK, PIATEK, False, ""),
			(CZWARTEK, None, False, ""),
			(None, PIATEK, True, "Ewa Zielińska"),
		]
		for stary, nowy, pokaz, zmieniajacy in warianty:
			d = zbuduj_powiadomienie_zmiany_terminu(
				LEAD_PELNY, url=URL, stary=stary, nowy=nowy, pokaz_zmieniajacego=pokaz, zmieniajacy=zmieniajacy
			)
			for wartosc in d.values():
				self.assertIsNone(_DASH_RE.search(wartosc), msg=wartosc)


class TestKsztaltZwracanychSlownikow(unittest.TestCase):
	def test_a_wszystkie_trzy_maja_te_same_klucze(self: "TestKsztaltZwracanychSlownikow") -> None:
		oczekiwane = {"subject", "title", "email_header", "email_content", "description"}
		d1 = zbuduj_powiadomienie_przydzialu(LEAD_PELNY, url=URL, pokaz_przekazujacego=False, przekazujacy="")
		d2 = zbuduj_powiadomienie_odebrania(LEAD_PELNY, url=URL)
		d3 = zbuduj_powiadomienie_zmiany_terminu(
			LEAD_PELNY, url=URL, stary=CZWARTEK, nowy=PIATEK, pokaz_zmieniajacego=False, zmieniajacy=""
		)
		for d in (d1, d2, d3):
			self.assertEqual(set(d.keys()), oczekiwane)
			self.assertEqual(d["title"], d["subject"])
			self.assertEqual(d["description"], d["email_content"])


if __name__ == "__main__":
	unittest.main()
