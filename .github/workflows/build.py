#!/usr/bin/env python3
"""Genera calendari iCalendar per materia dal feed pubblico UniSR (2º anno, sezione 3, viola).

Dipendenze: solo libreria standard Python 3.11+.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import html
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

SOURCE_URL = (
    "https://twentysecondproject.github.io/unisr-calendar/"
    "italiano-sezione3-viola-2anno.ics"
)
FALLBACK_URL = (
    "https://raw.githubusercontent.com/twentysecondproject/"
    "unisr-calendar/main/italiano-sezione3-viola-2anno.ics"
)

# Un calendario per ogni materia: i colori in Apple si impostano dal menu Calendari.
# Il feed UniSR usa "Morfologia Umana" per la materia indicata come Anatomia.
DEFAULT_SUBJECTS = {
    "Istologia": "#9655C8",  # viola
    "Anatomia": "#D83B3B",  # rosso
    "Genetica": "#2FA856",  # verde
    "Semeiotica": "#E6B800",  # giallo
    "Fisiologia": "#43A6DE",  # azzurro
    "Burnout": "#E38F25",  # arancione, modificabile
}
SUBJECT_ALIASES = {
    "istologia": "Istologia",
    "morfologia umana": "Anatomia",
    "anatomia": "Anatomia",
    "genetica medica": "Genetica",
    "genetica": "Genetica",
    "semeiotica": "Semeiotica",
    "fisiologia": "Fisiologia",
}
OTHER_NAME = "Altri eventi"
OTHER_COLOR = "#8291A8"


def unfold_ics(raw: str) -> list[str]:
    """RFC 5545: rimuove i folding (CRLF + spazio/tab) e restituisce linee logiche."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n[ \t]", "", text)
    return [line for line in text.split("\n") if line]


def parse_calendar(raw: str) -> tuple[list[list[str]], list[list[str]]]:
    lines = unfold_ics(raw)
    if not lines or lines[0] != "BEGIN:VCALENDAR" or "END:VCALENDAR" not in lines:
        raise ValueError("Il file di origine non è un calendario ICS valido.")
    events: list[list[str]] = []
    zones: list[list[str]] = []
    current: list[str] | None = None
    kind: str | None = None
    for line in lines:
        if line == "BEGIN:VEVENT" and current is None:
            current, kind = [line], "VEVENT"
        elif line == "BEGIN:VTIMEZONE" and current is None:
            current, kind = [line], "VTIMEZONE"
        elif current is not None:
            current.append(line)
            if line == "END:" + kind:
                (events if kind == "VEVENT" else zones).append(current)
                current, kind = None, None
    if not events:
        raise ValueError("Nessuna lezione o evento trovato: il file sorgente potrebbe essere vuoto.")
    return events, zones


def get_summary(event: list[str]) -> tuple[int, str, str]:
    for idx, line in enumerate(event):
        m = re.match(r"^(SUMMARY(?:;[^:]*)?):(.*)$", line, flags=re.I)
        if m:
            return idx, m.group(1), m.group(2)
    raise ValueError("Un evento nel calendario non ha un titolo (SUMMARY).")


def unescape_ical(text: str) -> str:
    return (text.replace(r"\n", "\n").replace(r"\N", "\n")
            .replace(r"\,", ",").replace(r"\;", ";").replace(r"\\", "\\"))


def escape_ical(text: str) -> str:
    return (text.replace("\\", r"\\").replace("\n", r"\n")
            .replace(",", r"\,").replace(";", r"\;"))


def simplify_title(original: str) -> tuple[str | None, str]:
    """Materia e titolo breve, oppure (None, ...) per lezioni non selezionate.

    Selezione esplicita: cinque materie principali e solo l'elettivo Burnout.
    Le lezioni non riconosciute NON sono incluse automaticamente: così non si
    aggiungono per sbaglio altri elettivi. Gli eventi non didattici restano.
    """
    text = unescape_ical(original).strip()
    # Identifica l'elettivo richiesto anche se nel titolo non compare "elettivo".
    if re.search(r"\bburn[ -]?out\b", text, flags=re.I):
        return "Burnout", "Burnout"
    if re.search(r"elettiv|\bADE\b", text, flags=re.I):
        return None, text
    lecture = re.match(r"^lezion[ei]\s*:\s*(.+)$", text, flags=re.I | re.S)
    if not lecture:
        return OTHER_NAME, text
    title = lecture.group(1)
    title = re.sub(r"\s*\(\s*LINEA\s+[^)]*\)", "", title, flags=re.I)
    title = re.sub(r"\s*\(\s*docente\s*:\s*[^)]*\)", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -")
    subject = SUBJECT_ALIASES.get(title.casefold())
    if subject:
        return subject, subject
    return None, title


def preserve_teacher(event: list[str], original_summary: str) -> list[str]:
    """Sposta il docente dal titolo alle note, senza perderlo."""
    found = re.search(r"\(\s*docente\s*:\s*([^)]+)\)", unescape_ical(original_summary), flags=re.I)
    if not found or not found.group(1).strip():
        return event
    teacher = found.group(1).strip()
    new_event = event.copy()
    for index, line in enumerate(new_event):
        m = re.match(r"^(DESCRIPTION(?:;[^:]*)?):(.*)$", line, flags=re.I)
        if m:
            original = unescape_ical(m.group(2))
            new_event[index] = m.group(1) + ":" + escape_ical("Docente: " + teacher + "\n\n" + original)
            return new_event
    new_event.insert(-1, "DESCRIPTION:" + escape_ical("Docente: " + teacher))
    return new_event


def safe_slug(name: str) -> str:
    value = unicodedata.normalize("NFKD", name)
    value = value.encode("ascii", errors="ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "evento"


def fold_line(line: str) -> list[str]:
    """Limita ogni linea fisica a 75 byte UTF-8 secondo RFC 5545."""
    chunks = []
    chunk = ""
    byte_len = 0
    for char in line:
        size = len(char.encode("utf-8"))
        if byte_len + size > 75:
            chunks.append(chunk)
            chunk = " "  # Continuazione: 1 byte nel limite di 75
            byte_len = 1
        chunk += char
        byte_len += size
    chunks.append(chunk)
    return chunks


def render_ics(events: list[list[str]], zones: list[list[str]], name: str, color: str) -> bytes:
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UniSR Personalizzato//Calendari per materia//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + escape_ical("UniSR · " + name),
        "X-WR-CALDESC:Calendario non ufficiale derivato dal feed pubblico UniSR Calendar",
        "X-WR-TIMEZONE:Europe/Rome",
        "X-APPLE-CALENDAR-COLOR:" + color,
    ]
    lines = header + [line for zone in zones for line in zone]
    for event in events:
        lines.extend(event)
    lines.append("END:VCALENDAR")
    physical = [piece for line in lines for piece in fold_line(line)]
    return ("\r\n".join(physical) + "\r\n").encode("utf-8")


def build_html(calendars: list[tuple[str, str, str, int]]) -> str:
    cards = []
    for title, file, color, count in calendars:
        ctitle = html.escape(title)
        cfile = html.escape(file, quote=True)
        cards.append(f'''
        <article class="cal" style="--accent:{color}">
          <div class="row"><span class="dot" aria-hidden="true"></span>
            <div><h2>{ctitle}</h2><span class="count">{count} eventi nell'ultimo aggiornamento</span></div></div>
          <a class="subscribe" data-calendar-file="{cfile}" href="{cfile}">Aggiungi ad Apple Calendario ↗</a>
        </article>''')
    today = datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M")
    return '''<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><title>UniSR · Calendario personalizzato</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#172332;background:#f6f8fc}*{box-sizing:border-box}
body{margin:0}main{max-width:920px;margin:0 auto;padding:40px 20px 72px}header{margin:0 0 28px}h1{letter-spacing:-.035em;font-size:clamp(30px,5vw,44px);margin:.2em 0}.lead{line-height:1.6;max-width:650px;color:#526279}h2{font-size:1.08rem;margin:0 0 5px}.tag{font-size:.8rem;text-transform:uppercase;letter-spacing:.13em;font-weight:750;color:#586b8c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.cal{background:#fff;border:1px solid #e5eaf1;border-radius:18px;padding:21px;box-shadow:0 3px 12px rgba(24,44,69,.03)}.row{display:flex;align-items:center;gap:12px;min-height:52px}.dot{background:var(--accent);width:16px;height:16px;flex:0 0 auto;border-radius:50%}.count{font-size:.82rem;color:#69768a}.subscribe{display:block;text-align:center;margin-top:23px;text-decoration:none;padding:12px;border-radius:10px;background:#1b55c4;color:white;font-weight:650;font-size:.92rem}.subscribe:hover{background:#13459f}footer{margin-top:25px;color:#5d6c81;font-size:.88rem;line-height:1.65}.note{margin-top:28px;background:#edf1f8;padding:17px;border-radius:12px}code{overflow-wrap:anywhere}
</style></head><body><main><header><div class="tag">Medicina e Chirurgia 3 · 2º anno · Linea viola</div>
<h1>Lezioni, finalmente leggibili.</h1><p class="lead">Titoli abbreviati, colori diversi per materia e sincronizzazione automatica con il feed UniSR Calendar. Tra i corsi elettivi viene incluso solo <strong>Burnout</strong>. Sottoscrivi ogni materia e assegna il colore indicato (o un altro) sul tuo iPhone.</p></header>
<div class="grid">''' + "".join(cards) + '''</div>
<div class="note"><strong>Come si usa</strong><p>Da Safari su iPhone, tocca “Aggiungi ad Apple Calendario” per ogni materia. Dopo la sottoscrizione vai su <strong>Calendario → Calendari → ⓘ</strong> per impostare il colore di quella materia. Al termine nascondi o disiscriviti dal precedente calendario UniSR per evitare lezioni duplicate.</p><p>Se l'iPhone scarica un file invece di proporti una sottoscrizione, apri <strong>Calendario → Calendari → Aggiungi calendario → Aggiungi calendario con iscrizione</strong> e incolla l'indirizzo HTTPS del file, ricavabile aprendo il link nella pagina.</p></div>
<footer><strong>Ultima generazione:</strong> ''' + html.escape(today) + ''' (ora italiana). Aggiornamenti richiesti da GitHub Actions ogni 4 ore; l'orario effettivo può slittare. La comparsa delle modifiche su Apple dipende anche dall'intervallo di aggiornamento impostato da Apple. Fonte: <a href="https://twentysecondproject.github.io/unisr-calendar/">UniSR Calendar</a> (progetto indipendente). Non è un servizio ufficiale UniSR. Per variazioni urgenti controlla sempre <a href="https://orario.unisr.it/default.asp">l'orario ufficiale</a>.<br>Gli eventi “Altri eventi” comprendono, per esempio, le sospensioni didattiche. Le lezioni di materie non riconosciute vengono escluse; se cambia il nome di un insegnamento, verifica il registro di GitHub Actions.</footer>
</main><script>
for(const a of document.querySelectorAll('[data-calendar-file]')) {
  const u = new URL(a.dataset.calendarFile, location.href);
  a.href = 'webcal://' + u.host + u.pathname;
}
</script></body></html>'''


def fetch_source() -> str:
    errors = []
    for url in (SOURCE_URL, FALLBACK_URL):
        try:
            req = Request(url, headers={"User-Agent": "UniSR-personalizzato/1.0", "Accept": "text/calendar,*/*"})
            with urlopen(req, timeout=30) as r:
                data = r.read(3_000_000)
            text = data.decode("utf-8-sig")
            if "BEGIN:VCALENDAR" not in text or "BEGIN:VEVENT" not in text:
                raise ValueError("Risposta non riconosciuta come ICS")
            print("Origine:", url)
            return text
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Impossibile scaricare il calendario di origine:\n" + "\n".join(errors))


def generate(raw: str, directory: Path) -> list[tuple[str, str, str, int]]:
    events, zones = parse_calendar(raw)
    grouped: dict[str, list[list[str]]] = defaultdict(list)
    skipped: dict[str, int] = defaultdict(int)
    for event in events:
        idx, prop_name, raw_title = get_summary(event)
        subject, short_title = simplify_title(raw_title)
        if subject is None:
            skipped[unescape_ical(raw_title)] += 1
            continue
        edited = event.copy()
        edited[idx] = prop_name + ":" + escape_ical(short_title)
        if subject != OTHER_NAME:
            edited = preserve_teacher(edited, raw_title)
        grouped[subject].append(edited)
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("*.ics"):
        old.unlink()
    names = list(DEFAULT_SUBJECTS) + [OTHER_NAME]
    calendars: list[tuple[str, str, str, int]] = []
    used_slugs = set()
    for name in names:
        slug = safe_slug(name)
        if slug in used_slugs:
            raise ValueError("Due materie producono lo stesso nome file: " + slug)
        used_slugs.add(slug)
        color = DEFAULT_SUBJECTS.get(name, OTHER_COLOR if name == OTHER_NAME else "#0C9CA3")
        filename = slug + ".ics"
        payload = render_ics(grouped.get(name, []), zones, name, color)
        (directory / filename).write_bytes(payload)
        calendars.append((name, filename, color, len(grouped.get(name, []))))
    (directory / "index.html").write_text(build_html(calendars), encoding="utf-8")
    (directory / ".nojekyll").write_text("", encoding="utf-8")
    print("Eventi originali:", len(events))
    for name, filename, _, count in calendars:
        print(f"- {name}: {count} → {filename}")
    print("Lezioni escluse (non fra le materie richieste):", sum(skipped.values()))
    for title, count in sorted(skipped.items()):
        print(f"  - {count} x {title}")
    return calendars


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Percorso di un ICS locale (solo per test)")
    parser.add_argument("--output", default="public", help="Cartella di output")
    args = parser.parse_args()
    try:
        raw = Path(args.input).read_text(encoding="utf-8-sig") if args.input else fetch_source()
        generate(raw, Path(args.output))
    except (OSError, ValueError, RuntimeError) as exc:
        print("ERRORE:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
