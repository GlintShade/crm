# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Generator PDF-u umowy obsługi dotacji Czyste Powietrze: nakłada
`crm.volteo_umowa_pdf_cp.zbuduj_kontekst_cp()` na ORYGINALNY plik
`crm/szablony/umowa_cp_obsluga_dotacji.pdf`, dokładnie tym samym mechanizmem co
`crm/volteo_umowa_render.py` dla umów PV/ME/PVME i `crm/volteo_kredyt_render.py`
dla formularza kredytowego — ten moduł importuje i reużywa prywatną funkcję
`_zloz_dokument()` z `volteo_umowa_render.py`, zamiast duplikować logikę
bezpiecznika sumy kontrolnej, klonowania stron i rysowania warstwy.

CELOWO POZA `SZABLONY`: dokładnie z tego samego powodu co `volteo_kredyt_render.py`
(zob. tamten docstring) — rejestr `SZABLONY` w `volteo_umowa_render.py` jest
kluczowany kodami rodzaju umowy PV/magazynu (`PV`/`PVME`/`ME`, plus warianty
`_2`) i kontrakt-testowany przeciwko kontekstowi TEJ rodziny umów. Umowa obsługi
dotacji CP jest zupełnym piątym dokumentem, ze swoim własnym szablonem i mapą
(`crm.volteo_umowa_mapa_cp`), niezależnym od rodzaju umowy PV/magazynu — stąd
osobny moduł z jednym, pojedynczym szablonem (`SZABLON_CP`), tak jak
`SZABLON_KREDYT` w `volteo_kredyt_render.py`."""

from pathlib import Path
from typing import Any

from crm.volteo_umowa_mapa_cp import LICZBA_STRON_CP, MAPA_CP, SHA256_SZABLONU_CP

# `_zloz_dokument` jest prywatną funkcją modułu `volteo_umowa_render` — zależność
# jest jawna i celowa (zob. docstring modułu wyżej oraz `_zloz_dokument()`
# w `volteo_umowa_render.py`, gdzie została wydzielona właśnie po to, żeby moduły
# takie jak ten mogły ją reużyć zamiast duplikować bezpiecznik sumy kontrolnej i
# pętlę renderowania stron — dokładnie ten sam wzorzec co `volteo_kredyt_render.py`).
from crm.volteo_umowa_render import Szablon, _zloz_dokument

SZABLON_CP = Szablon("umowa_cp_obsluga_dotacji.pdf", SHA256_SZABLONU_CP, LICZBA_STRON_CP, MAPA_CP)
"""Jedyny szablon tego modułu — umowa obsługi dotacji CP jest jednym, wspólnym
dokumentem (bez wariantów jak PV/ME/PVME), więc (w odróżnieniu od `SZABLONY` w
`volteo_umowa_render.py`) nie ma tu rejestru kluczowanego kodem, tylko jedna stała."""


def sciezka_szablonu_cp() -> Path:
	"""Zwraca ścieżkę do wbudowanego szablonu PDF-u umowy obsługi dotacji CP.

	Odpowiednik `sciezka_szablonu_kredytu()` z `volteo_kredyt_render.py` — ten
	moduł ma dokładnie jeden szablon, więc nie ma czego wybierać przez kod."""
	return Path(__file__).resolve().parent / "szablony" / SZABLON_CP.nazwa_pliku


def zloz_umowe_cp(kontekst: dict[str, Any], szablon_pdf: bytes) -> bytes:
	"""Nakłada `kontekst` (z `crm.volteo_umowa_pdf_cp.zbuduj_kontekst_cp()`) na
	`szablon_pdf` i zwraca gotowy PDF umowy obsługi dotacji CP w bajtach.

	Cienka nakładka na `_zloz_dokument()` z `volteo_umowa_render.py` — zob.
	docstring tamtej funkcji dla pełnego opisu kroków (bezpiecznik sumy
	kontrolnej, klonowanie do `PdfWriter`, rysowanie warstwy per strona).
	Nie mutuje `kontekst` ani `szablon_pdf`."""
	opis = f"umowy obsługi dotacji CP ({SZABLON_CP.nazwa_pliku})"
	return _zloz_dokument(kontekst, szablon_pdf, SZABLON_CP, opis)
