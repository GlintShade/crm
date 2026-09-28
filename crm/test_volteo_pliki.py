import unittest

from crm.volteo_pliki import (
	KAT_DOKUMENT,
	KAT_INNY,
	KAT_OBRAZ,
	KAT_WIDEO,
	PREFIKS_ZNACZNIKA_NOTATKI,
	ZNACZNIK_ROBOCZY,
	ZNACZNIK_ZDJEC_MONTAZU,
	ZRODLA,
	ZRODLO_AUDYT_CP_GALERIA,
	ZRODLO_AUDYT_CP_SLOT,
	ZRODLO_AUDYT_DODATKOWE,
	ZRODLO_AUDYT_KOMENTARZ,
	ZRODLO_AUDYT_SLOT,
	ZRODLO_EMAIL,
	ZRODLO_FAKTURA,
	ZRODLO_KOMENTARZ,
	ZRODLO_KREDYT_PDF,
	ZRODLO_KREDYT_PODPISANY,
	ZRODLO_LEAD,
	ZRODLO_LUZEM,
	ZRODLO_MONTAZ_ZDJECIE,
	ZRODLO_NOTATKA,
	ZRODLO_ROBOCZE,
	ZRODLO_UMOWA_PDF,
	ZRODLO_UMOWA_PODPISANA,
	czy_widoczne_robocze,
	etykieta_zakladki_notatki,
	etykieta_zrodla,
	flagi,
	hash_zakladki_notatki,
	kategoria_pliku,
	klasyfikuj_plik_szansy,
	posortuj,
	scal_po_url,
	zakladka_dla_zrodla,
	zbuduj_callable_systemowe,
	zbuduj_zrodla,
)


def _plik(**nadpisania):
	bazowy = {
		"name": "file-1",
		"file_name": "dokument.pdf",
		"file_url": "/private/files/dokument.pdf",
		"file_size": 1024,
		"file_type": "PDF",
		"creation": "2026-09-28 10:00:00",
		"owner": "rep@proenergy.pro",
		"is_private": 1,
		"attached_to_doctype": "CRM Deal",
		"attached_to_name": "PRO/PV/26/0001",
		"attached_to_field": None,
	}
	bazowy.update(nadpisania)
	return bazowy


def _systemowe_falsz(_file_name):
	return None


class TestKategoriaPliku(unittest.TestCase):
	def test_rozszerzenie_pdf_to_dokument(self):
		self.assertEqual(kategoria_pliku("umowa.pdf", ""), KAT_DOKUMENT)

	def test_rozszerzenie_jpg_to_obraz(self):
		self.assertEqual(kategoria_pliku("zdjecie.JPG", ""), KAT_OBRAZ)

	def test_rozszerzenie_mp4_to_wideo(self):
		self.assertEqual(kategoria_pliku("nagranie.mp4", ""), KAT_WIDEO)

	def test_rozszerzenie_ma_pierwszenstwo_nad_file_type(self):
		# file_type klamie (video/mp4), ale rozszerzenie .pdf wygrywa.
		self.assertEqual(kategoria_pliku("skan.pdf", "video/mp4"), KAT_DOKUMENT)

	def test_pusty_file_type_pada_na_rozszerzenie(self):
		self.assertEqual(kategoria_pliku("zdjecie.png", ""), KAT_OBRAZ)

	def test_brak_rozszerzenia_pada_na_mime_wideo(self):
		self.assertEqual(kategoria_pliku("nagranie_bez_rozszerzenia", "video/quicktime"), KAT_WIDEO)

	def test_brak_rozszerzenia_pada_na_mime_obrazu(self):
		self.assertEqual(kategoria_pliku("zdjecie_bez_rozszerzenia", "image/heic"), KAT_OBRAZ)

	def test_mime_application_pdf_bez_rozszerzenia(self):
		self.assertEqual(kategoria_pliku("plik_bez_rozszerzenia", "application/pdf"), KAT_DOKUMENT)

	def test_nieznany_typ_i_rozszerzenie_daje_inny(self):
		self.assertEqual(kategoria_pliku("archiwum.zip", "application/zip"), KAT_INNY)

	def test_brak_nazwy_i_typu_daje_inny(self):
		self.assertEqual(kategoria_pliku(None, None), KAT_INNY)

	def test_rozszerzenie_docx_to_dokument(self):
		self.assertEqual(kategoria_pliku("formularz.docx", ""), KAT_DOKUMENT)


class TestKlasyfikacjaAudytOze(unittest.TestCase):
	def test_slot_rozpoznany_po_url(self):
		plik = _plik(attached_to_doctype="Volteo Audyt", file_url="/private/files/rozdzielnica.jpg")
		kontekst = {
			"url_slotow_audytu": {"/private/files/rozdzielnica.jpg": "Rozdzielnica główna"},
			"url_dodatkowych": set(),
		}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_SLOT)
		self.assertEqual(wynik["zrodlo_szczegol"], "Rozdzielnica główna")
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt: Rozdzielnica główna")
		self.assertEqual(wynik["zakladka"], "audyt")

	def test_zdjecie_dodatkowe_rozpoznane_po_url(self):
		plik = _plik(attached_to_doctype="Volteo Audyt", file_url="/private/files/extra.jpg")
		kontekst = {"url_slotow_audytu": {}, "url_dodatkowych": {"/private/files/extra.jpg"}}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_DODATKOWE)
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt: zdjęcie dodatkowe")

	def test_audyt_bez_dopasowania_url_dostaje_fallback(self):
		plik = _plik(attached_to_doctype="Volteo Audyt", file_url="/private/files/nieznany.jpg")
		kontekst = {"url_slotow_audytu": {}, "url_dodatkowych": set()}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_SLOT)
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt: załącznik")


class TestKlasyfikacjaAudytCp(unittest.TestCase):
	def test_slot_cp_rozpoznany_po_url(self):
		plik = _plik(attached_to_doctype="Volteo Audyt CP", file_url="/private/files/ankieta.pdf")
		kontekst = {
			"url_slotow_cp": {"/private/files/ankieta.pdf": "Ankieta danych Czyste Powietrze"},
			"url_galerii_cp": set(),
		}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_CP_SLOT)
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt CP: Ankieta danych Czyste Powietrze")

	def test_galeria_cp_rozpoznana_po_url(self):
		plik = _plik(attached_to_doctype="Volteo Audyt CP", file_url="/private/files/galeria1.jpg")
		kontekst = {"url_slotow_cp": {}, "url_galerii_cp": {"/private/files/galeria1.jpg"}}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_CP_GALERIA)
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt CP: galeria")

	def test_cp_bez_dopasowania_dostaje_fallback(self):
		plik = _plik(attached_to_doctype="Volteo Audyt CP", file_url="/private/files/x.jpg")
		kontekst = {"url_slotow_cp": {}, "url_galerii_cp": set()}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_CP_SLOT)
		self.assertEqual(wynik["zrodlo_etykieta"], "Audyt CP: załącznik")


class TestKlasyfikacjaComment(unittest.TestCase):
	def test_komentarz_audytu_rozpoznany_po_url(self):
		plik = _plik(attached_to_doctype="Comment", file_url="/private/files/a.jpg")
		kontekst = {"url_komentarzy_audytu": {"/private/files/a.jpg"}, "url_komentarzy": set()}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_AUDYT_KOMENTARZ)

	def test_zwykly_komentarz_rozpoznany_po_url(self):
		plik = _plik(attached_to_doctype="Comment", file_url="/private/files/b.jpg")
		kontekst = {"url_komentarzy_audytu": set(), "url_komentarzy": {"/private/files/b.jpg"}}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_KOMENTARZ)

	def test_comment_bez_dopasowania_pada_na_komentarz(self):
		plik = _plik(attached_to_doctype="Comment", file_url="/private/files/nieznany.jpg")
		kontekst = {"url_komentarzy_audytu": set(), "url_komentarzy": set()}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_KOMENTARZ)


class TestKlasyfikacjaProstychRodzicow(unittest.TestCase):
	def test_communication_to_email(self):
		plik = _plik(attached_to_doctype="Communication")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_EMAIL)
		self.assertEqual(wynik["zakladka"], "attachments")

	def test_volteo_faktura_to_faktura(self):
		plik = _plik(attached_to_doctype="Volteo Faktura")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_FAKTURA)
		self.assertEqual(wynik["zakladka"], "faktury")

	def test_volteo_umowa_to_umowa_podpisana(self):
		plik = _plik(attached_to_doctype="Volteo Umowa")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_UMOWA_PODPISANA)
		self.assertEqual(wynik["zakladka"], "umowa")

	def test_volteo_kredyt_to_kredyt_podpisany(self):
		plik = _plik(attached_to_doctype="Volteo Kredyt")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_KREDYT_PODPISANY)
		self.assertEqual(wynik["zakladka"], "kredyt")

	def test_crm_lead_to_lead(self):
		plik = _plik(attached_to_doctype="CRM Lead")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_LEAD)

	def test_nieznany_rodzic_pada_na_luzem(self):
		plik = _plik(attached_to_doctype="Jakis Inny Doctype")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_LUZEM)


class TestKlasyfikacjaCrmDeal(unittest.TestCase):
	def test_montaz_zdjecie_po_znaczniku(self):
		plik = _plik(attached_to_field=ZNACZNIK_ZDJEC_MONTAZU)
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_MONTAZ_ZDJECIE)
		self.assertEqual(wynik["zakladka"], "montaz")

	def test_robocze_po_znaczniku(self):
		plik = _plik(attached_to_field=ZNACZNIK_ROBOCZY)
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_ROBOCZE)
		self.assertEqual(wynik["zrodlo_etykieta"], "Robocze")

	def test_notatka_po_znaczniku_ze_znana_zakladka(self):
		plik = _plik(attached_to_field=PREFIKS_ZNACZNIKA_NOTATKI + "abcd1234")
		kontekst = {"notatki": {"abcd1234": "Montaz"}}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_NOTATKA)
		self.assertEqual(wynik["zrodlo_szczegol"], "Montaż")
		self.assertEqual(wynik["zrodlo_etykieta"], "Notatka: Montaż")
		self.assertEqual(wynik["zakladka"], "montaz")

	def test_notatka_po_znaczniku_gdy_notatka_nieznana(self):
		# crm.volteo_notatki (W1) moze jeszcze nie istniec / notatka usunieta
		# -- klasyfikacja po samym znaczniku dziala, etykieta pada na domyslna.
		plik = _plik(attached_to_field=PREFIKS_ZNACZNIKA_NOTATKI + "usunieta")
		wynik = klasyfikuj_plik_szansy(plik, {"notatki": {}})
		self.assertEqual(wynik["zrodlo"], ZRODLO_NOTATKA)
		self.assertIsNone(wynik["zrodlo_szczegol"])
		self.assertEqual(wynik["zrodlo_etykieta"], "Notatka")
		self.assertEqual(wynik["zakladka"], "notatki")

	def test_plik_systemowy_umowy_rozpoznany_przez_callable(self):
		plik = _plik(file_name="Umowa-PRO-PV-26-0001.pdf")
		kontekst = {"systemowe": zbuduj_callable_systemowe(lambda n: True, lambda n: False)}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_UMOWA_PDF)
		self.assertEqual(wynik["zrodlo_etykieta"], "Umowa PDF")

	def test_plik_systemowy_kredytu_rozpoznany_przez_callable(self):
		plik = _plik(file_name="Formularz-kredytowy-PRO-PV-26-0001-abcd1234-20260101-000000.pdf")
		kontekst = {"systemowe": zbuduj_callable_systemowe(lambda n: False, lambda n: True)}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_KREDYT_PDF)

	def test_luzem_reklasyfikowany_do_faktury_po_url(self):
		# Duplikat: kopia pliku faktury podpieta wprost pod CRM Deal (patrz
		# docstring modulu o dedupie File po content_hash).
		plik = _plik(file_url="/private/files/faktura123.pdf")
		kontekst = {"systemowe": _systemowe_falsz, "url_faktur": {"/private/files/faktura123.pdf"}}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_FAKTURA)

	def test_luzem_reklasyfikowany_do_podpisanej_umowy_po_url(self):
		plik = _plik(file_url="/private/files/podpisana.pdf")
		kontekst = {
			"systemowe": _systemowe_falsz,
			"url_podpisanych": {"/private/files/podpisana.pdf": ZRODLO_UMOWA_PODPISANA},
		}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_UMOWA_PODPISANA)

	def test_prawdziwy_luzem_bez_zadnego_dopasowania(self):
		plik = _plik(file_url="/private/files/cokolwiek.pdf")
		kontekst = {"systemowe": _systemowe_falsz}
		wynik = klasyfikuj_plik_szansy(plik, kontekst)
		self.assertEqual(wynik["zrodlo"], ZRODLO_LUZEM)
		self.assertEqual(wynik["zrodlo_etykieta"], "Luzem")
		self.assertEqual(wynik["zakladka"], "attachments")

	def test_kontekst_bez_callable_systemowe_nie_wywala(self):
		plik = _plik(file_url="/private/files/cokolwiek.pdf")
		wynik = klasyfikuj_plik_szansy(plik, {})
		self.assertEqual(wynik["zrodlo"], ZRODLO_LUZEM)


class TestCzyWidoczneRobocze(unittest.TestCase):
	def test_wlasciciel_widzi_swoj_plik(self):
		self.assertTrue(czy_widoczne_robocze("rep@proenergy.pro", "rep@proenergy.pro"))

	def test_inny_uzytkownik_nie_widzi(self):
		self.assertFalse(czy_widoczne_robocze("rep@proenergy.pro", "kolega@proenergy.pro"))

	def test_brak_wlasciciela_nie_widoczny(self):
		self.assertFalse(czy_widoczne_robocze(None, "rep@proenergy.pro"))


def _wiersz(klucz, zrodlo, file_url="/private/files/f.pdf", **nadpisania):
	"""Buduje bezposrednio wiersz w KSZTALCIE zwracanym przez
	`klasyfikuj_plik_szansy` -- testy dedupu/sortu/flag operuja na tym
	ksztalcie wprost, niezaleznie od tego, JAK dany `zrodlo` powstal."""
	wiersz = {"klucz": klucz, "zrodlo": zrodlo, "file_url": file_url, "data": "2026-09-28 10:00:00"}
	wiersz.update(nadpisania)
	return wiersz


class TestScalPoUrl(unittest.TestCase):
	def test_faktura_wygrywa_nad_luzem(self):
		luzem = _wiersz("f1", ZRODLO_LUZEM)
		faktura = _wiersz("f2", ZRODLO_FAKTURA)
		wynik = scal_po_url([luzem, faktura])
		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["klucz"], "f2")
		self.assertEqual(wynik[0]["zrodlo"], ZRODLO_FAKTURA)

	def test_kolejnosc_wejscia_nie_wplywa_na_zwyciezce(self):
		luzem = _wiersz("f1", ZRODLO_LUZEM)
		faktura = _wiersz("f2", ZRODLO_FAKTURA)
		wynik = scal_po_url([faktura, luzem])
		self.assertEqual(wynik[0]["klucz"], "f2")

	def test_audyt_slot_wygrywa_nad_audyt_komentarz(self):
		# To samo zdjecie podpiete jako slot audytu I jako zalacznik
		# komentarza audytu -- slot (wyzszy priorytet) wygrywa.
		slot = _wiersz("s1", ZRODLO_AUDYT_SLOT)
		komentarz = _wiersz("k1", ZRODLO_AUDYT_KOMENTARZ)
		wynik = scal_po_url([komentarz, slot])
		self.assertEqual(wynik[0]["klucz"], "s1")

	def test_rozne_url_zostaja_osobnymi_wierszami(self):
		a = _wiersz("a", ZRODLO_LUZEM, file_url="/private/files/a.pdf")
		b = _wiersz("b", ZRODLO_LUZEM, file_url="/private/files/b.pdf")
		wynik = scal_po_url([a, b])
		self.assertEqual(len(wynik), 2)

	def test_brak_url_nie_collapsuje_wierszy(self):
		a = _wiersz("a", ZRODLO_EMAIL, file_url=None)
		b = _wiersz("b", ZRODLO_EMAIL, file_url=None)
		wynik = scal_po_url([a, b])
		self.assertEqual(len(wynik), 2)

	def test_nie_mutuje_wejsciowej_listy(self):
		a = _wiersz("a", ZRODLO_LUZEM)
		wejscie = [a]
		scal_po_url(wejscie)
		self.assertEqual(len(wejscie), 1)
		self.assertIs(wejscie[0], a)


class TestZbudujZrodla(unittest.TestCase):
	def test_liczy_i_pomija_zera(self):
		luzem = klasyfikuj_plik_szansy(_plik(file_url="/private/files/a.pdf"), {"systemowe": _systemowe_falsz})
		faktura = klasyfikuj_plik_szansy(_plik(attached_to_doctype="Volteo Faktura"), {})
		faktura2 = klasyfikuj_plik_szansy(
			_plik(name="f2", file_url="/private/files/f2.pdf", attached_to_doctype="Volteo Faktura"), {}
		)
		wynik = zbuduj_zrodla([luzem, faktura, faktura2])
		kluce = [w["klucz"] for w in wynik]
		self.assertIn(ZRODLO_LUZEM, kluce)
		self.assertIn(ZRODLO_FAKTURA, kluce)
		faktura_wpis = next(w for w in wynik if w["klucz"] == ZRODLO_FAKTURA)
		self.assertEqual(faktura_wpis["liczba"], 2)
		self.assertNotIn(ZRODLO_EMAIL, kluce)

	def test_kolejnosc_wedlug_priorytetu_zrodel(self):
		luzem = klasyfikuj_plik_szansy(_plik(file_url="/private/files/a.pdf"), {"systemowe": _systemowe_falsz})
		faktura = klasyfikuj_plik_szansy(_plik(attached_to_doctype="Volteo Faktura"), {})
		wynik = zbuduj_zrodla([luzem, faktura])
		self.assertEqual([w["klucz"] for w in wynik], [ZRODLO_FAKTURA, ZRODLO_LUZEM])

	def test_pusta_lista_daje_pusty_wynik(self):
		self.assertEqual(zbuduj_zrodla([]), [])


class TestPosortuj(unittest.TestCase):
	def test_domyslnie_od_najnowszych(self):
		a = _wiersz("a", ZRODLO_LUZEM, data="2026-09-01 10:00:00")
		b = _wiersz("b", ZRODLO_LUZEM, data="2026-09-28 10:00:00")
		wynik = posortuj([a, b])
		self.assertEqual([w["klucz"] for w in wynik], ["b", "a"])

	def test_asc_od_najstarszych(self):
		a = _wiersz("a", ZRODLO_LUZEM, data="2026-09-01 10:00:00")
		b = _wiersz("b", ZRODLO_LUZEM, data="2026-09-28 10:00:00")
		wynik = posortuj([a, b], kierunek="asc")
		self.assertEqual([w["klucz"] for w in wynik], ["a", "b"])

	def test_nie_mutuje_wejscia(self):
		a = _wiersz("a", ZRODLO_LUZEM, data="2026-09-01 10:00:00")
		b = _wiersz("b", ZRODLO_LUZEM, data="2026-09-28 10:00:00")
		wejscie = [a, b]
		posortuj(wejscie)
		self.assertEqual([w["klucz"] for w in wejscie], ["a", "b"])

	def test_brak_daty_ladowany_na_koniec_przy_desc(self):
		a = _wiersz("a", ZRODLO_LUZEM, data=None)
		b = _wiersz("b", ZRODLO_LUZEM, data="2026-09-28 10:00:00")
		wynik = posortuj([a, b])
		self.assertEqual([w["klucz"] for w in wynik], ["b", "a"])


class TestFlagi(unittest.TestCase):
	def test_luzem_z_prawem_zapisu_moze_usunac(self):
		wiersz = {"zrodlo": ZRODLO_LUZEM}
		wynik = flagi(wiersz, can_write=True, can_rename=False)
		self.assertTrue(wynik["mozna_usunac"])

	def test_luzem_bez_prawa_zapisu_nie_moze_usunac(self):
		wiersz = {"zrodlo": ZRODLO_LUZEM}
		wynik = flagi(wiersz, can_write=False, can_rename=False)
		self.assertFalse(wynik["mozna_usunac"])

	def test_notatka_nigdy_nie_moze_byc_usunieta_stad(self):
		wiersz = {"zrodlo": ZRODLO_NOTATKA}
		wynik = flagi(wiersz, can_write=True, can_rename=True)
		self.assertFalse(wynik["mozna_usunac"])

	def test_robocze_nigdy_nie_moze_byc_usuniete_stad(self):
		wiersz = {"zrodlo": ZRODLO_ROBOCZE}
		wynik = flagi(wiersz, can_write=True, can_rename=True)
		self.assertFalse(wynik["mozna_usunac"])

	def test_systemowy_nigdy_nie_zmienia_nazwy(self):
		for zrodlo in (ZRODLO_UMOWA_PDF, ZRODLO_KREDYT_PDF, ZRODLO_UMOWA_PODPISANA, ZRODLO_KREDYT_PODPISANY):
			wiersz = {"zrodlo": zrodlo}
			wynik = flagi(wiersz, can_write=True, can_rename=True)
			self.assertFalse(wynik["mozna_zmienic_nazwe"], zrodlo)

	def test_niesystemowy_z_can_rename_moze_zmienic_nazwe(self):
		wiersz = {"zrodlo": ZRODLO_LUZEM}
		wynik = flagi(wiersz, can_write=False, can_rename=True)
		self.assertTrue(wynik["mozna_zmienic_nazwe"])

	def test_bez_can_rename_nie_moze_zmienic_nazwy(self):
		wiersz = {"zrodlo": ZRODLO_LUZEM}
		wynik = flagi(wiersz, can_write=False, can_rename=False)
		self.assertFalse(wynik["mozna_zmienic_nazwe"])

	def test_zwraca_nowy_slownik_nie_mutuje_wejscia(self):
		wiersz = {"zrodlo": ZRODLO_LUZEM}
		wynik = flagi(wiersz, can_write=True, can_rename=True)
		self.assertNotIn("mozna_usunac", wiersz)
		self.assertIsNot(wynik, wiersz)


class TestEtykietyIZakladkiPomocnicze(unittest.TestCase):
	def test_etykieta_zrodla_stala(self):
		self.assertEqual(etykieta_zrodla(ZRODLO_FAKTURA), "Faktura")

	def test_etykieta_zrodla_z_placeholderem_i_szczegolem(self):
		self.assertEqual(etykieta_zrodla(ZRODLO_AUDYT_SLOT, "Dach"), "Audyt: Dach")

	def test_etykieta_zrodla_z_placeholderem_bez_szczegolu(self):
		self.assertEqual(etykieta_zrodla(ZRODLO_AUDYT_SLOT, None), "Audyt: załącznik")

	def test_etykieta_zakladki_notatki_znana(self):
		self.assertEqual(etykieta_zakladki_notatki("Montaz"), "Montaż")

	def test_etykieta_zakladki_notatki_brak(self):
		self.assertIsNone(etykieta_zakladki_notatki(None))

	def test_hash_zakladki_notatki_znana(self):
		self.assertEqual(hash_zakladki_notatki("Kredyt"), "kredyt")

	def test_hash_zakladki_notatki_brak_pada_na_notatki(self):
		self.assertEqual(hash_zakladki_notatki(None), "notatki")

	def test_zakladka_dla_zrodla_luzem(self):
		self.assertEqual(zakladka_dla_zrodla(ZRODLO_LUZEM), "attachments")

	def test_zakladka_dla_zrodla_notatka_z_kodem(self):
		self.assertEqual(zakladka_dla_zrodla(ZRODLO_NOTATKA, "Umowa"), "umowa")

	def test_zakladka_dla_zrodla_notatka_bez_kodu(self):
		self.assertEqual(zakladka_dla_zrodla(ZRODLO_NOTATKA, None), "notatki")


class TestKatalogZrodel(unittest.TestCase):
	def test_kazde_zrodlo_ma_unikalny_klucz(self):
		klucze = [zrodlo["klucz"] for zrodlo in ZRODLA]
		self.assertEqual(len(klucze), len(set(klucze)))

	def test_siedemnascie_zrodel(self):
		self.assertEqual(len(ZRODLA), 17)


if __name__ == "__main__":
	unittest.main()
