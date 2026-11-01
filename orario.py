#!/usr/bin/env python3
"""Legge l'orario pubblico UniSR (Medicina 3, anno 2, linea viola) e produce ICS."""
from __future__ import annotations
import argparse
import hashlib
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

BASE = "https://orario.unisr.it/default.asp"
COURSE_ID = "10324"  # Medicina e Chirurgia 3
YEAR = "2"
LINE = "VIOLA"

def tidy(value):
    return re.sub(r"\s+", " ", value or "").strip()

def ics_escape(value):
    return (str(value).replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))

def ics_fold(line):
    pieces, chunk = [], ""
    for char in line:
        if len((chunk + char).encode("utf-8")) > (74 if not pieces else 73):
            pieces.append(chunk)
            chunk = " " + char
        else:
            chunk += char
    return pieces + [chunk]

def request_params(day):
    return {"ext": "ok", "data": day.strftime("%d/%m/%Y"),
            "CDS_ID": COURSE_ID, "DAORA": "0", "ANNO_CORSO": YEAR,
            "id_palazzo": "0", "id_aula": "0", "lezioni": "ok"}

def parse_day(html, day):
    soup = BeautifulSoup(html, "html.parser")
    visible = tidy(soup.get_text(" ", strip=True))
    # Non pubblicare eventi del giorno sbagliato se UniSR ignora i filtri.
    if day.strftime("%d/%m/%Y") not in visible:
        raise ValueError("data richiesta non confermata nella pagina")
    rows = []
    current_room = ""
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            row = tidy(tr.get_text(" ", strip=True))
            room = re.search(
                r"([A-ZÀ-ÖØ-Ý0-9 .'-]+?)\s*-\s*Aula\s+"
                r"([A-ZÀ-ÖØ-Ý0-9][A-ZÀ-ÖØ-Ý0-9./'-]*(?:\s+[A-ZÀ-ÖØ-Ý0-9][A-ZÀ-ÖØ-Ý0-9./'-]*)*)"
                r"(?:\s*\(([^)]*)\))?", row, re.I)
            if room:
                current_room = tidy(room.group(1)) + " Aula " + tidy(room.group(2))
                if room.group(3):
                    current_room += " (" + tidy(room.group(3)) + ")"
            if "Lezione:" not in row:
                continue
            cells = [tidy(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
            combined = " | ".join(c for c in cells if c)
            times = re.search(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})", combined)
            if not times:
                continue
            subject = re.search(r"(Lezione:\s*.*?\(docente:\s*.*?\))", combined, re.I)
            if subject:
                title = tidy(subject.group(1))
            else:
                title = next((c for c in cells if c.lower().startswith("lezione:")), "")
            if not title:
                continue
            line = re.search(r"\(\s*LINEA\s+([^)]+)\)", title, re.I)
            if line and tidy(line.group(1)).casefold() != LINE.casefold():
                continue
            rows.append({"day": day, "start": times.group(1), "end": times.group(2),
                         "title": title, "room": current_room})
    if not rows and "nessun risultato" not in visible.casefold():
        raise ValueError("nessuna lezione e messaggio 'Nessun risultato' assente")
    unique = {}
    for item in rows:
        key = (item["day"], item["start"], item["end"], item["title"], item["room"])
        unique[key] = item
    return list(unique.values())

def to_calendar(events):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//UniSR Personalizzato//Orario di Medicina 3//IT",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:UniSR sorgente", "X-WR-TIMEZONE:Europe/Rome"]
    # Un UID stabile anche quando UniSR cambia l'orario della lezione.
    grouped = {}
    for e in events:
        grouped.setdefault((e["day"].isoformat(), e["title"]), []).append(e)
    for group in grouped.values():
        group.sort(key=lambda e: (e["start"], e["end"], e["room"]))
        for n, e in enumerate(group, 1):
            uid_key = "%s|%s|%d" % (e["day"], e["title"], n)
            uid = hashlib.sha256(uid_key.encode()).hexdigest()[:24] + "@unisr-personalizzato"
            start = e["day"].strftime("%Y%m%d") + "T" + e["start"].replace(":", "") + "00"
            end = e["day"].strftime("%Y%m%d") + "T" + e["end"].replace(":", "") + "00"
            lines += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + timestamp,
                      "DTSTART;TZID=Europe/Rome:" + start,
                      "DTEND;TZID=Europe/Rome:" + end,
                      "SUMMARY:" + ics_escape(e["title"]),
                      "LOCATION:" + ics_escape(e["room"]),
                      "URL:" + BASE, "STATUS:CONFIRMED", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(p for line in lines for p in ics_fold(line)) + "\r\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="raw.ics")
    parser.add_argument("--days-ahead", type=int, default=100)
    parser.add_argument("--days-back", type=int, default=14)
    args = parser.parse_args()
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Rome")).date()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; UniSR-personalizzato/1.0)"})
    all_events, valid_days, errors = [], 0, []
    for offset in range(-args.days_back, args.days_ahead + 1):
        day = today + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        try:
            response = session.get(BASE, params=request_params(day), timeout=25)
            response.raise_for_status()
            found = parse_day(response.text, day)
            all_events.extend(found)
            valid_days += 1
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{day.isoformat()}: {exc}")
        time.sleep(0.18)
    print(f"Giorni verificati: {valid_days}, errori: {len(errors)}, lezioni raccolte: {len(all_events)}")
    for error in errors[:15]:
        print("ATTENZIONE:", error)
    # Mai sovrascrivere i calendari pubblicati se UniSR non è accessibile.
    if valid_days < 40 or len(all_events) < 5 or len(errors) > valid_days // 3:
        raise RuntimeError("Orario UniSR non verificabile: pubblicazione interrotta per evitare calendari incompleti.")
    Path(args.output).write_text(to_calendar(all_events), encoding="utf-8")
    print("Creato:", args.output)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERRORE:", exc, file=sys.stderr)
        sys.exit(1)
