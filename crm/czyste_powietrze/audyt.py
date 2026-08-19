# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Rdzeń audytu specjalnego Czyste Powietrze -- czysty, bez importu frappe.

Formularz audytu CP ma 7 slotów dokumentów (PDF/obraz, patrz `SLOTY_DOKUMENTOW`) plus
jedną grupę zdjęć (`KLUCZ_ZDJECIA`, min. 1, maks. `MAX_ZDJEC`). Każdy element (slot z
wgranym plikiem albo grupa zdjęć) dostaje osobny akcept/odrzut w `weryfikacja_json` --
brak wpisu oznacza "oczekuje". Cykl statusu audytu to Szkic -> Weryfikacja -> Zatwierdzony
(`STATUSY`).

Klucze slotów (`dok:*`) celowo pokrywają się z kluczami podzadań `dok:*` etapu
"Dokumentacja" w `crm.volteo_pipeline.PODZADANIA_CP` -- to świadomy wspólny wzorzec,
przygotowanie pod przyszły sync (patrz `test_audyt.py::test_klucze_pokrywaja_sie_z_pipeline`).
Moduł nie importuje `crm.volteo_pipeline` (i odwrotnie) -- kontrakt trzyma test, nie
zależność w kodzie.

Ten moduł nie importuje frappe, nie robi wejścia/wyjścia i nie mutuje żadnego argumentu
(patrz `resetuj_werdykty`) -- zgodnie z zasadą niemutowalności obowiązującą w projekcie."""

import json
from typing import Any

SLOTY_DOKUMENTOW: tuple[dict[str, Any], ...] = (
	{"klucz": "dok:ankieta_cp", "etykieta": "Ankieta danych Czyste Powietrze", "wymagany": True},
	{"klucz": "dok:gops_zaswiadczenie", "etykieta": "Zaświadczenie o dochodach", "wymagany": True},
	{"klucz": "dok:umowa_obsluga_dotacji", "etykieta": "Umowa na obsługę dotacji", "wymagany": True},
	{"klucz": "dok:pelnomocnictwo_notarialne", "etykieta": "Pełnomocnictwo notarialne", "wymagany": True},
	{"klucz": "dok:ankieta_trify", "etykieta": "Ankieta kredytowa", "wymagany": True},
	{"klucz": "dok:zgoda_wspolwlascicieli", "etykieta": "Zgoda współwłaścicieli", "wymagany": False},
	{"klucz": "dok:zgoda_wspolmalzonka", "etykieta": "Zgoda współmałżonka", "wymagany": False},
)
"""Katalog 7 slotów dokumentów audytu, w kolejności formularza. 5 wymaganych, 2 opcjonalne."""

KLUCZ_ZDJECIA = "dok:zdjecia"
ETYKIETA_ZDJECIA = "Dokumentacja zdjęciowa"

MAX_ZDJEC = 20
MAX_NOTATKA = 500

STATUSY: tuple[str, ...] = ("Szkic", "Weryfikacja", "Zatwierdzony")
"""Cykl statusu audytu specjalnego CP, w kolejności przejścia."""

WERDYKTY: tuple[str, ...] = ("accepted", "error")
"""Możliwe ostateczne werdykty per element weryfikacji (bez "waiting" -- to brak wpisu)."""

_KLUCZE_SLOTOW: frozenset[str] = frozenset(slot["klucz"] for slot in SLOTY_DOKUMENTOW)
_SLOTY_WG_KLUCZA: dict[str, dict[str, Any]] = {slot["klucz"]: slot for slot in SLOTY_DOKUMENTOW}
_STATUSY_WERDYKTU: frozenset[str] = frozenset({"accepted", "error", "waiting"})


def etykieta_dla(klucz: str) -> str:
	"""Zwraca polską etykietę slotu albo grupy zdjęć; dla nieznanego klucza zwraca sam klucz."""
	if klucz == KLUCZ_ZDJECIA:
		return ETYKIETA_ZDJECIA
	slot = _SLOTY_WG_KLUCZA.get(klucz)
	if slot is not None:
		return slot["etykieta"]
	return klucz


def _podwojnie_zdekodowany(raw: str) -> Any:
	"""Parsuje JSON, tolerując pojedyncze i podwójne zakodowanie; zwraca None przy porażce."""
	try:
		wartosc = json.loads(raw)
	except (TypeError, ValueError):
		return None
	if isinstance(wartosc, str):
		try:
			wartosc = json.loads(wartosc)
		except (TypeError, ValueError):
			return wartosc
	return wartosc


def parsuj_mape(surowe: Any) -> dict:
	"""Defensywnie zamienia `surowe` na płaski dict.

	Toleruje None, pusty string, poprawny dict (zwracany bez zmian), JSON-string i
	podwójnie zakodowany JSON-string. Wszystko inne (śmieci, liczby, listy, JSON, który
	dekoduje się do czegoś innego niż dict) daje pusty dict -- ta funkcja nigdy nie rzuca."""
	if surowe is None or surowe == "":
		return {}
	if isinstance(surowe, dict):
		return surowe
	if isinstance(surowe, str):
		wartosc = _podwojnie_zdekodowany(surowe)
		return wartosc if isinstance(wartosc, dict) else {}
	return {}


def parsuj_liste(surowe: Any) -> list[str]:
	"""Defensywnie zamienia `surowe` na listę stringów (URL-i).

	Toleruje None, pusty string, poprawną listę, JSON-string i podwójnie zakodowany
	JSON-string. Elementy listy, które nie są niepustym stringiem, są odfiltrowane --
	ta funkcja nigdy nie rzuca i zawsze zwraca listę."""
	if surowe is None or surowe == "":
		return []
	wartosc: Any = surowe
	if isinstance(surowe, str):
		wartosc = _podwojnie_zdekodowany(surowe)
	if not isinstance(wartosc, list):
		return []
	return [element for element in wartosc if isinstance(element, str) and element != ""]


def braki_do_przeslania(dokumenty: dict, zdjecia: list, plik_istnieje: Any) -> list[str]:
	"""Zwraca listę polskich etykiet braków blokujących submit audytu ([] = można wysłać).

	`plik_istnieje` to callback `url -> bool`, wołany dla każdego wgranego URL-a (slotu i
	zdjęcia) -- pozwala wołającemu zweryfikować istnienie pliku (np. przez `frappe.db`) bez
	wciągania frappe do tego modułu."""
	braki: list[str] = []

	for slot in SLOTY_DOKUMENTOW:
		klucz = slot["klucz"]
		url = dokumenty.get(klucz)
		if not url:
			if slot["wymagany"]:
				braki.append(slot["etykieta"])
			continue
		if not plik_istnieje(url):
			braki.append(f"{slot['etykieta']} (plik nie istnieje)")

	if len(zdjecia) == 0:
		braki.append(f"{ETYKIETA_ZDJECIA} (wymagane co najmniej 1 zdjęcie)")
	elif len(zdjecia) > MAX_ZDJEC:
		braki.append(f"{ETYKIETA_ZDJECIA} (przekroczono limit {MAX_ZDJEC} zdjęć)")

	for url in zdjecia:
		if not plik_istnieje(url):
			braki.append(f"{ETYKIETA_ZDJECIA} (plik nie istnieje: {url})")

	return braki


def elementy_weryfikacji(dokumenty: dict, zdjecia: list) -> list[str]:
	"""Zwraca klucze aktualnych elementów podlegających weryfikacji, w stałej kolejności.

	Sloty z wgranym plikiem (w kolejności katalogu `SLOTY_DOKUMENTOW`), a na końcu zawsze
	`KLUCZ_ZDJECIA` -- grupa zdjęć jest elementem zawsze, bo co najmniej jedno zdjęcie jest
	wymagane do przesłania audytu."""
	elementy = [slot["klucz"] for slot in SLOTY_DOKUMENTOW if dokumenty.get(slot["klucz"])]
	elementy.append(KLUCZ_ZDJECIA)
	return elementy


def agreguj(weryfikacja: dict, elementy: list[str]) -> dict:
	"""Agreguje stan werdyktów po bieżących elementach weryfikacji.

	Zwraca {"razem", "zaakceptowane", "bledy", "oczekuje", "wszystkie_zaakceptowane"}.
	Gdy `elementy` jest puste, "wszystkie_zaakceptowane" jest False (nie ma czego uznać za
	skompletowane -- pusty zbiór nie powinien wyglądać jak sukces)."""
	razem = len(elementy)
	zaakceptowane = 0
	bledy = 0
	for klucz in elementy:
		wpis = weryfikacja.get(klucz)
		status = wpis.get("status") if isinstance(wpis, dict) else None
		if status == "accepted":
			zaakceptowane += 1
		elif status == "error":
			bledy += 1
	oczekuje = razem - zaakceptowane - bledy
	return {
		"razem": razem,
		"zaakceptowane": zaakceptowane,
		"bledy": bledy,
		"oczekuje": oczekuje,
		"wszystkie_zaakceptowane": razem > 0 and zaakceptowane == razem,
	}


def waliduj_werdykt(klucz: str, status: str, notatka: Any, dokumenty: dict, zdjecia: list) -> dict:
	"""Waliduje i normalizuje jeden werdykt weryfikacji, podnosząc `ValueError` z polskim
	komunikatem gdy dane są niepoprawne. Zwraca znormalizowany wpis: {"status": ...} dla
	"waiting" (bez "note" -- interpretowane przez wołającego jako usunięcie werdyktu), albo
	{"status": ..., "note": ...} dla "accepted"/"error" (`note` zawsze obecne, pusty string
	dla "accepted" bez notatki)."""
	elementy = elementy_weryfikacji(dokumenty, zdjecia)
	if klucz not in elementy:
		raise ValueError(f"Element weryfikacji {klucz} nie jest aktualnie dostępny do oceny.")

	if status not in _STATUSY_WERDYKTU:
		raise ValueError(f"Nieznany status weryfikacji: {status}.")

	if status == "waiting":
		return {"status": "waiting"}

	tekst_notatki = notatka.strip() if isinstance(notatka, str) else ""

	if status == "error" and tekst_notatki == "":
		raise ValueError("Odrzucenie elementu wymaga podania notatki.")

	if len(tekst_notatki) > MAX_NOTATKA:
		raise ValueError(f"Notatka nie może przekraczać {MAX_NOTATKA} znaków.")

	return {"status": status, "note": tekst_notatki}


def _zbior_zdjec_zmieniony(stare_zdj: list, nowe_zdj: list) -> bool:
	# Porównanie ZBIORÓW (kolejność bez znaczenia) -- permutacja tych samych URL-i nie
	# jest zmianą.
	return set(stare_zdj) != set(nowe_zdj)


def resetuj_werdykty(
	stare_dok: dict,
	nowe_dok: dict,
	stare_zdj: list,
	nowe_zdj: list,
	weryfikacja: dict,
) -> tuple[dict, list[str]]:
	"""Resetuje werdykty elementów, których źródłowy dokument/zdjęcia się zmieniły.

	Czysta funkcja: nie mutuje żadnego z argumentów, zwraca (nowa_mapa_weryfikacji,
	komunikaty). Dla slotu, którego URL się zmienił (dodany/usunięty/podmieniony), usuwa
	jego werdykt z KOPII `weryfikacja` i dodaje jeden polski komunikat. Dla zdjęć porównuje
	zbiory URL-i (kolejność bez znaczenia); przy zmianie usuwa werdykt `KLUCZ_ZDJECIA` i
	dodaje jeden komunikat zbiorczy. Werdykty elementów nieobjętych zmianą przeżywają
	niezmienione."""
	nowa_mapa = dict(weryfikacja)
	komunikaty: list[str] = []

	for slot in SLOTY_DOKUMENTOW:
		klucz = slot["klucz"]
		stary_url = stare_dok.get(klucz)
		nowy_url = nowe_dok.get(klucz)
		if stary_url == nowy_url:
			continue

		nowa_mapa.pop(klucz, None)
		etykieta = slot["etykieta"]
		if not stary_url and nowy_url:
			komunikaty.append(f"Dodano dokument audytu: {etykieta}")
		elif stary_url and not nowy_url:
			komunikaty.append(f"Usunięto dokument audytu: {etykieta}")
		else:
			komunikaty.append(f"Zmieniono dokument audytu: {etykieta}")

	if _zbior_zdjec_zmieniony(stare_zdj, nowe_zdj):
		nowa_mapa.pop(KLUCZ_ZDJECIA, None)
		komunikaty.append("Zmieniono dokumentację zdjęciową audytu")

	return nowa_mapa, komunikaty
