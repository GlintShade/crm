# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Whitelisted API rozliczeń prowizji z odbiorcami (Handlowiec, Manager, Partner), ops#281.

TWARDY WYMÓG: każda metoda jest dostępna wyłącznie dla `System Manager` i
`Volteo Core Admin` (`crm.api.koszty.ADMIN_ROLE`), nigdy dla `BYPASS_ROLES`. Bramka
`_wymagaj_admina()` stoi na początku każdej metody, PRZED jakimkolwiek odczytem danych.

Logika decyzyjna siedzi w frappe-free `crm/volteo_rozliczenie.py`, dostęp do bazy dla
hooków i naliczania w `crm/rozliczenia.py`; tu jest wyłącznie warstwa API, ślady w
Aktywności i rejestr.

Decyzje projektowe:

* Okres w rejestrze (`okres = {"wg", "od", "do"}`) filtrowany po stronie Pythona na
  datach (nie SQL): `podpisanie` -> `Volteo Rozliczenie.data_podpisania`, `wyplata` ->
  `data_wyplaty`, `utworzenie` -> data `CRM Deal.creation`, `oznaczenie` -> data
  `oznaczono`. Wiersze bez daty bazowej NIE wchodzą do listy rejestru. Kafelki liczą
  się z TEGO SAMEGO zestawu filtrów, ale wiersz bez daty bazowej dostaje datę zastępczą:
  `data_podpisania`, a gdy i ta pusta, data `CRM Deal.creation`, żeby "Do wypłaty w
  okresie" nie zerowało się dla nierozliczonych (nie mają `data_wyplaty`). Kafelki
  liczą cały zestaw, lista rejestru jest przycinana do `LIMIT_WIERSZY`.
* "Do wypłaty" w sumach grup i kafelkach to wyłącznie status `Do wypłaty`
  (wstrzymane liczy się osobno w `szans_z_otwartym`); `podsumowanie.pozostalo` szansy
  to natomiast `sumy()["do_wyplaty"]` z rdzenia (Do wypłaty + Wstrzymane).
* Kwoty w sumach i podsumowaniu to stringi z 2 miejscami (`"2400.00"`), kwoty
  pojedynczych wierszy to liczby z bazy.
"""

import csv
import datetime
import io
from collections import defaultdict
from decimal import Decimal
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_fullname

from crm.api.koszty import ADMIN_ROLE
from crm.rozliczenia import (
	DOCTYPE,
	POLA_CP,
	POLA_WIERSZA,
	_manager_szansy,
	wiersze_szansy,
)
from crm.rozliczenia import nalicz as nalicz_wiersze
from crm.volteo_aktywnosc import zapisz_slad
from crm.volteo_rozliczenie import (
	ROLE,
	STATUS_DO_WYPLATY,
	STATUS_NIE_DOTYCZY,
	STATUS_WSTRZYMANE,
	STATUS_WYPLACONE,
	ZNACZNIK_ROZLICZENIE,
	_data,
	_kwota,
	data_podpisania,
	formatuj_kwote,
	kwoty_odbiorcow,
	licznik,
	stan_zbiorczy,
	sumy,
	tekst_sladu,
	waliduj_kwote,
	waliduj_wyplate,
)

LIMIT_WIERSZY = 2000
LIMIT_POBRANIA = 20000
LIMIT_HISTORII = 50
OKRES_WG = ("podpisanie", "wyplata", "utworzenie", "oznaczenie")
GRUPOWANIA = ("osoba", "szansa")
STATUSY_USTAWIALNE = (STATUS_DO_WYPLATY, STATUS_WSTRZYMANE, STATUS_NIE_DOTYCZY)
_AKCJA_STATUSU = {
	STATUS_DO_WYPLATY: "do_wyplaty",
	STATUS_WSTRZYMANE: "wstrzymanie",
	STATUS_NIE_DOTYCZY: "nie_dotyczy",
}
NAGLOWEK_CSV = [
	"Szansa",
	"Klient",
	"Rodzaj",
	"Etap",
	"Rola",
	"Odbiorca",
	"Kwota",
	"Status",
	"Data wypłaty",
	"Oznaczył",
	"Uwaga",
]


# --- bramka i pomocnicze --------------------------------------------------------------


def _wymagaj_admina() -> None:
	"""Tylko `System Manager` i `Volteo Core Admin`; reszta dostaje `PermissionError`
	zanim cokolwiek zostanie odczytane."""
	if not ADMIN_ROLE & set(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("Brak uprawnień"), frappe.PermissionError)


def _kto() -> str:
	return get_fullname(frappe.session.user)


def _str(kwota: Any) -> str:
	return f"{_kwota(kwota):.2f}"


def _zl(kwota: Any) -> str:
	return formatuj_kwote(kwota if kwota is not None else 0)


def _parsuj_kwote(kwota: Any) -> Decimal:
	komunikat = waliduj_kwote(kwota)
	if komunikat:
		frappe.throw(komunikat)
	return _kwota(kwota)


def _deal_do_odczytu(deal: str):
	if not deal or not frappe.db.exists("CRM Deal", deal):
		frappe.throw(_("Nie znaleziono szansy."))
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("read")
	return doc


def _wiersz(nazwa: str, uprawnienie: str = "write"):
	if not nazwa or not frappe.db.exists(DOCTYPE, nazwa):
		frappe.throw(_("Nie znaleziono wiersza rozliczenia."))
	doc = frappe.get_doc(DOCTYPE, nazwa)
	doc.check_permission(uprawnienie)
	return doc


def _slad(deal: str, tekst: str) -> None:
	zapisz_slad(deal, tekst)


def _pozycji(n: int) -> str:
	if n == 1:
		return "1 pozycja"
	if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
		return f"{n} pozycje"
	return f"{n} pozycji"


def _inicjaly(uzytkownik: str) -> str:
	litery = "".join(c for c in (s[:1] for s in get_fullname(uzytkownik).split()) if c.isalpha())
	return litery.upper() or "XX"


def _nastepny_numer_partii(prefiks: str) -> int:
	istniejace = frappe.get_all(
		DOCTYPE, filters={"partia": ("like", f"{prefiks}-%")}, fields=["partia"], distinct=True
	)
	numery = []
	for w in istniejace:
		koniec = str(w["partia"]).rsplit("-", 1)[-1]
		if koniec.isdigit():
			numery.append(int(koniec))
	return (max(numery) if numery else 0) + 1


# --- widok szansy ---------------------------------------------------------------------


def _historia(deal: str) -> list[dict]:
	komentarze = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "CRM Deal",
			"reference_name": deal,
			"comment_type": "Info",
			"content": ("like", f"{ZNACZNIK_ROZLICZENIE}%"),
		},
		fields=["creation", "comment_by", "comment_email", "content"],
		order_by="creation desc",
		limit_page_length=LIMIT_HISTORII,
	)
	return [
		{
			"kiedy": k["creation"],
			"kto": k["comment_by"] or k["comment_email"],
			"tekst": str(k["content"])[len(ZNACZNIK_ROZLICZENIE) :].strip(),
		}
		for k in komentarze
	]


def _mozna_naliczyc(doc, istniejace: list[dict]) -> bool:
	kwoty = kwoty_odbiorcow(
		doc.get("custom_rodzaj_umowy"),
		doc.get("custom_koszty_json"),
		{pole: doc.get(pole) for pole in POLA_CP},
		doc.deal_owner,
		_manager_szansy(doc.deal_owner),
	)
	mamy = {w["rola"] for w in istniejace}
	return any(rola not in mamy for rola in kwoty)


def _widok_szansy(deal: str) -> dict[str, Any]:
	doc = _deal_do_odczytu(deal)
	wiersze = wiersze_szansy(deal)
	s = sumy(wiersze)
	return {
		"wiersze": [
			{**w, "potwierdzenie": frappe.db.get_value(DOCTYPE, w["name"], "potwierdzenie")} for w in wiersze
		],
		"podsumowanie": {
			"lacznie": _str(s["lacznie"]),
			"wyplacono": _str(s["wyplacono"]),
			"pozostalo": _str(s["do_wyplaty"]),
			"stan": stan_zbiorczy(wiersze),
			"licznik": licznik(wiersze),
		},
		"historia": _historia(deal),
		"rodzaj": doc.get("custom_rodzaj_umowy"),
		"mozna_naliczyc": _mozna_naliczyc(doc, wiersze),
	}


@frappe.whitelist()
def dla_szansy(deal: str) -> dict[str, Any]:
	"""Wiersze rozliczenia szansy, podsumowanie, historia śladów i flaga `mozna_naliczyc`."""
	_wymagaj_admina()
	return _widok_szansy(deal)


@frappe.whitelist()
def nalicz(deal: str) -> dict[str, Any]:
	"""Zakłada brakujące wiersze (idempotentnie) wg `crm.rozliczenia.nalicz`."""
	_wymagaj_admina()
	_deal_do_odczytu(deal)
	nowe = nalicz_wiersze(deal, frappe.session.user)
	if nowe:
		_slad(
			deal,
			f"{ZNACZNIK_ROZLICZENIE} {_kto()} naliczył odbiorców ze snapshotu ({_pozycji(len(nowe))})",
		)
	return _widok_szansy(deal)


@frappe.whitelist()
def dodaj_odbiorce(deal: str, rola: str, odbiorca: str | None, kwota: str) -> dict[str, Any]:
	"""Ręczne dodanie wiersza (np. Manager lub Partner przy OZE). Unikalność roli i
	nieujemność kwoty pilnuje też hook `validate` doctype'u."""
	_wymagaj_admina()
	doc = _deal_do_odczytu(deal)
	if rola not in ROLE:
		frappe.throw(_("Nieznana rola odbiorcy."))
	if odbiorca and not frappe.db.exists("User", odbiorca):
		frappe.throw(_("Nie znaleziono użytkownika."))
	wartosc = _parsuj_kwote(kwota)
	nazwa = get_fullname(odbiorca) if odbiorca else None
	podpisanie = data_podpisania(
		[{"to": w.to, "to_date": w.to_date} for w in (doc.get("status_change_log") or [])]
	)
	wiersz = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"deal": deal,
			"rola": rola,
			"odbiorca": odbiorca or None,
			"odbiorca_nazwa": nazwa,
			"kwota": wartosc,
			"status": STATUS_DO_WYPLATY,
			"zrodlo_kwoty": "Ręcznie",
			"data_podpisania": podpisanie,
		}
	)
	wiersz.insert()
	_slad(deal, tekst_sladu("dodanie", rola, nazwa, wartosc, None, _kto()))
	return _widok_szansy(deal)


# --- zmiany stanu wiersza -------------------------------------------------------------


@frappe.whitelist()
def oznacz_wyplacone(nazwy: list[str], data_wyplaty: str, uwaga: str = "") -> dict[str, Any]:
	"""Jedna akcja dla zakładki (1 wiersz) i rejestru (N wierszy). Wszystkie wiersze
	dostają wspólną `partia`; wiersz już `Wypłacone` jest pomijany. Jeden ślad na szansę."""
	_wymagaj_admina()
	komunikat = waliduj_wyplate(STATUS_WYPLACONE, data_wyplaty)
	if komunikat:
		frappe.throw(komunikat)
	data = _data(data_wyplaty)
	unikalne = list(dict.fromkeys(nazwy or []))
	if not unikalne:
		frappe.throw(_("Nie wybrano żadnych wierszy."))
	wiersze = [_wiersz(n) for n in unikalne]
	do_oznaczenia = [w for w in wiersze if w.status != STATUS_WYPLACONE]
	if not do_oznaczenia:
		return {"oznaczono": 0, "partia": None}

	prefiks = f"{data.isoformat()}-{_inicjaly(frappe.session.user)}"
	partia = f"{prefiks}-{_nastepny_numer_partii(prefiks):02d}"
	teraz = frappe.utils.now_datetime()
	pierwszy_na_szanse: dict[str, Any] = {}
	for w in do_oznaczenia:
		w.status = STATUS_WYPLACONE
		w.data_wyplaty = data
		w.oznaczyl = frappe.session.user
		w.oznaczono = teraz
		w.partia = partia
		if uwaga:
			w.uwaga = uwaga
		w.save()
		pierwszy_na_szanse.setdefault(w.deal, w)
	kto = _kto()
	for deal, w in pierwszy_na_szanse.items():
		_slad(
			deal,
			tekst_sladu(
				"wyplata",
				w.rola,
				w.odbiorca_nazwa,
				w.kwota,
				data,
				kto,
				partia_n=len(do_oznaczenia) - 1,
			),
		)
	return {"oznaczono": len(do_oznaczenia), "partia": partia}


@frappe.whitelist()
def cofnij(nazwa: str, uwaga: str = "") -> dict[str, Any]:
	"""Cofnięcie wypłaty: status `Do wypłaty`, czyszczenie daty, oznaczenia i partii."""
	_wymagaj_admina()
	w = _wiersz(nazwa)
	if w.status != STATUS_WYPLACONE:
		frappe.throw(_("Tylko wypłacony wiersz można cofnąć."))
	data = w.data_wyplaty
	w.status = STATUS_DO_WYPLATY
	w.data_wyplaty = None
	w.oznaczyl = None
	w.oznaczono = None
	w.partia = None
	if uwaga:
		w.uwaga = uwaga
	w.save()
	_slad(w.deal, tekst_sladu("cofniecie", w.rola, w.odbiorca_nazwa, w.kwota, data, _kto()))
	return _widok_szansy(w.deal)


@frappe.whitelist()
def ustaw_status(nazwa: str, status: str, uwaga: str = "") -> dict[str, Any]:
	"""`Do wypłaty` / `Wstrzymane` / `Nie dotyczy`. `Wypłacone` wyłącznie przez
	`oznacz_wyplacone`; wypłacony wiersz najpierw trzeba cofnąć."""
	_wymagaj_admina()
	if status not in STATUSY_USTAWIALNE:
		frappe.throw(_("Ten status można ustawić tylko przez oznaczenie wypłaty."))
	w = _wiersz(nazwa)
	if w.status == STATUS_WYPLACONE:
		frappe.throw(_("Najpierw cofnij wypłatę tego wiersza."))
	w.status = status
	if uwaga:
		w.uwaga = uwaga
	w.save()
	_slad(w.deal, tekst_sladu(_AKCJA_STATUSU[status], w.rola, w.odbiorca_nazwa, w.kwota, None, _kto()))
	return _widok_szansy(w.deal)


@frappe.whitelist()
def zmien_kwote(nazwa: str, kwota: str) -> dict[str, Any]:
	"""Nowa kwota wiersza; źródło kwoty przechodzi na `Ręcznie`."""
	_wymagaj_admina()
	wartosc = _parsuj_kwote(kwota)
	w = _wiersz(nazwa)
	stara = w.kwota
	w.kwota = wartosc
	w.zrodlo_kwoty = "Ręcznie"
	w.save()
	tekst = tekst_sladu("zmiana_kwoty", w.rola, w.odbiorca_nazwa, wartosc, None, _kto())
	_slad(w.deal, f"{tekst}, było {_zl(stara)}")
	return _widok_szansy(w.deal)


@frappe.whitelist()
def usun_odbiorce(nazwa: str) -> dict[str, Any]:
	"""Usunięcie wiersza w statusie innym niż `Wypłacone`."""
	_wymagaj_admina()
	w = _wiersz(nazwa, "delete")
	if w.status == STATUS_WYPLACONE:
		frappe.throw(_("Wypłaconego wiersza nie można usunąć, najpierw cofnij wypłatę."))
	deal, rola, odbiorca_nazwa, kwota = w.deal, w.rola, w.odbiorca_nazwa, w.kwota
	frappe.delete_doc(DOCTYPE, nazwa)
	_slad(
		deal,
		f"{ZNACZNIK_ROZLICZENIE} {_kto()} usunął odbiorcę rozliczenia: {rola}"
		+ (f" ({odbiorca_nazwa}, {_zl(kwota)})" if odbiorca_nazwa else f" ({_zl(kwota)})"),
	)
	return _widok_szansy(deal)


# --- rejestr i eksport ----------------------------------------------------------------


def _lista(wartosc: Any) -> list[str]:
	if wartosc in (None, ""):
		return []
	if isinstance(wartosc, str):
		return [wartosc]
	return [str(x) for x in wartosc]


def _zakres(okres: dict | None) -> tuple[str, datetime.date, datetime.date] | None:
	if not okres:
		return None
	wg = okres.get("wg")
	if wg not in OKRES_WG:
		frappe.throw(_("Nieznany sposób liczenia okresu."))
	od, do = _data(okres.get("od")), _data(okres.get("do"))
	if od is None or do is None:
		frappe.throw(_("Okres wymaga daty początkowej i końcowej."))
	if od > do:
		frappe.throw(_("Data początkowa nie może być późniejsza niż końcowa."))
	return wg, od, do


def _pobierz(filtry: dict | None, okres: dict | None) -> tuple[list[dict], list[dict]]:
	"""Zwraca `(lista, kafelki)`: wzbogacone wiersze spełniające filtry i okres wg daty
	bazowej (lista) oraz wg daty z fallbackiem (kafelki). Posortowane po szansie."""
	filtry = filtry or {}
	zakres = _zakres(okres)
	warunki: dict[str, Any] = {}
	if filtry.get("osoba"):
		warunki["odbiorca"] = filtry["osoba"]
	role = _lista(filtry.get("rola"))
	if role:
		warunki["rola"] = ("in", role)
	statusy = _lista(filtry.get("status"))
	if statusy:
		warunki["status"] = ("in", statusy)
	wiersze = frappe.get_all(
		DOCTYPE,
		filters=warunki,
		fields=[*POLA_WIERSZA],
		order_by="creation asc",
		limit_page_length=LIMIT_POBRANIA,
	)
	nazwy_szans = list({w["deal"] for w in wiersze})
	szanse: dict[str, dict] = {}
	for i in range(0, len(nazwy_szans), 500):
		for d in frappe.get_all(
			"CRM Deal",
			filters={"name": ("in", nazwy_szans[i : i + 500])},
			fields=["name", "lead_name", "custom_rodzaj_umowy", "status", "creation"],
		):
			szanse[d["name"]] = d
	rodzaje = _lista(filtry.get("rodzaj_umowy"))

	lista, kafelki = [], []
	for w in wiersze:
		szansa = szanse.get(w["deal"])
		if not szansa or (rodzaje and szansa.get("custom_rodzaj_umowy") not in rodzaje):
			continue
		utworzenie = _data(szansa.get("creation"))
		bazowe = {
			"podpisanie": _data(w.get("data_podpisania")),
			"wyplata": _data(w.get("data_wyplaty")),
			"utworzenie": utworzenie,
			"oznaczenie": _data(w.get("oznaczono")),
		}
		wzbogacony = {
			**w,
			"klient": szansa.get("lead_name"),
			"rodzaj": szansa.get("custom_rodzaj_umowy"),
			"etap": szansa.get("status"),
		}
		if zakres is None:
			lista.append(wzbogacony)
			kafelki.append(wzbogacony)
			continue
		wg, od, do = zakres
		data_listy = bazowe[wg]
		if data_listy is not None and od <= data_listy <= do:
			lista.append(wzbogacony)
		data_kafelka = data_listy or bazowe["podpisanie"] or utworzenie
		if data_kafelka is not None and od <= data_kafelka <= do:
			kafelki.append(wzbogacony)
	klucz = lambda x: (str(x.get("deal")), str(x.get("rola")))  # noqa: E731
	return sorted(lista, key=klucz), kafelki


def _suma(wiersze: list[dict], status: str) -> Decimal:
	return sum((_kwota(w["kwota"]) for w in wiersze if w["status"] == status), Decimal("0"))


def _kafelki(wiersze: list[dict]) -> dict[str, Any]:
	otwarte = [w for w in wiersze if w["status"] in (STATUS_DO_WYPLATY, STATUS_WSTRZYMANE)]
	return {
		"do_wyplaty_w_okresie": _str(_suma(wiersze, STATUS_DO_WYPLATY)),
		"wyplacono_w_okresie": _str(_suma(wiersze, STATUS_WYPLACONE)),
		"szans_z_otwartym": len({w["deal"] for w in otwarte}),
		"odbiorcow_do_rozliczenia": sum(1 for w in wiersze if w["status"] == STATUS_DO_WYPLATY),
	}


def _wiersz_rejestru(w: dict) -> dict[str, Any]:
	return {
		"nazwa": w["name"],
		"deal": w["deal"],
		"klient": w["klient"],
		"rodzaj": w["rodzaj"],
		"etap": w["etap"],
		"rola": w["rola"],
		"odbiorca_nazwa": w["odbiorca_nazwa"],
		"kwota": w["kwota"],
		"status": w["status"],
		"data_wyplaty": w["data_wyplaty"],
	}


def _grupuj(wiersze: list[dict], grupowanie: str) -> list[dict]:
	grupy: dict[str, list[dict]] = defaultdict(list)
	for w in wiersze:
		klucz = (w.get("odbiorca") or "") if grupowanie == "osoba" else w["deal"]
		grupy[klucz].append(w)
	wynik = []
	for klucz, czlonkowie in grupy.items():
		if grupowanie == "osoba":
			etykieta = czlonkowie[0].get("odbiorca_nazwa") or klucz or "(bez odbiorcy)"
			podtytul = ", ".join(sorted({w["rola"] for w in czlonkowie}, key=ROLE.index))
		else:
			etykieta = klucz
			podtytul = " | ".join(s for s in (czlonkowie[0]["klient"], czlonkowie[0]["rodzaj"]) if s)
		wynik.append(
			{
				"klucz": klucz,
				"etykieta": etykieta,
				"podtytul": podtytul,
				"suma_do_wyplaty": _str(_suma(czlonkowie, STATUS_DO_WYPLATY)),
				"liczba_szans": len({w["deal"] for w in czlonkowie}),
				"wiersze": [_wiersz_rejestru(w) for w in czlonkowie],
			}
		)
	return sorted(wynik, key=lambda g: (str(g["etykieta"]).lower(), g["klucz"]))


@frappe.whitelist()
def rejestr(
	filtry: dict | None = None, grupowanie: str = "osoba", okres: dict | None = None
) -> dict[str, Any]:
	"""Rejestr rozliczeń: grupy (wg osoby lub szansy) i kafelki podsumowania. Limit
	`LIMIT_WIERSZY` wierszy na liście; kafelki liczą cały zestaw. Semantyka okresu w
	docstringu modułu."""
	_wymagaj_admina()
	if grupowanie not in GRUPOWANIA:
		frappe.throw(_("Nieznane grupowanie."))
	lista, kafelki = _pobierz(filtry, okres)
	return {"grupy": _grupuj(lista[:LIMIT_WIERSZY], grupowanie), "kafelki": _kafelki(kafelki)}


def _komorka(wartosc: Any) -> str:
	tekst = "" if wartosc is None else str(wartosc)
	return f"'{tekst}" if tekst[:1] in ("=", "+", "-", "@") else tekst


@frappe.whitelist()
def eksport_csv(filtry: dict | None = None, okres: dict | None = None) -> str:
	"""CSV UTF-8 z BOM, separator średnik, kwoty z przecinkiem dziesiętnym. Zwraca treść
	(front robi pobieranie). Komórki tekstowe zaczynające się od `=`, `+`, `-`, `@` są
	poprzedzone apostrofem (ochrona przed formułami w arkuszu)."""
	_wymagaj_admina()
	lista, _kafelki_nieuzywane = _pobierz(filtry, okres)
	bufor = io.StringIO()
	pisarz = csv.writer(bufor, delimiter=";", lineterminator="\r\n")
	pisarz.writerow(NAGLOWEK_CSV)
	for w in lista:
		pisarz.writerow(
			[
				_komorka(w["deal"]),
				_komorka(w["klient"]),
				_komorka(w["rodzaj"]),
				_komorka(w["etap"]),
				_komorka(w["rola"]),
				_komorka(w["odbiorca_nazwa"]),
				_str(w["kwota"]).replace(".", ","),
				_komorka(w["status"]),
				_data(w["data_wyplaty"]).isoformat() if _data(w["data_wyplaty"]) else "",
				_komorka(get_fullname(w["oznaczyl"]) if w.get("oznaczyl") else ""),
				_komorka(w.get("uwaga")),
			]
		)
	return "﻿" + bufor.getvalue()
