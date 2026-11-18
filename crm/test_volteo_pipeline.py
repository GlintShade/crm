import json
import unittest

from crm.volteo_pipeline import (
	FORMY_FINANSOWANIA,
	NOTATKI,
	OZE_RODZAJE,
	PIPELINE_CP,
	PIPELINE_OZE,
	PODZADANIA_CP,
	PODZADANIA_OZE,
	STANY_PODZADAN,
	TERMINALE,
	czy_pozycja_dla_formy,
	dozwolone_stany,
	etap_nr,
	grupa_for,
	is_forward,
	notatka_for,
	parsuj_podzadania,
	pipeline_for,
	pipeline_key_for,
	podsumowanie_etapu,
	podsumowanie_szansy,
	podzadania_for,
	podzadanie_def,
	pozycje_etapu,
	step_index,
	wyczysc_po_zmianie_formy,
)


class TestVolteoPipeline(unittest.TestCase):
	def test_a_wszystkie_rodzaje_oze_dają_ten_sam_proces(self: "TestVolteoPipeline") -> None:
		for rodzaj in OZE_RODZAJE:
			self.assertEqual(pipeline_key_for(rodzaj), "OZE")
			self.assertEqual(pipeline_for(rodzaj), PIPELINE_OZE)

	def test_b_czyste_powietrze_ma_własny_proces(self: "TestVolteoPipeline") -> None:
		self.assertEqual(pipeline_key_for("Czyste Powietrze"), "CP")
		self.assertEqual(pipeline_for("Czyste Powietrze"), PIPELINE_CP)

	def test_b2_nowe_rodzaje_b68_dają_proces_oze(self: "TestVolteoPipeline") -> None:
		# Paczka "Wielki update kalkulatora OZE" (b68, chunk B3): cztery nowe
		# rodzaje idą DOKŁADNIE tym samym procesem OZE (decyzja właściciela
		# 2026-10-04), te same kroki, ten sam offset, bez wyjątków.
		for rodzaj in ("Rozbudowa PV/ME", "Klimatyzacja", "Pompa ciepła", "Kocioł"):
			self.assertEqual(pipeline_key_for(rodzaj), "OZE")
			self.assertEqual(pipeline_for(rodzaj), PIPELINE_OZE)
		self.assertEqual(pipeline_key_for("Kocioł"), "OZE")
		self.assertEqual(etap_nr("Pompa ciepła", "Lead"), 1)

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
		self.assertEqual(step_index("Fotowoltaika", "Finansowanie"), 3)
		self.assertEqual(step_index("Fotowoltaika", "Wygrana - zako\u0144czona"), 7)

	def test_d2_pipeline_oze_kolejnosc_finansowanie_przed_weryfikacja(self: "TestVolteoPipeline") -> None:
		# Regresja ops#181 (2026-09-24, decyzja właściciela): "Finansowanie" poprzedza
		# "Weryfikacja Backoffice" w procesie OZE (wcześniej było odwrotnie).
		self.assertEqual(
			PIPELINE_OZE,
			(
				"Lead",
				"Umowa Wygenerowana",
				"Umowa Podpisana",
				"Finansowanie",
				"Weryfikacja Backoffice",
				"Monta\u017c",
				"Obs\u0142uga pomonta\u017cowa",
				"Wygrana - zako\u0144czona",
			),
		)
		self.assertEqual(len(PIPELINE_OZE), 8)

	def test_e_step_index_pierwszy_środkowy_ostatni_cp(self: "TestVolteoPipeline") -> None:
		# Proces CP ma od b49 12 kroków (patrz PIPELINE_CP) — Lead pierwszy,
		# "Audyt Energetyczny" trzeci (indeks 2), "Projekt rozliczony" ostatni
		# (indeks 11, niesie type=Won na wierszu statusu, patrz docstring modułu).
		self.assertEqual(step_index("Czyste Powietrze", "Lead"), 0)
		self.assertEqual(step_index("Czyste Powietrze", "Audyt Energetyczny"), 2)
		self.assertEqual(step_index("Czyste Powietrze", "Projekt rozliczony"), 11)

	def test_f_finansowanie_wyłącznie_w_oze(self: "TestVolteoPipeline") -> None:
		# Do b48 "Finansowanie" był jednym wierszem statusu współdzielonym przez oba
		# procesy pod różnymi indeksami. Od b49 CP ma własny krok "Finansowanie Trify"
		# w jego miejsce, "Finansowanie" jest teraz statusem wyłącznie OZE. Od
		# 2026-09-24 (ops#181) "Finansowanie" poprzedza "Weryfikacja Backoffice" w OZE.
		self.assertEqual(step_index("Fotowoltaika", "Finansowanie"), 3)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie Trify"), 7)

	def test_f2_weryfikacja_backoffice_wyłącznie_oze(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Weryfikacja Backoffice"), 4)
		self.assertEqual(step_index("Czyste Powietrze", "Weryfikacja Backoffice"), -1)

	def test_f3_oferta_docelowa_usunięta_z_obu_procesów(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Oferta Docelowa"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Docelowa"), -1)

	def test_f4_oferta_wstępna_i_właściwa_usunięte_z_cp(self: "TestVolteoPipeline") -> None:
		# "Oferta Wstępna"/"Oferta Właściwa" były w procesie CP do b48; od b49 zastąpione
		# przez "Umowa na realizację" (z podzadaniami umowa:oferta_* — patrz PODZADANIA_CP).
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Wstępna"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Właściwa"), -1)

	def test_g_statusy_poza_procesem_dają_minus_jeden(self: "TestVolteoPipeline") -> None:
		stara_wygrana = "Wygrana " + chr(0x2013) + " monta\u017c"
		self.assertEqual(step_index("Fotowoltaika", "Przegrana"), -1)
		self.assertEqual(step_index("Fotowoltaika", stara_wygrana), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Przegrana"), -1)
		self.assertEqual(step_index("Czyste Powietrze", stara_wygrana), -1)

	def test_h_status_poza_procesem_jako_bieżący_daje_false(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Przegrana", "Umowa Wygenerowana"))
		stara_wygrana = "Wygrana " + chr(0x2013) + " monta\u017c"
		self.assertFalse(is_forward("Fotowoltaika", stara_wygrana, "Umowa Wygenerowana"))
		self.assertFalse(is_forward("Czyste Powietrze", "Przegrana", "Dokumentacja"))
		self.assertFalse(is_forward("Czyste Powietrze", stara_wygrana, "Dokumentacja"))

	def test_i_is_forward_do_przodu_prawda(self: "TestVolteoPipeline") -> None:
		self.assertTrue(is_forward("Fotowoltaika", "Lead", "Umowa Wygenerowana"))
		self.assertTrue(is_forward("Czyste Powietrze", "Dokumentacja", "Audyt Energetyczny"))
		self.assertTrue(is_forward("Fotowoltaika", "Finansowanie", "Weryfikacja Backoffice"))

	def test_j_is_forward_do_tyłu_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Umowa Podpisana", "Lead"))
		self.assertFalse(is_forward("Czyste Powietrze", "Audyt Energetyczny", "Dokumentacja"))
		self.assertFalse(is_forward("Fotowoltaika", "Weryfikacja Backoffice", "Finansowanie"))

	def test_k_is_forward_ten_sam_status_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Lead", "Lead"))
		self.assertFalse(is_forward("Czyste Powietrze", "Dokumentacja", "Dokumentacja"))

	def test_l_is_forward_cel_poza_procesem_fałsz(self: "TestVolteoPipeline") -> None:
		self.assertFalse(is_forward("Fotowoltaika", "Lead", "Przegrana"))
		self.assertFalse(is_forward("Czyste Powietrze", "Lead", "Wygrana - zako\u0144czona"))

	def test_l2_is_forward_bieżący_terminalny_zawsze_fałsz(self: "TestVolteoPipeline") -> None:
		# Terminale NIE są w procesie, więc jako status bieżący dają zawsze False,
		# niezależnie od tego, że target jest dalej w procesie.
		self.assertFalse(is_forward("Fotowoltaika", "Przegrana", "Finansowanie"))
		self.assertFalse(is_forward("Czyste Powietrze", "Przegrana", "Realizacja"))

	def test_m_notatka_for_zwraca_zdefiniowane_notatki(self: "TestVolteoPipeline") -> None:
		# Od 2026-09-24 (ops#181) notatka "co dalej" siedzi pod "Finansowanie", bo audyt
		# następuje TERAZ po finansowaniu, nie po podpisaniu umowy.
		# ops#381: audyt nie zmienia już etapu, więc OZE nie ma notatki pod "Finansowanie".
		self.assertIsNone(notatka_for("Fotowoltaika", "Finansowanie"))
		self.assertEqual(
			notatka_for("Czyste Powietrze", "Dokumentacja"),
			"Umowa na obsługę dotacji, GOPS, pełnomocnictwo",
		)

	def test_n_notatka_for_brak_wpisu_daje_none(self: "TestVolteoPipeline") -> None:
		self.assertIsNone(notatka_for("Fotowoltaika", "Lead"))
		self.assertIsNone(notatka_for("Czyste Powietrze", "Realizacja"))
		self.assertIsNone(notatka_for("Fotowoltaika", None))
		self.assertIsNone(notatka_for(None, "Lead"))
		# "Umowa Podpisana" nie ma już notatki od 2026-09-24 (ops#181), przeniesiona
		# na "Finansowanie", patrz test_m.
		self.assertIsNone(notatka_for("Fotowoltaika", "Umowa Podpisana"))

	def test_p_grupa_for_oze(self: "TestVolteoPipeline") -> None:
		for rodzaj in OZE_RODZAJE:
			grupa = grupa_for(rodzaj)
			self.assertEqual(len(grupa), 9)
			self.assertEqual(grupa, (*PIPELINE_OZE, "Przegrana"))
			self.assertEqual(grupa[-2:], ("Wygrana - zako\u0144czona", "Przegrana"))
			self.assertEqual(TERMINALE["OZE"], ("Przegrana",))

	def test_q_grupa_for_cp(self: "TestVolteoPipeline") -> None:
		grupa = grupa_for("Czyste Powietrze")
		self.assertEqual(len(grupa), 13)
		self.assertEqual(grupa, (*PIPELINE_CP, "Przegrana"))
		self.assertEqual(grupa[-1], "Przegrana")

	def test_r_grupa_for_brak_procesu_daje_none(self: "TestVolteoPipeline") -> None:
		for rodzaj in (None, "", "Nieznany"):
			self.assertIsNone(grupa_for(rodzaj))

	def test_s_grupa_for_kolejność_to_proces_potem_terminale(self: "TestVolteoPipeline") -> None:
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

	def test_x_podzadania_for_oze_zwraca_katalog_a_nieznane_pusty_dict(self: "TestVolteoPipeline") -> None:
		for rodzaj in OZE_RODZAJE:
			self.assertEqual(podzadania_for(rodzaj), PODZADANIA_OZE)
			self.assertTrue(podzadania_for(rodzaj))
		for rodzaj in (None, "", "Nieznany"):
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
		self.assertIsNone(podzadanie_def("Czyste Powietrze", "oze_mon:sprzet_u_klienta"))
		self.assertIsNone(podzadanie_def(None, "dok:zdjecia"))

	def test_aa_podzadanie_def_zwraca_kopię_nie_referencję(self: "TestVolteoPipeline") -> None:
		definicja = podzadanie_def("Czyste Powietrze", "dok:zdjecia")
		definicja["label"] = "ZMIENIONE"
		self.assertEqual(podzadanie_def("Czyste Powietrze", "dok:zdjecia")["label"], "Zdjęcia")

	# --- dozwolone_stany: macierz weryfikacja/odhaczenie x z ND/bez ND ------

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

	# --- etap_nr: numer kroku procesu (do sortowania listy szans) -----------

	def test_ap_etap_nr_oze_wartości_jawne(self: "TestVolteoPipeline") -> None:
		self.assertEqual(etap_nr("Fotowoltaika", "Lead"), 1)
		self.assertEqual(etap_nr("Fotowoltaika", "Umowa Wygenerowana"), 2)
		self.assertEqual(etap_nr("Fotowoltaika", "Umowa Podpisana"), 3)
		self.assertEqual(etap_nr("Fotowoltaika", "Finansowanie"), 4)
		self.assertEqual(etap_nr("Fotowoltaika", "Weryfikacja Backoffice"), 5)
		self.assertEqual(etap_nr("Fotowoltaika", "Monta\u017c"), 6)
		self.assertEqual(etap_nr("Fotowoltaika", "Obs\u0142uga pomonta\u017cowa"), 7)
		self.assertEqual(etap_nr("Fotowoltaika", "Wygrana - zako\u0144czona"), 8)
		self.assertEqual(etap_nr("Fotowoltaika", "Przegrana"), 9)

	def test_aq_etap_nr_cp_wartości_jawne(self: "TestVolteoPipeline") -> None:
		self.assertEqual(etap_nr("Czyste Powietrze", "Lead"), 101)
		self.assertEqual(etap_nr("Czyste Powietrze", "Dokumentacja"), 102)
		self.assertEqual(etap_nr("Czyste Powietrze", "Projekt rozliczony"), 112)
		self.assertEqual(etap_nr("Czyste Powietrze", "Przegrana"), 113)

	def test_ar_etap_nr_weryfikacja_backoffice_pod_cp_daje_zero(self: "TestVolteoPipeline") -> None:
		# Status istnieje w słowniku CRM Deal Status, ale nie w procesie CP —
		# to jest DOKŁADNIE różnica między "status nieznany" a "status spoza
		# procesu tego rodzaju", więc wynik musi być 0, nie -1+1 ani wyjątek.
		self.assertEqual(etap_nr("Czyste Powietrze", "Weryfikacja Backoffice"), 0)
		self.assertEqual(etap_nr("Fotowoltaika", "Finansowanie Trify"), 0)

	def test_as_etap_nr_nieznany_rodzaj_lub_status_daje_zero(self: "TestVolteoPipeline") -> None:
		self.assertEqual(etap_nr("Nieznany", "Lead"), 0)
		self.assertEqual(etap_nr("Fotowoltaika", "Status Który Nie Istnieje"), 0)
		self.assertEqual(etap_nr("", "Lead"), 0)

	def test_at_etap_nr_none_daje_zero(self: "TestVolteoPipeline") -> None:
		self.assertEqual(etap_nr(None, "Lead"), 0)
		self.assertEqual(etap_nr("Fotowoltaika", None), 0)
		self.assertEqual(etap_nr(None, None), 0)

	def test_au_etap_nr_każdy_rodzaj_i_każdy_status_grupy_zgodny_z_indeksem(
		self: "TestVolteoPipeline",
	) -> None:
		# Dla KAŻDEGO rodzaju z procesem i KAŻDEGO członka grupa_for(rodzaj)
		# (proces + terminale, w tej kolejności): etap_nr == indeks_w_grupie + 1,
		# plus 100 dla CP.
		for rodzaj in (*OZE_RODZAJE, "Czyste Powietrze"):
			offset = 100 if pipeline_key_for(rodzaj) == "CP" else 0
			grupa = grupa_for(rodzaj)
			for indeks, status in enumerate(grupa):
				self.assertEqual(etap_nr(rodzaj, status), offset + indeks + 1)

	def test_av_etap_nr_oze_i_cp_się_nie_przeplatają(self: "TestVolteoPipeline") -> None:
		najwyzszy_oze = max(etap_nr("Fotowoltaika", s) for s in grupa_for("Fotowoltaika"))
		najnizszy_cp = min(etap_nr("Czyste Powietrze", s) for s in grupa_for("Czyste Powietrze"))
		self.assertLess(najwyzszy_oze, najnizszy_cp)

	# --- Katalog pozycji OZE (ops#381) --------------------------------------

	def test_aw_etapy_katalogu_oze_w_pipeline_oze(self: "TestVolteoPipeline") -> None:
		for etap in PODZADANIA_OZE:
			self.assertIn(etap, PIPELINE_OZE)
		self.assertEqual(
			tuple(PODZADANIA_OZE),
			(
				"Umowa Podpisana",
				"Finansowanie",
				"Weryfikacja Backoffice",
				"Monta\u017c",
				"Obs\u0142uga pomonta\u017cowa",
			),
		)

	def test_ax_klucze_oze_unikalne_i_rozłączne_z_cp(self: "TestVolteoPipeline") -> None:
		klucze = [z["klucz"] for zadania in PODZADANIA_OZE.values() for z in zadania]
		self.assertEqual(len(klucze), 29)
		self.assertEqual(len(klucze), len(set(klucze)))
		klucze_cp = {z["klucz"] for zadania in PODZADANIA_CP.values() for z in zadania}
		self.assertFalse(set(klucze) & klucze_cp)

	def test_ay_formy_pozycji_należą_do_form_finansowania(self: "TestVolteoPipeline") -> None:
		self.assertEqual(FORMY_FINANSOWANIA, ("100% Got\u00f3wka", "100% Kredyt", "Got\u00f3wka + Kredyt"))
		for zadania in PODZADANIA_OZE.values():
			for z in zadania:
				self.assertEqual(z["typ"], "weryfikacja")
				self.assertTrue(z["nd_dozwolone"])
				self.assertFalse(z["z_data"])
				for forma in z.get("formy", ()):
					self.assertIn(forma, FORMY_FINANSOWANIA)

	def test_az_pozycje_etapu_finansowanie_wg_formy(self: "TestVolteoPipeline") -> None:
		def klucze(forma):
			return [p["klucz"] for p in pozycje_etapu("Fotowoltaika", "Finansowanie", forma)]

		self.assertEqual(
			klucze("100% Kredyt"),
			[
				"oze_fin:formularz_kredytowy",
				"oze_fin:kredyt_procesowany",
				"oze_fin:kredyt_odrzucony",
				"oze_fin:kredyt_podpisany",
			],
		)
		self.assertEqual(klucze("100% Got\u00f3wka"), ["oze_fin:proforma", "oze_fin:platnosc_klienta"])
		self.assertEqual(len(klucze("Got\u00f3wka + Kredyt")), 6)
		self.assertEqual(klucze("Got\u00f3wka + Kredyt")[0], "oze_fin:formularz_kredytowy")
		self.assertEqual(klucze("Got\u00f3wka + Kredyt")[-1], "oze_fin:platnosc_klienta")
		self.assertEqual(klucze(None), [])
		self.assertEqual(klucze(""), [])

	def test_ba_pozycje_etapu_inne_etapy_i_cp(self: "TestVolteoPipeline") -> None:
		self.assertEqual(len(pozycje_etapu("Fotowoltaika", "Monta\u017c")), 8)
		self.assertEqual(pozycje_etapu("Fotowoltaika", "Lead"), ())
		self.assertEqual(pozycje_etapu("Nieznany", "Monta\u017c"), ())
		cp = pozycje_etapu("Czyste Powietrze", "Dokumentacja", "100% Kredyt")
		self.assertEqual(cp, PODZADANIA_CP["Dokumentacja"])

	def test_bb_czy_pozycja_dla_formy(self: "TestVolteoPipeline") -> None:
		self.assertTrue(czy_pozycja_dla_formy({"klucz": "x"}, None))
		ograniczona = {"klucz": "x", "formy": ("100% Kredyt",)}
		self.assertTrue(czy_pozycja_dla_formy(ograniczona, "100% Kredyt"))
		self.assertFalse(czy_pozycja_dla_formy(ograniczona, "100% Got\u00f3wka"))
		self.assertFalse(czy_pozycja_dla_formy(ograniczona, None))
		self.assertFalse(czy_pozycja_dla_formy(ograniczona, ""))

	def test_bc_wyczysc_po_zmianie_formy(self: "TestVolteoPipeline") -> None:
		mapa = {
			"oze_fin:proforma": {"stan": "accepted"},
			"oze_fin:kredyt_podpisany": {"stan": "waiting"},
			"oze_mon:sprzet_zamowiony": {"stan": "accepted"},
			"dok:zdjecia": {"stan": "accepted"},
			"nieznany:klucz": {"stan": "error"},
		}
		przed = json.dumps(mapa, sort_keys=True)
		wynik = wyczysc_po_zmianie_formy(mapa, "100% Kredyt")
		self.assertEqual(json.dumps(mapa, sort_keys=True), przed)
		self.assertIsNot(wynik, mapa)
		self.assertEqual(
			set(wynik),
			{"oze_fin:kredyt_podpisany", "oze_mon:sprzet_zamowiony", "dok:zdjecia", "nieznany:klucz"},
		)
		self.assertEqual(
			set(wyczysc_po_zmianie_formy(mapa, "")),
			{"oze_mon:sprzet_zamowiony", "dok:zdjecia", "nieznany:klucz"},
		)
		self.assertEqual(len(wyczysc_po_zmianie_formy(mapa, "Got\u00f3wka + Kredyt")), 5)

	def test_bd_podsumowanie_etapu_wektory(self: "TestVolteoPipeline") -> None:
		pozycje = PODZADANIA_OZE["Umowa Podpisana"]
		mapa = {
			"oze_up:akceptacja_klienta": {"stan": "accepted"},
			"oze_up:akceptacja_handlowca": {"stan": "accepted"},
		}
		self.assertEqual(podsumowanie_etapu(pozycje, mapa), {"ok": 2, "err": 0, "razem": 3})

		pozycje = PODZADANIA_OZE["Monta\u017c"]
		mapa = {p["klucz"]: {"stan": "accepted"} for p in pozycje[:4]}
		mapa[pozycje[4]["klucz"]] = {"stan": "nd"}
		mapa[pozycje[5]["klucz"]] = {"stan": "waiting"}
		self.assertEqual(podsumowanie_etapu(pozycje, mapa), {"ok": 4, "err": 0, "razem": 7})

		pozycje = pozycje_etapu("Fotowoltaika", "Finansowanie", "100% Kredyt")
		mapa = {
			pozycje[0]["klucz"]: {"stan": "accepted"},
			pozycje[1]["klucz"]: {"stan": "error"},
		}
		self.assertEqual(podsumowanie_etapu(pozycje, mapa), {"ok": 1, "err": 1, "razem": 4})

	def test_be_podsumowanie_szansy(self: "TestVolteoPipeline") -> None:
		self.assertIsNone(podsumowanie_szansy("Czyste Powietrze", "Dokumentacja", {}, None))
		self.assertIsNone(podsumowanie_szansy("Fotowoltaika", "Lead", {}, None))
		self.assertIsNone(podsumowanie_szansy("Nieznany", "Monta\u017c", {}, None))
		self.assertEqual(
			podsumowanie_szansy("Fotowoltaika", "Finansowanie", {}, None),
			{"ok": 0, "err": 0, "razem": 0},
		)
		self.assertEqual(
			podsumowanie_szansy("Fotowoltaika", "Finansowanie", {}, "100% Got\u00f3wka"),
			{"ok": 0, "err": 0, "razem": 2},
		)
		self.assertEqual(
			podsumowanie_szansy("Klimatyzacja", "Monta\u017c", {"oze_mon:platnosc_100": {"stan": "accepted"}}, None),
			{"ok": 1, "err": 0, "razem": 8},
		)

	def test_bf_wywołania_oze_nie_mutują_katalogu(self: "TestVolteoPipeline") -> None:
		przed = {e: tuple(dict(z) for z in zs) for e, zs in PODZADANIA_OZE.items()}
		definicja = podzadanie_def("Fotowoltaika", "oze_fin:proforma")
		self.assertEqual(definicja["formy"], ("100% Got\u00f3wka", "Got\u00f3wka + Kredyt"))
		definicja["label"] = "ZMIENIONE"
		pozycje_etapu("Fotowoltaika", "Finansowanie", "100% Kredyt")
		self.assertEqual({e: tuple(dict(z) for z in zs) for e, zs in PODZADANIA_OZE.items()}, przed)


if __name__ == "__main__":
	unittest.main()
