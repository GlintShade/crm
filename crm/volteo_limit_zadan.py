# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
Klucz i prog wlasnego limitu zapytan (ops#303), bez `frappe`.

Adapter `crm/api/limit_zadan.py` uzywa tych funkcji do zliczania zapytan w Redis.
Okno jest STALE i kalendarzowe: numer okna to `int(timestamp) // okno_s`, wiec
kazde okno ma wlasny klucz. Dzieki temu zgubiony TTL (wyscig GET/SETEX/INCRBY w
`frappe.rate_limiter`) zostawia co najwyzej maly, nieuzywany juz klucz starego
okna i nigdy nie blokuje uzytkownika na stale.
"""

from datetime import datetime


def klucz_limitu(metoda: str, podmiot: str, teraz: datetime, okno_s: int) -> str:
	"""Klucz licznika: metoda, podmiot (uzytkownik lub IP) i numer okna kalendarzowego."""
	nr_okna = int(teraz.timestamp()) // okno_s
	return f"volteo:limit:{metoda}:{podmiot}:{nr_okna}"


def limit_przekroczony(licznik: int, limit: int) -> bool:
	"""True, gdy `licznik` (wlacznie z biezacym zadaniem) przekracza `limit`."""
	return licznik > limit
