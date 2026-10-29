# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import re
import unittest
from datetime import datetime, timedelta

from crm.volteo_sms import (
	STATUS_BLAD,
	STATUS_POMINIETY,
	STATUS_TEST,
	STATUS_WYSLANY,
	TRESC_DOMYSLNA,
	TTL_REZERWACJI_SEK,
	data_z_info,
	dlugosc_gsm7,
	interpretuj_odpowiedz,
	klucz_rezerwacji_numeru,
	liczba_czesci_sms,
	numer_do_smsapi,
	przetworz,
	przygotuj_tresc,
	transliteruj_gsm7,
	wzor_info_dnia,
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


def wywolaj(zwolnienia=None, **nadpisz):
	zwolnienia = [] if zwolnienia is None else zwolnienia
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
		limit_dzienny=50,
		wyslane_dzis=0,
		rezerwuj=lambda n: True,
		zwolnij=zwolnienia.append,
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

	def test_backtick_na_apostrof(self):
		self.assertEqual(transliteruj_gsm7("a`b"), "a'b")

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
		self.assertIn("2 części", ostrz)

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
			{"to": "48604932720", "message": "tresc", "from": "ProEnergy", "format": "json", "encoding": "utf-8", "nounicode": "1"},
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

	def test_wzor_info_dnia_pasuje_do_zbuduj_info(self):
		wzor = wzor_info_dnia(TERAZ)
		self.assertEqual(wzor, "%[2026-10-29 %]")
		regex = re.compile("^" + ".*".join(re.escape(c) for c in wzor.split("%")) + "$")
		self.assertTrue(regex.match(zbuduj_info("SMSAPI id X", TERAZ)))
		self.assertFalse(regex.match(zbuduj_info("SMSAPI id X", TERAZ - timedelta(days=1))))

	def test_ostrzezenie_nie_psuje_daty(self):
		self.assertEqual(data_z_info(zbuduj_info("SMSAPI id X; Treść SMS ma 200 znaków", TERAZ)), TERAZ)

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
		d = self.baza(wlaczone=False)
		self.assertEqual(d.powod, "wyłączone")
		self.assertFalse(d.zapisz)
		self.assertTrue(self.baza(token_ustawiony=False).zapisz)
		self.assertIn("token", self.baza(token_ustawiony=False).powod)
		self.assertIn("numer", self.baza(numer=None).powod)
		self.assertIn("już wysłany", self.baza(status_leada=STATUS_WYSLANY).powod)

	def test_okno_24h(self):
		swiezy = TERAZ - timedelta(hours=23, minutes=59)
		stary = TERAZ - timedelta(hours=24, minutes=1)
		self.assertFalse(self.baza(daty_innych_wyslanych=[swiezy]).wyslij)
		self.assertTrue(self.baza(daty_innych_wyslanych=[stary]).wyslij)
		self.assertFalse(self.baza(daty_innych_wyslanych=[stary, swiezy]).wyslij)

	def test_limit_dzienny(self):
		d = self.baza(limit_dzienny=50, wyslane_dzis=50)
		self.assertFalse(d.wyslij)
		self.assertIn("limit dzienny 50", d.powod)
		self.assertTrue(self.baza(limit_dzienny=50, wyslane_dzis=49).wyslij)
		self.assertFalse(self.baza(limit_dzienny=0, wyslane_dzis=0).wyslij)

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
		zapis, zw = [], []
		w = wywolaj(zwolnienia=zw, tryb_testowy=True, http_post=fake_http(200, {"list": [{"id": "T1"}]}, zapis))
		self.assertEqual(zapis[0][1]["test"], "1")
		self.assertEqual(w.status, STATUS_TEST)
		self.assertIn("test OK", w.info)
		self.assertNotIn("(tryb testowy)", w.info)
		self.assertIn("nic nie wysłano", w.slad)
		self.assertEqual(zw, ["48604932720"])

	def test_wyslana_tresc_jest_transliterowana(self):
		zapis = []
		wywolaj(tresc_surowa="Dziękujemy, Państwo", http_post=fake_http(200, {"list": [{"id": "1"}]}, zapis))
		self.assertEqual(zapis[0][1]["message"], "Dziekujemy, Panstwo")

	def test_wylaczone_nic_nie_zapisuje_i_nie_rezerwuje(self):
		zapis, rez = [], []

		def rezerwuj(n):
			rez.append(n)
			return True

		w = wywolaj(wlaczone=False, rezerwuj=rezerwuj, http_post=fake_http(200, {}, zapis))
		self.assertIs(w.zapisz, False)
		self.assertEqual((w.status, w.info, w.slad), ("", "", ""))
		self.assertEqual(zapis, [])
		self.assertEqual(rez, [])

	def test_parametr_nounicode(self):
		zapis = []
		wywolaj(http_post=fake_http(200, {"list": [{"id": "1"}]}, zapis))
		self.assertEqual(zapis[0][1]["nounicode"], "1")

	def test_rezerwacja_zajeta(self):
		zapis = []
		w = wywolaj(rezerwuj=lambda n: False, http_post=fake_http(200, {}, zapis))
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("rezerwację", w.info)
		self.assertEqual(zapis, [])

	def test_redis_niedostepny_fail_open(self):
		zapis, zw = [], []
		w = wywolaj(zwolnienia=zw, rezerwuj=lambda n: None, http_post=fake_http(200, {"list": [{"id": "1"}]}, zapis))
		self.assertEqual(w.status, STATUS_WYSLANY)
		self.assertEqual(len(zapis), 1)
		self.assertEqual(zw, [])
		self.assertTrue(w.redis_niedostepny)

	def test_blad_smsapi_zwalnia_rezerwacje(self):
		zw = []
		w = wywolaj(zwolnienia=zw, http_post=fake_http(200, {"error": 101, "message": "x"}))
		self.assertEqual(w.status, STATUS_BLAD)
		self.assertEqual(zw, ["48604932720"])

	def test_wyjatek_http_zwalnia_rezerwacje(self):
		zw = []

		def wybucha(url, dane, naglowki):
			raise ConnectionError("x")

		w = wywolaj(zwolnienia=zw, http_post=wybucha)
		self.assertEqual(w.status, STATUS_BLAD)
		self.assertEqual(zw, ["48604932720"])

	def test_sukces_nie_zwalnia_rezerwacji(self):
		zw = []
		w = wywolaj(zwolnienia=zw)
		self.assertEqual(w.status, STATUS_WYSLANY)
		self.assertEqual(zw, [])
		self.assertFalse(w.redis_niedostepny)

	def test_limit_dzienny_pomija(self):
		zapis = []
		w = wywolaj(limit_dzienny=50, wyslane_dzis=50, http_post=fake_http(200, {}, zapis))
		self.assertEqual(w.status, STATUS_POMINIETY)
		self.assertIn("wyczerpany limit dzienny 50 SMS", w.info)
		self.assertTrue(w.limit_wyczerpany)
		self.assertEqual(zapis, [])
		self.assertEqual(wywolaj(limit_dzienny=50, wyslane_dzis=49).status, STATUS_WYSLANY)
		self.assertEqual(wywolaj(limit_dzienny=0).status, STATUS_POMINIETY)

	def test_klucz_i_ttl_rezerwacji(self):
		self.assertEqual(klucz_rezerwacji_numeru("48604932720"), "volteo:sms_powitalny:numer:48604932720")
		self.assertEqual(TTL_REZERWACJI_SEK, 86400)

	def test_brak_tokenu(self):
		w = wywolaj(token=None)
		self.assertTrue(w.zapisz)
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
		self.assertIn("2 części", w.ostrzezenie)
		self.assertIn("2 części", w.info)
		self.assertEqual(data_z_info(w.info), TERAZ)

	def test_nie_mutuje_wejscia(self):
		daty = [TERAZ - timedelta(days=3)]
		kopia = list(daty)
		wywolaj(daty_innych_wyslanych=daty)
		self.assertEqual(daty, kopia)


if __name__ == "__main__":
	unittest.main()
