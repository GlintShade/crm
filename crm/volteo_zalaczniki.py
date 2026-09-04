"""Zmiana nazwy załącznika — logika bez importu frappe (testy: crm/test_volteo_zalaczniki.py).

Użytkownik edytuje tylko trzon nazwy pliku; rozszerzenie jest dokładane
automatycznie z obecnej nazwy, więc nie da się przez pomyłkę zmienić np.
".pdf" na coś innego ani go zgubić. Pliki generowane przez system (umowa,
formularz kredytowy) są wyłączone z edycji, bo `crm/api/umowa.py`,
`crm/api/kredyt.py` i `crm/integrations/autenti/api.py` wyszukują je PO
NAZWIE — zmiana nazwy pod spodem po cichu zerwałaby to wyszukiwanie.

Moduł niesie DWA rozpoznawacze pliku systemowego: `czy_plik_systemowy` (dla
JEDNEJ, konkretnej szansy — używane przy wyszukiwaniu i przy blokadzie zmiany
nazwy plików TEJ szansy) i `czy_nazwa_systemowa` (dla wzorca nazwy DOWOLNEJ
szansy — używane przy rezerwacji nazw, żeby nie dało się podszyć pod umowę
INNEJ szansy niż ta, pod którą plik akurat się wgrywa; zob. docstring
`czy_nazwa_systemowa` niżej i issue GlintShade/proenergy-crm-ops#77).
"""

import os
import re

from crm.integrations.autenti.logika import nazwa_pliku_umowy, prefiks_pliku_kredytu

MAKS_DLUGOSC = 140
"""Maksymalna dopuszczalna długość pełnej nazwy pliku (trzon + rozszerzenie)."""

ZAKAZANE = set("/\\")
"""Znaki niedozwolone w trzonie nazwy — ukośniki mogłyby zostać odczytane jako
separator ścieżki gdziekolwiek dalej nazwa pliku trafia do systemu plików."""


def rozszerzenie(nazwa: str) -> str:
	"""Rozszerzenie (z kropką) obecnej nazwy pliku, albo pusty string gdy go brak."""
	return os.path.splitext(nazwa or "")[1]


def nowa_nazwa_pliku(stara_nazwa: str, nowy_trzon: str) -> str:
	"""Składa nową nazwę pliku z użytkownikowego trzonu i rozszerzenia starej nazwy.

	Trzon jest obcinany z białych znaków na brzegach. Pusty/samo-białoznakowy
	trzon, trzon zawierający ukośnik/wsteczny ukośnik albo znak sterujący
	(`ord < 32`), oraz wynikowa nazwa dłuższa niż `MAKS_DLUGOSC` znaków — każdy
	z tych przypadków podnosi `ValueError` z komunikatem po polsku, gotowym do
	pokazania użytkownikowi.
	"""
	trzon = (nowy_trzon or "").strip()
	if not trzon:
		raise ValueError("Nazwa pliku nie może być pusta.")
	if (ZAKAZANE & set(trzon)) or any(ord(znak) < 32 for znak in trzon):
		raise ValueError("Nazwa pliku nie może zawierać ukośników ani znaków sterujących.")
	nowa = trzon + rozszerzenie(stara_nazwa)
	if len(nowa) > MAKS_DLUGOSC:
		raise ValueError(f"Nazwa pliku może mieć najwyżej {MAKS_DLUGOSC} znaków.")
	return nowa


def czy_plik_systemowy(file_name: str, deal: str) -> bool:
	"""Czy `file_name` to plik wygenerowany przez system dla danej szansy
	(umowa albo formularz kredytowy) — takich plików nie wolno przemianować,
	bo są wyszukiwane po nazwie gdzie indziej (patrz docstring modułu).

	Rozpoznanie jest po prefiksie, nie po pełnej nazwie: obejmuje to zarówno
	niepodpisaną, jak i podpisaną wersję (`...-podpisana.pdf`/`...-podpisany.pdf`)
	oraz warianty ze znacznikiem czasu w nazwie.
	"""
	nazwa_umowy = nazwa_pliku_umowy(deal)
	prefiks_umowy = nazwa_umowy[: -len(".pdf")]
	prefiks_kredytu = prefiks_pliku_kredytu(deal)
	return (file_name or "").startswith((prefiks_umowy, prefiks_kredytu))


_WZORZEC_NAZWY_SYSTEMOWEJ = re.compile(
	r"^(Umowa|Formularz-kredytowy)-(PRO-[A-Z]{2,4}-\d{2}-\d{4,}|CRM-DEAL-\d{4}-\d+)"
)
"""Rozpoznaje prefiks nazwy pliku systemowego DOWOLNEJ szansy (nie tylko tej,
pod którą plik akurat jest podpięty) — patrz `czy_nazwa_systemowa` niżej.

Dwa formaty nazwy szansy, oba zdefiniowane w `crm/volteo_naming.py`:
- bieżący `PRO/<KOD>/<RR>/<NUMER>` (`format_deal_name`), z ukośnikami
  zamienionymi na myślniki w nazwie pliku -> `PRO-<KOD>-<RR>-<NUMER>`;
  `<KOD>` to jedna z wartości `UMOWA_CODES` (PV, PVME, ME, CP) albo
  `FALLBACK_CODE` ("XX") — wszystkie mieszczą się w 2–4 wielkich literach;
- legacy `CRM-DEAL-<RRRR>-<NNNNN>` sprzed b38 (np. `CRM-DEAL-2026-00016`).

Skompilowany raz na poziomie modułu, bez asercji końca (`$`) — tak samo jak
`czy_plik_systemowy`, dopasowanie samego PREFIKSU wystarcza: obejmuje warianty
ze znacznikiem czasu w nazwie (formularz kredytowy), sufiksem doklejonym przy
kolizji ścieżki na dysku (np. `e41034`) i sufiksem "-podpisana"/"-podpisany".
"""


def czy_nazwa_systemowa(file_name: str) -> bool:
	"""Czy `file_name` PASUJE DO WZORCA nazwy pliku systemowego (umowa albo
	formularz kredytowy) DOWOLNEJ szansy — w odróżnieniu od `czy_plik_systemowy`,
	który sprawdza dopasowanie do JEDNEJ, konkretnej, znanej z góry szansy.

	Ta funkcja istnieje, bo Frappe trzyma wszystkie prywatne pliki w JEDNYM
	katalogu na dysku (`/private/files/`), niezależnie od tego, pod jaki
	dokument (`attached_to_name`) są podpięte. Plik o nazwie pasującej do
	wzorca umowy szansy B, wgrany pod szansę A, nie przejdzie wyszukiwania
	`_pdf_umowy_plik` dla B (ono filtruje po `attached_to_name`) — ALE zajmie
	na dysku ścieżkę, której chce użyć prawdziwy generator umowy szansy B.
	`File.write_file` woła wtedy `generate_file_name`, które przy kolizji
	ścieżki dokleja losowy sufiks do nazwy NOWEGO pliku, więc prawdziwa umowa
	szansy B ląduje pod nazwą, jakiej `_pdf_umowy_plik` (dopasowanie po
	dokładnej nazwie) już nie znajdzie — wysyłka do Autenti pada z
	`komunikat_brak_pdf`, `pdf_exists` wychodzi `False`, a regeneracja PDF-u
	tego nie naprawia, bo kolizja powtarza się przy każdej kolejnej próbie.
	Zob. issue GlintShade/proenergy-crm-ops#77 (follow-up).

	Dlatego rezerwacja nazw systemowych (`crm.permissions.file_nazwy_systemowe`,
	`crm.api.volteo_zmien_nazwe_zalacznika`) musi odrzucać każdą nazwę pasującą
	do wzorca DOWOLNEJ szansy, nie tylko tej, pod którą plik akurat się wgrywa
	albo jest już podpięty.
	"""
	return bool(_WZORZEC_NAZWY_SYSTEMOWEJ.match(file_name or ""))
