# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: ME z klimatyzacją i ładowarką EV (K + Ł), `crm/szablony/umowa_me_k_ev.pdf`.

Plik źródłowy wzoru: `Umowa ME + K + Ł ProEnergy - 06.10.2026-2.pdf` (ostateczny wzór z 06.10.2026, b69).

SZKIELET: mapa `MAPA_MEKEV` jest CELOWO PUSTA do czasu pomiaru współrzędnych od
zera w chunku U2. Pusta mapa jest bezpieczna: rejestr `SZABLONY` i API
(chunki U3/U4) odmawiają renderu dla pustej mapy, więc nie da się wygenerować
umowy bez naniesionych danych. Konwencje pomiaru (układ współrzędnych
`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkreśleniu, kratek i
komórek tabel) opisano w nagłówku `crm/volteo_umowa_mapa.py`; wzorzec pustego
szkieletu: `crm/volteo_umowa_mapa_pv2.py` (b61). Generator PDF-u sprawdza sumę
SHA-256 pliku względem `SHA256_SZABLONU_MEKEV` przed użyciem mapy.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_MEKEV: str = "0a5d5fe8cd19119d8320fd5079d6994d62b7306f0da324cef2364efbc1a7a1eb"
"""SHA-256 pliku `crm/szablony/umowa_me_k_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_MEKEV: int = 22
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_MEKEV: tuple[Pole, ...] = ()
"""Pusta do czasu pomiaru (chunk U2)."""
