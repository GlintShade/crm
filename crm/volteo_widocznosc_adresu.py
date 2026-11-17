"""
Widocznosc dokumentu Address (ops#376): czysta skladnia SQL, bez `import frappe`.

Adres jest widoczny, gdy: (a) wskazuje go widoczny klient (`Contact.address`),
(b) ma wiersz Dynamic Link do widocznego rekordu, (c) ma wiersz Dynamic Link
do typu, ktory nie jest zawezony dla tego uzytkownika, albo (d) jest wlasny
i jeszcze z niczym niepowiazany (przeplyw nowego adresu: najpierw Address,
potem zapis kontaktu).
"""

# Typy uprawnien, ktorych nie zawezamy (tworzenie adresu jest zawsze dozwolone).
PTYPY_BEZ_OGRANICZEN = frozenset({"create"})


def literal_sql(wartosc: str) -> str:
	"""Literal SQL w apostrofach z ucieczka; odrzuca znaki niebezpieczne."""
	if "%" in wartosc or "\x00" in wartosc or "\n" in wartosc or "\r" in wartosc:
		raise ValueError("Niedozwolony znak w literale SQL.")
	return "'" + wartosc.replace("\\", "\\\\").replace("'", "\\'") + "'"


def warunek_adresu(user: str, warunki_typow: dict[str, str]) -> str:
	"""Jedno wyrazenie w nawiasach: OR czterech galezi widocznosci adresu."""
	galezie = []

	# a. adres wskazany przez widocznego klienta
	kontakt = "SELECT `address` FROM `tabContact` WHERE ifnull(`address`,'') != ''"
	if "Contact" in warunki_typow:
		kontakt += f" AND ({warunki_typow['Contact']})"
	galezie.append(f"`tabAddress`.`name` IN ({kontakt})")

	# b. Dynamic Link do widocznego rekordu
	for typ in sorted(warunki_typow):
		galezie.append(
			"`tabAddress`.`name` IN (SELECT `parent` FROM `tabDynamic Link` "
			f"WHERE `parenttype` = 'Address' AND `link_doctype` = {literal_sql(typ)} "
			f"AND `link_name` IN (SELECT `name` FROM `tab{typ}` WHERE ({warunki_typow[typ]})))"
		)

	# c. Dynamic Link do typu niezawezonego
	c = (
		"`tabAddress`.`name` IN (SELECT `parent` FROM `tabDynamic Link` "
		"WHERE `parenttype` = 'Address' AND ifnull(`link_doctype`,'') != ''"
	)
	if warunki_typow:
		lista = ", ".join(literal_sql(t) for t in sorted(warunki_typow))
		c += f" AND `link_doctype` NOT IN ({lista})"
	galezie.append(c + ")")

	# d. wlasny adres jeszcze z niczym niepowiazany
	galezie.append(
		f"(`tabAddress`.`owner` = {literal_sql(user)} "
		"AND `tabAddress`.`name` NOT IN (SELECT `parent` FROM `tabDynamic Link` WHERE `parenttype` = 'Address') "
		"AND `tabAddress`.`name` NOT IN (SELECT `address` FROM `tabContact` WHERE ifnull(`address`,'') != ''))"
	)

	wynik = "(" + " OR ".join(galezie) + ")"
	if "%" in wynik:
		raise ValueError("Wygenerowany warunek zawiera znak procenta.")
	return wynik
