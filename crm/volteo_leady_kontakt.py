# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Pola robocze CC na leadzie: czas do pierwszego kontaktu i proby kontaktu.

Modul celowo nie importuje ``frappe``: logike da sie wtedy przetestowac
lokalnie. `throw` mieszka w `CRMLead.validate()`.

- `CRM Lead.custom_czas_do_kontaktu` (Duration, sekundy): wpisywany recznie w
  formacie `gg:mm` (godziny 1 do 3 cyfr, bez gornej granicy biznesowej);
  0/puste = nie wpisano.
- `CRM Lead.custom_proby_kontaktu` (Select "0".."5"): licznik prob polaczenia.

Frontendowe lustro formatowania i parsowania: `frontend/src/utils/czasKontaktu.js`.

Zadanie H (2026-11-05): `czy_uzupelnic_czas_kontaktu`/`sekundy_do_pierwszego_kontaktu`
nizej niosa czysta logike automatycznego uzupelniania `custom_czas_do_kontaktu`
z PIERWSZEJ notatki (komentarza) CC/backoffice na leadzie, gdy pole jest jeszcze
puste/0. Warstwe frappe-owa (hook `Comment.after_insert`, odczyt reguly
`Volteo Automatyzacja`, zapis pola, slad w Aktywnosci) niesie
`crm/api/czas_kontaktu.py`.
"""

import datetime
import re

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
	0..59). Gornej granicy nie ma (limit 24:00 zdjety, ops#319).
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


ROLE_AUTOMATYCZNEGO_CZASU: tuple[str, ...] = ("Volteo Call Center", "Volteo Backend")
"""Role autora notatki (komentarza), ktorych PIERWSZA notatka na leadzie moze
automatycznie uzupelnic `custom_czas_do_kontaktu` (Zadanie H, decyzja
wlasciciela 2026-11-05) - wszystkie inne role (w tym Administrator/System
Manager bez ktorejs z tych dwoch rol) nie uruchamiaja automatyzacji."""


def czy_uzupelnic_czas_kontaktu(obecna_wartosc, role_autora, wlaczona: bool) -> bool:
	"""Czy nowa notatka (komentarz) na leadzie ma automatycznie uzupelnic
	`custom_czas_do_kontaktu`.

	`obecna_wartosc` to DZISIEJSZA wartosc pola (sekundy, dowolny typ przyjmowany
	przez `waliduj_czas_do_kontaktu`): puste/0 oznacza "jeszcze nie wpisano" i
	jest jedynym przypadkiem, kiedy automatyzacja moze zadzialac - juz wypelnione
	pole (reczny wpis albo wczesniejsza notatka) nigdy nie jest nadpisywane.

	`role_autora` to role autora notatki (dowolny iterable stringow, np.
	`frappe.get_roles(user)`) - wymagana czesc wspolna z `ROLE_AUTOMATYCZNEGO_CZASU`.

	`wlaczona` to flaga reguly automatyzacji `Volteo Automatyzacja` (klucz
	`czas_kontaktu_z_notatki`) juz rozstrzygnieta przez wolajacego (brak wiersza
	w bazie ma byc tam potraktowany jako `True` - domyslnie wlaczona).
	"""
	if not wlaczona:
		return False
	if _na_liczbe(obecna_wartosc):
		return False
	if not set(role_autora or ()) & set(ROLE_AUTOMATYCZNEGO_CZASU):
		return False
	return True


def _parsuj_creation_kontaktu(creation) -> datetime.datetime:
	"""Parsuje `creation` na `datetime.datetime` - akceptuje `datetime.datetime`
	albo string ISO `"YYYY-MM-DD HH:MM:SS"` / `"YYYY-MM-DD HH:MM:SS.ffffff"`."""
	if isinstance(creation, datetime.datetime):
		return creation
	for wzorzec in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
		try:
			return datetime.datetime.strptime(str(creation), wzorzec)
		except (TypeError, ValueError):
			continue
	raise ValueError(f"Nieobslugiwany format creation: {creation!r}")


def sekundy_do_pierwszego_kontaktu(creation_leada, creation_notatki) -> int:
	"""Liczba sekund od utworzenia leada (`CRM Lead.creation`) do utworzenia
	notatki (`Comment.creation`), zaokraglona W DOL do pelnej minuty (pole jest
	wyswietlane jako `gg:mm`, patrz `formatuj_gg_mm`), minimum 0 (roznica ujemna,
	np. zegar/kolejnosc danych niespojne, nigdy nie daje wartosci ujemnej).

	Oba argumenty przyjmuja `datetime.datetime` albo string
	`"YYYY-MM-DD HH:MM:SS"` / `"YYYY-MM-DD HH:MM:SS.ffffff"`.
	"""
	poczatek = _parsuj_creation_kontaktu(creation_leada)
	koniec = _parsuj_creation_kontaktu(creation_notatki)
	roznica_s = (koniec - poczatek).total_seconds()
	if roznica_s <= 0:
		return 0
	return (int(roznica_s) // 60) * 60
