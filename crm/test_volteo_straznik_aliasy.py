"""Strazniki (override_whitelisted_methods) nie moga trzymac w module nazwy
wskazujacej na oryginalna funkcje rdzenia: Frappe wywola ja pod
/api/method/<modul strażnika>.<nazwa> z pominieciem strazniku (ops#423).
Test bez frappe: czyta hooks.py i zrodla modulow jako AST."""

import ast
import unittest
from pathlib import Path

KORZEN = Path(__file__).resolve().parent


def _cele():
	"""{metoda rdzenia: modul strażnika} z override_whitelisted_methods."""
	for wezel in ast.parse((KORZEN / "hooks.py").read_text()).body:
		if isinstance(wezel, ast.Assign) and wezel.targets[0].id == "override_whitelisted_methods":
			return ast.literal_eval(wezel.value)
	raise AssertionError("brak override_whitelisted_methods w hooks.py")


class TestStraznikBezAliasow(unittest.TestCase):
	def test_modul_strażnika_nie_importuje_nazw_nadpisanych_funkcji(self):
		bledy = []
		for rdzen, cel in _cele().items():
			modul_rdzenia, _, nazwa = rdzen.rpartition(".")
			modul_rdzenia = modul_rdzenia or "frappe.handler"  # run_doc_method, runserverobj
			sciezka = KORZEN.parent / (cel.rpartition(".")[0].replace(".", "/") + ".py")
			if not sciezka.exists():
				continue
			for w in ast.walk(ast.parse(sciezka.read_text())):
				if isinstance(w, ast.ImportFrom) and w.module == modul_rdzenia:
					bledy += [f"{sciezka.name}: from {w.module} import {a.name}"
						for a in w.names if a.name == nazwa]
		self.assertEqual(bledy, [])

	def test_hooks_ma_cele(self):
		self.assertGreaterEqual(len(_cele()), 10)


if __name__ == "__main__":
	unittest.main()
