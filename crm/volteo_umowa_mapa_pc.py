# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Pompa ciepla, `crm/szablony/umowa_pompa_ciepla.pdf`.

Plik zrodlowy wzoru: `Umowa PC ProEnergy - 09.10.2026.pdf` (wzor dostarczony przez CEO 2026-10-09,
b69, dogrywka chunka U1), A4, 12 stron.

STAN: szkielet. Mapa `MAPA_PC` jest CELOWO PUSTA do czasu pomiaru wspolrzednych od
zera narzedziem `ops/narzedzia/umowa-mapa-pomiar.py`. Pusta mapa jest zabezpieczona
bezpiecznikiem pustej mapy w rejestrze szablonow i w API: generowanie PDF dla tego
wzoru jest odrzucane, dopoki mapa nie zostanie zmierzona i zarejestrowana.
Konwencje ukladu (`y_reportlab = 842 - y_od_gory`, offsety tekstu, kratek i komorek
tabeli): naglowek `crm/volteo_umowa_mapa.py` oraz `crm/volteo_umowa_mapa_pv2.py`.

STRUKTURA WZORU (12 stron): bez pelnomocnictwa OSD; Zal. 1 urzadzenie; Zal. 2 i 3 zgody;
Zal. 4 RODO; Zal. 5 pouczenie i formularz odstapienia; Zal. 6 protokol odbioru.
Zal. 1 (urzadzenie): Producent, Typ, Moc, Zasobnik CWU (NIE / TAK 200 l / TAK 300 l),
  grzejniki 600x600 / 800 / 1000 / 1200 / 1600 (ilosc szt.). Uwaga: to NIE jest umowa
  Czyste Powietrze (`umowa_cp_obsluga_dotacji.pdf`, kod CP).

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_PC` i odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PC: str = "6050d38c01764225d7387093002b25ee6f177a251ae2114a8ac839f8f665724a"
"""SHA-256 pliku `crm/szablony/umowa_pompa_ciepla.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PC: int = 12
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_PC: tuple[Pole, ...] = ()
"""Pozycje mapy wzoru PC: CELOWO PUSTE do pomiaru."""
