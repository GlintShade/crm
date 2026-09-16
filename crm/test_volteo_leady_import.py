import unittest

from crm.volteo_leady_import import (
	NAGLOWKI_ARKUSZA,
	AdresRozbity,
	WartoscOdrzucona,
	domyslny_status_zrodla,
	mapuj_zainteresowanie,
	normalizuj_date,
	normalizuj_kod,
	normalizuj_pisownie_osoby,
	normalizuj_posiadane_produkty,
	normalizuj_produkt_procesu,
	normalizuj_status_zrodla,
	normalizuj_telefon,
	normalizuj_uwagi,
	normalizuj_wojewodztwo,
	normalizuj_zasady,
	normalizuj_zrodlo,
	rozbij_adres_arkusza,
	rozbij_fragment_ulicy,
	rozdziel_imie_nazwisko,
	scal_duble,
	ulica_zawiera_cyfre,
	waliduj_naglowek,
	wczytaj_arkusz,
	wykryj_duble_telefonow,
	zbuduj_leada_z_arkusza,
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


class TestRozbijFragmentUlicy(unittest.TestCase):
	"""`rozbij_fragment_ulicy` (b59, issue #141, uniformizacja) - zastępuje
	starą, usuniętą `rozbij_adres`. Pierwsza porcja testów portuje pokrycie
	starej funkcji (proste "ulica + numer", "sam numer bierze miasto", straż
	kodu pocztowego), reszta pokrywa nowe reguły a-g (nawiasy, segmenty po
	przecinku, tolerancyjny numer ze słowem 'nr', numer sklejony bez odstępu,
	prefiks 'ul.')."""

	# --- portowane z usuniętej TestRozbijAdres ---

	def test_a_ulica_z_numerem(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Kwiatowa 19", "Poznań"), ("Kwiatowa", "19", ""))

	def test_b_numer_z_litera(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Kwiatowa 19A", "Poznań"), ("Kwiatowa", "19A", ""))

	def test_c_numer_z_ukosnikiem(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Polna 5/2", "Poznań"), ("Polna", "5/2", ""))

	def test_d_wieloczlonowa_nazwa_ulicy(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Aleje Jerozolimskie 120", "Warszawa"),
			("Aleje Jerozolimskie", "120", ""),
		)

	def test_e_wies_bez_ulicy_sam_numer_bierze_miasto(self: "TestRozbijFragmentUlicy") -> None:
		# reguła "Zbożowo 5, 64-300 Zbożowo" z issue ops#92
		self.assertEqual(rozbij_fragment_ulicy("5", "Zbożowo"), ("Zbożowo", "5", ""))

	def test_f_sam_numer_z_litera_bierze_miasto(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("5A", "Zbożowo"), ("Zbożowo", "5A", ""))

	def test_g_sam_numer_bez_miasta_zostaje_bez_zmian(self: "TestRozbijFragmentUlicy") -> None:
		# brak miasta do podstawienia - reguła g (nierozpoznany numer), NIE None
		self.assertEqual(rozbij_fragment_ulicy("5", ""), ("5", "", ""))

	def test_h_brak_liczby_na_koncu_zostaje_bez_zmian(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Rynek", "Kraków"), ("Rynek", "", ""))

	def test_i_puste_daje_puste(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("", "Kraków"), ("", "", ""))
		self.assertEqual(rozbij_fragment_ulicy("   ", "Kraków"), ("", "", ""))

	def test_j_ulica_z_myslnikiem_bez_numeru_zostaje_bez_zmian(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(rozbij_fragment_ulicy("Plac Wolności", "Poznań"), ("Plac Wolności", "", ""))

	def test_k_kod_pocztowy_jako_ulica_nierozpoznane(self: "TestRozbijFragmentUlicy") -> None:
		# Produkcyjna anomalia danych: "62-300 300" w kolumnie Ulica (kod pocztowy
		# wpisany przez pomylke, po nim jeszcze liczba) - bez straznika regex
		# mechanicznie rozbilby to na ulica="62-300"/numer="300", co jest bez sensu.
		self.assertEqual(rozbij_fragment_ulicy("62-300 300", "Poznań"), ("62-300 300", "", ""))

	def test_l_kod_pocztowy_sam_bez_numeru(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("62-300", "Poznań"), ("62-300", "", ""))

	# --- regula a) nawias w srodku fragmentu ---

	def test_m_nawias_domkniety_w_srodku_fragmentu(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Kolejowa (budynek ma mieć odbiór...)", ""),
			("Kolejowa", "", "budynek ma mieć odbiór..."),
		)

	def test_n_nawias_niedomkniety_w_srodku_fragmentu(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Kolejowa (budynek ma mieć odbiór...", ""),
			("Kolejowa", "", "budynek ma mieć odbiór..."),
		)

	# --- regula b) segmenty po przecinku ---

	def test_o_dwa_przecinki_ulica_z_prefiksem_jako_pierwszy_segment(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Rogierówko, Ul. Kościuszki 16A", ""),
			("Kościuszki", "16A", "Rogierówko"),
		)

	def test_p_ulica_przecinek_miejscowosc_dopisek(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("ul. Szafranowa 14, Jezierzyce", ""),
			("Szafranowa", "14", "Jezierzyce"),
		)

	def test_q_trzy_segmenty_srodkowy_kod_pocztowy_odrzucony(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Ul. Wąpielsk 76, 87-337, Wąpielsk", ""),
			("Wąpielsk", "76", "Wąpielsk"),
		)

	def test_r_spoldzielcza_z_dopiskiem_po_przecinku(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Spółdzielcza 6a, Warszawa - Wesoła", ""),
			("Spółdzielcza", "6a", "Warszawa - Wesoła"),
		)

	def test_s_miejscowosc_przed_ulica_numer_w_drugim_segmencie(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Marianów, Marianowska 29", ""),
			("Marianowska", "29", "Marianów"),
		)

	def test_t_miejscowosc_przed_ul_prefiksem_numer_z_litera(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Kaczory, Ul. Gajowa 6H", ""),
			("Gajowa", "6H", "Kaczory"),
		)

	def test_u_zaden_segment_bez_numeru_ostatni_segment_wygrywa(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Kaczory, Wielka Wieś", ""),
			("Wielka Wieś", "", "Kaczory"),
		)

	# --- regula c) prefiks 'ul.'/'ul'/'ulica' ---

	def test_v_prefiks_ul_kropka_spacja(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("ul. Kręta 2/a", ""), ("Kręta", "2/a", ""))

	def test_w_prefiks_sklejony_bez_spacji(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("UL.PARKOWA5", ""), ("PARKOWA", "5", ""))

	def test_x_prefiks_nie_okraja_prawdziwej_nazwy_ulicy(self: "TestRozbijFragmentUlicy") -> None:
		# "Ulicowa" NIE zaczyna sie od prefiksu 'ul.'/'ul '/'ulica ' - zostaje cala.
		self.assertEqual(rozbij_fragment_ulicy("Ulicowa 5", ""), ("Ulicowa", "5", ""))

	# --- regula d) numer tolerancyjny (ze slowem 'nr' i bez) ---

	def test_y_numer_z_ukosnikiem_i_litera(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Wrzosowa 22/A", ""), ("Wrzosowa", "22/A", ""))

	def test_z_numer_z_odstepami_wokol_ukosnika(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Słupska 1 /2", ""), ("Słupska", "1/2", ""))

	def test_aa_numer_ze_slowem_nr_i_kropka(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("dywizjonu 303 nr 34.", ""), ("dywizjonu 303", "34", "")
		)

	def test_ab_zakrzewo_45_prosty_przypadek(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Zakrzewo 45", "Zakrzewo"), ("Zakrzewo", "45", ""))

	def test_ac_ulica_dwuczlonowa_numer_z_litera(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Chałupki Dębniańskie 42a", ""),
			("Chałupki Dębniańskie", "42a", ""),
		)

	def test_ad_numer_trzycyfrowy(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Jaśminowa 816", ""), ("Jaśminowa", "816", ""))

	def test_ae_ulica_dwuczlonowa_numer_trzycyfrowy(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Grodzisko Dolne 270", ""), ("Grodzisko Dolne", "270", "")
		)

	# --- regula e) numer sklejony bez odstepu ---

	def test_af_numer_sklejony_bez_prefiksu(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("KOWALEWICZKI32", ""), ("KOWALEWICZKI", "32", ""))

	# --- odstep przed litera koncowa (uniformizacja po tescie dymnym na
	# realnym arkuszu - "21 A"/"3 B" jest w praktyce czestszy niz "21A") ---

	def test_af2_numer_z_odstepem_przed_litera_normalizowany_bez_odstepu(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(rozbij_fragment_ulicy("Dziadowice 3 A", ""), ("Dziadowice", "3A", ""))

	def test_af3_ulica_dwuczlonowa_numer_z_odstepem_przed_litera(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Woskrzenice Małe 21 A", ""), ("Woskrzenice Małe", "21A", "")
		)

	# --- regula f) sam numer, w tym zapis Excela "x.0" ---

	def test_ag_sam_numer_excel_float_40(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("4.0", "Trzcinka"), ("Trzcinka", "4", ""))

	def test_ah_sam_numer_excel_float_10(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("1.0", "Trzcinka"), ("Trzcinka", "1", ""))

	def test_ah2_sam_numer_z_ukosnikiem_i_sama_litera_po_ukosniku(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		# spojnosc z regula d ("22/A" ma litere-bez-cyfry po ukosniku) - ta sama
		# forma numeru MA dzialac tak samo, gdy przed nim nie stoi nazwa ulicy.
		self.assertEqual(rozbij_fragment_ulicy("21/A", "Żelkówko"), ("Żelkówko", "21/A", ""))

	# --- regula g) numer nierozpoznany (i pulapka na regule e dla "14m2") ---

	def test_ai_blizinskiego_bez_numeru(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Blizińskiego", ""), ("Blizińskiego", "", ""))

	def test_aj_koscino_bez_numeru(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("Kościno", ""), ("Kościno", "", ""))

	def test_ak_rzepkowo_14m2_nie_lapie_sie_na_regule_e_sklejona(
		self: "TestRozbijFragmentUlicy",
	) -> None:
		# Bialy znak miedzy "Rzepkowo" i "14m2" wylacza regule e) (sklejony numer) -
		# bez tej strazy regex zlapalby to jako ulica="Rzepkowo 14m", numer="2".
		self.assertEqual(rozbij_fragment_ulicy("Rzepkowo 14m2", ""), ("Rzepkowo 14m2", "", ""))

	def test_al_znacznik_czasu_bez_numeru(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("1952-01-22T00:00:00", ""), ("1952-01-22T00:00:00", "", "")
		)

	def test_am_wolny_tekst_bez_cyfry_zostaje_caly(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(
			rozbij_fragment_ulicy("Pani w pracy w pośpiechu nie zdążyła podać", ""),
			("Pani w pracy w pośpiechu nie zdążyła podać", "", ""),
		)

	def test_an_xxx_zostaje_bez_zmian(self: "TestRozbijFragmentUlicy") -> None:
		self.assertEqual(rozbij_fragment_ulicy("xxx", ""), ("xxx", "", ""))


class TestUlicaZawieraCyfre(unittest.TestCase):
	def test_a_zawiera_cyfre(self: "TestUlicaZawieraCyfre") -> None:
		self.assertTrue(ulica_zawiera_cyfre("Rzepkowo 14m2"))

	def test_b_bez_cyfry(self: "TestUlicaZawieraCyfre") -> None:
		self.assertFalse(ulica_zawiera_cyfre("Blizińskiego"))

	def test_c_puste_bez_cyfry(self: "TestUlicaZawieraCyfre") -> None:
		self.assertFalse(ulica_zawiera_cyfre(""))


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


class TestNormalizujPisownieOsoby(unittest.TestCase):
	"""`normalizuj_pisownie_osoby` (b59, decyzja właściciela 2026-09-16,
	ujednolicenie pisowni)."""

	def test_a_same_wielkie_litery_dwa_slowa(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("RADOSŁAW GIEREMEK"), "Radosław Gieremek")

	def test_b_myslnik_kapitalizuje_obie_strony(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("kowalska-nowak"), "Kowalska-Nowak")

	def test_c_apostrof_kapitalizuje_po_sobie(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("o'brien"), "O'Brien")

	def test_d_polski_diakrytyk_lukasz(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("ŁUKASZ"), "Łukasz")

	def test_e_polski_diakrytyk_swietoslawa(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("ŚWIĘTOSŁAWA"), "Świętosława")

	def test_f_juz_poprawna_pisownia_bez_zmian(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("Jan Kowalski"), "Jan Kowalski")

	def test_g_puste_zostaje_puste(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby(""), "")

	def test_h_mieszana_wielkosc_liter_jedno_slowo(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(normalizuj_pisownie_osoby("aLEKSANDRA"), "Aleksandra")

	def test_i_trzy_slowa_kazde_kapitalizowane(self: "TestNormalizujPisownieOsoby") -> None:
		self.assertEqual(
			normalizuj_pisownie_osoby("agnieszka katarzyna marciniak"),
			"Agnieszka Katarzyna Marciniak",
		)


# ---------------------------------------------------------------------------
# Nowe testy formatu arkusza Grega (b59, issue #98 + #131).
# ---------------------------------------------------------------------------


class TestPusta(unittest.TestCase):
	"""`_pusta()` poszerzone o `brak`/`nie` (bez wielkości liter) - testowane
	pośrednio przez publiczne funkcje, żeby nie sięgać po prywatny helper wprost."""

	def test_a_puste_i_myslnik_nadal_puste(self: "TestPusta") -> None:
		self.assertIsNone(normalizuj_wojewodztwo(""))
		self.assertIsNone(normalizuj_wojewodztwo("-"))

	def test_b_brak_dowolna_wielkosc_liter(self: "TestPusta") -> None:
		self.assertIsNone(normalizuj_wojewodztwo("brak"))
		self.assertIsNone(normalizuj_wojewodztwo("Brak"))
		self.assertIsNone(normalizuj_wojewodztwo("BRAK"))

	def test_c_nie_traktowane_jak_puste(self: "TestPusta") -> None:
		# "nie" nie byl markerem pustki w starym formacie - nowy marker, zero
		# istniejacych testow go uzywalo, wiec nic sie nie psuje.
		self.assertIsNone(normalizuj_wojewodztwo("nie"))
		self.assertIsNone(normalizuj_wojewodztwo("Nie"))
		self.assertIsNone(normalizuj_wojewodztwo("NIE"))

	def test_d_otaczajace_biale_znaki_nie_przeszkadzaja(self: "TestPusta") -> None:
		self.assertIsNone(normalizuj_wojewodztwo("  brak  "))

	def test_e_mapuj_zainteresowanie_nie_traktowane_jak_puste(self: "TestPusta") -> None:
		self.assertIsNone(mapuj_zainteresowanie("nie"))

	def test_f_rozdziel_imie_nazwisko_nie_jako_nazwisko_traktowane_jak_puste(
		self: "TestPusta",
	) -> None:
		self.assertEqual(rozdziel_imie_nazwisko("Adam Banik", "nie"), ("Adam", "Banik"))


class TestNormalizujPosiadaneProdukty(unittest.TestCase):
	def test_a_pojedynczy_token(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(normalizuj_posiadane_produkty("PV"), "PV")

	def test_b_kanoniczna_kolejnosc_z_arkusza(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(
			normalizuj_posiadane_produkty("AUDYT, OKNA, PC, PV, TERMO"),
			"PV+PC+AUDYT+TERMO+OKNA",
		)

	def test_c_separator_plus(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(normalizuj_posiadane_produkty("PV+ME"), "PV+ME")

	def test_d_male_litery(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(normalizuj_posiadane_produkty("pv, me"), "PV+ME")

	def test_e_duplikaty_scalone(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(normalizuj_posiadane_produkty("PV, PV, ME"), "PV+ME")

	def test_f_wszystkie_dziewiec_naraz(self: "TestNormalizujPosiadaneProdukty") -> None:
		wynik = normalizuj_posiadane_produkty("GRUNT,OKNA,REKU,TERMO,AUDYT,PP,PC,ME,PV")
		self.assertEqual(wynik, "PV+ME+PC+PP+AUDYT+TERMO+REKU+OKNA+GRUNT")

	def test_g_nieznany_token_odrzuca_cale_pole(self: "TestNormalizujPosiadaneProdukty") -> None:
		with self.assertRaises(WartoscOdrzucona):
			normalizuj_posiadane_produkty("PV+KLIMATYZACJA")

	def test_h_nieznany_token_niesie_powod_w_wyjatku(self: "TestNormalizujPosiadaneProdukty") -> None:
		try:
			normalizuj_posiadane_produkty("KLIMATYZACJA")
		except WartoscOdrzucona as blad:
			self.assertIn("KLIMATYZACJA", blad.tokeny)
		else:
			self.fail("oczekiwano WartoscOdrzucona")

	def test_i_puste_daje_pusty_string(self: "TestNormalizujPosiadaneProdukty") -> None:
		self.assertEqual(normalizuj_posiadane_produkty(""), "")


class TestNormalizujProduktProcesu(unittest.TestCase):
	def test_a_pojedynczy_token(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu("PC"), "PC")

	def test_b_kanoniczna_kolejnosc_cp_plus_pv(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu("CP+PV"), "PV+CP")

	def test_c_arkusz_pc_przecinek_pv(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu("PC, PV"), "PV+PC")

	def test_d_arkusz_me_przecinek_pv(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu("ME, PV"), "PV+ME")

	def test_e_pvme_token(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu("PVME"), "PVME")

	def test_f_wszystkie_piec_naraz(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(
			normalizuj_produkt_procesu("CP,PC,ME,PVME,PV"), "PV+PVME+ME+PC+CP"
		)

	def test_g_nieznany_token_odrzuca_cale_pole(self: "TestNormalizujProduktProcesu") -> None:
		with self.assertRaises(WartoscOdrzucona):
			normalizuj_produkt_procesu("PV+AUDYT")

	def test_h_puste_daje_pusty_string(self: "TestNormalizujProduktProcesu") -> None:
		self.assertEqual(normalizuj_produkt_procesu(""), "")


class TestNormalizujZrodlo(unittest.TestCase):
	def test_a_pojedynczy_token(self: "TestNormalizujZrodlo") -> None:
		self.assertEqual(normalizuj_zrodlo("ARG"), "ARG")

	def test_b_kanoniczna_kolejnosc(self: "TestNormalizujZrodlo") -> None:
		self.assertEqual(normalizuj_zrodlo("SD+ARG"), "ARG+SD")

	def test_c_trzy_zrodla_naraz(self: "TestNormalizujZrodlo") -> None:
		self.assertEqual(normalizuj_zrodlo("SD+CC+ARG"), "ARG+CC+SD")

	def test_d_male_litery(self: "TestNormalizujZrodlo") -> None:
		self.assertEqual(normalizuj_zrodlo("cc"), "CC")

	def test_e_nieznany_token_odrzuca_cale_pole(self: "TestNormalizujZrodlo") -> None:
		with self.assertRaises(WartoscOdrzucona):
			normalizuj_zrodlo("ARG+FACEBOOK")

	def test_f_puste_daje_pusty_string(self: "TestNormalizujZrodlo") -> None:
		self.assertEqual(normalizuj_zrodlo(""), "")


class TestNormalizujStatusZrodla(unittest.TestCase):
	def test_a_wygrana(self: "TestNormalizujStatusZrodla") -> None:
		self.assertEqual(normalizuj_status_zrodla("Wygrana"), "Wygrana")

	def test_b_przegrana(self: "TestNormalizujStatusZrodla") -> None:
		self.assertEqual(normalizuj_status_zrodla("Przegrana"), "Przegrana")

	def test_c_nieaktualna(self: "TestNormalizujStatusZrodla") -> None:
		self.assertEqual(normalizuj_status_zrodla("Nieaktualna"), "Nieaktualna")

	def test_d_potencjal(self: "TestNormalizujStatusZrodla") -> None:
		self.assertEqual(normalizuj_status_zrodla("Potencjał"), "Potencjał")

	def test_e_male_litery_normalizuja_sie(self: "TestNormalizujStatusZrodla") -> None:
		self.assertEqual(normalizuj_status_zrodla("wygrana"), "Wygrana")

	def test_f_nieznane_daje_none(self: "TestNormalizujStatusZrodla") -> None:
		self.assertIsNone(normalizuj_status_zrodla("Telefon"))


class TestDomyslnyStatusZrodla(unittest.TestCase):
	def test_a_cc_daje_potencjal(self: "TestDomyslnyStatusZrodla") -> None:
		self.assertEqual(domyslny_status_zrodla("CC"), "Potencjał")

	def test_b_sd_daje_potencjal(self: "TestDomyslnyStatusZrodla") -> None:
		self.assertEqual(domyslny_status_zrodla("SD"), "Potencjał")

	def test_c_unia_arg_cc_daje_potencjal(self: "TestDomyslnyStatusZrodla") -> None:
		self.assertEqual(domyslny_status_zrodla("ARG+CC"), "Potencjał")

	def test_d_sam_arg_daje_none(self: "TestDomyslnyStatusZrodla") -> None:
		self.assertIsNone(domyslny_status_zrodla("ARG"))

	def test_e_puste_daje_none(self: "TestDomyslnyStatusZrodla") -> None:
		self.assertIsNone(domyslny_status_zrodla(""))


class TestNormalizujZasady(unittest.TestCase):
	def test_a_token_nowe(self: "TestNormalizujZasady") -> None:
		self.assertEqual(normalizuj_zasady("NOWE"), "Nowe zasady")

	def test_b_token_stare(self: "TestNormalizujZasady") -> None:
		self.assertEqual(normalizuj_zasady("STARE"), "Stare zasady")

	def test_c_literal_nowe_zasady(self: "TestNormalizujZasady") -> None:
		self.assertEqual(normalizuj_zasady("Nowe zasady"), "Nowe zasady")

	def test_d_literal_stare_zasady(self: "TestNormalizujZasady") -> None:
		self.assertEqual(normalizuj_zasady("Stare zasady"), "Stare zasady")

	def test_e_male_litery_dzialaja(self: "TestNormalizujZasady") -> None:
		self.assertEqual(normalizuj_zasady("nowe"), "Nowe zasady")

	def test_f_smiec_naglowka_rzuca(self: "TestNormalizujZasady") -> None:
		with self.assertRaises(WartoscOdrzucona):
			normalizuj_zasady("Telefon")

	def test_g_inny_smiec_naglowka_rzuca(self: "TestNormalizujZasady") -> None:
		with self.assertRaises(WartoscOdrzucona):
			normalizuj_zasady("Adres")


class TestRozbijAdresArkusza(unittest.TestCase):
	def test_a_pelny_adres_z_ucietym_dopiskiem(self: "TestRozbijAdresArkusza") -> None:
		wynik = rozbij_adres_arkusza("Miodowa 10, 89-422 Sypniewo (Wybudowani")
		self.assertEqual(
			wynik,
			AdresRozbity(ulica="Miodowa", nr_domu="10", kod="89-422", miejscowosc="Sypniewo", dopisek="Wybudowani"),
		)

	def test_b_dopisek_z_zamknietym_nawiasem(self: "TestRozbijAdresArkusza") -> None:
		wynik = rozbij_adres_arkusza("Polna 3, 60-100 Poznań (Wilanów)")
		self.assertEqual(wynik.dopisek, "Wilanów")
		self.assertEqual(wynik.miejscowosc, "Poznań")

	def test_c_ulica_myslnik_kopiuje_miejscowosc(self: "TestRozbijAdresArkusza") -> None:
		# issue #116, decyzja właściciela 2026-09-09: wieś bez ulicy -> ulica
		# ma niesc TA SAMA wartosc co miejscowosc, nie zostac pusta.
		wynik = rozbij_adres_arkusza("-, 62-020 Swarzędz")
		self.assertEqual(
			wynik,
			AdresRozbity(ulica="Swarzędz", nr_domu="", kod="62-020", miejscowosc="Swarzędz", dopisek=""),
		)

	def test_c2_ulica_pusta_wg_pusta_tez_kopiuje_miejscowosc(
		self: "TestRozbijAdresArkusza",
	) -> None:
		# "brak"/"nie" tez licza sie jako pustka fragmentu ulicy (_pusta), nie
		# tylko dosłowny "-".
		wynik = rozbij_adres_arkusza("brak, 62-020 Swarzędz")
		self.assertEqual(wynik.ulica, "Swarzędz")
		self.assertEqual(wynik.nr_domu, "")
		self.assertFalse(wynik.numer_nierozpoznany_z_cyfra)

	def test_d_dwa_przecinki_pierwszy_segment_miejscowosc_drugi_ulica(
		self: "TestRozbijAdresArkusza",
	) -> None:
		# b59 (#141): fragment "Rogierówko, Ul. Kościuszki 16A" (grupa 1
		# zachlannego _WZOR_ADRES) idzie teraz przez rozbij_fragment_ulicy,
		# ktora dzieli go po przecinku - "Rogierówko" nie daje numeru,
		# "Ul. Kościuszki 16A" daje, wiec TO jest ulica, a "Rogierówko"
		# trafia do dopisku.
		wynik = rozbij_adres_arkusza("Rogierówko, Ul. Kościuszki 16A, 62-090 Rokietnica")
		self.assertEqual(
			wynik,
			AdresRozbity(
				ulica="Kościuszki",
				nr_domu="16A",
				kod="62-090",
				miejscowosc="Rokietnica",
				dopisek="Rogierówko",
			),
		)

	def test_e_ulica_bez_numeru_nie_jest_odrzuceniem(self: "TestRozbijAdresArkusza") -> None:
		# "Blizińskiego" nie ma rozpoznawalnego numeru na koncu (regula g) -
		# rozbij_adres_arkusza uzywa calego fragmentu jako ulicy z pustym
		# numerem, NIE odrzuca calego pola Adres. Brak cyfry w "Blizińskiego"
		# -> tez brak wpisu informacyjnego.
		wynik = rozbij_adres_arkusza("Blizińskiego, 97-200 Tomaszów Mazowiecki")
		self.assertEqual(wynik.ulica, "Blizińskiego")
		self.assertEqual(wynik.nr_domu, "")
		self.assertEqual(wynik.miejscowosc, "Tomaszów Mazowiecki")
		self.assertFalse(wynik.numer_nierozpoznany_z_cyfra)

	def test_e2_numer_nierozpoznany_z_cyfra_flaga_ustawiona(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza("Rzepkowo 14m2, 62-080 Poznań")
		self.assertEqual(wynik.ulica, "Rzepkowo 14m2")
		self.assertEqual(wynik.nr_domu, "")
		self.assertTrue(wynik.numer_nierozpoznany_z_cyfra)

	def test_e3_dopisek_z_fragmentu_i_z_miejscowosci_razem(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza("Kolejowa (uwaga), 62-080 Poznań (Wilanów)")
		self.assertEqual(wynik.ulica, "Kolejowa")
		self.assertEqual(wynik.dopisek, "uwaga, Wilanów")

	# --- QA parsera 2026-09-16: przecinki TEZ w czesci PO kodzie pocztowym ---

	def test_e4_miejscowosc_z_koncowym_przecinkiem_bez_dopisku(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza("-, 66-010 Przybymierz,")
		self.assertEqual(wynik.miejscowosc, "Przybymierz")
		self.assertEqual(wynik.dopisek, "")

	def test_e5_miejscowosc_przecinek_dopisek_bez_spacji(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza("-, 72-006 Dołuje,Mierzyn")
		self.assertEqual(wynik.miejscowosc, "Dołuje")
		self.assertEqual(wynik.dopisek, "Mierzyn")

	def test_e6_miejscowosc_przecinek_dopisek_ze_spacja(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza("-, 78-627 Wałcz, Różewo")
		self.assertEqual(wynik.miejscowosc, "Wałcz")
		self.assertEqual(wynik.dopisek, "Różewo")

	def test_e7_miejscowosc_nawias_i_segment_po_przecinku_razem_w_dopisku(
		self: "TestRozbijAdresArkusza",
	) -> None:
		wynik = rozbij_adres_arkusza(
			"-, 23-114 Jabłonna (gmina), Chmiel Kolonia- miejscowość"
		)
		self.assertEqual(wynik.miejscowosc, "Jabłonna")
		self.assertEqual(wynik.dopisek, "gmina, Chmiel Kolonia- miejscowość")

	def test_e8_drugi_kod_pocztowy_sklejony_przecinkiem_bez_dopisku_myslnik(
		self: "TestRozbijAdresArkusza",
	) -> None:
		# "-, 62-640 Boryslawice Koscielne 20,62-640 Grzegorzew": _WZOR_ADRES
		# kotwiczy sie na DRUGIM wystapieniu ", dd-ddd " (po "20,"), wiec grupa 1
		# to "-, 62-640 Boryslawice Koscielne 20" - fragment ulicy ma WEWNATRZ
		# siebie wlasny przecinek z wiodacym "-" (odrzucany jako pusty segment)
		# i wlasny wiodacy kod pocztowy (zdejmowany jako prefiks segmentu).
		wynik = rozbij_adres_arkusza(
			"-, 62-640 Boryslawice Kościelne 20,62-640 Grzegorzew"
		)
		self.assertEqual(wynik.ulica, "Boryslawice Kościelne")
		self.assertEqual(wynik.nr_domu, "20")
		self.assertEqual(wynik.miejscowosc, "Grzegorzew")
		self.assertEqual(wynik.dopisek, "")

	def test_e9_segment_pusta_myslnik_odrzucony_z_miejscowosci(
		self: "TestRozbijAdresArkusza",
	) -> None:
		# analogiczny przypadek po stronie miejscowosci: sam "-" jako segment nie
		# ma trafic do dopisku.
		wynik = rozbij_adres_arkusza("-, 62-080 Poznań,-")
		self.assertEqual(wynik.miejscowosc, "Poznań")
		self.assertEqual(wynik.dopisek, "")

	def test_f_brak_dopasowania_wzorca_daje_none(self: "TestRozbijAdresArkusza") -> None:
		self.assertIsNone(rozbij_adres_arkusza("zupelnie inny format bez kodu pocztowego"))

	def test_g_puste_daje_none(self: "TestRozbijAdresArkusza") -> None:
		self.assertIsNone(rozbij_adres_arkusza(""))
		self.assertIsNone(rozbij_adres_arkusza("   "))

	def test_h_miejscowosc_bez_dopisku(self: "TestRozbijAdresArkusza") -> None:
		wynik = rozbij_adres_arkusza("Kwiatowa 5, 62-080 Poznań")
		self.assertEqual(wynik.dopisek, "")
		self.assertEqual(wynik.miejscowosc, "Poznań")

	def test_i_numer_z_ukosnikiem(self: "TestRozbijAdresArkusza") -> None:
		wynik = rozbij_adres_arkusza("Polna 5/2, 62-080 Poznań")
		self.assertEqual(wynik.ulica, "Polna")
		self.assertEqual(wynik.nr_domu, "5/2")

	def test_j_sam_numer_bez_nazwy_ulicy_zostaje_bez_zmian(self: "TestRozbijAdresArkusza") -> None:
		# rozbij_adres_arkusza NIE stosuje reguly "sam numer bierze miasto" z
		# rozbij_adres - jesli czesc uliczna to "5" (nie "-"), rozbij_adres("5",
		# miejscowosc) zwraca (miejscowosc, "5"), wiec ulica de facto STAJE SIE
		# miejscowoscia - to zachowanie dziedziczone wprost z rozbij_adres.
		wynik = rozbij_adres_arkusza("5, 64-300 Zbożowo")
		self.assertEqual(wynik.ulica, "Zbożowo")
		self.assertEqual(wynik.nr_domu, "5")


class TestNormalizujUwagi(unittest.TestCase):
	def test_a_pojedyncza_linia(self: "TestNormalizujUwagi") -> None:
		self.assertEqual(normalizuj_uwagi("lead z formularza"), "lead z formularza")

	def test_b_kilka_linii_separator_pipe(self: "TestNormalizujUwagi") -> None:
		wynik = normalizuj_uwagi("linia jeden|linia dwa|linia trzy")
		self.assertEqual(wynik, "linia jeden | linia dwa | linia trzy")

	def test_c_puste_linie_odrzucone(self: "TestNormalizujUwagi") -> None:
		wynik = normalizuj_uwagi("linia jeden||linia trzy")
		self.assertEqual(wynik, "linia jeden | linia trzy")

	def test_d_puste_bez_dopisku_daje_pusty_string(self: "TestNormalizujUwagi") -> None:
		self.assertEqual(normalizuj_uwagi(""), "")

	def test_e_dopisek_doklejony_jako_ostatnia_linia(self: "TestNormalizujUwagi") -> None:
		wynik = normalizuj_uwagi("lead z formularza", "Wybudowani")
		self.assertEqual(wynik, "lead z formularza | Adres (dopisek): Wybudowani")

	def test_f_dopisek_bez_uwag(self: "TestNormalizujUwagi") -> None:
		wynik = normalizuj_uwagi("", "Wilanów")
		self.assertEqual(wynik, "Adres (dopisek): Wilanów")

	def test_g_otaczajace_biale_znaki_przyciete(self: "TestNormalizujUwagi") -> None:
		wynik = normalizuj_uwagi("  linia jeden  |  linia dwa  ")
		self.assertEqual(wynik, "linia jeden | linia dwa")


class TestWalidujNaglowek(unittest.TestCase):
	def test_a_poprawny_naglowek_nie_rzuca(self: "TestWalidujNaglowek") -> None:
		waliduj_naglowek(list(NAGLOWKI_ARKUSZA))

	def test_b_bom_tolerowany(self: "TestWalidujNaglowek") -> None:
		naglowek = list(NAGLOWKI_ARKUSZA)
		naglowek[0] = "﻿" + naglowek[0]
		waliduj_naglowek(naglowek)

	def test_c_otaczajace_spacje_tolerowane(self: "TestWalidujNaglowek") -> None:
		naglowek = [f" {nazwa} " for nazwa in NAGLOWKI_ARKUSZA]
		waliduj_naglowek(naglowek)

	def test_d_brakujaca_kolumna_rzuca(self: "TestWalidujNaglowek") -> None:
		naglowek = list(NAGLOWKI_ARKUSZA)[:-1]
		with self.assertRaises(ValueError):
			waliduj_naglowek(naglowek)

	def test_e_nadmiarowa_kolumna_rzuca(self: "TestWalidujNaglowek") -> None:
		naglowek = [*NAGLOWKI_ARKUSZA, "Dodatkowa"]
		with self.assertRaises(ValueError):
			waliduj_naglowek(naglowek)

	def test_f_przestawiona_kolejnosc_rzuca(self: "TestWalidujNaglowek") -> None:
		naglowek = list(NAGLOWKI_ARKUSZA)
		naglowek[0], naglowek[1] = naglowek[1], naglowek[0]
		with self.assertRaises(ValueError):
			waliduj_naglowek(naglowek)


def _wiersz_arkusza(**nadpisania: str) -> dict[str, str]:
	"""Buduje wiersz arkusza testowy z sensownymi domyślnymi wartościami, nadpisując
	tylko podane pola - zgodny kluczami z `NAGLOWKI_ARKUSZA`."""
	bazowy: dict[str, str] = {
		"Telefon": "+48502103270",
		"Imię": "Jan",
		"Nazwisko": "Kowalski",
		"Adres": "Kwiatowa 5, 62-080 Poznań",
		"Powiat": "poznański",
		"Województwo": "wielkopolskie",
		"Źródło": "SD",
		"Data pozyskania": "2022-03-10",
		"Status źródła": "-",
		"Zasady rozliczania": "-",
		"Obecne produkty": "-",
		"Produkt w procesie": "-",
		"Zainteresowanie": "-",
		"Uwagi": "-",
	}
	bazowy.update(nadpisania)
	return bazowy


class TestWczytajArkusz(unittest.TestCase):
	def test_a_podstawowe_wczytanie(self: "TestWczytajArkusz") -> None:
		tekst = ",".join(NAGLOWKI_ARKUSZA) + "\n" + ",".join(_wiersz_arkusza().values()) + "\n"
		wiersze = wczytaj_arkusz(tekst)
		self.assertEqual(len(wiersze), 1)
		self.assertEqual(wiersze[0]["Imię"], "Jan")
		self.assertEqual(wiersze[0]["Telefon"], "+48502103270")

	def test_b_pusty_csv_daje_pusta_liste(self: "TestWczytajArkusz") -> None:
		self.assertEqual(wczytaj_arkusz(""), [])

	def test_c_zly_naglowek_rzuca(self: "TestWczytajArkusz") -> None:
		with self.assertRaises(ValueError):
			wczytaj_arkusz("Zla,Lista,Kolumn\na,b,c\n")

	def test_d_zbyt_krotki_wiersz_dopelniony_pustymi(self: "TestWczytajArkusz") -> None:
		tekst = ",".join(NAGLOWKI_ARKUSZA) + "\n" + "+48502103270,Jan\n"
		wiersze = wczytaj_arkusz(tekst)
		self.assertEqual(len(wiersze), 1)
		self.assertEqual(wiersze[0]["Telefon"], "+48502103270")
		self.assertEqual(wiersze[0]["Uwagi"], "")


class TestWykryjDubleTelefonow(unittest.TestCase):
	def test_a_bez_dubli_puste(self: "TestWykryjDubleTelefonow") -> None:
		wiersze = [_wiersz_arkusza(Telefon="+48502103270"), _wiersz_arkusza(Telefon="+48609116693")]
		self.assertEqual(wykryj_duble_telefonow(wiersze), {})

	def test_b_dubel_wskazuje_pierwszy_wiersz(self: "TestWykryjDubleTelefonow") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270"),
			_wiersz_arkusza(Telefon="+48609116693"),
			_wiersz_arkusza(Telefon="+48502103270"),
		]
		# indeksy 0/2 w liscie -> wiersze arkusza 2/4 (naglowek to wiersz 1).
		self.assertEqual(wykryj_duble_telefonow(wiersze), {4: 2})

	def test_c_niepoprawny_telefon_pomijany(self: "TestWykryjDubleTelefonow") -> None:
		wiersze = [_wiersz_arkusza(Telefon="za krotki"), _wiersz_arkusza(Telefon="tez zly")]
		self.assertEqual(wykryj_duble_telefonow(wiersze), {})

	def test_d_rozne_formaty_tego_samego_numeru_traktowane_jak_dubel(
		self: "TestWykryjDubleTelefonow",
	) -> None:
		wiersze = [_wiersz_arkusza(Telefon="502103270"), _wiersz_arkusza(Telefon="+48 502 103 270")]
		self.assertEqual(wykryj_duble_telefonow(wiersze), {3: 2})


class TestScalDuble(unittest.TestCase):
	"""`scal_duble` (b59, uniformizacja, spec `docs/LEADY-ARKUSZ-IMPORT-GREG.md`
	sekcja "Duble")."""

	def test_a_bez_dubli_wiersze_bez_zmian(self: "TestScalDuble") -> None:
		wiersze = [_wiersz_arkusza(Telefon="+48502103270"), _wiersz_arkusza(Telefon="+48609116693")]
		scalone, pary = scal_duble(wiersze)
		self.assertEqual([nr for nr, _ in scalone], [2, 3])
		self.assertEqual(pary, [])
		self.assertEqual(scalone[0][1]["Telefon"], "+48502103270")
		self.assertEqual(scalone[1][1]["Telefon"], "+48609116693")

	def test_b_dwa_wiersze_scalone_do_pierwszego(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", Imię="Jan", Nazwisko="Kowalski"),
			_wiersz_arkusza(Telefon="+48502103270", Imię="Adam", Nazwisko="Nowak"),
		]
		scalone, pary = scal_duble(wiersze)
		self.assertEqual(len(scalone), 1)
		self.assertEqual(scalone[0][0], 2)
		self.assertEqual(scalone[0][1]["Imię"], "Jan")
		self.assertEqual(scalone[0][1]["Nazwisko"], "Kowalski")
		self.assertEqual(pary, [(3, 2)])

	def test_c_zrodlo_sumowane_tokenami(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Źródło": "SD"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Źródło": "CC"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Źródło"], "SD CC")

	def test_d_uwagi_sklejone_pipe(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", Uwagi="pierwsza notatka"),
			_wiersz_arkusza(Telefon="+48502103270", Uwagi="druga notatka"),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Uwagi"], "pierwsza notatka|druga notatka")

	def test_e_obecne_produkty_sumowane_przecinkiem(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Obecne produkty": "PV"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Obecne produkty": "PC"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Obecne produkty"], "PV,PC")

	def test_f_produkt_w_procesie_sumowany_przecinkiem(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Produkt w procesie": "PV"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Produkt w procesie": "CP"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Produkt w procesie"], "PV,CP")

	def test_g_pusta_komorka_pierwszego_dopelniona_drugim(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", Powiat="-"),
			_wiersz_arkusza(Telefon="+48502103270", Powiat="ostrowski"),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Powiat"], "ostrowski")

	def test_h_niepusta_komorka_pierwszego_nie_nadpisywana(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", Powiat="poznański"),
			_wiersz_arkusza(Telefon="+48502103270", Powiat="ostrowski"),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Powiat"], "poznański")

	def test_i_status_zrodla_priorytet_wygrana_bije_potencjal(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Status źródła": "Potencjał"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Status źródła": "Wygrana"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Status źródła"], "Wygrana")

	def test_j_status_zrodla_priorytet_potencjal_bije_przegrana(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Status źródła": "Przegrana"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Status źródła": "Potencjał"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Status źródła"], "Potencjał")

	def test_k_data_pozyskania_nowsza_wygrywa(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Data pozyskania": "2022-01-01"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Data pozyskania": "2022-06-15"}),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual(scalone[0][1]["Data pozyskania"], "2022-06-15")

	def test_l_niepoprawny_telefon_nie_jest_grupowany(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="za krotki", Imię="Ala"),
			_wiersz_arkusza(Telefon="tez zly", Imię="Ola"),
		]
		scalone, pary = scal_duble(wiersze)
		self.assertEqual(len(scalone), 2)
		self.assertEqual(pary, [])
		self.assertEqual(scalone[0][1]["Imię"], "Ala")
		self.assertEqual(scalone[1][1]["Imię"], "Ola")

	def test_m_trzy_wiersze_ten_sam_telefon_scalone_progresywnie(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48502103270", **{"Źródło": "SD"}),
			_wiersz_arkusza(Telefon="+48502103270", **{"Źródło": "CC"}),
			_wiersz_arkusza(Telefon="502103270", **{"Źródło": "ARG"}),
		]
		scalone, pary = scal_duble(wiersze)
		self.assertEqual(len(scalone), 1)
		self.assertEqual(scalone[0][1]["Źródło"], "SD CC ARG")
		self.assertEqual(pary, [(3, 2), (4, 2)])

	def test_n_kolejnosc_wyjsciowa_wedlug_pierwszych_wystapien(self: "TestScalDuble") -> None:
		wiersze = [
			_wiersz_arkusza(Telefon="+48111111111"),
			_wiersz_arkusza(Telefon="+48222222222"),
			_wiersz_arkusza(Telefon="+48111111111"),
		]
		scalone, _ = scal_duble(wiersze)
		self.assertEqual([nr for nr, _ in scalone], [2, 3])


class TestZbudujLeadaZArkusza(unittest.TestCase):
	def test_a_zly_telefon_odrzuca_caly_wiersz(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(Telefon="za krotki")
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 5)
		self.assertIsNone(lead)
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Telefon")
		self.assertEqual(odrzucone[0].wiersz, 5)

	def test_b_pelny_poprawny_wiersz_bez_odrzucen(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(
			**{
				"Status źródła": "Wygrana",
				"Zasady rozliczania": "NOWE",
				"Obecne produkty": "PV, PC",
				"Produkt w procesie": "PC",
				"Zainteresowanie": "PV",
			}
		)
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone, [])
		self.assertIsNotNone(lead)
		self.assertEqual(lead["first_name"], "Jan")
		self.assertEqual(lead["last_name"], "Kowalski")
		self.assertEqual(lead["mobile_no"], "+48502103270")
		self.assertEqual(lead["status"], "Nowy")
		self.assertEqual(lead["business_line"], "D2D")
		self.assertEqual(lead["custom_install_address"], "Kwiatowa")
		self.assertEqual(lead["custom_nr_domu"], "5")
		self.assertEqual(lead["custom_install_postal_code"], "62-080")
		self.assertEqual(lead["custom_install_city"], "Poznań")
		self.assertEqual(lead["custom_powiat"], "poznański")
		self.assertEqual(lead["custom_voivodeship"], "wielkopolskie")
		self.assertEqual(lead["custom_import_source"], "SD")
		self.assertEqual(lead["custom_import_date"], "2022-03-10")
		self.assertEqual(lead["custom_status_zrodla"], "Wygrana")
		self.assertEqual(lead["custom_zasady_dotacji"], "Nowe zasady")
		self.assertEqual(lead["custom_posiadane_produkty"], "PV+PC")
		self.assertEqual(lead["custom_produkt_procesu"], "PC")
		self.assertEqual(lead["custom_product_interest"], "Fotowoltaika")

	def test_c_bez_lead_owner_bez_cc_bez_wspolrzednych(self: "TestZbudujLeadaZArkusza") -> None:
		lead, _ = zbuduj_leada_z_arkusza(_wiersz_arkusza(), 2)
		self.assertNotIn("lead_owner", lead)
		self.assertNotIn("custom_cc", lead)
		self.assertNotIn("custom_lat", lead)
		self.assertNotIn("custom_lng", lead)

	def test_d_fallback_imienia_gdy_puste(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Imię": "-", "Nazwisko": "-"})
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["first_name"], "Kontakt")

	def test_e_puste_zrodlo_odrzucone_jako_wymagane(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Źródło": "-"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 7)
		self.assertIsNotNone(lead)
		self.assertEqual(lead["custom_import_source"], "")
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Źródło")
		self.assertEqual(odrzucone[0].powod, "wymagane")

	def test_f_nieznany_token_zrodla_odrzuca_tylko_to_pole(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Źródło": "FACEBOOK"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 3)
		self.assertIsNotNone(lead)
		self.assertEqual(lead["custom_import_source"], "")
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Źródło")
		self.assertEqual(odrzucone[0].wartosc, "FACEBOOK")

	def test_g_puste_status_zrodla_bierze_domyslny_z_zrodla_cc(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Źródło": "CC", "Status źródła": "-"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["custom_status_zrodla"], "Potencjał")
		self.assertEqual(odrzucone, [])

	def test_h_puste_status_zrodla_arg_samo_daje_none_bez_odrzucenia(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Źródło": "ARG", "Status źródła": "-"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNone(lead["custom_status_zrodla"])
		self.assertEqual(odrzucone, [])

	def test_i_smiec_w_zasadach_rozliczania_odrzuca_tylko_to_pole(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Zasady rozliczania": "Telefon"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 42)
		self.assertIsNotNone(lead)
		self.assertIsNone(lead["custom_zasady_dotacji"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Zasady rozliczania")
		self.assertEqual(odrzucone[0].wiersz, 42)

	def test_j_nieznany_token_obecne_produkty_odrzuca_tylko_to_pole(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Obecne produkty": "PV+KLIMATYZACJA"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertIsNone(lead["custom_posiadane_produkty"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Obecne produkty")

	def test_k_nieznany_token_produkt_procesu_odrzuca_tylko_to_pole(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Produkt w procesie": "AUDYT"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertIsNone(lead["custom_produkt_procesu"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Produkt w procesie")

	def test_l_zle_wojewodztwo_odrzuca_tylko_to_pole(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Województwo": "mazowsze"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertIsNone(lead["custom_voivodeship"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Województwo")

	def test_m_zla_data_pozyskania_odrzuca_tylko_to_pole(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Data pozyskania": "nie wiadomo kiedy"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertIsNone(lead["custom_import_date"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Data pozyskania")

	def test_n_adres_nierozpoznany_zostaje_surowy_w_ulicy(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Adres": "adres bez kodu pocztowego wcale"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertEqual(lead["custom_install_address"], "adres bez kodu pocztowego wcale")
		self.assertEqual(lead["custom_nr_domu"], "")
		self.assertEqual(lead["custom_install_city"], "")
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Adres")

	def test_o_adres_z_dopiskiem_trafia_do_uwag_nie_do_miejscowosci(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(
			**{"Adres": "Miodowa 10, 89-422 Sypniewo (Wybudowani)", "Uwagi": "notatka handlowca"}
		)
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone, [])
		self.assertEqual(lead["custom_install_city"], "Sypniewo")
		self.assertIn("notatka handlowca", lead["custom_uwagi_import"])
		self.assertIn("Adres (dopisek): Wybudowani", lead["custom_uwagi_import"])

	def test_p_adres_pusty_zostaje_bez_odrzucenia(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Adres": "-"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone, [])
		self.assertEqual(lead["custom_install_address"], "")

	def test_q_sklejone_imie_nazwisko_rozdzielone(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(**{"Imię": "Adam Banik", "Nazwisko": "-"})
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["first_name"], "Adam")
		self.assertEqual(lead["last_name"], "Banik")

	def test_r_zainteresowanie_brak_daje_none_bez_odrzucenia(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Zainteresowanie": "brak"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNone(lead["custom_product_interest"])
		self.assertEqual(odrzucone, [])

	def test_s_wolny_tekst_zainteresowania_odrzuca_tylko_to_pole(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Zainteresowanie": "zastanawia sie"})
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNone(lead["custom_product_interest"])
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Zainteresowanie")

	def test_t_telefon_raportu_odrzucen_to_znormalizowany_numer(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(**{"Zasady rozliczania": "Adres"})
		_, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone[0].telefon, "+48502103270")

	def test_u_wszystkie_pola_puste_naraz_daja_puste_wartosci_bez_odrzucen(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(
			**{
				"Imię": "-",
				"Nazwisko": "-",
				"Adres": "-",
				"Powiat": "-",
				"Województwo": "-",
				"Data pozyskania": "-",
				"Status źródła": "-",
				"Zasady rozliczania": "-",
				"Obecne produkty": "-",
				"Produkt w procesie": "-",
				"Zainteresowanie": "-",
				"Uwagi": "-",
				"Źródło": "ARG",
			}
		)
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone, [])
		self.assertIsNone(lead["custom_voivodeship"])
		self.assertIsNone(lead["custom_import_date"])
		self.assertIsNone(lead["custom_status_zrodla"])
		self.assertIsNone(lead["custom_zasady_dotacji"])
		self.assertIsNone(lead["custom_posiadane_produkty"])
		self.assertIsNone(lead["custom_produkt_procesu"])
		self.assertIsNone(lead["custom_product_interest"])
		self.assertEqual(lead["custom_uwagi_import"], "")

	def test_v_pisownia_imienia_i_nazwiska_znormalizowana(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(Imię="RADOSŁAW", Nazwisko="GIEREMEK")
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["first_name"], "Radosław")
		self.assertEqual(lead["last_name"], "Gieremek")

	def test_w_pisownia_nazwiska_z_myslnikiem_znormalizowana(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(Imię="Anna", Nazwisko="kowalska-nowak")
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["last_name"], "Kowalska-Nowak")

	def test_x_firma_w_imieniu_pisownia_bez_zmian(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(
			Imię="PRZEDSIĘBIORSTWO WIELOBRANŻOWE KRZYSZTOF STECKIEWICZ", Nazwisko="-"
		)
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["first_name"], "PRZEDSIĘBIORSTWO WIELOBRANŻOWE KRZYSZTOF STECKIEWICZ")
		self.assertEqual(lead["last_name"], "")

	def test_y_firma_inwestprojekt_pisownia_bez_zmian(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(Imię="Firma Inwestprojekt", Nazwisko="-")
		lead, _ = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(lead["first_name"], "Firma Inwestprojekt")

	def test_z_wies_bez_ulicy_ulica_rowna_miejscowosci(self: "TestZbudujLeadaZArkusza") -> None:
		wiersz = _wiersz_arkusza(Adres="-, 62-020 Swarzędz")
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertEqual(odrzucone, [])
		self.assertEqual(lead["custom_install_address"], "Swarzędz")
		self.assertEqual(lead["custom_nr_domu"], "")
		self.assertEqual(lead["custom_install_city"], "Swarzędz")

	def test_aa_numer_domu_nierozpoznany_z_cyfra_dodaje_wpis_informacyjny(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(Adres="Rzepkowo 14m2, 62-080 Poznań")
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertEqual(lead["custom_install_address"], "Rzepkowo 14m2")
		self.assertEqual(len(odrzucone), 1)
		self.assertEqual(odrzucone[0].kolumna, "Adres")
		self.assertEqual(odrzucone[0].powod, "numer domu nierozpoznany, tekst zostawiony w Ulicy")

	def test_ab_ulica_bez_numeru_bez_cyfry_nie_dodaje_wpisu(
		self: "TestZbudujLeadaZArkusza",
	) -> None:
		wiersz = _wiersz_arkusza(Adres="Blizińskiego, 97-200 Tomaszów Mazowiecki")
		lead, odrzucone = zbuduj_leada_z_arkusza(wiersz, 2)
		self.assertIsNotNone(lead)
		self.assertEqual(odrzucone, [])


if __name__ == "__main__":
	unittest.main()
