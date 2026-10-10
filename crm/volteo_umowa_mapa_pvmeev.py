# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: PV + ME z ładowarką EV (Ł), `crm/szablony/umowa_pv_me_ev.pdf`.

Plik źródłowy wzoru: `Umowa PV + ME + Ł ProEnergy - 06.10.2026.pdf` (ostateczny wzór z 06.10.2026, b69).

SZKIELET: mapa `MAPA_PVMEEV` jest CELOWO PUSTA do czasu pomiaru współrzędnych od
zera w chunku U2. Pusta mapa jest bezpieczna: rejestr `SZABLONY` i API
(chunki U3/U4) odmawiają renderu dla pustej mapy, więc nie da się wygenerować
umowy bez naniesionych danych. Konwencje pomiaru (układ współrzędnych
`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkreśleniu, kratek i
komórek tabel) opisano w nagłówku `crm/volteo_umowa_mapa.py`; wzorzec pustego
szkieletu: `crm/volteo_umowa_mapa_pv2.py` (b61). Generator PDF-u sprawdza sumę
SHA-256 pliku względem `SHA256_SZABLONU_PVMEEV` przed użyciem mapy.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVMEEV: str = "645bca70bce4046eb185d5d4d3372bc61c29a83e1258d263625d219a00e3c119"
"""SHA-256 pliku `crm/szablony/umowa_pv_me_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PVMEEV: int = 22
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_PVMEEV: tuple[Pole, ...] = ()
"""Pusta do czasu pomiaru (chunk U2)."""
