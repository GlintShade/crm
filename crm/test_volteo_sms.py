# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import unittest
from datetime import datetime, timedelta

from crm.volteo_sms import (
	STATUS_BLAD,
	STATUS_POMINIETY,
	STATUS_WYSLANY,
	TRESC_DOMYSLNA,
	data_z_info,
	dlugosc_gsm7,
	interpretuj_odpowiedz,
	liczba_czesci_sms,
	numer_do_smsapi,
	przetworz,
	przygotuj_tresc,
	transliteruj_gsm7,
	zbuduj_info,
	zbuduj_parametry,
	zdecyduj_wysylke,
)

TERAZ = datetime(2026, 10, 29, 12, 0, 0)
TOKEN = "sekretny-token-123"


def fake_http(kod, odp, zapis=None):
	def _http(url, dane, naglowki):
		if zapis is not None:
			zapis.append((url, dane, naglowki))
		return kod, odp

	return _http


def wywolaj(**nadpisz):
	baza = dict(
		wlaczone=True,
		token=TOKEN,
		nadawca="ProEnergy",
		tresc_surowa=TRESC_DOMYSLNA,
		tryb_testowy=False,
		mobile_no="+48604932720",
		status_leada=None,
		daty_innych_wyslanych=[],
		teraz=TERAZ,
		http_post=fake_http(200, {"count": 1, "list": [{"id": "ABC123", "status": "QUEUE"}]}),
	)
	baza.update(nadpisz)
	return przetworz(**baza)


class TestTransliteracja(unittest.TestCase):
	def test_polskie_znaki(self):
		self.assertEqual(transliteruj_gsm7("zażółć gęślą jaźń"), "zazolc gesla jazn")
		self.assertEqual(transliteruj_gsm7("ĄĆĘŁŃÓŚŹŻ"), "ACELNOSZZ")

	def test_ascii_bez_zmian(self):
		self.assertEqual(transliteruj_gsm7("Dzien dobry, ProEnergy!"), "Dzien dobry, ProEnergy!")

	def test_pauzy_i_cudzyslowy(self):
		self.assertEqual(transliteruj_gsm7("a\u2013b\u2014c"), "a-b-c")
		self.assertEqual(transliteruj_gsm7("\u201cx\u201d \u2019"), '"x" \'')

	def test_obce_znaki_przez_nfkd(self):
		self.assertEqual(transliteruj_gsm7("café"), "cafe")

	def test_emoji_pomijane(self):
		self.assertEqual(transliteruj_gsm7("ok \U0001f600"), "ok ")

	def test_puste(self):
		self.assertEqual(transliteruj_gsm7(""), "")
		self.assertEqual(transliteruj_gsm7(None), "")


class TestCzesci(unittest.TestCase):
	def test_domyslna_tresc_to_jedna_czesc(self):
		self.assertEqual(liczba_czesci_sms(TRESC_DOMYSLNA), 1)
		self.assertLessEqual(len(TRESC_DOMYSLNA), 160)
		self.assertTrue(TRESC_DOMYSLNA.isascii())

	def test_granice(self):
		self.assertEqual(liczba_czesci_sms("a" * 160), 1)
		self.assertEqual(liczba_czesci_sms("a" * 161), 2)
		self.assertEqual(liczba_czesci_sms("a" * 306), 2)
		self.assertEqual(liczba_czesci_sms("a" * 307), 3)
		self.assertEqual(liczba_czesci_sms(""), 0)

	def test_rozszerzenia_licza_sie_podwojnie(self):
		self.assertEqual(dlugosc_gsm7("[a]"), 5)
		self.assertEqual(liczba_czesci_sms("[" * 81), 2)

	def test_ostrzezenie_przy_dlugiej_tresci(self):
		tresc, ostrz = przygotuj_tresc("ą" * 200)
		self.assertEqual(tresc, "a" * 200)
		self.assertIn("2 czesci", ostrz)

	def test_brak_ostrzezenia_dla_krotkiej(self):
		tresc, ostrz = przygotuj_tresc("Dzień dobry ąę")
		self.assertEqual(tresc, "Dzien dobry ae")
		self.assertIsNone(ostrz)


class TestNumer(unittest.TestCase):
	def test_formaty(self):
		self.assertEqual(numer_do_smsapi("+48604932720"), "48604932720")
		self.assertEqual(numer_do_smsapi("48604932720"), "48604932720")
		self.assertEqual(numer_do_smsapi("+48 604 932 720"), "48604932720")

	def test_niepoprawne(self):
		for zly in (None, "", "604932720", "+4860493272", "+49604932720", "+48abc932720", "+486049327200"):
			self.assertIsNone(numer_do_smsapi(zly), zly)


class TestParametry(unittest.TestCase):
	def test_bez_testu(self):
		p = zbuduj_parametry("48604932720", "tresc", "ProEnergy", False)
		self.assertEqual(
			p,
			{"to": "48604932720", "message": "tresc", "from": "ProEnergy", "format": "json", "encoding": "utf-8"},
		)

	def test_z_testem(self):
		self.assertEqual(zbuduj_parametry("48604932720", "t", "P", True)["test"], "1")


class TestOdpowiedz(unittest.TestCase):
	def test_sukces(self):
		w = interpretuj_odpowiedz(200, {"count": 1, "list": [{"id": "X1", "points": 0.16, "status": "QUEUE"}]})
		self.assertTrue(w.ok)
		self.assertEqual(w.id_wiadomosci, "X1")

	def test_blad_z_kodem(self):
		w = interpretuj_odpowiedz(200, {"error": 101, "message": "Authorization failed"})
		self.assertFalse(w.ok)
		self.assertEqual(w.kod, "101")
		self.assertIn("101", w.powod)
		self.assertIn("Authorization failed", w.powod)

	def test_blad_http_401(self):
		w = interpretuj_odpowiedz(401, {"message": "Authorization failed", "error": "authorization_failed"})
		self.assertFalse(w.ok)
		self.assertEqual(w.kod, "authorization_failed")

	def test_blad_http_bez_kodu(self):
		w = interpretuj_odpowiedz(400, {"message": "zle"})
		self.assertFalse(w.ok)
		self.assertIn("HTTP 400", w.powod)

	def test_nieczytelna(self):
		self.assertFalse(interpretuj_odpowiedz(502, None).ok)
		self.assertFalse(interpretuj_odpowiedz(200, {"count": 0, "list": []}).ok)


class TestInfoIData(unittest.TestCase):
	def test_okrazenie(self):
		self.assertEqual(data_z_info(zbuduj_info("SMSAPI id X", TERAZ)), TERAZ)

	def test_brak_daty(self):
		self.assertIsNone(data_z_info(None))
		self.assertIsNone(data_z_info("bez daty"))
		self.assertIsNone(data_z_info("x [2026-13-45 99:99:99]"))


class TestDecyzja(unittest.TestCase):
	def baza(self, **n):
		d = dict(
			wlaczone=True,
			token_ustawiony=True,
			numer="48604932720",
			status_leada=None,
			daty_innych_wyslanych=[],
			teraz=TERAZ,
		)
		d.update(n)
		return zdecyduj_wysylke(**d)

	def test_wysylka(self):
		self.assertTrue(self.baza().wyslij)

	def test_pominiecia(self):
		self.assertEqual(self.baza(wlaczone=False).powod, "wyłączone")
		self.assertIn("token", self.baza(token_ustawiony=False).powod)
		self.assertIn("numer", self.baza(numer=None).powod)
		self.assertIn("już wysłany", self.baza(status_leada=STATUS_WYSLANY).powod)

	def test_okno_24h(self):
		swiezy = TERAZ - timedelta(hours=23, minutes=59)
		stary = TERAZ - timedelta(hours=24, minutes=1)
		self.assertFalse(self.baza(daty_innych_wyslanych=[swiezy]).wyslij)
		self.assertTrue(self.baza(daty_innych_wyslanych=[stary]).wyslij)
		self.assertFalse(self.baza(daty_innych_wyslanych=[stary, swiezy]).wyslij)

	def test_status_blad_nie_blokuje(self):
		self.assertTrue(self.baza(status_leada=STATUS_BLAD).wyslij)


class TestPrzetworz(unittest.TestCase):
	def test_sukces(self):
		zapis = []
		w = wywolaj(http_post=fake_http(200, {"list": [{"id": "ABC123"}]}, zapis))
		self.assertEqual(w.status, STATUS_WYSLANY)
		self.assertIn("ABC123", w.info)
		self.assertEqual(data_z_info(w.info), TERAZ)
		self.assertEqual(w.slad, "SMS powitalny wysłany na +48604932720")
		url, dane, naglowki = zapis[0]
		self.assertEqual(url, "https://api.smsapi.pl/sms.do")
		self.assertEqual(dane["to"], "48604932720")
		self.assertNotIn("test", dane)
		self.assertEqual(naglowki["Authorization"], f"Bearer {TOKEN}")

	def test_tryb_testowy(self):
		zapis = []
		w = wywolaj(tryb_testowy=True, http_post=fake_http(200, {"list": [{"id": "T1"}]}, zapis))
		self.assertEqual(zapis[0][1]["test"], "1")
		self.assertIn("(tryb testowy)", w.info)
		self.assertIn("(tryb testowy)", w.slad)

	def test_wyslana_tresc_jest_transliterowana(self):
		zapis = []
		wywolaj(tresc_surowa="Dziękujemy, Państwo", http_post=fake_http(200, {"list": [{"id": "1"}]}, zapis))
		self.assertEqual(zapis[0][1]["message"], "Dziekujemy, Panstwo")

	def test_wylaczone_nie_wola_http(self):
		zapis = []
		w = wywolaj(wlaczone=False, http_post=fake_http(200, {}, zapis))
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("Pominięty (wyłączone)", w.info)
		self.assertEqual(zapis, [])

	def test_brak_tokenu(self):
		w = wywolaj(token=None)
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("brak tokenu", w.info)

	def test_zly_numer(self):
		w = wywolaj(mobile_no="123")
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("numer", w.info)

	def test_juz_wyslany(self):
		self.assertEqual(wywolaj(status_leada=STATUS_WYSLANY).status, STATUS_POMINIETY)

	def test_dubel_numeru(self):
		w = wywolaj(daty_innych_wyslanych=[TERAZ - timedelta(hours=2)])
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("24 godzin", w.info)

	def test_pusta_tresc(self):
		w = wywolaj(tresc_surowa="   ")
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("pusta treść", w.info)

	def test_blad_smsapi_bez_tokenu_w_tekstach(self):
		w = wywolaj(http_post=fake_http(401, {"error": "authorization_failed", "message": "Authorization failed"}))
		self.assertEqual(w.status, STATUS_BLAD)
		self.assertIn("authorization_failed", w.info)
		self.assertIsNotNone(w.blad_do_logu)
		for tekst in (w.info, w.slad, w.blad_do_logu):
			self.assertNotIn(TOKEN, tekst)

	def test_wyjatek_http_nie_wycieka_tokenu(self):
		def wybucha(url, dane, naglowki):
			raise ConnectionError(f"timeout przy {naglowki['Authorization']}")

		w = wywolaj(http_post=wybucha)
		self.assertEqual(w.status, STATUS_BLAD)
		self.assertIn("ConnectionError", w.info)
		for tekst in (w.info, w.slad, w.blad_do_logu):
			self.assertNotIn(TOKEN, tekst)

	def test_ostrzezenie_o_dlugiej_tresci(self):
		w = wywolaj(tresc_surowa="ą" * 200)
		self.assertEqual(w.status, STATUS_WYSLANY)
		self.assertIn("2 czesci", w.ostrzezenie)

	def test_nie_mutuje_wejscia(self):
		daty = [TERAZ - timedelta(days=3)]
		kopia = list(daty)
		wywolaj(daty_innych_wyslanych=daty)
		self.assertEqual(daty, kopia)


if __name__ == "__main__":
	unittest.main()
