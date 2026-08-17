import unittest

from crm.integrations.autenti.logika import (
	PENDING_REMOTE_STATUSES,
	SEND_BLOCKED_STATUSES,
	STATUS_MAP,
	mozna_wyslac,
	nazwa_pliku_kredytu,
	nazwa_pliku_kredytu_podpisanego,
	nazwa_pliku_podpisanego,
	nazwa_pliku_umowy,
	prefiks_pliku_kredytu,
	tytul_dokumentu,
	tytul_dokumentu_kredytu,
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

	def test_r_prefiks_pliku_kredytu(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			prefiks_pliku_kredytu("PRO/PVME/26/1021"), "Formularz-kredytowy-PRO-PVME-26-1021"
		)

	def test_s_nazwa_pliku_kredytu(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_kredytu("PRO/PVME/26/1021"), "Formularz-kredytowy-PRO-PVME-26-1021.pdf"
		)

	def test_t_nazwa_pliku_kredytu_podpisanego(self: "TestAutentiLogika") -> None:
		self.assertEqual(
			nazwa_pliku_kredytu_podpisanego("PRO/PVME/26/1021"),
			"Formularz-kredytowy-PRO-PVME-26-1021-podpisany.pdf",
		)

	def test_u_nazwy_plikow_kredytu_dziela_wspolny_prefiks(self: "TestAutentiLogika") -> None:
		# Odpytywanie Autenti po prefiksie (LIKE) i sprzątanie starych plików
		# formularza kredytowego w `crm/api/kredyt.py` zależą od tego, że OBIE
		# nazwy zaczynają się dokładnie od `prefiks_pliku_kredytu(deal)` —
		# rozjazd tu po cichu psuje dopasowanie w obu miejscach.
		deal = "PRO/PVME/26/1021"
		prefiks = prefiks_pliku_kredytu(deal)
		self.assertTrue(nazwa_pliku_kredytu(deal).startswith(prefiks))
		self.assertTrue(nazwa_pliku_kredytu_podpisanego(deal).startswith(prefiks))


if __name__ == "__main__":
	unittest.main()
