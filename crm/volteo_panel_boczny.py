"""Panel boczny: czysta logika sekcji "Lost Reason" (frappe-free, ops#326).

Upstream wstawia do globalnego ukladu panelu boczna sekcje `lost_reason_section`
przy statusie Lost. Gdy uklad ma wlasna sekcje z `lost_reason`/`lost_notes`,
wstawienie dubluje karte, wiec w takim ukladzie sekcji upstream nie dodajemy
(a zabladzona usuwamy).
"""

SEKCJA_UPSTREAM = "lost_reason_section"
POLA_UTRATY = ("lost_reason", "lost_notes")


def _nazwy_pol(sekcja: dict) -> set:
	nazwy = set()
	for kolumna in sekcja.get("columns") or []:
		for pole in kolumna.get("fields") or []:
			nazwy.add(pole.get("fieldname") if isinstance(pole, dict) else pole)
	return nazwy


def _sekcja_upstream() -> dict:
	return {
		"name": SEKCJA_UPSTREAM,
		"label": "Lost Reason",
		"opened": True,
		"columns": [{"name": "lost_reason_column", "fields": list(POLA_UTRATY)}],
	}


def plan_sekcji_utraty(sekcje: list, czy_utracony: bool):
	"""Zwraca nowa liste sekcji albo None, gdy nic sie nie zmienia."""
	istnieje = any(s.get("name") == SEKCJA_UPSTREAM for s in sekcje)
	wlasna = any(
		s.get("name") != SEKCJA_UPSTREAM and _nazwy_pol(s) & set(POLA_UTRATY) for s in sekcje
	)

	if wlasna:
		if istnieje:
			return [s for s in sekcje if s.get("name") != SEKCJA_UPSTREAM]
		return None

	if czy_utracony and not istnieje:
		if sekcje and sekcje[0].get("name") == "contacts_section":
			return [*sekcje[:1], _sekcja_upstream(), *sekcje[1:]]
		return [_sekcja_upstream(), *sekcje]
	if not czy_utracony and istnieje:
		return [s for s in sekcje if s.get("name") != SEKCJA_UPSTREAM]
	return None
