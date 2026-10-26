# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""
Wlasny limiter zapytan zamiast `frappe.rate_limiter.rate_limit` (ops#303)
======================================================================

Dekorator ma te sama nazwe i sygnature `rate_limit(limit, seconds)`, wiec w
plikach API zmienia sie tylko linia importu.

Dlaczego nie `frappe.rate_limiter`: Frappe robi `GET`, potem `SETEX` tylko gdy
klucza brak, potem `INCRBY`. Gdy klucz wygasnie miedzy `GET` a `INCRBY`,
`INCRBY` tworzy go na nowo BEZ TTL i licznik rosnie bez konca (na produkcji
10 z 11 licznikow Autenti mialo TTL -1, uzytkownik dostawal HTTP 429 na stale).
Odpytywanie co 30 s przy oknie 60 s trafia w ten wyscig systematycznie.

Tutaj: `INCR` i `EXPIRE(seconds * 2)` zawsze razem w jednym pipeline, bez
warunku, a klucz zawiera numer okna kalendarzowego (`crm.volteo_limit_zadan`).
Zgubiony TTL zostawia co najwyzej maly klucz starego okna, ktory nigdy nie
blokuje kolejnego.

Uwaga: ten modul nie moze importowac niczego z `crm.api` (import cykliczny,
`crm/api/__init__.py` importuje stad).
"""

from datetime import datetime, timezone
from functools import wraps

import frappe
from frappe import _

from crm.volteo_limit_zadan import klucz_limitu, limit_przekroczony


def rate_limit(limit: int, seconds: int):
	def dekorator(fn):
		metoda = f"{fn.__module__}.{fn.__name__}"

		@wraps(fn)
		def opakowanie(*args, **kwargs):
			# Bez zadania HTTP (bench console, job) bez limitu, jak we Frappe.
			if not getattr(frappe.local, "request", None):
				return fn(*args, **kwargs)

			podmiot = frappe.session.user
			if not podmiot or podmiot == "Guest":
				podmiot = getattr(frappe.local, "request_ip", None) or "nieznany"

			klucz = klucz_limitu(metoda, podmiot, datetime.now(timezone.utc), seconds)
			potok = frappe.cache().pipeline()
			potok.incr(klucz)
			potok.expire(klucz, seconds * 2)
			licznik = int(potok.execute()[0])

			if limit_przekroczony(licznik, limit):
				frappe.throw(
					_("Zbyt wiele żądań. Spróbuj ponownie za chwilę."),
					frappe.RateLimitExceededError,
				)
			return fn(*args, **kwargs)

		return opakowanie

	return dekorator
