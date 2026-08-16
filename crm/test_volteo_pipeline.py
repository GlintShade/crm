import unittest

from crm.volteo_pipeline import (
	NOTATKI,
	OZE_RODZAJE,
	PIPELINE_CP,
	PIPELINE_OZE,
	TERMINALE,
	grupa_for,
	is_forward,
	notatka_for,
	pipeline_for,
	pipeline_key_for,
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
		self.assertEqual(step_index("Czyste Powietrze", "Lead"), 0)
		self.assertEqual(step_index("Czyste Powietrze", "Audyt Energetyczny"), 3)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie"), 5)

	def test_f_finansowanie_ma_różny_indeks_w_obu_rurociągach(self: "TestVolteoPipeline") -> None:
		# "Finansowanie" jest JEDNYM wierszem statusu współdzielonym przez oba rurociągi,
		# ale zajmuje w nich dwa różne miejsca — to właśnie dlatego kolejność rurociągu
		# nie może żyć w `CRM Deal Status.position` (patrz docstring modułu).
		self.assertEqual(step_index("Fotowoltaika", "Finansowanie"), 4)
		self.assertEqual(step_index("Czyste Powietrze", "Finansowanie"), 5)

	def test_f2_weryfikacja_backoffice_wyłącznie_oze(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Weryfikacja Backoffice"), 3)
		self.assertEqual(step_index("Czyste Powietrze", "Weryfikacja Backoffice"), -1)

	def test_f3_oferta_docelowa_usunięta_z_obu_rurociągów(self: "TestVolteoPipeline") -> None:
		self.assertEqual(step_index("Fotowoltaika", "Oferta Docelowa"), -1)
		self.assertEqual(step_index("Czyste Powietrze", "Oferta Docelowa"), -1)

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
		self.assertFalse(is_forward("Czyste Powietrze", "Przegrana", "Finansowanie"))

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
		self.assertIsNone(notatka_for("Czyste Powietrze", "Finansowanie"))
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
		self.assertEqual(len(grupa), 7)
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

		pipeline_key_for("Fotowoltaika")
		pipeline_for("Czyste Powietrze")
		step_index("Fotowoltaika", "Lead")
		notatka_for("Czyste Powietrze", "Dokumentacja")
		is_forward("Fotowoltaika", "Lead", "Umowa Wygenerowana")
		grupa_for("Fotowoltaika")
		grupa_for("Czyste Powietrze")

		self.assertEqual(PIPELINE_OZE, przed_oze)
		self.assertEqual(PIPELINE_CP, przed_cp)
		self.assertEqual(NOTATKI, przed_notatki)
		self.assertEqual(OZE_RODZAJE, przed_rodzaje)
		self.assertEqual(TERMINALE, przed_terminale)


if __name__ == "__main__":
	unittest.main()
