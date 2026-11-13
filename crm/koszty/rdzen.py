"""Rdzeń snapshotu kosztów/marży (schema v1), zapisywanego na `CRM Deal` w polach
permlevel-2 (`custom_koszty_json`, `custom_koszty_zysk_plan`,
`custom_koszty_zysk_rzeczywisty`; pola tworzy osobny skrypt ops, nie ten moduł).

Frappe-free: wyłącznie stdlib (`decimal`, `typing`) -- analogicznie do
`crm/czyste_powietrze/obliczenia.py`, testowalny bez instalacji Frappe.

Dwie odpowiedzialności, ostro rozdzielone:

- `zbuduj_snapshot_cp` buduje snapshot v1 z wyniku AUTORYTATYWNEGO przeliczenia
  serwerowego kalkulatora Czyste Powietrze (`wynik["wewnetrzne"]`, patrz
  `crm/czyste_powietrze/obliczenia.py::oblicz_oferte`) w chwili tworzenia
  szansy. Snapshot niesie wyłącznie wartości KATALOGOWE tego przeliczenia --
  sandboxowe nadpisania stawek/kosztów administratora w przeglądarce
  (`frontend/src/utils/cpMarza.js`, piaskownica modelowania prowizji) są
  wyłącznie podglądem "co jeśli" na ekranie administratora i NIGDY nie trafiają
  do tego modułu ani do zapisanego snapshotu -- nic z tamtej arytmetyki nie
  jest utrwalane.
- `scal_snapshot` łączy ZAPISANY snapshot z edycją "kosztów rzeczywistych"
  administratora (zakładki Zestaw -- panel kosztów na dole zakładki, przez
  `crm/api/koszty.py`). Hostile-payload-proof: `wersja`, `linia_produktowa`, `utworzono` oraz
  wszystkie pola PLANU każdej linii (`klucz`, `etykieta`, `ilosc`, `jednostka`,
  `netto`, `prowizja_plan`, `koszt_plan`), `skladniki_marzy` i `podsumowanie`
  są zawsze kopiowane z ZAPISANEGO snapshotu -- nigdy z wejścia klienta.
  Wejście klienta może wpłynąć wyłącznie na `koszt_rzeczywisty` per linia i na
  listę `dodatkowe`.
"""

import copy
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

WERSJA = 1

KLUCZ_KOREKTY_SUMY = "korekta_sumy_plan"
ETYKIETA_KOREKTY_SUMY = "Korekta sumy kosztów planowanych"
LINIE_EDYTOWALNE_PLANU = ("pv", "oze")

_KWANT = Decimal("0.01")
_ZERO = Decimal("0.00")


def _jako_decimal(wartosc: Any) -> Decimal:
	"""Koercja do `Decimal` bez zaokrąglania -- używana dla ILOŚCI (nie kwot),
	które mogą mieć więcej niż 2 miejsca po przecinku (np. powierzchnia w m²)."""
	try:
		wynik = Decimal(str(wartosc))
	except (ArithmeticError, TypeError, ValueError):
		raise ValueError(f"Nieprawidłowa wartość liczbowa: {wartosc!r}.") from None
	if not wynik.is_finite():
		raise ValueError(f"Nieprawidłowa wartość liczbowa: {wartosc!r}.")
	return wynik


def _kwota(wartosc: Any) -> Decimal:
	"""Koercja do `Decimal` + zaokrąglenie do grosza (ROUND_HALF_UP) -- zgodnie
	z konwencją `crm/czyste_powietrze/obliczenia.py::_kwota`. Zaokrąglenie
	dzieje się tu w LIŚCIU: wejścia tej funkcji są już kwotami jednostkowymi
	albo sumami już-zaokrąglonych kwot, nigdy pośrednimi kandydatami wyceny."""
	return _jako_decimal(wartosc).quantize(_KWANT, rounding=ROUND_HALF_UP)


def _str_kwota(wartosc: Any) -> str:
	return str(_kwota(wartosc))


def _parsuj_kwote_klienta(wartosc: Any) -> Decimal:
	"""Parsuje kwotę przesłaną przez przeglądarkę (str/int/float), lustrzane
	zasady wobec `frontend/src/utils/cpMarza.js` (`parsujStawke`/`parsujKwote`):
	spacje zwykłe i nierozdzielające (`\\xa0`) są usuwane, przecinek zamienia
	się na kropkę, wynik musi być SKOŃCZONĄ liczbą >= 0.

	W odróżnieniu od `cpMarza.js` -- który po cichu zamienia śmieciowe wejście
	na 0, bo to tylko podgląd na żywo -- ta funkcja rzuca `ValueError` na
	śmieciowym/ujemnym/nieskończonym wejściu: to jest ścieżka ZAPISU, nie
	podgląd, więc niepoprawne dane muszą zablokować zapis, nie po cichu
	wyzerować kwotę.
	"""
	if isinstance(wartosc, bool):
		raise ValueError("Nieprawidłowa kwota.")
	if isinstance(wartosc, (int, float, Decimal)):
		try:
			dec = Decimal(str(wartosc))
		except (ArithmeticError, ValueError):
			raise ValueError("Nieprawidłowa kwota.") from None
	elif isinstance(wartosc, str):
		bez_spacji = wartosc.replace("\xa0", "").replace(" ", "").strip()
		if not bez_spacji:
			raise ValueError("Nieprawidłowa kwota.")
		znormalizowany = bez_spacji.replace(",", ".")
		try:
			dec = Decimal(znormalizowany)
		except InvalidOperation:
			raise ValueError("Nieprawidłowa kwota.") from None
	else:
		raise ValueError("Nieprawidłowa kwota.")

	if not dec.is_finite() or dec < 0:
		raise ValueError("Nieprawidłowa kwota.")
	return dec.quantize(_KWANT, rounding=ROUND_HALF_UP)


def zbuduj_snapshot_cp(wewnetrzne: dict[str, Any], nazwy: dict[str, str], utworzono: str) -> dict[str, Any]:
	"""Buduje snapshot v1 (`linia_produktowa="cp"`) z `wynik["wewnetrzne"]` -- kształt
	dokumentowany w `crm/czyste_powietrze/obliczenia.py` (ok. linii 500-560):
	`{koszt_calkowity, marza, prowizja_handlowa, nadprowizja_manager,
	nadprowizja_partner, prowizja_pelna, zysk, linie: [{kod, ilosc_rozliczeniowa,
	jednostka_rozliczeniowa, netto, koszt, ..., prowizja_pelna}]}`, wszystkie kwoty
	już zaokrąglone do grosza przez rdzeń kalkulatora. `zysk` jest tam już liczony jako
	`marza - prowizja_pelna` (nadprowizje Managera/Partnera wliczone), więc
	`podsumowanie.zysk_plan` niżej jest sumą pełną bez dodatkowej arytmetyki tutaj.

	Snapshot niesie wyłącznie wartości z tego AUTORYTATYWNEGO przeliczenia
	serwerowego w chwili wywołania -- sandboxowe nadpisania administratora w
	przeglądarce (`frontend/src/utils/cpMarza.js`) są osobnym, nietrwałym
	podglądem "co jeśli" i nigdy nie docierają do tej funkcji ani do
	zapisanego snapshotu.

	`etykieta` używa `nazwy.get(kod) or kod`: `nazwy` może mieć klucz obecny,
	ale pusty (nazwa pozycji katalogowej niewypełniona) -- `.get()` sam w sobie
	zwróciłby wtedy ten pusty string zamiast czytelnego fallbacku na kod
	katalogowy (identyczne rozumowanie co przy zapisie `custom_zestaw` w
	`crm/api/czyste_powietrze.py::volteo_cp_create_deal`).

	Żaden z argumentów nie jest mutowany.
	"""
	linie = [
		{
			"klucz": linia["kod"],
			"etykieta": nazwy.get(linia["kod"]) or linia["kod"],
			"ilosc": str(_jako_decimal(linia["ilosc_rozliczeniowa"])),
			"jednostka": linia["jednostka_rozliczeniowa"],
			"netto": _str_kwota(linia["netto"]),
			"prowizja_plan": _str_kwota(linia["prowizja_pelna"]),
			"koszt_plan": _str_kwota(linia["koszt"]),
			"koszt_rzeczywisty": None,
		}
		for linia in wewnetrzne.get("linie", [])
	]

	suma_netto = sum((Decimal(linia["netto"]) for linia in linie), _ZERO)

	return {
		"wersja": WERSJA,
		"linia_produktowa": "cp",
		"utworzono": utworzono,
		"zmodyfikowano": None,
		"zmodyfikowal": None,
		"linie": linie,
		"skladniki_marzy": [],
		"dodatkowe": [],
		"podsumowanie": {
			"netto": _str_kwota(suma_netto),
			"koszt_plan": _str_kwota(wewnetrzne["koszt_calkowity"]),
			"marza_plan": _str_kwota(wewnetrzne["marza"]),
			# "prowizja_plan" nosi teraz PEŁNĄ prowizję (handlowiec + obie nadprowizje), nie
			# samą prowizję handlowca -- lustrzane wobec zmiany "prowizja" -> "prowizja_pelna"
			# na liniach wyżej, tak żeby suma linii nadal zgadzała się z podsumowaniem.
			"prowizja_plan": _str_kwota(wewnetrzne["prowizja_pelna"]),
			# "zysk_plan" pozostaje = wewnetrzne["zysk"], które rdzeń kalkulatora liczy już
			# jako marza - prowizja_pelna (patrz obliczenia.py) -- żadna dodatkowa arytmetyka
			# nadprowizji nie jest tu potrzebna.
			"zysk_plan": _str_kwota(wewnetrzne["zysk"]),
		},
		"podsumowanie_rzeczywiste": None,
	}


def zbuduj_snapshot_oze(wewnetrzne: dict[str, Any], utworzono: str) -> dict[str, Any]:
	"""Buduje snapshot v1 (`linia_produktowa="oze"`) z `wynik["wewnetrzne"]` wyniku
	`crm.volteo_kalkulator_oze.oblicz_oferte` (jeden z czterech nowych rodzajów instalacji:
	Rozbudowa PV/ME, Klimatyzacja, Pompa ciepła, Kocioł; b68, issue ops#222) -- kształt
	dokumentowany w `crm/volteo_kalkulator_oze.py`: `{koszt_calkowity, marza_proenergy,
	bonus_liderski, narzut, marza, zysk, linie: [{klucz, etykieta, typ, kwota}], pozycje: [...]}`.

	Tylko linie typu `"Koszt"` trafiają do `snapshot["linie"]` -- linie typu `"Marża
	Proenergy"`/`"Bonus liderski"` już mają swoją agregatową reprezentację w
	`skladniki_marzy` (plus `"narzut"`, który NIE jest linią `wewnetrzne["linie"]` wcale,
	bo to pole wejściowe handlowca, nie pozycja katalogowa) -- identyczna konwencja co
	`ops/crm-kalkulator-bom.py`'s `koszty_linie`/`skladniki_marzy` dla silnika PV: `ilosc`,
	`jednostka`, `netto` i `prowizja_plan` są tu zawsze `None` (te linie nie mają własnej
	ceny klienta rozbitej per pozycja na poziomie snapshotu -- tylko koszt).

	`podsumowanie.zysk_plan` jest tu RÓWNE `marza_plan` (nie wewnętrznemu `wewnetrzne["zysk"]`,
	które w kalkulatorze OZE świadomie WYKLUCZA narzut handlowca z zysku firmy -- patrz
	docstring `crm/volteo_kalkulator_oze.py::oblicz_oferte`) -- to jest ŚWIADOMA decyzja
	zgodności z istniejącym precedensem: `podsumowanie.prowizja_plan` jest `None` (tak jak w
	snapshotach PV), a `scal_snapshot`/`_oblicz_podsumowanie_rzeczywiste` niżej liczy
	`zysk = marza - prowizja` z `prowizja` domyślnie `0`, gdy `prowizja_plan` jest `None` --
	więc `zysk_plan` RÓWNE `marza_plan` tutaj jest jedyną wartością zgodną z tym, jak reszta
	modułu (i Zestaw tab) interpretuje snapshot z `prowizja_plan=None` gdziekolwiek indziej.
	Rozbieżność między tym a `wewnetrzne["zysk"]` (który jest wyłącznie podglądem na żywo w
	panelu admina kalkulatora, nigdy nie trafia do żadnego snapshotu) jest opisana w raporcie
	agenta, który dodał tę funkcję -- do potwierdzenia, czy to właściwa interpretacja.

	Żaden argument nie jest mutowany.
	"""
	linie = [
		{
			"klucz": linia["klucz"],
			"etykieta": linia["etykieta"],
			"ilosc": None,
			"jednostka": None,
			"netto": None,
			"prowizja_plan": None,
			"koszt_plan": _str_kwota(linia["kwota"]),
			"koszt_rzeczywisty": None,
		}
		for linia in wewnetrzne.get("linie", [])
		if linia["typ"] == "Koszt"
	]

	koszt_plan = _kwota(wewnetrzne["koszt_calkowity"])
	marza_proenergy = _kwota(wewnetrzne["marza_proenergy"])
	bonus_liderski = _kwota(wewnetrzne["bonus_liderski"])
	narzut = _kwota(wewnetrzne["narzut"])
	netto = _kwota(koszt_plan + marza_proenergy + bonus_liderski + narzut)
	marza_plan = _kwota(netto - koszt_plan)

	return {
		"wersja": WERSJA,
		"linia_produktowa": "oze",
		"utworzono": utworzono,
		"zmodyfikowano": None,
		"zmodyfikowal": None,
		"linie": linie,
		"skladniki_marzy": [
			{"klucz": "marza_proenergy", "etykieta": "Marża ProEnergy", "kwota": _str_kwota(marza_proenergy)},
			{"klucz": "bonus_liderski", "etykieta": "Bonus liderski", "kwota": _str_kwota(bonus_liderski)},
			{"klucz": "narzut", "etykieta": "Narzut handlowca", "kwota": _str_kwota(narzut)},
		],
		"dodatkowe": [],
		"podsumowanie": {
			"netto": _str_kwota(netto),
			"koszt_plan": _str_kwota(koszt_plan),
			"marza_plan": _str_kwota(marza_plan),
			"prowizja_plan": None,
			"zysk_plan": _str_kwota(marza_plan),
		},
		"podsumowanie_rzeczywiste": None,
	}


def _scal_dodatkowe(
	stare: list[dict[str, Any]],
	nowe: list[dict[str, Any]],
	teraz: str,
	uzytkownik: str,
) -> list[dict[str, Any]]:
	"""Zastępuje CAŁĄ listę `dodatkowe` nową listą, zachowując `autor`/`utworzono`
	istniejących wpisów rozpoznanych po `id`. Nowe wpisy (bez `id` albo z `id`
	nieznanym zapisanemu snapshotowi) dostają deterministyczny identyfikator
	`"d-<n>"`, gdzie `n` to maksymalny dotychczasowy numeryczny sufiks + 1 --
	deterministyczne generowanie bije znacznik czasu ściany (łatwe do
	przetestowania, nie zależy od zegara) i jest jedynym sensownym wyborem w
	module bez dostępu do żadnego licznika/zegara systemowego.
	"""
	if not isinstance(nowe, list):
		raise ValueError("Nieprawidłowy format listy dodatkowych pozycji.")

	# Obrona przed zdegenerowanym payloadem: to samo `id` powtórzone w `nowe` (np.
	# przypadkowe podwójne wysłanie tego samego wiersza formularza) zmapowałoby DWA
	# wpisy na ten sam zapisany rekord `stare_wg_id[id]`, dając na wyjściu dwa wpisy
	# o identycznym `id` -- kolejna edycja nie wiedziałaby już, którego z nich dotyczy
	# zmiana. Sprawdzamy PRZED zbudowaniem czegokolwiek, więc payload jest odrzucany
	# w całości, a nie po cichu okaleczony.
	widziane_id: set[str] = set()
	for wpis in nowe:
		if not isinstance(wpis, dict):
			continue
		id_wejscia = wpis.get("id")
		if isinstance(id_wejscia, str):
			if id_wejscia in widziane_id:
				raise ValueError(f"Zduplikowany identyfikator dodatkowej pozycji: {id_wejscia}.")
			widziane_id.add(id_wejscia)

	stare_wg_id = {wpis["id"]: wpis for wpis in stare if isinstance(wpis, dict) and isinstance(wpis.get("id"), str)}

	nastepny_numer = 1
	for wpis in stare:
		if not isinstance(wpis, dict):
			continue
		id_ = wpis.get("id")
		if isinstance(id_, str) and id_.startswith("d-"):
			try:
				nastepny_numer = max(nastepny_numer, int(id_[2:]) + 1)
			except ValueError:
				continue

	wynik: list[dict[str, Any]] = []
	for wpis in nowe:
		if not isinstance(wpis, dict):
			raise ValueError("Nieprawidłowy wpis dodatkowej pozycji.")

		nazwa_surowa = wpis.get("nazwa")
		if not isinstance(nazwa_surowa, str):
			raise ValueError("Nazwa dodatkowej pozycji musi być tekstem.")
		nazwa = nazwa_surowa.strip()
		if not nazwa:
			raise ValueError("Nazwa dodatkowej pozycji nie może być pusta.")
		if len(nazwa) > 140:
			raise ValueError("Nazwa dodatkowej pozycji jest za długa (maks. 140 znaków).")

		kwota = _parsuj_kwote_klienta(wpis.get("kwota"))

		id_wejscia = wpis.get("id")
		istniejacy = stare_wg_id.get(id_wejscia) if isinstance(id_wejscia, str) else None
		if istniejacy is not None:
			wynik.append(
				{
					"id": istniejacy["id"],
					"nazwa": nazwa,
					"kwota": str(kwota),
					"autor": istniejacy.get("autor"),
					"utworzono": istniejacy.get("utworzono"),
				}
			)
		else:
			nowy_id = f"d-{nastepny_numer}"
			nastepny_numer += 1
			wynik.append(
				{
					"id": nowy_id,
					"nazwa": nazwa,
					"kwota": str(kwota),
					"autor": uzytkownik,
					"utworzono": teraz,
				}
			)
	return wynik


def _oblicz_podsumowanie_rzeczywiste(snapshot: dict[str, Any]) -> dict[str, Any]:
	"""Liczy `podsumowanie_rzeczywiste` z linii/dodatkowych JUŻ scalonych do
	`snapshot`. `podsumowanie.netto` jest kopiowane z zapisanego snapshotu
	(plan), nigdy przeliczane na nowo -- to jedyne źródło prawdy o cenie
	klienta, ustalone raz przy tworzeniu szansy."""
	koszt_total = _ZERO
	pozycje_wg_planu = 0
	for linia in snapshot["linie"]:
		koszt_rzeczywisty = linia.get("koszt_rzeczywisty")
		if koszt_rzeczywisty is None:
			koszt_total += Decimal(linia["koszt_plan"])
			pozycje_wg_planu += 1
		else:
			koszt_total += Decimal(koszt_rzeczywisty)
	for wpis in snapshot.get("dodatkowe") or []:
		koszt_total += Decimal(wpis["kwota"])
	koszt_total = _kwota(koszt_total)

	netto = Decimal(snapshot["podsumowanie"]["netto"])
	marza = _kwota(netto - koszt_total)

	prowizja_plan = snapshot["podsumowanie"].get("prowizja_plan")
	prowizja = Decimal(prowizja_plan) if prowizja_plan is not None else _ZERO
	zysk = _kwota(marza - prowizja)

	return {
		"koszt_rzeczywisty": str(koszt_total),
		"marza_rzeczywista": str(marza),
		"zysk_rzeczywisty": str(zysk),
		"pozycje_wg_planu": pozycje_wg_planu,
	}


def scal_snapshot(
	snapshot: dict[str, Any],
	koszty_rzeczywiste: dict[str, Any],
	dodatkowe: list[dict[str, Any]],
	teraz: str,
	uzytkownik: str,
) -> dict[str, Any]:
	"""Zwraca NOWY snapshot zbudowany z zapisanego `snapshot`, z naniesioną
	edycją kosztów rzeczywistych administratora. `snapshot` nie jest mutowany.

	`koszty_rzeczywiste`: mapa klucz -> (kwota | `None`). Każdy klucz MUSI
	pasować do jednej z `snapshot["linie"][i]["klucz"]`, inaczej `ValueError`
	nazywa nieznany klucz po polsku. `None` czyści koszt rzeczywisty (powrót do
	fallbacku na plan). Linie pominięte w mapie zachowują swój zapisany koszt
	rzeczywisty bez zmian.

	`dodatkowe`: PEŁNE zastąpienie listy dodatkowych pozycji kosztowych --
	patrz `_scal_dodatkowe`.

	Wszystkie pola PLANU (wersja, linia_produktowa, utworzono, pola planu
	każdej linii, skladniki_marzy, podsumowanie) są kopiowane z zapisanego
	`snapshot` -- odporne na wrogi payload, bo `koszty_rzeczywiste`/`dodatkowe`
	fizycznie nie mają jak wpłynąć na te pola.
	"""
	stare_linie = snapshot.get("linie") or []
	klucze_znane = {linia["klucz"] for linia in stare_linie}

	if not isinstance(koszty_rzeczywiste, dict):
		raise ValueError("Nieprawidłowy format kosztów rzeczywistych.")
	for klucz in koszty_rzeczywiste:
		if klucz not in klucze_znane:
			raise ValueError(f"Nieznana pozycja kosztorysu: {klucz}.")

	nowe_linie = []
	for linia in stare_linie:
		klucz = linia["klucz"]
		nowa_linia = {
			"klucz": linia["klucz"],
			"etykieta": linia["etykieta"],
			"ilosc": linia["ilosc"],
			"jednostka": linia["jednostka"],
			"netto": linia["netto"],
			"prowizja_plan": linia["prowizja_plan"],
			"koszt_plan": linia["koszt_plan"],
			"koszt_rzeczywisty": linia.get("koszt_rzeczywisty"),
		}
		if linia.get("koszt_plan_pierwotny") is not None:
			# Pierwotny koszt planowany linii (edycja planu, ops#335) przeżywa edycję kosztów rzeczywistych.
			nowa_linia["koszt_plan_pierwotny"] = linia["koszt_plan_pierwotny"]
		if klucz in koszty_rzeczywiste:
			wartosc = koszty_rzeczywiste[klucz]
			if klucz == KLUCZ_KOREKTY_SUMY:
				if wartosc is not None:
					raise ValueError("Korekty sumy kosztów planowanych nie edytuje się jako kosztu rzeczywistego.")
				nowe_linie.append(nowa_linia)
				continue
			nowa_linia["koszt_rzeczywisty"] = None if wartosc is None else str(_parsuj_kwote_klienta(wartosc))
		nowe_linie.append(nowa_linia)

	nowe_dodatkowe = _scal_dodatkowe(snapshot.get("dodatkowe") or [], dodatkowe, teraz, uzytkownik)

	nowy = {
		"wersja": snapshot["wersja"],
		"linia_produktowa": snapshot["linia_produktowa"],
		"utworzono": snapshot["utworzono"],
		"zmodyfikowano": teraz,
		"zmodyfikowal": uzytkownik,
		"linie": nowe_linie,
		"skladniki_marzy": list(snapshot.get("skladniki_marzy") or []),
		"dodatkowe": nowe_dodatkowe,
		"podsumowanie": dict(snapshot["podsumowanie"]),
		"podsumowanie_rzeczywiste": None,
	}
	if snapshot.get("edycja_reczna") is not None:
		# Ślad ręcznej edycji zestawu (ops#270) przeżywa późniejszą edycję kosztów.
		nowy["edycja_reczna"] = dict(snapshot["edycja_reczna"])
	if snapshot.get("edycja_planu") is not None:
		# Ślad edycji kosztów planowanych (ops#335) też przeżywa edycję kosztów rzeczywistych.
		nowy["edycja_planu"] = dict(snapshot["edycja_planu"])
	nowy["podsumowanie_rzeczywiste"] = _oblicz_podsumowanie_rzeczywiste(nowy)
	return nowy


def aktualizuj_po_edycji_zestawu(
	snapshot: dict[str, Any] | None,
	netto_nowe: Any,
	kto: str,
	kiedy: str,
	powod: str | None = None,
) -> dict[str, Any] | None:
	"""Zwraca NOWY snapshot po ręcznej edycji zestawu/ceny przez administrację (ops#270).

	`None` lub pusty snapshot (stare szanse bez snapshotu) daje `None` -- nic do
	aktualizacji, bez błędu. Nie dotyka `linie`, `dodatkowe` ani `skladniki_marzy`
	(linie PV to kubełki kosztów, nie wiersze zestawu; nie ma klucza, po którym dałoby się
	je dopasować). Przelicza `podsumowanie`: `netto` = `netto_nowe`, `marza_plan = netto -
	koszt_plan`, `zysk_plan = marza_plan - prowizja_plan` (gdy `prowizja_plan` jest `None`,
	`zysk_plan = marza_plan`, jak dla snapshotów OZE). `podsumowanie_rzeczywiste` liczone
	tym samym wzorem co po edycji kosztów, ale tylko gdy już istniało (wcześniej `None` =
	koszty rzeczywiste nigdy nie edytowane, zostaje `None`).

	Dodaje `edycja_reczna: {kiedy, kto, powod, netto_przed, netto_pierwotne}`; nadpisywane
	przy kolejnej edycji, `netto_pierwotne` (netto sprzed PIERWSZEJ edycji) zostaje
	zachowane. Wejście nie jest mutowane.
	"""
	if not snapshot:
		return None
	netto_przed = snapshot["podsumowanie"]["netto"]
	poprzednia = snapshot.get("edycja_reczna") or {}
	netto = _kwota(netto_nowe)
	koszt_plan = _kwota(snapshot["podsumowanie"]["koszt_plan"])
	marza_plan = _kwota(netto - koszt_plan)
	prowizja_plan = snapshot["podsumowanie"].get("prowizja_plan")
	prowizja = _kwota(prowizja_plan) if prowizja_plan is not None else _ZERO
	zysk_plan = _kwota(marza_plan - prowizja)

	nowy = copy.deepcopy(snapshot)
	nowy["zmodyfikowano"] = kiedy
	nowy["zmodyfikowal"] = kto
	nowy["podsumowanie"] = {
		**snapshot["podsumowanie"],
		"netto": str(netto),
		"marza_plan": str(marza_plan),
		"zysk_plan": str(zysk_plan),
	}
	nowy["edycja_reczna"] = {
		"kiedy": kiedy,
		"kto": kto,
		"powod": (powod or "").strip(),
		"netto_przed": str(netto_przed),
		"netto_pierwotne": str(poprzednia.get("netto_pierwotne") or netto_przed),
	}
	if snapshot.get("podsumowanie_rzeczywiste") is not None:
		nowy["podsumowanie_rzeczywiste"] = _oblicz_podsumowanie_rzeczywiste(nowy)
	return nowy


def _linia_korekty(kwota: Decimal) -> dict[str, Any]:
	return {
		"klucz": KLUCZ_KOREKTY_SUMY,
		"etykieta": ETYKIETA_KOREKTY_SUMY,
		"ilosc": None,
		"jednostka": None,
		"netto": None,
		"prowizja_plan": None,
		"koszt_plan": str(_kwota(kwota)),
		"koszt_rzeczywisty": None,
	}


def zmien_koszty_planowane(
	snapshot: dict[str, Any] | None,
	koszty_plan: dict[str, Any],
	suma_plan: Any,
	teraz: str,
	uzytkownik: str,
) -> dict[str, Any]:
	"""Zwraca NOWY snapshot po edycji kosztów PLANOWANYCH przez administratora (ops#335).
	Tylko snapshoty OZE (`linia_produktowa` = `pv` albo `oze`); `cp` daje `ValueError`.

	`koszty_plan`: mapa klucz -> (kwota | `None`). Klucz musi pasować do istniejącej linii.
	Kwota ustawia `koszt_plan` linii; przy PIERWSZEJ zmianie dotychczasowa wartość trafia do
	`koszt_plan_pierwotny` i nigdy nie jest nadpisywana. `None` albo wartość równa pierwotnej
	przywraca pierwotny koszt i usuwa `koszt_plan_pierwotny`. Klucz `korekta_sumy_plan`
	przyjmuje tylko `None` (usuwa korektę).

	`suma_plan`: `None` (suma przesuwa się o zmiany linii) albo kwota >= 0. Różnicę między
	wpisaną sumą a sumą po zmianach linii niesie jedna linia `korekta_sumy_plan` (może mieć
	ujemny `koszt_plan`; korekta równa 0 znika). Wygrywa wpisana suma.

	`podsumowanie.koszt_plan` = dotychczasowe + delta zmian linii (NIE suma od zera z linii:
	stare snapshoty mogą mieć sumę różną od sumy linii), a przy podanej `suma_plan` dokładnie
	ona. `marza_plan`/`zysk_plan` liczone jak w `aktualizuj_po_edycji_zestawu`;
	`podsumowanie_rzeczywiste` przeliczane tylko gdy już istniało. Wejście nie jest mutowane.
	"""
	if not snapshot:
		raise ValueError("Brak snapshotu kosztów dla tej szansy.")
	if snapshot.get("linia_produktowa") not in LINIE_EDYTOWALNE_PLANU:
		raise ValueError("Kosztów planowanych Czystego Powietrza nie edytuje się w tym panelu.")
	if not isinstance(koszty_plan, dict):
		raise ValueError("Nieprawidłowy format kosztów planowanych.")

	stare_linie = snapshot.get("linie") or []
	klucze_znane = {linia["klucz"] for linia in stare_linie}
	zadane: dict[str, Decimal | None] = {}
	for klucz, wartosc in koszty_plan.items():
		if klucz == KLUCZ_KOREKTY_SUMY:
			if wartosc is not None:
				raise ValueError("Korekty sumy kosztów planowanych nie edytuje się jako pozycji.")
			zadane[klucz] = None
			continue
		if klucz not in klucze_znane:
			raise ValueError(f"Nieznana pozycja kosztorysu: {klucz}.")
		zadane[klucz] = None if wartosc is None else _parsuj_kwote_klienta(wartosc)
	suma_wpisana = None if suma_plan is None else _parsuj_kwote_klienta(suma_plan)

	suma_przed = _kwota(snapshot["podsumowanie"]["koszt_plan"])
	delta = _ZERO
	nowe_linie: list[dict[str, Any]] = []
	korekta = _ZERO
	for linia in stare_linie:
		klucz = linia["klucz"]
		nowa = dict(linia)
		if klucz == KLUCZ_KOREKTY_SUMY:
			if KLUCZ_KOREKTY_SUMY in zadane:  # jedyna dozwolona wartość to None: usuń korektę
				delta -= _kwota(linia["koszt_plan"])
				continue
			korekta = _kwota(linia["koszt_plan"])
			nowe_linie.append(nowa)
			continue
		if klucz in zadane:
			stary_koszt = _kwota(linia["koszt_plan"])
			pierwotny_surowy = linia.get("koszt_plan_pierwotny")
			bazowy = _kwota(pierwotny_surowy) if pierwotny_surowy is not None else stary_koszt
			zadana = zadane[klucz]
			nowy_koszt = bazowy if zadana is None else zadana
			if nowy_koszt == bazowy:
				nowa.pop("koszt_plan_pierwotny", None)
			else:
				nowa["koszt_plan_pierwotny"] = str(bazowy)
			nowa["koszt_plan"] = str(nowy_koszt)
			delta += nowy_koszt - stary_koszt
		nowe_linie.append(nowa)

	suma_po_liniach = _kwota(suma_przed + delta)
	if suma_wpisana is None:
		suma_nowa = suma_po_liniach
	else:
		korekta = _kwota(korekta + suma_wpisana - suma_po_liniach)
		suma_nowa = suma_wpisana
		nowe_linie = [linia for linia in nowe_linie if linia["klucz"] != KLUCZ_KOREKTY_SUMY]
		if korekta != _ZERO:
			nowe_linie.append(_linia_korekty(korekta))

	if suma_nowa < _ZERO:
		raise ValueError("Suma kosztów planowanych nie może być ujemna.")

	def _odcisk(linie: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
		return [
			(
				linia["klucz"],
				_kwota(linia["koszt_plan"]),
				None if linia.get("koszt_plan_pierwotny") is None else _kwota(linia["koszt_plan_pierwotny"]),
			)
			for linia in linie
		]

	if _odcisk(nowe_linie) == _odcisk(stare_linie) and suma_nowa == suma_przed:
		raise ValueError("Brak zmian w kosztach planowanych.")

	netto = _kwota(snapshot["podsumowanie"]["netto"])
	marza_plan = _kwota(netto - suma_nowa)
	prowizja_plan = snapshot["podsumowanie"].get("prowizja_plan")
	prowizja = _kwota(prowizja_plan) if prowizja_plan is not None else _ZERO
	zysk_plan = _kwota(marza_plan - prowizja)

	poprzednia = snapshot.get("edycja_planu") or {}
	nowy = copy.deepcopy(snapshot)
	nowy["linie"] = nowe_linie
	nowy["zmodyfikowano"] = teraz
	nowy["zmodyfikowal"] = uzytkownik
	nowy["podsumowanie"] = {
		**snapshot["podsumowanie"],
		"koszt_plan": str(suma_nowa),
		"marza_plan": str(marza_plan),
		"zysk_plan": str(zysk_plan),
	}
	nowy["edycja_planu"] = {
		"kiedy": teraz,
		"kto": uzytkownik,
		"koszt_plan_przed": str(suma_przed),
		"koszt_plan_pierwotny": str(poprzednia.get("koszt_plan_pierwotny") or suma_przed),
	}
	if snapshot.get("podsumowanie_rzeczywiste") is not None:
		nowy["podsumowanie_rzeczywiste"] = _oblicz_podsumowanie_rzeczywiste(nowy)
	return nowy


def policz_zmiany_planu(przed: dict[str, Any], po: dict[str, Any]) -> int:
	"""Liczba linii, których `koszt_plan` różni się między dwoma snapshotami (łącznie z
	dodaną, zmienioną lub usuniętą korektą sumy). Do śladu aktywności: tylko licznik, bez kwot."""
	stare = {linia["klucz"]: _kwota(linia["koszt_plan"]) for linia in przed.get("linie") or []}
	nowe = {linia["klucz"]: _kwota(linia["koszt_plan"]) for linia in po.get("linie") or []}
	return sum(1 for klucz in set(stare) | set(nowe) if stare.get(klucz) != nowe.get(klucz))


def czy_zmieniona_korekta(przed: dict[str, Any], po: dict[str, Any]) -> bool:
	"""Czy linia `korekta_sumy_plan` różni się między snapshotami (dodana, usunięta albo inna kwota)."""

	def _korekta(snapshot: dict[str, Any]) -> Decimal | None:
		for linia in snapshot.get("linie") or []:
			if linia["klucz"] == KLUCZ_KOREKTY_SUMY:
				return _kwota(linia["koszt_plan"])
		return None

	return _korekta(przed) != _korekta(po)
