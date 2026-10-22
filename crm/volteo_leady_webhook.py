# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Webhook leadow z Facebook Lead Ads przez Make.com (ops#296): logika czysta.

Scenariusz Make.com ("Facebook Lead Ads > Watch Leads") wysyla kazdy nowy lead
jako POST JSON do `crm.api.leady_webhook.przyjmij`. Ten modul zamienia ladunek
na slownik pol `CRM Lead`; sam insert, bramka roli, idempotencja i log odrzuconych
mieszkaja w cienkim adapterze `crm/api/leady_webhook.py`.

Modul celowo nie importuje ``frappe`` (precedens `crm/volteo_leady_import.py`),
zeby dalo sie go przetestowac lokalnie. Nie mutuje argumentow wejsciowych.

Odrzucenie calego ladunku (`LadunekOdrzucony`): brak albo zly telefon, brak
`facebook_lead_id` (klucz idempotencji). Kazde inne pole, ktorego nie da sie
rozpoznac, NIE gubi leada: surowa wartosc trafia jako linia do
`custom_uwagi_import`, a pole docelowe zostaje puste.
"""

import re
from collections.abc import Mapping
from datetime import date
from typing import Any

from crm.volteo_leady_import import (
	SEPARATOR_UWAG,
	normalizuj_kod,
	normalizuj_pisownie_osoby,
	normalizuj_telefon,
	rozdziel_imie_nazwisko,
	wyglada_na_firme,
)

ROLA_INTEGRACJI: str = "Volteo Integracja"
"""Rola konta integracji Make.com: jedyna bramka endpointu (bez zadnego DocPerm)."""

TOKEN_ZRODLA_FB: str = "FB"
"""Token w `custom_import_source` dla leadow z Facebooka."""

ZRODLO_LEADA: str = "Facebook"
"""Wartosc `CRM Lead.source` (wiersz `CRM Lead Source` istnieje z patcha upstreamu)."""

IMIE_ZASTEPCZE: str = "Lead Facebook"
"""`first_name`, gdy formularz nie niesie imienia (kontroler wymaga imienia)."""

_TAK = frozenset({"tak", "yes", "true", "1"})
_NIE = frozenset({"nie", "no", "false", "0"})

_SYSTEM_NOWE = ("net-billing", "net billing", "netbilling", "nowe", "nowy")
_SYSTEM_STARE = ("net-metering", "net metering", "netmetering", "opust", "stare", "stary")

_WZOR_DATY = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[T ].*)?$")
_WZOR_SLOW = re.compile(r"[^\W_]+", re.UNICODE)

_SLOWA_PV = frozenset({"pv", "fotowoltaika", "fotowoltaiki", "fotowoltaike", "fotowoltaiczna"})
_SLOWA_ME = frozenset({"mag", "magazyn", "magazyny", "magazynem", "magazynu", "me"})
_SLOWA_PC = frozenset({"pc", "pompa", "pompy", "pompe", "ciepla", "ciepła"})
_SLOWA_CP = frozenset({"cp", "czyste", "powietrze"})
_SLOWA_LACZNIKI = frozenset({"i", "z", "oraz", "plus", "energii"})


class LadunekOdrzucony(ValueError):
	"""Ladunek webhooka nie nadaje sie do zalozenia leada; `powod` czytelny dla logu."""

	def __init__(self, powod: str):
		super().__init__(powod)
		self.powod = powod


def _tekst(wartosc: Any) -> str:
	"""Sprowadza dowolna wartosc ladunku do przyciętego tekstu.

	`None` -> "", liczby -> tekst (`5.0` -> "5"), listy/krotki -> niepuste elementy
	przez ", " (Make potrafi wyslac liste jednoelementowa), reszta przez `str()`."""
	if wartosc is None:
		return ""
	if isinstance(wartosc, bool):
		return "true" if wartosc else "false"
	if isinstance(wartosc, float) and wartosc.is_integer():
		return str(int(wartosc))
	if isinstance(wartosc, (list, tuple)):
		return ", ".join(t for t in (_tekst(e) for e in wartosc) if t)
	if isinstance(wartosc, Mapping):
		return ""
	return str(wartosc).strip()


def _klucze_malymi(ladunek: Mapping[str, Any]) -> dict[str, Any]:
	"""Kopia ladunku z kluczami po `strip()` i malymi literami (nowy slownik)."""
	return {str(k).strip().lower(): v for k, v in ladunek.items()}


def normalizuj_posiada_pv(tekst: str) -> str | None:
	"""`tak/yes/true/1` -> `"PV"`, `nie/no/false/0` albo pusty -> `""`, inne -> `None`."""
	czysty = _tekst(tekst).lower()
	if not czysty or czysty in _NIE:
		return ""
	if czysty in _TAK:
		return "PV"
	return None


def normalizuj_system_rozliczen(tekst: str) -> str | None:
	"""Mapuje opis systemu rozliczen na literaly `custom_zasady_dotacji`.

	Net-billing / nowe -> `"Nowe zasady"`, net-metering / opust / stare ->
	`"Stare zasady"`. Pusty, nierozpoznany albo dwuznaczny (oba rodzaje naraz) -> `None`."""
	czysty = _tekst(tekst).lower()
	if not czysty:
		return None
	nowe = any(w in czysty for w in _SYSTEM_NOWE)
	stare = any(w in czysty for w in _SYSTEM_STARE)
	if nowe and not stare:
		return "Nowe zasady"
	if stare and not nowe:
		return "Stare zasady"
	return None


def normalizuj_produkt_reklamy(tekst: str) -> str | None:
	"""Mapuje produkt z reklamy na token `KOLEJNOSC_PRODUKTOW_PROCESU`.

	PV + magazyn / `pvme` -> `PVME`, sam magazyn / `me` -> `ME`, sam `pv` -> `PV`,
	pompa ciepla / `pc` -> `PC`, czyste powietrze / `cp` -> `CP`. Kazde nieznane
	slowo albo mieszanka rodzin (np. PV i pompa) -> `None` (surowy tekst idzie do Uwag)."""
	czysty = _tekst(tekst).lower()
	slowa = _WZOR_SLOW.findall(czysty)
	if not slowa:
		return None
	pv = me = pc = cp = False
	for slowo in slowa:
		if slowo == "pvme":
			pv = me = True
		elif slowo in _SLOWA_PV:
			pv = True
		elif slowo in _SLOWA_ME or slowo.startswith("magazyn"):
			me = True
		elif slowo in _SLOWA_PC:
			pc = True
		elif slowo in _SLOWA_CP:
			cp = True
		elif slowo in _SLOWA_LACZNIKI:
			continue
		else:
			return None
	rodziny = sum((pv or me, pc, cp))
	if rodziny != 1:
		return None
	if cp:
		return "CP"
	if pc:
		return "PC"
	if pv and me:
		return "PVME"
	if me:
		return "ME"
	return "PV"


def normalizuj_date_zgloszenia(tekst: str) -> str | None:
	"""Czesc daty z ISO `YYYY-MM-DD` albo ISO datetime; inaczej `None`."""
	dopasowanie = _WZOR_DATY.match(_tekst(tekst))
	if not dopasowanie:
		return None
	try:
		return date.fromisoformat(dopasowanie.group(1)).isoformat()
	except ValueError:
		return None


def splaszcz_odpowiedzi(odpowiedzi: Any) -> list[tuple[str, str]]:
	"""Splaszcza `odpowiedzi` do listy `(pytanie, odpowiedz)`, bez pustych odpowiedzi.

	Akceptuje slownik `{pytanie: odpowiedz}` albo liste Facebookowa
	`[{"name": ..., "values": [...]}]` (tez z kluczem `value`). Inne ksztalty -> `[]`."""
	wynik: list[tuple[str, str]] = []
	if isinstance(odpowiedzi, Mapping):
		pary = list(odpowiedzi.items())
	elif isinstance(odpowiedzi, (list, tuple)):
		pary = []
		for element in odpowiedzi:
			if not isinstance(element, Mapping):
				continue
			klucze = _klucze_malymi(element)
			pary.append((klucze.get("name"), klucze.get("values", klucze.get("value"))))
	else:
		return wynik
	for pytanie, odpowiedz in pary:
		nazwa = _tekst(pytanie)
		tresc = _tekst(odpowiedz)
		if nazwa and tresc:
			wynik.append((nazwa, tresc))
	return wynik


def zbuduj_leada_z_webhooka(ladunek: Mapping[str, Any], dzisiaj: str) -> dict[str, Any]:
	"""Zamienia ladunek webhooka na slownik pol `CRM Lead` (bez `doctype`).

	Rzuca `LadunekOdrzucony` przy braku/zlym telefonie albo braku `facebook_lead_id`.
	Klucze wyjsciowe puste sa pomijane. `dzisiaj` (ISO) to wartosc zastepcza
	`custom_import_date`. Nie mutuje `ladunek`."""
	if not isinstance(ladunek, Mapping):
		raise LadunekOdrzucony("Ladunek nie jest obiektem JSON.")
	dane = _klucze_malymi(ladunek)

	telefon_surowy = _tekst(dane.get("telefon"))
	if not telefon_surowy:
		raise LadunekOdrzucony("Brak numeru telefonu.")
	telefon = normalizuj_telefon(telefon_surowy)
	if telefon is None:
		raise LadunekOdrzucony("Niepoprawny numer telefonu: %s" % telefon_surowy)

	id_leada = _tekst(dane.get("facebook_lead_id"))
	if not id_leada:
		raise LadunekOdrzucony("Brak facebook_lead_id.")

	uwagi_nierozpoznane: list[str] = []

	# Imie i nazwisko
	pelne = _tekst(dane.get("imie_nazwisko"))
	if not pelne:
		imie, nazwisko = IMIE_ZASTEPCZE, ""
	elif wyglada_na_firme(pelne):
		imie, nazwisko = pelne, ""
	else:
		imie, nazwisko = rozdziel_imie_nazwisko(pelne, "")
		imie = normalizuj_pisownie_osoby(imie)
		nazwisko = normalizuj_pisownie_osoby(nazwisko)

	# Czy posiada PV
	posiada_surowe = _tekst(dane.get("posiada_pv"))
	posiada = normalizuj_posiada_pv(posiada_surowe)
	if posiada is None:
		uwagi_nierozpoznane.append("Posiada PV (nierozpoznane): %s" % posiada_surowe)
		posiada = ""

	# System rozliczen: tylko gdy klient ma PV
	system_surowy = _tekst(dane.get("system_rozliczen"))
	zasady = ""
	if system_surowy:
		if posiada == "PV":
			rozpoznane = normalizuj_system_rozliczen(system_surowy)
			if rozpoznane is None:
				uwagi_nierozpoznane.append("System rozliczen (nierozpoznane): %s" % system_surowy)
			else:
				zasady = rozpoznane
		else:
			uwagi_nierozpoznane.append("System rozliczen: %s" % system_surowy)

	# Produkt z reklamy
	produkt_surowy = _tekst(dane.get("produkt"))
	produkt = ""
	if produkt_surowy:
		rozpoznany = normalizuj_produkt_reklamy(produkt_surowy)
		if rozpoznany is None:
			uwagi_nierozpoznane.append("Produkt (nierozpoznany): %s" % produkt_surowy)
		else:
			produkt = rozpoznany

	# Data zgloszenia
	data_surowa = _tekst(dane.get("data_zgloszenia"))
	data = normalizuj_date_zgloszenia(data_surowa) if data_surowa else None
	if data is None:
		data = dzisiaj
		if data_surowa:
			uwagi_nierozpoznane.append("Data zgloszenia (nierozpoznana): %s" % data_surowa)
		else:
			uwagi_nierozpoznane.append("Data zgloszenia (brak): ustawiono date przyjecia")

	# Kod pocztowy (opcjonalny)
	kod_surowy = _tekst(dane.get("kod_pocztowy"))
	kod = ""
	if kod_surowy:
		kod = normalizuj_kod(kod_surowy) or ""
		if not kod:
			uwagi_nierozpoznane.append("Kod pocztowy (nierozpoznany): %s" % kod_surowy)

	linie = ["Zrodlo: Facebook Lead Ads"]
	formularz = _tekst(dane.get("formularz"))
	if formularz:
		linie.append("Formularz: %s" % formularz)
	kampania = _tekst(dane.get("kampania"))
	if kampania:
		linie.append("Kampania: %s" % kampania)
	linie.extend(uwagi_nierozpoznane)
	linie.extend("%s: %s" % (p, o) for p, o in splaszcz_odpowiedzi(dane.get("odpowiedzi")))

	wynik: dict[str, Any] = {
		"first_name": imie,
		"mobile_no": telefon,
		"source": ZRODLO_LEADA,
		"custom_import_source": TOKEN_ZRODLA_FB,
		"custom_import_date": data,
		"facebook_lead_id": id_leada,
		"custom_uwagi_import": SEPARATOR_UWAG.join(linie),
	}
	opcjonalne = {
		"last_name": nazwisko,
		"custom_install_city": _tekst(dane.get("miasto")),
		"custom_install_postal_code": kod,
		"custom_posiadane_produkty": posiada,
		"custom_zasady_dotacji": zasady,
		"custom_produkt_procesu": produkt,
		"facebook_form_id": _tekst(dane.get("facebook_form_id")),
	}
	return {**wynik, **{k: v for k, v in opcjonalne.items() if v}}
