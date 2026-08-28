import unittest

from crm.volteo_leady_import import (
	KLUCZ_HISTORIA,
	KLUCZ_STARE_NOWE,
	deduplikuj,
	mapuj_zainteresowanie,
	normalizuj_date,
	normalizuj_kod,
	normalizuj_telefon,
	normalizuj_wojewodztwo,
	wczytaj_wiersze,
	zbuduj_leada,
)


class TestNormalizujTelefon(unittest.TestCase):
	def test_a_format_48_prefiks(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("48502103270"), "+48502103270")

	def test_b_format_plus48_prefiks(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("+48509859417"), "+48509859417")

	def test_c_format_9_cyfr(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("661531000"), "+48661531000")

	def test_d_format_9_cyfr_z_odstepami(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("608 026 565"), "+48608026565")

	def test_e_uszkodzony_excel_twarde_spacje_i_koncowka_00(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("507\xa0063\xa0129,00"), "+48507063129")

	def test_e2_myslniki_jako_separator(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("604-932-720"), "+48604932720")

	def test_e3_kropki_jako_separator(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("604.932.720"), "+48604932720")

	def test_e4_myslniki_z_prefiksem_48(self: "TestNormalizujTelefon") -> None:
		self.assertEqual(normalizuj_telefon("+48-604-932-720"), "+48604932720")

	def test_f_odrzuca_za_krotki(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon("12345"))

	def test_g_odrzuca_litery(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon("ccc"))
		self.assertIsNone(normalizuj_telefon("501abc123"))

	def test_h_odrzuca_12_cyfr_bez_prefiksu_48(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon("905345514931"))

	def test_i_odrzuca_puste(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon(""))
		self.assertIsNone(normalizuj_telefon("-"))

	def test_j_odrzuca_wiele_numerow_w_jednym_polu(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon("723309923, 782631166"))

	def test_k_odrzuca_wiele_numerow_z_myslnikami_i_tekstem(self: "TestNormalizujTelefon") -> None:
		self.assertIsNone(normalizuj_telefon("733-794-111, tel do syna: 788 406 223"))


class TestNormalizujDate(unittest.TestCase):
	def test_a_format_iso(self: "TestNormalizujDate") -> None:
		self.assertEqual(normalizuj_date("2022-03-10"), "2022-03-10")

	def test_b_format_dd_mm_rrrr(self: "TestNormalizujDate") -> None:
		self.assertEqual(normalizuj_date("17-10-2022"), "2022-10-17")

	def test_c_format_d_m_rrrr(self: "TestNormalizujDate") -> None:
		self.assertEqual(normalizuj_date("4-1-2023"), "2023-01-04")

	def test_d_puste_daje_none(self: "TestNormalizujDate") -> None:
		self.assertIsNone(normalizuj_date(""))
		self.assertIsNone(normalizuj_date("-"))

	def test_e_smieci_daja_none(self: "TestNormalizujDate") -> None:
		self.assertIsNone(normalizuj_date("nie wiadomo kiedy"))

	def test_f_niepoprawna_data_kalendarzowa_daje_none(self: "TestNormalizujDate") -> None:
		self.assertIsNone(normalizuj_date("2022-02-31"))


class TestNormalizujKod(unittest.TestCase):
	def test_a_poprawny_format(self: "TestNormalizujKod") -> None:
		self.assertEqual(normalizuj_kod("62-080"), "62-080")

	def test_b_bez_kreski_daje_none(self: "TestNormalizujKod") -> None:
		self.assertIsNone(normalizuj_kod("62080"))

	def test_c_puste_daje_none(self: "TestNormalizujKod") -> None:
		self.assertIsNone(normalizuj_kod(""))
		self.assertIsNone(normalizuj_kod("-"))

	def test_d_zle_umiejscowiona_kreska_daje_none(self: "TestNormalizujKod") -> None:
		self.assertIsNone(normalizuj_kod("62_080"))


class TestNormalizujWojewodztwo(unittest.TestCase):
	def test_a_kanoniczna_forma_male_litery(self: "TestNormalizujWojewodztwo") -> None:
		self.assertEqual(normalizuj_wojewodztwo("wielkopolskie"), "wielkopolskie")

	def test_b_wielka_litera_normalizuje_sie(self: "TestNormalizujWojewodztwo") -> None:
		self.assertEqual(normalizuj_wojewodztwo("Wielkopolskie"), "wielkopolskie")
		self.assertEqual(normalizuj_wojewodztwo("POMORSKIE"), "pomorskie")

	def test_c_brak_daje_none(self: "TestNormalizujWojewodztwo") -> None:
		self.assertIsNone(normalizuj_wojewodztwo("brak"))

	def test_d_myslnik_daje_none(self: "TestNormalizujWojewodztwo") -> None:
		self.assertIsNone(normalizuj_wojewodztwo("-"))

	def test_e_nieznane_daje_none(self: "TestNormalizujWojewodztwo") -> None:
		self.assertIsNone(normalizuj_wojewodztwo("mazowsze"))


class TestMapujZainteresowanie(unittest.TestCase):
	def test_a_pompa_ciepla(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("PC"), "Pompa ciepła")

	def test_b_fotowoltaika(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("PV"), "Fotowoltaika")

	def test_c_magazyn_energii(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("MGZ"), "Magazyn energii")

	def test_d_zlozenie_pc_plus_mgz(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("PC+MGZ"), "Pompa ciepła + Magazyn energii")

	def test_e_zlozenie_z_ukosnikiem(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("MGZ/PC"), "Magazyn energii + Pompa ciepła")

	def test_f_male_litery_tez_dzialaja(self: "TestMapujZainteresowanie") -> None:
		self.assertEqual(mapuj_zainteresowanie("pv"), "Fotowoltaika")

	def test_g_brak_daje_none(self: "TestMapujZainteresowanie") -> None:
		self.assertIsNone(mapuj_zainteresowanie("brak"))
		self.assertIsNone(mapuj_zainteresowanie("BRAK"))
		self.assertIsNone(mapuj_zainteresowanie("-"))
		self.assertIsNone(mapuj_zainteresowanie(""))

	def test_h_kwota_daje_none(self: "TestMapujZainteresowanie") -> None:
		self.assertIsNone(mapuj_zainteresowanie("300"))

	def test_i_wolny_tekst_daje_none(self: "TestMapujZainteresowanie") -> None:
		self.assertIsNone(mapuj_zainteresowanie("zużywa 720 kw na 2 miesiące"))


class TestWczytajWiersze(unittest.TestCase):
	def test_a_podstawowe_wczytanie(self: "TestWczytajWiersze") -> None:
		tekst = "Data,Imię,Numer\n2022-03-10,Jan,+48502103270\n"
		wiersze = wczytaj_wiersze(tekst)
		self.assertEqual(len(wiersze), 1)
		self.assertEqual(wiersze[0]["Imię"], "Jan")
		self.assertEqual(wiersze[0]["Numer"], "+48502103270")

	def test_b_pusty_csv_daje_pusta_liste(self: "TestWczytajWiersze") -> None:
		self.assertEqual(wczytaj_wiersze("Data,Imię,Numer\n"), [])

	def test_c_dwie_puste_kolumny_naglowka_rozdzielone_pozycyjnie(self: "TestWczytajWiersze") -> None:
		# Odwzorowuje realny kształt pliku źródłowego: pusta kolumna zaraz po
		# Uwagi niesie historię wyniku szansy, pusta kolumna na końcu wiersza
		# niesie znacznik STARE/NOWE. Goły csv.DictReader zderzyłby oba klucze
		# ("") i po cichu zgubił historię — to sprawdza, że tak się NIE dzieje.
		tekst = (
			"Data,Imię,Numer,Uwagi,,ŹRÓDŁO,\n"
			"2022-03-10,Jan,+48502103270,Lead z formularza,wygrana,SD,STARE\n"
		)
		wiersze = wczytaj_wiersze(tekst)
		self.assertEqual(len(wiersze), 1)
		self.assertEqual(wiersze[0][KLUCZ_HISTORIA], "wygrana")
		self.assertEqual(wiersze[0][KLUCZ_STARE_NOWE], "STARE")
		self.assertNotEqual(wiersze[0][KLUCZ_HISTORIA], wiersze[0][KLUCZ_STARE_NOWE])

	def test_d_inna_liczba_pustych_kolumn_niz_dwie_zglasza_blad(self: "TestWczytajWiersze") -> None:
		tekst = "Data,Imię,Numer,\n2022-03-10,Jan,+48502103270,coś\n"
		with self.assertRaises(ValueError):
			wczytaj_wiersze(tekst)


def _wiersz(**nadpisania: str) -> dict[str, str]:
	"""Buduje wiersz CSV testowy z sensownymi domyślnymi wartościami, nadpisując tylko podane pola."""
	bazowy: dict[str, str] = {
		"Data": "2022-03-10",
		"Imię": "Jan",
		"Nazwisko": "Kowalski",
		"Numer": "+48502103270",
		"Województwo": "wielkopolskie",
		"Powiat": "-",
		"Miasto": "Poznań",
		"Kod pocztowy": "62-080",
		"Ulica": "-",
		"Rachunek na mc": "PV",
		"Typ dachu": "-",
		"Pokrycie": "-",
		"Uwagi": "-",
		KLUCZ_HISTORIA: "-",
		KLUCZ_STARE_NOWE: "-",
		"ŹRÓDŁO": "SD",
	}
	bazowy.update(nadpisania)
	return bazowy


class TestDeduplikuj(unittest.TestCase):
	def test_a_wiersz_bez_poprawnego_telefonu_odpada(self: "TestDeduplikuj") -> None:
		wiersze = [_wiersz(Numer="za krotki")]
		self.assertEqual(deduplikuj(wiersze), {})

	def test_b_pojedynczy_wiersz_trafia_do_wyniku(self: "TestDeduplikuj") -> None:
		wynik = deduplikuj([_wiersz()])
		self.assertIn("+48502103270", wynik)
		self.assertEqual(wynik["+48502103270"]["imie"], "Jan")

	def test_c_ranking_po_najnowszej_dacie(self: "TestDeduplikuj") -> None:
		stary = _wiersz(Data="2020-01-01", Imię="Stary", ŹRÓDŁO="SD")
		nowy = _wiersz(Data="2023-06-15", Imię="Nowy", ŹRÓDŁO="CC")
		wynik = deduplikuj([stary, nowy])
		self.assertEqual(wynik["+48502103270"]["imie"], "Nowy")

	def test_d_remis_daty_rozstrzyga_kompletnosc(self: "TestDeduplikuj") -> None:
		niekompletny = _wiersz(Data="2022-01-01", Imię="Niepelny", Ulica="-", ŹRÓDŁO="SD")
		kompletny = _wiersz(
			Data="2022-01-01", Imię="Pelny", Ulica="Słoneczna 2", ŹRÓDŁO="CC"
		)
		wynik = deduplikuj([niekompletny, kompletny])
		self.assertEqual(wynik["+48502103270"]["imie"], "Pelny")

	def test_e_unia_zrodel_dla_numeru_w_dwoch_zrodlach(self: "TestDeduplikuj") -> None:
		a = _wiersz(ŹRÓDŁO="SD")
		b = _wiersz(ŹRÓDŁO="CC")
		wynik = deduplikuj([a, b])
		self.assertEqual(wynik["+48502103270"]["zrodlo"], "SD+CC")

	def test_f_konkatenacja_uwag_z_tagami_zrodel(self: "TestDeduplikuj") -> None:
		a = _wiersz(ŹRÓDŁO="SD", Uwagi="Lead z formularza")
		b = _wiersz(ŹRÓDŁO="CC", Uwagi="Telefon od klienta")
		wynik = deduplikuj([a, b])
		uwagi = wynik["+48502103270"]["uwagi"]
		self.assertIn("[SD] Lead z formularza", uwagi)
		self.assertIn("[CC] Telefon od klienta", uwagi)

	def test_g_typ_dachu_pokrycie_i_stare_nowe_skladaja_sie_do_uwag(self: "TestDeduplikuj") -> None:
		wiersz = _wiersz(
			Uwagi="-",
			**{"Typ dachu": "dwuspadowy", "Pokrycie": "dachówka", KLUCZ_STARE_NOWE: "STARE"},
		)
		wynik = deduplikuj([wiersz])
		uwagi = wynik["+48502103270"]["uwagi"]
		self.assertIn("Typ dachu: dwuspadowy", uwagi)
		self.assertIn("Pokrycie: dachówka", uwagi)
		self.assertIn("STARE", uwagi)

	def test_h2_historia_wyniku_trafia_do_uwag_z_tagiem(self: "TestDeduplikuj") -> None:
		wiersz = _wiersz(**{KLUCZ_HISTORIA: "wygrana"})
		wynik = deduplikuj([wiersz])
		self.assertIn("[HISTORIA] wygrana", wynik["+48502103270"]["uwagi"])

	def test_h3_historia_status_nie_wplywa_na_status_leada(self: "TestDeduplikuj") -> None:
		wiersz = _wiersz(**{KLUCZ_HISTORIA: "przegrana"})
		wynik = deduplikuj([wiersz])
		lead = zbuduj_leada(wynik["+48502103270"])
		self.assertEqual(lead["status"], "Nowy")
		self.assertIn("[HISTORIA] przegrana", lead["custom_uwagi_import"])

	def test_h4_powtorzona_historia_w_grupie_deduplikuje_sie(self: "TestDeduplikuj") -> None:
		a = _wiersz(ŹRÓDŁO="SD", **{KLUCZ_HISTORIA: "wygrana"})
		b = _wiersz(ŹRÓDŁO="CC", **{KLUCZ_HISTORIA: "wygrana"})
		wynik = deduplikuj([a, b])
		uwagi = wynik["+48502103270"]["uwagi"]
		self.assertEqual(uwagi.count("[HISTORIA] wygrana"), 1)

	def test_h5_rozne_wartosci_historii_w_grupie_obie_widoczne(self: "TestDeduplikuj") -> None:
		a = _wiersz(ŹRÓDŁO="SD", Data="2020-01-01", **{KLUCZ_HISTORIA: "przegrana"})
		b = _wiersz(ŹRÓDŁO="CC", Data="2023-01-01", **{KLUCZ_HISTORIA: "wygrana"})
		wynik = deduplikuj([a, b])
		uwagi = wynik["+48502103270"]["uwagi"]
		self.assertIn("[HISTORIA] przegrana", uwagi)
		self.assertIn("[HISTORIA] wygrana", uwagi)

	def test_h_rozne_telefony_daja_rozne_grupy(self: "TestDeduplikuj") -> None:
		a = _wiersz(Numer="+48502103270")
		b = _wiersz(Numer="+48609116693")
		wynik = deduplikuj([a, b])
		self.assertEqual(len(wynik), 2)


class TestZbudujLeada(unittest.TestCase):
	def test_a_fallback_imienia_gdy_puste(self: "TestZbudujLeada") -> None:
		rekord = {"telefon": "+48502103270", "imie": ""}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["first_name"], "Kontakt")

	def test_b_brak_lead_owner(self: "TestZbudujLeada") -> None:
		rekord = {"telefon": "+48502103270", "imie": "Jan"}
		lead = zbuduj_leada(rekord)
		self.assertNotIn("lead_owner", lead)

	def test_c_mapowanie_kolumn(self: "TestZbudujLeada") -> None:
		rekord = {
			"telefon": "+48502103270",
			"imie": "Jan",
			"nazwisko": "Kowalski",
			"wojewodztwo": "wielkopolskie",
			"powiat": "poznański",
			"miasto": "Poznań",
			"kod_pocztowy": "62-080",
			"ulica": "Słoneczna 2",
			"rachunek_na_mc": "PC+MGZ",
			"data": "2022-03-10",
			"zrodlo": "SD+CC",
			"uwagi": "[SD] Lead z formularza",
		}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["first_name"], "Jan")
		self.assertEqual(lead["last_name"], "Kowalski")
		self.assertEqual(lead["mobile_no"], "+48502103270")
		self.assertEqual(lead["status"], "Nowy")
		self.assertEqual(lead["business_line"], "D2D")
		self.assertEqual(lead["custom_install_address"], "Słoneczna 2")
		self.assertEqual(lead["custom_install_city"], "Poznań")
		self.assertEqual(lead["custom_install_postal_code"], "62-080")
		self.assertEqual(lead["custom_powiat"], "poznański")
		self.assertEqual(lead["custom_voivodeship"], "wielkopolskie")
		self.assertEqual(lead["custom_import_source"], "SD+CC")
		self.assertEqual(lead["custom_import_date"], "2022-03-10")
		self.assertEqual(lead["custom_uwagi_import"], "[SD] Lead z formularza")
		self.assertEqual(lead["custom_product_interest"], "Pompa ciepła + Magazyn energii")

	def test_d_status_zawsze_nowy_i_linia_zawsze_d2d(self: "TestZbudujLeada") -> None:
		rekord = {"telefon": "+48502103270", "imie": "Jan"}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["status"], "Nowy")
		self.assertEqual(lead["business_line"], "D2D")


if __name__ == "__main__":
	unittest.main()
