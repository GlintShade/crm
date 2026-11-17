# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Czysta (bez frappe) decyzja, czy zadanie HTTP jest zapisem przez REST (ops#180, ops#372).

REST v1 `PUT`/`POST /api/resource/<doctype>` zwraca dokument bez filtra pol
permlevel, wiec dla zwyklych uzytkownikow jest blokowane w
`crm.api.volteo_zapis_guard.before_request`. Od ops#372 to samo dotyczy REST v2:
`POST`/`PUT`/`PATCH /api/v2/document/...` (zwraca dokument bez filtra) oraz
kazdej metody na `/api/v2/method/run_doc_method` (dokleja dokument bez filtra).
Pozostale `/api/v2/method/...` nie sa blokowane.
"""

PREFIKSY_REST_V1 = ("/api/resource/", "/api/v1/resource/")
PREFIKS_DOKUMENTU_V2 = "/api/v2/document/"
SCIEZKA_RUN_DOC_METHOD_V2 = "/api/v2/method/run_doc_method"
METODY_ZAPISU = frozenset({"PUT", "POST"})
METODY_ZAPISU_V2 = frozenset({"PUT", "POST", "PATCH"})


def czy_zapis_rest(metoda: str, sciezka: str) -> bool:
	"""True dla zapisu przez REST: v1 (PUT/POST), v2 dokument (PUT/POST/PATCH)
	albo dowolna metoda na v2 `run_doc_method`. Metoda bez wzgledu na wielkosc
	liter."""
	if not metoda or not sciezka:
		return False
	metoda = metoda.upper()
	if sciezka.rstrip("/") == SCIEZKA_RUN_DOC_METHOD_V2:
		return True
	if sciezka.startswith(PREFIKS_DOKUMENTU_V2):
		return metoda in METODY_ZAPISU_V2
	if sciezka.startswith(PREFIKSY_REST_V1):
		return metoda in METODY_ZAPISU
	return False
