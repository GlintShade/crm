import unittest

from crm.volteo_notatki import (
	DOCTYPE,
	DOZWOLONE_ROZSZERZENIA,
	ETYKIETY_ZAKLADEK,
	ETYKIETY_ZRODEL_DODATKOWYCH,
	PREFIKS_ZNACZNIKA,
	TYPY_BAZOWE,
	TYPY_PER_ZAKLADKA,
	ZAKLADKI,
	ZNACZNIK_ROBOCZY,
	ZRODLA_FEEDU,
	czy_dozwolony,
	czy_obraz,
	czy_pdf,
	etykieta_zrodla,
	normalizuj_komentarz_audytu,
	normalizuj_notatke,
	odfiltruj_zmigrowane,
	posortuj,
	rozbij_znacznik,
	rozszerzenie,
	tekst_aktywnosci,
	tekst_na_html,
	tekst_pusty,
	typy_dla,
	wszystkie_typy,
	zbuduj_powiadomienie,
	zbuduj_znacznik,
	zbuduj_zrodla,
)


class TestVolteoNotatkiZakladki(unittest.TestCase):
	def test_a_osiem_zakladek(self: "TestVolteoNotatkiZakladki") -> None:
		self.assertEqual(len(ZAKLADKI), 8)

	def test_b_bez_duplikatow(self: "TestVolteoNotatkiZakladki") -> None:
		self.assertEqual(len(ZAKLADKI), len(set(ZAKLADKI)))

	def test_c_montaz_bez_ogonka(self: "TestVolteoNotatkiZakladki") -> None:
		self.assertIn("Montaz", ZAKLADKI)
		self.assertNotIn("Montaż", ZAKLADKI)

	def test_d_kazda_zakladka_ma_etykiete(self: "TestVolteoNotatkiZakladki") -> None:
		for zakladka in ZAKLADKI:
			self.assertIn(zakladka, ETYKIETY_ZAKLADEK)

	def test_e_etykieta_montaz_z_ogonkiem(self: "TestVolteoNotatkiZakladki") -> None:
		self.assertEqual(ETYKIETY_ZAKLADEK["Montaz"], "Montaż")

	def test_f_etykieta_reszty_jak_nazwa(self: "TestVolteoNotatkiZakladki") -> None:
		for zakladka in ZAKLADKI:
			if zakladka == "Montaz":
				continue
			self.assertEqual(ETYKIETY_ZAKLADEK[zakladka], zakladka)


class TestVolteoNotatkiTypyDla(unittest.TestCase):
	def test_a_kazda_zakladka_ma_wpis(self: "TestVolteoNotatkiTypyDla") -> None:
		for zakladka in ZAKLADKI:
			self.assertIn(zakladka, TYPY_PER_ZAKLADKA)

	def test_b_baza_dla_zestaw(self: "TestVolteoNotatkiTypyDla") -> None:
		self.assertEqual(typy_dla("Zestaw"), TYPY_BAZOWE)

	def test_c_baza_dla_umowa_kredyt_faktury_osd_dotacja(self: "TestVolteoNotatkiTypyDla") -> None:
		for zakladka in ("Umowa", "Kredyt", "Faktury", "OSD", "Dotacja"):
			self.assertEqual(typy_dla(zakladka), TYPY_BAZOWE)

	def test_d_montaz_dodaje_termin_montazu(self: "TestVolteoNotatkiTypyDla") -> None:
		typy = typy_dla("Montaz")
		self.assertIn("Termin montażu", typy)
		for typ in TYPY_BAZOWE:
			self.assertIn(typ, typy)
		self.assertEqual(len(typy), len(TYPY_BAZOWE) + 1)

	def test_e_trify_ma_wlasny_slownik(self: "TestVolteoNotatkiTypyDla") -> None:
		typy = typy_dla("Trify")
		self.assertEqual(
			typy,
			("Notatka", "Wniosek Trify", "Decyzja Trify", "Umowa Trify", "Wypłata Trify", "Problem"),
		)

	def test_f_nieznana_zakladka_rzuca(self: "TestVolteoNotatkiTypyDla") -> None:
		with self.assertRaises(ValueError):
			typy_dla("Nieistniejaca")

	def test_g_zaden_slownik_nie_ma_duplikatow(self: "TestVolteoNotatkiTypyDla") -> None:
		for zakladka in ZAKLADKI:
			typy = typy_dla(zakladka)
			self.assertEqual(len(typy), len(set(typy)))


class TestVolteoNotatkiWszystkieTypy(unittest.TestCase):
	def test_a_zawiera_kazdy_typ_z_kazdej_zakladki(self: "TestVolteoNotatkiWszystkieTypy") -> None:
		wszystkie = wszystkie_typy()
		for zakladka in ZAKLADKI:
			for typ in TYPY_PER_ZAKLADKA[zakladka]:
				self.assertIn(typ, wszystkie)

	def test_b_bez_duplikatow(self: "TestVolteoNotatkiWszystkieTypy") -> None:
		wszystkie = wszystkie_typy()
		self.assertEqual(len(wszystkie), len(set(wszystkie)))

	def test_c_kolejnosc_stabilna_notatka_pierwsza(self: "TestVolteoNotatkiWszystkieTypy") -> None:
		wszystkie = wszystkie_typy()
		self.assertEqual(wszystkie[0], "Notatka")

	def test_d_deterministyczna_miedzy_wywolaniami(self: "TestVolteoNotatkiWszystkieTypy") -> None:
		self.assertEqual(wszystkie_typy(), wszystkie_typy())


class TestVolteoNotatkiZnaczniki(unittest.TestCase):
	def test_a_zbuduj_znacznik(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertEqual(zbuduj_znacznik("abc123"), "notatka_abc123")

	def test_b_zbuduj_znacznik_ma_prefiks(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertTrue(zbuduj_znacznik("xyz").startswith(PREFIKS_ZNACZNIKA))

	def test_c_rozbij_znacznik_roboczy_daje_none(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertIsNone(rozbij_znacznik("notatka_robocza"))
		self.assertIsNone(rozbij_znacznik(ZNACZNIK_ROBOCZY))

	def test_d_rozbij_znacznik_docelowy(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertEqual(rozbij_znacznik("notatka_abc123"), "abc123")

	def test_e_rozbij_znacznik_none_i_pusty(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertIsNone(rozbij_znacznik(None))
		self.assertIsNone(rozbij_znacznik(""))

	def test_f_rozbij_znacznik_obcego_modulu(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertIsNone(rozbij_znacznik("zdjecia_montaz"))

	def test_g_zbuduj_i_rozbij_sa_odwrotne(self: "TestVolteoNotatkiZnaczniki") -> None:
		self.assertEqual(rozbij_znacznik(zbuduj_znacznik("hash-xyz")), "hash-xyz")


class TestVolteoNotatkiRozszerzenia(unittest.TestCase):
	def test_a_dozwolone_rozszerzenia(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertEqual(DOZWOLONE_ROZSZERZENIA, frozenset({"pdf", "jpg", "jpeg", "png", "webp"}))

	def test_b_rozszerzenie_male_litery(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertEqual(rozszerzenie("Zdjecie.JPG"), "jpg")

	def test_c_rozszerzenie_bez_kropki(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertIsNone(rozszerzenie("plik_bez_rozszerzenia"))

	def test_d_rozszerzenie_none(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertIsNone(rozszerzenie(None))

	def test_e_czy_pdf(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertTrue(czy_pdf("umowa.pdf"))
		self.assertTrue(czy_pdf("UMOWA.PDF"))
		self.assertFalse(czy_pdf("zdjecie.jpg"))

	def test_f_czy_obraz(self: "TestVolteoNotatkiRozszerzenia") -> None:
		for nazwa in ("a.jpg", "a.jpeg", "a.png", "a.webp"):
			self.assertTrue(czy_obraz(nazwa))
		self.assertFalse(czy_obraz("a.pdf"))
		self.assertFalse(czy_obraz("a.gif"))

	def test_g_czy_dozwolony(self: "TestVolteoNotatkiRozszerzenia") -> None:
		self.assertTrue(czy_dozwolony("dokument.pdf"))
		self.assertTrue(czy_dozwolony("zdjecie.webp"))
		self.assertFalse(czy_dozwolony("wideo.mp4"))
		self.assertFalse(czy_dozwolony("bez_rozszerzenia"))


class TestVolteoNotatkiTekstPusty(unittest.TestCase):
	def test_a_none_i_pusty_string_sa_puste(self: "TestVolteoNotatkiTekstPusty") -> None:
		self.assertTrue(tekst_pusty(None))
		self.assertTrue(tekst_pusty(""))

	def test_b_pusty_akapit_tiptapa_jest_pusty(self: "TestVolteoNotatkiTekstPusty") -> None:
		self.assertTrue(tekst_pusty("<p></p>"))

	def test_c_tekst_nie_jest_pusty(self: "TestVolteoNotatkiTekstPusty") -> None:
		self.assertFalse(tekst_pusty("<p>x</p>"))


class TestVolteoNotatkiTekstNaHtml(unittest.TestCase):
	def test_a_escapuje_script(self: "TestVolteoNotatkiTekstNaHtml") -> None:
		wynik = tekst_na_html("<script>alert(1)</script>")
		self.assertNotIn("<script>", wynik)
		self.assertIn("&lt;script&gt;", wynik)

	def test_b_nowa_linia_na_br(self: "TestVolteoNotatkiTekstNaHtml") -> None:
		wynik = tekst_na_html("linia 1\nlinia 2")
		self.assertIn("linia 1<br>linia 2", wynik)

	def test_c_owiniete_w_p(self: "TestVolteoNotatkiTekstNaHtml") -> None:
		wynik = tekst_na_html("tresc")
		self.assertTrue(wynik.startswith("<p>"))
		self.assertTrue(wynik.endswith("</p>"))

	def test_d_pusty_string(self: "TestVolteoNotatkiTekstNaHtml") -> None:
		self.assertEqual(tekst_na_html(""), "<p></p>")


class TestVolteoNotatkiTekstAktywnosci(unittest.TestCase):
	def test_a_zawiera_etykiete_zakladki_typ_i_tresc(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		linia = tekst_aktywnosci("Montaz", "Notatka", "<p>Klient prosi o telefon</p>")
		self.assertIn("Montaż", linia)
		self.assertIn("Notatka", linia)
		self.assertIn("Klient prosi o telefon", linia)

	def test_b_format_dokladny(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		linia = tekst_aktywnosci("Zestaw", "Telefon", "<p>Rozmowa</p>")
		self.assertEqual(linia, "dodano notatkę (Zestaw): Telefon: „Rozmowa”")

	def test_c_html_usuniety_z_fragmentu(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		linia = tekst_aktywnosci("Umowa", "Notatka", "<p><strong>Pilne</strong></p>")
		self.assertNotIn("<strong>", linia)
		self.assertIn("Pilne", linia)

	def test_d_obcina_do_80_znakow(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		dlugi = "a" * 200
		linia = tekst_aktywnosci("Zestaw", "Notatka", f"<p>{dlugi}</p>")
		self.assertIn("…", linia)
		self.assertNotIn("a" * 81, linia)

	def test_e_krotki_tekst_bez_wielokropka(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		linia = tekst_aktywnosci("Zestaw", "Notatka", "<p>krotko</p>")
		self.assertNotIn("…", linia)

	def test_f_pusty_tekst_daje_pusty_fragment(self: "TestVolteoNotatkiTekstAktywnosci") -> None:
		linia = tekst_aktywnosci("Zestaw", "Notatka", "")
		self.assertEqual(linia, "dodano notatkę (Zestaw): Notatka: „”")

	def test_g_nieznana_zakladka_uzywa_wartosci_jako_etykiety(
		self: "TestVolteoNotatkiTekstAktywnosci",
	) -> None:
		linia = tekst_aktywnosci("Nieznana", "Notatka", "<p>x</p>")
		self.assertIn("Nieznana", linia)


class TestVolteoNotatkiZbudujPowiadomienie(unittest.TestCase):
	def test_a_komplet_kluczy(self: "TestVolteoNotatkiZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie(
			"autor@proenergy.pro", "Jan Kowalski", "PRO/PV/26/0001", "abc123", "Montaz", "b@proenergy.pro"
		)
		oczekiwane_klucze = {
			"owner",
			"assigned_to",
			"notification_type",
			"message",
			"notification_text",
			"reference_doctype",
			"reference_docname",
			"redirect_to_doctype",
			"redirect_to_docname",
		}
		self.assertEqual(set(wynik.keys()), oczekiwane_klucze)

	def test_b_typ_i_referencje(self: "TestVolteoNotatkiZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie(
			"autor@proenergy.pro", "Jan Kowalski", "PRO/PV/26/0001", "abc123", "Montaz", "b@proenergy.pro"
		)
		self.assertEqual(wynik["notification_type"], "Mention")
		self.assertEqual(wynik["redirect_to_doctype"], "CRM Deal")
		self.assertEqual(wynik["reference_doctype"], DOCTYPE)
		self.assertEqual(wynik["reference_docname"], "abc123")
		self.assertEqual(wynik["redirect_to_docname"], "PRO/PV/26/0001")
		self.assertEqual(wynik["owner"], "autor@proenergy.pro")
		self.assertEqual(wynik["assigned_to"], "b@proenergy.pro")

	def test_c_etykieta_zakladki_w_tresci(self: "TestVolteoNotatkiZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie(
			"autor@proenergy.pro", "Jan Kowalski", "PRO/PV/26/0001", "abc123", "Montaz", "b@proenergy.pro"
		)
		self.assertIn("Montaż", wynik["message"])
		self.assertIn("Jan Kowalski", wynik["message"])
		self.assertIn("PRO/PV/26/0001", wynik["message"])

	def test_d_escapowanie_nazwy_autora(self: "TestVolteoNotatkiZbudujPowiadomienie") -> None:
		wynik = zbuduj_powiadomienie(
			"autor@proenergy.pro",
			"<script>alert(1)</script>",
			"PRO/PV/26/0001",
			"abc123",
			"Zestaw",
			"b@proenergy.pro",
		)
		self.assertNotIn("<script>", wynik["message"])
		self.assertIn("&lt;script&gt;", wynik["message"])


class TestVolteoNotatkiPosortuj(unittest.TestCase):
	def test_a_domyslnie_malejaco(self: "TestVolteoNotatkiPosortuj") -> None:
		wpisy = [
			{"data_zdarzenia": "2026-09-01 10:00:00", "creation": "2026-09-01 10:00:00", "name": "a"},
			{"data_zdarzenia": "2026-09-02 10:00:00", "creation": "2026-09-02 10:00:00", "name": "b"},
		]
		posortowane = posortuj(wpisy)
		self.assertEqual([w["name"] for w in posortowane], ["b", "a"])

	def test_b_rosnaco(self: "TestVolteoNotatkiPosortuj") -> None:
		wpisy = [
			{"data_zdarzenia": "2026-09-02 10:00:00", "creation": "2026-09-02 10:00:00", "name": "b"},
			{"data_zdarzenia": "2026-09-01 10:00:00", "creation": "2026-09-01 10:00:00", "name": "a"},
		]
		posortowane = posortuj(wpisy, kierunek="asc")
		self.assertEqual([w["name"] for w in posortowane], ["a", "b"])

	def test_c_creation_jako_tiebreak(self: "TestVolteoNotatkiPosortuj") -> None:
		wpisy = [
			{"data_zdarzenia": "2026-09-01 10:00:00", "creation": "2026-09-01 09:00:00", "name": "wczesniej"},
			{"data_zdarzenia": "2026-09-01 10:00:00", "creation": "2026-09-01 11:00:00", "name": "pozniej"},
		]
		posortowane = posortuj(wpisy)
		self.assertEqual([w["name"] for w in posortowane], ["pozniej", "wczesniej"])

	def test_d_pusta_lista(self: "TestVolteoNotatkiPosortuj") -> None:
		self.assertEqual(posortuj([]), [])


class TestVolteoNotatkiZrodlaFeedu(unittest.TestCase):
	def test_a_dziesiec_zrodel(self: "TestVolteoNotatkiZrodlaFeedu") -> None:
		self.assertEqual(len(ZRODLA_FEEDU), 10)

	def test_b_bez_duplikatow(self: "TestVolteoNotatkiZrodlaFeedu") -> None:
		self.assertEqual(len(ZRODLA_FEEDU), len(set(ZRODLA_FEEDU)))

	def test_c_osiem_zakladek_potem_audyt_i_audytcp(self: "TestVolteoNotatkiZrodlaFeedu") -> None:
		self.assertEqual(ZRODLA_FEEDU[:8], ZAKLADKI)
		self.assertEqual(ZRODLA_FEEDU[8:], ("Audyt", "AudytCP"))

	def test_d_audyt_i_audytcp_poza_zakladkami(self: "TestVolteoNotatkiZrodlaFeedu") -> None:
		self.assertNotIn("Audyt", ZAKLADKI)
		self.assertNotIn("AudytCP", ZAKLADKI)


class TestVolteoNotatkiEtykietaZrodla(unittest.TestCase):
	def test_a_zakladka_notatki(self: "TestVolteoNotatkiEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla("Montaz"), "Montaż")
		self.assertEqual(etykieta_zrodla("Zestaw"), "Zestaw")

	def test_b_audyt_i_audytcp(self: "TestVolteoNotatkiEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla("Audyt"), "Audyt")
		self.assertEqual(etykieta_zrodla("AudytCP"), "Audyt CP")

	def test_c_nieznane_zrodlo_spada_na_klucz(self: "TestVolteoNotatkiEtykietaZrodla") -> None:
		self.assertEqual(etykieta_zrodla("CosNieznanego"), "CosNieznanego")

	def test_d_kazde_zrodlo_feedu_ma_etykiete(self: "TestVolteoNotatkiEtykietaZrodla") -> None:
		for zrodlo in ZRODLA_FEEDU:
			self.assertTrue(etykieta_zrodla(zrodlo), zrodlo)

	def test_e_dodatkowe_etykiety_maja_dokladnie_audyt_i_audytcp(
		self: "TestVolteoNotatkiEtykietaZrodla",
	) -> None:
		self.assertEqual(set(ETYKIETY_ZRODEL_DODATKOWYCH), {"Audyt", "AudytCP"})


class TestVolteoNotatkiNormalizujNotatke(unittest.TestCase):
	def _wpis(self: "TestVolteoNotatkiNormalizujNotatke", **nadpisania: object) -> dict:
		bazowy = {
			"name": "NOTATKA-0001",
			"zakladka": "Montaz",
			"typ": "Telefon",
			"data_zdarzenia": "2026-09-28 10:00:00",
			"creation": "2026-09-28 09:00:00",
			"tekst": "<p>Tresc notatki</p>",
			"kredyt": None,
			"owner": "jan@proenergy.pro",
			"autor_nazwa": "Jan Kowalski",
			"pliki": [{"name": "FILE-0001", "file_name": "a.pdf"}],
		}
		bazowy.update(nadpisania)
		return bazowy

	def test_a_ksztalt_wyniku(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis())
		oczekiwane_klucze = {
			"klucz",
			"zrodlo",
			"zrodlo_etykieta",
			"zakladka_hash",
			"typ",
			"data",
			"creation",
			"autor",
			"autor_nazwa",
			"tekst_html",
			"pliki",
			"kredyt",
		}
		self.assertEqual(set(wynik.keys()), oczekiwane_klucze)

	def test_b_klucz_prefiks_notatka(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis())
		self.assertEqual(wynik["klucz"], "notatka:NOTATKA-0001")

	def test_c_zrodlo_etykieta_i_hash_z_zakladki(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis(zakladka="Montaz"))
		self.assertEqual(wynik["zrodlo"], "Montaz")
		self.assertEqual(wynik["zrodlo_etykieta"], "Montaż")
		self.assertEqual(wynik["zakladka_hash"], "montaz")

	def test_d_data_spada_na_creation_gdy_brak_data_zdarzenia(
		self: "TestVolteoNotatkiNormalizujNotatke",
	) -> None:
		wynik = normalizuj_notatke(self._wpis(data_zdarzenia=None))
		self.assertEqual(wynik["data"], "2026-09-28 09:00:00")

	def test_e_tekst_html_przepisany_bez_zmian(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis(tekst="<p>Bez zmian</p>"))
		self.assertEqual(wynik["tekst_html"], "<p>Bez zmian</p>")

	def test_f_autor_i_autor_nazwa(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis())
		self.assertEqual(wynik["autor"], "jan@proenergy.pro")
		self.assertEqual(wynik["autor_nazwa"], "Jan Kowalski")

	def test_g_autor_nazwa_spada_na_owner_gdy_brak(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis(autor_nazwa=None))
		self.assertEqual(wynik["autor_nazwa"], "jan@proenergy.pro")

	def test_h_pliki_i_kredyt_przepisane(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis(kredyt="KREDYT-0001"))
		self.assertEqual(wynik["kredyt"], "KREDYT-0001")
		self.assertEqual(wynik["pliki"], [{"name": "FILE-0001", "file_name": "a.pdf"}])

	def test_i_brak_plikow_daje_pusta_liste(self: "TestVolteoNotatkiNormalizujNotatke") -> None:
		wynik = normalizuj_notatke(self._wpis(pliki=None))
		self.assertEqual(wynik["pliki"], [])


class TestVolteoNotatkiNormalizujKomentarzAudytu(unittest.TestCase):
	def _komentarz(self: "TestVolteoNotatkiNormalizujKomentarzAudytu", **nadpisania: object) -> dict:
		bazowy = {
			"name": "COMMENT-0001",
			"owner": "anna@proenergy.pro",
			"creation": "2026-09-28 11:30:00",
			"content": "Wszystko gotowe do wyslania",
			"autor_nazwa": "Anna Nowak",
			"pliki": [],
		}
		bazowy.update(nadpisania)
		return bazowy

	def test_a_ksztalt_wyniku(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		oczekiwane_klucze = {
			"klucz",
			"zrodlo",
			"zrodlo_etykieta",
			"zakladka_hash",
			"typ",
			"data",
			"creation",
			"autor",
			"autor_nazwa",
			"tekst_html",
			"pliki",
			"kredyt",
		}
		self.assertEqual(set(wynik.keys()), oczekiwane_klucze)

	def test_b_klucz_prefiks_audyt(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		self.assertEqual(wynik["klucz"], "audyt:COMMENT-0001")

	def test_c_zrodlo_oze_i_cp(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik_oze = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		self.assertEqual(wynik_oze["zrodlo"], "Audyt")
		self.assertEqual(wynik_oze["zrodlo_etykieta"], "Audyt")
		self.assertEqual(wynik_oze["zakladka_hash"], "audyt")

		wynik_cp = normalizuj_komentarz_audytu(self._komentarz(), "AudytCP")
		self.assertEqual(wynik_cp["zrodlo"], "AudytCP")
		self.assertEqual(wynik_cp["zrodlo_etykieta"], "Audyt CP")
		self.assertEqual(wynik_cp["zakladka_hash"], "audytcp")

	def test_d_typ_zawsze_komentarz(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		self.assertEqual(wynik["typ"], "Komentarz")

	def test_e_kredyt_zawsze_none(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		self.assertIsNone(wynik["kredyt"])

	def test_f_nieznane_zrodlo_rzuca_value_error(
		self: "TestVolteoNotatkiNormalizujKomentarzAudytu",
	) -> None:
		with self.assertRaises(ValueError):
			normalizuj_komentarz_audytu(self._komentarz(), "Zestaw")

	def test_g_autor_i_autor_nazwa(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(), "Audyt")
		self.assertEqual(wynik["autor"], "anna@proenergy.pro")
		self.assertEqual(wynik["autor_nazwa"], "Anna Nowak")

	def test_h_autor_nazwa_spada_na_owner_nigdy_na_comment_by(
		self: "TestVolteoNotatkiNormalizujKomentarzAudytu",
	) -> None:
		# `comment_by` swiadomie zignorowane, nawet jesli jest obecne w
		# wejsciu -- jedynym zrodlem prawdy o imieniu i nazwisku jest
		# `autor_nazwa` (rozwiazane przez wywolujacego zbiorczym zapytaniem
		# User.full_name), nigdy `Comment.comment_by`.
		wynik = normalizuj_komentarz_audytu(
			self._komentarz(autor_nazwa=None, comment_by="Ignorowane Pole"), "Audyt"
		)
		self.assertEqual(wynik["autor_nazwa"], "anna@proenergy.pro")

	def test_i_tekst_zwykly_zamieniony_na_html_escapowany(
		self: "TestVolteoNotatkiNormalizujKomentarzAudytu",
	) -> None:
		# Stary komentarz sprzed wzmianek @ (issue #205): zwykly tekst z
		# dawnej `textarea`, ktory NIE zaczyna sie od `<` (nawet jesli ma go
		# w srodku zdania) -- musi nadal trafiac do `tekst_na_html`
		# (escapowanie + `<br>` za nowa linie), zeby nie renderowal sie jako
		# zywy znacznik. `<script>` w tresci jest tu celowo w srodku, nie na
		# poczatku -- patrz `_wyglada_na_html` w `crm/volteo_notatki.py`.
		wynik = normalizuj_komentarz_audytu(
			self._komentarz(content="Cena < 5000 zl, <script>alert(1)</script>\ndruga linia"),
			"Audyt",
		)
		self.assertNotIn("<script>", wynik["tekst_html"])
		self.assertIn("&lt;script&gt;", wynik["tekst_html"])
		self.assertIn("<br>", wynik["tekst_html"])
		self.assertTrue(wynik["tekst_html"].startswith("<p>"))

	def test_j_pusta_tresc_daje_pusty_akapit(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(content=""), "Audyt")
		self.assertEqual(wynik["tekst_html"], "<p></p>")

	def test_k_pliki_przepisane(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		pliki = [{"name": "FILE-0002", "file_name": "zdjecie.png"}]
		wynik = normalizuj_komentarz_audytu(self._komentarz(pliki=pliki), "Audyt")
		self.assertEqual(wynik["pliki"], pliki)

	def test_l_brak_plikow_daje_pusta_liste(self: "TestVolteoNotatkiNormalizujKomentarzAudytu") -> None:
		wynik = normalizuj_komentarz_audytu(self._komentarz(pliki=None), "Audyt")
		self.assertEqual(wynik["pliki"], [])

	def test_m_tekst_html_z_edytora_przepisany_bez_zmian(
		self: "TestVolteoNotatkiNormalizujKomentarzAudytu",
	) -> None:
		# Nowy komentarz z edytora TextEditor (issue #205): `content` jest
		# juz bezpiecznym HTML-em zaczynajacym sie od znacznika blokowego --
		# przepisany 1:1, BEZ przechodzenia przez `tekst_na_html` (inaczej
		# `<p>` zamienioby sie w widoczne `&lt;p&gt;`).
		html_z_edytora = "<p>Wszystko gotowe, sprawdz proszę.</p>"
		wynik = normalizuj_komentarz_audytu(self._komentarz(content=html_z_edytora), "Audyt")
		self.assertEqual(wynik["tekst_html"], html_z_edytora)

	def test_n_wzmianka_we_wpisie_zachowana_bez_zmian(
		self: "TestVolteoNotatkiNormalizujKomentarzAudytu",
	) -> None:
		# Wzmianka @ wewnatrz komentarza audytu -- znacznik
		# `data-type="mention"` musi przetrwac normalizacje nietkniety,
		# zeby feed „Notatki" pokazal ja tak samo jak watek Komentarze.
		html_ze_wzmianka = (
			'<p>Sprawdz to <span class="mention" data-type="mention" '
			'data-id="handlowiec@proenergy.pro" data-label="Jan Kowalski">'
			"@Jan Kowalski</span></p>"
		)
		wynik = normalizuj_komentarz_audytu(self._komentarz(content=html_ze_wzmianka), "AudytCP")
		self.assertEqual(wynik["tekst_html"], html_ze_wzmianka)
		self.assertIn('data-type="mention"', wynik["tekst_html"])


class TestVolteoNotatkiZbudujZrodla(unittest.TestCase):
	def test_a_wszystkie_zrodla_obecne_w_stalej_kolejnosci(
		self: "TestVolteoNotatkiZbudujZrodla",
	) -> None:
		wynik = zbuduj_zrodla({})
		self.assertEqual([w["klucz"] for w in wynik], list(ZRODLA_FEEDU))

	def test_b_brak_licznika_daje_zero(self: "TestVolteoNotatkiZbudujZrodla") -> None:
		wynik = zbuduj_zrodla({})
		self.assertTrue(all(w["liczba"] == 0 for w in wynik))

	def test_c_liczniki_przepisane_po_kluczu(self: "TestVolteoNotatkiZbudujZrodla") -> None:
		wynik = zbuduj_zrodla({"Zestaw": 3, "Audyt": 1})
		po_kluczu = {w["klucz"]: w["liczba"] for w in wynik}
		self.assertEqual(po_kluczu["Zestaw"], 3)
		self.assertEqual(po_kluczu["Audyt"], 1)
		self.assertEqual(po_kluczu["Umowa"], 0)
		self.assertEqual(po_kluczu["AudytCP"], 0)

	def test_d_kazdy_wpis_ma_etykiete_niepusta(self: "TestVolteoNotatkiZbudujZrodla") -> None:
		wynik = zbuduj_zrodla({})
		for wpis in wynik:
			self.assertTrue(wpis["etykieta"], wpis["klucz"])

	def test_e_nieznany_klucz_w_licznikach_jest_ignorowany(
		self: "TestVolteoNotatkiZbudujZrodla",
	) -> None:
		wynik = zbuduj_zrodla({"CosNieznanego": 5})
		self.assertEqual(len(wynik), len(ZRODLA_FEEDU))
		self.assertNotIn("CosNieznanego", [w["klucz"] for w in wynik])


class TestVolteoNotatkiOdfiltrujZmigrowane(unittest.TestCase):
	def test_a_pusty_zbior_migracji_zwraca_wszystkie_rekordy_bez_zmian(
		self: "TestVolteoNotatkiOdfiltrujZmigrowane",
	) -> None:
		rekordy = [{"name": "MU-0001"}, {"name": "MU-0002"}]
		self.assertEqual(odfiltruj_zmigrowane(rekordy, set()), rekordy)

	def test_b_none_jako_zbior_migracji_zwraca_wszystkie_rekordy(
		self: "TestVolteoNotatkiOdfiltrujZmigrowane",
	) -> None:
		rekordy = [{"name": "MU-0001"}]
		self.assertEqual(odfiltruj_zmigrowane(rekordy, None), rekordy)

	def test_c_rekord_zmigrowany_jest_pominiety(self: "TestVolteoNotatkiOdfiltrujZmigrowane") -> None:
		rekordy = [{"name": "MU-0001"}, {"name": "MU-0002"}]
		wynik = odfiltruj_zmigrowane(rekordy, {"MU-0001"})
		self.assertEqual([r["name"] for r in wynik], ["MU-0002"])

	def test_d_wszystkie_rekordy_zmigrowane_daje_pusta_liste(
		self: "TestVolteoNotatkiOdfiltrujZmigrowane",
	) -> None:
		rekordy = [{"name": "MU-0001"}, {"name": "MU-0002"}]
		self.assertEqual(odfiltruj_zmigrowane(rekordy, {"MU-0001", "MU-0002"}), [])

	def test_e_zachowuje_kolejnosc_wejsciowa(self: "TestVolteoNotatkiOdfiltrujZmigrowane") -> None:
		rekordy = [{"name": "MU-0003"}, {"name": "MU-0001"}, {"name": "MU-0002"}]
		wynik = odfiltruj_zmigrowane(rekordy, {"MU-0001"})
		self.assertEqual([r["name"] for r in wynik], ["MU-0003", "MU-0002"])

	def test_f_akceptuje_liste_zamiast_zbioru(self: "TestVolteoNotatkiOdfiltrujZmigrowane") -> None:
		rekordy = [{"name": "MU-0001"}, {"name": "MU-0002"}]
		wynik = odfiltruj_zmigrowane(rekordy, ["MU-0001"])
		self.assertEqual([r["name"] for r in wynik], ["MU-0002"])

	def test_g_pusta_lista_rekordow_zwraca_pusta_liste(
		self: "TestVolteoNotatkiOdfiltrujZmigrowane",
	) -> None:
		self.assertEqual(odfiltruj_zmigrowane([], {"MU-0001"}), [])

	def test_h_nie_mutuje_wejsciowej_listy(self: "TestVolteoNotatkiOdfiltrujZmigrowane") -> None:
		rekordy = [{"name": "MU-0001"}, {"name": "MU-0002"}]
		odfiltruj_zmigrowane(rekordy, {"MU-0001"})
		self.assertEqual(len(rekordy), 2)


if __name__ == "__main__":
	unittest.main()
