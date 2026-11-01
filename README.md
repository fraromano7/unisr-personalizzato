# UniSR · Calendario personalizzato (2° anno, sezione 3, linea viola)

Crea automaticamente calendari `.ics` separati per **Morfologia Umana, Istologia, Fisiologia, Genetica Medica, Semeiotica e altri eventi**, partendo dal calendario pubblico [UniSR Calendar](https://twentysecondproject.github.io/unisr-calendar/). Ogni titolo in Apple Calendario inizia direttamente con il nome della materia, senza «Lezione:», «LINEA VIOLA» o il nome del docente (il docente viene spostato nelle note; aula e orari restano nei singoli eventi). Se compaiono nuove materie, vengono creati automaticamente nuovi calendari, da sottoscrivere una volta. I colori sono suggeriti, ma **vanno impostati sul dispositivo Apple**.

## Pubblicare con GitHub (configurazione iniziale)

1. Accedi a [GitHub](https://github.com/) e crea un **repository pubblico** chiamato `unisr-personalizzato`, selezionando **Add a README = NO** (repository inizialmente vuoto).
2. Estrai il file ZIP in una cartella del computer. Apri il repository GitHub, scegli **uploading an existing file** e trascina i contenuti estratti, **inclusa la cartella `.github`**. Controlla che il file `.github/workflows/pubblica.yml` sia stato caricato. Salva con **Commit changes** sul ramo `main`.
3. Vai in **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Apri **Actions → Aggiorna calendari UniSR → Run workflow** e avvia. Attendi che compaia una spunta verde: nel registro dell'azione trovi il link del sito pubblicato, normalmente `https://TUO-USERNAME.github.io/unisr-personalizzato/`.
5. Apri **quel sito con Safari su iPhone**, aggiungi le materie che ti interessano e per ciascuna assegna il colore in **Calendario → Calendari → ⓘ**. Poi nascondi o rimuovi la precedente sottoscrizione UniSR per evitare duplicati.

### Come funziona l'aggiornamento

GitHub Actions tenta di recuperare il feed ogni **4 ore** (non è una garanzia sull'ora esatta di esecuzione); la visualizzazione delle modifiche dipende anche da Apple e dal momento in cui il servizio terzo aggiorna i suoi dati. Controlla sempre l'orario ufficiale per eventuali cambiamenti improvvisi. Per forzare una verifica manuale: **Actions → Aggiorna calendari UniSR → Run workflow**.

**Attenzione:** i repository pubblici e le GitHub Pages sono consultabili da chi conosce il link; gli orari nel feed sono già pubblici. Per account inattivi, GitHub può disabilitare i workflow programmati di un repository pubblico dopo un periodo di inattività: se gli aggiornamenti si fermano, controlla la scheda Actions.

### Problemi comuni

- **Non trovi le materie nella pagina:** il workflow potrebbe non essere ancora stato eseguito, oppure GitHub Pages non è configurato come `GitHub Actions`.
- **La pagina GitHub risponde 404:** apri Actions e verifica l'esito della pubblicazione, poi ricarica il sito.
- **iPhone scarica un file `.ics`:** non importarlo come calendario statico. Usa **Calendario → Calendari → Aggiungi calendario → Aggiungi calendario con iscrizione** e incolla l'URL HTTPS del file `.ics` sulla tua GitHub Pages.
- **Vedi eventi doppi:** nascondi o rimuovi il precedente calendario in abbonamento, dopo aver verificato la nuova sottoscrizione.
- **Mancano lezioni:** il sistema copia il feed terzo, che potrebbe essere incompleto o aggiornarsi in ritardo. Verifica l'orario ufficiale su https://orario.unisr.it/default.asp.
- **Il colore non corrisponde:** modificalo nella schermata di dettaglio di ciascun calendario in Apple Calendario.

## Dati e struttura

Il file `build.py` usa soltanto la libreria standard di Python. Preserva UID, date, orari, luoghi e dettagli non modificati; abbrevia il campo `SUMMARY`, sposta il docente nel campo `DESCRIPTION` e smista gli eventi per nome. Gli altri eventi, incluse le sospensioni didattiche, vanno in `Altri eventi`.

Origine: [twentysecondproject/unisr-calendar](https://github.com/twentysecondproject/unisr-calendar), progetto indipendente. Questo kit non è approvato né gestito da UniSR e dipende dal feed originale.

### Test locale (facoltativo)

```shell
python build.py --input calendario-esempio.ics --output public
```

Oppure, con accesso a Internet:

```shell
python build.py --output public
```
