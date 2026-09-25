# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Reguly kasowania rekordow CRM: kto wolno usunac ktory doctype, oraz kiedy
kaskadowe usuniecie szansy (`CRM Deal`) trzeba zablokowac.

Moduł celowo nie importuje ``frappe``: to jedyny sposob, zeby dalo sie go
przetestowac lokalnie (na tej maszynie ``frappe`` nie jest instalowalne).
Cala logika zalezna od frameworka (odczyt rol, zapytania do bazy, throw)
mieszka w ``crm.permissions.delete_lockdown`` i ``crm.api.doc``, ktore
importuja stale i funkcje stad.

Zasada: backoffice (`Volteo Backend`) jest jedynym wyjatkiem od reguly
"tylko admin usuwa", moze usuwac WYLACZNIE szanse (`CRM Deal`), po silnym
ostrzezeniu po stronie frontu (`frontend/src/utils/usuwanieSzansy.js`).
Pozostale zablokowane doctype'y (`CRM Lead`, `Contact`, `FCRM Note`,
`CRM Task`, `CRM Organization`) zostaja admin-only.
"""

ROLE_ADMIN_USUWANIA: frozenset[str] = frozenset({"System Manager", "Volteo Core Admin"})
"""Role, ktore moga usunac dowolny zablokowany doctype, niezaleznie od statusu."""

ROLE_BACKOFFICE_USUWANIA: frozenset[str] = frozenset({"Volteo Backend"})
"""Role, ktore moga usunac WYLACZNIE doctype'y z `DOCTYPY_BACKOFFICE`."""

DOCTYPY_ZABLOKOWANE: frozenset[str] = frozenset(
	{
		"CRM Deal",
		"CRM Lead",
		"FCRM Note",
		"CRM Task",
		"CRM Organization",
		"Contact",
	}
)
"""Doctype'y, na ktorych `delete` jest domyslnie zarezerwowany dla admina."""

DOCTYPY_BACKOFFICE: frozenset[str] = frozenset({"CRM Deal"})
"""Podzbior `DOCTYPY_ZABLOKOWANE`, ktory backoffice (Volteo Backend) rowniez moze usuwac."""

AUTENTI_STATUSY_BLOKADY: frozenset[str] = frozenset({"Wysyłanie", "Wysłana", "Podpisana"})
"""Statusy `autenti_status` na `Volteo Umowa` / `Volteo Kredyt`, ktore blokuja usuniecie
szansy dla kazdego (takze admina), dokument jest juz wyslany albo podpisany."""

OFERTA_STATUSY_BLOKADY: frozenset[str] = frozenset({"Wysłana do podpisu", "Podpisana"})
"""Statusy `status` na `Volteo Oferta`, ktore blokuja usuniecie szansy dla kazdego."""

AUDYT_STATUS_ZATWIERDZONY = "Zatwierdzony"
"""Status `Volteo Audyt`, powyzej ktorego usuniecie szansy zostaje wylacznie dla admina."""


def czy_wolno_usunac(doctype: str, roles: set[str] | frozenset[str], user: str) -> bool:
	"""Czy `user` (z rolami `roles`) moze usunac dokument typu `doctype`.

	Nie sprawdza samego DocPerm/permlevel, to robi wolajacy osobno
	(`frappe.has_permission`); ta bramka tylko zawęza, nigdy nie rozszerza
	uprawnien ponad to, co da DocPerm.
	"""
	if user == "Administrator":
		return True
	if roles & ROLE_ADMIN_USUWANIA:
		return True
	if doctype not in DOCTYPY_ZABLOKOWANE:
		return True
	if (roles & ROLE_BACKOFFICE_USUWANIA) and doctype in DOCTYPY_BACKOFFICE:
		return True
	return False


def powod_blokady_kaskady(
	wiersze: list[tuple[str, str, str | None]], admin: bool
) -> str | None:
	"""Zwraca powod odmowy usuniecia szansy, albo `None` gdy nic nie blokuje.

	`wiersze` to lista krotek `(doctype, name, status)` dla dokumentow
	kaskady powiazanych z usuwana szansa (status `None`, gdy dany doctype
	go nie ma / nie jest sprawdzany, patrz `Volteo Audyt CP` ponizej).
	Wygrywa pierwszy pasujacy wiersz (kolejnosc `wiersze` ma znaczenie).

	Dwie kategorie blokad:
	  * status podpisu (`Volteo Umowa` / `Volteo Kredyt` / `Volteo Oferta`)
	    blokuje KAZDEGO, takze admina: usuniecie skasowaloby prawnie
	    wiazacy dokument;
	  * audyt specjalny CP (`Volteo Audyt CP`, dowolny wiersz) albo
	    zatwierdzony audyt (`Volteo Audyt`) blokuje tylko nie-admina.
	"""
	for doctype, name, status in wiersze:
		if doctype in ("Volteo Umowa", "Volteo Kredyt") and status in AUTENTI_STATUSY_BLOKADY:
			return (
				f'Powiązany dokument {doctype} {name} ma status podpisu „{status}”, '
				"podpisanych lub wysłanych do podpisu dokumentów nie wolno usuwać."
			)
		if doctype == "Volteo Oferta" and status in OFERTA_STATUSY_BLOKADY:
			return (
				f'Powiązany dokument {doctype} {name} ma status podpisu „{status}”, '
				"podpisanych lub wysłanych do podpisu dokumentów nie wolno usuwać."
			)
		if not admin:
			if doctype == "Volteo Audyt CP":
				return f"Szansa ma audyt specjalny CP {name}; taką szansę może usunąć tylko administrator."
			if doctype == "Volteo Audyt" and status == AUDYT_STATUS_ZATWIERDZONY:
				return f"Szansa ma zatwierdzony audyt {name}; taką szansę może usunąć tylko administrator."

	return None
