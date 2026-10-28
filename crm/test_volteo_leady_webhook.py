# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import copy
import unittest
from datetime import datetime

from crm.volteo_leady_import import SEPARATOR_UWAG
from crm.volteo_leady_webhook import (
	IMIE_ZASTEPCZE,
	LIMIT_ZADAN_NA_MINUTE,
	LadunekOdrzucony,
	klucz_limitu,
	limit_przekroczony,
	normalizuj_date_zgloszenia,
	normalizuj_posiada_pv,
	normalizuj_produkt_reklamy,
	normalizuj_system_rozliczen,
	splaszcz_odpowiedzi,
	zbuduj_leada_z_webhooka,
)

DZIS = "2026-10-22"


def ladunek(**nadpisz):
	baza = {
		"imie_nazwisko": "jan KOWALSKI",
		"telefon": "604 932 720",
		"miasto": "  Poznań ",
		"posiada_pv": "Tak",
		"system_rozliczen": "Net-billing",
		"produkt": "PV + magazyn",
		"data_zgloszenia": "2026-10-20T10:11:12+0000",
		"facebook_lead_id": "123456789",
		"facebook_form_id": "987",
		"formularz": "Formularz PV",
	}
	baza.update(nadpisz)
	return baza


def uwagi(wynik):
	return wynik["custom_uwagi_import"].split(SEPARATOR_UWAG)


class TestPosiadaPv(unittest.TestCase):
	def test_tak_warianty(self):
		for t in ("tak", "Tak", " TAK ", "yes", "True", "1"):
			self.assertEqual(normalizuj_posiada_pv(t), "PV", t)

	def test_nie_warianty(self):
		for t in ("nie", "Nie", "no", "FALSE", "0"):
			self.assertEqual(normalizuj_posiada_pv(t), "", t)

	def test_puste(self):
		self.assertEqual(normalizuj_posiada_pv(""), "")
		self.assertEqual(normalizuj_posiada_pv(None), "")

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_posiada_pv("moze"))

	def test_liczba(self):
		self.assertEqual(normalizuj_posiada_pv(1), "PV")

	def test_opisowe_czytelne_i_slugi(self):
		przypadki = {
			"Mam Fotowoltaik\u0119 bez magazynu energii": "PV",
			"mam_fotowoltaik\u0119_bez_magazynu_energii": "PV",
			"Mam Fotowoltaik\u0119 z magazynem energii": "PV+ME",
			"mam_fotowoltaik\u0119_z_magazynem_energii": "PV+ME",
			"mam_fotowoltaike_z_magazynem_energii": "PV+ME",
			"Nie mam jeszcze Fotowoltaiki": "",
			"nie_mam_jeszcze_fotowoltaiki": "",
		}
		for tekst, oczekiwane in przypadki.items():
			self.assertEqual(normalizuj_posiada_pv(tekst), oczekiwane, tekst)

	def test_opisowe_nierozpoznane(self):
		self.assertIsNone(normalizuj_posiada_pv("mam_pompe_ciepla"))
		self.assertIsNone(normalizuj_posiada_pv("fotowoltaika z magazynem"))


class TestSystemRozliczen(unittest.TestCase):
	def test_nowe(self):
		for t in ("Net-billing", "net billing", "NETBILLING", "nowe zasady", "Nowy system"):
			self.assertEqual(normalizuj_system_rozliczen(t), "Nowe zasady", t)

	def test_stare(self):
		for t in ("net-metering", "Net Metering", "opust", "stare zasady", "stary"):
			self.assertEqual(normalizuj_system_rozliczen(t), "Stare zasady", t)

	def test_slugi_meta(self):
		self.assertEqual(normalizuj_system_rozliczen("nowe_zasady_(net-billing)"), "Nowe zasady")
		self.assertEqual(normalizuj_system_rozliczen("Nowe zasady (net-billing)"), "Nowe zasady")
		self.assertEqual(normalizuj_system_rozliczen("stare_zasady"), "Stare zasady")

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_system_rozliczen("nie wiem"))

	def test_puste(self):
		self.assertIsNone(normalizuj_system_rozliczen(""))
		self.assertIsNone(normalizuj_system_rozliczen(None))

	def test_dwuznaczne(self):
		self.assertIsNone(normalizuj_system_rozliczen("net-billing albo opust"))


class TestProduktReklamy(unittest.TestCase):
	def test_pvme(self):
		for t in ("PV MAG", "pv+mag", "PV + magazyn", "pvme", "PV i magazyn energii", "Fotowoltaika z magazynem"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PVME", t)

	def test_me(self):
		for t in ("mag", "Magazyn", "magazyn energii", "ME"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "ME", t)

	def test_pv(self):
		for t in ("PV", "pv", "Fotowoltaika"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PV", t)

	def test_pc(self):
		for t in ("pompa ciepła", "Pompa ciepla", "PC"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "PC", t)

	def test_cp(self):
		for t in ("czyste powietrze", "Czyste Powietrze", "cp"):
			self.assertEqual(normalizuj_produkt_reklamy(t), "CP", t)

	def test_nierozpoznane(self):
		self.assertIsNone(normalizuj_produkt_reklamy("klimatyzacja"))
		self.assertIsNone(normalizuj_produkt_reklamy("PV tanio"))

	def test_mieszanka_rodzin(self):
		self.assertIsNone(normalizuj_produkt_reklamy("PV i pompa ciepła"))

	def test_puste(self):
		self.assertIsNone(normalizuj_produkt_reklamy(""))
		self.assertIsNone(normalizuj_produkt_reklamy(None))


class TestDataZgloszenia(unittest.TestCase):
	def test_iso_data(self):
		self.assertEqual(normalizuj_date_zgloszenia("2026-10-22"), "2026-10-22")

	def test_iso_datetime_warianty(self):
		for t in ("2026-10-22T10:11:12+0000", "2026-10-22T10:11:12Z", "2026-10-22T10:11:12+02:00"):
			self.assertEqual(normalizuj_date_zgloszenia(t), "2026-10-22", t)

	def test_ze_spacja(self):
		self.assertEqual(normalizuj_date_zgloszenia("2026-10-22 10:11:12"), "2026-10-22")

	def test_nieparsowalne(self):
		for t in ("22.10.2026", "jutro", "2026-13-40", "2026-10-22x"):
			self.assertIsNone(normalizuj_date_zgloszenia(t), t)

	def test_puste(self):
		self.assertIsNone(normalizuj_date_zgloszenia(""))
		self.assertIsNone(normalizuj_date_zgloszenia(None))


class TestSplaszczOdpowiedzi(unittest.TestCase):
	def test_slownik(self):
		self.assertEqual(
			splaszcz_odpowiedzi({"Rachunek": "400 zł", "Dom": "tak"}),
			[("Rachunek", "400 zł"), ("Dom", "tak")],
		)

	def test_lista_facebookowa(self):
		wej = [{"name": "Rachunek", "values": ["400 zł"]}, {"name": "Dom", "values": ["a", "b"]}]
		self.assertEqual(splaszcz_odpowiedzi(wej), [("Rachunek", "400 zł"), ("Dom", "a, b")])

	def test_lista_z_value(self):
		self.assertEqual(splaszcz_odpowiedzi([{"name": "X", "value": "1"}]), [("X", "1")])

	def test_puste_odpowiedzi_pominiete(self):
		self.assertEqual(splaszcz_odpowiedzi({"A": "", "B": None, "C": "x"}), [("C", "x")])

	def test_inne_ksztalty(self):
		self.assertEqual(splaszcz_odpowiedzi("tekst"), [])
		self.assertEqual(splaszcz_odpowiedzi(None), [])
		self.assertEqual(splaszcz_odpowiedzi(["a", 1]), [])

	def test_element_bez_nazwy(self):
		self.assertEqual(splaszcz_odpowiedzi([{"values": ["x"]}]), [])


class TestPelnyLadunek(unittest.TestCase):
	def test_dokladny_slownik(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		self.assertEqual(
			wynik,
			{
				"first_name": "Jan",
				"last_name": "Kowalski",
				"mobile_no": "+48604932720",
				"source": "Facebook",
				"custom_import_source": "FB",
				"custom_import_date": "2026-10-20",
				"facebook_lead_id": "123456789",
				"facebook_form_id": "987",
				"custom_install_city": "Poznań",
				"custom_posiadane_produkty": "PV",
				"custom_zasady_dotacji": "Nowe zasady",
				"custom_produkt_procesu": "PVME",
				"custom_uwagi_import": SEPARATOR_UWAG.join(
					["Zrodlo: Facebook Lead Ads", "Formularz: Formularz PV"]
				),
			},
		)

	def test_nie_mutuje_wejscia(self):
		wej = ladunek(odpowiedzi={"A": "b"})
		kopia = copy.deepcopy(wej)
		zbuduj_leada_z_webhooka(wej, DZIS)
		self.assertEqual(wej, kopia)

	def test_status_i_wlasciciel_nieustawiane(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		for klucz in ("status", "lead_owner", "custom_cc", "doctype"):
			self.assertNotIn(klucz, wynik)

	def test_klucze_bez_wielkosci_liter_i_ze_spacjami(self):
		wynik = zbuduj_leada_z_webhooka({" Telefon ": "604932720", "FACEBOOK_LEAD_ID": "5"}, DZIS)
		self.assertEqual(wynik["mobile_no"], "+48604932720")
		self.assertEqual(wynik["facebook_lead_id"], "5")

	def test_nieznane_klucze_ignorowane(self):
		wynik = zbuduj_leada_z_webhooka(ladunek(cokolwiek="x", status="Won", lead_owner="a@b.pl"), DZIS)
		self.assertNotIn("cokolwiek", wynik)
		self.assertNotIn("status", wynik)
		self.assertNotIn("lead_owner", wynik)

	def test_minimalny_ladunek(self):
		wynik = zbuduj_leada_z_webhooka({"telefon": "604932720", "facebook_lead_id": "1"}, DZIS)
		self.assertEqual(wynik["first_name"], IMIE_ZASTEPCZE)
		self.assertNotIn("last_name", wynik)
		self.assertNotIn("custom_install_city", wynik)
		self.assertNotIn("custom_posiadane_produkty", wynik)
		self.assertNotIn("custom_produkt_procesu", wynik)
		self.assertEqual(wynik["custom_import_date"], DZIS)


class TestOdrzucenia(unittest.TestCase):
	def test_brak_telefonu(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(telefon=""), DZIS)
		self.assertIn("telefon", ctx.exception.powod.lower())

	def test_telefon_none(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka(ladunek(telefon=None), DZIS)

	def test_zly_telefon(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(telefon="12345"), DZIS)
		self.assertIn("12345", ctx.exception.powod)

	def test_brak_klucza_telefon(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka({"facebook_lead_id": "1"}, DZIS)

	def test_brak_id_leada(self):
		with self.assertRaises(LadunekOdrzucony) as ctx:
			zbuduj_leada_z_webhooka(ladunek(facebook_lead_id=""), DZIS)
		self.assertIn("facebook_lead_id", ctx.exception.powod)

	def test_brak_klucza_id(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka({"telefon": "604932720"}, DZIS)

	def test_ladunek_nie_slownik(self):
		with self.assertRaises(LadunekOdrzucony):
			zbuduj_leada_z_webhooka(["a"], DZIS)

	def test_jest_value_error(self):
		self.assertTrue(issubclass(LadunekOdrzucony, ValueError))


class TestImieNazwisko(unittest.TestCase):
	def test_dwa_slowa(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="anna NOWAK"), DZIS)
		self.assertEqual((w["first_name"], w["last_name"]), ("Anna", "Nowak"))

	def test_jedno_slowo(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="anna"), DZIS)
		self.assertEqual(w["first_name"], "Anna")
		self.assertNotIn("last_name", w)

	def test_trzy_slowa(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="Jan Maria Kowalski"), DZIS)
		self.assertEqual((w["first_name"], w["last_name"]), ("Jan", "Maria Kowalski"))

	def test_firma_bez_zmian(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="Jan Kowalski Usługi Handlowe"), DZIS)
		self.assertEqual(w["first_name"], "Jan Kowalski Usługi Handlowe")
		self.assertNotIn("last_name", w)

	def test_puste_imie(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko=""), DZIS)
		self.assertEqual(w["first_name"], IMIE_ZASTEPCZE)

	def test_nazwisko_z_myslnikiem(self):
		w = zbuduj_leada_z_webhooka(ladunek(imie_nazwisko="ewa kowalska-nowak"), DZIS)
		self.assertEqual(w["last_name"], "Kowalska-Nowak")


class TestOdpowiedziOpisowe(unittest.TestCase):
	def test_pv_me_ze_starymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(
				posiada_pv="mam_fotowoltaik\u0119_z_magazynem_energii",
				system_rozliczen="stare_zasady",
			),
			DZIS,
		)
		self.assertEqual(w["custom_posiadane_produkty"], "PV+ME")
		self.assertEqual(w["custom_zasady_dotacji"], "Stare zasady")
		self.assertNotIn("nierozpoznane", w.get("custom_uwagi_import", ""))

	def test_pv_bez_magazynu_z_nowymi_zasadami(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(
				posiada_pv="Mam Fotowoltaik\u0119 bez magazynu energii",
				system_rozliczen="nowe_zasady_(net-billing)",
			),
			DZIS,
		)
		self.assertEqual(w["custom_posiadane_produkty"], "PV")
		self.assertEqual(w["custom_zasady_dotacji"], "Nowe zasady")

	def test_nie_mam_zasady_do_uwag(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(posiada_pv="nie_mam_jeszcze_fotowoltaiki", system_rozliczen="stare_zasady"),
			DZIS,
		)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("System rozliczen: stare_zasady", uwagi(w))
		self.assertNotIn("nierozpoznane", w["custom_uwagi_import"])


class TestPolaLadunku(unittest.TestCase):
	def test_lista_zamiast_stringa(self):
		w = zbuduj_leada_z_webhooka(ladunek(telefon=["604932720"], miasto=["Kraków"]), DZIS)
		self.assertEqual(w["mobile_no"], "+48604932720")
		self.assertEqual(w["custom_install_city"], "Kraków")

	def test_liczba_jako_id_i_telefon(self):
		w = zbuduj_leada_z_webhooka(ladunek(telefon=604932720, facebook_lead_id=123456789.0), DZIS)
		self.assertEqual(w["mobile_no"], "+48604932720")
		self.assertEqual(w["facebook_lead_id"], "123456789")

	def test_system_bez_pv_idzie_do_uwag(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="Nie", system_rozliczen="net-billing"), DZIS)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertIn("System rozliczen: net-billing", uwagi(w))

	def test_system_nierozpoznany_z_pv(self):
		w = zbuduj_leada_z_webhooka(ladunek(system_rozliczen="nie wiem"), DZIS)
		self.assertNotIn("custom_zasady_dotacji", w)
		self.assertIn("System rozliczen (nierozpoznane): nie wiem", uwagi(w))

	def test_posiada_pv_nierozpoznane(self):
		w = zbuduj_leada_z_webhooka(ladunek(posiada_pv="moze", system_rozliczen=""), DZIS)
		self.assertNotIn("custom_posiadane_produkty", w)
		self.assertIn("Posiada PV (nierozpoznane): moze", uwagi(w))

	def test_produkt_nierozpoznany(self):
		w = zbuduj_leada_z_webhooka(ladunek(produkt="klimatyzacja"), DZIS)
		self.assertNotIn("custom_produkt_procesu", w)
		self.assertIn("Produkt (nierozpoznany): klimatyzacja", uwagi(w))

	def test_pusta_data_to_dzisiaj(self):
		w = zbuduj_leada_z_webhooka(ladunek(data_zgloszenia=""), DZIS)
		self.assertEqual(w["custom_import_date"], DZIS)
		self.assertTrue(any(l.startswith("Data zgloszenia") for l in uwagi(w)))

	def test_zla_data_to_dzisiaj_z_surowa_w_uwagach(self):
		w = zbuduj_leada_z_webhooka(ladunek(data_zgloszenia="wczoraj"), DZIS)
		self.assertEqual(w["custom_import_date"], DZIS)
		self.assertIn("Data zgloszenia (nierozpoznana): wczoraj", uwagi(w))

	def test_kampania_i_formularz_w_kolejnosci(self):
		w = zbuduj_leada_z_webhooka(ladunek(kampania="Jesien 2026"), DZIS)
		self.assertEqual(
			uwagi(w)[:3], ["Zrodlo: Facebook Lead Ads", "Formularz: Formularz PV", "Kampania: Jesien 2026"]
		)

	def test_odpowiedzi_slownik_na_koncu(self):
		w = zbuduj_leada_z_webhooka(ladunek(produkt="x y", odpowiedzi={"Rachunek": "400 zł"}), DZIS)
		linie = uwagi(w)
		self.assertEqual(linie[-1], "Rachunek: 400 zł")
		self.assertLess(linie.index("Produkt (nierozpoznany): x y"), len(linie) - 1)

	def test_odpowiedzi_lista_facebookowa(self):
		w = zbuduj_leada_z_webhooka(
			ladunek(odpowiedzi=[{"name": "Dach", "values": ["skośny"]}]), DZIS
		)
		self.assertIn("Dach: skośny", uwagi(w))

	def test_pusta_lista_linii_nie_istnieje(self):
		# zawsze jest linia zrodla, wiec pole Uwagi nigdy nie jest puste
		w = zbuduj_leada_z_webhooka({"telefon": "604932720", "facebook_lead_id": "1", "data_zgloszenia": DZIS}, DZIS)
		self.assertEqual(w["custom_uwagi_import"], "Zrodlo: Facebook Lead Ads")


class TestKodPocztowy(unittest.TestCase):
	def test_poprawny(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="61-001"), DZIS)
		self.assertEqual(w["custom_install_postal_code"], "61-001")

	def test_niepoprawny(self):
		w = zbuduj_leada_z_webhooka(ladunek(kod_pocztowy="61001"), DZIS)
		self.assertNotIn("custom_install_postal_code", w)
		self.assertIn("Kod pocztowy (nierozpoznany): 61001", uwagi(w))

	def test_brak(self):
		w = zbuduj_leada_z_webhooka(ladunek(), DZIS)
		self.assertNotIn("custom_install_postal_code", w)


class TestKluczLimitu(unittest.TestCase):
	def test_format(self):
		k = klucz_limitu("make@x.pl", datetime(2026, 10, 22, 14, 5, 59))
		self.assertEqual(k, "volteo:webhook_leady:limit:make@x.pl:202610221405")

	def test_ta_sama_minuta_ten_sam_klucz(self):
		a = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 0))
		b = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 59))
		self.assertEqual(a, b)

	def test_granica_minuty_inny_klucz(self):
		a = klucz_limitu("u", datetime(2026, 10, 22, 14, 5, 30))
		b = klucz_limitu("u", datetime(2026, 10, 22, 14, 6, 29))
		self.assertNotEqual(a, b)

	def test_uzytkownik_w_kluczu(self):
		t = datetime(2026, 10, 22, 14, 5)
		self.assertNotEqual(klucz_limitu("a", t), klucz_limitu("b", t))


class TestLimitPrzekroczony(unittest.TestCase):
	def test_stala(self):
		self.assertEqual(LIMIT_ZADAN_NA_MINUTE, 3)

	def test_zero_i_trzy_przechodza(self):
		self.assertFalse(limit_przekroczony(0))
		self.assertFalse(limit_przekroczony(3))

	def test_czwarte_odrzucone(self):
		self.assertTrue(limit_przekroczony(4))

	def test_wlasny_limit(self):
		self.assertFalse(limit_przekroczony(10, limit=10))
		self.assertTrue(limit_przekroczony(11, limit=10))


if __name__ == "__main__":
	unittest.main()
