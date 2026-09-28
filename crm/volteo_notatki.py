# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Fundament systemu notatek na szansie (uwaga 43, baza pod uwage 40), frappe-free.

Jeden doctype dla wszystkich zakladek szansy, `Volteo Notatka` -- kategoria
notatki to zakladka (pole `zakladka`), nie osobny wybor z listy. Modul celowo
nie importuje ``frappe`` -- to jedyny sposob, zeby dalo sie go przetestowac
lokalnie (na tej maszynie ``frappe`` nie jest instalowalne, reszta backendu
ma wylacznie bramke skladniowa). Cala logika zalezna od frameworka (walidacja
dokumentu, wysylka powiadomienia, obsluga plikow) mieszka w
``crm.api.notatki``, tu tylko czyste funkcje.

Doctype ``Volteo Notatka`` tworzy ``ops/crm-notatki.py`` w
``proenergy-crm-ops`` -- tutaj (w forku) go nie ma. Wzorowany na
``Volteo Trify Update`` (``crm.volteo_trify``): ta sama para
widocznosc-po-szansie (``crm.permissions.faktura_visibility``) i wzmianki
przez ``extract_mentions``/``notify_user``.

Slownik typow per zakladka jest LUSTRZANY w trzech miejscach, ktore trzeba
synchronizowac recznie przy kazdej zmianie: ten modul (kanon), pole Select w
``ops/crm-notatki.py`` i stala we frontendowym ``frontend/src/utils/notatki.js``
(przyszle issue, frontend tego cyklu nie dotyczy).

Zalaczniki nie zyja na polu Attach notatki -- rdzen Frappe tworzy drugi
wiersz ``File`` przy kazdym zapisie dokumentu majacego pole Attach (znany
tryb powielania na ``Volteo Faktura.plik``). Zamiast tego zalaczniki to
zwykle wiersze ``File`` podpiete pod ``CRM Deal`` (dokladnie jak galeria
"Zdjecia z realizacji" w ``crm.api.montaz``), rozroznione znacznikiem w
``attached_to_field``: roboczy upload dostaje ``ZNACZNIK_ROBOCZY``, po
utworzeniu notatki API przepina znacznik na ``zbuduj_znacznik(notatka.name)``.
Znaczniki maja wspolny prefiks (``PREFIKS_ZNACZNIKA``) -- ``_`` jest
wildcardem w SQL LIKE, wiec kazde rozpoznawanie/filtrowanie znacznikow musi
isc przez Pythonowy ``str.startswith``, nigdy przez filtr ``like`` w bazie.
"""

import html
import re

from crm.volteo_trify import tekst_pusty

__all__ = [
	"DOCTYPE",
	"DOZWOLONE_ROZSZERZENIA",
	"ETYKIETY_ZAKLADEK",
	"ETYKIETY_ZRODEL_DODATKOWYCH",
	"PREFIKS_ZNACZNIKA",
	"TYPY_BAZOWE",
	"TYPY_PER_ZAKLADKA",
	"ZAKLADKI",
	"ZNACZNIK_ROBOCZY",
	"ZRODLA_FEEDU",
	"czy_dozwolony",
	"czy_obraz",
	"czy_pdf",
	"etykieta_zrodla",
	"normalizuj_komentarz_audytu",
	"normalizuj_notatke",
	"posortuj",
	"rozbij_znacznik",
	"rozszerzenie",
	"tekst_aktywnosci",
	"tekst_na_html",
	"tekst_pusty",
	"typy_dla",
	"wszystkie_typy",
	"zbuduj_powiadomienie",
	"zbuduj_znacznik",
	"zbuduj_zrodla",
]

DOCTYPE = "Volteo Notatka"

ZAKLADKI: tuple[str, ...] = (
	"Zestaw",
	"Umowa",
	"Kredyt",
	"Faktury",
	"Montaz",
	"OSD",
	"Dotacja",
	"Trify",
)
"""Wartosci pola Select `zakladka`, co do litery jak `name` zakladek w
`Deal.vue` (Montaz bez ogonka -- etykieta „Montaż” zyje wylacznie w
`ETYKIETY_ZAKLADEK` ponizej, fieldname/wartosc Select zostaja bez polskich
znakow, jak reszta identyfikatorow forka). Faza 1 (ten cykl) dotyczy
wylacznie szans OZE -- schemat i backend sa jednak wspolne od razu, zeby CP
nie wymagalo migracji w fazie 2."""

ETYKIETY_ZAKLADEK: dict[str, str] = {
	"Zestaw": "Zestaw",
	"Umowa": "Umowa",
	"Kredyt": "Kredyt",
	"Faktury": "Faktury",
	"Montaz": "Montaż",
	"OSD": "OSD",
	"Dotacja": "Dotacja",
	"Trify": "Trify",
}
"""Etykieta wyswietlana dla kazdej zakladki -- jedyna roznica wzgledem
`ZAKLADKI` to `Montaz` -> „Montaż”, reszta jak nazwa wartosci Select."""

TYPY_BAZOWE: tuple[str, ...] = (
	"Notatka",
	"Telefon",
	"Wizyta",
	"Ustalenie",
	"Problem",
	"Dokument",
)
"""Wspolna baza typow notatki, dla kazdej zakladki poza wyjatkami ponizej."""

TYPY_PER_ZAKLADKA: dict[str, tuple[str, ...]] = {
	"Zestaw": TYPY_BAZOWE,
	"Umowa": TYPY_BAZOWE,
	"Kredyt": TYPY_BAZOWE,
	"Faktury": TYPY_BAZOWE,
	# Wyjatek Montaz: baza + "Termin montażu".
	"Montaz": (*TYPY_BAZOWE, "Termin montażu"),
	"OSD": TYPY_BAZOWE,
	"Dotacja": TYPY_BAZOWE,
	# Trify NIE dziedziczy bazy -- wlasny, calkowicie osobny slownik (faza 2,
	# ale kanon juz tutaj). Lustro (nie import) `crm.volteo_trify.TYPY`,
	# ktora zostaje jego wlasnym, niezaleznym zrodlem prawdy dla
	# `Volteo Trify Update` -- ten slownik jest kanonem WYLACZNIE dla
	# `Volteo Notatka.typ`, gdy `zakladka == "Trify"`.
	"Trify": (
		"Notatka",
		"Wniosek Trify",
		"Decyzja Trify",
		"Umowa Trify",
		"Wypłata Trify",
		"Problem",
	),
}
"""Dozwolone wartosci pola `typ`, w zaleznosci od `zakladka`. Suma tego
slownika (`wszystkie_typy()`) to pelna lista opcji pola Select `typ` na
poziomie doctype'u -- Frappe waliduje Select wobec PELNEJ listy opcji,
dopuszczalnosc per zakladka sprawdza dopiero `validate` w `crm.api.notatki`."""


def typy_dla(zakladka: str) -> tuple[str, ...]:
	"""Dozwolone typy notatki dla danej zakladki. Rzuca `ValueError` dla
	nieznanej zakladki -- wolajacy (walidacja dokumentu) sprawdza `zakladka
	in ZAKLADKI` osobno i wczesniej, wiec to jest tylko druga linia obrony."""
	if zakladka not in TYPY_PER_ZAKLADKA:
		raise ValueError(f"Nieznana zakladka notatki: {zakladka}")
	return TYPY_PER_ZAKLADKA[zakladka]


def wszystkie_typy() -> tuple[str, ...]:
	"""Suma slownikow wszystkich zakladek, kolejnosc stabilna (kolejnosc
	`ZAKLADKI`, potem kolejnosc w kazdym slowniku), bez duplikatow -- to jest
	pelna lista opcji Select `typ` na poziomie doctype'u."""
	widziane: list[str] = []
	for zakladka in ZAKLADKI:
		for typ in TYPY_PER_ZAKLADKA[zakladka]:
			if typ not in widziane:
				widziane.append(typ)
	return tuple(widziane)


ZNACZNIK_ROBOCZY = "notatka_robocza"
"""`attached_to_field` uzywany przez upload roboczy z frontu (jeszcze bez
notatki-rodzica), zawsze na `CRM Deal`."""

PREFIKS_ZNACZNIKA = "notatka_"
"""Wspolny prefiks kazdego znacznika notatki (roboczego i docelowego) --
`_` jest wildcardem w SQL LIKE, wiec kazde rozpoznawanie musi isc przez
`str.startswith`, nigdy przez filtr `like` w bazie."""


def zbuduj_znacznik(name: str) -> str:
	"""Znacznik docelowy `attached_to_field` dla plikow przypietych do
	notatki `name` (po utworzeniu notatki, przepiecie z `ZNACZNIK_ROBOCZY`)."""
	return f"{PREFIKS_ZNACZNIKA}{name}"


def rozbij_znacznik(attached_to_field: str | None) -> str | None:
	"""Odwrotnosc `zbuduj_znacznik`: z `attached_to_field` wyciaga nazwe
	notatki, albo `None`, gdy pole nie jest znacznikiem notatki docelowej
	(w tym: `None`/pusty, `ZNACZNIK_ROBOCZY` sam w sobie, albo znacznik zupelnie
	innego modulu np. `zdjecia_montaz`)."""
	if not attached_to_field:
		return None
	if attached_to_field == ZNACZNIK_ROBOCZY:
		return None
	if not attached_to_field.startswith(PREFIKS_ZNACZNIKA):
		return None
	return attached_to_field[len(PREFIKS_ZNACZNIKA):]


DOZWOLONE_ROZSZERZENIA: frozenset[str] = frozenset({"pdf", "jpg", "jpeg", "png", "webp"})
"""Rozszerzenia dozwolone jako zalacznik notatki -- decyzja wlasciciela
2026-09-28: PDF, JPEG, PNG, WEBP."""


def rozszerzenie(file_name: str | None) -> str | None:
	"""Rozszerzenie pliku (male litery, bez kropki), albo `None`, gdy nazwa
	nie ma kropki. `file_type` bywa puste w `File`, wiec rozstrzyganie idzie
	zawsze po nazwie pliku, nigdy po tym polu."""
	if not file_name or "." not in file_name:
		return None
	return file_name.rsplit(".", 1)[-1].lower()


def czy_pdf(file_name: str | None) -> bool:
	return rozszerzenie(file_name) == "pdf"


def czy_obraz(file_name: str | None) -> bool:
	return rozszerzenie(file_name) in {"jpg", "jpeg", "png", "webp"}


def czy_dozwolony(file_name: str | None) -> bool:
	"""Czy rozszerzenie pliku nalezy do `DOZWOLONE_ROZSZERZENIA` -- uzywane
	przez `crm.api.notatki.dodaj` do odrzucenia zalacznika o niedozwolonym
	typie, ostatnia linia obrony po walidacji front-endowej."""
	return rozszerzenie(file_name) in DOZWOLONE_ROZSZERZENIA


# `tekst_pusty` jest importowana z `crm.volteo_trify` (patrz import na gorze
# pliku) -- JEDNA implementacja wspolna dla `Volteo Notatka` i
# `Volteo Trify Update`, re-eksportowana stad przez `__all__` tak, zeby
# `crm.api.notatki` mogla importowac wszystko z jednego, wlasciwego dla
# siebie modulu (`from crm.volteo_notatki import tekst_pusty, ...`) bez
# wiedzy o tym, ze logika mieszka fizycznie w Trify.


def tekst_na_html(zwykly_tekst: str) -> str:
	"""Zamienia zwykly tekst (nie-HTML) na bezpieczny fragment HTML: escapuje
	znaki specjalne, `\\n` zamienia na `<br>`, calosc owija w `<p>`. Nie ma
	dzis wywolujacego w tym cyklu (frontend to osobne issue) -- funkcja
	istnieje jako czesc kanonu, testowana osobno."""
	bezpieczny = html.escape(zwykly_tekst or "")
	z_br = bezpieczny.replace("\n", "<br>")
	return f"<p>{z_br}</p>"


def _bez_html(tekst_html: str | None) -> str:
	"""Zwraca plaski tekst z HTML: znaczniki zamienia na spacje (nie na
	pusty string -- inaczej `'<p>A</p><p>B</p>'` sklejaloby sie w `'AB'`
	zamiast `'A B'`), potem dekoduje encje (`&nbsp;` itp.) i normalizuje
	biale znaki. Regex zamiast parsera HTML: modul jest celowo frappe-free
	(bez BeautifulSoup), a zadanie nie wymaga drzewa DOM."""
	if not tekst_html:
		return ""
	bez_tagow = re.sub(r"<[^>]*>", " ", tekst_html)
	bez_encji = html.unescape(bez_tagow)
	return re.sub(r"\s+", " ", bez_encji).strip()


def tekst_aktywnosci(zakladka: str, typ: str, tekst_html: str) -> str:
	"""Linia Aktywnosci szansy dla nowej notatki: „dodano notatkę
	(<etykieta zakladki>): <typ>: „<pierwsze 80 znakow tekstu bez HTML>"”.
	Wywolywana z `crm.api.activities.compose_volteo_linked_text` dla
	`dt == "Volteo Notatka"` -- ta funkcja jest jedynym zrodlem prawdy dla
	tekstu tej linii, zeby nie duplikowac formatowania w pliku, ktory nie
	jest frappe-free."""
	etykieta = ETYKIETY_ZAKLADEK.get(zakladka, zakladka)
	plaski = _bez_html(tekst_html)
	snippet = plaski[:80] + "…" if len(plaski) > 80 else plaski
	return f"dodano notatkę ({etykieta}): {typ}: „{snippet}”"


def zbuduj_powiadomienie(
	owner: str,
	autor_nazwa: str,
	deal: str,
	notatka: str,
	zakladka: str,
	email_wzmiankowanego: str,
) -> dict:
	"""Sklada slownik dla `notify_user`
	(`crm.fcrm.doctype.crm_notification.crm_notification.notify_user`) --
	powiadomienie-dzwoneczek o wzmiance w tresci notatki. Uogolnienie
	`crm.volteo_trify.zbuduj_powiadomienie` o zakladke (etykieta w tresci
	powiadomienia). Ksztalt slownika (klucze `reference_doctype`/
	`reference_docname`/`redirect_to_doctype`/`redirect_to_docname`) musi
	zostac identyczny jak w Trify -- `notify_user` mapuje je na
	`CRM Notification.notification_type_doctype`/`notification_type_doc`/
	`reference_doctype`/`reference_name`, a `crm.api.notifications.get_hash`
	czyta `notification_type_doctype` po tej nazwie, zeby zwrocic `#notatki`.

	`autor_nazwa` i `deal` sa escapowane przez `html.escape` -- oba pochodza
	z danych uzytkownika (imie i nazwisko, nazwa szansy), nie z ustalonego
	slownika jak `zakladka`/typ wpisu.
	"""
	autor_nazwa_bezp = html.escape(autor_nazwa)
	deal_bezp = html.escape(deal)
	etykieta = ETYKIETY_ZAKLADEK.get(zakladka, zakladka)
	tresc = (
		'<div class="mb-2 leading-5 text-ink-gray-5">'
		f'<span class="font-medium text-ink-gray-9">{autor_nazwa_bezp}</span>'
		f" wspomniał(a) Cię w notatce ({etykieta}) szansy"
		f' <span class="font-medium text-ink-gray-9">{deal_bezp}</span>'
		"</div>"
	)
	return {
		"owner": owner,
		"assigned_to": email_wzmiankowanego,
		"notification_type": "Mention",
		"message": tresc,
		"notification_text": tresc,
		"reference_doctype": DOCTYPE,
		"reference_docname": notatka,
		"redirect_to_doctype": "CRM Deal",
		"redirect_to_docname": deal,
	}


def posortuj(wpisy: list[dict], kierunek: str = "desc") -> list[dict]:
	"""Sortuje liste wpisow (slownikow z kluczami `data_zdarzenia` i
	`creation`) tak samo, jak `order_by="data_zdarzenia desc, creation desc"`
	w `frappe.get_list` -- czysta, testowalna wersja tej samej reguly
	sortowania, uzywana defensywnie po stronie Pythona (np. po doklejeniu
	`autor_nazwa`/`pliki` do wynikow zapytania). `kierunek` inny niz `"desc"`
	daje sortowanie rosnace."""
	malejaco = kierunek == "desc"
	return sorted(
		wpisy,
		key=lambda wpis: (wpis.get("data_zdarzenia") or "", wpis.get("creation") or ""),
		reverse=malejaco,
	)


# ---------------------------------------------------------------------------
# Feed „Notatki" (issue ops#201, uwaga 40) -- strumien LACZACY notatki z
# kazdej zakladki z komentarzami watku „Komentarze" zakladki Audyt (OZE i
# CP). Wylacznie widok: bez karty dodawania, edycji ani kosza (te operacje
# zyja na zakladce zrodlowej). Cala normalizacja ksztaltu wpisu mieszka tu,
# frappe-free -- `crm.api.notatki.feed` tylko czyta z bazy (frappe.get_list/
# get_all, uprawnienia) i woła te funkcje.
# ---------------------------------------------------------------------------

ZRODLA_FEEDU: tuple[str, ...] = (*ZAKLADKI, "Audyt", "AudytCP")
"""Kolejnosc i zestaw wszystkich mozliwych wartosci `zrodlo` w feedzie:
osiem zakladek `Volteo Notatka` (kolejnosc `ZAKLADKI`) plus dwa dodatkowe
zrodla komentarzy watku Audytu (OZE i CP). `crm.api.notatki.feed` zwraca
liste `zrodla` w DOKLADNIE tej kolejnosci (`zbuduj_zrodla` ponizej) -- lista
filtrow po stronie frontu (`FiltrZrodel.vue`) pokazuje wiec zawsze ten sam
uklad, niezaleznie od tego, ktore zrodla maja akurat jakies wpisy."""

ETYKIETY_ZRODEL_DODATKOWYCH: dict[str, str] = {
	"Audyt": "Audyt",
	"AudytCP": "Audyt CP",
}
"""Etykiety dla dwoch zrodel spoza `ZAKLADKI` (komentarze watku Audytu OZE i
CP) -- `Audyt`/`AudytCP` NIE sa wartosciami pola Select `zakladka` na
`Volteo Notatka`, wiec nie naleza do `ETYKIETY_ZAKLADEK`; maja wlasny,
osobny slownik etykiet."""


def etykieta_zrodla(zrodlo: str) -> str:
	"""Etykieta dowolnego zrodla feedu -- najpierw `ETYKIETY_ZAKLADEK` (osiem
	zakladek notatki), potem `ETYKIETY_ZRODEL_DODATKOWYCH` (Audyt/AudytCP),
	w ostatecznosci sam klucz (nieznane zrodlo, nie powinno sie zdarzyc przy
	wejsciu z `ZRODLA_FEEDU`, ale bez rzucania wyjatku dla defensywnosci)."""
	if zrodlo in ETYKIETY_ZAKLADEK:
		return ETYKIETY_ZAKLADEK[zrodlo]
	return ETYKIETY_ZRODEL_DODATKOWYCH.get(zrodlo, zrodlo)


def normalizuj_notatke(wpis: dict) -> dict:
	"""Normalizuje jeden wpis `Volteo Notatka` do wspolnego ksztaltu wpisu
	feedu. `wpis` ma ksztalt, ktory `crm.api.notatki.lista()` juz zwraca dla
	pojedynczego wpisu (wzbogacony o `autor_nazwa`/`pliki` PRZED wywolaniem
	tej funkcji): `name`, `zakladka`, `typ`, `data_zdarzenia`, `tekst`,
	`kredyt`, `owner`, `creation`, `autor_nazwa`, `pliki`.

	`tekst` na `Volteo Notatka` jest juz bezpiecznym HTML-em (TipTap +
	sanityzacja rdzenia przy zapisie dokumentu) -- `tekst_html` w wyniku jest
	wiec przepisywany 1:1, bez przepuszczania przez `tekst_na_html` (ta
	funkcja jest wylacznie dla zwyklego tekstu, patrz
	`normalizuj_komentarz_audytu` ponizej)."""
	zakladka = wpis.get("zakladka") or ""
	return {
		"klucz": "notatka:{0}".format(wpis.get("name")),
		"zrodlo": zakladka,
		"zrodlo_etykieta": etykieta_zrodla(zakladka),
		"zakladka_hash": zakladka.lower(),
		"typ": wpis.get("typ") or "",
		"data": wpis.get("data_zdarzenia") or wpis.get("creation"),
		"creation": wpis.get("creation"),
		"autor": wpis.get("owner"),
		"autor_nazwa": wpis.get("autor_nazwa") or wpis.get("owner") or "",
		"tekst_html": wpis.get("tekst") or "",
		"pliki": wpis.get("pliki") or [],
		"kredyt": wpis.get("kredyt"),
	}


def _wyglada_na_html(tekst: str) -> bool:
	"""Heurystyka odroznienia starych komentarzy watku Audytu (zwykly tekst
	z dawnej `textarea`, sprzed wzmianek @ -- issue #205) od nowych (HTML z
	edytora `TextEditor`, moze zawierac wzmianke jako
	`<span data-type="mention" ...>`): czy `tekst`, po obcieciu bialych
	znakow z lewej, zaczyna sie od `<`.

	Rdzen CRM (`crm.api.comment.add_comment` -> `frappe_add_comment`) juz
	dzis traktuje `Comment.content` jako HTML dla wszystkich innych watkow
	komentarzy (lead/szansa) -- ale zanim ten watek dostal edytor TipTap,
	front wysylal tu SUROWY tekst z `<textarea>` (bez zadnego escapowania
	po stronie JS), wiec baza moze trzymac oba ksztalty na starych
	rekordach. Rozroznienie po prefiksie `<` (a nie np. po obecnosci
	jakiegokolwiek znacznika w srodku) jest celowe: prawdziwy komentarz w
	zwyklym tekscie moze zawierac `<`/`>` w srodku zdania (np. „cena < 5000
	zl") bez przestawania byc zwyklym tekstem, ale nie zaczyna sie nim --
	edytor TipTap za to ZAWSZE zwraca HTML zaczynajacy sie od znacznika
	blokowego (`<p>`, `<ul>`...)."""
	return (tekst or "").lstrip().startswith("<")


def normalizuj_komentarz_audytu(komentarz: dict, zrodlo: str) -> dict:
	"""Normalizuje jeden komentarz watku „Komentarze" zakladki Audyt
	(`Comment` z `reference_doctype in ("Volteo Audyt", "Volteo Audyt CP")`)
	do wspolnego ksztaltu wpisu feedu. `komentarz` ma klucze `name`, `owner`,
	`creation`, `content`, `autor_nazwa` (juz rozwiazane przez wywolujacego
	JEDNYM zbiorczym zapytaniem `User.full_name` -- ta funkcja celowo NIE
	czyta `comment_by`, zeby nie miec dwoch zrodel prawdy o imieniu i
	nazwisku autora obok siebie w tym samym module), oraz opcjonalnie
	`pliki` (zalaczniki `File` z `attached_to_doctype = "Comment"`).

	`zrodlo` musi byc `"Audyt"` albo `"AudytCP"` -- kazda inna wartosc rzuca
	`ValueError` (wywolujacy zna zrodlo z tego, KTORY doctype wlasnie
	odpytal, wiec to jest tylko druga linia obrony, jak `typy_dla`).

	Komentarz nie ma wlasnego `typ` (nie jest `Volteo Notatka`) -- w feedzie
	dostaje stala etykiete `"Komentarz"`, zeby karta wpisu mogla pokazac cos
	sensownego zamiast pustego chipu typu.

	`tekst_html` (issue #205): odkad watek Komentarze ma edytor ze
	wzmiankami, `content` JEST juz bezpiecznym HTML-em z TipTap -- przepisany
	1:1, bez ponownego escapowania (inaczej wzmianka `<span data-type=
	"mention" ...>` zamieniłaby sie w widoczny tekst znacznika). Stare
	komentarze (zwykly tekst sprzed tej zmiany) nadal ida przez
	`tekst_na_html` -- patrz `_wyglada_na_html` powyzej."""
	if zrodlo not in ("Audyt", "AudytCP"):
		raise ValueError(f"Nieznane zrodlo komentarza audytu: {zrodlo}")
	tresc = komentarz.get("content") or ""
	tekst_html = tresc if _wyglada_na_html(tresc) else tekst_na_html(tresc)
	return {
		"klucz": "audyt:{0}".format(komentarz.get("name")),
		"zrodlo": zrodlo,
		"zrodlo_etykieta": etykieta_zrodla(zrodlo),
		"zakladka_hash": zrodlo.lower(),
		"typ": "Komentarz",
		"data": komentarz.get("creation"),
		"creation": komentarz.get("creation"),
		"autor": komentarz.get("owner"),
		"autor_nazwa": komentarz.get("autor_nazwa") or komentarz.get("owner") or "",
		"tekst_html": tekst_html,
		"pliki": komentarz.get("pliki") or [],
		"kredyt": None,
	}


def zbuduj_zrodla(liczniki: dict[str, int]) -> list[dict]:
	"""Buduje liste `zrodla` zwracana przez `crm.api.notatki.feed`: jeden
	wpis na kazde `ZRODLA_FEEDU`, w STALEJ kolejnosci, z etykieta i liczba
	wpisow. Zrodlo bez zadnego wpisu w `liczniki` (bo jeszcze nie ma tam
	zadnej notatki, albo -- dla Audyt/AudytCP -- bo dokument audytu nie
	istnieje lub wywolujacy nie ma do niego uprawnien) dostaje `liczba: 0`,
	NIE znika z listy -- lista wielokrotnego wyboru zrodel ma pokazywac
	wszystkie mozliwe zrodla, zeby ich zestaw byl przewidywalny niezaleznie
	od tego, co akurat jest na tej konkretnej szansie."""
	return [
		{"klucz": zrodlo, "etykieta": etykieta_zrodla(zrodlo), "liczba": liczniki.get(zrodlo, 0)}
		for zrodlo in ZRODLA_FEEDU
	]
