"""Nazwy plików generowanych przez system (PDF umowy, PDF formularza kredytowego)
są zarezerwowane -- żaden `File` o takiej nazwie nie może powstać poza jednym z
wyznaczonych generatorów (`crm.api.umowa`, `crm.api.kredyt`).

Bez tej blokady dowolny użytkownik z prawem zapisu na szansie (`CRM Deal`) mógł
wgrać spreparowany PDF pod nazwą pasującą do `czy_plik_systemowy()` -- np.
`Umowa-PRO-PV-26-1011.pdf` -- a `crm/integrations/autenti/api.py::_pdf_umowy_plik`
(dokładna nazwa, `limit=1`) mógł podpiąć do wysyłki do e-podpisu WŁAŚNIE ten
podrzucony plik zamiast prawdziwej umowy. Zob. issue ops#77.

Dlaczego `before_insert`, nie `validate`/`before_validate`: hook musi działać
WYŁĄCZNIE przy wstawianiu nowego wiersza. Późniejsze zapisy prawdziwych plików
systemowych (np. `File.handle_is_private_changed()` wołane z
`crm.permissions.file_privacy` przy zmianie `is_private`) nie mają jak podać
flagi `plik_systemowy()` -- gdyby ten hook wisiał też na `validate`, każdy
taki zapis wywalałby się z tym samym `ValidationError`, mimo że nazwy pliku
w ogóle nie zmienia. `before_insert` odcina tylko moment powstania wiersza,
więc żaden późniejszy, legalny zapis nie jest tym objęty.

Dlaczego bez żadnego znacznika na samym `File`: `czy_plik_systemowy()` już
dziś rozpoznaje plik systemowy PO NAZWIE (prefiks) -- to jest źródło prawdy,
z którego korzystają `crm/api/umowa.py`, `crm/api/kredyt.py` i
`crm/integrations/autenti/api.py` przy WYSZUKIWANIU takich plików. Dokładanie
osobnego pola/znacznika na `File` byłoby zmianą schematu (nowa kolumna, skrypt
ops, migracja istniejących wierszy) tylko po to, żeby zdublować informację,
która już jest jednoznacznie odczytywalna z nazwy -- ta blokada tylko
gwarantuje, że po jej wdrożeniu nazwę systemową może przyjąć WYŁĄCZNIE plik
wstawiony przez jeden z generatorów, więc istniejące wyszukiwania po nazwie
zostają poprawne bez zmian.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import frappe
from frappe import _

from crm.volteo_zalaczniki import czy_plik_systemowy

FLAGA = "volteo_plik_systemowy"
"""Klucz we `frappe.flags` -- ustawiany tylko wewnątrz `plik_systemowy()`,
na czas jednego `File.insert()` z generatora."""

KOMUNIKAT_ZAREZERWOWANA = "Ta nazwa jest zarezerwowana dla dokumentów generowanych przez system."


def blokuj_nazwy_systemowe(doc, method=None) -> None:
	"""`before_insert` na `File`: odrzuca insert, którego `file_name` pasuje do
	`czy_plik_systemowy()` dla szansy, pod którą plik jest podpinany -- chyba
	że insert idzie przez `plik_systemowy()` (czyli faktycznie jest jednym z
	generatorów).

	Dotyczy wyłącznie plików podpiętych pod `CRM Deal` -- `czy_plik_systemowy`
	sam jest zdefiniowany dla nazwy szansy, a wszystkie pozostałe generatory
	`File` w tym repo (komentarze, oświadczenie poufności, biblioteka
	dokumentów, podpisany PDF z Autenti) podpinają pliki pod inne doctype'y i
	nie są tym objęte.
	"""
	# before_insert biegnie PRZED validate() (Document.insert() woła
	# run_method("before_insert"), dopiero potem run_before_save_methods), więc
	# attached_to_name może tu jeszcze być puste -- zanim Frappe zdąży to
	# samo odrzucić. czy_plik_systemowy(nazwa, None) rzuciłoby AttributeError
	# (HTTP 500) zamiast zwykłej walidacji Frappe, więc odcinamy to tutaj.
	if doc.attached_to_doctype != "CRM Deal" or not doc.attached_to_name:
		return
	if not czy_plik_systemowy(doc.file_name or "", doc.attached_to_name):
		return
	if frappe.flags.get(FLAGA):
		return
	frappe.throw(_(KOMUNIKAT_ZAREZERWOWANA), frappe.ValidationError)


@contextmanager
def plik_systemowy() -> Iterator[None]:
	"""Kontekst, w którym `blokuj_nazwy_systemowe` przepuszcza insert -- do
	użycia WYŁĄCZNIE wewnątrz właściwych generatorów plików systemowych
	(`crm.api.umowa`, `crm.api.kredyt`), otaczając dokładnie wywołanie
	`File(...).insert(...)`, nic więcej.

	Zapamiętuje i przywraca POPRZEDNIĄ wartość flagi zamiast zerować ją na
	ślepo w `finally` -- gdyby ten kontekst kiedyś się zagnieździł (np. jeden
	generator wywołujący drugi w ramach tego samego wstawiania pliku),
	wyjście z wewnętrznego `with` nie może po cichu zdjąć ochrony jeszcze
	trwającej dla zewnętrznego.
	"""
	poprzednia = frappe.flags.get(FLAGA)
	frappe.flags[FLAGA] = True
	try:
		yield
	finally:
		frappe.flags[FLAGA] = poprzednia
