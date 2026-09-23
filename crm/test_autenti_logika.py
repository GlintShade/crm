import unittest
from datetime import datetime, timedelta

from crm.integrations.autenti.logika import (
	DECYZJA_NOWY_PROCES,
	DECYZJA_ODZYSKAJ,
	KOMUNIKAT_TIMEOUT_WYSYLANIA_BEZ_PROCESU,
	PENDING_REMOTE_STATUSES,
	SEND_BLOCKED_STATUSES,
	STATUS_MAP,
	WYSYLANIE_TIMEOUT_MIN,
	ZALEGLY_PODPISANY_PLIK_LOG_MIN,
	czy_legacy_kredyt,
	czy_logowac_brak_podpisanego_pliku,
	czy_logowac_nierozpoznany_status,
	czy_wysylanie_przekroczylo_timeout,
	decyzja_ponownej_wysylki,
	komunikat_bledu_wysylki,
	komunikat_nierozpoznanego_statusu,
	mozna_wyslac,
	nazwa_pliku_kredytu,
	nazwa_pliku_kredytu_podpisanego,
	nazwa_pliku_podpisanego,
	nazwa_pliku_umowy,
	prefiks_pliku_kredytu,
	tytul_dokumentu,
	tytul_dokumentu_kredytu,
	wybierz_id_podpisanego_pliku,
	zbuduj_odbiorcow,
)


class TestAutentiLogika(unittest.TestCase):
	def test_a_status_map_kompletnosc(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			STATUS_MAP,
			{
				"COMPLETED": "Podpisana",
				"REJECTED": "Odrzucona",
				"EXPIRED": "Wygasła",
				"WITHDRAWN": "Wycofana",
			},
		)
		# Mapowane statusy i statusy oczekujące (nieterminalne) nigdy się nie pokrywają.
		self.assertFalse(set(STATUS_MAP) & set(PENDING_REMOTE_STATUSES))

	def test_b_mozna_wyslac_brak_wyslania(self: "TestAutentiLogika") -> None:
		self.assertTrue(mozna_wyslac(None))
		self.assertTrue(mozna_wyslac(""))

	def test_c_mozna_wyslac_statusy_zablokowane(self: "TestAutentiLogika") -> None:
		for status in SEND_BLOCKED_STATUSES:
			with self.subTest(status=status):
				self.assertFalse(mozna_wyslac(status))

	def test_d_mozna_wyslac_statusy_do_ponowienia(self: "TestAutentiLogika") -> None:
		for status in ("Błąd", "Odrzucona", "Wygasła", "Wycofana"):
			with self.subTest(status=status):
				self.assertTrue(mozna_wyslac(status))

	def test_e_mozna_wyslac_nierozpoznany_status(self: "TestAutentiLogika") -> None:
		self.assertFalse(mozna_wyslac("Coś nieznanego"))

	def test_f_tytul_dokumentu_normalny(self: "TestAutentiLogika") -> None:
		self.assertEqual(tytul_dokumentu("Jan Kowalski"), "Umowa ProEnergy - Jan Kowalski")
		self.assertIn("-", tytul_dokumentu("Jan Kowalski"))
		self.assertNotIn("—", tytul_dokumentu("Jan Kowalski"))

	def test_g_tytul_dokumentu_puste_imie(self: "TestAutentiLogika") -> None:
		self.assertEqual(tytul_dokumentu(None), "Umowa ProEnergy")
		self.assertEqual(tytul_dokumentu(""), "Umowa ProEnergy")
		self.assertNotIn("-", tytul_dokumentu(None))
		self.assertNotIn("—", tytul_dokumentu(None))

	def test_h_nazwa_pliku_umowy(self: "TestAutentiLogika") -> None:
		self.assertEqual(nazwa_pliku_umowy("PRO/CP/26/0007"), "Umowa-PRO-CP-26-0007.pdf")

	def test_i_nazwa_pliku_podpisanego(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_podpisanego("PRO/CP/26/0007"), "Umowa-PRO-CP-26-0007-podpisana.pdf"
		)

	def test_j_zbuduj_odbiorcow_pelny_komplet(self: "TestAutentiLogika") -> None:
		klient = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": "jan.kowalski@example.com",
		}
		prezes = {
			"first_name": "Leszek",
			"last_name": "Furmann",
			"full_name": "Leszek Furmann",
			"email": "l.furmann@proenergy.pro",
		}
		handlowiec = {
			"first_name": "Grzegorz",
			"last_name": "Furmann",
			"full_name": "Grzegorz Furmann",
			"email": "g.furmann@proenergy.pro",
		}
		archiwum = {
			"first_name": "Archiwum",
			"last_name": "ProEnergy",
			"full_name": "Archiwum ProEnergy",
			"email": "umowy@proenergy.pro",
		}

		wynik = zbuduj_odbiorcow(klient, prezes, handlowiec, archiwum)

		self.assertEqual(len(wynik), 4)
		self.assertEqual([o["zrodlo"] for o in wynik], ["klient", "prezes", "handlowiec", "archiwum"])
		self.assertEqual([o["role"] for o in wynik], ["SIGNER", "SIGNER", "VIEWER", "VIEWER"])
		for oczekiwany, otrzymany in zip(
			(klient, prezes, handlowiec, archiwum), wynik, strict=True
		):
			self.assertEqual(otrzymany["first_name"], oczekiwany["first_name"])
			self.assertEqual(otrzymany["last_name"], oczekiwany["last_name"])
			self.assertEqual(otrzymany["full_name"], oczekiwany["full_name"])
			self.assertEqual(otrzymany["email"], oczekiwany["email"])
			self.assertEqual(set(otrzymany.keys()), {"first_name", "last_name", "full_name", "email", "role", "zrodlo"})

	def test_k_zbuduj_odbiorcow_dedupe_klient_rowny_prezesowi(self: "TestAutentiLogika") -> None:
		wspolny_email = "prezes@proenergy.pro"
		klient = {
			"first_name": "Leszek",
			"last_name": "Furmann",
			"full_name": "Leszek Furmann",
			"email": wspolny_email,
		}
		prezes = {
			"first_name": "Leszek",
			"last_name": "Furmann",
			"full_name": "Leszek Furmann",
			"email": wspolny_email,
		}

		wynik = zbuduj_odbiorcow(klient, prezes, None, None)

		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["zrodlo"], "klient")
		self.assertEqual(wynik[0]["role"], "SIGNER")

	def test_l_zbuduj_odbiorcow_dedupe_handlowiec_rowny_klientowi(self: "TestAutentiLogika") -> None:
		wspolny_email = "jan.kowalski@example.com"
		klient = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": wspolny_email,
		}
		handlowiec = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": wspolny_email,
		}

		wynik = zbuduj_odbiorcow(klient, None, handlowiec, None)

		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["zrodlo"], "klient")
		self.assertEqual(wynik[0]["role"], "SIGNER")

	def test_m_zbuduj_odbiorcow_none_handlowiec_pomijany(self: "TestAutentiLogika") -> None:
		klient = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": "jan.kowalski@example.com",
		}

		wynik = zbuduj_odbiorcow(klient, None, None, None)

		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["zrodlo"], "klient")

	def test_n_zbuduj_odbiorcow_pusty_email_archiwum_pomijany(self: "TestAutentiLogika") -> None:
		klient = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": "jan.kowalski@example.com",
		}
		archiwum_pusty = {
			"first_name": "Archiwum",
			"last_name": "ProEnergy",
			"full_name": "Archiwum ProEnergy",
			"email": "   ",
		}

		wynik = zbuduj_odbiorcow(klient, None, None, archiwum_pusty)

		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["zrodlo"], "klient")

	def test_o_zbuduj_odbiorcow_dedupe_bez_rozroznienia_wielkosci_liter(
		self: "TestAutentiLogika",
	) -> None:
		klient = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": "Jan.Kowalski@Example.com",
		}
		handlowiec = {
			"first_name": "Jan",
			"last_name": "Kowalski",
			"full_name": "Jan Kowalski",
			"email": "jan.kowalski@example.com",
		}

		wynik = zbuduj_odbiorcow(klient, None, handlowiec, None)

		self.assertEqual(len(wynik), 1)
		self.assertEqual(wynik[0]["zrodlo"], "klient")
		self.assertEqual(wynik[0]["email"], "Jan.Kowalski@Example.com")

	def test_p_tytul_dokumentu_kredytu_normalny(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			tytul_dokumentu_kredytu("Jan Kowalski"), "Formularz kredytowy ProEnergy - Jan Kowalski"
		)
		self.assertIn("-", tytul_dokumentu_kredytu("Jan Kowalski"))
		self.assertNotIn("—", tytul_dokumentu_kredytu("Jan Kowalski"))

	def test_q_tytul_dokumentu_kredytu_puste_imie(self: "TestAutentiLogika") -> None:
		self.assertEqual(tytul_dokumentu_kredytu(None), "Formularz kredytowy ProEnergy")
		self.assertEqual(tytul_dokumentu_kredytu(""), "Formularz kredytowy ProEnergy")
		self.assertEqual(tytul_dokumentu_kredytu("   "), "Formularz kredytowy ProEnergy")
		self.assertNotIn("-", tytul_dokumentu_kredytu(None))
		self.assertNotIn("—", tytul_dokumentu_kredytu(None))

	def test_r_prefiks_pliku_kredytu_legacy(self: "TestAutentiLogika") -> None:
		# Rekord legacy: kredyt_name == deal (nazwa rekordu sprzed migracji na
		# formularze 1:N, ops#159). Stary prefiks bez sufiksu, bajt w bajt jak
		# przed migracją: pięć istniejących produkcyjnych plików musi dalej
		# pasować.
		deal = "PRO/PVME/26/1021"
		self.assertEqual(
			prefiks_pliku_kredytu(deal, deal), "Formularz-kredytowy-PRO-PVME-26-1021"
		)

	def test_r2_prefiks_pliku_kredytu_hash(self: "TestAutentiLogika") -> None:
		# Rekord hash: kredyt_name różne od deal (założony po migracji na
		# formularze 1:N). Nowy prefiks z 8-znakowym sufiksem nazwy rekordu.
		self.assertEqual(
			prefiks_pliku_kredytu("PRO/PVME/26/1021", "a1b2c3d4e5"),
			"Formularz-kredytowy-PRO-PVME-26-1021-a1b2c3d4",
		)

	def test_r3_prefiks_pliku_kredytu_hash_krotszy_niz_8_znakow(
		self: "TestAutentiLogika",
	) -> None:
		# Nazwa rekordu krótsza niż 8 znaków (nie powinno się zdarzyć dla
		# prawdziwego hasha Frappe, ale wycinek [:8] nie rzuca wyjątku i po
		# prostu bierze cały string).
		self.assertEqual(
			prefiks_pliku_kredytu("PRO/PVME/26/1021", "ab12"),
			"Formularz-kredytowy-PRO-PVME-26-1021-ab12",
		)

	def test_r4_prefiks_pliku_kredytu_hash_bez_ukosnikow_nie_normalizowany(
		self: "TestAutentiLogika",
	) -> None:
		# Sufiks NIE przechodzi przez .replace('/', '-'): hash names nie mają
		# ukośników, więc gdyby ktoś kiedyś podał tu coś z ukośnikiem (błąd
		# wywołującego), musi to być widoczne w nazwie pliku, nie po cichu
		# znormalizowane jak deal.
		self.assertEqual(
			prefiks_pliku_kredytu("PRO/PVME/26/1021", "ab/cd1234"),
			"Formularz-kredytowy-PRO-PVME-26-1021-ab/cd123",
		)

	def test_r5_prefiks_pliku_kredytu_dwa_hashe_rozne_prefiksy(
		self: "TestAutentiLogika",
	) -> None:
		# Dwa różne formularze (rekordy Volteo Kredyt) na TEJ SAMEJ szansie
		# muszą dostać ROZŁĄCZNE prefiksy, to jest cały sens ops#159:
		# regeneracja/wysyłka jednego formularza nie może po cichu
		# skasować/podpiąć plik drugiego.
		deal = "PRO/PVME/26/1021"
		prefiks_a = prefiks_pliku_kredytu(deal, "aaaaaaaaaa")
		prefiks_b = prefiks_pliku_kredytu(deal, "bbbbbbbbbb")
		self.assertNotEqual(prefiks_a, prefiks_b)
		self.assertFalse(prefiks_b.startswith(prefiks_a))
		self.assertFalse(prefiks_a.startswith(prefiks_b))

	def test_r6_czy_legacy_kredyt(self: "TestAutentiLogika") -> None:
		deal = "PRO/PVME/26/1021"
		self.assertTrue(czy_legacy_kredyt(deal, deal))
		self.assertFalse(czy_legacy_kredyt(deal, "a1b2c3d4e5"))
		self.assertFalse(czy_legacy_kredyt(deal, ""))

	def test_s_nazwa_pliku_kredytu_legacy(self: "TestAutentiLogika") -> None:
		deal = "PRO/PVME/26/1021"
		self.assertEqual(
			nazwa_pliku_kredytu(deal, deal), "Formularz-kredytowy-PRO-PVME-26-1021.pdf"
		)

	def test_s2_nazwa_pliku_kredytu_hash(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_kredytu("PRO/PVME/26/1021", "a1b2c3d4e5"),
			"Formularz-kredytowy-PRO-PVME-26-1021-a1b2c3d4.pdf",
		)

	def test_t_nazwa_pliku_kredytu_podpisanego_legacy(self: "TestAutentiLogika") -> None:
		deal = "PRO/PVME/26/1021"
		self.assertEqual(
			nazwa_pliku_kredytu_podpisanego(deal, deal),
			"Formularz-kredytowy-PRO-PVME-26-1021-podpisany.pdf",
		)

	def test_t2_nazwa_pliku_kredytu_podpisanego_hash(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_kredytu_podpisanego("PRO/PVME/26/1021", "a1b2c3d4e5"),
			"Formularz-kredytowy-PRO-PVME-26-1021-a1b2c3d4-podpisany.pdf",
		)

	def test_u_nazwy_plikow_kredytu_dziela_wspolny_prefiks_legacy(
		self: "TestAutentiLogika",
	) -> None:
		# Odpytywanie Autenti po prefiksie (LIKE) i sprzątanie starych plików
		# formularza kredytowego w `crm/api/kredyt.py` zależą od tego, że OBIE
		# nazwy zaczynają się dokładnie od `prefiks_pliku_kredytu(deal, name)`:
		# rozjazd tu po cichu psuje dopasowanie w obu miejscach.
		deal = "PRO/PVME/26/1021"
		prefiks = prefiks_pliku_kredytu(deal, deal)
		self.assertTrue(nazwa_pliku_kredytu(deal, deal).startswith(prefiks))
		self.assertTrue(nazwa_pliku_kredytu_podpisanego(deal, deal).startswith(prefiks))

	def test_u2_nazwy_plikow_kredytu_dziela_wspolny_prefiks_hash(
		self: "TestAutentiLogika",
	) -> None:
		deal = "PRO/PVME/26/1021"
		kredyt_name = "a1b2c3d4e5"
		prefiks = prefiks_pliku_kredytu(deal, kredyt_name)
		self.assertTrue(nazwa_pliku_kredytu(deal, kredyt_name).startswith(prefiks))
		self.assertTrue(
			nazwa_pliku_kredytu_podpisanego(deal, kredyt_name).startswith(prefiks)
		)


	def test_v_decyzja_ponownej_wysylki_processing_odzyskaj(self: "TestAutentiLogika") -> None:
		self.assertEqual(decyzja_ponownej_wysylki("PROCESSING"), DECYZJA_ODZYSKAJ)

	def test_w_decyzja_ponownej_wysylki_completed_odzyskaj(self: "TestAutentiLogika") -> None:
		self.assertEqual(decyzja_ponownej_wysylki("COMPLETED"), DECYZJA_ODZYSKAJ)

	def test_x_decyzja_ponownej_wysylki_draft_nowy_proces(self: "TestAutentiLogika") -> None:
		# DRAFT oznacza proces utworzony, ale nigdy niewysłany (awaria przed send()) --
		# stary draft zostaje w Autenti nieszkodliwy, wymuszamy nowy proces.
		self.assertEqual(decyzja_ponownej_wysylki("DRAFT"), DECYZJA_NOWY_PROCES)

	def test_y_decyzja_ponownej_wysylki_terminalne_nie_sukces_nowy_proces(
		self: "TestAutentiLogika",
	) -> None:
		for status in ("REJECTED", "EXPIRED", "WITHDRAWN"):
			with self.subTest(status=status):
				self.assertEqual(decyzja_ponownej_wysylki(status), DECYZJA_NOWY_PROCES)

	def test_z_decyzja_ponownej_wysylki_404_none_nowy_proces(self: "TestAutentiLogika") -> None:
		# `None` reprezentuje odpowiedź 404 (proces nie istnieje po stronie Autenti).
		self.assertEqual(decyzja_ponownej_wysylki(None), DECYZJA_NOWY_PROCES)

	def test_aa_czy_wysylanie_przekroczylo_timeout_brak_znacznika_zawsze_przekroczony(
		self: "TestAutentiLogika",
	) -> None:
		# Legacy rekordy sprzed tej poprawki nigdy nie dostały znacznika `sent_at`
		# przy ustawieniu "Wysyłanie" -- brak znacznika nie może oznaczać "jeszcze
		# nie", bo wtedy taki rekord utknąłby na zawsze.
		self.assertTrue(czy_wysylanie_przekroczylo_timeout(None, datetime(2026, 1, 1, 12, 0, 0)))

	def test_ab_czy_wysylanie_przekroczylo_timeout_swiezy_nie_przekroczony(
		self: "TestAutentiLogika",
	) -> None:
		teraz = datetime(2026, 1, 1, 12, 0, 0)
		sent_at = teraz - timedelta(minutes=5)
		self.assertFalse(czy_wysylanie_przekroczylo_timeout(sent_at, teraz))

	def test_ac_czy_wysylanie_przekroczylo_timeout_stary_przekroczony(
		self: "TestAutentiLogika",
	) -> None:
		teraz = datetime(2026, 1, 1, 12, 0, 0)
		sent_at = teraz - timedelta(minutes=WYSYLANIE_TIMEOUT_MIN + 1)
		self.assertTrue(czy_wysylanie_przekroczylo_timeout(sent_at, teraz))

	def test_ad_czy_wysylanie_przekroczylo_timeout_dokladnie_na_granicy(
		self: "TestAutentiLogika",
	) -> None:
		# Dokładnie WYSYLANIE_TIMEOUT_MIN minut to jeszcze NIE "starszy niż" -- granica
		# jest ostra (>), nie >=.
		teraz = datetime(2026, 1, 1, 12, 0, 0)
		sent_at = teraz - timedelta(minutes=WYSYLANIE_TIMEOUT_MIN)
		self.assertFalse(czy_wysylanie_przekroczylo_timeout(sent_at, teraz))

	def test_ae_czy_logowac_brak_podpisanego_pliku_swiezy_nie(self: "TestAutentiLogika") -> None:
		teraz = datetime(2026, 1, 1, 12, 0, 0)
		signed_at = teraz - timedelta(minutes=5)
		self.assertFalse(czy_logowac_brak_podpisanego_pliku(signed_at, teraz))

	def test_af_czy_logowac_brak_podpisanego_pliku_zalegly_tak(self: "TestAutentiLogika") -> None:
		teraz = datetime(2026, 1, 1, 12, 0, 0)
		signed_at = teraz - timedelta(minutes=ZALEGLY_PODPISANY_PLIK_LOG_MIN + 1)
		self.assertTrue(czy_logowac_brak_podpisanego_pliku(signed_at, teraz))

	def test_ag_czy_logowac_brak_podpisanego_pliku_brak_znacznika_tak(
		self: "TestAutentiLogika",
	) -> None:
		self.assertTrue(czy_logowac_brak_podpisanego_pliku(None, datetime(2026, 1, 1, 12, 0, 0)))

	def test_ah_komunikat_nierozpoznanego_statusu_zawiera_status(self: "TestAutentiLogika") -> None:
		komunikat = komunikat_nierozpoznanego_statusu("SOME_WEIRD_STATUS")
		self.assertIn("SOME_WEIRD_STATUS", komunikat)
		self.assertNotIn("\u2014", komunikat)

	def test_ai_czy_logowac_nierozpoznany_status_pierwszy_raz_tak(
		self: "TestAutentiLogika",
	) -> None:
		self.assertTrue(czy_logowac_nierozpoznany_status(None, "SOME_WEIRD_STATUS"))
		self.assertTrue(czy_logowac_nierozpoznany_status("", "SOME_WEIRD_STATUS"))
		self.assertTrue(czy_logowac_nierozpoznany_status("Inny błąd", "SOME_WEIRD_STATUS"))

	def test_aj_czy_logowac_nierozpoznany_status_juz_zapisany_nie(
		self: "TestAutentiLogika",
	) -> None:
		komunikat = komunikat_nierozpoznanego_statusu("SOME_WEIRD_STATUS")
		self.assertFalse(czy_logowac_nierozpoznany_status(komunikat, "SOME_WEIRD_STATUS"))

	def test_ak_czy_logowac_nierozpoznany_status_inny_status_tak(
		self: "TestAutentiLogika",
	) -> None:
		# Zapisany komunikat dotyczył INNEGO nierozpoznanego statusu -- nowy status
		# musi zostać zalogowany osobno.
		stary_komunikat = komunikat_nierozpoznanego_statusu("STATUS_A")
		self.assertTrue(czy_logowac_nierozpoznany_status(stary_komunikat, "STATUS_B"))

	def test_al_komunikat_bledu_wysylki_timeout(self: "TestAutentiLogika") -> None:
		import requests

		komunikat = komunikat_bledu_wysylki(requests.Timeout("read timed out"))
		self.assertEqual(
			komunikat, "Przekroczono czas oczekiwania na odpowiedź Autenti. Wyślij ponownie."
		)
		self.assertNotIn("\u2014", komunikat)

	def test_am_komunikat_bledu_wysylki_http_error_z_kodem(self: "TestAutentiLogika") -> None:
		import requests

		response = requests.Response()
		response.status_code = 500
		exc = requests.HTTPError("500 Server Error", response=response)

		komunikat = komunikat_bledu_wysylki(exc)
		self.assertEqual(
			komunikat, "Autenti odpowiedziało błędem HTTP 500. Szczegóły w dzienniku błędów."
		)
		self.assertNotIn("\u2014", komunikat)

	def test_an_komunikat_bledu_wysylki_http_error_bez_odpowiedzi(
		self: "TestAutentiLogika",
	) -> None:
		import requests

		komunikat = komunikat_bledu_wysylki(requests.HTTPError("brak odpowiedzi"))
		self.assertEqual(komunikat, "Autenti odpowiedziało błędem HTTP. Szczegóły w dzienniku błędów.")

	def test_ao_komunikat_bledu_wysylki_inny_wyjatek(self: "TestAutentiLogika") -> None:
		komunikat = komunikat_bledu_wysylki(ValueError("cokolwiek po angielsku"))
		self.assertEqual(komunikat, "Wysyłka do Autenti nie powiodła się. Szczegóły w dzienniku błędów.")
		self.assertNotIn("\u2014", komunikat)
		# Surowy angielski tekst wyjątku nigdy nie ląduje w komunikacie dla użytkownika.
		self.assertNotIn("cokolwiek", komunikat)

	def test_ap_komunikat_timeout_bez_procesu_po_polsku(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			KOMUNIKAT_TIMEOUT_WYSYLANIA_BEZ_PROCESU,
			"Wysyłka została przerwana przed utworzeniem procesu w Autenti. Wyślij ponownie.",
		)
		self.assertNotIn("\u2014", KOMUNIKAT_TIMEOUT_WYSYLANIA_BEZ_PROCESU)

	def test_aq_wybierz_id_podpisanego_pliku_preferuje_signed_content_file(
		self: "TestAutentiLogika",
	) -> None:
		pliki = [
			{"id": "id-partial", "filePurpose": "PARTIALLY_SIGNED_CONTENT_FILE"},
			{"id": "id-signed", "filePurpose": "SIGNED_CONTENT_FILE"},
		]
		self.assertEqual(wybierz_id_podpisanego_pliku(pliki), "id-signed")

	def test_ar_wybierz_id_podpisanego_pliku_nigdy_partially_signed(
		self: "TestAutentiLogika",
	) -> None:
		# Krytyczne dla F3: COMPLETED z tylko jednym podpisem (PARTIALLY_SIGNED) nie
		# może zostać nigdy zapisany jako gotowy podpisany plik.
		pliki = [{"id": "id-partial", "filePurpose": "PARTIALLY_SIGNED_CONTENT_FILE"}]
		self.assertIsNone(wybierz_id_podpisanego_pliku(pliki))

	def test_as_wybierz_id_podpisanego_pliku_brak_kandydatow_none(
		self: "TestAutentiLogika",
	) -> None:
		self.assertIsNone(wybierz_id_podpisanego_pliku([]))
		self.assertIsNone(wybierz_id_podpisanego_pliku([{"id": "x", "filePurpose": "CONTENT_ARCHIVE"}]))


if __name__ == "__main__":
	unittest.main()
