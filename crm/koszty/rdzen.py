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

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

WERSJA = 1

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
	dokumentowany w `crm/czyste_powietrze/obliczenia.py` (ok. linii 500-513):
	`{koszt_calkowity, marza, prowizja_handlowa, zysk, linie: [{kod,
	ilosc_rozliczeniowa, jednostka_rozliczeniowa, netto, koszt, ...}]}`, wszystkie
	kwoty już zaokrąglone do grosza przez rdzeń kalkulatora.

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
			"prowizja_plan": _str_kwota(linia["prowizja"]),
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
			"prowizja_plan": _str_kwota(wewnetrzne["prowizja_handlowa"]),
			"zysk_plan": _str_kwota(wewnetrzne["zysk"]),
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
		if klucz in koszty_rzeczywiste:
			wartosc = koszty_rzeczywiste[klucz]
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
	nowy["podsumowanie_rzeczywiste"] = _oblicz_podsumowanie_rzeczywiste(nowy)
	return nowy
