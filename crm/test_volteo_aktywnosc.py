import datetime
import unittest
from typing import ClassVar

from crm.volteo_aktywnosc import (
	OKNO_GRUPOWANIA_S,
	POLA_WLASNA_LINIA,
	ZNACZNIK_KOSZTY,
	ZNACZNIKI_ADMIN,
	bez_znacznika,
	czy_widoczny,
	grupuj,
	linie_z_wersji,
	roznice_plikow_audytu,
	tekst_sladu,
	zapisz_slad,
)

ETYKIETY = {
	"status": "Status",
	"lost_reason": "Powód przegranej",
	"lost_notes": "Notatki przegranej",
	"deal_owner": "Właściciel szansy",
	"organization": "Firma",
	"custom_rodzaj_umowy": "Rodzaj umowy",
	"custom_zasady_dotacji": "Zasady dotacji",
	"custom_narzut": "Narzut",
	"custom_pv_power_kwp": "Moc PV (kWp)",
}


class TestLinieZWersjiPolaWlasne(unittest.TestCase):
	def test_a_status_i_powod_daja_dwie_linie_bez_podsumowania(self: "TestLinieZWersjiPolaWlasne") -> None:
		data = {"changed": [["status", "Lead", "Umowa Wygenerowana"], ["lost_reason", None, "Cena"]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(len(linie), 2)
		self.assertEqual(linie[0]["rodzaj"], "pole")
		self.assertEqual(linie[0]["field"], "status")
		self.assertEqual(linie[0]["text"], "zmieniono Status: Lead → Umowa Wygenerowana")
		self.assertEqual(linie[1]["field"], "lost_reason")
		self.assertEqual(linie[1]["text"], "ustawiono Powód przegranej: Cena")
		self.assertTrue(all(linia["rodzaj"] != "podsumowanie" for linia in linie))

	def test_b_kolejnosc_linii_wlasnych_wg_krotki_nie_wg_wersji(self: "TestLinieZWersjiPolaWlasne") -> None:
		# lost_reason jest w danych PRZED status, ale POLA_WLASNA_LINIA ma status pierwszy.
		data = {"changed": [["lost_reason", None, "Cena"], ["status", "Lead", "Przegrana"]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual([linia["field"] for linia in linie], ["status", "lost_reason"])

	def test_c_usunieto_gdy_nowa_wartosc_pusta(self: "TestLinieZWersjiPolaWlasne") -> None:
		data = {"changed": [["lost_reason", "Cena", None]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie[0]["text"], "usunięto Powód przegranej: Cena")

	def test_d_pole_bez_etykiety_dostaje_etykiete_rowna_nazwie_pola(self: "TestLinieZWersjiPolaWlasne") -> None:
		data = {"changed": [["custom_narzut", 1000, 2000]]}
		linie = linie_z_wersji(data, {})
		self.assertEqual(linie[0]["field_label"], "custom_narzut")
		self.assertEqual(linie[0]["text"], "zmieniono custom_narzut: 1000 → 2000")

	def test_e_pusty_do_pustego_nie_daje_linii(self: "TestLinieZWersjiPolaWlasne") -> None:
		data = {"changed": [["lost_reason", None, ""], ["lost_reason", "", None]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie, [])

	def test_f_pusta_lista_gdy_brak_changed(self: "TestLinieZWersjiPolaWlasne") -> None:
		self.assertEqual(linie_z_wersji({}, ETYKIETY), [])
		self.assertEqual(linie_z_wersji({"changed": []}, ETYKIETY), [])


class TestLinieZWersjiPodsumowanie(unittest.TestCase):
	def test_a_wersja_kalkulatora_24_pola(self: "TestLinieZWersjiPodsumowanie") -> None:
		# 24 pola zmienione łącznie: custom_pv_power_kwp pierwsze, custom_narzut w
		# środku (jedyne pole z POLA_WLASNA_LINIA) -- reszta (23 pola) idzie do
		# jednego podsumowania: pierwsze 5 etykiet pokazane, +18 więcej (23-5=18).
		pola = ["custom_pv_power_kwp" if i == 0 else f"custom_pole_{i}" for i in range(24)]
		pola[12] = "custom_narzut"
		self.assertEqual(len(pola), 24)
		self.assertEqual(pola[0], "custom_pv_power_kwp")
		self.assertIn("custom_narzut", pola)

		changed = [[fn, 0, 1] for fn in pola]
		data = {"changed": changed}
		linie = linie_z_wersji(data, ETYKIETY)

		wlasne = [linia for linia in linie if linia["rodzaj"] == "pole"]
		podsumowania = [linia for linia in linie if linia["rodzaj"] == "podsumowanie"]
		self.assertEqual(len(wlasne), 1)
		self.assertEqual(wlasne[0]["field"], "custom_narzut")
		self.assertEqual(len(podsumowania), 1)
		self.assertTrue(podsumowania[0]["text"].startswith("zmieniono 23 pól: "))
		self.assertTrue(podsumowania[0]["text"].endswith(", +18 więcej"))

	def test_b_jedno_pole_pozostale_daje_liczbe_pojedyncza(self: "TestLinieZWersjiPodsumowanie") -> None:
		data = {"changed": [["custom_cos", None, "x"]]}
		linie = linie_z_wersji(data, {"custom_cos": "Coś"})
		self.assertEqual(len(linie), 1)
		self.assertEqual(linie[0]["rodzaj"], "podsumowanie")
		self.assertEqual(linie[0]["text"], "zmieniono pole: Coś")

	def test_c_avoid_wyklucza_pole_z_podsumowania(self: "TestLinieZWersjiPodsumowanie") -> None:
		data = {"changed": [["lead", "a", "b"], ["custom_cos", None, "x"]]}
		linie = linie_z_wersji(data, {"custom_cos": "Coś"}, avoid=("lead",))
		self.assertEqual(len(linie), 1)
		self.assertEqual(linie[0]["text"], "zmieniono pole: Coś")

	def test_d_avoid_wszystkiego_daje_brak_podsumowania(self: "TestLinieZWersjiPodsumowanie") -> None:
		data = {"changed": [["lead", "a", "b"], ["sla", "x", "y"]]}
		linie = linie_z_wersji(data, {}, avoid=("lead", "sla"))
		# brak linii wlasnych (lead/sla nie sa w POLA_WLASNA_LINIA) i brak podsumowania
		self.assertEqual(linie, [])

	def test_e_podsumowanie_zachowuje_kolejnosc_wystapienia(self: "TestLinieZWersjiPodsumowanie") -> None:
		data = {"changed": [["b", None, "1"], ["a", None, "1"], ["c", None, "1"]]}
		linie = linie_z_wersji(data, {})
		self.assertEqual(linie[0]["text"], "zmieniono 3 pól: b, a, c")

	def test_f_pola_wlasna_linia_nigdy_nie_trafiaja_do_podsumowania(
		self: "TestLinieZWersjiPodsumowanie",
	) -> None:
		changed = [[fn, "stare", "nowe"] for fn in POLA_WLASNA_LINIA]
		linie = linie_z_wersji({"changed": changed}, ETYKIETY)
		self.assertEqual(len(linie), len(POLA_WLASNA_LINIA))
		self.assertTrue(all(linia["rodzaj"] == "pole" for linia in linie))


class TestLinieZWersjiKontakty(unittest.TestCase):
	def test_a_dodano_kontakt(self: "TestLinieZWersjiKontakty") -> None:
		data = {"added": [["contacts", {"contact": "Jan Kowalski", "name": "row1", "is_primary": 0}]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie, [{"rodzaj": "kontakt", "text": "dodano kontakt Jan Kowalski"}])

	def test_b_usunieto_kontakt(self: "TestLinieZWersjiKontakty") -> None:
		data = {"removed": [["contacts", {"contact": "Jan Kowalski", "name": "row1"}]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie, [{"rodzaj": "kontakt", "text": "usunięto kontakt Jan Kowalski"}])

	def test_c_row_changed_is_primary_0_do_1_ustawia_glowny(self: "TestLinieZWersjiKontakty") -> None:
		data = {"row_changed": [["contacts", 0, "row1", [["is_primary", 0, 1], ["contact", "x", "x"]]]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(len(linie), 1)
		self.assertEqual(linie[0]["rodzaj"], "kontakt")
		self.assertIn("ustawiono główny kontakt", linie[0]["text"])

	def test_d_row_changed_is_primary_1_do_0_nie_daje_linii(self: "TestLinieZWersjiKontakty") -> None:
		data = {"row_changed": [["contacts", 0, "row1", [["is_primary", 1, 0]]]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie, [])

	def test_e_row_changed_bez_row_name_uzywa_contact_z_pol(self: "TestLinieZWersjiKontakty") -> None:
		data = {"row_changed": [["contacts", 0, None, [["is_primary", 0, 1], ["contact", "Anna Nowak", "Anna Nowak"]]]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie[0]["text"], "ustawiono główny kontakt Anna Nowak")

	def test_f_row_changed_bez_contact_pola_uzywa_row_name(self: "TestLinieZWersjiKontakty") -> None:
		data = {"row_changed": [["contacts", 0, "row-xyz", [["is_primary", 0, 1]]]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie[0]["text"], "ustawiono główny kontakt row-xyz")

	def test_g_inna_tabela_niz_contacts_jest_ignorowana(self: "TestLinieZWersjiKontakty") -> None:
		data = {"added": [["custom_inna_tabela", {"contact": "X"}]]}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(linie, [])


class TestLinieZWersjiCustomZestaw(unittest.TestCase):
	def test_a_added_custom_zestaw_ignorowane(self: "TestLinieZWersjiCustomZestaw") -> None:
		data = {"added": [["custom_zestaw", {"typ": "panel", "nazwa": "X", "ilosc": 10}]]}
		self.assertEqual(linie_z_wersji(data, ETYKIETY), [])

	def test_b_removed_custom_zestaw_ignorowane(self: "TestLinieZWersjiCustomZestaw") -> None:
		data = {"removed": [["custom_zestaw", {"typ": "panel"}]]}
		self.assertEqual(linie_z_wersji(data, ETYKIETY), [])

	def test_c_row_changed_custom_zestaw_ignorowane(self: "TestLinieZWersjiCustomZestaw") -> None:
		data = {"row_changed": [["custom_zestaw", 0, "row1", [["ilosc", 1, 2]]]]}
		self.assertEqual(linie_z_wersji(data, ETYKIETY), [])

	def test_d_mieszana_wersja_zestaw_i_pole_wlasne(self: "TestLinieZWersjiCustomZestaw") -> None:
		data = {
			"changed": [["status", "Lead", "Umowa Wygenerowana"]],
			"row_changed": [["custom_zestaw", 0, "row1", [["ilosc", 1, 2]]]],
		}
		linie = linie_z_wersji(data, ETYKIETY)
		self.assertEqual(len(linie), 1)
		self.assertEqual(linie[0]["field"], "status")


class TestLinieZWersjiImmutable(unittest.TestCase):
	def test_a_nie_mutuje_data_ani_etykiety(self: "TestLinieZWersjiImmutable") -> None:
		data = {"changed": [["status", "Lead", "Wygrana"], ["custom_cos", None, "x"]]}
		etykiety = dict(ETYKIETY)
		data_kopia = {"changed": [list(w) for w in data["changed"]]}
		etykiety_kopia = dict(etykiety)
		linie_z_wersji(data, etykiety)
		self.assertEqual(data, data_kopia)
		self.assertEqual(etykiety, etykiety_kopia)


class TestGrupuj(unittest.TestCase):
	def _wpis(self, typ: str, owner: str, creation: str, pole: str | None = None) -> dict:
		dane = {"field": pole} if pole else {}
		return {"activity_type": typ, "owner": owner, "creation": creation, "data": dane}

	def test_a_skleja_w_oknie_600s(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:10:00"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 1)
		self.assertEqual(len(wynik[0]["other_versions"]), 1)

	def test_b_nie_skleja_przy_601s(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:10:01"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 2)
		self.assertNotIn("other_versions", wynik[0])
		self.assertNotIn("other_versions", wynik[1])

	def test_c_nie_skleja_roznych_autorow(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:30"),
			self._wpis("changed", "b@x.pl", "2026-09-03 12:00:00"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 2)

	def test_d_status_zawsze_osobno_i_przerywa_grupe(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:30"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:20", pole="status"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 3)
		for pozycja in wynik:
			self.assertNotIn("other_versions", pozycja)

	def test_e_inne_typy_aktywnosci_zawsze_osobno(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:30"),
			{"activity_type": "comment", "owner": "a@x.pl", "creation": "2026-09-03 12:00:25", "data": {}},
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 3)

	def test_f_nie_mutuje_wejscia(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:30"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		kopia = [dict(w) for w in wpisy]
		grupuj(wpisy)
		self.assertEqual(wpisy, kopia)
		for w in wpisy:
			self.assertNotIn("other_versions", w)

	def test_g_akceptuje_datetime_obiekty(self: "TestGrupuj") -> None:
		wpisy = [
			{
				"activity_type": "changed",
				"owner": "a@x.pl",
				"creation": datetime.datetime(2026, 9, 3, 12, 10, 0),
				"data": {},
			},
			{
				"activity_type": "changed",
				"owner": "a@x.pl",
				"creation": datetime.datetime(2026, 9, 3, 12, 0, 0),
				"data": {},
			},
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 1)

	def test_h_akceptuje_creation_z_mikrosekundami(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:05:00.123456"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00.654321"),
		]
		wynik = grupuj(wpisy)
		self.assertEqual(len(wynik), 1)

	def test_i_pusta_lista_daje_pusta_liste(self: "TestGrupuj") -> None:
		self.assertEqual(grupuj([]), [])

	def test_j_okno_konfigurowalne(self: "TestGrupuj") -> None:
		wpisy = [
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:30"),
			self._wpis("changed", "a@x.pl", "2026-09-03 12:00:00"),
		]
		self.assertEqual(len(grupuj(wpisy, okno_s=10)), 2)
		self.assertEqual(len(grupuj(wpisy, okno_s=OKNO_GRUPOWANIA_S)), 1)


class TestCzyWidocznyIBezZnacznika(unittest.TestCase):
	def test_a_znacznik_kosztow_ukryty_bez_roli_admina(self: "TestCzyWidocznyIBezZnacznika") -> None:
		text = f"{ZNACZNIK_KOSZTY} zaktualizowano koszty rzeczywiste (3 pozycji, 1 dodatkowych)"
		self.assertFalse(czy_widoczny(text, role=["Volteo D2D Sales"], admin_role=["System Manager", "Volteo Core Admin"]))

	def test_b_znacznik_kosztow_widoczny_z_rola_admina(self: "TestCzyWidocznyIBezZnacznika") -> None:
		text = f"{ZNACZNIK_KOSZTY} zaktualizowano koszty rzeczywiste (3 pozycji, 1 dodatkowych)"
		self.assertTrue(czy_widoczny(text, role=["Volteo Core Admin"], admin_role=["System Manager", "Volteo Core Admin"]))

	def test_c_tekst_bez_znacznika_zawsze_widoczny(self: "TestCzyWidocznyIBezZnacznika") -> None:
		self.assertTrue(czy_widoczny("zmieniono Status: Lead → Wygrana", role=[], admin_role=["System Manager"]))

	def test_d_bez_znacznika_usuwa_prefiks(self: "TestCzyWidocznyIBezZnacznika") -> None:
		text = f"{ZNACZNIK_KOSZTY} zaktualizowano koszty rzeczywiste (3 pozycji, 1 dodatkowych)"
		self.assertEqual(bez_znacznika(text), "zaktualizowano koszty rzeczywiste (3 pozycji, 1 dodatkowych)")

	def test_e_bez_znacznika_bez_zmian_gdy_brak_prefiksu(self: "TestCzyWidocznyIBezZnacznika") -> None:
		self.assertEqual(bez_znacznika("zmieniono Status: Lead → Wygrana"), "zmieniono Status: Lead → Wygrana")

	def test_f_znaczniki_admin_zawiera_znacznik_kosztow(self: "TestCzyWidocznyIBezZnacznika") -> None:
		self.assertIn(ZNACZNIK_KOSZTY, ZNACZNIKI_ADMIN)


class TestRozniceplikowAudytu(unittest.TestCase):
	SLOTY: ClassVar[dict[str, str]] = {
		"dok_umowa": "Umowa na obsługę dotacji",
		"dok_zaswiadczenie": "Zaświadczenie GOPS",
	}

	def test_a_dodano_slot(self: "TestRozniceplikowAudytu") -> None:
		wynik = roznice_plikow_audytu({}, {"dok_umowa": "/files/a.pdf"}, [], [], self.SLOTY)
		self.assertEqual(wynik, ["dodano dokument audytu: Umowa na obsługę dotacji"])

	def test_b_usunieto_slot(self: "TestRozniceplikowAudytu") -> None:
		wynik = roznice_plikow_audytu({"dok_umowa": "/files/a.pdf"}, {}, [], [], self.SLOTY)
		self.assertEqual(wynik, ["usunięto dokument audytu: Umowa na obsługę dotacji"])

	def test_c_zmieniono_slot(self: "TestRozniceplikowAudytu") -> None:
		wynik = roznice_plikow_audytu(
			{"dok_umowa": "/files/a.pdf"}, {"dok_umowa": "/files/b.pdf"}, [], [], self.SLOTY
		)
		self.assertEqual(wynik, ["zmieniono dokument audytu: Umowa na obsługę dotacji"])

	def test_d_zdjecia_rozne_daje_linie(self: "TestRozniceplikowAudytu") -> None:
		wynik = roznice_plikow_audytu({}, {}, ["/f/1.jpg"], ["/f/1.jpg", "/f/2.jpg"], self.SLOTY)
		self.assertEqual(wynik, ["zmieniono zdjęcia audytu"])

	def test_e_zdjecia_takie_same_nie_daje_linii(self: "TestRozniceplikowAudytu") -> None:
		wynik = roznice_plikow_audytu({}, {}, ["/f/1.jpg"], ["/f/1.jpg"], self.SLOTY)
		self.assertEqual(wynik, [])

	def test_f_brak_zmian_daje_pusta_liste(self: "TestRozniceplikowAudytu") -> None:
		self.assertEqual(roznice_plikow_audytu({"a": "x"}, {"a": "x"}, [], [], {}), [])

	def test_g_nie_mutuje_argumentow(self: "TestRozniceplikowAudytu") -> None:
		stare = {"dok_umowa": "/files/a.pdf"}
		nowe = {"dok_umowa": "/files/b.pdf"}
		stare_zdj = ["/f/1.jpg"]
		nowe_zdj = ["/f/2.jpg"]
		stare_kopia, nowe_kopia = dict(stare), dict(nowe)
		roznice_plikow_audytu(stare, nowe, stare_zdj, nowe_zdj, self.SLOTY)
		self.assertEqual(stare, stare_kopia)
		self.assertEqual(nowe, nowe_kopia)


class TestTekstSladu(unittest.TestCase):
	def test_a_podzadanie_bez_notatki(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("podzadanie", label="Audyt zlecony", stan="accepted"),
			'ustawiono stan podzadania „Audyt zlecony” na: accepted',
		)

	def test_b_podzadanie_z_notatka(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("podzadanie", label="Audyt zlecony", stan="error", note="brak kontaktu"),
			'ustawiono stan podzadania „Audyt zlecony” na: error — „brak kontaktu”',
		)

	def test_c_podzadanie_cofniete(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("podzadanie", label="Audyt zlecony", stan="accepted", cofnieto=True),
			"cofnięto stan podzadania: Audyt zlecony",
		)

	def test_d_autenti_wyslano_umowe(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("autenti_wyslano", dokument="umowę"), "wysłano umowę do podpisu Autenti")

	def test_e_autenti_wyslano_kredyt(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("autenti_wyslano", dokument="formularz kredytowy"),
			"wysłano formularz kredytowy do podpisu Autenti",
		)

	def test_f_autenti_status(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("autenti_status", dokument="umowę", status="Podpisana"),
			"Autenti: umowę — Podpisana",
		)

	def test_g_autenti_pdf(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("autenti_pdf", dokument="umowę"), "podpięto podpisany PDF (umowę)")

	def test_h_umowa_utworzono(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("umowa_utworzono"), "utworzono umowę (formularz roboczy)")

	def test_i_umowa_pdf(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("umowa_pdf"), "wygenerowano PDF umowy")

	def test_j_kredyt_utworzono(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("kredyt_utworzono"), "utworzono formularz kredytowy")

	def test_k_kredyt_pdf(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("kredyt_pdf"), "wygenerowano PDF formularza kredytowego")

	def test_l_koszty_nigdy_nie_niesie_kwot(self: "TestTekstSladu") -> None:
		text = tekst_sladu("koszty", pozycje=3, dodatkowe=1)
		self.assertEqual(text, f"{ZNACZNIK_KOSZTY} zaktualizowano koszty rzeczywiste (3 pozycji, 1 dodatkowych)")
		self.assertTrue(text.startswith(ZNACZNIK_KOSZTY))

	def test_m_status_auto(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("status_auto", automatyzacja="Umowa Wygenerowana", stary="Lead", nowy="Umowa Wygenerowana"),
			"status zmieniony automatycznie (Umowa Wygenerowana): Lead → Umowa Wygenerowana",
		)

	def test_n_kalkulator_oze(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("kalkulator_oze", moc_kw=6.5, pozycje=12),
			"utworzono szansę z kalkulatora OZE: 6.5 kW, 12 pozycji zestawu",
		)

	def test_o_kalkulator_cp(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("kalkulator_cp", pozycje=4),
			"utworzono szansę z kalkulatora Czyste Powietrze: 4 pozycji zestawu",
		)

	def test_p_audyt_plik_dodano(self: "TestTekstSladu") -> None:
		self.assertEqual(
			tekst_sladu("audyt_plik", akcja="dodano", etykieta="Zdjęcia"),
			"dodano dokument audytu: Zdjęcia",
		)

	def test_q_audyt_plik_nieznana_akcja(self: "TestTekstSladu") -> None:
		with self.assertRaises(ValueError):
			tekst_sladu("audyt_plik", akcja="cos innego", etykieta="X")

	def test_r_audyt_zdjecia(self: "TestTekstSladu") -> None:
		self.assertEqual(tekst_sladu("audyt_zdjecia"), "zmieniono zdjęcia audytu")

	def test_s_nieznany_rodzaj_daje_value_error(self: "TestTekstSladu") -> None:
		with self.assertRaises(ValueError):
			tekst_sladu("cos_nieznanego")


class TestZapiszSladBezFrappe(unittest.TestCase):
	def test_a_wywolanie_bez_frappe_rzuca_import_error(self: "TestZapiszSladBezFrappe") -> None:
		# frappe nie jest zainstalowane lokalnie -- funkcja MUSI robić import lokalny
		# (a nie na poziomie modułu), inaczej cały moduł nie zaimportowałby się w ogóle.
		with self.assertRaises(ImportError):
			zapisz_slad("CRM-DEAL-2026-00001", "tekst")


if __name__ == "__main__":
	unittest.main()
