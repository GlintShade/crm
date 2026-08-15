# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Generator PDF-u umowy: nakłada dane z kontekstu na ORYGINALNY plik PDF.

Moduł celowo NIE odtwarza dokumentu w HTML — bierze gotowy plik dostarczony
przez prawnika i rysuje na nim wartości z `crm.volteo_umowa_pdf.zbuduj_kontekst()`,
w miejscach opisanych przez odpowiednią mapę współrzędnych. Dzięki temu treść
prawna, logo, stopka, fonty i podział stron są dokładnie takie jak w
oryginale — bo to fizycznie ten sam plik, tylko z naniesioną warstwą.

Trzy rodzaje umowy mają TRZY osobne szablony PDF i TRZY osobne mapy
współrzędnych (rejestr `SZABLONY` niżej): `PV` (Fotowoltaika), `ME` (Magazyn
energii), `PVME` (Fotowoltaika + Magazyn). Wybór szablonu jest jawny — wołający
(`crm/api/umowa.py`) przekazuje kod rodzaju umowy (te same kody, co
`crm.volteo_naming.UMOWA_CODES`) do `zloz_umowe()`, tu nie ma żadnego
domyślnego szablonu. „Czyste Powietrze” (`CP`) i nieznany/pusty rodzaj (`XX`)
CELOWO nie mają wpisu w `SZABLONY` — ten PDF dotyczy wyłącznie umów PV/magazyn;
brak klucza w rejestrze jest właśnie tym, co pozwala wołającemu odmówić
generowania dla pozostałych rodzajów, zamiast po cichu użyć niewłaściwego
szablonu.

BEZPIECZNIK (dokument prawny podpisywany przez klienta): `zloz_umowe()`
sprawdza sumę SHA-256 przekazanego szablonu względem `SZABLONY[kod].sha256`
i przerywa z czytelnym komunikatem przy niezgodności. Współrzędne w każdej
mapie są skalibrowane WYŁĄCZNIE dla dokładnie jednej wersji jednego pliku
źródłowego — każda zmiana szablonu (nawet kosmetyczna) unieważnia je, więc
lepsza jest głośna awaria niż dane naniesione w cudzą rubrykę.

FONT: rejestrujemy Liberation Sans (metryka identyczna z Arialem, którym
złożono oryginał). Wbudowane fonty base-14 reportlaba (Helvetica) używają
kodowania WinAnsi, w którym NIE MA polskich znaków `ł ą ę ś ż ź ć ń` — użycie
ich zniszczyłoby polskie nazwiska i adresy. Gdy Liberation Sans nie jest
jeszcze obecny w obrazie, moduł JAWNIE (przez `warnings.warn`, nigdy po cichu)
przechodzi na DejaVu Sans, który obraz ma zawsze — używa go już silnik
HTML→PDF w `crm/volteo_umowa_szablon.py`.

Moduł importuje `reportlab` i `pypdf` — obie biblioteki są dodane do
`pyproject.toml` w tym samym zadaniu; żadna z nich nie jest zainstalowana
lokalnie poza wirtualnym środowiskiem użytym do testów (zob. raport zadania).
"""

import hashlib
import io
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from crm.volteo_umowa_mapa import MAPA, SHA256_SZABLONU, Pole
from crm.volteo_umowa_mapa_me import LICZBA_STRON_ME, MAPA_ME, SHA256_SZABLONU_ME
from crm.volteo_umowa_mapa_pv import LICZBA_STRON_PV, MAPA_PV, SHA256_SZABLONU_PV


@dataclass(frozen=True)
class Szablon:
	"""Jeden wbudowany szablon PDF-u umowy: plik + suma kontrolna + mapa współrzędnych.

	`nazwa_pliku` jest tylko nazwą (bez katalogu) wewnątrz `crm/szablony/` —
	`sciezka_wbudowanego_szablonu()` dokleja katalog. `sha256` i `mapa` muszą
	pochodzić z TEJ SAMEJ kalibracji tego samego pliku (zob. bezpiecznik w
	`_sprawdz_sume_kontrolna`); `liczba_stron` jest tu wyłącznie informacyjnie
	(diagnostyka/testy), generator sam czyta liczbę stron z `PdfWriter`.
	"""

	nazwa_pliku: str
	sha256: str
	liczba_stron: int
	mapa: tuple[Pole, ...]


SZABLONY: dict[str, Szablon] = {
	"PV": Szablon("umowa_pv.pdf", SHA256_SZABLONU_PV, LICZBA_STRON_PV, MAPA_PV),
	"PVME": Szablon("umowa_pv_me.pdf", SHA256_SZABLONU, 18, MAPA),
	"ME": Szablon("umowa_me.pdf", SHA256_SZABLONU_ME, LICZBA_STRON_ME, MAPA_ME),
}
"""Rejestr szablonów wg kodu rodzaju umowy (te same kody, co
`crm.volteo_naming.UMOWA_CODES`: `PV`, `PVME`, `ME`). `CP` i `XX` są tu CELOWO
nieobecne — ten generator PDF-u obsługuje wyłącznie umowy PV/magazyn; nieobecność
klucza w tym słowniku jest właśnie mechanizmem, którym `crm/api/umowa.py` odmawia
generowania dla „Czyste Powietrze” i nierozpoznanego/pustego rodzaju umowy."""

_KOLOR_TEKSTU = HexColor("#1B1C1F")
"""Czerń dokumentu — zgodna z kolorem tekstu oryginału."""

_NAZWA_FONTU: str = "UmowaLiberationSans"
"""Nazwa, pod jaką zarejestrowany font (Liberation Sans albo, awaryjnie,
DejaVu Sans) jest znany reportlabowi — używana też jako nazwa w kolejnych
wywołaniach `zloz_umowe()`, więc rejestracja jest wykonywana za każdym razem
(tania operacja: samo wczytanie pliku TTF), a nie cache'owana w module —
unika to problemu "stara ścieżka fontu zapamiętana z poprzedniego wywołania"."""

_SCIEZKA_LIBERATION: Path = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
"""Standardowa lokalizacja Debiana dla pakietu `fonts-liberation` — pakiet jest
dodawany do obrazu przez innego agenta równolegle z tym zadaniem (zob. brief)."""

_SCIEZKA_DEJAVU: Path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
"""Standardowa lokalizacja Debiana dla pakietu `fonts-dejavu-core`. W obrazie
jest zawsze — używa go już silnik HTML→PDF `wkhtmltopdf` (zob.
`crm/volteo_umowa_szablon.py`), więc to bezpieczna awaryjna ścieżka."""

_MIN_ROZMIAR_FONTU_PT: float = 6.0
"""Rozsądna dolna granica zmniejszania fontu przy dopasowywaniu do
`maks_szerokosc` — poniżej tego rozmiaru tekst przestaje być czytelny, więc
dalsze dopasowanie robi już wyłącznie przycięcie (`_przytnij`)."""

_KROK_ZMNIEJSZANIA_PT: float = 0.5
"""Krok, o jaki zmniejszamy font przy każdej nieudanej próbie dopasowania."""

_WIELOKROPEK: str = "…"
"""Znak dodawany na końcu przyciętej wartości, żeby przycięcie było widoczne
dla osoby czytającej dokument, a nie wyglądało jak ucięte przez przypadek."""


def sciezka_wbudowanego_szablonu(kod: str) -> Path:
	"""Zwraca ścieżkę do wbudowanego szablonu PDF-u umowy dla rodzaju umowy `kod`.

	`kod` to kod z `crm.volteo_naming.UMOWA_CODES` (`PV`/`PVME`/`ME`). Wołający
	(np. `crm/api/umowa.py`) nie musi znać układu katalogów pakietu ani nazwy
	pliku szablonu — wystarczy przeczytać wskazany plik binarnie i przekazać
	jego zawartość do `zloz_umowe()` jako `szablon_pdf`.

	`kod` spoza `SZABLONY` (w tym `CP` i `XX`) rzuca `ValueError` z czytelnym
	komunikatem po polsku — w praktyce do tego nie powinno dojść, bo
	`crm/api/umowa.py` sprawdza `kod in SZABLONY` PRZED wywołaniem tej funkcji
	i odmawia generowania wcześniej, własnym komunikatem dla użytkownika; ten
	wyjątek jest więc drugą linią obrony (np. dla przyszłych wywołujących),
	nie ścieżką, którą ma przejść normalny ruch.
	"""
	if kod not in SZABLONY:
		raise ValueError(
			f"Nieznany kod rodzaju umowy: {kod!r}. Wbudowany szablon PDF-u istnieje "
			f"wyłącznie dla kodów: {sorted(SZABLONY)}."
		)
	return Path(__file__).resolve().parent / "szablony" / SZABLONY[kod].nazwa_pliku


def zloz_umowe(kontekst: dict[str, Any], szablon_pdf: bytes, kod: str) -> bytes:
	"""Nakłada `kontekst` na `szablon_pdf` (szablon rodzaju umowy `kod`) i zwraca gotowy PDF w bajtach.

	`kod` nie ma wartości domyślnej — wybór szablonu jest zawsze jawny, nigdy
	dorozumiany, bo pomylenie szablonu w dokumencie prawnym byłoby cichym
	uszkodzeniem umowy.

	Kroki: (1) suma SHA-256 `szablon_pdf` musi się zgadzać z `SZABLONY[kod].sha256`
	— w przeciwnym razie funkcja przerywa z czytelnym wyjątkiem, zamiast
	nanieść dane w oparciu o nieaktualne współrzędne; (2) `szablon_pdf`
	klonujemy bezpośrednio do `PdfWriter` (`clone_from=`), więc strony, na
	których rysujemy, są od razu DOŁĄCZONE do writera — pypdf w wersji 6.x
	oznacza jako przestarzały (i "niewiarygodny") wariant, w którym scala się
	strony `PdfReader` PRZED dodaniem ich do writera przez `add_page()`; (3) dla
	każdej strony, na której `SZABLONY[kod].mapa` ma choć jedną pozycję, budujemy
	jednostronicową warstwę `reportlab` (rozmiar strony brany z oryginału przez
	`pypdf`, nie zakładany na sztywno) i scalamy ją z tą stroną (`merge_page`
	— warstwa rysuje się NA WIERZCHU oryginału); (4) strony bez żadnej pozycji
	w mapie przechodzą bez zmian.

	Nie mutuje `kontekst` ani `szablon_pdf` — obie wartości są tylko czytane.
	"""
	szablon = SZABLONY[kod]
	opis = f"umowy rodzaju '{kod}' ({szablon.nazwa_pliku})"
	return _zloz_dokument(kontekst, szablon_pdf, szablon, opis)


def _zloz_dokument(kontekst: dict[str, Any], szablon_pdf: bytes, szablon: Szablon, opis: str) -> bytes:
	"""Rdzeń nakładania: identyczny dla każdego dokumentu złożonego z pary
	(szablon PDF + mapa współrzędnych), niezależnie od tego, czy to umowa
	(`zloz_umowe()`, `SZABLONY[kod]`) czy formularz kredytowy
	(`crm.volteo_kredyt_render.zloz_kredyt()`, `SZABLON_KREDYT`).

	`opis` jest wyłącznie tekstem błędu — nazywa dokument w komunikacie
	`_sprawdz_sume_kontrolna()` (np. "umowy rodzaju 'PVME' (umowa_pv_me.pdf)"
	albo "formularza kredytowego (formularz_kredytowy.pdf)"), nie wpływa na
	samo renderowanie.

	Kroki: (1) suma SHA-256 `szablon_pdf` musi się zgadzać z `szablon.sha256`
	— w przeciwnym razie funkcja przerywa z czytelnym wyjątkiem, zamiast
	nanieść dane w oparciu o nieaktualne współrzędne; (2) `szablon_pdf`
	klonujemy bezpośrednio do `PdfWriter` (`clone_from=`), więc strony, na
	których rysujemy, są od razu DOŁĄCZONE do writera — pypdf w wersji 6.x
	oznacza jako przestarzały (i "niewiarygodny") wariant, w którym scala się
	strony `PdfReader` PRZED dodaniem ich do writera przez `add_page()`; (3) dla
	każdej strony, na której `szablon.mapa` ma choć jedną pozycję, budujemy
	jednostronicową warstwę `reportlab` (rozmiar strony brany z oryginału przez
	`pypdf`, nie zakładany na sztywno) i scalamy ją z tą stroną (`merge_page`
	— warstwa rysuje się NA WIERZCHU oryginału); (4) strony bez żadnej pozycji
	w mapie przechodzą bez zmian.

	Nie mutuje `kontekst` ani `szablon_pdf` — obie wartości są tylko czytane.
	"""
	_sprawdz_sume_kontrolna(szablon_pdf, szablon, opis)
	nazwa_fontu = _zarejestruj_font()
	pozycje_wg_strony = _pogrupuj_wg_strony(szablon.mapa)

	pisarz = PdfWriter(clone_from=io.BytesIO(szablon_pdf))

	for indeks_strony, strona in enumerate(pisarz.pages):
		pozycje = pozycje_wg_strony.get(indeks_strony, ())
		if pozycje:
			szerokosc_pt = float(strona.mediabox.width)
			wysokosc_pt = float(strona.mediabox.height)
			warstwa_pdf = _narysuj_warstwe_strony(kontekst, pozycje, szerokosc_pt, wysokosc_pt, nazwa_fontu)
			warstwa_strona = PdfReader(io.BytesIO(warstwa_pdf)).pages[0]
			strona.merge_page(warstwa_strona)

	bufor_wyjsciowy = io.BytesIO()
	pisarz.write(bufor_wyjsciowy)
	return bufor_wyjsciowy.getvalue()


def _sprawdz_sume_kontrolna(szablon_pdf: bytes, szablon: Szablon, opis: str) -> None:
	"""Bezpiecznik: przerywa, gdy `szablon_pdf` nie jest bajt-w-bajt tym plikiem,
	dla którego mapa współrzędnych `szablon.mapa` była mierzona.

	`opis` nazywa dokument w komunikacie błędu (zob. `_zloz_dokument()`) —
	wołający dobiera go tak, żeby był jednoznaczny (np. zawierał kod rodzaju
	umowy albo nazwę formularza), ta funkcja go tylko wstawia do tekstu."""
	suma = hashlib.sha256(szablon_pdf).hexdigest()
	if suma != szablon.sha256:
		raise ValueError(
			f"Szablon PDF dla {opis} został zmieniony — mapa współrzędnych "
			"wymaga ponownego pomiaru. Generowanie wstrzymane, żeby nie nanieść "
			"danych w niewłaściwe miejsca. Oczekiwana suma SHA-256: "
			f"{szablon.sha256}, otrzymana: {suma}."
		)


def _pogrupuj_wg_strony(mapa: tuple[Pole, ...]) -> dict[int, tuple[Pole, ...]]:
	"""Grupuje pozycje `MAPA` po numerze strony, zachowując kolejność mapy w każdej grupie."""
	grupy: dict[int, list[Pole]] = {}
	for pole in mapa:
		grupy.setdefault(pole.strona, []).append(pole)
	return {strona: tuple(pola) for strona, pola in grupy.items()}


def _zarejestruj_font() -> str:
	"""Rejestruje font do rysowania w reportlabie pod nazwą `_NAZWA_FONTU` i zwraca ją.

	Preferuje Liberation Sans; gdy plik nie istnieje pod `_SCIEZKA_LIBERATION`,
	przechodzi JAWNIE (ostrzeżenie `RuntimeWarning`, nie cicha podmiana) na
	DejaVu Sans pod `_SCIEZKA_DEJAVU`. Gdy nie ma żadnego z nich, przerywa —
	rysowanie polskich nazwisk/adresów fontem bez obsługi diakrytyków (np.
	wbudowanym Helveticą) byłoby cichym uszkodzeniem dokumentu prawnego.
	"""
	if _SCIEZKA_LIBERATION.is_file():
		pdfmetrics.registerFont(TTFont(_NAZWA_FONTU, str(_SCIEZKA_LIBERATION)))
		return _NAZWA_FONTU

	if _SCIEZKA_DEJAVU.is_file():
		warnings.warn(
			f"Liberation Sans nie znaleziono pod {_SCIEZKA_LIBERATION} — generator umowy PDF "
			f"przechodzi awaryjnie na DejaVu Sans ({_SCIEZKA_DEJAVU}). Oba fonty mają pełne "
			"pokrycie polskich znaków diakrytycznych, ale metryka DejaVu Sans nieznacznie różni "
			"się od Ariala, którym złożono oryginał dokumentu — sprawdź wizualnie wygenerowany PDF.",
			RuntimeWarning,
			stacklevel=2,
		)
		pdfmetrics.registerFont(TTFont(_NAZWA_FONTU, str(_SCIEZKA_DEJAVU)))
		return _NAZWA_FONTU

	raise RuntimeError(
		"Nie znaleziono ani Liberation Sans "
		f"({_SCIEZKA_LIBERATION}), ani awaryjnego DejaVu Sans ({_SCIEZKA_DEJAVU}). Bez jednego z "
		"nich nie da się poprawnie wyrenderować polskich znaków diakrytycznych — wbudowany "
		"Helvetica (kodowanie WinAnsi) ich nie ma, więc generowanie umowy jest wstrzymane."
	)


def _narysuj_warstwe_strony(
	kontekst: dict[str, Any],
	pozycje: tuple[Pole, ...],
	szerokosc_pt: float,
	wysokosc_pt: float,
	nazwa_fontu: str,
) -> bytes:
	"""Buduje jednostronicowy PDF (rozmiar dokładnie jak oryginalna strona) z
	naniesionymi wartościami wszystkich `pozycje`, które faktycznie mają coś do
	narysowania. Puste stringi i kratki o wartości innej niż `True` są pomijane
	całkowicie — nic się dla nich nie rysuje."""
	bufor = io.BytesIO()
	platno = Canvas(bufor, pagesize=(szerokosc_pt, wysokosc_pt))
	platno.setFillColor(_KOLOR_TEKSTU)

	for pole in pozycje:
		wartosc = kontekst.get(pole.klucz)
		if pole.rodzaj == "kratka":
			if wartosc is True:
				_narysuj_kratke(platno, pole, nazwa_fontu)
		elif isinstance(wartosc, str) and wartosc:
			_narysuj_tekst(platno, pole, wartosc, nazwa_fontu)

	platno.showPage()
	platno.save()
	return bufor.getvalue()


def _narysuj_kratke(platno: Canvas, pole: Pole, nazwa_fontu: str) -> None:
	"""Rysuje pojedyncze `X` wyśrodkowane w punkcie `(pole.x, pole.y)` — kratki
	zawsze mają `wyrownanie="srodek"` (zob. `crm/volteo_umowa_mapa.py`)."""
	platno.setFont(nazwa_fontu, pole.rozmiar)
	platno.drawCentredString(pole.x, pole.y, "X")


def _narysuj_tekst(platno: Canvas, pole: Pole, tekst: str, nazwa_fontu: str) -> None:
	"""Rysuje `tekst` w `(pole.x, pole.y)`, dopasowując rozmiar fontu i, w razie
	potrzeby, przycinając wartość do `pole.maks_szerokosc` (zob. `_dopasuj_rozmiar`
	i `_przytnij`), z wyrównaniem zgodnym z `pole.wyrownanie`."""
	rozmiar = _dopasuj_rozmiar(tekst, nazwa_fontu, pole.rozmiar, pole.maks_szerokosc)
	do_wypisania = _przytnij(tekst, nazwa_fontu, rozmiar, pole.maks_szerokosc)
	platno.setFont(nazwa_fontu, rozmiar)
	if pole.wyrownanie == "srodek":
		platno.drawCentredString(pole.x, pole.y, do_wypisania)
	elif pole.wyrownanie == "prawo":
		platno.drawRightString(pole.x, pole.y, do_wypisania)
	else:
		platno.drawString(pole.x, pole.y, do_wypisania)


def _dopasuj_rozmiar(tekst: str, nazwa_fontu: str, rozmiar_bazowy: float, maks_szerokosc: float | None) -> float:
	"""Zmniejsza `rozmiar_bazowy` krok po kroku (`_KROK_ZMNIEJSZANIA_PT`), aż `tekst`
	zmieści się w `maks_szerokosc`, ale nie poniżej `_MIN_ROZMIAR_FONTU_PT`. Brak
	`maks_szerokosc` (kratki, pola bez zmierzonego ograniczenia) → rozmiar bazowy
	bez zmian. To PIERWSZY krok dopasowania — dopiero gdy nawet minimalny rozmiar
	nie wystarcza, wkracza przycinanie w `_przytnij`."""
	if maks_szerokosc is None:
		return rozmiar_bazowy
	rozmiar = rozmiar_bazowy
	while rozmiar > _MIN_ROZMIAR_FONTU_PT:
		if pdfmetrics.stringWidth(tekst, nazwa_fontu, rozmiar) <= maks_szerokosc:
			return rozmiar
		rozmiar -= _KROK_ZMNIEJSZANIA_PT
	return _MIN_ROZMIAR_FONTU_PT


def _przytnij(tekst: str, nazwa_fontu: str, rozmiar: float, maks_szerokosc: float | None) -> str:
	"""Przycina `tekst` (dodając `_WIELOKROPEK`) tylko jeśli nawet przy `rozmiar`
	zwróconym przez `_dopasuj_rozmiar` nie mieści się w `maks_szerokosc`. Nigdy nie
	zawija do drugiej linii — w oryginalnym dokumencie nie ma na to miejsca."""
	if maks_szerokosc is None:
		return tekst
	if pdfmetrics.stringWidth(tekst, nazwa_fontu, rozmiar) <= maks_szerokosc:
		return tekst
	obciety = tekst
	while obciety and pdfmetrics.stringWidth(obciety + _WIELOKROPEK, nazwa_fontu, rozmiar) > maks_szerokosc:
		obciety = obciety[:-1]
	return (obciety + _WIELOKROPEK) if obciety else _WIELOKROPEK
