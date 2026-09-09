import unittest

from crm.volteo_leady_import import (
	KLUCZ_HISTORIA,
	KLUCZ_STARE_NOWE,
	deduplikuj,
	mapuj_zainteresowanie,
	normalizuj_date,
	normalizuj_kod,
	normalizuj_produkty,
	normalizuj_telefon,
	normalizuj_wojewodztwo,
	rozbij_adres,
	rozdziel_imie_nazwisko,
	status_zrodla_z_uwag,
	wczytaj_wiersze,
	zasady_z_uwag,
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


class TestNormalizujProdukty(unittest.TestCase):
	def test_a_pojedynczy_token_z_product_interest(self: "TestNormalizujProdukty") -> None:
		self.assertEqual(normalizuj_produkty("Fotowoltaika", ""), "PV")

	def test_b_zlozenie_z_product_interest_zachowuje_kanoniczna_kolejnosc(
		self: "TestNormalizujProdukty",
	) -> None:
		# "Pompa ciepła + Fotowoltaika" -> mimo kolejnosci w tekscie, wynik to PV+PC
		# (kanoniczna kolejnosc KOLEJNOSC_PRODUKTOW, nie kolejnosc wystapienia).
		self.assertEqual(normalizuj_produkty("Pompa ciepła + Fotowoltaika", ""), "PV+PC")

	def test_c_magazyn_energii(self: "TestNormalizujProdukty") -> None:
		self.assertEqual(normalizuj_produkty("Magazyn energii", ""), "ME")

	def test_d_fraza_arago_z_uwag_piec_na_pellet(self: "TestNormalizujProdukty") -> None:
		self.assertEqual(normalizuj_produkty("", "klient ma piec na pellet od 2019"), "PP")

	def test_e_fraza_arago_termomodernizacja_i_rekuperacja(self: "TestNormalizujProdukty") -> None:
		wynik = normalizuj_produkty("", "termomodernizacja, rekuperacja")
		self.assertEqual(wynik, "TERMO+REKU")

	def test_f_audyt_okna_grunt(self: "TestNormalizujProdukty") -> None:
		wynik = normalizuj_produkty("", "audyt energetyczny wykonany, okna i drzwi wymienione, dzierżawa gruntów rozważana")
		self.assertEqual(wynik, "AUDYT+OKNA+GRUNT")

	def test_g_lacza_product_interest_i_uwagi_naraz(self: "TestNormalizujProdukty") -> None:
		wynik = normalizuj_produkty("Fotowoltaika + Pompa ciepła", "rekuperacja")
		self.assertEqual(wynik, "PV+PC+REKU")

	def test_h_wszystkie_dziewiec_naraz_w_kanonicznej_kolejnosci(self: "TestNormalizujProdukty") -> None:
		wynik = normalizuj_produkty(
			"Magazyn energii + Fotowoltaika + Pompa ciepła",
			"piec na pellet, termomodernizacja, rekuperacja, audyt energetyczny, "
			"okna i drzwi, dzierżawa gruntów",
		)
		self.assertEqual(wynik, "PV+ME+PC+PP+AUDYT+TERMO+REKU+OKNA+GRUNT")

	def test_i_puste_daje_pusty_string(self: "TestNormalizujProdukty") -> None:
		self.assertEqual(normalizuj_produkty("", ""), "")

	def test_j_nieznana_fraza_pomijana_bez_wyjatku(self: "TestNormalizujProdukty") -> None:
		# "klimatyzacja" nie jest zadnym z 9 kanonicznych tokenow - ma zostac po
		# prostu pominieta, bez wyjatku, dokladnie jak nierozpoznany token w
		# mapuj_zainteresowanie.
		wynik = normalizuj_produkty("", "klient chce klimatyzację")
		self.assertEqual(wynik, "")

	def test_k_nieznana_fraza_obok_znanej_zostaje_tylko_znana(self: "TestNormalizujProdukty") -> None:
		wynik = normalizuj_produkty("", "klimatyzacja i rekuperacja")
		self.assertEqual(wynik, "REKU")

	def test_l_male_i_wielkie_litery_bez_znaczenia(self: "TestNormalizujProdukty") -> None:
		self.assertEqual(normalizuj_produkty("FOTOWOLTAIKA", ""), "PV")


class TestStatusZrodlaZUwag(unittest.TestCase):
	def test_a_historia_wygrana(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("[HISTORIA] wygrana", "SD"), "Wygrana")

	def test_b_historia_przegrana(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("[HISTORIA] przegrana", "SD"), "Przegrana")

	def test_c_historia_nieaktualna(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("[HISTORIA] nieaktualna", "SD"), "Nieaktualna")

	def test_d_historia_otwarta_daje_potencjal(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("[HISTORIA] otwarta", "SD"), "Potencjał")

	def test_e_kilka_wpisow_priorytet_wygrana_ponad_potencjal(self: "TestStatusZrodlaZUwag") -> None:
		uwagi = "[HISTORIA] otwarta | [HISTORIA] wygrana"
		self.assertEqual(status_zrodla_z_uwag(uwagi, "SD"), "Wygrana")

	def test_f_kilka_wpisow_priorytet_potencjal_ponad_przegrana(self: "TestStatusZrodlaZUwag") -> None:
		uwagi = "[HISTORIA] przegrana | [HISTORIA] otwarta"
		self.assertEqual(status_zrodla_z_uwag(uwagi, "SD"), "Potencjał")

	def test_g_kilka_wpisow_priorytet_przegrana_ponad_nieaktualna(self: "TestStatusZrodlaZUwag") -> None:
		uwagi = "[HISTORIA] nieaktualna | [HISTORIA] przegrana"
		self.assertEqual(status_zrodla_z_uwag(uwagi, "SD"), "Przegrana")

	def test_h_brak_historii_zrodlo_cc_daje_potencjal(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("", "CC"), "Potencjał")

	def test_i_brak_historii_zrodlo_sd_daje_potencjal(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("", "SD"), "Potencjał")

	def test_j_brak_historii_zrodlo_unia_sd_cc_daje_potencjal(self: "TestStatusZrodlaZUwag") -> None:
		self.assertEqual(status_zrodla_z_uwag("", "SD+CC"), "Potencjał")

	def test_k_brak_historii_zrodlo_arg_daje_none(self: "TestStatusZrodlaZUwag") -> None:
		self.assertIsNone(status_zrodla_z_uwag("", "ARG"))

	def test_l_zupelnie_puste_daje_none(self: "TestStatusZrodlaZUwag") -> None:
		self.assertIsNone(status_zrodla_z_uwag("", ""))


class TestZasadyZUwag(unittest.TestCase):
	def test_a_token_nowe(self: "TestZasadyZUwag") -> None:
		self.assertEqual(zasady_z_uwag("[SD] notatka, NOWE"), "Nowe zasady")

	def test_b_token_stare(self: "TestZasadyZUwag") -> None:
		self.assertEqual(zasady_z_uwag("[SD] notatka, STARE"), "Stare zasady")

	def test_c_male_litery_tez_dzialaja(self: "TestZasadyZUwag") -> None:
		self.assertEqual(zasady_z_uwag("[SD] notatka, nowe"), "Nowe zasady")

	def test_d_brak_tokenu_daje_none(self: "TestZasadyZUwag") -> None:
		self.assertIsNone(zasady_z_uwag("[SD] zwykla notatka bez znacznika"))

	def test_e_puste_daje_none(self: "TestZasadyZUwag") -> None:
		self.assertIsNone(zasady_z_uwag(""))

	def test_f_oba_tokeny_naraz_sprzeczne_daje_none(self: "TestZasadyZUwag") -> None:
		uwagi = "[SD] notatka, STARE | [ARG] notatka, NOWE"
		self.assertIsNone(zasady_z_uwag(uwagi))

	def test_g_slowo_zawierajace_nowe_jako_podciag_nie_lapie_sie(self: "TestZasadyZUwag") -> None:
		# "odnowe" zawiera "nowe" jako podciag - dopasowanie ma byc CALYM slowem.
		self.assertIsNone(zasady_z_uwag("planuje odnowę dachu"))


class TestRozbijAdres(unittest.TestCase):
	def test_a_ulica_z_numerem(self: "TestRozbijAdres") -> None:
		self.assertEqual(rozbij_adres("Kwiatowa 19", "Poznań"), ("Kwiatowa", "19"))

	def test_b_numer_z_litera(self: "TestRozbijAdres") -> None:
		self.assertEqual(rozbij_adres("Kwiatowa 19A", "Poznań"), ("Kwiatowa", "19A"))

	def test_c_numer_z_ukosnikiem(self: "TestRozbijAdres") -> None:
		self.assertEqual(rozbij_adres("Polna 5/2", "Poznań"), ("Polna", "5/2"))

	def test_d_wieloczlonowa_nazwa_ulicy(self: "TestRozbijAdres") -> None:
		self.assertEqual(
			rozbij_adres("Aleje Jerozolimskie 120", "Warszawa"), ("Aleje Jerozolimskie", "120")
		)

	def test_e_wies_bez_ulicy_sam_numer_bierze_miasto(self: "TestRozbijAdres") -> None:
		# reguła "Zbożowo 5, 64-300 Zbożowo" z issue ops#92
		self.assertEqual(rozbij_adres("5", "Zbożowo"), ("Zbożowo", "5"))

	def test_f_sam_numer_z_litera_bierze_miasto(self: "TestRozbijAdres") -> None:
		self.assertEqual(rozbij_adres("5A", "Zbożowo"), ("Zbożowo", "5A"))

	def test_g_sam_numer_bez_miasta_nierozpoznane(self: "TestRozbijAdres") -> None:
		self.assertIsNone(rozbij_adres("5", ""))

	def test_h_brak_liczby_na_koncu_nierozpoznane(self: "TestRozbijAdres") -> None:
		self.assertIsNone(rozbij_adres("Rynek", "Kraków"))

	def test_i_puste_nierozpoznane(self: "TestRozbijAdres") -> None:
		self.assertIsNone(rozbij_adres("", "Kraków"))
		self.assertIsNone(rozbij_adres("   ", "Kraków"))

	def test_j_juz_sama_nazwa_ulicy_z_myslnikiem_bez_numeru_nierozpoznane(
		self: "TestRozbijAdres",
	) -> None:
		self.assertIsNone(rozbij_adres("Plac Wolności", "Poznań"))


class TestRozdzielImieNazwisko(unittest.TestCase):
	def test_a_nazwisko_juz_obecne_bez_zmian(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(rozdziel_imie_nazwisko("Adam", "Banik"), ("Adam", "Banik"))

	def test_b_myslnik_jako_nazwisko_traktowany_jak_puste(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(rozdziel_imie_nazwisko("Adam Banik", "-"), ("Adam", "Banik"))

	def test_c_dwa_slowa_dziela_sie_pol_na_pol(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(rozdziel_imie_nazwisko("Adam Banik", ""), ("Adam", "Banik"))

	def test_d_trzy_slowa_drugie_imie_trafia_do_nazwiska(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("Agnieszka Katarzyna Marciniak", ""),
			("Agnieszka", "Katarzyna Marciniak"),
		)

	def test_e_trzy_slowa_podwojne_nazwisko_zostaje_razem(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("Aleksandra Ratajczak Witkowska", ""),
			("Aleksandra", "Ratajczak Witkowska"),
		)

	def test_f_partykula_zostaje_w_calosci_w_nazwisku(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("Alicja de Groot", ""),
			("Alicja", "de Groot"),
		)

	def test_g_firma_ze_spolka_nie_jest_dzielona(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("DARK TRADE SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ", ""),
			("DARK TRADE SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ", ""),
		)

	def test_h_firma_hotel_nie_jest_dzielona(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("APOLLO HISTORIC HOTEL", ""),
			("APOLLO HISTORIC HOTEL", ""),
		)

	def test_i_firma_skrot_sp_nie_jest_dzielona(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("Kowalski Sp. z o.o.", ""),
			("Kowalski Sp. z o.o.", ""),
		)

	def test_j_firma_handlowa_prefiks_nie_jest_dzielona(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(
			rozdziel_imie_nazwisko("Firma Handlowa Dana", ""),
			("Firma Handlowa Dana", ""),
		)

	def test_k_jednowyrazowe_imie_bez_zmian(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(rozdziel_imie_nazwisko("Jan", ""), ("Jan", ""))

	def test_l_puste_oba_pola(self: "TestRozdzielImieNazwisko") -> None:
		self.assertEqual(rozdziel_imie_nazwisko("", ""), ("", ""))
		self.assertEqual(rozdziel_imie_nazwisko("-", "-"), ("", ""))


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

	def test_m_preferuje_rozdzielona_wersje_imienia_mimo_gorszego_rankingu_daty(
		self: "TestDeduplikuj",
	) -> None:
		# ops#30: 333 grupy telefonu maja w CSV obie wersje - sklejona I rozdzielona.
		# Wiersz z NOWSZA data (ogolny zwyciezca rankingu) niesie sklejone imie;
		# starszy wiersz niesie juz rozdzielone imie+nazwisko. Nazwisko/imie
		# musza przyjsc z tego drugiego, mimo ze przegrywa ogolny ranking.
		sklejony_nowszy = _wiersz(
			Data="2023-06-15", Imię="Adam Banik", Nazwisko="-", ŹRÓDŁO="ARG"
		)
		rozdzielony_starszy = _wiersz(
			Data="2020-01-01", Imię="Adam", Nazwisko="Banik", ŹRÓDŁO="SD"
		)
		wynik = deduplikuj([sklejony_nowszy, rozdzielony_starszy])
		rekord = wynik["+48502103270"]
		self.assertEqual(rekord["imie"], "Adam")
		self.assertEqual(rekord["nazwisko"], "Banik")
		# reszta pol (Data) nadal pochodzi z OGOLNEGO zwyciezcy - rankingi sa niezalezne.
		self.assertEqual(rekord["data"], "2023-06-15")

	def test_n_brak_rozdzielonej_wersji_w_grupie_zostaje_sklejone(self: "TestDeduplikuj") -> None:
		a = _wiersz(Data="2020-01-01", Imię="Adam Banik", Nazwisko="-", ŹRÓDŁO="SD")
		b = _wiersz(Data="2023-06-15", Imię="Adam Banik", Nazwisko="-", ŹRÓDŁO="ARG")
		wynik = deduplikuj([a, b])
		rekord = wynik["+48502103270"]
		self.assertEqual(rekord["imie"], "Adam Banik")
		self.assertEqual(rekord["nazwisko"], "")

	def test_o_nr_domu_pochodzi_od_tego_samego_zwyciezcy_co_ulica(self: "TestDeduplikuj") -> None:
		# issue ops#92: arkusz z osobną kolumną "Nr domu" (nowszy format) - musi
		# przyjść z TEGO SAMEGO wiersza co "Ulica" (ogólny zwycięzca rankingu).
		wiersz = _wiersz(Ulica="Kwiatowa", **{"Nr domu": "19A"})
		wynik = deduplikuj([wiersz])
		rekord = wynik["+48502103270"]
		self.assertEqual(rekord["ulica"], "Kwiatowa")
		self.assertEqual(rekord["nr_domu"], "19A")

	def test_p_brak_kolumny_nr_domu_daje_pusty_string(self: "TestDeduplikuj") -> None:
		# stary format arkusza (bez kolumny "Nr domu") - klucz musi istnieć i być pusty,
		# nie brakujący, żeby zbuduj_leada mógł bezpiecznie użyć .get().
		wynik = deduplikuj([_wiersz()])
		self.assertEqual(wynik["+48502103270"]["nr_domu"], "")


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

	def test_e_sklejone_imie_z_dedupu_wychodzi_rozdzielone(self: "TestZbudujLeada") -> None:
		# ops#30 end-to-end: deduplikuj() zostawia sklejone "Adam Banik" w polu
		# imie (Nazwisko puste w calej grupie) - zbuduj_leada musi je rozdzielic.
		rekord = {"telefon": "+48502103270", "imie": "Adam Banik", "nazwisko": ""}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["first_name"], "Adam")
		self.assertEqual(lead["last_name"], "Banik")

	def test_f_firma_sklejona_zostaje_calosc_w_first_name(self: "TestZbudujLeada") -> None:
		rekord = {
			"telefon": "+48502103270",
			"imie": "DARK TRADE SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
			"nazwisko": "",
		}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["first_name"], "DARK TRADE SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ")
		self.assertEqual(lead["last_name"], "")

	def test_g_produkty_status_zrodla_zasady_koniec_do_konca(self: "TestZbudujLeada") -> None:
		# issue ops#91 - trzy nowe pola strukturalne wyprowadzone z product_interest
		# (rachunek_na_mc) i uwagi (uwagi z [HISTORIA]/STARE-NOWE) razem.
		rekord = {
			"telefon": "+48502103270",
			"imie": "Jan",
			"rachunek_na_mc": "PC",
			"uwagi": "[SD] notatka, rekuperacja, NOWE | [HISTORIA] wygrana",
			"zrodlo": "SD",
		}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["custom_posiadane_produkty"], "PC+REKU")
		self.assertEqual(lead["custom_status_zrodla"], "Wygrana")
		self.assertEqual(lead["custom_zasady_dotacji"], "Nowe zasady")

	def test_h_brak_danych_trzy_nowe_pola_daja_none(self: "TestZbudujLeada") -> None:
		rekord = {"telefon": "+48502103270", "imie": "Jan", "zrodlo": "ARG"}
		lead = zbuduj_leada(rekord)
		self.assertIsNone(lead["custom_posiadane_produkty"])
		self.assertIsNone(lead["custom_status_zrodla"])
		self.assertIsNone(lead["custom_zasady_dotacji"])

	def test_i_nr_domu_juz_osobno_uzyty_wprost(self: "TestZbudujLeada") -> None:
		# issue ops#92 - arkusz nowego formatu z kolumną "Nr domu" osobno.
		rekord = {
			"telefon": "+48502103270",
			"imie": "Jan",
			"ulica": "Kwiatowa",
			"nr_domu": "19A",
			"miasto": "Poznań",
		}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["custom_install_address"], "Kwiatowa")
		self.assertEqual(lead["custom_nr_domu"], "19A")

	def test_j_wies_bez_ulicy_sam_numer_rozbity_na_import(self: "TestZbudujLeada") -> None:
		# stary format: "Ulica" = sam numer, wieś w "miasto" - jedyny przypadek
		# stosowany PRZY IMPORCIE, per issue ops#92.
		rekord = {"telefon": "+48502103270", "imie": "Jan", "ulica": "5", "miasto": "Zbożowo"}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["custom_install_address"], "Zbożowo")
		self.assertEqual(lead["custom_nr_domu"], "5")

	def test_k_ulica_i_numer_sklejone_nie_sa_rozbijane_przy_imporcie(self: "TestZbudujLeada") -> None:
		# ogólne rozbicie "Ulica Numer" jest ŚWIADOMIE zarezerwowane dla backfillu
		# (ops/crm-leady-pola-import.py), nie dla nowych importów - patrz docstring
		# zbuduj_leada. custom_install_address zostaje niezmieniony, tak jak dziś.
		rekord = {"telefon": "+48502103270", "imie": "Jan", "ulica": "Słoneczna 2", "miasto": "Poznań"}
		lead = zbuduj_leada(rekord)
		self.assertEqual(lead["custom_install_address"], "Słoneczna 2")
		self.assertEqual(lead["custom_nr_domu"], "")


if __name__ == "__main__":
	unittest.main()
