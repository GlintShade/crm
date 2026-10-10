# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: ME z ładowarką EV (Ł), `crm/szablony/umowa_me_ev.pdf`.

Plik źródłowy wzoru: `Umowa ME + Ł ProEnergy - 06.10.2026.pdf` (ostateczny wzór z 06.10.2026, b69).

SZKIELET: mapa `MAPA_MEEV` jest CELOWO PUSTA do czasu pomiaru współrzędnych od
zera w chunku U2. Pusta mapa jest bezpieczna: rejestr `SZABLONY` i API
(chunki U3/U4) odmawiają renderu dla pustej mapy, więc nie da się wygenerować
umowy bez naniesionych danych. Konwencje pomiaru (układ współrzędnych
`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkreśleniu, kratek i
komórek tabel) opisano w nagłówku `crm/volteo_umowa_mapa.py`; wzorzec pustego
szkieletu: `crm/volteo_umowa_mapa_pv2.py` (b61). Generator PDF-u sprawdza sumę
SHA-256 pliku względem `SHA256_SZABLONU_MEEV` przed użyciem mapy.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_MEEV: str = "b486ac44b9bb9b91e67c44b9ccc3cbaeb7609c51d9a1b735f0002a8bd3d42bec"
"""SHA-256 pliku `crm/szablony/umowa_me_ev.pdf`, policzone na pliku w repo."""

LICZBA_STRON_MEEV: int = 19
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_MEEV: tuple[Pole, ...] = ()
"""Pusta do czasu pomiaru (chunk U2)."""
