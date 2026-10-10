# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Mapa współrzędnych do nakładania danych umowy na oryginalny plik PDF -
wariant jednoosobowy: PV z klimatyzacją (K), `crm/szablony/umowa_pv_k.pdf`.

Plik źródłowy wzoru: `Umowa PV + K ProEnergy - 06.10.2026-2.pdf` (ostateczny wzór z 06.10.2026, b69).

SZKIELET: mapa `MAPA_PVK` jest CELOWO PUSTA do czasu pomiaru współrzędnych od
zera w chunku U2. Pusta mapa jest bezpieczna: rejestr `SZABLONY` i API
(chunki U3/U4) odmawiają renderu dla pustej mapy, więc nie da się wygenerować
umowy bez naniesionych danych. Konwencje pomiaru (układ współrzędnych
`y_reportlab = 842 - y_od_gory`, offsety tekstu na podkreśleniu, kratek i
komórek tabel) opisano w nagłówku `crm/volteo_umowa_mapa.py`; wzorzec pustego
szkieletu: `crm/volteo_umowa_mapa_pv2.py` (b61). Generator PDF-u sprawdza sumę
SHA-256 pliku względem `SHA256_SZABLONU_PVK` przed użyciem mapy.
"""

from crm.volteo_umowa_mapa import Pole

SHA256_SZABLONU_PVK: str = "7b1dfbef6b78f61eb1d4e2502bdf09cedea3d8a98c7f816acaee3cfbe32e2e58"
"""SHA-256 pliku `crm/szablony/umowa_pv_k.pdf`, policzone na pliku w repo."""

LICZBA_STRON_PVK: int = 17
"""Liczba stron pliku, zweryfikowana `pdfinfo` i `pypdf`."""

MAPA_PVK: tuple[Pole, ...] = ()
"""Pusta do czasu pomiaru (chunk U2)."""
