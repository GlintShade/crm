import unittest

from crm.volteo_filtry_szybkie import (
	LIMIT_POL_NA_PASKU,
	klucz_domyslnej_uzytkownika,
	parsuj_json_listy,
	scal_globalne,
	waliduj_liste,
	wybierz_kolejnosc,
)

DOZWOLONE = {"name", "status", "lead_name", "deal_owner", "custom_powiat", "custom_koszty"}
ISTNIEJACE = {"name", "status", "lead_name", "deal_owner", "custom_powiat", "custom_koszty", "custom_nieistniejace_wiecej"}


class TestKluczDomyslnejUzytkownika(unittest.TestCase):
	def test_a_format_klucza(self: "TestKluczDomyslnejUzytkownika") -> None:
		self.assertEqual(klucz_domyslnej_uzytkownika("CRM Lead"), "volteo_filtry_szybkie::CRM Lead")
		self.assertEqual(klucz_domyslnej_uzytkownika("CRM Deal"), "volteo_filtry_szybkie::CRM Deal")

	def test_b_rozne_doctypy_rozne_klucze(self: "TestKluczDomyslnejUzytkownika") -> None:
		self.assertNotEqual(klucz_domyslnej_uzytkownika("CRM Lead"), klucz_domyslnej_uzytkownika("CRM Deal"))


class TestParsujJsonListy(unittest.TestCase):
	def test_a_none(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy(None))

	def test_b_puste_wejscie(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy(""))

	def test_c_nie_string(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy(["a", "b"]))
		self.assertIsNone(parsuj_json_listy(5))
		self.assertIsNone(parsuj_json_listy({"a": 1}))

	def test_d_niepoprawny_json(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy("{nie json"))
		self.assertIsNone(parsuj_json_listy("["))

	def test_e_json_nie_tablica(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy('{"a": 1}'))
		self.assertIsNone(parsuj_json_listy('"tekst"'))
		self.assertIsNone(parsuj_json_listy("5"))

	def test_f_tablica_z_niestring_elementem(self: "TestParsujJsonListy") -> None:
		self.assertIsNone(parsuj_json_listy('["a", 5]'))
		self.assertIsNone(parsuj_json_listy('["a", null]'))

	def test_g_poprawna_tablica_stringow(self: "TestParsujJsonListy") -> None:
		self.assertEqual(parsuj_json_listy('["status", "lead_name"]'), ["status", "lead_name"])

	def test_h_pusta_tablica_to_pusta_lista_nie_none(self: "TestParsujJsonListy") -> None:
		self.assertEqual(parsuj_json_listy("[]"), [])


class TestWybierzKolejnosc(unittest.TestCase):
	def test_a_brak_wlasnego_ukladu_uzywa_globalnego(self: "TestWybierzKolejnosc") -> None:
		wynik = wybierz_kolejnosc(["status", "lead_name"], None, DOZWOLONE, ISTNIEJACE)
		self.assertEqual(wynik, ["status", "lead_name"])

	def test_b_wlasny_uklad_wygrywa(self: "TestWybierzKolejnosc") -> None:
		wynik = wybierz_kolejnosc(
			["status", "lead_name"], ["lead_name", "deal_owner"], DOZWOLONE, ISTNIEJACE
		)
		self.assertEqual(wynik, ["lead_name", "deal_owner"])

	def test_c_wlasny_uklad_po_przefiltrowaniu_pusty_wraca_do_globalnego(
		self: "TestWybierzKolejnosc",
	) -> None:
		# "custom_koszty" nie jest dozwolone dla tego uzytkownika w tym teście
		# (patrz test_d) -- tutaj symulujemy sytuację, gdy WSZYSTKIE pola
		# własnego układu wypadają z filtra.
		dozwolone_bez_kosztow = DOZWOLONE - {"custom_koszty"}
		wynik = wybierz_kolejnosc(
			["status", "lead_name"], ["custom_koszty"], dozwolone_bez_kosztow, ISTNIEJACE
		)
		self.assertEqual(wynik, ["status", "lead_name"])

	def test_d_wlasny_uklad_czesciowo_odfiltrowany_zostaje_z_reszta(
		self: "TestWybierzKolejnosc",
	) -> None:
		dozwolone_bez_kosztow = DOZWOLONE - {"custom_koszty"}
		wynik = wybierz_kolejnosc(
			["status", "custom_koszty", "lead_name"], ["status", "custom_koszty", "lead_name"], dozwolone_bez_kosztow, ISTNIEJACE
		)
		self.assertEqual(wynik, ["status", "lead_name"])

	def test_e_garbage_jako_wlasny_uklad_tolerowany(self: "TestWybierzKolejnosc") -> None:
		for garbage in (None, "status", 5, {"a": 1}, 3.14, True):
			wynik = wybierz_kolejnosc(["status"], garbage, DOZWOLONE, ISTNIEJACE)
			self.assertEqual(wynik, ["status"], msg=f"garbage={garbage!r}")

	def test_f_wlasny_uklad_z_niestring_elementami_odfiltrowane(
		self: "TestWybierzKolejnosc",
	) -> None:
		wynik = wybierz_kolejnosc(["status"], ["lead_name", 5, None, "deal_owner"], DOZWOLONE, ISTNIEJACE)
		self.assertEqual(wynik, ["lead_name", "deal_owner"])

	def test_g_dedup_zachowuje_pierwsze_wystapienie(self: "TestWybierzKolejnosc") -> None:
		wynik = wybierz_kolejnosc(None, ["status", "lead_name", "status"], DOZWOLONE, ISTNIEJACE)
		self.assertEqual(wynik, ["status", "lead_name"])

	def test_h_pole_poza_istniejace_odrzucone(self: "TestWybierzKolejnosc") -> None:
		# "owner" jest w DOZWOLONE (pseudopole zawsze dozwolone), ale NIE w
		# ISTNIEJACE (nie da się z niego zbudować wpisu paska) -- symulacja
		# tej sytuacji osobnym zbiorem lokalnym.
		dozwolone_z_owner = DOZWOLONE | {"owner"}
		wynik = wybierz_kolejnosc(["owner", "status"], None, dozwolone_z_owner, ISTNIEJACE)
		self.assertEqual(wynik, ["status"])

	def test_i_oba_puste(self: "TestWybierzKolejnosc") -> None:
		self.assertEqual(wybierz_kolejnosc([], None, DOZWOLONE, ISTNIEJACE), [])
		self.assertEqual(wybierz_kolejnosc(None, [], DOZWOLONE, ISTNIEJACE), [])

	def test_j_globalne_none(self: "TestWybierzKolejnosc") -> None:
		self.assertEqual(wybierz_kolejnosc(None, None, DOZWOLONE, ISTNIEJACE), [])


class TestWaliduj(unittest.TestCase):
	def test_a_nie_lista(self: "TestWaliduj") -> None:
		for zle in (None, "status", 5, {"a": 1}):
			with self.assertRaises(ValueError):
				waliduj_liste(zle, DOZWOLONE)

	def test_b_pusta_lista(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste([], DOZWOLONE)

	def test_c_przekroczony_limit(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste(["status"] * (LIMIT_POL_NA_PASKU + 1), DOZWOLONE | {"status"})

	def test_d_limit_na_granicy_przechodzi(self: "TestWaliduj") -> None:
		# LIMIT_POL_NA_PASKU unikalnych pol, wszystkie dozwolone -- musi
		# przejść bez wyjątku.
		pola = [f"custom_pole_{i}" for i in range(LIMIT_POL_NA_PASKU)]
		wynik = waliduj_liste(pola, set(pola))
		self.assertEqual(wynik, pola)

	def test_e_niestring_element(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste(["status", 5], DOZWOLONE)

	def test_f_pusty_string_element(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste(["status", ""], DOZWOLONE)

	def test_g_duplikat(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste(["status", "status"], DOZWOLONE)

	def test_h_pole_niedozwolone(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError):
			waliduj_liste(["status", "custom_cc"], DOZWOLONE)

	def test_i_poprawna_lista_zwraca_nowa_liste_tej_samej_tresci(self: "TestWaliduj") -> None:
		pola = ["status", "lead_name"]
		wynik = waliduj_liste(pola, DOZWOLONE)
		self.assertEqual(wynik, pola)
		self.assertIsNot(wynik, pola)

	def test_j_komunikaty_po_polsku(self: "TestWaliduj") -> None:
		with self.assertRaises(ValueError) as ctx:
			waliduj_liste([], DOZWOLONE)
		self.assertIn("Przywróć domyślny", str(ctx.exception))

		with self.assertRaises(ValueError) as ctx:
			waliduj_liste(["custom_cc"], DOZWOLONE)
		self.assertIn("custom_cc", str(ctx.exception))


class TestScalGlobalne(unittest.TestCase):
	def test_a_edytujacy_widzi_wszystko_wynik_bez_zmian(self: "TestScalGlobalne") -> None:
		stare = ["a", "b", "c"]
		nowe = ["c", "a"]  # "b" świadomie usunięte, kolejność zmieniona
		wynik = scal_globalne(nowe, stare, {"a", "b", "c"})
		self.assertEqual(wynik, ["c", "a"])

	def test_b_niewidoczne_pole_w_srodku_wraca_na_miejsce(self: "TestScalGlobalne") -> None:
		stare = ["a", "b", "c"]
		nowe = ["a", "c"]  # edytujący nie widzi "b", więc nie mógł go wysłać
		wynik = scal_globalne(nowe, stare, {"a", "c"})
		self.assertEqual(wynik, ["a", "b", "c"])

	def test_c_niewidoczne_pole_na_poczatku(self: "TestScalGlobalne") -> None:
		stare = ["a", "b", "c"]
		nowe = ["b", "c"]  # edytujący nie widzi "a"
		wynik = scal_globalne(nowe, stare, {"b", "c"})
		self.assertEqual(wynik, ["a", "b", "c"])

	def test_d_niewidoczne_pole_na_koncu(self: "TestScalGlobalne") -> None:
		stare = ["a", "b", "c"]
		nowe = ["a", "b"]  # edytujący nie widzi "c"
		wynik = scal_globalne(nowe, stare, {"a", "b"})
		self.assertEqual(wynik, ["a", "b", "c"])

	def test_e_wiele_niewidocznych_pol_zachowuja_wzgledny_porzadek(
		self: "TestScalGlobalne",
	) -> None:
		stare = ["a", "b", "c", "d", "e"]
		nowe = ["d", "a"]  # edytujący widzi tylko a i d, przestawił D przed A
		wynik = scal_globalne(nowe, stare, {"a", "d"})
		self.assertEqual(wynik, ["d", "e", "a", "b", "c"])

	def test_f_wszystko_niewidoczne_pusty_nowy_odtwarza_stary_porzadek(
		self: "TestScalGlobalne",
	) -> None:
		stare = ["a", "b", "c"]
		wynik = scal_globalne([], stare, set())
		self.assertEqual(wynik, stare)

	def test_g_nowe_pole_dodane_przez_edytujacego_zostaje(self: "TestScalGlobalne") -> None:
		stare = ["a", "b"]
		nowe = ["a", "x", "b"]  # "x" nowe, nie było w starym układzie
		wynik = scal_globalne(nowe, stare, {"a", "b", "x"})
		self.assertEqual(wynik, ["a", "x", "b"])

	def test_h_nie_mutuje_wejsciowych_list(self: "TestScalGlobalne") -> None:
		stare = ["a", "b", "c"]
		nowe = ["a", "c"]
		stare_kopia = list(stare)
		nowe_kopia = list(nowe)
		scal_globalne(nowe, stare, {"a", "c"})
		self.assertEqual(stare, stare_kopia)
		self.assertEqual(nowe, nowe_kopia)

	def test_i_puste_stare_i_nowe(self: "TestScalGlobalne") -> None:
		self.assertEqual(scal_globalne([], [], set()), [])

	def test_j_niewidoczne_pole_juz_obecne_w_nowych_nie_duplikowane(
		self: "TestScalGlobalne",
	) -> None:
		# Bezpiecznik: "b" formalnie niewidoczne dla edytującego, ale z
		# jakiegoś powodu (np. inny wywołujący złożył payload ręcznie)
		# obecne w `nowe_widoczne` -- nie powinno zduplikować się.
		stare = ["a", "b", "c"]
		nowe = ["a", "b", "c"]
		wynik = scal_globalne(nowe, stare, {"a", "c"})
		self.assertEqual(wynik, ["a", "b", "c"])


if __name__ == "__main__":
	unittest.main()
