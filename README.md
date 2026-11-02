# UniSR · Calendario personalizzato — Medicina 3, 2° anno, linea viola

Questo progetto pubblica calendari iCalendar separati per **Istologia (viola), Anatomia (rosso), Genetica (verde), Semeiotica (giallo), Fisiologia (azzurro)** e **Burnout (arancione)**. I titoli sono abbreviati e non iniziano con «Lezione:». Il docente viene riportato nelle note.

## Stato di Burnout

L'elettivo **Burnout e stress lavoro correlato nella professione medica**, codice UniSR **1396**, figura nell'offerta formativa 2026/27 (primo semestre, 24 ore). Non sono però stati trovati suoi appuntamenti nel calendario aule pubblico nelle date 1° ottobre 2026 – 15 gennaio 2027, dopo aver controllato gli ordinamenti pubblicati per Medicina 1, 2 e 3, al secondo/terzo anno.

Per non inventare date, `burnout.ics` è **vuoto finché UniSR non pubblica gli orari**. È possibile sottoscriverlo già ora: eventuali lezioni future compariranno con i successivi aggiornamenti se pubblicate nel filtro previsto. Se gli orari vengono comunicati in un'area riservata, occorre fornire l'elenco o uno screenshot per importarli correttamente.

## Come si usa su iPhone

1. Apri **https://fraromano7.github.io/unisr-personalizzato/** con Safari.
2. Seleziona «Aggiungi ad Apple Calendario» per ogni materia. **Sottoscrivi**, non importare un file statico.
3. In Calendario → Calendari → ⓘ, modifica i colori per ogni sottoscrizione.
4. Nascondi il vecchio calendario UniSR per evitare eventi doppi, soltanto dopo aver verificato gli eventi.

## Aggiornamenti

GitHub Actions controlla il portale pubblico **https://orario.unisr.it/default.asp** ogni **sei ore** (fuso UTC, esecuzioni eventualmente ritardate). Il progetto ripubblica i file .ics con nomi invariati, così Apple può aggiornare le sottoscrizioni; i tempi di aggiornamento su iPhone dipendono anche dall'app Calendario.

Il corso ordinario di secondo anno viene letto dal programma «Medicina e Chirurgia 3» con identificativo `10324`; l'elettivo Burnout viene cercato separatamente nel terzo anno dell'ordinamento 2024 (`10285`), senza importare altri elettivi. Se il portale non restituisce abbastanza date affidabili, la pubblicazione si interrompe anziché sostituire i calendari con file vuoti.

Per avviare manualmente: **Actions → Aggiorna calendari UniSR → Run workflow**. Il workflow pubblica il sito tramite GitHub Pages.

## Limiti

Non è un progetto ufficiale UniSR. Controlla l'orario universitario per variazioni urgenti; la sottoscrizione non è una notifica in tempo reale. I file del repository e i calendari pubblicati sono accessibili pubblicamente.
