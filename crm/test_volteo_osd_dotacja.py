import unittest

from crm.volteo_osd_dotacja import (
	ETYKIETY_KART,
	KOLORY,
	POLE,
	STATUSY,
	ZAKLADKI,
	tekst_sladu_statusu,
)


class TestZakladkiIPole(unittest.TestCase):
	def test_a_zakladki_sa_dokladnie_osd_i_dotacja(self: "TestZakladkiIPole") -> None:
		self.assertEqual(ZAKLADKI, ("OSD", "Dotacja"))

	def test_b_pole_ma_wpis_dla_kazdej_zakladki(self: "TestZakladkiIPole") -> None:
		self.assertEqual(set(POLE.keys()), set(ZAKLADKI))

	def test_c_pole_fieldnames(self: "TestZakladkiIPole") -> None:
		self.assertEqual(POLE["OSD"], "custom_status_osd")
		self.assertEqual(POLE["Dotacja"], "custom_status_dotacja")


class TestStatusy(unittest.TestCase):
	def test_a_statusy_ma_wpis_dla_kazdej_zakladki(self: "TestStatusy") -> None:
		self.assertEqual(set(STATUSY.keys()), set(ZAKLADKI))

	def test_b_kazda_krotka_zaczyna_sie_od_nie_rozpoczeto(self: "TestStatusy") -> None:
		for zakladka in ZAKLADKI:
			self.assertEqual(STATUSY[zakladka][0], "Nie rozpoczęto")

	def test_c_pusty_string_nigdy_nie_jest_czlonkiem_zadnej_krotki(self: "TestStatusy") -> None:
		for zakladka in ZAKLADKI:
			self.assertNotIn("", STATUSY[zakladka])

	def test_d_osd_szesc_statusow_w_kolejnosci(self: "TestStatusy") -> None:
		self.assertEqual(
			STATUSY["OSD"],
			(
				"Nie rozpoczęto",
				"Zgłoszenie wysłane",
				"Uwagi OSD",
				"Umowa przyłączeniowa",
				"Licznik wymieniony",
				"Zakończone",
			),
		)

	def test_e_dotacja_szesc_statusow_w_kolejnosci(self: "TestStatusy") -> None:
		self.assertEqual(
			STATUSY["Dotacja"],
			(
				"Nie rozpoczęto",
				"Wniosek złożony",
				"Uzupełnienie",
				"Decyzja pozytywna",
				"Wypłacona",
				"Odrzucona",
			),
		)

	def test_f_zadna_wartosc_sie_nie_powtarza_w_krotce(self: "TestStatusy") -> None:
		for zakladka in ZAKLADKI:
			wartosci = STATUSY[zakladka]
			self.assertEqual(len(wartosci), len(set(wartosci)))


class TestKolory(unittest.TestCase):
	def test_a_kolory_ma_wpis_dla_kazdej_zakladki(self: "TestKolory") -> None:
		self.assertEqual(set(KOLORY.keys()), set(ZAKLADKI))

	def test_b_kazda_wartosc_statusu_ma_dokladnie_jeden_kolor(self: "TestKolory") -> None:
		for zakladka in ZAKLADKI:
			self.assertEqual(set(KOLORY[zakladka].keys()), set(STATUSY[zakladka]))

	def test_c_nie_rozpoczeto_jest_zawsze_gray(self: "TestKolory") -> None:
		for zakladka in ZAKLADKI:
			self.assertEqual(KOLORY[zakladka]["Nie rozpoczęto"], "gray")

	def test_d_statusy_w_trakcie_osd_sa_niebieskie(self: "TestKolory") -> None:
		for status in ("Zgłoszenie wysłane", "Uwagi OSD", "Umowa przyłączeniowa", "Licznik wymieniony"):
			self.assertEqual(KOLORY["OSD"][status], "blue")

	def test_e_statusy_w_trakcie_dotacja_sa_niebieskie(self: "TestKolory") -> None:
		for status in ("Wniosek złożony", "Uzupełnienie"):
			self.assertEqual(KOLORY["Dotacja"][status], "blue")

	def test_f_stany_terminalne_zielone(self: "TestKolory") -> None:
		self.assertEqual(KOLORY["OSD"]["Zakończone"], "green")
		self.assertEqual(KOLORY["Dotacja"]["Wypłacona"], "green")

	def test_g_decyzja_pozytywna_jest_lime(self: "TestKolory") -> None:
		self.assertEqual(KOLORY["Dotacja"]["Decyzja pozytywna"], "lime")

	def test_h_odrzucona_jest_czerwona(self: "TestKolory") -> None:
		self.assertEqual(KOLORY["Dotacja"]["Odrzucona"], "red")


class TestEtykietyKart(unittest.TestCase):
	def test_a_etykiety_kart_ma_wpis_dla_kazdej_zakladki(self: "TestEtykietyKart") -> None:
		self.assertEqual(set(ETYKIETY_KART.keys()), set(ZAKLADKI))

	def test_b_etykiety_dokladne(self: "TestEtykietyKart") -> None:
		self.assertEqual(ETYKIETY_KART["OSD"], "Status OSD")
		self.assertEqual(ETYKIETY_KART["Dotacja"], "Status dotacji")


class TestTekstSladuStatusu(unittest.TestCase):
	def test_a_osd_zmiana_ze_strzalka(self: "TestTekstSladuStatusu") -> None:
		self.assertEqual(
			tekst_sladu_statusu("OSD", "Zgłoszenie wysłane", "Zakończone"),
			"status OSD: Zgłoszenie wysłane → Zakończone",
		)

	def test_b_osd_pierwsze_ustawienie_stary_puste(self: "TestTekstSladuStatusu") -> None:
		self.assertEqual(
			tekst_sladu_statusu("OSD", "", "Zgłoszenie wysłane"),
			"ustawiono status OSD: Zgłoszenie wysłane",
		)

	def test_c_osd_pierwsze_ustawienie_stary_none(self: "TestTekstSladuStatusu") -> None:
		self.assertEqual(
			tekst_sladu_statusu("OSD", None, "Zgłoszenie wysłane"),
			"ustawiono status OSD: Zgłoszenie wysłane",
		)

	def test_d_dotacja_zmiana_ze_strzalka_uzywa_dopelniacza(self: "TestTekstSladuStatusu") -> None:
		self.assertEqual(
			tekst_sladu_statusu("Dotacja", "Wniosek złożony", "Decyzja pozytywna"),
			"status dotacji: Wniosek złożony → Decyzja pozytywna",
		)

	def test_e_dotacja_pierwsze_ustawienie(self: "TestTekstSladuStatusu") -> None:
		self.assertEqual(
			tekst_sladu_statusu("Dotacja", None, "Wniosek złożony"),
			"ustawiono status dotacji: Wniosek złożony",
		)

	def test_f_nieznana_zakladka_rzuca_value_error(self: "TestTekstSladuStatusu") -> None:
		with self.assertRaises(ValueError):
			tekst_sladu_statusu("Umowa", None, "cokolwiek")


if __name__ == "__main__":
	unittest.main()
