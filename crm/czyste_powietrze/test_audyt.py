import unittest

from crm.czyste_powietrze.audyt import (
	ETYKIETA_ZDJECIA,
	KLUCZ_ZDJECIA,
	MAX_NOTATKA,
	MAX_ZDJEC,
	SLOTY_DOKUMENTOW,
	STATUSY,
	WERDYKTY,
	agreguj,
	braki_do_przeslania,
	elementy_weryfikacji,
	etykieta_dla,
	parsuj_liste,
	parsuj_mape,
	resetuj_werdykty,
	waliduj_werdykt,
)

PLIK_ISTNIEJE = lambda _url: True  # noqa: E731
PLIK_NIE_ISTNIEJE = lambda _url: False  # noqa: E731

_KLUCZE_WYMAGANE = tuple(slot["klucz"] for slot in SLOTY_DOKUMENTOW if slot["wymagany"])
_KLUCZE_OPCJONALNE = tuple(slot["klucz"] for slot in SLOTY_DOKUMENTOW if not slot["wymagany"])


def _komplet_dokumentow() -> dict:
	return {slot["klucz"]: f"/files/{slot['klucz']}.pdf" for slot in SLOTY_DOKUMENTOW}


def _zdjecia(n: int) -> list:
	return [f"/files/zdjecie-{i}.jpg" for i in range(n)]


class TestKatalogSlotow(unittest.TestCase):
	def test_siedem_slotow(self):
		self.assertEqual(len(SLOTY_DOKUMENTOW), 7)

	def test_piec_wymaganych(self):
		self.assertEqual(len(_KLUCZE_WYMAGANE), 5)
		self.assertEqual(len(_KLUCZE_OPCJONALNE), 2)

	def test_klucze_unikalne(self):
		klucze = [slot["klucz"] for slot in SLOTY_DOKUMENTOW]
		self.assertEqual(len(klucze), len(set(klucze)))

	def test_kazdy_slot_ma_wymagane_pola(self):
		for slot in SLOTY_DOKUMENTOW:
			self.assertIn("klucz", slot)
			self.assertIn("etykieta", slot)
			self.assertIn("wymagany", slot)
			self.assertIsInstance(slot["wymagany"], bool)

	def test_statusy_i_werdykty(self):
		self.assertEqual(STATUSY, ("Szkic", "Weryfikacja", "Zatwierdzony"))
		self.assertEqual(WERDYKTY, ("accepted", "error"))

	def test_stale_liczbowe(self):
		self.assertEqual(MAX_ZDJEC, 20)
		self.assertEqual(MAX_NOTATKA, 500)

	def test_klucze_pokrywaja_sie_z_pipeline(self):
		# Cementuje kontrakt przyszłego syncu z crm.volteo_pipeline.PODZADANIA_CP: każdy
		# klucz slotu tego modułu (plus KLUCZ_ZDJECIA) musi wystąpić wśród kluczy podzadań
		# etapu "Dokumentacja". Import lokalny -- ten moduł nie zależy od volteo_pipeline
		# w kodzie produkcyjnym, tylko test asercją trzyma je zsynchronizowane.
		from crm.volteo_pipeline import PODZADANIA_CP

		klucze_pipeline = {zadanie["klucz"] for zadanie in PODZADANIA_CP["Dokumentacja"]}
		klucze_audytu = {slot["klucz"] for slot in SLOTY_DOKUMENTOW} | {KLUCZ_ZDJECIA}
		self.assertTrue(klucze_audytu.issubset(klucze_pipeline))


class TestEtykietaDla(unittest.TestCase):
	def test_etykieta_slotu(self):
		self.assertEqual(etykieta_dla("dok:ankieta_cp"), "Ankieta danych Czyste Powietrze")

	def test_etykieta_zdjec(self):
		self.assertEqual(etykieta_dla(KLUCZ_ZDJECIA), ETYKIETA_ZDJECIA)

	def test_nieznany_klucz_zwraca_siebie(self):
		self.assertEqual(etykieta_dla("dok:nieznany"), "dok:nieznany")


class TestParsujMape(unittest.TestCase):
	def test_none(self):
		self.assertEqual(parsuj_mape(None), {})

	def test_pusty_string(self):
		self.assertEqual(parsuj_mape(""), {})

	def test_dict_bez_zmian(self):
		mapa = {"a": 1}
		self.assertEqual(parsuj_mape(mapa), mapa)

	def test_poprawny_json(self):
		self.assertEqual(parsuj_mape('{"a": 1}'), {"a": 1})

	def test_podwojnie_zakodowany_json(self):
		self.assertEqual(parsuj_mape('"{\\"a\\": 1}"'), {"a": 1})

	def test_smieciowy_string(self):
		self.assertEqual(parsuj_mape("nie json"), {})

	def test_json_liste(self):
		self.assertEqual(parsuj_mape("[1, 2]"), {})

	def test_zla_liczba(self):
		self.assertEqual(parsuj_mape(123), {})

	def test_zla_lista(self):
		self.assertEqual(parsuj_mape([1, 2]), {})


class TestParsujListe(unittest.TestCase):
	def test_none(self):
		self.assertEqual(parsuj_liste(None), [])

	def test_pusty_string(self):
		self.assertEqual(parsuj_liste(""), [])

	def test_lista_bez_zmian(self):
		self.assertEqual(parsuj_liste(["a", "b"]), ["a", "b"])

	def test_poprawny_json(self):
		self.assertEqual(parsuj_liste('["a", "b"]'), ["a", "b"])

	def test_podwojnie_zakodowany_json(self):
		self.assertEqual(parsuj_liste('"[\\"a\\", \\"b\\"]"'), ["a", "b"])

	def test_smieciowy_string(self):
		self.assertEqual(parsuj_liste("nie json"), [])

	def test_json_mape(self):
		self.assertEqual(parsuj_liste('{"a": 1}'), [])

	def test_odfiltrowuje_nie_stringi(self):
		self.assertEqual(parsuj_liste(["a", 1, None, "", "b", 2.5, True]), ["a", "b"])

	def test_zla_liczba(self):
		self.assertEqual(parsuj_liste(123), [])


class TestBrakiDoPrzeslania(unittest.TestCase):
	def test_komplet_bez_brakow(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), _zdjecia(3), PLIK_ISTNIEJE)
		self.assertEqual(braki, [])

	def test_brak_wymaganego_slotu(self):
		dokumenty = _komplet_dokumentow()
		del dokumenty["dok:ankieta_cp"]
		braki = braki_do_przeslania(dokumenty, _zdjecia(1), PLIK_ISTNIEJE)
		self.assertIn("Ankieta danych Czyste Powietrze", braki)

	def test_brak_opcjonalnego_nie_blokuje(self):
		dokumenty = _komplet_dokumentow()
		del dokumenty["dok:zgoda_wspolwlascicieli"]
		del dokumenty["dok:zgoda_wspolmalzonka"]
		braki = braki_do_przeslania(dokumenty, _zdjecia(1), PLIK_ISTNIEJE)
		self.assertEqual(braki, [])

	def test_callback_odrzuca_url_slotu(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), _zdjecia(1), PLIK_NIE_ISTNIEJE)
		# Każdy wgrany slot (5 wymaganych + 2 opcjonalne) + każde zdjęcie ma dostać brak.
		self.assertEqual(len(braki), 7 + 1)
		self.assertTrue(any("plik nie istnieje" in b for b in braki))

	def test_zero_zdjec_blokuje(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), [], PLIK_ISTNIEJE)
		self.assertTrue(any("co najmniej 1 zdjęcie" in b for b in braki))

	def test_21_zdjec_blokuje(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), _zdjecia(21), PLIK_ISTNIEJE)
		self.assertTrue(any("limit 20 zdjęć" in b for b in braki))

	def test_20_zdjec_przechodzi(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), _zdjecia(20), PLIK_ISTNIEJE)
		self.assertEqual(braki, [])

	def test_callback_odrzuca_zdjecie(self):
		braki = braki_do_przeslania(_komplet_dokumentow(), ["/files/zle.jpg"], PLIK_NIE_ISTNIEJE)
		self.assertTrue(any("/files/zle.jpg" in b for b in braki))


class TestElementyWeryfikacji(unittest.TestCase):
	def test_opcjonalny_bez_pliku_wykluczony(self):
		dokumenty = _komplet_dokumentow()
		del dokumenty["dok:zgoda_wspolwlascicieli"]
		elementy = elementy_weryfikacji(dokumenty, _zdjecia(1))
		self.assertNotIn("dok:zgoda_wspolwlascicieli", elementy)

	def test_opcjonalny_z_plikiem_wlaczony(self):
		elementy = elementy_weryfikacji(_komplet_dokumentow(), _zdjecia(1))
		self.assertIn("dok:zgoda_wspolwlascicieli", elementy)

	def test_grupa_zawsze_na_koncu(self):
		elementy = elementy_weryfikacji(_komplet_dokumentow(), _zdjecia(1))
		self.assertEqual(elementy[-1], KLUCZ_ZDJECIA)

	def test_grupa_obecna_nawet_bez_zdjec(self):
		elementy = elementy_weryfikacji({}, [])
		self.assertEqual(elementy, [KLUCZ_ZDJECIA])

	def test_kolejnosc_katalogu_zachowana(self):
		elementy = elementy_weryfikacji(_komplet_dokumentow(), _zdjecia(1))
		oczekiwane = [slot["klucz"] for slot in SLOTY_DOKUMENTOW] + [KLUCZ_ZDJECIA]
		self.assertEqual(elementy, oczekiwane)


class TestAgreguj(unittest.TestCase):
	def test_zero_elementow_nie_jest_kompletem(self):
		wynik = agreguj({}, [])
		self.assertEqual(wynik["razem"], 0)
		self.assertFalse(wynik["wszystkie_zaakceptowane"])

	def test_mieszane_stany(self):
		elementy = ["a", "b", "c", "d"]
		weryfikacja = {
			"a": {"status": "accepted"},
			"b": {"status": "error", "note": "zły plik"},
		}
		wynik = agreguj(weryfikacja, elementy)
		self.assertEqual(wynik["razem"], 4)
		self.assertEqual(wynik["zaakceptowane"], 1)
		self.assertEqual(wynik["bledy"], 1)
		self.assertEqual(wynik["oczekuje"], 2)
		self.assertFalse(wynik["wszystkie_zaakceptowane"])

	def test_komplet_zaakceptowany(self):
		elementy = ["a", "b"]
		weryfikacja = {"a": {"status": "accepted"}, "b": {"status": "accepted"}}
		wynik = agreguj(weryfikacja, elementy)
		self.assertEqual(wynik["zaakceptowane"], 2)
		self.assertEqual(wynik["oczekuje"], 0)
		self.assertTrue(wynik["wszystkie_zaakceptowane"])

	def test_wpis_spoza_elementow_ignorowany(self):
		# Werdykt dla klucza, który nie jest już elementem (np. plik usunięty), nie ma
		# wpływać na agregację -- liczymy tylko po `elementy`.
		weryfikacja = {"nieaktualny": {"status": "accepted"}}
		wynik = agreguj(weryfikacja, ["a"])
		self.assertEqual(wynik["razem"], 1)
		self.assertEqual(wynik["zaakceptowane"], 0)
		self.assertEqual(wynik["oczekuje"], 1)


class TestWaliduWerdykt(unittest.TestCase):
	def setUp(self):
		self.dokumenty = _komplet_dokumentow()
		self.zdjecia = _zdjecia(2)

	def test_klucz_nieznany(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:nieistnieje", "accepted", None, self.dokumenty, self.zdjecia)

	def test_klucz_pustego_slotu_nie_jest_elementem(self):
		dokumenty = dict(self.dokumenty)
		del dokumenty["dok:zgoda_wspolwlascicieli"]
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:zgoda_wspolwlascicieli", "accepted", None, dokumenty, self.zdjecia)

	def test_status_spoza_zbioru(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:ankieta_cp", "zatwierdzone", None, self.dokumenty, self.zdjecia)

	def test_error_bez_notatki(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:ankieta_cp", "error", "", self.dokumenty, self.zdjecia)

	def test_error_z_sama_bialymi_znakami(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:ankieta_cp", "error", "   ", self.dokumenty, self.zdjecia)

	def test_error_z_none_jako_notatka(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt("dok:ankieta_cp", "error", None, self.dokumenty, self.zdjecia)

	def test_notatka_za_dluga(self):
		with self.assertRaises(ValueError):
			waliduj_werdykt(
				"dok:ankieta_cp", "error", "x" * (MAX_NOTATKA + 1), self.dokumenty, self.zdjecia
			)

	def test_accepted_ok(self):
		wynik = waliduj_werdykt("dok:ankieta_cp", "accepted", None, self.dokumenty, self.zdjecia)
		self.assertEqual(wynik, {"status": "accepted", "note": ""})

	def test_accepted_z_notatka(self):
		wynik = waliduj_werdykt("dok:ankieta_cp", "accepted", "  ok  ", self.dokumenty, self.zdjecia)
		self.assertEqual(wynik, {"status": "accepted", "note": "ok"})

	def test_error_ok(self):
		wynik = waliduj_werdykt(
			"dok:ankieta_cp", "error", "  zły skan  ", self.dokumenty, self.zdjecia
		)
		self.assertEqual(wynik, {"status": "error", "note": "zły skan"})

	def test_waiting_ok(self):
		wynik = waliduj_werdykt("dok:ankieta_cp", "waiting", None, self.dokumenty, self.zdjecia)
		self.assertEqual(wynik, {"status": "waiting"})

	def test_waiting_ignoruje_notatke(self):
		wynik = waliduj_werdykt("dok:ankieta_cp", "waiting", "cokolwiek", self.dokumenty, self.zdjecia)
		self.assertEqual(wynik, {"status": "waiting"})

	def test_notatka_dokladnie_na_limicie(self):
		wynik = waliduj_werdykt(
			"dok:ankieta_cp", "error", "x" * MAX_NOTATKA, self.dokumenty, self.zdjecia
		)
		self.assertEqual(len(wynik["note"]), MAX_NOTATKA)

	def test_klucz_zdjec_jest_zawsze_elementem(self):
		wynik = waliduj_werdykt(KLUCZ_ZDJECIA, "accepted", None, {}, [])
		self.assertEqual(wynik, {"status": "accepted", "note": ""})


class TestResetujWerdykty(unittest.TestCase):
	def test_zmiana_jednego_slotu_resetuje_tylko_jego_klucz(self):
		stare_dok = _komplet_dokumentow()
		nowe_dok = dict(stare_dok)
		nowe_dok["dok:ankieta_cp"] = "/files/nowa-ankieta.pdf"
		weryfikacja = {
			"dok:ankieta_cp": {"status": "accepted"},
			"dok:gops_zaswiadczenie": {"status": "accepted"},
			KLUCZ_ZDJECIA: {"status": "accepted"},
		}
		nowa_mapa, komunikaty = resetuj_werdykty(stare_dok, nowe_dok, [], [], weryfikacja)
		self.assertNotIn("dok:ankieta_cp", nowa_mapa)
		self.assertIn("dok:gops_zaswiadczenie", nowa_mapa)
		self.assertIn(KLUCZ_ZDJECIA, nowa_mapa)
		self.assertEqual(komunikaty, ["Zmieniono dokument audytu: Ankieta danych Czyste Powietrze"])

	def test_dodanie_dokumentu(self):
		stare_dok = _komplet_dokumentow()
		del stare_dok["dok:zgoda_wspolwlascicieli"]
		nowe_dok = _komplet_dokumentow()
		weryfikacja = {}
		_, komunikaty = resetuj_werdykty(stare_dok, nowe_dok, [], [], weryfikacja)
		self.assertEqual(komunikaty, ["Dodano dokument audytu: Zgoda współwłaścicieli"])

	def test_usuniecie_dokumentu(self):
		stare_dok = _komplet_dokumentow()
		nowe_dok = dict(stare_dok)
		del nowe_dok["dok:zgoda_wspolwlascicieli"]
		_, komunikaty = resetuj_werdykty(stare_dok, nowe_dok, [], [], {})
		self.assertEqual(komunikaty, ["Usunięto dokument audytu: Zgoda współwłaścicieli"])

	def test_podmiana_zdjecia_resetuje_tylko_grupe(self):
		stare_zdj = _zdjecia(3)
		nowe_zdj = _zdjecia(3)
		nowe_zdj[0] = "/files/zdjecie-nowe.jpg"
		weryfikacja = {"dok:ankieta_cp": {"status": "accepted"}, KLUCZ_ZDJECIA: {"status": "accepted"}}
		nowa_mapa, komunikaty = resetuj_werdykty({}, {}, stare_zdj, nowe_zdj, weryfikacja)
		self.assertNotIn(KLUCZ_ZDJECIA, nowa_mapa)
		self.assertIn("dok:ankieta_cp", nowa_mapa)
		self.assertEqual(komunikaty, ["Zmieniono dokumentację zdjęciową audytu"])

	def test_dodanie_zdjecia_resetuje_grupe(self):
		stare_zdj = _zdjecia(2)
		nowe_zdj = _zdjecia(3)
		_, komunikaty = resetuj_werdykty({}, {}, stare_zdj, nowe_zdj, {KLUCZ_ZDJECIA: {"status": "accepted"}})
		self.assertEqual(komunikaty, ["Zmieniono dokumentację zdjęciową audytu"])

	def test_usuniecie_zdjecia_resetuje_grupe(self):
		stare_zdj = _zdjecia(3)
		nowe_zdj = _zdjecia(2)
		_, komunikaty = resetuj_werdykty({}, {}, stare_zdj, nowe_zdj, {KLUCZ_ZDJECIA: {"status": "accepted"}})
		self.assertEqual(komunikaty, ["Zmieniono dokumentację zdjęciową audytu"])

	def test_permutacja_kolejnosci_zdjec_nie_resetuje(self):
		stare_zdj = ["a.jpg", "b.jpg", "c.jpg"]
		nowe_zdj = ["c.jpg", "a.jpg", "b.jpg"]
		weryfikacja = {KLUCZ_ZDJECIA: {"status": "accepted"}}
		nowa_mapa, komunikaty = resetuj_werdykty({}, {}, stare_zdj, nowe_zdj, weryfikacja)
		self.assertIn(KLUCZ_ZDJECIA, nowa_mapa)
		self.assertEqual(komunikaty, [])

	def test_nietkniete_werdykty_przezywaja(self):
		stare_dok = _komplet_dokumentow()
		nowe_dok = dict(stare_dok)
		nowe_dok["dok:ankieta_cp"] = "/files/inna.pdf"
		weryfikacja = {
			"dok:ankieta_cp": {"status": "accepted"},
			"dok:gops_zaswiadczenie": {"status": "error", "note": "zły PIT"},
			"dok:umowa_obsluga_dotacji": {"status": "accepted"},
			KLUCZ_ZDJECIA: {"status": "accepted"},
		}
		nowa_mapa, _ = resetuj_werdykty(stare_dok, nowe_dok, ["a.jpg"], ["a.jpg"], weryfikacja)
		self.assertEqual(nowa_mapa["dok:gops_zaswiadczenie"], {"status": "error", "note": "zły PIT"})
		self.assertEqual(nowa_mapa["dok:umowa_obsluga_dotacji"], {"status": "accepted"})
		self.assertEqual(nowa_mapa[KLUCZ_ZDJECIA], {"status": "accepted"})

	def test_brak_zmian_zero_komunikatow(self):
		stare_dok = _komplet_dokumentow()
		nowe_dok = dict(stare_dok)
		zdjecia = _zdjecia(2)
		weryfikacja = {"dok:ankieta_cp": {"status": "accepted"}}
		nowa_mapa, komunikaty = resetuj_werdykty(stare_dok, nowe_dok, zdjecia, list(zdjecia), weryfikacja)
		self.assertEqual(komunikaty, [])
		self.assertEqual(nowa_mapa, weryfikacja)

	def test_wejscia_nie_sa_mutowane(self):
		stare_dok = _komplet_dokumentow()
		nowe_dok = dict(stare_dok)
		nowe_dok["dok:ankieta_cp"] = "/files/inna.pdf"
		stare_dok_kopia = dict(stare_dok)
		nowe_dok_kopia = dict(nowe_dok)
		stare_zdj = _zdjecia(2)
		nowe_zdj = _zdjecia(3)
		stare_zdj_kopia = list(stare_zdj)
		nowe_zdj_kopia = list(nowe_zdj)
		weryfikacja = {"dok:ankieta_cp": {"status": "accepted"}, KLUCZ_ZDJECIA: {"status": "accepted"}}
		weryfikacja_kopia = {k: dict(v) for k, v in weryfikacja.items()}

		resetuj_werdykty(stare_dok, nowe_dok, stare_zdj, nowe_zdj, weryfikacja)

		self.assertEqual(stare_dok, stare_dok_kopia)
		self.assertEqual(nowe_dok, nowe_dok_kopia)
		self.assertEqual(stare_zdj, stare_zdj_kopia)
		self.assertEqual(nowe_zdj, nowe_zdj_kopia)
		self.assertEqual(weryfikacja, weryfikacja_kopia)

	def test_zwrocona_mapa_jest_nowym_obiektem(self):
		weryfikacja = {"dok:ankieta_cp": {"status": "accepted"}}
		nowa_mapa, _ = resetuj_werdykty({}, {}, [], [], weryfikacja)
		self.assertIsNot(nowa_mapa, weryfikacja)


if __name__ == "__main__":
	unittest.main()
