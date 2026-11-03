# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Kalendarz spotkan handlowcow (ops#318): czysta logika bez `frappe`.

Spotkanie to `CRM Lead` z `custom_termin_spotkania` (Datetime) i `lead_owner`
(handlowiec). Modul celowo nie importuje ``frappe``: zakres uprawnien, daty,
walidacja zakresu i grupowanie da sie wtedy przetestowac lokalnie. Odczyt
bazy i `throw` mieszkaja w adapterze `crm/api/kalendarz.py`.
"""

import json
from datetime import date, datetime, timedelta

ZAKRES_WSZYSCY = "wszyscy"
ZAKRES_WLASNY = "wlasny"

ROLE_WSZYSCY: frozenset[str] = frozenset(
	{"System Manager", "Volteo Core Admin", "Volteo Backend", "Volteo Call Center"}
)
"""Role widzace tablice wszystkich handlowcow."""

ROLA_HANDLOWCA: str = "Volteo D2D Sales"
"""Rola handlowca: bez ról uprzywilejowanych widzi tylko wlasny kalendarz."""

MAKS_DNI_ZAKRESU: int = 62


def zakres_kalendarza(user: str, roles) -> str | None:
	""" "wszyscy" | "wlasny" | None (brak dostepu) dla `user` z rolami `roles`."""
	if user == "Administrator":
		return ZAKRES_WSZYSCY
	zbior = set(roles or ())
	if zbior & ROLE_WSZYSCY:
		return ZAKRES_WSZYSCY
	if ROLA_HANDLOWCA in zbior:
		return ZAKRES_WLASNY
	return None


def _parsuj_date(tekst) -> date:
	"""`YYYY-MM-DD` (rowniez z doklejona godzina) na `date`; ValueError przy bledzie."""
	if isinstance(tekst, datetime):
		return tekst.date()
	if isinstance(tekst, date):
		return tekst
	if not isinstance(tekst, str) or len(tekst.strip()) < 10:
		raise ValueError("Niepoprawna data (oczekiwano RRRR-MM-DD).")
	try:
		return date.fromisoformat(tekst.strip()[:10])
	except ValueError as exc:
		raise ValueError("Niepoprawna data (oczekiwano RRRR-MM-DD).") from exc


def zakres_tygodnia(data_iso: str) -> tuple[str, str]:
	"""(poniedzialek, niedziela) tygodnia zawierajacego `data_iso`, RRRR-MM-DD."""
	d = _parsuj_date(data_iso)
	poniedzialek = d - timedelta(days=d.weekday())
	niedziela = poniedzialek + timedelta(days=6)
	return poniedzialek.isoformat(), niedziela.isoformat()


def zakres_dnia(data_iso: str) -> tuple[str, str]:
	"""(dzien, dzien) dla widoku dnia."""
	d = _parsuj_date(data_iso).isoformat()
	return d, d


def waliduj_zakres_dat(od: str, do: str, max_dni: int = MAKS_DNI_ZAKRESU) -> None:
	"""ValueError przy zlym formacie, `od` > `do` albo zakresie ponad `max_dni` dni."""
	d_od = _parsuj_date(od)
	d_do = _parsuj_date(do)
	if d_od > d_do:
		raise ValueError("Data początkowa jest późniejsza niż końcowa.")
	if (d_do - d_od).days + 1 > max_dni:
		raise ValueError(f"Zakres dat jest zbyt duży (maksymalnie {max_dni} dni).")


def granice_czasu(od: str, do: str) -> tuple[str, str]:
	"""Granice Datetime dla filtra `between`: `od 00:00:00` i `do 23:59:59`."""
	return f"{_parsuj_date(od).isoformat()} 00:00:00", f"{_parsuj_date(do).isoformat()} 23:59:59"


def normalizuj_termin(termin) -> str | None:
	"""Termin z formularza na `RRRR-MM-DD GG:MM:SS`; pusty => None (czyszczenie).

	Przyjmuje separator spacje albo `T`, sekundy opcjonalne. ValueError przy
	niepoprawnym formacie.
	"""
	if termin is None:
		return None
	if isinstance(termin, datetime):
		return termin.strftime("%Y-%m-%d %H:%M:%S")
	if not isinstance(termin, str):
		raise ValueError("Niepoprawny termin spotkania.")
	tekst = termin.strip()
	if not tekst:
		return None
	tekst = tekst.replace("T", " ")
	for wzor in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
		try:
			return datetime.strptime(tekst, wzor).strftime("%Y-%m-%d %H:%M:%S")
		except ValueError:
			continue
	raise ValueError("Niepoprawny termin spotkania (oczekiwano RRRR-MM-DD GG:MM).")


def normalizuj_handlowcow(handlowcy) -> list[str]:
	"""Lista maili z JSON-a (string), listy albo pojedynczego stringa; bez duplikatow."""
	if handlowcy is None or handlowcy == "":
		return []
	if isinstance(handlowcy, str):
		tekst = handlowcy.strip()
		if not tekst:
			return []
		try:
			handlowcy = json.loads(tekst)
		except ValueError:
			handlowcy = [tekst]
	if isinstance(handlowcy, str):
		handlowcy = [handlowcy]
	if not isinstance(handlowcy, (list, tuple)):
		return []
	wynik: list[str] = []
	for h in handlowcy:
		if isinstance(h, str) and h.strip() and h.strip() not in wynik:
			wynik.append(h.strip())
	return wynik


def przetnij_handlowcow(zadani: list[str], dostepni: list[str]) -> list[str]:
	"""Czesc wspolna `zadani` i `dostepni`, w kolejnosci `dostepni`.

	Pusta lista `zadani` oznacza wszystkich dostepnych; nieznane maile sa pomijane.
	"""
	if not zadani:
		return list(dostepni)
	zbior = set(zadani)
	return [u for u in dostepni if u in zbior]


def _klucz_handlowca(h) -> str | None:
	if isinstance(h, str):
		return h
	if isinstance(h, dict):
		return h.get("user") or h.get("name")
	return None


def _klucz_terminu(wiersz) -> str:
	return str(wiersz.get("custom_termin_spotkania") or "")


def pogrupuj_spotkania(wiersze, handlowcy) -> dict:
	"""handlowiec -> lista wierszy posortowana po terminie.

	Kazdy handlowiec z `handlowcy` (maile albo slowniki z `user`) dostaje klucz,
	takze bez spotkan; kolejnosc zachowana. Wiersze bez terminu lub z wlascicielem
	spoza listy sa pomijane.
	"""
	wynik: dict[str, list] = {}
	for h in handlowcy or []:
		klucz = _klucz_handlowca(h)
		if klucz:
			wynik[klucz] = []
	for w in wiersze or []:
		if not w.get("custom_termin_spotkania"):
			continue
		wlasciciel = w.get("lead_owner")
		if wlasciciel in wynik:
			wynik[wlasciciel].append(w)
	for lista in wynik.values():
		lista.sort(key=_klucz_terminu)
	return wynik


# ---------------------------------------------------------------------------
# Grafik dostepnosci handlowcow (b82). Doctype `Volteo Dostepnosc` (tworzy
# skrypt ops, wzor w docs/ops/crm-dostepnosc.py): staly wzor tygodniowy
# (`dzien_tygodnia`) plus zmiany na konkretne dni (`data`, zastepuja wzor na
# ten dzien). Jeden wiersz = jedno okno `od`..`do` w pelnych godzinach albo
# dzien wolny (`wolne`). Dzien moze miec kilka okien (malowanie z przerwa).
# ---------------------------------------------------------------------------

DOCTYPE_DOSTEPNOSCI = "Volteo Dostepnosc"

ROLE_GRAFIKU: frozenset[str] = frozenset({"System Manager", "Volteo Core Admin", "Volteo Backend"})
"""Role, ktore wpisuja grafik (decyzja wlasciciela: handlowiec nie wpisuje)."""

DNI_TYGODNIA: tuple[str, ...] = (
	"Poniedziałek",
	"Wtorek",
	"Środa",
	"Czwartek",
	"Piątek",
	"Sobota",
	"Niedziela",
)
"""Literaly Select `dzien_tygodnia`; indeks = `date.weekday()` (jak `Volteo Dyzur SMS`)."""

ZAKRES_ZAPISU_STALY = "staly"
ZAKRES_ZAPISU_TYDZIEN = "tydzien"


def moze_edytowac_grafik(user: str, roles) -> bool:
	"""True dla Administratora i rol z `ROLE_GRAFIKU`."""
	if user == "Administrator":
		return True
	return bool(set(roles or ()) & ROLE_GRAFIKU)


def _godzina_calkowita(wartosc, nazwa: str) -> int:
	if isinstance(wartosc, bool):
		raise ValueError(f"Niepoprawna godzina {nazwa}.")
	if isinstance(wartosc, int):
		return wartosc
	if isinstance(wartosc, float) and wartosc.is_integer():
		return int(wartosc)
	if isinstance(wartosc, str) and wartosc.strip().isdigit():
		return int(wartosc.strip())
	raise ValueError(f"Niepoprawna godzina {nazwa} (oczekiwano pełnej godziny 0 do 24).")


def normalizuj_okna(okna) -> list[list[int]]:
	"""Lista okien `[od, do]` (pelne godziny, 0 <= od < do <= 24) posortowana i scalona.

	Okna nachodzace albo stykajace sie sa laczone w jedno. Pusta lista = dzien
	wolny. ValueError przy niepoprawnym wejsciu.
	"""
	if okna is None:
		return []
	if not isinstance(okna, (list, tuple)):
		raise ValueError("Niepoprawny grafik dnia.")
	pary: list[list[int]] = []
	for okno in okna:
		if not isinstance(okno, (list, tuple)) or len(okno) != 2:
			raise ValueError("Niepoprawne okno dostępności.")
		od = _godzina_calkowita(okno[0], "od")
		do = _godzina_calkowita(okno[1], "do")
		if not (0 <= od < do <= 24):
			raise ValueError("Godzina „do” musi być późniejsza niż „od” (zakres 0 do 24).")
		pary.append([od, do])
	pary.sort()
	wynik: list[list[int]] = []
	for od, do in pary:
		if wynik and od <= wynik[-1][1]:
			wynik[-1][1] = max(wynik[-1][1], do)
		else:
			wynik.append([od, do])
	return wynik


def normalizuj_tydzien(dni) -> list[list[list[int]]]:
	"""7 dni (pon..niedz) jako listy okien; przyjmuje JSON (string) albo liste."""
	if isinstance(dni, str):
		try:
			dni = json.loads(dni)
		except ValueError as exc:
			raise ValueError("Niepoprawny grafik tygodnia.") from exc
	if not isinstance(dni, (list, tuple)) or len(dni) != 7:
		raise ValueError("Grafik tygodnia musi mieć 7 dni.")
	return [normalizuj_okna(d) for d in dni]


def waliduj_wiersz_dostepnosci(dzien_tygodnia, data, wolne, od, do) -> str | None:
	"""Komunikat bledu wiersza `Volteo Dostepnosc` albo None, gdy poprawny.

	Wiersz wzoru ma `dzien_tygodnia` i pusta `data`; zmiana na dzien ma `data`
	(wtedy `dzien_tygodnia` jest ignorowany). Dzien wolny nie ma godzin.
	"""
	if not data and dzien_tygodnia not in DNI_TYGODNIA:
		return "Podaj dzień tygodnia (stały grafik) albo datę (zmiana na jeden dzień)."
	if data:
		try:
			_parsuj_date(str(data))
		except ValueError as exc:
			return str(exc)
	if wolne:
		return None
	try:
		normalizuj_okna([[od, do]])
	except ValueError as exc:
		return str(exc)
	return None


def dni_zakresu(od: str, do: str) -> list[str]:
	"""Kolejne daty `RRRR-MM-DD` od `od` do `do` wlacznie."""
	d_od, d_do = _parsuj_date(od), _parsuj_date(do)
	wynik = []
	while d_od <= d_do:
		wynik.append(d_od.isoformat())
		d_od += timedelta(days=1)
	return wynik


def _okna_z_wierszy(wiersze) -> list[list[int]]:
	"""Okna dnia z wierszy; wiersz `wolne` bez okien daje dzien wolny."""
	okna = []
	for w in wiersze:
		if w.get("wolne"):
			continue
		okna.append([w.get("od"), w.get("do")])
	try:
		return normalizuj_okna(okna)
	except ValueError:
		# Wiersz zepsuty recznie w Desku: pomin tylko zle okna, nie caly dzien.
		dobre = []
		for o in okna:
			try:
				dobre.extend(normalizuj_okna([o]))
			except ValueError:
				continue
		return normalizuj_okna(dobre)


def rozdziel_wiersze(wiersze) -> tuple[dict, dict]:
	"""(wzor: dzien_tygodnia -> okna, zmiany: data ISO -> okna) z wierszy jednego handlowca."""
	wzor_surowy: dict[str, list] = {}
	zmiany_surowe: dict[str, list] = {}
	for w in wiersze or []:
		data = w.get("data")
		if data:
			try:
				klucz = _parsuj_date(data if isinstance(data, (date, datetime)) else str(data)).isoformat()
			except ValueError:
				continue
			zmiany_surowe.setdefault(klucz, []).append(w)
		elif w.get("dzien_tygodnia") in DNI_TYGODNIA:
			wzor_surowy.setdefault(w["dzien_tygodnia"], []).append(w)
	wzor = {d: _okna_z_wierszy(lista) for d, lista in wzor_surowy.items()}
	zmiany = {d: _okna_z_wierszy(lista) for d, lista in zmiany_surowe.items()}
	return wzor, zmiany


def rozwin_dostepnosc(wiersze, dni_iso) -> dict | None:
	"""Dostepnosc handlowca na kazdy dzien `dni_iso`: {data: okna | None}.

	None zamiast slownika = handlowiec nie ma zadnego wiersza (brak grafiku).
	Dzien bez wzoru i bez zmiany dostaje None (traktowany jak brak grafiku dnia).
	Zmiana na dzien zastepuje wzor w calosci.
	"""
	if not wiersze:
		return None
	wzor, zmiany = rozdziel_wiersze(wiersze)
	wynik: dict[str, list | None] = {}
	for dzien in dni_iso:
		if dzien in zmiany:
			wynik[dzien] = zmiany[dzien]
		else:
			nazwa = DNI_TYGODNIA[_parsuj_date(dzien).weekday()]
			wynik[dzien] = wzor.get(nazwa)
	return wynik


def dostepnosc_handlowcow(wiersze, handlowcy, dni_iso) -> tuple[dict, dict]:
	"""({user: rozwin_dostepnosc}, {user: [daty ze zmiana]}) dla listy maili `handlowcy`."""
	po_userze: dict[str, list] = {u: [] for u in handlowcy}
	for w in wiersze or []:
		if w.get("handlowiec") in po_userze:
			po_userze[w["handlowiec"]].append(w)
	dostepnosc = {u: rozwin_dostepnosc(lista, dni_iso) for u, lista in po_userze.items()}
	zbior_dni = set(dni_iso)
	zmiany = {}
	for u, lista in po_userze.items():
		_, zm = rozdziel_wiersze(lista)
		zmiany[u] = sorted(d for d in zm if d in zbior_dni)
	return dostepnosc, zmiany


def wiersze_dnia(okna) -> list[dict]:
	"""Wiersze do zapisu dla jednego dnia: dzien wolny to jeden wiersz `wolne=1`."""
	okna = normalizuj_okna(okna)
	if not okna:
		return [{"wolne": 1, "od": None, "do": None}]
	return [{"wolne": 0, "od": od, "do": do} for od, do in okna]


def plan_zapisu(tydzien, zakres: str, poniedzialek: str, wzor_obecny: dict) -> dict:
	"""Co zapisac po edycji tygodnia `poniedzialek`..+6 (decyzja: staly wzor plus zmiany).

	`tydzien`: 7 list okien (pon..niedz). `wzor_obecny`: dzien_tygodnia -> okna.
	Zwraca {"wzor": 7 list okien albo None (bez zmiany wzoru),
	"usun_zmiany": [7 dat tygodnia], "zmiany": {data: okna}}.

	- "staly": tydzien staje sie wzorem; zmiany w tym tygodniu znikaja.
	- "tydzien": wzor bez zmian; zmiana tylko dla dni rozniacych sie od wzoru
	  (dzien rowny wzorowi traci ewentualna zmiane, wiec wraca do wzoru).
	"""
	tydzien = normalizuj_tydzien(tydzien)
	start = _parsuj_date(poniedzialek)
	if start.weekday() != 0:
		raise ValueError("Tydzień musi zaczynać się od poniedziałku.")
	daty = [(start + timedelta(days=i)).isoformat() for i in range(7)]
	if zakres == ZAKRES_ZAPISU_STALY:
		return {"wzor": tydzien, "usun_zmiany": daty, "zmiany": {}}
	if zakres != ZAKRES_ZAPISU_TYDZIEN:
		raise ValueError("Niepoprawny zakres zapisu (staly albo tydzien).")
	zmiany = {}
	for i, okna in enumerate(tydzien):
		wzor_dnia = (wzor_obecny or {}).get(DNI_TYGODNIA[i])
		if wzor_dnia is None or normalizuj_okna(wzor_dnia) != okna:
			zmiany[daty[i]] = okna
	return {"wzor": None, "usun_zmiany": daty, "zmiany": zmiany}
