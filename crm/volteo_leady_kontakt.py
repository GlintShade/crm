# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Pola robocze CC na leadzie: czas do pierwszego kontaktu i proby kontaktu.

Modul celowo nie importuje ``frappe``: logike da sie wtedy przetestowac
lokalnie. `throw` mieszka w `CRMLead.validate()`.

- `CRM Lead.custom_czas_do_kontaktu` (Duration, sekundy): wpisywany recznie w
  formacie `gg:mm`, maksymalnie `24:00` (86400 s); 0/puste = nie wpisano.
- `CRM Lead.custom_proby_kontaktu` (Select "0".."5"): licznik prob polaczenia.

Frontendowe lustro formatowania i parsowania: `frontend/src/utils/czasKontaktu.js`.
"""

import re

MAKS_CZAS_DO_KONTAKTU_S: int = 24 * 3600
"""Gorna granica czasu do pierwszego kontaktu: 24:00."""

PROBY_KONTAKTU_OPCJE: tuple[str, ...] = ("0", "1", "2", "3", "4", "5")
"""Dozwolone wartosci Select `custom_proby_kontaktu`."""

_RE_GG_MM = re.compile(r"^(\d{1,3}):(\d{1,2})$")
_RE_CYFRY = re.compile(r"^\d+$")


def _na_liczbe(wartosc) -> float | None:
	"""Zamienia wejscie (liczba lub tekst z liczba) na liczbe; None gdy sie nie da."""
	if isinstance(wartosc, bool):
		return None
	if isinstance(wartosc, (int, float)):
		return wartosc
	try:
		return float(str(wartosc).strip())
	except (TypeError, ValueError):
		return None


def waliduj_czas_do_kontaktu(sekundy) -> str | None:
	"""None gdy wartosc jest poprawna, inaczej komunikat po polsku.

	`None`, ``0`` i ``""`` oznaczaja "nie wpisano" i zawsze sa poprawne.
	"""
	if sekundy is None or sekundy == "":
		return None
	liczba = _na_liczbe(sekundy)
	if liczba is None:
		return "Czas do pierwszego kontaktu musi być liczbą sekund."
	if liczba < 0:
		return "Czas do pierwszego kontaktu nie może być ujemny."
	if liczba > MAKS_CZAS_DO_KONTAKTU_S:
		return "Czas do pierwszego kontaktu nie może przekraczać 24:00."
	return None


def waliduj_proby_kontaktu(wartosc) -> str | None:
	"""None gdy wartosc jest poprawna (puste tez), inaczej komunikat po polsku."""
	if wartosc is None or wartosc == "":
		return None
	if isinstance(wartosc, bool):
		return "Próby kontaktu muszą być liczbą od 0 do 5."
	if isinstance(wartosc, float) and wartosc.is_integer():
		wartosc = int(wartosc)
	if str(wartosc).strip() not in PROBY_KONTAKTU_OPCJE:
		return "Próby kontaktu muszą być liczbą od 0 do 5."
	return None


def formatuj_gg_mm(sekundy) -> str:
	"""Sekundy na `HH:MM` (z zerami wiodacymi); "" dla 0/None/nieliczby."""
	liczba = _na_liczbe(sekundy)
	if not liczba or liczba <= 0:
		return ""
	minuty_lacznie = int(liczba // 60)
	return f"{minuty_lacznie // 60:02d}:{minuty_lacznie % 60:02d}"


def parsuj_gg_mm(tekst) -> int | None:
	"""Parsuje `H:MM`, `HH:MM`, `HHMM` (3-4 cyfry) lub `H`/`HH` (same godziny).

	Zwraca sekundy albo None dla wejscia nieparsowalnego (minuty musza byc
	0..59). Nie sprawdza gornej granicy 24:00, to robi walidator.
	"""
	if tekst is None:
		return None
	t = str(tekst).strip()
	if not t:
		return None
	m = _RE_GG_MM.match(t)
	if m:
		godziny, minuty = int(m.group(1)), int(m.group(2))
	elif _RE_CYFRY.match(t):
		if len(t) <= 2:
			godziny, minuty = int(t), 0
		elif len(t) <= 4:
			godziny, minuty = int(t[:-2]), int(t[-2:])
		else:
			return None
	else:
		return None
	if minuty > 59:
		return None
	return godziny * 3600 + minuty * 60
