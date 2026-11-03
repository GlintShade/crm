import unittest
from types import SimpleNamespace

from crm.volteo_widocznosc_wlasciciela import (
	nieaktualni_uzytkownicy,
	plan_odebrania_dostepu,
	przypisani_po_zmianie,
)

A = "a@volteo.pl"
B = "b@volteo.pl"
CC = "cc@volteo.pl"
BO = "backoffice@volteo.pl"


def todo(name, user, status="Open"):
	return {"name": name, "allocated_to": user, "status": status}


def share(name, user):
	return {"name": name, "user": user}


class TestPlanOdebraniaDostepu(unittest.TestCase):
	def test_a_zmiana_a_na_b_anuluje_todo_i_share_a(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(
			A,
			B,
			[todo("T1", A), todo("T2", B)],
			[share("S1", A), share("S2", B)],
		)
		self.assertEqual(plan, {"todo": ["T1"], "udostepnienia": ["S1"]})

	def test_b_zamkniete_todo_a_tez_jest_anulowane(self: "TestPlanOdebraniaDostepu") -> None:
		# Closed nadal wpuszcza przez galaz q2 (status != Cancelled).
		plan = plan_odebrania_dostepu(A, B, [todo("T1", A, "Closed"), todo("T0", A, "Open")], [])
		self.assertEqual(plan["todo"], ["T1", "T0"])

	def test_c_juz_anulowane_todo_nie_jest_ruszane(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(A, B, [todo("T1", A, "Cancelled")], [])
		self.assertEqual(plan["todo"], [])

	def test_d_wiersze_b_cc_i_innych_zostaja(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(
			A,
			B,
			[todo("T1", B), todo("T2", CC), todo("T3", BO)],
			[share("S1", B), share("S2", CC), share("S3", BO)],
			chronieni=[CC],
		)
		self.assertEqual(plan, {"todo": [], "udostepnienia": []})

	def test_e_brak_zmiany_nic_nie_robi(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(A, A, [todo("T1", A)], [share("S1", A)])
		self.assertEqual(plan, {"todo": [], "udostepnienia": []})

	def test_f_pusty_stary_wlasciciel_nic_nie_robi(self: "TestPlanOdebraniaDostepu") -> None:
		for stary in (None, "", "   "):
			plan = plan_odebrania_dostepu(stary, B, [todo("T1", B)], [share("S1", B)])
			self.assertEqual(plan, {"todo": [], "udostepnienia": []})

	def test_g_wyczyszczenie_wlasciciela_odbiera_dostep_a(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(A, None, [todo("T1", A)], [share("S1", A)])
		self.assertEqual(plan, {"todo": ["T1"], "udostepnienia": ["S1"]})

	def test_h_stary_wlasciciel_bedacy_cc_jest_chroniony(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(CC, B, [todo("T1", CC)], [share("S1", CC)], chronieni=[CC])
		self.assertEqual(plan, {"todo": [], "udostepnienia": []})

	def test_i_porownanie_po_przycieciu_spacji(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(f" {A} ", B, [todo("T1", A)], [share("S1", f"{A} ")])
		self.assertEqual(plan, {"todo": ["T1"], "udostepnienia": ["S1"]})

	def test_j_przyjmuje_obiekty_z_atrybutami(self: "TestPlanOdebraniaDostepu") -> None:
		# frappe.get_all zwraca frappe._dict; SimpleNamespace symuluje dostep atrybutowy.
		t = SimpleNamespace(name="T1", allocated_to=A, status="Open")
		s = SimpleNamespace(name="S1", user=A)
		self.assertEqual(plan_odebrania_dostepu(A, B, [t], [s]), {"todo": ["T1"], "udostepnienia": ["S1"]})

	def test_k_wiele_todo_a_wszystkie_anulowane(self: "TestPlanOdebraniaDostepu") -> None:
		plan = plan_odebrania_dostepu(A, B, [todo("T1", A), todo("T2", A), todo("T3", B)], [])
		self.assertEqual(plan["todo"], ["T1", "T2"])

	def test_l_nowy_wlasciciel_zawsze_chroniony(self: "TestPlanOdebraniaDostepu") -> None:
		# Nawet gdy wolajacy nie poda go w `chronieni`.
		plan = plan_odebrania_dostepu(A, B, [todo("T1", B)], [share("S1", B)], chronieni=[])
		self.assertEqual(plan, {"todo": [], "udostepnienia": []})


class TestPrzypisaniPoZmianie(unittest.TestCase):
	def test_a_pomija_anulowane_i_zamkniete(self: "TestPrzypisaniPoZmianie") -> None:
		todos = [todo("T1", A), todo("T2", B), todo("T3", CC, "Closed"), todo("T4", BO, "Cancelled")]
		self.assertEqual(przypisani_po_zmianie(todos, ["T1"]), [B])

	def test_b_bez_duplikatow(self: "TestPrzypisaniPoZmianie") -> None:
		todos = [todo("T1", B), todo("T2", B), todo("T3", BO)]
		self.assertEqual(przypisani_po_zmianie(todos, []), [B, BO])

	def test_c_pusto_gdy_wszystko_anulowane(self: "TestPrzypisaniPoZmianie") -> None:
		self.assertEqual(przypisani_po_zmianie([todo("T1", A)], ["T1"]), [])


class TestNieaktualniUzytkownicy(unittest.TestCase):
	def test_a_handlowiec_nie_bedacy_wlascicielem_jest_nieaktualny(
		self: "TestNieaktualniUzytkownicy",
	) -> None:
		self.assertEqual(nieaktualni_uzytkownicy(B, [A, B], [CC], [A, B]), [A])

	def test_b_cc_backoffice_i_admin_nigdy(self: "TestNieaktualniUzytkownicy") -> None:
		self.assertEqual(
			nieaktualni_uzytkownicy(B, [CC, BO, "Administrator"], [CC], [A, B]),
			[],
		)

	def test_c_custom_cc_chroniony_nawet_jako_handlowiec(self: "TestNieaktualniUzytkownicy") -> None:
		self.assertEqual(nieaktualni_uzytkownicy(B, [A], [A], [A, B]), [])

	def test_d_bez_wlasciciela_kazdy_handlowiec_nieaktualny(self: "TestNieaktualniUzytkownicy") -> None:
		self.assertEqual(nieaktualni_uzytkownicy(None, [A, A, B, None, ""], [], [A, B]), [A, B])


if __name__ == "__main__":
	unittest.main()
