# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

import re
import sys
import unittest
from datetime import date, datetime, timedelta
from typing import ClassVar

from crm.volteo_sms import dlugosc_gsm7, liczba_czesci_sms
from crm.volteo_sms_handlowiec import (
	CISZA_DO,
	CISZA_OD,
	DANE_PRZYKLADOWE_HANDLOWIEC,
	KLUCZ_ODROCZONYCH,
	LIMIT_DZIENNY_DOMYSLNY,
	OPISY_WYNIKU,
	PLACEHOLDERY_HANDLOWIEC,
	POLA_SZABLONOW,
	PREFIKS_KLUCZA,
	PROG_MASOWY,
	STAN_PUSTY,
	TRESC_NOWE_DOMYSLNA,
	TRESC_ODWOLANIE_DOMYSLNA,
	TRESC_ZMIANA_DOMYSLNA,
	TRESCI_DOMYSLNE,
	TYP_NOWE,
	TYP_ODWOLANIE,
	TYP_ZMIANA,
	TYPY,
	WYNIK_BLAD,
	WYNIK_BRAK_NUMERU,
	WYNIK_LIMIT,
	WYNIK_ODLOZONY,
	WYNIK_TEST,
	WYNIK_WLASNA_ZMIANA,
	WYNIK_WYSLANY,
	Zdarzenie,
	czy_cisza_nocna,
	czy_flaga,
	czy_kandydat,
	czy_masowa,
	czy_w_przyszlosci,
	dane_do_szablonu,
	formatuj_termin_sms,
	klucz_alertu,
	klucz_licznika_dnia,
	klucz_rezerwacji,
	klucz_stanu,
	limit_dzienny,
	najblizszy_start_wysylki,
	normalizuj_stan,
	odkoduj_odroczenie,
	odkoduj_stan,
	opis_sladu,
	szablon_dla,
	ustal_zdarzenia,
	waliduj_limit_handlowiec,
	waliduj_tresc_handlowiec,
	zakoduj_odroczenie,
	zakoduj_stan,
	zbuduj_tresc_handlowiec,
)

H = "h.handlowiec@proenergy.pro"
A = "a.poprzedni@proenergy.pro"
TERAZ = datetime(2026, 11, 5, 12, 0, 0)
T1 = "2026-11-06 10:00"  # piątek
T2 = "2026-11-07 14:30"  # sobota
PRZESZLY = "2026-11-04 09:00"


class TestModul(unittest.TestCase):
	def test_bez_frappe(self) -> None:
		self.assertNotIn("frappe", sys.modules)


class TestNormalizujStan(unittest.TestCase):
	def test_termin_do_minuty(self) -> None:
		self.assertEqual(normalizuj_stan(H, "2026-11-06 10:00:59"), (H, "2026-11-06 10:00"))

	def test_datetime(self) -> None:
		self.assertEqual(normalizuj_stan(H, datetime(2026, 11, 6, 10, 0, 7)), (H, "2026-11-06 10:00"))

	def test_separator_t_i_bez_sekund(self) -> None:
		self.assertEqual(normalizuj_stan(H, "2026-11-06T10:00"), (H, "2026-11-06 10:00"))

	def test_none_na_pusty(self) -> None:
		self.assertEqual(normalizuj_stan(None, None), ("", ""))

	def test_przyciecie_wlasciciela(self) -> None:
		self.assertEqual(normalizuj_stan(f"  {H} ", ""), (H, ""))

	def test_nieparsowalny_termin_pusty(self) -> None:
		self.assertEqual(normalizuj_stan(H, "jutro"), (H, ""))
		self.assertEqual(normalizuj_stan(H, 12345), (H, ""))
		self.assertEqual(normalizuj_stan(H, date(2026, 11, 6)), (H, ""))


class TestCzyKandydat(unittest.TestCase):
	def test_bez_zmiany(self) -> None:
		self.assertFalse(czy_kandydat((H, T1), (H, T1)))

	def test_tylko_sekundy(self) -> None:
		self.assertFalse(czy_kandydat((H, "2026-11-06 10:00:00"), (H, "2026-11-06 10:00:30")))

	def test_datetime_i_tekst_ta_sama_chwila(self) -> None:
		self.assertFalse(czy_kandydat((H, datetime(2026, 11, 6, 10, 0)), (H, "2026-11-06 10:00:00")))

	def test_zmiana_terminu(self) -> None:
		self.assertTrue(czy_kandydat((H, T1), (H, T2)))

	def test_zmiana_wlasciciela(self) -> None:
		self.assertTrue(czy_kandydat((A, T1), (H, T1)))

	def test_insert_z_wlascicielem_i_terminem(self) -> None:
		self.assertTrue(czy_kandydat(STAN_PUSTY, (H, T1)))

	def test_insert_bez_terminu(self) -> None:
		self.assertFalse(czy_kandydat(STAN_PUSTY, (H, "")))

	def test_puste_bez_spotkania_po_obu_stronach(self) -> None:
		self.assertFalse(czy_kandydat(("", T1), ("", T2)))
		self.assertFalse(czy_kandydat((A, ""), (H, "")))
		self.assertFalse(czy_kandydat(STAN_PUSTY, STAN_PUSTY))

	def test_wyczyszczenie(self) -> None:
		self.assertTrue(czy_kandydat((H, T1), (H, "")))
		self.assertTrue(czy_kandydat((H, T1), ("", T1)))


class TestUstalZdarzenia(unittest.TestCase):
	def _z(self, baza, po, odwolania: bool = True, teraz: datetime = TERAZ) -> list[Zdarzenie]:
		return ustal_zdarzenia(baza, po, teraz=teraz, odwolania=odwolania)

	def test_1_nowe_spotkanie(self) -> None:
		self.assertEqual(self._z(STAN_PUSTY, (H, T1)), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_1_nowe_gdy_byl_wlasciciel_bez_terminu(self) -> None:
		self.assertEqual(self._z((H, ""), (H, T1)), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_1_nowe_z_innego_wlasciciela_bez_terminu(self) -> None:
		self.assertEqual(self._z((A, ""), (H, T1)), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_2_przekazanie_odwolanie_przed_nowym(self) -> None:
		self.assertEqual(
			self._z((A, T1), (H, T1)),
			[Zdarzenie(TYP_ODWOLANIE, A, T1, T1), Zdarzenie(TYP_NOWE, H, T1, "")],
		)

	def test_2_przekazanie_z_pustego(self) -> None:
		self.assertEqual(self._z(("", T1), (H, T1)), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_2_przekazanie_ze_zmiana_terminu(self) -> None:
		self.assertEqual(
			self._z((A, T1), (H, T2)),
			[Zdarzenie(TYP_ODWOLANIE, A, T1, T1), Zdarzenie(TYP_NOWE, H, T2, "")],
		)

	def test_2_odwolania_wylaczone(self) -> None:
		self.assertEqual(self._z((A, T1), (H, T1), odwolania=False), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_2_bazowy_termin_w_przeszlosci_bez_odwolania(self) -> None:
		self.assertEqual(self._z((A, PRZESZLY), (H, T1)), [Zdarzenie(TYP_NOWE, H, T1, "")])

	def test_3_zmiana_terminu(self) -> None:
		self.assertEqual(self._z((H, T1), (H, T2)), [Zdarzenie(TYP_ZMIANA, H, T2, T1)])

	def test_3_zmiana_z_przeszlego_na_przyszly(self) -> None:
		self.assertEqual(self._z((H, PRZESZLY), (H, T2)), [Zdarzenie(TYP_ZMIANA, H, T2, PRZESZLY)])

	def test_3_zmiana_bez_odwolan_tez_idzie(self) -> None:
		self.assertEqual(self._z((H, T1), (H, T2), odwolania=False), [Zdarzenie(TYP_ZMIANA, H, T2, T1)])

	def test_4_wyczyszczenie_terminu(self) -> None:
		self.assertEqual(self._z((H, T1), (H, "")), [Zdarzenie(TYP_ODWOLANIE, H, T1, T1)])

	def test_4_wyczyszczenie_odwolania_wylaczone(self) -> None:
		self.assertEqual(self._z((H, T1), (H, ""), odwolania=False), [])

	def test_4_wyczyszczenie_przeszlego_terminu(self) -> None:
		self.assertEqual(self._z((H, PRZESZLY), (H, "")), [])

	def test_4_wyczyszczenie_z_przekazaniem(self) -> None:
		self.assertEqual(self._z((A, T1), (H, "")), [Zdarzenie(TYP_ODWOLANIE, A, T1, T1)])

	def test_5_zdjecie_wlasciciela(self) -> None:
		self.assertEqual(self._z((H, T1), ("", T1)), [Zdarzenie(TYP_ODWOLANIE, H, T1, T1)])

	def test_5_zdjecie_wlasciciela_odwolania_wylaczone(self) -> None:
		self.assertEqual(self._z((H, T1), ("", T1), odwolania=False), [])

	def test_7_nowy_termin_w_przeszlosci(self) -> None:
		self.assertEqual(self._z(STAN_PUSTY, (H, PRZESZLY)), [])
		self.assertEqual(self._z((H, T1), (H, PRZESZLY)), [])

	def test_7_przekazanie_na_termin_w_przeszlosci_odwoluje_przyszly_poprzedniego(self) -> None:
		self.assertEqual(self._z((A, T1), (H, PRZESZLY)), [Zdarzenie(TYP_ODWOLANIE, A, T1, T1)])

	def test_bez_zmiany(self) -> None:
		self.assertEqual(self._z((H, T1), (H, "2026-11-06 10:00:45")), [])

	def test_termin_za_30_minut(self) -> None:
		za_30 = (TERAZ + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
		self.assertEqual(self._z(STAN_PUSTY, (H, za_30)), [Zdarzenie(TYP_NOWE, H, za_30, "")])

	def test_termin_teraz_to_nie_przyszlosc(self) -> None:
		self.assertEqual(self._z(STAN_PUSTY, (H, "2026-11-05 12:00")), [])

	def test_wejscie_nienormalizowane(self) -> None:
		self.assertEqual(
			self._z((None, None), (H, datetime(2026, 11, 6, 10, 0, 33))),
			[Zdarzenie(TYP_NOWE, H, T1, "")],
		)

	def test_czy_w_przyszlosci(self) -> None:
		self.assertTrue(czy_w_przyszlosci(T1, TERAZ))
		self.assertFalse(czy_w_przyszlosci(PRZESZLY, TERAZ))
		self.assertFalse(czy_w_przyszlosci("", TERAZ))


class TestCzyMasowa(unittest.TestCase):
	def test_prog_domyslny(self) -> None:
		self.assertEqual(PROG_MASOWY, 5)
		self.assertEqual([czy_masowa(n) for n in range(1, 8)], [False] * 5 + [True] * 2)

	def test_prog_wlasny(self) -> None:
		self.assertFalse(czy_masowa(2, prog=2))
		self.assertTrue(czy_masowa(3, prog=2))


class TestDaneDoSzablonu(unittest.TestCase):
	LEAD: ClassVar[dict] = {
		"lead_name": "Jan Kowalski",
		"mobile_no": "+48 600 100 200",
		"custom_install_address": "Parkowa",
		"custom_nr_domu": "5",
		"custom_install_postal_code": "64-100",
		"custom_install_city": "Leszno",
		"custom_termin_spotkania": "2026-11-07 14:30:00",
		"custom_uwagi_import": "Umówiła TAJNA_UWAGA_CC",
		"custom_cc": "cc.tajna@proenergy.pro",
		"owner": "cc.tajna@proenergy.pro",
		"modified_by": "Kasia Tajna",
	}

	def test_nowe(self) -> None:
		dane = dane_do_szablonu(self.LEAD, Zdarzenie(TYP_NOWE, H, T2, ""))
		self.assertEqual(
			dane,
			{
				"termin": "sob. 07.11 14:30",
				"stary_termin": "brak",
				"data": "sob. 07.11",
				"godzina": "14:30",
				"klient": "Jan Kowalski",
				"adres": "Parkowa 5, 64-100 Leszno",
				"miejscowosc": "Leszno",
			},
		)
		self.assertEqual(set(dane), set(PLACEHOLDERY_HANDLOWIEC))

	def test_zmiana_stary_termin(self) -> None:
		dane = dane_do_szablonu(self.LEAD, Zdarzenie(TYP_ZMIANA, H, T2, T1))
		self.assertEqual(dane["stary_termin"], "pt. 06.11 10:00")
		self.assertEqual(dane["termin"], "sob. 07.11 14:30")

	def test_odwolanie_termin_odwolany(self) -> None:
		dane = dane_do_szablonu(self.LEAD, Zdarzenie(TYP_ODWOLANIE, A, T1, T1))
		self.assertEqual(dane["stary_termin"], "pt. 06.11 10:00")
		self.assertEqual(dane["termin"], "pt. 06.11 10:00")

	def test_brak_danych_cc_i_telefonu_klienta_w_wyniku(self) -> None:
		for typ in TYPY:
			dane = dane_do_szablonu(self.LEAD, Zdarzenie(typ, H, T2, T1))
			wartosci = " ".join(dane.values())
			with self.subTest(typ=typ):
				self.assertNotIn("tajna", wartosci.lower())
				self.assertNotIn("TAJNA_UWAGA_CC", wartosci)
				self.assertNotIn("Umówiła", wartosci)
				self.assertNotIn("600", wartosci)
				self.assertNotIn("telefon", dane)
				self.assertNotIn("link", dane)

	def test_puste_wartosci(self) -> None:
		dane = dane_do_szablonu({}, Zdarzenie(TYP_NOWE, H, T2, ""))
		self.assertEqual(dane["klient"], "bez nazwy")
		self.assertEqual(dane["adres"], "brak adresu")
		self.assertEqual(dane["miejscowosc"], "brak")
		self.assertEqual(dane["stary_termin"], "brak")

	def test_wartosci_nietekstowe(self) -> None:
		dane = dane_do_szablonu(
			{**self.LEAD, "custom_nr_domu": 5, "lead_name": None}, Zdarzenie(TYP_NOWE, H, T2, "")
		)
		self.assertEqual(dane["adres"], "Parkowa 5, 64-100 Leszno")
		self.assertEqual(dane["klient"], "bez nazwy")

	def test_nie_mutuje_wejscia(self) -> None:
		kopia = dict(self.LEAD)
		dane_do_szablonu(self.LEAD, Zdarzenie(TYP_NOWE, H, T2, ""))
		self.assertEqual(self.LEAD, kopia)

	def test_formatuj_termin_sms(self) -> None:
		self.assertEqual(formatuj_termin_sms("2026-11-06 10:00:59"), "pt. 06.11 10:00")
		self.assertEqual(formatuj_termin_sms(""), "")
		self.assertEqual(formatuj_termin_sms(None), "")


class TestZbudujTresc(unittest.TestCase):
	def test_domyslne_jedna_czesc_z_danymi_przykladowymi(self) -> None:
		for typ in TYPY:
			tresc, ostrzezenie = zbuduj_tresc_handlowiec(TRESCI_DOMYSLNE[typ], DANE_PRZYKLADOWE_HANDLOWIEC)
			with self.subTest(typ=typ, dlugosc=dlugosc_gsm7(tresc)):
				self.assertEqual(liczba_czesci_sms(tresc), 1)
				self.assertIsNone(ostrzezenie)
				self.assertNotIn("{", tresc)

	def test_tresci_dokladnie(self) -> None:
		oczekiwane = {
			TYP_NOWE: "Nowe spotkanie pt. 07.11 14:30: Jan Kowalski, Parkowa 5, 64-100 Leszno. Szczegoly w CRM.",
			TYP_ZMIANA: "Zmiana terminu: Jan Kowalski, Parkowa 5, 64-100 Leszno, teraz pt. 07.11 14:30 "
			"(bylo czw. 06.11 10:00). Szczegoly w CRM.",
			TYP_ODWOLANIE: "Spotkanie czw. 06.11 10:00: Jan Kowalski, Leszno, odwolane albo przekazane innej "
			"osobie. Nie jedz.",
		}
		for typ, tekst in oczekiwane.items():
			with self.subTest(typ=typ):
				tresc, _ = zbuduj_tresc_handlowiec(TRESCI_DOMYSLNE[typ], DANE_PRZYKLADOWE_HANDLOWIEC)
				self.assertEqual(tresc, tekst)
				self.assertTrue(tresc.isascii())

	def test_budzet_jednej_czesci_nowe(self) -> None:
		# Decyzje Jana pkt 7: budżet klient + adres w jednej części NOWE to ok. 107 znaków.
		def _nowe(dlugosc_klient_adres: int) -> str:
			dane = {**DANE_PRZYKLADOWE_HANDLOWIEC, "klient": "K", "adres": "a" * (dlugosc_klient_adres - 1)}
			return zbuduj_tresc_handlowiec(TRESC_NOWE_DOMYSLNA, dane)[0]

		self.assertEqual(liczba_czesci_sms(_nowe(107)), 1)
		self.assertEqual(liczba_czesci_sms(_nowe(115)), 2)

	def test_dane_z_leada_do_tresci(self) -> None:
		lead = TestDaneDoSzablonu.LEAD
		for typ in TYPY:
			zdarzenie = Zdarzenie(typ, H, T2, T1)
			tresc, _ = zbuduj_tresc_handlowiec(TRESCI_DOMYSLNE[typ], dane_do_szablonu(lead, zdarzenie))
			with self.subTest(typ=typ):
				self.assertNotIn("tajna", tresc.lower())
				self.assertNotIn("600", tresc)
				self.assertNotIn("http", tresc)

	def test_ostrzezenie_przy_dwoch_czesciach(self) -> None:
		dane = {
			**DANE_PRZYKLADOWE_HANDLOWIEC,
			"klient": "Bartłomiej Szczepański-Wróblewski",
			"adres": "Aleja Niepodległości 123/45 lok. 7, 64-100 Leszno Wielkopolskie",
		}
		tresc, ostrzezenie = zbuduj_tresc_handlowiec(TRESC_ZMIANA_DOMYSLNA, dane)
		self.assertEqual(liczba_czesci_sms(tresc), 2)
		self.assertIsNotNone(ostrzezenie)
		self.assertIn("2 części", ostrzezenie or "")

	def test_nieznany_placeholder_zostaje(self) -> None:
		tresc, _ = zbuduj_tresc_handlowiec("X {cc} {klient}", {"klient": "Jan", "cc": "Tajna"})
		self.assertEqual(tresc, "X {cc} Jan")

	def test_telefon_i_link_nie_sa_podstawiane(self) -> None:
		tresc, _ = zbuduj_tresc_handlowiec(
			"{klient} {telefon} {link}", {"klient": "Jan", "telefon": "600100200", "link": "https://x"}
		)
		self.assertEqual(tresc, "Jan {telefon} {link}")

	def test_placeholdery_dyzuru_nie_sa_znane(self) -> None:
		tresc, _ = zbuduj_tresc_handlowiec("{kod} {klient}", {"klient": "Jan", "kod": "00-001"})
		self.assertEqual(tresc, "{kod} Jan")

	def test_dane_przykladowe_komplet(self) -> None:
		self.assertEqual(set(DANE_PRZYKLADOWE_HANDLOWIEC), set(PLACEHOLDERY_HANDLOWIEC))


class TestWalidacja(unittest.TestCase):
	def test_domyslne_poprawne(self) -> None:
		for tresc in TRESCI_DOMYSLNE.values():
			self.assertIsNone(waliduj_tresc_handlowiec(tresc))

	def test_pusta(self) -> None:
		self.assertEqual(waliduj_tresc_handlowiec("  "), "Treść SMS nie może być pusta.")
		self.assertEqual(waliduj_tresc_handlowiec(None), "Treść SMS nie może być pusta.")

	def test_nieznany_placeholder(self) -> None:
		komunikat = waliduj_tresc_handlowiec("Spotkanie {termin} {autor}")
		self.assertIsNotNone(komunikat)
		self.assertIn("{autor}", komunikat or "")
		self.assertIn("{stary_termin}", komunikat or "")

	def test_placeholder_dyzuru_odrzucony(self) -> None:
		self.assertIsNotNone(waliduj_tresc_handlowiec("{kod}"))

	def test_telefon_i_link_odrzucone(self) -> None:
		self.assertIn("{telefon}", waliduj_tresc_handlowiec("tel. {telefon}") or "")
		self.assertIn("{link}", waliduj_tresc_handlowiec("{termin} {link}") or "")

	def test_limit(self) -> None:
		self.assertIsNone(waliduj_limit_handlowiec(0))
		self.assertIsNone(waliduj_limit_handlowiec("200"))
		self.assertIsNone(waliduj_limit_handlowiec(1000))
		self.assertIsNotNone(waliduj_limit_handlowiec(1001))
		self.assertIsNotNone(waliduj_limit_handlowiec(-1))
		self.assertIsNotNone(waliduj_limit_handlowiec("abc"))
		self.assertIsNotNone(waliduj_limit_handlowiec(None))

	def test_szablon_dla(self) -> None:
		self.assertEqual(szablon_dla(TYP_NOWE, {}), TRESC_NOWE_DOMYSLNA)
		self.assertEqual(szablon_dla(TYP_ZMIANA, {"tresc_handlowiec_zmiana": "  "}), TRESC_ZMIANA_DOMYSLNA)
		self.assertEqual(
			szablon_dla(TYP_ODWOLANIE, {"tresc_handlowiec_odwolanie": None}), TRESC_ODWOLANIE_DOMYSLNA
		)
		self.assertEqual(szablon_dla(TYP_NOWE, {"tresc_handlowiec_nowe": "Moje {termin}"}), "Moje {termin}")
		with self.assertRaises(ValueError):
			szablon_dla("inne", {})

	def test_pola_szablonow(self) -> None:
		self.assertEqual(
			dict(POLA_SZABLONOW),
			{
				"nowe": "tresc_handlowiec_nowe",
				"zmiana": "tresc_handlowiec_zmiana",
				"odwolanie": "tresc_handlowiec_odwolanie",
			},
		)

	def test_czy_flaga_jak_cint(self) -> None:
		self.assertFalse(czy_flaga({}, "handlowiec_wlaczone"))
		self.assertFalse(czy_flaga({"handlowiec_wlaczone": None}, "handlowiec_wlaczone"))
		self.assertFalse(czy_flaga({"handlowiec_wlaczone": "0"}, "handlowiec_wlaczone"))
		self.assertFalse(czy_flaga({"handlowiec_wlaczone": "x"}, "handlowiec_wlaczone"))
		self.assertTrue(czy_flaga({"handlowiec_wlaczone": "1"}, "handlowiec_wlaczone"))
		self.assertTrue(czy_flaga({"handlowiec_wlaczone": 1}, "handlowiec_wlaczone"))

	def test_limit_dzienny_z_ustawien(self) -> None:
		self.assertEqual(LIMIT_DZIENNY_DOMYSLNY, 100)
		self.assertEqual(limit_dzienny({}), 100)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": ""}), 100)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": "200"}), 200)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": "0"}), 0)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": "35"}), 35)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": "zle"}), 100)
		self.assertEqual(limit_dzienny({"limit_dzienny_handlowiec": -3}), 0)


class TestKlucze(unittest.TestCase):
	def test_prefiks(self) -> None:
		self.assertEqual(PREFIKS_KLUCZA, "volteo:sms_handlowiec:")
		self.assertEqual(klucz_stanu("CRM-LEAD-1"), "volteo:sms_handlowiec:stan:CRM-LEAD-1")
		self.assertEqual(
			klucz_rezerwacji("CRM-LEAD-1", TYP_NOWE, H, T1),
			f"volteo:sms_handlowiec:wyslane:CRM-LEAD-1:nowe:{H}:{T1}",
		)
		self.assertEqual(klucz_licznika_dnia(date(2026, 11, 5)), "volteo:sms_handlowiec:2026-11-05")
		self.assertEqual(klucz_licznika_dnia(TERAZ), "volteo:sms_handlowiec:2026-11-05")
		self.assertEqual(klucz_alertu("limit", TERAZ), "volteo:sms_handlowiec:alert:limit:2026-11-05")

	def test_brak_numeru_w_kluczu(self) -> None:
		klucz = klucz_rezerwacji("CRM-LEAD-1", TYP_ZMIANA, H, T1)
		self.assertNotIn("600100200", klucz)
		self.assertNotIn("+48", klucz)

	def test_rozne_typy_rozne_klucze(self) -> None:
		klucze = {klucz_rezerwacji("L", typ, H, T1) for typ in TYPY}
		self.assertEqual(len(klucze), 3)

	def test_stan_tam_i_z_powrotem(self) -> None:
		for stan in ((H, T1), ("", T1), (H, ""), STAN_PUSTY):
			with self.subTest(stan=stan):
				self.assertEqual(odkoduj_stan(zakoduj_stan(stan)), stan)
		self.assertEqual(zakoduj_stan((H, "2026-11-06 10:00:59")), f"{H}|2026-11-06 10:00")

	def test_odkoduj_bytes_i_smieci(self) -> None:
		self.assertEqual(odkoduj_stan(f"{H}|{T1}".encode()), (H, T1))
		self.assertIsNone(odkoduj_stan(None))
		self.assertIsNone(odkoduj_stan(""))
		self.assertIsNone(odkoduj_stan("bez separatora"))
		self.assertIsNone(odkoduj_stan(f"{H}|jutro"))


class TestOpisSladu(unittest.TestCase):
	def test_formaty(self) -> None:
		self.assertEqual(
			opis_sladu(Zdarzenie(TYP_NOWE, H, T1, ""), "Jan Handlowiec", WYNIK_WYSLANY, None),
			"SMS do handlowca Jan Handlowiec (nowe spotkanie pt. 06.11 10:00): wysłany.",
		)
		self.assertEqual(
			opis_sladu(Zdarzenie(TYP_ZMIANA, H, T2, T1), "Jan Handlowiec", WYNIK_TEST, None),
			"SMS do handlowca Jan Handlowiec (zmiana terminu na sob. 07.11 14:30): "
			"tryb testowy, SMS nie wyszedł do sieci.",
		)
		self.assertEqual(
			opis_sladu(Zdarzenie(TYP_ODWOLANIE, A, T1, T1), "Anna Poprzednia", WYNIK_BRAK_NUMERU, None),
			"SMS do handlowca Anna Poprzednia (odwołanie spotkania pt. 06.11 10:00): "
			"pominięty, brak numeru telefonu w profilu handlowca.",
		)

	def test_wszystkie_wyniki(self) -> None:
		for wynik in (
			WYNIK_WYSLANY,
			WYNIK_TEST,
			WYNIK_BRAK_NUMERU,
			WYNIK_WLASNA_ZMIANA,
			WYNIK_LIMIT,
			WYNIK_BLAD,
			WYNIK_ODLOZONY,
		):
			with self.subTest(wynik=wynik):
				tekst = opis_sladu(Zdarzenie(TYP_NOWE, H, T1, ""), "X", wynik, None)
				self.assertTrue(tekst.endswith(OPISY_WYNIKU[wynik] + "."))

	def test_brak_nazwy_odbiorcy(self) -> None:
		self.assertIn(H, opis_sladu(Zdarzenie(TYP_NOWE, H, T1, ""), "", WYNIK_WYSLANY, None))

	def test_brak_cyfr_numeru(self) -> None:
		tekst = opis_sladu(
			Zdarzenie(TYP_NOWE, H, T1, ""),
			"Jan Handlowiec",
			WYNIK_BLAD,
			"SMSAPI: niepoprawny numer +48 600 100 200 i 48600100200",
		)
		for fragment in ("600", "48600100200", "100 200"):
			self.assertNotIn(fragment, tekst)
		self.assertIn("błąd wysyłki", tekst)

	def test_brak_tresci_sms(self) -> None:
		tresc, _ = zbuduj_tresc_handlowiec(TRESC_NOWE_DOMYSLNA, DANE_PRZYKLADOWE_HANDLOWIEC)
		tekst = opis_sladu(Zdarzenie(TYP_NOWE, H, T1, ""), "Jan Handlowiec", WYNIK_WYSLANY, None)
		self.assertNotIn(tresc, tekst)
		self.assertNotIn("Kowalski", tekst)
		self.assertIsNone(re.search(r"\d{6,}", tekst))

	def test_dopisek_ostrzezenia(self) -> None:
		tekst = opis_sladu(
			Zdarzenie(TYP_NOWE, H, T1, ""),
			"Jan",
			WYNIK_WYSLANY,
			"Treść SMS ma 170 znaków, wyjdzie 2 części (limit jednej to 160).",
		)
		self.assertTrue(
			tekst.endswith("wysłany; Treść SMS ma 170 znaków, wyjdzie 2 części (limit jednej to 160).")
		)


class TestCiszaNocna(unittest.TestCase):
	def _o(self, godzina: int, minuta: int, dzien: int = 5) -> datetime:
		return datetime(2026, 11, dzien, godzina, minuta, 0)

	def test_granice(self) -> None:
		przypadki = {
			(20, 59): False,
			(21, 0): True,
			(23, 59): True,
			(0, 0): True,
			(3, 30): True,
			(7, 59): True,
			(8, 0): False,
			(12, 0): False,
		}
		for (g, m), oczekiwane in przypadki.items():
			with self.subTest(godzina=f"{g:02d}:{m:02d}"):
				self.assertEqual(czy_cisza_nocna(self._o(g, m)), oczekiwane)

	def test_sekundy_na_granicach(self) -> None:
		self.assertFalse(czy_cisza_nocna(datetime(2026, 11, 5, 20, 59, 59)))
		self.assertTrue(czy_cisza_nocna(datetime(2026, 11, 5, 7, 59, 59)))

	def test_start_poza_cisza_to_teraz(self) -> None:
		teraz = datetime(2026, 11, 5, 20, 59, 30)
		self.assertEqual(najblizszy_start_wysylki(teraz), teraz)
		self.assertEqual(najblizszy_start_wysylki(self._o(8, 0)), self._o(8, 0))

	def test_start_wieczorem_jutro_rano(self) -> None:
		self.assertEqual(najblizszy_start_wysylki(self._o(21, 0)), datetime(2026, 11, 6, 8, 0))
		self.assertEqual(najblizszy_start_wysylki(self._o(23, 45)), datetime(2026, 11, 6, 8, 0))

	def test_start_po_polnocy_tego_dnia(self) -> None:
		self.assertEqual(najblizszy_start_wysylki(self._o(0, 0, dzien=6)), datetime(2026, 11, 6, 8, 0))
		self.assertEqual(
			najblizszy_start_wysylki(datetime(2026, 11, 6, 7, 59, 59)), datetime(2026, 11, 6, 8, 0)
		)

	def test_przelom_miesiaca_i_roku(self) -> None:
		self.assertEqual(najblizszy_start_wysylki(datetime(2026, 11, 30, 22, 0)), datetime(2026, 12, 1, 8, 0))
		self.assertEqual(najblizszy_start_wysylki(datetime(2026, 12, 31, 21, 30)), datetime(2027, 1, 1, 8, 0))

	def test_okno_wlasne_bez_przejscia_przez_polnoc(self) -> None:
		self.assertTrue(czy_cisza_nocna(self._o(1, 0), od="00:30", do="06:00"))
		self.assertFalse(czy_cisza_nocna(self._o(6, 0), od="00:30", do="06:00"))
		self.assertFalse(czy_cisza_nocna(self._o(23, 0), od="00:30", do="06:00"))
		self.assertEqual(
			najblizszy_start_wysylki(self._o(1, 0), od="00:30", do="06:00"), datetime(2026, 11, 5, 6, 0)
		)

	def test_rowne_granice_bez_ciszy(self) -> None:
		self.assertFalse(czy_cisza_nocna(self._o(3, 0), od="08:00", do="08:00"))

	def test_spotkanie_z_nocy_juz_w_przeszlosci_rano(self) -> None:
		# Odroczony lead przetwarzany po 08:00 na bieżącym stanie: spotkanie o 07:30 już minęło.
		rano = datetime(2026, 11, 6, 8, 0)
		self.assertEqual(ustal_zdarzenia(STAN_PUSTY, (H, "2026-11-06 07:30"), teraz=rano, odwolania=True), [])


class TestOdroczenie(unittest.TestCase):
	def test_klucz(self) -> None:
		self.assertEqual(KLUCZ_ODROCZONYCH, "volteo:sms_handlowiec:odroczone")

	def test_tam_i_z_powrotem(self) -> None:
		for przed in ((H, T1), STAN_PUSTY, ("", T1), (H, "")):
			with self.subTest(przed=przed):
				self.assertEqual(odkoduj_odroczenie(zakoduj_odroczenie(przed, A)), (przed, A))

	def test_normalizuje_i_bytes(self) -> None:
		tekst = zakoduj_odroczenie((H, "2026-11-06 10:00:59"), A)
		self.assertEqual(odkoduj_odroczenie(tekst.encode()), ((H, T1), A))

	def test_nieczytelne(self) -> None:
		for tekst in (None, "", "nie json", "[1, 2]", b"\xff"):
			with self.subTest(tekst=tekst):
				self.assertIsNone(odkoduj_odroczenie(tekst))

	def test_slad_odlozenia(self) -> None:
		self.assertEqual(
			opis_sladu(Zdarzenie(TYP_NOWE, H, T1, ""), "Jan Handlowiec", WYNIK_ODLOZONY, None),
			"SMS do handlowca Jan Handlowiec (nowe spotkanie pt. 06.11 10:00): odłożony do 08:00 (cisza nocna).",
		)


class TestDomyslne(unittest.TestCase):
	def test_teksty_z_decyzji_znak_w_znak(self) -> None:
		self.assertEqual(TRESC_NOWE_DOMYSLNA, "Nowe spotkanie {termin}: {klient}, {adres}. Szczegóły w CRM.")
		self.assertEqual(
			TRESC_ZMIANA_DOMYSLNA,
			"Zmiana terminu: {klient}, {adres}, teraz {termin} (było {stary_termin}). Szczegóły w CRM.",
		)
		self.assertEqual(
			TRESC_ODWOLANIE_DOMYSLNA,
			"Spotkanie {stary_termin}: {klient}, {miejscowosc}, odwołane albo przekazane innej osobie. Nie jedź.",
		)

	def test_typy(self) -> None:
		self.assertEqual((TYP_NOWE, TYP_ZMIANA, TYP_ODWOLANIE), ("nowe", "zmiana", "odwolanie"))
		self.assertEqual(TYPY, (TYP_NOWE, TYP_ZMIANA, TYP_ODWOLANIE))

	def test_placeholdery(self) -> None:
		self.assertEqual(
			PLACEHOLDERY_HANDLOWIEC,
			(
				"termin",
				"stary_termin",
				"data",
				"godzina",
				"klient",
				"adres",
				"miejscowosc",
			),
		)

	def test_bez_telefonu_i_linku_w_domyslnych(self) -> None:
		for tresc in TRESCI_DOMYSLNE.values():
			self.assertNotIn("{link}", tresc)
			self.assertNotIn("{telefon}", tresc)

	def test_limit_i_cisza(self) -> None:
		self.assertEqual(LIMIT_DZIENNY_DOMYSLNY, 100)
		self.assertEqual((CISZA_OD, CISZA_DO), ("21:00", "08:00"))

	def test_brak_placeholdera_autora(self) -> None:
		for zakazany in ("autor", "cc", "custom_cc", "uwagi", "kto", "telefon", "link"):
			self.assertNotIn(zakazany, PLACEHOLDERY_HANDLOWIEC)


if __name__ == "__main__":
	unittest.main()
