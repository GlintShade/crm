# Copyright (c) 2026, ProEnergy and contributors
# For license information, please see license.txt

"""Rdzeń „Oświadczenia o zachowaniu poufności" (bramka NDA przy pierwszym logowaniu).

Moduł celowo NIE importuje ``frappe`` — z tego samego powodu co
`crm/volteo_umowa_pdf.py` / `crm/volteo_umowa_render.py`: ``frappe`` nie jest
instalowalne na tej maszynie deweloperskiej, więc to jedyny sposób na lokalną,
silną bramkę testową (`crm/test_volteo_oswiadczenie.py`). Cała logika zależna
od frameworka (odczyt/zapis stanu „czy użytkownik już podpisał", wywołanie
whitelisted API, wysyłka PDF-u do przeglądarki) mieszka gdzie indziej — tu
tylko czyste funkcje: treść dokumentu, jego suma kontrolna wersji, budowa
spersonalizowanego tekstu, porównanie wpisanego imienia i nazwiska z tym na
koncie, oraz generator PDF-u.

Font: rejestrujemy ten sam plik TTF co generator umów, przez reużytą
`crm.volteo_umowa_render._zarejestruj_font()` — Liberation Sans (z awaryjnym
przejściem na DejaVu Sans, oba z pełnym pokryciem polskich znaków
diakrytycznych). Wbudowane fonty base-14 reportlaba (Helvetica) używają
kodowania WinAnsi, w którym NIE MA `ł ą ę ś ż ź ć ń` — użycie ich
zniszczyłoby polskie imiona i nazwiska doradców. Ten moduł nie duplikuje
rejestracji fontu ani logiki awaryjnego przejścia — to JEDYNY import z
`crm.volteo_umowa_render` dopuszczony w tym pliku (poza `reportlab` i
biblioteką standardową).
"""

import hashlib
import io
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from crm.volteo_umowa_render import _zarejestruj_font

TRESC_OSWIADCZENIA: str = """\
Oświadczenie o zachowaniu poufności
z dnia {data}

Ja, niżej podpisany/a {imie_nazwisko} („Doradca Klienta") niniejszym oświadczam, że w związku z posiadaniem przeze mnie dostępu do konta w systemie ProEnergy sp. z o.o. z siedzibą w Poznaniu („Proenergy") zobowiązuję się w okresie posiadania przeze mnie dostępów do konta nadanego mi przez ProEnergy oraz w okresie 36 miesięcy po zablokowania konta w systemie ProEnergy do:

1. Utrzymywania w tajemnicy wszelkich informacji poufnych tj. wszelkie informacje handlowe, prawne lub organizacyjne dotyczące ProEnergy, mające, lub mogące potencjalnie mieć jakąkolwiek wartość finansową lub handlową, które nie są powszechnie znane i dostępne publicznie, w tym w szczególności bazy danych zawierające informacje i dane teleadresowe Klientów, w zakresie w jakim nie są one publicznie dostępne, w tym ich dane osobowe, numery telefoniczne, faksowe, adresy emailowe etc wszelkich osób działających w imieniu ProEnergy, z którymi Doradca Klienta się kontaktował lub kontaktuje lub ma możliwość skontaktowania w związku z nadanym dostępem do systemu ProEnergy. Informacjami Poufnymi są także informacje dotyczące stosowanej przez ProEnergy taktyki rynkowej, informacje specjalistyczne/ fachowe (know - how), informacje zawarte we wszelkiego rodzaju dokumentach wykorzystywanych przez ProEnergy w ramach szeroko rozumianego prowadzenia działalności gospodarczej, w tym we wzorach umów, cennikach, dokumentach korporacyjnych i wewnętrznych obowiązujących w ProEnergy, dokumentach prawnych, technicznych, projektowych, wykonawczych, administracyjnych, jak również inne dane i informacje objęte tajemnicą handlową przedsiębiorstwa, jak również wszelkie informacje, które stanowią zgodnie z art. 11 Ustawy o zwalczaniu nieuczciwej konkurencji tajemnicę przedsiębiorstwa, niezależnie od formy, w jakiej informacje te zostały uzyskane (ustnie, pisemnie, telefonicznie, elektronicznie etc) i niezależnie od źródła pochodzenia tych informacji. Za Informacje Poufne uważa się także wszelkie dane osobowe, w przetwarzaniu, których Doradca Klienta bierze lub będzie brał udział, uzyskane choćby nawet pośrednio w związku ze świadczeniem przez niego usług na rzecz ProEnergy, niezależnie od formy i źródła uzyskania przez niego tych informacji i danych, chyba że oczywistym jest, iż informacje te oraz dane są publicznie znane i powszechnie dostępne. W celu rozwiania wszelkich wątpliwości przyjmuje się, że Informacjami Poufnymi są wszelkie informacje związane z wewnętrzną i zewnętrzną działalnością ProEnergy („Informacje Poufne").

2. Wszystkie materiały i informacje drukowane, pisemne oraz inne informacje dostępne za pomocą sieci, urządzeń elektronicznych, oprogramowania komputerowego, dysków zewnętrznych, w których posiadanie Doradca Klienta wszedł w związku z wykonywaniem jego zobowiązań, będą stanowić wyłączną własność ProEnergy w zależności od podmiotu, który te materiały i informacje przekazał. W szczególności własnością ProEnergy są niemające charakteru jawnego dokumenty finansowe, techniczne, projektowe, prawne, umowy, korespondencja handlowa (w oryginale i/lub kopiach), oferty, cenniki i wszelkie inne dokumenty związane z działalnością ProEnergy, niezależnie od tego czy zostały udostępnione przez ProEnergy czy też zostały przez nią sporządzone. Dokumenty i informacje, o których mowa powyżej, jak również wszelkie bazy danych, notatki, kalendarze mogą być przez Doradcę Klienta wykorzystywane wyłącznie do celów służbowych i w interesie ProEnergy. Doradca Klienta nie jest uprawniony do kopiowania jakichkolwiek informacji, o których mowa powyżej (w tym w szczególności kalendarza i nośników zawierających bazy danych Klientów) oraz Informacji Poufnych na nośniki informacji inne niż będące wyłączną własnością ProEnergy chyba że skopiowanie tych informacji na inny nośnik informacji uzasadnione jest wyłącznie interesem i dobrem ProEnergy oraz następuje za jej zgodą. Ciężar udowodnienia, że spółka ProEnergy wyraził na powyższe zgodę, spoczywa na Doradcy Klienta.

3. Doradca Klienta jest zobowiązany do bezpiecznego przechowywania dokumentów i innych nośników danych, na których zapisane są informacje, o których mowa powyżej lub Informacje Poufne oraz ich ochrony przed dostępem do nich osób nieuprawnionych, zniszczeniem lub zagubieniem.

4. Doradca Klienta zobowiązuje się, w kontaktach z klientami i potencjalnymi klientami ProEnergy, do przekazywania wyłącznie prawdziwych, rzetelnych i aktualnych informacji dotyczących oferowanych produktów i usług, w tym w szczególności: realnego terminu realizacji montażu, rzeczywistej wysokości i warunków przyznawania dotacji oraz innych form dofinansowania, cen, parametrów technicznych urządzeń oraz warunków umowy. Doradcy Klienta nie wolno składać klientom obietnic ani zapewnień nieznajdujących pokrycia w aktualnej ofercie i rzeczywistych możliwościach ProEnergy. Naruszenie powyższego zobowiązania może stanowić podstawę do natychmiastowego zablokowania dostępu do systemu ProEnergy oraz dochodzenia odpowiedzialności na zasadach ogólnych.

5. Doradca Klienta oświadcza, iż jest w pełni świadomy i wyraża na to zgodę, iż w przypadku naruszenia obowiązku zachowania w tajemnicy Informacji Poufnych ProEnergy będzie uprawniona do dochodzenia od Doradcy Klienta zapłaty kary umownej w wysokości do maksymalnie 5.000,00 zł.

Podpisano elektronicznie w systemie CRM ProEnergy.
Data: {data}
Imię i nazwisko: {imie_nazwisko}
"""
# Punkt 4. jest NOWĄ klauzulą (rzetelność informacji przekazywanych klientom),
# nieobecną w oryginalnym dokumencie właściciela (.docx) — dodana na prośbę
# właściciela do tego zadania, ale CZEKA NA JEGO FORMALNĄ AKCEPTACJĘ treści
# przed pierwszym realnym wysłaniem do doradcy. Do czasu akceptacji traktować
# jako roboczą: nie usuwać samodzielnie, ale nie polegać na niej jako na
# finalnym brzmieniu prawnym bez potwierdzenia właściciela.

_WZORZEC_WIELU_BIALYCH_ZNAKOW = re.compile(r"\s+")
"""Wyłapuje dowolny ciąg białych znaków (spacje, tabulacje, wielokrotne spacje
wpisane przez pomyłkę) — używane do zwinięcia go do pojedynczej spacji
w `normalizuj_imie()`, żeby porównanie nie było wrażliwe na literówki
w odstępach."""

def wersja_tresci() -> str:
	"""Zwraca sumę SHA-256 (hex) SUROWEGO szablonu `TRESC_OSWIADCZENIA` — NIE
	spersonalizowanego renderu.

	To „numer wersji" dokumentu: wołający (whitelisted API forka) zapisuje ten
	hash razem z faktem podpisania, żeby przy każdej zmianie treści (np. po
	akceptacji klauzuli 4. albo jakiejkolwiek innej redakcji prawnej) dało się
	odróżnić „podpisał aktualną wersję" od „podpisał starą, nieaktualną wersję"
	— bez porównywania długich stringów przy każdym logowaniu.
	"""
	return hashlib.sha256(TRESC_OSWIADCZENIA.encode("utf-8")).hexdigest()


def zbuduj_tresc(imie_nazwisko: str, data: str) -> str:
	"""Podstawia `imie_nazwisko` i `data` do `TRESC_OSWIADCZENIA` i zwraca gotowy tekst.

	`imie_nazwisko` musi być niepustym stringiem po `strip()` — oświadczenie
	bez wskazania osoby, która je składa, nie ma żadnej wartości dowodowej,
	więc funkcja rzuca `ValueError` z czytelnym komunikatem po polsku zamiast
	po cichu wygenerować dokument z pustym polem. `data` NIE jest tu
	walidowana jako parsowalna data — wołający (API forka) formatuje ją
	zgodnie z konwencją wyświetlania dat w CRM i przekazuje jako gotowy
	string; ten moduł tylko go wstawia.

	Nie mutuje żadnego z argumentów — oba są tylko czytane.
	"""
	if not imie_nazwisko or not imie_nazwisko.strip():
		raise ValueError(
			"Nie można zbudować treści oświadczenia bez imienia i nazwiska — pole "
			"'imie_nazwisko' jest puste albo składa się wyłącznie z białych znaków."
		)
	return TRESC_OSWIADCZENIA.format(imie_nazwisko=imie_nazwisko, data=data)


def normalizuj_imie(s: str) -> str:
	"""Normalizuje `s` do porównywalnej postaci: Unicode NFC, `casefold()`
	(silniejsze niż `lower()` — poprawnie zwija np. niemieckie ß), zwinięcie
	dowolnego ciągu białych znaków do pojedynczej spacji, i przycięcie
	brzegów.

	CELOWO nie transliteruje ani nie usuwa znaków diakrytycznych — „Jozef" i
	„Józef" mają pozostać różne (zob. `imiona_zgodne()`), bo oświadczenie musi
	identyfikować osobę dokładnie tak, jak jest zapisana w systemie, nie w
	przybliżeniu.
	"""
	znormalizowany = unicodedata.normalize("NFC", s)
	zwiniety = _WZORZEC_WIELU_BIALYCH_ZNAKOW.sub(" ", znormalizowany)
	return zwiniety.strip().casefold()


def imiona_zgodne(wpisane: str, oczekiwane: str) -> bool:
	"""Porównuje `wpisane` (to, co doradca wpisał w formularzu) z `oczekiwane`
	(imię i nazwisko zapisane na jego koncie) po normalizacji obu stron przez
	`normalizuj_imie()`.

	Różnice wielkości liter i odstępów są ignorowane; różnice w znakach
	diakrytycznych NIE są ignorowane (`normalizuj_imie()` ich nie usuwa) —
	„Jozef Nowak" nie jest zgodne z „Józef Nowak". Pusty string po dowolnej
	stronie (przed albo po normalizacji) zawsze daje `False` — nigdy nie
	traktujemy braku danych jako zgodność.
	"""
	a = normalizuj_imie(wpisane)
	b = normalizuj_imie(oczekiwane)
	if not a or not b:
		return False
	return a == b


_NAZWA_STYLU_TYTUL = "OswiadczenieTytul"
_NAZWA_STYLU_NAGLOWEK = "OswiadczenieNaglowek"
_NAZWA_STYLU_TRESC = "OswiadczenieTresc"
_NAZWA_STYLU_PODPIS = "OswiadczeniePodpis"
"""Nazwy `ParagraphStyle` używane wewnątrz `zbuduj_pdf()` — wyodrębnione jako
stałe wyłącznie po to, żeby literały nie powtarzały się w kilku miejscach
funkcji budującej style."""

_MARGINES_CM = 2.0
"""Rozsądny margines A4 dla dokumentu tekstowego (bez tabel/pieczątek) —
wspólny dla wszystkich czterech krawędzi strony."""


def zbuduj_pdf(imie_nazwisko: str, data: str) -> bytes:
	"""Generuje PDF (A4) spersonalizowanego oświadczenia i zwraca go jako bajty.

	Używa `reportlab.platypus` (przepływowy layout, NIE rysowanie na sztywno
	skalibrowanych współrzędnych jak `crm/volteo_umowa_render.py` — tu nie ma
	gotowego szablonu firmowego do nałożenia, dokument składamy od zera) —
	dokument może swobodnie rozlać się na 2 strony, jeśli treść tego wymaga;
	funkcja NIGDY nie przycina treści, żeby zmieścić ją na jednej stronie.

	Font rejestrujemy przez reużytą `crm.volteo_umowa_render._zarejestruj_font()`
	(Liberation Sans, awaryjnie DejaVu Sans — oba z pełnym pokryciem polskich
	znaków diakrytycznych) i używamy jej nazwy we WSZYSTKICH stylach akapitów
	— w tym w tytule i bloku podpisu, nie tylko w treści.

	Walidacja `imie_nazwisko` dzieje się w `zbuduj_tresc()` (wołanej
	wewnątrz) — pusta wartość rzuca stamtąd `ValueError` zanim cokolwiek
	zostanie narysowane.

	Nie mutuje żadnego z argumentów.
	"""
	tresc = zbuduj_tresc(imie_nazwisko, data)
	nazwa_fontu = _zarejestruj_font()

	styl_tytul = ParagraphStyle(
		_NAZWA_STYLU_TYTUL,
		fontName=nazwa_fontu,
		fontSize=15,
		leading=19,
		alignment=TA_CENTER,
		textColor=colors.black,
		spaceAfter=4,
	)
	styl_naglowek = ParagraphStyle(
		_NAZWA_STYLU_NAGLOWEK,
		fontName=nazwa_fontu,
		fontSize=10,
		leading=13,
		alignment=TA_CENTER,
		textColor=colors.black,
		spaceAfter=16,
	)
	styl_tresc = ParagraphStyle(
		_NAZWA_STYLU_TRESC,
		fontName=nazwa_fontu,
		fontSize=10,
		leading=14,
		alignment=TA_JUSTIFY,
		textColor=colors.black,
		spaceAfter=10,
	)
	styl_podpis = ParagraphStyle(
		_NAZWA_STYLU_PODPIS,
		fontName=nazwa_fontu,
		fontSize=10,
		leading=14,
		alignment=TA_JUSTIFY,
		textColor=colors.black,
		spaceBefore=14,
	)

	akapity_wejsciowe = _rozbij_na_akapity(tresc)
	elementy = _zbuduj_elementy_pdf(
		akapity_wejsciowe, styl_tytul, styl_naglowek, styl_tresc, styl_podpis
	)

	bufor = io.BytesIO()
	dokument = SimpleDocTemplate(
		bufor,
		pagesize=A4,
		leftMargin=_MARGINES_CM * cm,
		rightMargin=_MARGINES_CM * cm,
		topMargin=_MARGINES_CM * cm,
		bottomMargin=_MARGINES_CM * cm,
		title="Oświadczenie o zachowaniu poufności",
	)
	dokument.build(elementy)
	return bufor.getvalue()


def _rozbij_na_akapity(tresc: str) -> tuple[str, ...]:
	"""Dzieli spersonalizowany `tresc` (wyjście `zbuduj_tresc()`) na akapity po
	PUSTEJ LINII — dokładnie ta granica oddziela tytuł, wstęp, każdy z pięciu
	punktów numerowanych, i blok podpisu w `TRESC_OSWIADCZENIA`. Puste akapity
	(np. z podwójnych pustych linii) są odrzucane."""
	bloki = tresc.split("\n\n")
	return tuple(blok.strip() for blok in bloki if blok.strip())


def _zbuduj_elementy_pdf(
	akapity: tuple[str, ...],
	styl_tytul: ParagraphStyle,
	styl_naglowek: ParagraphStyle,
	styl_tresc: ParagraphStyle,
	styl_podpis: ParagraphStyle,
) -> list[Paragraph | Spacer]:
	"""Mapuje akapity wyprodukowane przez `_rozbij_na_akapity()` na listę
	elementów `platypus` gotowych do `SimpleDocTemplate.build()`.

	Pierwszy akapit to zawsze tytuł+data (dwie linie sklejone `\\n` w
	`TRESC_OSWIADCZENIA` — rozbijane tu na osobne style: tytuł pogrubiony
	wyśrodkowany, data pod nim mniejszą czcionką). Ostatni akapit to zawsze
	blok podpisu („Podpisano elektronicznie…" / „Data: …" / „Imię i
	nazwisko: …") — wyrównany do lewej, oddzielony dodatkowym odstępem od
	reszty treści. Wszystko pomiędzy to punkty numerowane (albo — dla
	zdegenerowanego wejścia — zwykłe akapity), sprawiedliwie wyjustowane.

	Nie mutuje `akapity`."""
	if not akapity:
		return []

	elementy: list[Paragraph | Spacer] = []

	pierwszy = akapity[0]
	linie_tytulu = pierwszy.split("\n", 1)
	tytul = linie_tytulu[0]
	elementy.append(Paragraph(_escape(tytul), styl_tytul))
	if len(linie_tytulu) > 1:
		elementy.append(Paragraph(_escape(linie_tytulu[1]), styl_naglowek))
	else:
		elementy.append(Spacer(1, 12))

	srodkowe = akapity[1:-1] if len(akapity) > 2 else ()
	for akapit in srodkowe:
		tekst_jednoliniowy = " ".join(akapit.split("\n"))
		elementy.append(Paragraph(_escape(tekst_jednoliniowy), styl_tresc))

	if len(akapity) > 1:
		ostatni = akapity[-1]
		for linia in ostatni.split("\n"):
			if linia.strip():
				elementy.append(Paragraph(_escape(linia.strip()), styl_podpis))

	return elementy


def _escape(tekst: str) -> str:
	"""Ucieka znaki specjalne mini-języka znaczników `reportlab` (`&`, `<`,
	`>`) w tekście pochodzącym z danych (imię i nazwisko doradcy), zanim
	trafi do `Paragraph` — bez tego np. `<` w nazwisku zepsułoby parsowanie
	znaczników wewnątrz akapitu. `TRESC_OSWIADCZENIA` sam nie zawiera tych
	znaków, ale `imie_nazwisko` jest daną wejściową, więc funkcja jest
	stosowana jednolicie do wszystkich akapitów, nie tylko tych z
	podstawieniem."""
	return tekst.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
