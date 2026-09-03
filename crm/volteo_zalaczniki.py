"""Zmiana nazwy załącznika — logika bez importu frappe (testy: crm/test_volteo_zalaczniki.py).

Użytkownik edytuje tylko trzon nazwy pliku; rozszerzenie jest dokładane
automatycznie z obecnej nazwy, więc nie da się przez pomyłkę zmienić np.
".pdf" na coś innego ani go zgubić. Pliki generowane przez system (umowa,
formularz kredytowy) są wyłączone z edycji, bo `crm/api/umowa.py`,
`crm/api/kredyt.py` i `crm/integrations/autenti/api.py` wyszukują je PO
NAZWIE — zmiana nazwy pod spodem po cichu zerwałaby to wyszukiwanie.
"""

import os

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
