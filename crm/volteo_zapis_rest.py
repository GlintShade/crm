# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta (bez frappe) decyzja, czy zadanie HTTP jest zapisem przez REST v1 (ops#180).

REST v1 `PUT`/`POST /api/resource/<doctype>` zwraca dokument bez filtra pol
permlevel, wiec dla zwyklych uzytkownikow jest blokowane w
`crm.api.volteo_zapis_guard.before_request`. REST v2 (`/api/v2/...`) filtruje
poprawnie i nie jest blokowany.
"""

PREFIKSY_REST_V1 = ("/api/resource/", "/api/v1/resource/")
METODY_ZAPISU = frozenset({"PUT", "POST"})


def czy_zapis_rest(metoda: str, sciezka: str) -> bool:
	"""True, gdy `metoda` to PUT/POST (bez wzgledu na wielkosc liter), a
	`sciezka` zaczyna sie od prefiksu REST v1."""
	if not metoda or not sciezka:
		return False
	if metoda.upper() not in METODY_ZAPISU:
		return False
	return sciezka.startswith(PREFIKSY_REST_V1)
