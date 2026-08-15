# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Generator PDF-u formularza kredytowego: nakłada `crm.volteo_kredyt_pdf.zbuduj_kontekst_kredytu()`
na ORYGINALNY plik `crm/szablony/formularz_kredytowy.pdf`, dokładnie tym samym
mechanizmem co `crm/volteo_umowa_render.py` dla umów PV/ME/PVME — ten moduł
importuje i reużywa jego prywatną funkcję `_zloz_dokument()`, zamiast
duplikować logikę bezpiecznika sumy kontrolnej, klonowania stron i rysowania
warstwy (zob. komentarz przy imporcie niżej).

CELOWO POZA `SZABLONY`: rejestr `SZABLONY` w `volteo_umowa_render.py` jest
kluczowany kodami rodzaju umowy (`PV`/`PVME`/`ME`, te same co
`crm.volteo_naming.UMOWA_CODES`) i kontrakt-testowany przeciwko kontekstowi
UMOWY w `crm/test_volteo_umowa_mapa.py` — dopisanie tu wpisu z kluczem typu
"KREDYT" zepsułoby ten kontrakt (kod rodzaju umowy i "czy dołączyć formularz
kredytowy" to dwa niezależne pytania: formularz kredytowy jest JEDNYM
dokumentem wspólnym dla wszystkich trzech linii OZE, z własnym, osobnym
kontekstem — `KLUCZE_KONTEKSTU` w `crm/volteo_kredyt_pdf.py` — który nie ma
nic wspólnego z kluczami kontekstu umowy). Stąd osobny moduł z jednym,
pojedynczym szablonem (`SZABLON_KREDYT`) zamiast kolejnego wpisu w cudzym
rejestrze.
"""

from pathlib import Path
from typing import Any

from crm.volteo_kredyt_mapa import LICZBA_STRON_KREDYT, MAPA_KREDYT, SHA256_SZABLONU_KREDYT

# `_zloz_dokument` jest prywatną funkcją modułu `volteo_umowa_render` — zależność
# jest jawna i celowa (zob. docstring modułu wyżej oraz `_zloz_dokument()`
# w `volteo_umowa_render.py`, gdzie została wydzielona właśnie po to, żeby ten
# moduł mógł ją reużyć zamiast duplikować bezpiecznik sumy kontrolnej i pętlę
# renderowania stron).
from crm.volteo_umowa_render import Szablon, _zloz_dokument

SZABLON_KREDYT = Szablon("formularz_kredytowy.pdf", SHA256_SZABLONU_KREDYT, LICZBA_STRON_KREDYT, MAPA_KREDYT)
"""Jedyny szablon tego modułu — formularz kredytowy jest wspólny dla wszystkich
rodzajów umowy, więc (w odróżnieniu od `SZABLONY` w `volteo_umowa_render.py`)
nie ma tu rejestru kluczowanego kodem, tylko jedna stała."""


def sciezka_szablonu_kredytu() -> Path:
	"""Zwraca ścieżkę do wbudowanego szablonu PDF-u formularza kredytowego.

	Odpowiednik `sciezka_wbudowanego_szablonu()` z `volteo_umowa_render.py`,
	bez parametru `kod` (i bez odpowiadającego mu odrzucenia nieznanego kodu)
	— ten moduł ma dokładnie jeden szablon, więc nie ma czego wybierać."""
	return Path(__file__).resolve().parent / "szablony" / SZABLON_KREDYT.nazwa_pliku


def zloz_kredyt(kontekst: dict[str, Any], szablon_pdf: bytes) -> bytes:
	"""Nakłada `kontekst` (z `crm.volteo_kredyt_pdf.zbuduj_kontekst_kredytu()`) na
	`szablon_pdf` i zwraca gotowy PDF formularza kredytowego w bajtach.

	Cienka nakładka na `_zloz_dokument()` z `volteo_umowa_render.py` — zob.
	docstring tamtej funkcji dla pełnego opisu kroków (bezpiecznik sumy
	kontrolnej, klonowanie do `PdfWriter`, rysowanie warstwy per strona).
	Nie mutuje `kontekst` ani `szablon_pdf`."""
	opis = f"formularza kredytowego ({SZABLON_KREDYT.nazwa_pliku})"
	return _zloz_dokument(kontekst, szablon_pdf, SZABLON_KREDYT, opis)
