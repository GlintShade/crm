import json
import unittest

from crm.volteo_pipeline import (
	NOTATKI,
	OZE_RODZAJE,
	PIPELINE_CP,
	PIPELINE_OZE,
	PODZADANIA_CP,
	STANY_PODZADAN,
	TERMINALE,
	dozwolone_stany,
	grupa_for,
	is_forward,
	notatka_for,
	parsuj_podzadania,
	pipeline_for,
	pipeline_key_for,
	podzadania_for,
	podzadanie_def,
	step_index,
)


class TestVolteoPipeline(unittest.TestCase):
	def test_a_wszystkie_rodzaje_oze_dają_ten_sam_rurociąg(self: "TestVolteoPipeline") -> None:
		for rodzaj in OZE_RODZAJE:
			self.assertEqual(pipeline_key_for(rodzaj), "OZE")
			self.assertEqual(pipeline_for(rodzaj), PIPELINE_OZE)

	def test_b_czyste_powietrze_ma_własny_rurociąg(self: "TestVolteoPipeline") -> None:
		self.assertEqual(pipeline_key_for("Czyste Powietrze"), "CP")
		self.assertEqual(pipeline_for("Czyste Powietrze"), PIPELINE_CP)

	def test_c_brak_pusty_nieznany_rodzaj_dają_wartości_puste(self: "TestVolteoPipeline") -> None:
		for rodzaj in (None, "", "Nieznany"):
			self.assertIsNone(pipeline_key_for(rodzaj))
			self.assertIsNone(pipeline_for(rodzaj))
			self.assertIsNone(grupa_for(rodzaj))
			self.assertEqual(step_index(rodzaj, "Lead"), -1)
			self.assertFalse(is_forward(rodzaj, "Lead", "Dokumentacja"))
			self.assertIsNone(notatka_for(rodzaj, "Lead"))

	def test_d_step_index_pierwszy_środkowy_ostatni_oze(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Lead"), 0)
		self.assertEqual(step_index("Fotowoltaika", "Umowa Wygenerowana"), 1)
		self.assertEqual(step_index("Fotowoltaika", "Finansowanie"), 4)

	def test_e_step_index_pierwszy_środkowy_ostatni_cp(self: "TestVolteoPipeline") -> None:
		# Rurociąg CP ma od b49 12 kroków (patrz PIPELINE_CP) — Lead pierwszy,
		# "Audyt Energetyczny" trzeci (indeks 2), "Projekt rozliczony" ostatni
		# (indeks 11, niesie type=Won na wierszu statusu, patrz docstring modułu).
		self.assertEqual(step_index("Czyste Powietrze", "Lead"), 0)
		self.assertEqual(step_index("Czyste Powietrze", "Audyt Energetyczny"), 2)
		self.assertEqual(step_index("Czyste Powietrze", "Projekt rozliczony"), 11)

	def test_f_finansowanie_wyłącznie_w_oze(self: "TestVolteoPipeline") -> None:
		# Do b48 "Finansowanie" był jednym wierszem statusu współdzielonym przez oba
		# rurociągi pod różnymi indeksami. Od b49 CP ma własny krok "Finansowanie Trify"
		# w jego miejsce — "Finansowanie" jest teraz statusem wyłącznie OZE.
		self.assertEqual(step_index("Fotowoltaika", "Finansowanie"), 4)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie Trify"), 7)

	def test_f2_weryfikacja_backoffice_wyłącznie_oze(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Weryfikacja Backoffice"), 3)
		self.assertEqual(step_index("Czyste Powietrze", "Weryfikacja Backoffice"), -1)

	def test_f3_oferta_docelowa_usunięta_z_obu_rurociągów(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Oferta Docelowa"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Docelowa"), -1)

	def test_f4_oferta_wstępna_i_właściwa_usunięte_z_cp(self: "TestVolteoPipeline") -> None:
		# "Oferta Wstępna"/"Oferta Właściwa" były w rurociągu CP do b48; od b49 zastąpione
		# przez "Umowa na realizację" (z podzadaniami umowa:oferta_* — patrz PODZADANIA_CP).
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Wstępna"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Właściwa"), -1)

	def test_g_statusy_poza_rurociągiem_dają_minus_jeden(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Przegrana"), -1)
		self.assertEqual(step_index("Fotowoltaika", "Wygrana – montaż"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Przegrana"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Wygrana – montaż"), -1)

	def test_h_status_poza_rurociągiem_jako_bieżący_daje_false(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Przegrana", "Umowa Wygenerowana"))
		self.assertFalse(is_forward("Fotowoltaika", "Wygrana – montaż", "Umowa Wygenerowana"))
		self.assertFalse(is_forward("Czyste Powietrze", "Przegrana", "Dokumentacja"))
		self.assertFalse(is_forward("Czyste Powietrze", "Wygrana – montaż", "Dokumentacja"))

	def test_i_is_forward_do_przodu_prawda(self: "TestVolteoPipeline") -> None:
		self.assertTrue(is_forward("Fotowoltaika", "Lead", "Umowa Wygenerowana"))
		self.assertTrue(is_forward("Czyste Powietrze", "Dokumentacja", "Audyt Energetyczny"))
		self.assertTrue(is_forward("Fotowoltaika", "Weryfikacja Backoffice", "Finansowanie"))

	def test_j_is_forward_do_tyłu_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Umowa Podpisana", "Lead"))
		self.assertFalse(is_forward("Czyste Powietrze", "Audyt Energetyczny", "Dokumentacja"))
		self.assertFalse(is_forward("Fotowoltaika", "Finansowanie", "Weryfikacja Backoffice"))

	def test_k_is_forward_ten_sam_status_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Lead", "Lead"))
		self.assertFalse(is_forward("Czyste Powietrze", "Dokumentacja", "Dokumentacja"))

	def test_l_is_forward_cel_poza_rurociągiem_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Lead", "Przegrana"))
		self.assertFalse(is_forward("Czyste Powietrze", "Lead", "Wygrana – montaż"))

	def test_l2_is_forward_bieżący_terminalny_zawsze_fałsz(self: "TestVolteoPipeline") -> None:
		# Terminale NIE są w rurociągu, więc jako status bieżący dają zawsze False,
		# niezależnie od tego, że target jest dalej w rurociągu.
		self.assertFalse(is_forward("Fotowoltaika", "Wygrana – montaż", "Finansowanie"))
		self.assertFalse(is_forward("Czyste Powietrze", "Przegrana", "Realizacja"))

	def test_m_notatka_for_zwraca_zdefiniowane_notatki(self: "TestVolteoPipeline") -> None:
		self.assertEqual(
			notatka_for("Fotowoltaika", "Umowa Podpisana"),
			"Uzupełnij audyt i wyślij do weryfikacji.",
		)
		self.assertEqual(
			notatka_for("Czyste Powietrze", "Dokumentacja"),
			"Umowa na obsługę dotacji, GOPS, pełnomocnictwo",
		)

	def test_n_notatka_for_brak_wpisu_daje_none(self: "TestVolteoPipeline") -> None:
		self.assertIsNone(notatka_for("Fotowoltaika", "Lead"))
		self.assertIsNone(notatka_for("Czyste Powietrze", "Realizacja"))
		self.assertIsNone(notatka_for("Fotowoltaika", None))
		self.assertIsNone(notatka_for(None, "Lead"))

	def test_p_grupa_for_oze(self: "TestVolteoPipeline") -> None:
		for rodzaj in OZE_RODZAJE:
			grupa = grupa_for(rodzaj)
			self.assertEqual(len(grupa), 7)
			self.assertEqual(grupa, (*PIPELINE_OZE, "Wygrana – montaż", "Przegrana"))
			self.assertEqual(grupa[-2:], ("Wygrana – montaż", "Przegrana"))

	def test_q_grupa_for_cp(self: "TestVolteoPipeline") -> None:
		grupa = grupa_for("Czyste Powietrze")
		self.assertEqual(len(grupa), 13)
		self.assertEqual(grupa, (*PIPELINE_CP, "Przegrana"))
		self.assertEqual(grupa[-1], "Przegrana")

	def test_r_grupa_for_brak_rurociągu_daje_none(self: "TestVolteoPipeline") -> None:
		for rodzaj in (None, "", "Nieznany"):
			self.assertIsNone(grupa_for(rodzaj))

	def test_s_grupa_for_kolejność_to_rurociąg_potem_terminale(self: "TestVolteoPipeline") -> None:
		grupa_oze = grupa_for("Fotowoltaika")
		self.assertEqual(grupa_oze[: len(PIPELINE_OZE)], PIPELINE_OZE)
		grupa_cp = grupa_for("Czyste Powietrze")
		self.assertEqual(grupa_cp[: len(PIPELINE_CP)], PIPELINE_CP)

	def test_o_wywołania_nie_mutują_stałych_modułowych(self: "TestVolteoPipeline") -> None:
		przed_oze = tuple(PIPELINE_OZE)
		przed_cp = tuple(PIPELINE_CP)
		przed_notatki = {klucz: dict(wartosc) for klucz, wartosc in NOTATKI.items()}
		przed_rodzaje = frozenset(OZE_RODZAJE)
		przed_terminale = {klucz: tuple(wartosc) for klucz, wartosc in TERMINALE.items()}
		przed_podzadania = {
			etap: tuple(dict(zadanie) for zadanie in zadania) for etap, zadania in PODZADANIA_CP.items()
		}

		pipeline_key_for("Fotowoltaika")
		pipeline_for("Czyste Powietrze")
		step_index("Fotowoltaika", "Lead")
		notatka_for("Czyste Powietrze", "Dokumentacja")
		is_forward("Fotowoltaika", "Lead", "Umowa Wygenerowana")
		grupa_for("Fotowoltaika")
		grupa_for("Czyste Powietrze")
		podzadania_for("Czyste Powietrze")
		definicja = podzadanie_def("Czyste Powietrze", "dok:zdjecia")
		definicja["label"] = "ZMIENIONE"  # mutacja KOPII zwróconej przez podzadanie_def
		dozwolone_stany({"typ": "weryfikacja", "nd_dozwolone": True})
		wsad = {"dok:zdjecia": {"stan": "accepted"}}
		wynik = parsuj_podzadania(wsad)
		wynik["dok:zdjecia"]["stan"] = "error"  # mutacja KOPII zwróconej przez parsuj_podzadania

		self.assertEqual(PIPELINE_OZE, przed_oze)
		self.assertEqual(PIPELINE_CP, przed_cp)
		self.assertEqual(NOTATKI, przed_notatki)
		self.assertEqual(OZE_RODZAJE, przed_rodzaje)
		self.assertEqual(TERMINALE, przed_terminale)
		self.assertEqual(
			{etap: tuple(dict(zadanie) for zadanie in zadania) for etap, zadania in PODZADANIA_CP.items()},
			przed_podzadania,
		)
		self.assertEqual(wsad["dok:zdjecia"]["stan"], "accepted")

	# --- Katalog podzadań CP (PODZADANIA_CP) ---------------------------------

	def test_t_klucze_podzadań_unikalne_w_całym_katalogu(self: "TestVolteoPipeline") -> None:
		wszystkie_klucze = [zadanie["klucz"] for zadania in PODZADANIA_CP.values() for zadanie in zadania]
		self.assertEqual(len(wszystkie_klucze), len(set(wszystkie_klucze)))
		self.assertGreater(len(wszystkie_klucze), 0)

	def test_u_każdy_etap_katalogu_należy_do_pipeline_cp(self: "TestVolteoPipeline") -> None:
		for etap in PODZADANIA_CP:
			self.assertIn(etap, PIPELINE_CP)

	def test_v_lead_i_projekt_rozliczony_bez_podzadań(self: "TestVolteoPipeline") -> None:
		self.assertNotIn("Lead", PODZADANIA_CP)
		self.assertNotIn("Projekt rozliczony", PODZADANIA_CP)

	def test_w_podzadania_for_cp_zwraca_cały_katalog(self: "TestVolteoPipeline") -> None:
		self.assertEqual(podzadania_for("Czyste Powietrze"), PODZADANIA_CP)

	def test_x_podzadania_for_oze_i_nieznane_dają_pusty_dict(self: "TestVolteoPipeline") -> None:
		for rodzaj in (*OZE_RODZAJE, None, "", "Nieznany"):
			self.assertEqual(podzadania_for(rodzaj), {})

	def test_y_podzadanie_def_zwraca_definicję_po_kluczu(self: "TestVolteoPipeline") -> None:
		definicja = podzadanie_def("Czyste Powietrze", "dok:zdjecia")
		self.assertIsNotNone(definicja)
		self.assertEqual(definicja["label"], "Zdjęcia")
		self.assertEqual(definicja["typ"], "weryfikacja")
		self.assertFalse(definicja["nd_dozwolone"])

	def test_z_podzadanie_def_nieznany_klucz_lub_rodzaj_daje_none(self: "TestVolteoPipeline") -> None:
		self.assertIsNone(podzadanie_def("Czyste Powietrze", "brak:takiego"))
		self.assertIsNone(podzadanie_def("Fotowoltaika", "dok:zdjecia"))
		self.assertIsNone(podzadanie_def(None, "dok:zdjecia"))

	def test_aa_podzadanie_def_zwraca_kopię_nie_referencję(self: "TestVolteoPipeline") -> None:
		definicja = podzadanie_def("Czyste Powietrze", "dok:zdjecia")
		definicja["label"] = "ZMIENIONE"
		self.assertEqual(podzadanie_def("Czyste Powietrze", "dok:zdjecia")["label"], "Zdjęcia")

	# --- dozwolone_stany: macierz weryfikacja/odhaczenie × z ND/bez ND ------

	def test_ab_dozwolone_stany_weryfikacja_bez_nd(self: "TestVolteoPipeline") -> None:
		zadanie = podzadanie_def("Czyste Powietrze", "dok:zdjecia")  # weryfikacja, nd_dozwolone=False
		self.assertEqual(dozwolone_stany(zadanie), frozenset({"waiting", "accepted", "error"}))

	def test_ac_dozwolone_stany_weryfikacja_z_nd(self: "TestVolteoPipeline") -> None:
		zadanie = podzadanie_def("Czyste Powietrze", "dok:zgoda_wspolwlascicieli")  # weryfikacja, ND
		self.assertEqual(dozwolone_stany(zadanie), frozenset({"waiting", "accepted", "error", "nd"}))

	def test_ad_dozwolone_stany_odhaczenie_bez_nd(self: "TestVolteoPipeline") -> None:
		zadanie = podzadanie_def("Czyste Powietrze", "dok:poziom_dotacji")  # odhaczenie, nd_dozwolone=False
		self.assertEqual(dozwolone_stany(zadanie), frozenset({"accepted"}))

	def test_ae_dozwolone_stany_odhaczenie_z_nd(self: "TestVolteoPipeline") -> None:
		zadanie = podzadanie_def("Czyste Powietrze", "trify:umowa_podpisana")  # odhaczenie, ND
		self.assertEqual(dozwolone_stany(zadanie), frozenset({"accepted", "nd"}))

	# --- parsuj_podzadania: defensywny parse na śmieciach --------------------

	def test_af_parsuj_podzadania_none_i_pusty_string(self: "TestVolteoPipeline") -> None:
		self.assertEqual(parsuj_podzadania(None), {})
		self.assertEqual(parsuj_podzadania(""), {})

	def test_ag_parsuj_podzadania_string_null(self: "TestVolteoPipeline") -> None:
		self.assertEqual(parsuj_podzadania("null"), {})

	def test_ah_parsuj_podzadania_string_nieparsowalny(self: "TestVolteoPipeline") -> None:
		self.assertEqual(parsuj_podzadania("{nie json"), {})

	def test_ai_parsuj_podzadania_pojedynczo_zakodowany_json(self: "TestVolteoPipeline") -> None:
		surowe = {"audyt:umowiony": {"stan": "waiting"}}
		self.assertEqual(parsuj_podzadania(json.dumps(surowe)), surowe)

	def test_aj_parsuj_podzadania_podwójnie_zakodowany_json(self: "TestVolteoPipeline") -> None:
		surowe = {"dok:zdjecia": {"stan": "accepted"}}
		podwójnie_zakodowany = json.dumps(json.dumps(surowe))
		self.assertEqual(parsuj_podzadania(podwójnie_zakodowany), surowe)

	def test_ak_parsuj_podzadania_odrzuca_wpis_z_nieznanym_stanem(self: "TestVolteoPipeline") -> None:
		self.assertEqual(parsuj_podzadania({"dok:zdjecia": {"stan": "bogus"}}), {})

	def test_al_parsuj_podzadania_odrzuca_wpis_nie_dict(self: "TestVolteoPipeline") -> None:
		self.assertEqual(parsuj_podzadania({"dok:zdjecia": "accepted"}), {})

	def test_am_parsuj_podzadania_mieszany_wsad(self: "TestVolteoPipeline") -> None:
		wsad = {
			"dok:zdjecia": {"stan": "accepted"},
			"dok:ankieta_cp": "not-a-dict",
			"audyt:umowiony": {"stan": "bogus"},
			"trify:wyplacone": {"stan": "nd"},
		}
		wynik = parsuj_podzadania(wsad)
		self.assertEqual(set(wynik.keys()), {"dok:zdjecia", "trify:wyplacone"})

	def test_an_stany_podzadan_zgodne_z_audytweryfikacja_js(self: "TestVolteoPipeline") -> None:
		self.assertEqual(STANY_PODZADAN, ("waiting", "accepted", "error", "nd"))

	def test_ao_is_forward_2_transza_do_projektu_rozliczonego(self: "TestVolteoPipeline") -> None:
		self.assertTrue(is_forward("Czyste Powietrze", "2 transza", "Projekt rozliczony"))


if __name__ == "__main__":
	unittest.main()
