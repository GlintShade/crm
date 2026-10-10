# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa wspolrzednych do nakladania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Klimatyzacja, `crm/szablony/umowa_klimatyzacja.pdf`.

Plik zrodlowy wzoru: `Umowa Klimatyzacja ProEnergy - 09.10.2026.pdf` (wzor dostarczony przez CEO 2026-10-09,
b69, dogrywka chunka U1), A4, 12 stron.

STAN: szkielet. Mapa `MAPA_KL` jest CELOWO PUSTA do czasu pomiaru wspolrzednych od
zera narzedziem `ops/narzedzia/umowa-mapa-pomiar.py`. Pusta mapa jest zabezpieczona
bezpiecznikiem pustej mapy w rejestrze szablonow i w API: generowanie PDF dla tego
wzoru jest odrzucane, dopoki mapa nie zostanie zmierzona i zarejestrowana.
Konwencje ukladu (`y_reportlab = 842 - y_od_gory`, offsety tekstu, kratek i komorek
tabeli): naglowek `crm/volteo_umowa_mapa.py` oraz `crm/volteo_umowa_mapa_pv2.py`.

STRUKTURA WZORU (12 stron): bez pelnomocnictwa OSD; Zal. 1 urzadzenie; Zal. 2 i 3 zgody;
Zal. 4 RODO; Zal. 5 pouczenie i formularz odstapienia; Zal. 6 protokol odbioru.
Zal. 1 (urzadzenie): "Rodzaj klimatyzacji", "Moc klimatyzacji (kW)".

BEZPIECZNIK ZMIANY SZABLONU: generator sprawdza SHA-256 pliku wzgledem
`SHA256_SZABLONU_KL` i odmawia renderu przy niezgodnosci.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_KL: str = "3b688e43f36ca2ac7691414748781e29c36472c270d41dc3b1a6b23776053791"
"""SHA-256 pliku `crm/szablony/umowa_klimatyzacja.pdf`, policzone na pliku w repo."""

LICZBA_STRON_KL: int = 12
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_KL: tuple[Pole, ...] = ()
"""Pozycje mapy wzoru KL: CELOWO PUSTE do pomiaru."""
