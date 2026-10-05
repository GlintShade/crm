# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Zakładki „OSD” i „Dotacja” na szansie OZE (ops#202), frappe-free.

Dwie nowe zakładki na szansie, wyglądem identyczne z Montażem: karta z ręcznym
statusem (kolorowy dropdown dla backoffice/adminów, kolorowa plakietka dla
handlowca) nad strumieniem notatek tej zakładki (`NotatkiStrumien`, issue W2).
Zmianę statusu zapisuje wyłącznie backoffice/admin (`BYPASS_ROLES`) przez
`crm.api.osd_dotacja.ustaw_status`: moduł tutaj niesie WYŁĄCZNIE czyste
słowniki i formatowanie tekstu, bez żadnej walidacji uprawnień ani zapisu do
bazy (to żyje w `crm.api.osd_dotacja`, bo wymaga `frappe`).

Moduł celowo nie importuje ``frappe`` (to jedyny sposób, żeby dało się go
przetestować lokalnie na tej maszynie, gdzie ``frappe`` nie jest instalowalne;
reszta backendu ma wyłącznie bramkę składniową `ruff`/`py_compile`).

Faza 1 (ten cykl) dotyczy wyłącznie szans OZE (`crm.volteo_pipeline.
OZE_RODZAJE`). Schemat i backend są jednak wspólne od razu (pola i uprawnienia
na `CRM Deal` nie różnicują linii produktowej), żeby Czyste Powietrze w fazie 2
nie wymagało migracji, tylko odblokowania w `Deal.vue`/`MobileDeal.vue`.

Od paczki "Wielki update kalkulatora OZE" (b68, chunk B3) `OZE_RODZAJE` samo
rośnie o cztery nowe rodzaje instalacji (Rozbudowa PV/ME, Klimatyzacja, Pompa
ciepła, Kocioł), ale te dwie zakładki NIE dotyczą ich identycznie. "OSD"
dotyczy każdej instalacji, która fizycznie łączy się z siecią (PV/PVME/ME
i Rozbudowa: rozbudowa istniejącego zestawu PV/ME też wymaga zgłoszenia do
operatora). "Dotacja" (Mój Prąd) dotyczy wyłącznie trzech pierwotnych rodzajów
PV/PVME/ME, bo żaden z czterech nowych rodzajów nie ma dotacji Mój Prąd
(decyzja właściciela 2026-10-04: `dotacja = 0` dla nowych rodzajów w rdzeniu
kalkulatora). Stąd `RODZAJE_OSD` i `RODZAJE_DOTACJA` niżej, per-zakładkowa
bramka zamiast jednej wspólnej.

Słowniki i kolory są kanonem TUTAJ i lustrzane w dwóch innych miejscach, które
trzeba synchronizować ręcznie przy każdej zmianie:
  - ``ops/crm-osd-dotacja.py`` (opcje pól Select `custom_status_osd` /
    `custom_status_dotacja` na `CRM Deal`);
  - ``frontend/src/utils/osdDotacja.js`` (lustro JS: `STATUSY`, `KOLORY`,
    `ETYKIETY`, `kolorStatusu()`).

Pusta wartość w bazie (pole nigdy nie ustawione) renderuje się jak „Nie
rozpoczęto” (gray), bez żadnego zapisu. „Nie rozpoczęto” jest też PRAWDZIWĄ
wartością w `STATUSY` (backoffice może jawnie ustawić ten status, np. żeby
cofnąć omyłkowy wybór), tylko domyślny (nieustawiony) stan renderuje się
identycznie.
"""

from crm.volteo_pipeline import OZE_RODZAJE

__all__ = [
	"ETYKIETY_KART",
	"KOLORY",
	"POLE",
	"RODZAJE",
	"RODZAJE_DOTACJA",
	"RODZAJE_OSD",
	"STATUSY",
	"ZAKLADKI",
	"tekst_sladu_statusu",
]

ZAKLADKI: tuple[str, ...] = ("OSD", "Dotacja")
"""Klucze zakładki, co do litery jak `name` zakładek w `Deal.vue`/`MobileDeal.vue`."""

POLE: dict[str, str] = {
	"OSD": "custom_status_osd",
	"Dotacja": "custom_status_dotacja",
}
"""Zakładka -> fieldname pola Select na `CRM Deal` (permlevel 3, `ops/crm-osd-dotacja.py`)."""

RODZAJE_OSD: frozenset[str] = OZE_RODZAJE - {"Klimatyzacja", "Pompa ciepła", "Kocioł"}
"""Rodzaje umowy, dla których zakładka "OSD" jest dostępna: PV, PV+ME, ME, Rozbudowa PV/ME, czyli
każda instalacja, która fizycznie łączy się z siecią operatora. Klimatyzacja/Pompa ciepła/Kocioł
nie łączą się z siecią w sposób wymagający zgłoszenia OSD, więc zostają poza tym zbiorem."""

RODZAJE_DOTACJA: frozenset[str] = frozenset({"Fotowoltaika", "Fotowoltaika + Magazyn", "Magazyn energii"})
"""Rodzaje umowy, dla których zakładka "Dotacja" (Mój Prąd) jest dostępna: wyłącznie trzy pierwotne
rodzaje OZE. Żaden z czterech nowych rodzajów (łącznie z Rozbudową) nie ma dotacji Mój Prąd, bo
`dotacja = 0` dla nich w rdzeniu kalkulatora (decyzja właściciela 2026-10-04)."""

RODZAJE: dict[str, frozenset[str]] = {
	"OSD": RODZAJE_OSD,
	"Dotacja": RODZAJE_DOTACJA,
}
"""Zakładka -> zbiór rodzajów umowy, dla których ta zakładka jest dostępna. Wołane z
`crm.api.osd_dotacja._sprawdz_rodzaj_oze` per zakładka: bramka nie jest już wspólna dla obu
zakładek od paczki b68 (chunk B3), patrz docstring modułu."""

STATUSY: dict[str, tuple[str, ...]] = {
	"OSD": (
		"Nie rozpoczęto",
		"Zgłoszenie wysłane",
		"Uwagi OSD",
		"Umowa przyłączeniowa",
		"Licznik wymieniony",
		"Zakończone",
	),
	"Dotacja": (
		"Nie rozpoczęto",
		"Wniosek złożony",
		"Uzupełnienie",
		"Decyzja pozytywna",
		"Wypłacona",
		"Odrzucona",
	),
}
"""Zakładka -> krotka dozwolonych wartości pola Select, w kolejności wyświetlania
w dropdownie. Pierwsza wartość każdej krotki jest zawsze „Nie rozpoczęto” (stan
początkowy). Pusty string NIE jest członkiem żadnej krotki, więc
`crm.api.osd_dotacja.ustaw_status` odrzuca pusty `status` samą przynależnością
do tej krotki, bez osobnego sprawdzenia."""

KOLORY: dict[str, dict[str, str]] = {
	"OSD": {
		"Nie rozpoczęto": "gray",
		"Zgłoszenie wysłane": "blue",
		"Uwagi OSD": "blue",
		"Umowa przyłączeniowa": "blue",
		"Licznik wymieniony": "blue",
		"Zakończone": "green",
	},
	"Dotacja": {
		"Nie rozpoczęto": "gray",
		"Wniosek złożony": "blue",
		"Uzupełnienie": "blue",
		"Decyzja pozytywna": "lime",
		"Wypłacona": "green",
		"Odrzucona": "red",
	},
}
"""Kolor (klucz `COLOR_BUTTON_CLASS_MAP` we `frontend/src/utils/statusColors.js`) dla
każdej wartości `STATUSY`. Decyzja właściciela 2026-09-28: statusy „w trakcie” są
zawsze niebieskie (ten sam wybór co `Procesowane` na statusie finansowania
formularza kredytowego, ops#197), tylko stany terminalne dostają inny kolor.
`Odrzucona` jest czerwona, `Zakończone`/`Wypłacona` zielone, `Decyzja pozytywna`
jasnozielona (`lime`, klucz dopisany do `COLOR_BUTTON_CLASS_MAP` przez ten
issue)."""

ETYKIETY_KART: dict[str, str] = {
	"OSD": "Status OSD",
	"Dotacja": "Status dotacji",
}
"""Etykieta karty statusu wyświetlana nad strumieniem notatek każdej zakładki."""

_ETYKIETY_SLADU: dict[str, str] = {
	"OSD": "OSD",
	"Dotacja": "dotacji",
}
"""Rzeczownik/skrót wplatany w środek zdania śladu Aktywności (odmiana: „status
OSD”, skrót się nie odmienia, ale „status dotacji”, dopełniacz). Prywatne:
konsumowane wyłącznie przez `tekst_sladu_statusu` poniżej."""


def tekst_sladu_statusu(zakladka: str, stary: str | None, nowy: str) -> str:
	"""Tekst linii Aktywności dla zmiany statusu zakładki OSD/Dotacja. Wołane z
	`crm.volteo_aktywnosc.tekst_sladu` (gałąź `"status_zakladki"`), strzałka `→`
	jak `status_auto`/`kredyt_status_finansowania`. `stary` puste/`None` (pierwsze
	ustawienie statusu) daje „ustawiono status …: <nowy>” zamiast strzałki.
	Rzuca `ValueError` dla nieznanej zakładki."""
	etykieta = _ETYKIETY_SLADU.get(zakladka)
	if etykieta is None:
		raise ValueError(f"Nieznana zakładka: {zakladka!r}")
	if stary:
		return f"status {etykieta}: {stary} → {nowy}"
	return f"ustawiono status {etykieta}: {nowy}"
