# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Uklad paska szybkich filtrow PER UZYTKOWNIK (issue #219).

Do tego cyklu pasek szybkich filtrow (`ViewControls.vue`, `crm.api.doc.get_quick_filters`)
mial jeden, globalny uklad na doctype, zapisany w `CRM Global Settings`
(type="Quick Filters") i edytowalny wylacznie przez managera (ops#79).
Ten modul dodaje DRUGI, wlasny uklad na uzytkownika, przechowywany jako User
Default (`frappe.defaults`, klucz `klucz_domyslnej_uzytkownika(doctype)`) w
`crm/api/doc.py` -- ten modul liczy tylko CZYSTA LOGIKE wokol tego ukladu:

- `wybierz_kolejnosc`: ktory uklad (wlasny czy globalny) ostatecznie trafia
  na pasek danego uzytkownika.
- `waliduj_liste`: czy lista nazw pol, ktora uzytkownik chce zapisac (wlasna
  albo globalna), jest poprawna.
- `scal_globalne`: jak manager/admin edytujacy GLOBALNY uklad nie usuwa z
  niego, niechcacy, pol, ktorych sam nie widzi (patrz docstring nizej).
- `parsuj_json_listy` / `klucz_domyslnej_uzytkownika`: male funkcje pomocnicze
  wokol samego formatu przechowywania.

Modul jest celowo frappe-free (ten sam powod co `crm.volteo_lista_szans`,
patrz jej docstring): to jedyny sposob, zeby dalo sie go przetestowac na tej
maszynie, gdzie `frappe` nie jest instalowalny. Odczyt/zapis `frappe.defaults`
i uprawnien (`_pola_dozwolone`) liczy wywolujacy (`crm/api/doc.py`) i
przekazuje tutaj wylacznie jako proste wartosci (listy, zbiory nazw pol).
"""

import json
from collections.abc import Iterable, Sequence

# Prefiks klucza User Default (`frappe.defaults`), pod ktorym zyje wlasny
# uklad paska danego uzytkownika dla danego doctype'u. Jeden klucz na
# (uzytkownik, doctype) -- `frappe.defaults.set_user_default`/`get_user_default`/
# `clear_user_default` adresuja go domyslnie dla `frappe.session.user`, wiec
# wolajacy nigdy nie przekazuje innego uzytkownika (patrz brief: "session user
# only, no user param").
PREFIKS_KLUCZA_UZYTKOWNIKA = "volteo_filtry_szybkie::"

# Maksymalna liczba pol na pasku -- bez tego ktos mogby zapisac (przez
# bezposrednie wywolanie API, nie przez UI) kilkaset pol i uczynic pasek
# bezuzytecznym/wolnym; UI i tak nigdy nie generuje takiej liczby przez
# normalne klikanie.
LIMIT_POL_NA_PASKU = 30


def klucz_domyslnej_uzytkownika(doctype: str) -> str:
	"""Klucz User Default dla wlasnego ukladu paska uzytkownika na danym
	doctype'ie. Jedno miejsce formatu klucza -- `crm/api/doc.py` go nie
	formatuje samo, zeby zapis i odczyt nigdy nie rozjechaly sie na literalu.
	"""
	return f"{PREFIKS_KLUCZA_UZYTKOWNIKA}{doctype}"


def parsuj_json_listy(wartosc: object) -> list[str] | None:
	"""Bezpieczny odczyt zapisanej wartosci (string JSON, albo cokolwiek
	innego, co moze przyjsc z `frappe.defaults.get_user_default`) jako listy
	nazw pol.

	Zwraca `None` dla: `None`, nie-string, string nie bedacy poprawnym JSON,
	JSON nie bedacy tablica, tablica zawierajaca cokolwiek innego niz string
	(wolimy odrzucic cala wartosc niz zgadywac, ktore elementy sa "dobre").
	Pusta tablica JSON (`"[]"`) zwraca pusta liste `[]` -- to jest odrebny
	wynik od `None` (odrozniajacy "uzytkownik nigdy nie zapisal wlasnego
	ukladu" od "zapisal pusty uklad"), nawet jesli strona zapisu
	(`waliduj_liste` nizej) nigdy go realnie nie wyprodukuje (pusty uklad
	jest tam odrzucany -- do tego sluzy przycisk "Przywroc domyslny", nie
	zapis pustej listy).
	"""
	if not isinstance(wartosc, str) or not wartosc:
		return None
	try:
		dane = json.loads(wartosc)
	except (TypeError, ValueError):
		return None
	if not isinstance(dane, list):
		return None
	if not all(isinstance(pole, str) for pole in dane):
		return None
	return dane


def _odfiltruj_i_dedup(
	pola: Iterable[str],
	dozwolone: Iterable[str],
	istniejace: Iterable[str],
) -> list[str]:
	"""Zwraca `pola` w tej samej kolejnosci, bez duplikatow (pierwsze
	wystapienie wygrywa) i wylacznie te, ktore sa jednoczesnie w `dozwolone`
	(uprawnienia odczytu) i w `istniejace` (pole faktycznie da sie
	wyrenderowac na pasku -- patrz `crm.api.doc._pola_istniejace_do_paska`).
	"""
	dozwolone_zbior = set(dozwolone)
	istniejace_zbior = set(istniejace)
	wynik: list[str] = []
	widziane: set[str] = set()
	for pole in pola:
		if pole in widziane:
			continue
		if pole not in dozwolone_zbior or pole not in istniejace_zbior:
			continue
		widziane.add(pole)
		wynik.append(pole)
	return wynik


def wybierz_kolejnosc(
	globalne: Sequence[str] | None,
	uzytkownika: object,
	dozwolone: Iterable[str],
	istniejace: Iterable[str],
) -> list[str]:
	"""Rozstrzyga, KTORY uklad (wlasny uzytkownika czy globalny) i w jakiej
	formie trafia na pasek szybkich filtrow danego uzytkownika (issue #219).

	Zasada: wlasny uklad uzytkownika wygrywa, ALE wylacznie jesli po
	przefiltrowaniu go do pol dozwolonych/istniejacych cokolwiek z niego
	zostaje -- pusty wynik (np. uzytkownik zapisal uklad, po czym admin
	odebral mu uprawnienie do kazdego z tych pol) oznacza w praktyce
	"wlasny uklad jest teraz bez znaczenia", wiec pasek wraca do globalnego,
	zamiast pokazac sie calkowicie pusty.

	`uzytkownika` jest typowana jako `object` i tolerowana jako
	None/cokolwiek-nie-liste (garbage) -- wywolujacy zwykle przekazuje tu
	wynik `parsuj_json_listy` (wiec i tak `list[str] | None`), ale ta
	funkcja nie zaklada tego i sama odrzuca kazdy inny typ jako "brak
	wlasnego ukladu", zamiast wywalic wyjatek.

	Obie listy wynikowe (wlasna i globalna) przechodza przez ten sam filtr
	dozwolone/istniejace i ten sam dedup (`_odfiltruj_i_dedup`) -- kolejnosc
	elementow WEWNATRZ kazdej listy jest zachowana z wejscia, nigdy
	przesortowana wedlug drugiej listy.
	"""
	globalna_lista = _odfiltruj_i_dedup(globalne or [], dozwolone, istniejace)

	uzytkownika_lista = uzytkownika if isinstance(uzytkownika, list) else None
	if uzytkownika_lista is not None:
		uzytkownika_lista = [pole for pole in uzytkownika_lista if isinstance(pole, str)]
		przefiltrowana = _odfiltruj_i_dedup(uzytkownika_lista, dozwolone, istniejace)
		if przefiltrowana:
			return przefiltrowana

	return globalna_lista


def waliduj_liste(
	pola: object,
	dozwolone: Iterable[str],
	limit: int = LIMIT_POL_NA_PASKU,
) -> list[str]:
	"""Waliduje liste nazw pol do zapisania jako uklad paska (wlasny albo,
	po `scal_globalne`, globalny) -- rzuca `ValueError` z polskim
	komunikatem na pierwszy napotkany problem, w tej kolejnosci:

	1. `pola` nie jest lista.
	2. lista jest pusta -- zapis pustego ukladu jest celowo zablokowany,
	   do wyczyszczenia wlasnego ukladu sluzy osobna akcja (reset, patrz
	   `crm.api.doc.resetuj_filtry_szybkie_uzytkownika`), nie zapis `[]`.
	3. lista przekracza `limit` pol.
	4. ktorys element nie jest niepustym stringiem.
	5. lista zawiera duplikat.
	6. ktores pole nie jest w `dozwolone` (ani uprawnienie odczytu, ani
	   pole, z ktorego da sie zbudowac wpis paska -- wywolujacy przekazuje
	   tu przeciecie obu, patrz `crm.api.doc._pola_istniejace_do_paska`).

	Zwraca NOWA liste (ta sama kolejnosc, ten sam zawartosc) -- nie mutuje
	`pola`.
	"""
	if not isinstance(pola, list):
		raise ValueError("Lista pól musi być tablicą nazw pól.")

	if len(pola) == 0:
		raise ValueError(
			"Pasek szybkich filtrów nie może być pusty. Użyj przycisku "
			"'Przywróć domyślny', aby usunąć własny układ."
		)

	if len(pola) > limit:
		raise ValueError(f"Pasek szybkich filtrów może mieć maksymalnie {limit} pól.")

	for pole in pola:
		if not isinstance(pole, str) or not pole:
			raise ValueError("Lista pól może zawierać tylko nazwy pól (tekst).")

	widziane: set[str] = set()
	for pole in pola:
		if pole in widziane:
			raise ValueError(f"Pole '{pole}' występuje na pasku więcej niż raz.")
		widziane.add(pole)

	dozwolone_zbior = set(dozwolone)
	for pole in pola:
		if pole not in dozwolone_zbior:
			raise ValueError(f"Pole '{pole}' nie jest dostępne do filtrowania.")

	return list(pola)


def scal_globalne(
	nowe_widoczne: Sequence[str],
	stare_globalne: Sequence[str],
	widoczne_dla_edytujacego: Iterable[str],
) -> list[str]:
	"""Scala nowy globalny uklad paska (wpisany przez managera/admina) ze
	starym tak, zeby edycja NIE usuwala z globalnego ukladu pol, ktorych
	edytujacy po prostu nie widzi (permlevel) -- w odroznieniu od pol,
	ktore widzial i SWIADOMIE usunal.

	Kontekst: edytujacy globalny uklad (`update_quick_filters`, rola
	Sales Manager/Volteo Core Admin/System Manager) nie zawsze widzi WSZYSTKIE
	pola, ktore globalny uklad niesie dzisiaj -- np. Sales Manager bez
	permlevel 2 nie widzi pola kosztow/prowizji, ktore admin chcial miec na
	pasku dla siebie. Przed ta funkcja `update_quick_filters` po prostu
	NADPISYWAL cala globalna liste tym, co edytujacy wyslal
	(`newQuickFilters` we froncie) -- co mogl zbudowac WYLACZNIE z pol,
	ktore widzial. Kazde pole niewidoczne dla edytujacego wypadalo wiec z
	globalnego ukladu NIE dlatego, ze ktos je swiadomie usunal, tylko dlatego,
	ze front nigdy go nie pokazal w edytorze -- i znikalo to TEZ dla
	administratora, ktory mial je widziec.

	Algorytm: dla kazdego pola ze `stare_globalne`, ktorego edytujacy NIE
	widzi (nie jest w `widoczne_dla_edytujacego`), wstawiamy je z powrotem do
	wyniku na jego WZGLEDNEJ pozycji -- tuz za najblizszym POPRZEDZAJACYM je
	(w STARYM ukladzie) polem, ktore przetrwalo w wyniku; jesli zadne
	wczesniejsze pole nie przetrwalo, wstawiamy je na sam poczatek. Pola
	widoczne dla edytujacego, ktorych nie ma w `nowe_widoczne`, zostaja
	usuniete -- to jest ich swiadome usuniecie, nie dotykamy go.

	Pola z `nowe_widoczne`, ktorych nie bylo w `stare_globalne` (nowo
	dodane), przechodza bez zmian, na pozycji, na ktorej je wstawil
	edytujacy.
	"""
	widoczne_zbior = set(widoczne_dla_edytujacego)
	stare_lista = list(stare_globalne)

	wynik = list(nowe_widoczne)

	for idx, pole in enumerate(stare_lista):
		if pole in widoczne_zbior:
			# Edytujacy widzial to pole -- jego usuniecie (albo
			# pozostawienie) w `nowe_widoczne` jest swiadome, nie dotykamy.
			continue
		if pole in wynik:
			# Bezpiecznik: pole niewidoczne dla edytujacego nie powinno
			# moglo trafic do `nowe_widoczne` (front budowal je wylacznie z
			# pol widocznych) -- jesli jednak trafilo, nie duplikujemy go.
			continue

		kotwica = None
		for wczesniejsze in reversed(stare_lista[:idx]):
			if wczesniejsze in wynik:
				kotwica = wczesniejsze
				break

		if kotwica is None:
			wynik.insert(0, pole)
		else:
			wynik.insert(wynik.index(kotwica) + 1, pole)

	return wynik
