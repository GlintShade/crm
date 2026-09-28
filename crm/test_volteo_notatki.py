import unittest

from crm.volteo_notatki import (
	DOCTYPE,
	DOZWOLONE_ROZSZERZENIA,
	ETYKIETY_ZAKLADEK,
	PREFIKS_ZNACZNIKA,
	TYPY_BAZOWE,
	TYPY_PER_ZAKLADKA,
	ZAKLADKI,
	ZNACZNIK_ROBOCZY,
	czy_dozwolony,
	czy_obraz,
	czy_pdf,
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


if __name__ == "__main__":
	unittest.main()
