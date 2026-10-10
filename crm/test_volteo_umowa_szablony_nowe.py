# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Testy 11 ostatecznych szablonów PDF umów (b69, chunk U1): pliki w repo, sumy
SHA-256 zgodne ze stałymi w modułach map, liczby stron, bezpiecznik zakresu
(warianty dwuosobowe z cechą nie są zarejestrowane w `SZABLONY`) oraz regresja
trzech szablonów PODWÓJNA."""

import hashlib
import unittest
from pathlib import Path

from crm import volteo_umowa_mapa as m_pvme
from crm import volteo_umowa_mapa_me as m_me
from crm import volteo_umowa_mapa_me2 as m_me2
from crm import volteo_umowa_mapa_meev as m_meev
from crm import volteo_umowa_mapa_mek as m_mek
from crm import volteo_umowa_mapa_mekev as m_mekev
from crm import volteo_umowa_mapa_pv as m_pv
from crm import volteo_umowa_mapa_pv2 as m_pv2
from crm import volteo_umowa_mapa_pvk as m_pvk
from crm import volteo_umowa_mapa_pvme2 as m_pvme2
from crm import volteo_umowa_mapa_pvmeev as m_pvmeev
from crm import volteo_umowa_mapa_pvmek as m_pvmek
from crm import volteo_umowa_mapa_pvmekev as m_pvmekev
from crm import volteo_umowa_mapa_roz as m_roz
from crm.volteo_umowa_render import SZABLONY

try:
	from pypdf import PdfReader

	_PYPDF = True
except ImportError:
	_PYPDF = False

# klucz, plik, liczba stron, pierwsze 16 znaków SHA-256
OCZEKIWANE = (
	("PV", "umowa_pv.pdf", 14, "1dd2cf9a810d71a6"),
	("PV_K", "umowa_pv_k.pdf", 17, "7b1dfbef6b78f61e"),
	("PVME", "umowa_pv_me.pdf", 18, "e2fcd4503cc44575"),
	("PVME_K", "umowa_pv_me_k.pdf", 22, "750ac43143f042b3"),
	("PVME_EV", "umowa_pv_me_ev.pdf", 22, "645bca70bce4046e"),
	("PVME_K_EV", "umowa_pv_me_k_ev.pdf", 25, "4bad7ce370d8398a"),
	("ME", "umowa_me.pdf", 16, "de2d526db3ea8a9f"),
	("ME_K", "umowa_me_k.pdf", 19, "67a9912a37320b6b"),
	("ME_EV", "umowa_me_ev.pdf", 19, "b486ac44b9bb9b91"),
	("ME_K_EV", "umowa_me_k_ev.pdf", 22, "0a5d5fe8cd19119d"),
	("ROZ", "umowa_rozbudowa.pdf", 17, "6cd50df2b3c8b7e5"),
)

# klucz -> (SHA, LICZBA_STRON) z modułów map
STALE = {
	"PV": (m_pv.SHA256_SZABLONU_PV, m_pv.LICZBA_STRON_PV),
	"PV_K": (m_pvk.SHA256_SZABLONU_PVK, m_pvk.LICZBA_STRON_PVK),
	"PVME": (m_pvme.SHA256_SZABLONU, m_pvme.LICZBA_STRON_PVME),
	"PVME_K": (m_pvmek.SHA256_SZABLONU_PVMEK, m_pvmek.LICZBA_STRON_PVMEK),
	"PVME_EV": (m_pvmeev.SHA256_SZABLONU_PVMEEV, m_pvmeev.LICZBA_STRON_PVMEEV),
	"PVME_K_EV": (m_pvmekev.SHA256_SZABLONU_PVMEKEV, m_pvmekev.LICZBA_STRON_PVMEKEV),
	"ME": (m_me.SHA256_SZABLONU_ME, m_me.LICZBA_STRON_ME),
	"ME_K": (m_mek.SHA256_SZABLONU_MEK, m_mek.LICZBA_STRON_MEK),
	"ME_EV": (m_meev.SHA256_SZABLONU_MEEV, m_meev.LICZBA_STRON_MEEV),
	"ME_K_EV": (m_mekev.SHA256_SZABLONU_MEKEV, m_mekev.LICZBA_STRON_MEKEV),
	"ROZ": (m_roz.SHA256_SZABLONU_ROZ, m_roz.LICZBA_STRON_ROZ),
}

KATALOG = Path(__file__).resolve().parent / "szablony"


def _sha(nazwa: str) -> str:
	return hashlib.sha256((KATALOG / nazwa).read_bytes()).hexdigest()


class TestSzablonyNowe(unittest.TestCase):
	def test_plik_istnieje(self) -> None:
		for klucz, plik, _n, _h in OCZEKIWANE:
			with self.subTest(klucz=klucz):
				self.assertTrue((KATALOG / plik).is_file())

	def test_sha_zgodne_z_tabela(self) -> None:
		for klucz, plik, _n, h in OCZEKIWANE:
			with self.subTest(klucz=klucz):
				self.assertTrue(_sha(plik).startswith(h))

	def test_sha_zgodne_ze_stala_mapy(self) -> None:
		for klucz, plik, _n, _h in OCZEKIWANE:
			with self.subTest(klucz=klucz):
				self.assertEqual(_sha(plik), STALE[klucz][0])

	def test_liczba_stron_stala_i_tabela(self) -> None:
		for klucz, _plik, n, _h in OCZEKIWANE:
			with self.subTest(klucz=klucz):
				self.assertEqual(STALE[klucz][1], n)

	@unittest.skipUnless(_PYPDF, "pypdf nie jest zainstalowany")
	def test_liczba_stron_w_pliku(self) -> None:
		for klucz, plik, n, _h in OCZEKIWANE:
			with self.subTest(klucz=klucz):
				self.assertEqual(len(PdfReader(str(KATALOG / plik)).pages), n)

	def test_klucze_dwuosobowe_z_cecha_niezarejestrowane(self) -> None:
		for klucz in ("PV_K_2", "PVME_K_2", "PVME_EV_2", "PVME_K_EV_2", "ME_K_2", "ME_EV_2", "ME_K_EV_2", "ROZ_2"):
			with self.subTest(klucz=klucz):
				self.assertNotIn(klucz, SZABLONY)

	def test_szablony_podwojna_bez_zmian(self) -> None:
		self.assertEqual(_sha("umowa_pv_podwojna.pdf"), m_pv2.SHA256_SZABLONU_PV2)
		self.assertEqual(_sha("umowa_me_podwojna.pdf"), m_me2.SHA256_SZABLONU_ME2)
		self.assertEqual(_sha("umowa_pv_me_podwojna.pdf"), m_pvme2.SHA256_SZABLONU_PVME2)


if __name__ == "__main__":
	unittest.main()
