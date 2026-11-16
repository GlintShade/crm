import json
import unittest

from crm.volteo_komentarze import (
	czy_komentarz_edytowalny,
	liczba_zmian_tresci,
	nowe_wzmianki,
	wzmianki,
	zmiany_tresci,
)


def _wzm(email: str, nazwa: str) -> str:
	return f'<span data-type="mention" data-id="{email}" data-label="{nazwa}">@{nazwa}</span>'


class TestWzmianki(unittest.TestCase):
	def test_pusta_tresc(self: "TestWzmianki") -> None:
		self.assertEqual(wzmianki(None), [])
		self.assertEqual(wzmianki(""), [])
		self.assertEqual(wzmianki("<p>bez wzmianek</p>"), [])

	def test_dwie_wzmianki_w_kolejnosci(self: "TestWzmianki") -> None:
		tresc = f"<p>{_wzm('a@x.pl', 'Anna')} i {_wzm('b@x.pl', 'Bartek')}</p>"
		self.assertEqual(
			wzmianki(tresc),
			[
				{"email": "a@x.pl", "full_name": "Anna"},
				{"email": "b@x.pl", "full_name": "Bartek"},
			],
		)

	def test_inny_span_nie_jest_wzmianka(self: "TestWzmianki") -> None:
		self.assertEqual(wzmianki('<span data-type="tag" data-id="a@x.pl">x</span>'), [])


class TestNoweWzmianki(unittest.TestCase):
	def test_bez_zmiany_wzmianek_nic_nowego(self: "TestNoweWzmianki") -> None:
		przed = f"<p>{_wzm('a@x.pl', 'Anna')} popraw</p>"
		po = f"<p>{_wzm('a@x.pl', 'Anna')} popraw to</p>"
		self.assertEqual(nowe_wzmianki(przed, po), [])

	def test_dodana_wzmianka_tylko_nowa_osoba(self: "TestNoweWzmianki") -> None:
		przed = f"<p>{_wzm('a@x.pl', 'Anna')}</p>"
		po = f"<p>{_wzm('a@x.pl', 'Anna')} {_wzm('b@x.pl', 'Bartek')}</p>"
		self.assertEqual(nowe_wzmianki(przed, po), [{"email": "b@x.pl", "full_name": "Bartek"}])

	def test_usunieta_wzmianka_nic_nie_wysyla(self: "TestNoweWzmianki") -> None:
		przed = f"<p>{_wzm('a@x.pl', 'Anna')}</p>"
		self.assertEqual(nowe_wzmianki(przed, "<p>bez</p>"), [])

	def test_pusty_przed_wszystkie_nowe(self: "TestNoweWzmianki") -> None:
		po = f"<p>{_wzm('a@x.pl', 'Anna')}</p>"
		self.assertEqual(len(nowe_wzmianki(None, po)), 1)

	def test_duplikat_w_po_jeden_wpis(self: "TestNoweWzmianki") -> None:
		po = f"<p>{_wzm('a@x.pl', 'Anna')} {_wzm('a@x.pl', 'Anna')}</p>"
		self.assertEqual(len(nowe_wzmianki("", po)), 1)

	def test_wzmianka_bez_adresu_pomijana(self: "TestNoweWzmianki") -> None:
		self.assertEqual(nowe_wzmianki("", '<span data-type="mention" data-label="X">@X</span>'), [])


class TestEdytowalnosc(unittest.TestCase):
	def test_lead_i_szansa(self: "TestEdytowalnosc") -> None:
		self.assertTrue(czy_komentarz_edytowalny("CRM Lead", "Comment"))
		self.assertTrue(czy_komentarz_edytowalny("CRM Deal", "Comment"))

	def test_pozostale_nie(self: "TestEdytowalnosc") -> None:
		self.assertFalse(czy_komentarz_edytowalny("CRM Task", "Comment"))
		self.assertFalse(czy_komentarz_edytowalny("Volteo Audyt", "Comment"))
		self.assertFalse(czy_komentarz_edytowalny("CRM Lead", "Info"))
		self.assertFalse(czy_komentarz_edytowalny(None, None))


class TestHistoriaReuzyta(unittest.TestCase):
	def test_zmiany_i_licznik(self: "TestHistoriaReuzyta") -> None:
		wersje = [
			{
				"owner": "a@x.pl",
				"creation": "2026-11-16 10:00:00",
				"data": json.dumps({"changed": [["content", "<p>a</p>", "<p>b</p>"]]}),
			}
		]
		self.assertEqual(liczba_zmian_tresci(wersje), 1)
		self.assertEqual(zmiany_tresci(wersje)[0]["przed"], "<p>a</p>")


if __name__ == "__main__":
	unittest.main()
