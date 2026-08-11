"""Mapuje dane doctype'ów na wejście kalkulatora bez ujawniania logiki frameworka.

Moduł jest celowo czysty: nie importuje Frappe i nie wykonuje operacji wejścia/wyjścia.
W szczególności wartość limitu równa zero oznacza brak limitu i jest mapowana na
``None``. Przekazanie zera do rdzenia jako liczby wyzerowałoby dotację dla pozycji,
które nie mają per-itemowego ograniczenia.
"""

from typing import Any


class CPBladMapowania(Exception):
	"""Dane z doctype'ów nie mogą zostać zamienione na dane kalkulatora."""


def _wymagane(wiersz: dict[str, Any], pole: str) -> Any:
	if not isinstance(wiersz, dict) or pole not in wiersz or wiersz[pole] is None:
		raise CPBladMapowania(f"Brak wymaganego pola: {pole}.")
	return wiersz[pole]


def _limit(wiersz: dict[str, Any], pole: str) -> Any:
	wartosc = wiersz.get(pole)
	return None if wartosc is None or wartosc == 0 else wartosc


def katalog_z_wierszy(wiersze: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
	"""Zamienia wiersze katalogu na strukturę wymaganą przez rdzeń obliczeń."""
	wynik: dict[str, dict[str, Any]] = {}
	poziomy = ("podstawowy", "podwyzszony", "najwyzszy")

	for wiersz in wiersze:
		kod = _wymagane(wiersz, "kod")
		if not isinstance(kod, str):
			raise CPBladMapowania("Nieprawidłowy kod pozycji katalogowej.")
		if kod in wynik:
			raise CPBladMapowania("Powtórzony kod pozycji katalogowej.")

		_wymagane(wiersz, "nazwa")
		kategoria = _wymagane(wiersz, "kategoria")
		jednostka = _wymagane(wiersz, "jednostka")
		cena_netto = _wymagane(wiersz, "cena_netto")
		prowizja = _wymagane(wiersz, "prowizja")
		koszt_proenergy = _wymagane(wiersz, "koszt_proenergy")
		koszt_staly = _wymagane(wiersz, "koszt_staly")
		aktywny = _wymagane(wiersz, "aktywny")
		dotacja = {poziom: _wymagane(wiersz, f"dotacja_{poziom}") for poziom in poziomy}
		limit_dotacji = {poziom: _limit(wiersz, f"limit_{poziom}") for poziom in poziomy}
		wynik[kod] = {
			"kategoria": kategoria,
			"jednostka": jednostka,
			"cena_netto": cena_netto,
			"dotacja": dotacja,
			"limit_dotacji": limit_dotacji,
			"prowizja": prowizja,
			"koszt_proenergy": koszt_proenergy,
			"koszt_staly": koszt_staly,
			"aktywny": bool(aktywny),
		}

	return wynik


def limity_z_wierszy(wiersze: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
	"""Zamienia wiersze limitów na mapę używaną przez rdzeń obliczeń."""
	wynik: dict[tuple[str, str], dict[str, Any]] = {}
	statusy = {"kwota", "brak_dotacji", "niedozwolone", "do_ustalenia"}

	for wiersz in wiersze:
		poziom = _wymagane(wiersz, "poziom")
		standard = _wymagane(wiersz, "standard")
		status = _wymagane(wiersz, "status_limitu")
		limit_laczny = _wymagane(wiersz, "limit_laczny")
		if status not in statusy:
			raise CPBladMapowania("Nieznany status limitu termomodernizacji.")
		if not isinstance(poziom, str) or not isinstance(standard, str):
			raise CPBladMapowania("Nieprawidłowy klucz limitu termomodernizacji.")

		klucz = (poziom, standard)
		if klucz in wynik:
			raise CPBladMapowania("Powtórzony limit termomodernizacji.")
		wynik[klucz] = {
			"status": status,
			"kwota": limit_laczny if status == "kwota" else None,
		}

	return wynik


def stale_z_dokumentu(dokument: dict[str, Any]) -> dict[str, Any]:
	"""Wybiera stałe kalkulatora z dokumentu Single, zachowując ich wartości."""
	return {
		"vat_mnoznik": _wymagane(dokument, "vat_mnoznik"),
		"mnozniki": {
			"elewacja": _wymagane(dokument, "mnoznik_elewacja"),
			"strop": _wymagane(dokument, "mnoznik_strop"),
			"dach": _wymagane(dokument, "mnoznik_dach"),
			"okna": _wymagane(dokument, "mnoznik_okna"),
		},
		"m2_na_drzwi": _wymagane(dokument, "m2_na_drzwi"),
		# Klucze na poziomie głównym (nie w "mnozniki"), bo rdzeń czyta je właśnie stamtąd.
		# Wymagane z _wymagane(): jeśli obraz wejdzie przed skryptem seedującym Single,
		# ma to głośno wybuchnąć zamiast po cichu policzyć błędną cenę.
		"mnoznik_okna_od_elewacji": _wymagane(dokument, "mnoznik_okna_od_elewacji"),
		"udzial_dotacji_elewacja": _wymagane(dokument, "udzial_dotacji_elewacja"),
	}
