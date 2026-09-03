# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Wspólna, czysta logika śladów aktywności na szansie (`CRM Deal`).

Moduł celowo nie importuje ``frappe`` na poziomie modułu — precedens
``crm/volteo_naming.py`` i ``crm/volteo_pipeline.py``. To jedyny sposób, żeby
dało się go przetestować lokalnie (``frappe`` nie jest instalowalne na tej
maszynie, więc reszta backendu ma wyłącznie bramkę składniową `ruff`/
`py_compile`). Wyjątek: `zapisz_slad` robi `import frappe` lokalnie, w ciele
funkcji — to jedyne miejsce w pliku, które dotyka frameworka.

Ten moduł powstał, bo zakładka Aktywność na szansie gubiła ślady: Frappe
podaje tylko 10 najnowszych wersji, dotychczasowy czytnik
(`crm/api/activities.py:get_deal_activities`) czytał wyłącznie
`data["changed"][0]` (pierwszą zmianę z wersji, ignorując resztę),
`handle_multiple_versions` sklejał wpisy tego samego autora bez limitu
czasu, a komentarze `Info` (podzadania rurociągu) trafiały do
`docinfo.info_logs`, którego czytnik nie dotykał. Ten moduł niesie CAŁĄ
czystą logikę; pozostałe pozycje paczki (czytnik w `crm/api/activities.py`,
pisarze w `crm/api/*.py`) wyłącznie go konsumują — patrz ops#57.

Wszystkie funkcje są immutable: zwracają nowe struktury, nigdy nie mutują
argumentów wejściowych.
"""

import datetime
from collections.abc import Iterable

POLA_WLASNA_LINIA: tuple[str, ...] = (
	"status",
	"lost_reason",
	"lost_notes",
	"deal_owner",
	"organization",
	"custom_rodzaj_umowy",
	"custom_zasady_dotacji",
	"custom_narzut",
)
"""Pola `CRM Deal`, które zawsze dostają własną linię feedu (w tej kolejności), zamiast
wpadać do zbiorczego podsumowania — to one najbardziej interesują handlowca/backoffice."""

ZNACZNIK_KOSZTY = "[volteo:koszty]"
"""Znacznik wiodący tekstu śladu kosztów rzeczywistych — nigdy nie niesie kwot, ale sama
linia i tak jest widoczna wyłącznie dla ról administracyjnych (patrz `czy_widoczny`)."""

ZNACZNIKI_ADMIN: frozenset[str] = frozenset({ZNACZNIK_KOSZTY})
"""Zbiór znaczników wiodących, których linie feedu są widoczne wyłącznie dla ról
administracyjnych — patrz `czy_widoczny`/`bez_znacznika`."""

OKNO_GRUPOWANIA_S = 600
"""Maksymalny odstęp (w sekundach) między kolejnymi wpisami tego samego autora, żeby
`grupuj` je sklejał w jeden wiersz feedu — decyzja właściciela 2026-09-03: 10 minut."""

_TYPY_LACZALNE: frozenset[str] = frozenset({"changed", "added", "removed"})
"""Typy aktywności, które `grupuj` w ogóle rozważa do sklejenia — wszystko inne (komentarz,
załącznik, komunikacja...) zawsze przerywa grupę i idzie do wyniku bez zmian."""

_AKCJE_AUDYTU: frozenset[str] = frozenset({"dodano", "usunięto", "zmieniono"})
"""Dozwolone wartości `akcja` dla `tekst_sladu("audyt_plik", ...)`."""


def _etykieta(fieldname: str, etykiety: dict[str, str]) -> str:
	"""Etykieta pola do wyświetlenia: z `etykiety`, albo (gdy brak) sama nazwa pola."""
	return etykiety.get(fieldname, fieldname)


def linie_z_wersji(data: dict, etykiety: dict[str, str], avoid: Iterable[str] = ()) -> list[dict]:
	"""Rozkłada `Version.data` (kształt Frappe: `changed`/`added`/`removed`/`row_changed`) na
	listę linii feedu, w kolejności:

	  1. po jednej linii `{"rodzaj": "pole", ...}` dla KAŻDEGO zmienionego pola z
	     `POLA_WLASNA_LINIA` (w kolejności tej krotki, nie w kolejności `data["changed"]`);
	  2. po jednej linii `{"rodzaj": "kontakt", ...}` dla każdego wiersza tabeli `contacts`
	     dodanego/usuniętego, oraz dla każdego ustawienia głównego kontaktu (`is_primary`
	     0 → 1) w `row_changed`;
	  3. najwyżej jedna linia `{"rodzaj": "podsumowanie", ...}` dla pozostałych zmienionych
	     pól (poza `avoid` i poza `POLA_WLASNA_LINIA`), pomijając pary pusty→pusty.

	Pary pusty→pusty (`not old and not new`) są pomijane wszędzie — nie liczą się jako
	zmiana. Wiersze tabeli `custom_zestaw` (BOM) są ignorowane — obsługuje je istniejące
	`extract_zestaw_version_summary` w `crm/api/activities.py`. Zwraca pustą listę, gdy nic
	nie zostało. Nie mutuje `data` ani `etykiety`.
	"""
	changed = data.get("changed") or []
	avoid_set = set(avoid)
	wlasna_set = set(POLA_WLASNA_LINIA)

	diffs: dict[str, tuple] = {}
	kolejnosc: list[str] = []
	for wpis in changed:
		if not wpis or len(wpis) < 3:
			continue
		fieldname, old, new = wpis[0], wpis[1], wpis[2]
		if not old and not new:
			continue
		if fieldname in diffs:
			continue
		diffs[fieldname] = (old, new)
		kolejnosc.append(fieldname)

	linie: list[dict] = []

	for fieldname in POLA_WLASNA_LINIA:
		if fieldname not in diffs:
			continue
		old, new = diffs[fieldname]
		etykieta = _etykieta(fieldname, etykiety)
		if not old:
			text = f"ustawiono {etykieta}: {new}"
		elif not new:
			text = f"usunięto {etykieta}: {old}"
		else:
			text = f"zmieniono {etykieta}: {old} → {new}"
		linie.append(
			{
				"rodzaj": "pole",
				"field": fieldname,
				"field_label": etykieta,
				"old_value": old,
				"value": new,
				"text": text,
			}
		)

	for wpis in data.get("added") or []:
		if not wpis or wpis[0] != "contacts":
			continue
		row = wpis[1] if len(wpis) > 1 else {}
		if not isinstance(row, dict):
			continue
		linie.append({"rodzaj": "kontakt", "text": f"dodano kontakt {row.get('contact')}"})

	for wpis in data.get("removed") or []:
		if not wpis or wpis[0] != "contacts":
			continue
		row = wpis[1] if len(wpis) > 1 else {}
		if not isinstance(row, dict):
			continue
		linie.append({"rodzaj": "kontakt", "text": f"usunięto kontakt {row.get('contact')}"})

	for wpis in data.get("row_changed") or []:
		if not wpis or wpis[0] != "contacts":
			continue
		row_name = wpis[2] if len(wpis) > 2 else None
		zmiany_pol = wpis[3] if len(wpis) > 3 else []
		kontakt = None
		ustawiono_glowny = False
		for zmiana in zmiany_pol or []:
			if not zmiana or len(zmiana) < 3:
				continue
			pole_fn, pole_old, pole_new = zmiana[0], zmiana[1], zmiana[2]
			if pole_fn == "contact":
				kontakt = pole_new
			if pole_fn == "is_primary" and not pole_old and pole_new:
				ustawiono_glowny = True
		if ustawiono_glowny:
			identyfikator = kontakt or row_name
			linie.append({"rodzaj": "kontakt", "text": f"ustawiono główny kontakt {identyfikator}"})

	pozostale = [fn for fn in kolejnosc if fn not in wlasna_set and fn not in avoid_set]
	if len(pozostale) == 1:
		etykieta = _etykieta(pozostale[0], etykiety)
		linie.append({"rodzaj": "podsumowanie", "text": f"zmieniono pole: {etykieta}"})
	elif len(pozostale) > 1:
		pokazane = [_etykieta(fn, etykiety) for fn in pozostale[:5]]
		reszta = len(pozostale) - len(pokazane)
		text = f"zmieniono {len(pozostale)} pól: " + ", ".join(pokazane)
		if reszta > 0:
			text += f", +{reszta} więcej"
		linie.append({"rodzaj": "podsumowanie", "text": text})

	return linie


def tekst_sladu(rodzaj: str, **dane: object) -> str:
	"""Autorytatywne, bezosobowe polskie teksty śladów — feed pokazuje je po pogrubionym
	autorze, jak istniejące `compose_volteo_linked_text` w `crm/api/activities.py`
	("dodano fakturę …", "zaktualizowano audyt"). Nieznany `rodzaj` daje `ValueError`.
	"""
	if rodzaj == "podzadanie":
		label = dane["label"]
		if dane.get("cofnieto"):
			return f"cofnięto stan podzadania: {label}"
		text = f'ustawiono stan podzadania „{label}” na: {dane["stan"]}'
		note = dane.get("note")
		if note:
			text += f' — „{note}”'
		return text

	if rodzaj == "autenti_wyslano":
		return f"wysłano {dane['dokument']} do podpisu Autenti"

	if rodzaj == "autenti_status":
		return f"Autenti: {dane['dokument']} — {dane['status']}"

	if rodzaj == "autenti_pdf":
		return f"podpięto podpisany PDF ({dane['dokument']})"

	if rodzaj == "umowa_utworzono":
		return "utworzono umowę (formularz roboczy)"

	if rodzaj == "umowa_pdf":
		return "wygenerowano PDF umowy"

	if rodzaj == "kredyt_utworzono":
		return "utworzono formularz kredytowy"

	if rodzaj == "kredyt_pdf":
		return "wygenerowano PDF formularza kredytowego"

	if rodzaj == "koszty":
		return (
			f"{ZNACZNIK_KOSZTY} zaktualizowano koszty rzeczywiste "
			f"({dane['pozycje']} pozycji, {dane['dodatkowe']} dodatkowych)"
		)

	if rodzaj == "status_auto":
		return f"status zmieniony automatycznie ({dane['automatyzacja']}): {dane['stary']} → {dane['nowy']}"

	if rodzaj == "kalkulator_oze":
		return f"utworzono szansę z kalkulatora OZE: {dane['moc_kw']} kW, {dane['pozycje']} pozycji zestawu"

	if rodzaj == "kalkulator_cp":
		return f"utworzono szansę z kalkulatora Czyste Powietrze: {dane['pozycje']} pozycji zestawu"

	if rodzaj == "audyt_plik":
		akcja = dane["akcja"]
		if akcja not in _AKCJE_AUDYTU:
			raise ValueError(f"Nieznana akcja audytu: {akcja!r}")
		return f"{akcja} dokument audytu: {dane['etykieta']}"

	if rodzaj == "audyt_zdjecia":
		return "zmieniono zdjęcia audytu"

	raise ValueError(f"Nieznany rodzaj śladu: {rodzaj!r}")


def czy_widoczny(text: str, role: Iterable[str], admin_role: Iterable[str]) -> bool:
	"""False, gdy `text` zaczyna się od któregoś znacznika z `ZNACZNIKI_ADMIN`, a `role`
	nie ma części wspólnej z `admin_role`. W przeciwnym razie True."""
	for znacznik in ZNACZNIKI_ADMIN:
		if text.startswith(znacznik):
			if not (set(role) & set(admin_role)):
				return False
	return True


def bez_znacznika(text: str) -> str:
	"""Usuwa wiodący znacznik (np. `[volteo:koszty] `) z tekstu do wyświetlenia."""
	for znacznik in ZNACZNIKI_ADMIN:
		if text.startswith(znacznik):
			return text[len(znacznik) :].lstrip()
	return text


def roznice_plikow_audytu(
	stare_dok: dict,
	nowe_dok: dict,
	stare_zdj: list,
	nowe_zdj: list,
	etykiety_slotow: dict[str, str],
) -> list[str]:
	"""Diff dwóch map slotów dokumentów (klucz slotu → url/ścieżka albo None) i dwóch list
	zdjęć → lista tekstów przez `tekst_sladu("audyt_plik"/"audyt_zdjecia")`. Slot, który
	pojawił się (był pusty, jest wypełniony) → dodano; zniknął → usunięto; zmienił wartość
	(oba niepuste, ale różne) → zmieniono. Różne listy zdjęć dają jedną linię zbiorczą.
	Nie mutuje żadnego z argumentów.
	"""
	stare_dok = stare_dok or {}
	nowe_dok = nowe_dok or {}

	sloty = list(etykiety_slotow.keys())
	for slot in list(stare_dok.keys()) + list(nowe_dok.keys()):
		if slot not in sloty:
			sloty.append(slot)

	wyniki: list[str] = []
	for slot in sloty:
		stara = stare_dok.get(slot)
		nowa = nowe_dok.get(slot)
		if stara == nowa:
			continue
		etykieta = etykiety_slotow.get(slot, slot)
		if not stara and nowa:
			wyniki.append(tekst_sladu("audyt_plik", akcja="dodano", etykieta=etykieta))
		elif stara and not nowa:
			wyniki.append(tekst_sladu("audyt_plik", akcja="usunięto", etykieta=etykieta))
		else:
			wyniki.append(tekst_sladu("audyt_plik", akcja="zmieniono", etykieta=etykieta))

	if list(stare_zdj or []) != list(nowe_zdj or []):
		wyniki.append(tekst_sladu("audyt_zdjecia"))

	return wyniki


def _parsuj_creation(creation: object) -> datetime.datetime:
	"""Parsuje `creation` na `datetime.datetime` — akceptuje zarówno `datetime.datetime`,
	jak i string ISO `"YYYY-MM-DD HH:MM:SS"` / `"YYYY-MM-DD HH:MM:SS.ffffff"`."""
	if isinstance(creation, datetime.datetime):
		return creation
	for wzorzec in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
		try:
			return datetime.datetime.strptime(creation, wzorzec)
		except (TypeError, ValueError):
			continue
	raise ValueError(f"Nieobsługiwany format creation: {creation!r}")


def grupuj(wpisy: list[dict], okno_s: int = OKNO_GRUPOWANIA_S) -> list[dict]:
	"""Zamiennik `handle_multiple_versions` z `crm/api/activities.py`.

	Wejście: lista aktywności POSORTOWANA malejąco po `creation`, każda z kluczami
	`activity_type`, `owner`, `creation` (`datetime` albo string ISO), `data`. Wpisy typu
	changed/added/removed tego samego autora są sklejane (pierwszy zostaje, reszta idzie
	do jego `other_versions`) TYLKO gdy: żaden z nich nie dotyczy pola `status`
	(`data.get("field") == "status"` → zawsze osobny wiersz, nigdy nie skleja i przerywa
	grupę), oraz odstęp między kolejnymi `creation` ≤ `okno_s`. Pozostałe typy aktywności
	przechodzą bez zmian i przerywają grupę. Nie mutuje wejścia — zwraca nowe dicty.
	"""
	wynik: list[dict] = []
	grupa: list[dict] = []
	poprzedni_czas: datetime.datetime | None = None
	poprzedni_autor = None

	def domknij() -> None:
		if not grupa:
			return
		pierwszy = dict(grupa[0])
		if len(grupa) > 1:
			pierwszy["other_versions"] = [dict(w) for w in grupa[1:]]
		wynik.append(pierwszy)

	for wpis in wpisy:
		typ = wpis.get("activity_type")
		wpis_data = wpis.get("data")
		pole = wpis_data.get("field") if isinstance(wpis_data, dict) else None
		laczalny = typ in _TYPY_LACZALNE and pole != "status"
		czas = _parsuj_creation(wpis["creation"])
		autor = wpis.get("owner")

		if not laczalny:
			domknij()
			grupa = []
			wynik.append(dict(wpis))
			poprzedni_czas = None
			poprzedni_autor = None
			continue

		if (
			grupa
			and autor == poprzedni_autor
			and poprzedni_czas is not None
			and abs((poprzedni_czas - czas).total_seconds()) <= okno_s
		):
			grupa.append(wpis)
		else:
			domknij()
			grupa = [wpis]

		poprzedni_czas = czas
		poprzedni_autor = autor

	domknij()
	return wynik


def zapisz_slad(deal: str, tekst: str) -> None:
	"""JEDYNE miejsce w tym pliku, które dotyka Frappe — import lokalny, w ciele funkcji,
	żeby moduł importował się bez Frappe w `unittest`. Pisarze (`crm/api/*.py`) wołają to
	jedno miejsce zamiast każdy osobno składać `add_comment`."""
	import frappe

	frappe.get_doc("CRM Deal", deal).add_comment("Info", tekst)
