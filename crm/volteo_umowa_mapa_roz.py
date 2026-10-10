# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: Rozbudowa instalacji, `crm/szablony/umowa_rozbudowa.pdf`.

Plik źródłowy wzoru: `Umowa Rozbudowa ProEnergy - 06.10.2026-3.pdf` (ostateczny wzór z 06.10.2026, b69).

SZKIELET: mapa `MAPA_ROZ` jest CELOWO PUSTA do czasu pomiaru współrzędnych od
zera w chunku U2. Pusta mapa jest bezpieczna: rejestr `SZABLONY` i API
(chunki U3/U4) odmawiają renderu dla pustej mapy, więc nie da się wygenerować
umowy bez naniesionych danych. Konwencje pomiaru (układ współrzędnych
`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkreśleniu, kratek i
komórek tabel) opisano w nagłówku `crm/volteo_umowa_mapa.py`; wzorzec pustego
szkieletu: `crm/volteo_umowa_mapa_pv2.py` (b61). Generator PDF-u sprawdza sumę
SHA-256 pliku względem `SHA256_SZABLONU_ROZ` przed użyciem mapy.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_ROZ: str = "6cd50df2b3c8b7e56f16ed989102d8e1b24038446a6ce9080fc677aafc665eb5"
"""SHA-256 pliku `crm/szablony/umowa_rozbudowa.pdf`, policzone na pliku w repo."""

LICZBA_STRON_ROZ: int = 17
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_ROZ: tuple[Pole, ...] = ()
"""Pusta do czasu pomiaru (chunk U2)."""
