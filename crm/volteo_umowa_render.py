# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Generator PDF-u umowy: nakłada dane z kontekstu na ORYGINALNY plik PDF.

Moduł celowo NIE odtwarza dokumentu w HTML — bierze gotowy plik dostarczony
przez prawnika (`crm/szablony/umowa_pv_me.pdf`) i rysuje na nim wartości z
`crm.volteo_umowa_pdf.zbuduj_kontekst()`, w miejscach opisanych przez
`crm.volteo_umowa_mapa.MAPA`. Dzięki temu treść prawna, logo, stopka, fonty
i podział stron są dokładnie takie jak w oryginale — bo to fizycznie ten sam
plik, tylko z naniesioną warstwą.

BEZPIECZNIK (dokument prawny podpisywany przez klienta): `zloz_umowe()`
sprawdza sumę SHA-256 przekazanego szablonu względem `SHA256_SZABLONU` z
`crm/volteo_umowa_mapa.py` i przerywa z czytelnym komunikatem przy
niezgodności. Współrzędne w `MAPA` są skalibrowane WYŁĄCZNIE dla dokładnie
jednej wersji pliku źródłowego — każda zmiana szablonu (nawet kosmetyczna)
unieważnia je, więc lepsza jest głośna awaria niż dane naniesione w cudzą
rubrykę.

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
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from crm.volteo_umowa_mapa import MAPA, SHA256_SZABLONU, Pole

_NAZWA_SZABLONU: str = "umowa_pv_me.pdf"
"""Nazwa pliku wbudowanego szablonu wewnątrz `crm/szablony/` — jedyne miejsce,
które trzeba zmienić, gdyby nazwa pliku szablonu kiedyś się zmieniła."""

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


def sciezka_wbudowanego_szablonu() -> Path:
	"""Zwraca ścieżkę do wbudowanego szablonu PDF-u umowy (`crm/szablony/umowa_pv_me.pdf`).

	Wołający (np. `crm/api/umowa.py`) nie musi znać układu katalogów pakietu —
	wystarczy przeczytać wskazany plik binarnie i przekazać jego zawartość do
	`zloz_umowe()` jako `szablon_pdf`.
	"""
	return Path(__file__).resolve().parent / "szablony" / _NAZWA_SZABLONU


def zloz_umowe(kontekst: dict[str, Any], szablon_pdf: bytes) -> bytes:
	"""Nakłada `kontekst` na `szablon_pdf` i zwraca gotowy PDF w bajtach.

	Kroki: (1) suma SHA-256 `szablon_pdf` musi się zgadzać z `SHA256_SZABLONU`
	— w przeciwnym razie funkcja przerywa z czytelnym wyjątkiem, zamiast
	nanieść dane w oparciu o nieaktualne współrzędne; (2) `szablon_pdf`
	klonujemy bezpośrednio do `PdfWriter` (`clone_from=`), więc strony, na
	których rysujemy, są od razu DOŁĄCZONE do writera — pypdf w wersji 6.x
	oznacza jako przestarzały (i "niewiarygodny") wariant, w którym scala się
	strony `PdfReader` PRZED dodaniem ich do writera przez `add_page()`; (3) dla
	każdej strony, na której `MAPA` ma choć jedną pozycję, budujemy
	jednostronicową warstwę `reportlab` (rozmiar strony brany z oryginału przez
	`pypdf`, nie zakładany na sztywno) i scalamy ją z tą stroną (`merge_page`
	— warstwa rysuje się NA WIERZCHU oryginału); (4) strony bez żadnej pozycji
	w `MAPA` przechodzą bez zmian.

	Nie mutuje `kontekst` ani `szablon_pdf` — obie wartości są tylko czytane.
	"""
	_sprawdz_sume_kontrolna(szablon_pdf)
	nazwa_fontu = _zarejestruj_font()
	pozycje_wg_strony = _pogrupuj_wg_strony(MAPA)

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


def _sprawdz_sume_kontrolna(szablon_pdf: bytes) -> None:
	"""Bezpiecznik: przerywa, gdy `szablon_pdf` nie jest bajt-w-bajt tym plikiem,
	dla którego `crm/volteo_umowa_mapa.py` był mierzony."""
	suma = hashlib.sha256(szablon_pdf).hexdigest()
	if suma != SHA256_SZABLONU:
		raise ValueError(
			"Szablon umowy PDF został zmieniony — mapa współrzędnych w "
			"`crm/volteo_umowa_mapa.py` wymaga ponownego pomiaru. Generowanie "
			"wstrzymane, żeby nie nanieść danych w niewłaściwe miejsca. "
			f"Oczekiwana suma SHA-256: {SHA256_SZABLONU}, otrzymana: {suma}."
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
