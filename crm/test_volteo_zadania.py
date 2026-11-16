import inspect
import unittest
from datetime import date, datetime

from crm.volteo_zadania import (
	ETYKIETA_RODZAJU,
	KLUCZ_REGULY,
	RODZAJE,
	STATUSY_ZAMKNIETE,
	dane_zadania,
	filtr_duplikatu,
	oblicz_termin,
	oblicz_termin_godzinowy,
	opis_zadania_html,
	tytul_zadania,
)


class TestTytulZadania(unittest.TestCase):
	def test_a_tytul_oze(self: "TestTytulZadania") -> None:
		self.assertEqual(
			tytul_zadania("oze", "Jan Kowalski"),
			"Audyt OZE: Jan Kowalski",
		)

	def test_b_tytul_cp(self: "TestTytulZadania") -> None:
		self.assertEqual(
			tytul_zadania("cp", "Anna Nowak"),
			"Audyt CP: Anna Nowak",
		)

	def test_c_nieznany_rodzaj_daje_value_error(self: "TestTytulZadania") -> None:
		with self.assertRaises(ValueError):
			tytul_zadania("cos_innego", "Jan Kowalski")


class TestOpisZadaniaHtml(unittest.TestCase):
	def test_a_opis_oze_tresc_dokladna(self: "TestOpisZadaniaHtml") -> None:
		self.assertEqual(
			opis_zadania_html("oze", "Jan Kowalski", "PRO/PV/26/0001", "Anna Nowak"),
			"<p>Audyt OZE szansy <b>PRO/PV/26/0001</b> (klient: <b>Jan Kowalski</b>) "
			"został przesłany do weryfikacji przez Anna Nowak.</p>",
		)

	def test_b_opis_cp_tresc_dokladna(self: "TestOpisZadaniaHtml") -> None:
		self.assertEqual(
			opis_zadania_html("cp", "Ewa Wisniewska", "PRO/CP/26/0002", "Piotr Zielinski"),
			"<p>Audyt CP szansy <b>PRO/CP/26/0002</b> (klient: <b>Ewa Wisniewska</b>) "
			"został przesłany do weryfikacji przez Piotr Zielinski.</p>",
		)

	def test_c_nieznany_rodzaj_daje_value_error(self: "TestOpisZadaniaHtml") -> None:
		with self.assertRaises(ValueError):
			opis_zadania_html("cos_innego", "Jan Kowalski", "PRO/PV/26/0001", "Anna Nowak")


class TestObliczTermin(unittest.TestCase):
	def test_a_zero_daje_none(self: "TestObliczTermin") -> None:
		self.assertIsNone(oblicz_termin(date(2026, 9, 25), 0))

	def test_b_ujemna_daje_none(self: "TestObliczTermin") -> None:
		self.assertIsNone(oblicz_termin(date(2026, 9, 25), -3))

	def test_c_dodatnia_dodaje_dni(self: "TestObliczTermin") -> None:
		self.assertEqual(oblicz_termin(date(2026, 9, 25), 5), date(2026, 9, 30))

	def test_d_string_liczbowy_jest_parsowany(self: "TestObliczTermin") -> None:
		self.assertEqual(oblicz_termin(date(2026, 9, 25), "2"), date(2026, 9, 27))

	def test_e_none_daje_none(self: "TestObliczTermin") -> None:
		self.assertIsNone(oblicz_termin(date(2026, 9, 25), None))

	def test_f_string_niepoprawny_traktowany_jako_zero(self: "TestObliczTermin") -> None:
		self.assertIsNone(oblicz_termin(date(2026, 9, 25), "abc"))

	def test_g_string_zero_daje_none(self: "TestObliczTermin") -> None:
		self.assertIsNone(oblicz_termin(date(2026, 9, 25), "0"))

	def test_h_przejscie_przez_koniec_miesiaca(self: "TestObliczTermin") -> None:
		self.assertEqual(oblicz_termin(date(2026, 9, 29), 3), date(2026, 10, 2))


class TestFiltrDuplikatu(unittest.TestCase):
	def test_a_ksztalt_dokladny(self: "TestFiltrDuplikatu") -> None:
		self.assertEqual(
			filtr_duplikatu("PRO/PV/26/0001", "rep@proenergy.pro", "Audyt OZE: Jan Kowalski"),
			{
				"reference_doctype": "CRM Deal",
				"reference_docname": "PRO/PV/26/0001",
				"assigned_to": "rep@proenergy.pro",
				"title": "Audyt OZE: Jan Kowalski",
				"status": ["not in", ["Done", "Canceled"]],
			},
		)

	def test_b_dwa_wywolania_zwracaja_odrebne_obiekty(self: "TestFiltrDuplikatu") -> None:
		a = filtr_duplikatu("PRO/PV/26/0001", "rep@proenergy.pro", "tytul")
		b = filtr_duplikatu("PRO/PV/26/0001", "rep@proenergy.pro", "tytul")
		self.assertEqual(a, b)
		self.assertIsNot(a, b)
		self.assertIsNot(a["status"], b["status"])

	def test_c_status_uzywa_statusy_zamkniete(self: "TestFiltrDuplikatu") -> None:
		filtr = filtr_duplikatu("PRO/PV/26/0001", "rep@proenergy.pro", "tytul")
		self.assertEqual(filtr["status"], ["not in", list(STATUSY_ZAMKNIETE)])


class TestObliczTerminGodzinowy(unittest.TestCase):
	def test_a_zaokragla_w_gore_do_pelnej_godziny(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 14, 20, 0), 1),
			datetime(2026, 11, 17, 15, 0, 0),
		)

	def test_b_pelna_godzina_zostaje(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 14, 0, 0), 1),
			datetime(2026, 11, 17, 14, 0, 0),
		)

	def test_c_sekunda_ponad_godzine_zaokragla_w_gore(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 14, 0, 1), 1),
			datetime(2026, 11, 17, 15, 0, 0),
		)

	def test_d_mikrosekundy_zaokraglaja_w_gore(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 14, 0, 0, 5), 2),
			datetime(2026, 11, 18, 15, 0, 0),
		)

	def test_e_przejscie_przez_polnoc_i_rok(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 23, 30, 0), 1),
			datetime(2026, 11, 18, 0, 0, 0),
		)
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 12, 31, 23, 10, 0), 1),
			datetime(2027, 1, 2, 0, 0, 0),
		)

	def test_f_zero_ujemne_none_i_smieci_daja_none(self: "TestObliczTerminGodzinowy") -> None:
		teraz = datetime(2026, 11, 16, 14, 20, 0)
		for dni in (0, -2, None, "abc", "0"):
			self.assertIsNone(oblicz_termin_godzinowy(teraz, dni), dni)

	def test_g_string_liczbowy_jest_parsowany(self: "TestObliczTerminGodzinowy") -> None:
		self.assertEqual(
			oblicz_termin_godzinowy(datetime(2026, 11, 16, 14, 20, 0), "1"),
			datetime(2026, 11, 17, 15, 0, 0),
		)

	def test_h_nie_mutuje_argumentu(self: "TestObliczTerminGodzinowy") -> None:
		teraz = datetime(2026, 11, 16, 14, 20, 0)
		oblicz_termin_godzinowy(teraz, 1)
		self.assertEqual(teraz, datetime(2026, 11, 16, 14, 20, 0))


class TestDaneZadania(unittest.TestCase):
	def test_a_pelny_dict_rownosc(self: "TestDaneZadania") -> None:
		wynik = dane_zadania(
			rodzaj="oze",
			klient="Jan Kowalski",
			deal="PRO/PV/26/0001",
			autor="Anna Nowak",
			odbiorca="rep@proenergy.pro",
			dzisiaj=date(2026, 9, 25),
			termin_dni=3,
		)
		self.assertEqual(
			wynik,
			{
				"doctype": "CRM Task",
				"title": "Audyt OZE: Jan Kowalski",
				"description": (
					"<p>Audyt OZE szansy <b>PRO/PV/26/0001</b> (klient: <b>Jan Kowalski</b>) "
					"został przesłany do weryfikacji przez Anna Nowak.</p>"
				),
				"status": "Todo",
				"priority": "Medium",
				"start_date": "2026-09-25",
				"due_date": "2026-09-28",
				"assigned_to": "rep@proenergy.pro",
				"reference_doctype": "CRM Deal",
				"reference_docname": "PRO/PV/26/0001",
			},
		)

	def test_b_termin_dni_zero_daje_due_date_none(self: "TestDaneZadania") -> None:
		wynik = dane_zadania(
			rodzaj="cp",
			klient="Ewa Wisniewska",
			deal="PRO/CP/26/0002",
			autor="Piotr Zielinski",
			odbiorca="rep2@proenergy.pro",
			dzisiaj=date(2026, 9, 25),
			termin_dni=0,
		)
		self.assertIsNone(wynik["due_date"])

	def test_d_z_teraz_due_date_godzinowy(self: "TestDaneZadania") -> None:
		wynik = dane_zadania(
			rodzaj="oze",
			klient="Jan Kowalski",
			deal="PRO/PV/26/0001",
			autor="Anna Nowak",
			odbiorca="rep@proenergy.pro",
			dzisiaj=date(2026, 11, 16),
			termin_dni=1,
			teraz=datetime(2026, 11, 16, 14, 20, 0),
		)
		self.assertEqual(wynik["due_date"], "2026-11-17 15:00:00")
		self.assertEqual(wynik["start_date"], "2026-11-16")

	def test_e_z_teraz_i_zerem_dni_due_date_none(self: "TestDaneZadania") -> None:
		wynik = dane_zadania(
			rodzaj="cp",
			klient="Ewa Wisniewska",
			deal="PRO/CP/26/0002",
			autor="Piotr Zielinski",
			odbiorca="rep2@proenergy.pro",
			dzisiaj=date(2026, 11, 16),
			termin_dni=0,
			teraz=datetime(2026, 11, 16, 14, 20, 0),
		)
		self.assertIsNone(wynik["due_date"])

	def test_c_nieznany_rodzaj_daje_value_error(self: "TestDaneZadania") -> None:
		with self.assertRaises(ValueError):
			dane_zadania(
				rodzaj="cos_innego",
				klient="Jan Kowalski",
				deal="PRO/PV/26/0001",
				autor="Anna Nowak",
				odbiorca="rep@proenergy.pro",
				dzisiaj=date(2026, 9, 25),
				termin_dni=3,
			)


class TestStale(unittest.TestCase):
	def test_a_klucz_reguly_oze(self: "TestStale") -> None:
		self.assertEqual(KLUCZ_REGULY["oze"], "zadanie_audyt_przeslany")

	def test_b_klucz_reguly_cp(self: "TestStale") -> None:
		self.assertEqual(KLUCZ_REGULY["cp"], "zadanie_audyt_cp_przeslany")

	def test_c_rodzaje_zawiera_oze_i_cp(self: "TestStale") -> None:
		self.assertEqual(RODZAJE, ("oze", "cp"))

	def test_d_etykieta_rodzaju_pokrywa_rodzaje(self: "TestStale") -> None:
		self.assertEqual(set(ETYKIETA_RODZAJU.keys()), set(RODZAJE))

	def test_e_klucz_reguly_pokrywa_rodzaje(self: "TestStale") -> None:
		self.assertEqual(set(KLUCZ_REGULY.keys()), set(RODZAJE))


class TestBrakMyslnikow(unittest.TestCase):
	def test_a_zrodlo_modulu_bez_em_i_en_myslnika(self: "TestBrakMyslnikow") -> None:
		import crm.volteo_zadania as modul

		zrodlo = inspect.getsource(modul)
		self.assertNotIn("\u2014", zrodlo)  # em dash (unicode escape, not the literal character, per HARD RULE)
		self.assertNotIn("\u2013", zrodlo)  # en dash (unicode escape, not the literal character, per HARD RULE)


if __name__ == "__main__":
	unittest.main()
