# EngLab: esercizi di ingegneria risolti passo passo

Sito web gratuito di calcolatori **con tutti i passaggi** per gli esami del primo anno di ingegneria.
Pensato per essere utile agli studenti, posizionarsi su Google (SEO) e guadagnare con pubblicità e donazioni.

| Materia | Strumenti |
|---|---|
| **Analisi 1** | derivate (regole spiegate a ogni passo), integrali (per parti, sostituzione…), limiti (forme indeterminate, de l'Hôpital), studio di funzione completo con grafico |
| **Algebra lineare** | riduzione di Gauss-Jordan, sistemi con Rouché-Capelli, determinante (Sarrus/Laplace), inversa, autovalori e diagonalizzazione, discussione con parametro |
| **Calcolo numerico** | bisezione/Newton/secanti/punto fisso, quadratura composita, ODE (Eulero, Heun, RK4), interpolazione e fenomeno di Runge, **con il codice Python di ogni metodo** |
| **Chimica** | massa molare, bilanciamento delle reazioni, reagente limitante e stechiometria |
| **Fisica 1** | simulatori interattivi: moto del proiettile (anche con attrito), oscillatore smorzato |

Ogni risultato si può condividere con un link (utile nei gruppi WhatsApp/Telegram del corso) e stampare in PDF.

## Avvio in locale

```bash
pip install -r requirements-dev.txt
uvicorn englab.main:app --reload
# apri http://localhost:8000
pytest -q          # 125 test
```

Con Docker:

```bash
docker build -t englab .
docker run -p 8000:8000 --env-file .env englab
```

## Come è fatto

```
englab/
├── core/
│   ├── parsing.py     # input utente -> SymPy, con whitelist (niente eval libero) e notazione italiana (sen, tg, ln…)
│   └── sandbox.py     # ogni calcolo gira in un processo separato con timeout
├── modules/           # la matematica: analisi, algebra, numerico, chimica (funzioni pure, testate)
├── tools.py           # registro degli strumenti: SEO, form, esempi, teoria e "presenter" dei risultati
├── main.py            # FastAPI: pagine, API, sitemap, robots, ads.txt, rate limit
├── templates/         # pagine Jinja (HTML generato lato server, quindi indicizzabile)
└── static/            # app.js (rendering dei risultati), sim.js (fisica), CSS, KaTeX e Plotly inclusi
```

**Aggiungere uno strumento** = scrivere la funzione di calcolo in `modules/` e una voce `Tool(...)` in `tools.py`.
Form, pagina, sitemap e API si generano da soli; il test `test_every_example_runs` verifica gli esempi.

### Sicurezza (sito pubblico)
- Parser con whitelist di caratteri e nomi, valutazione senza builtins.
- Ogni calcolo in un processo figlio ucciso dopo `ENGLAB_TIMEOUT` secondi; i calcoli facoltativi (soluzione esatta) hanno un limite più breve.
- Limite di calcoli simultanei e di richieste al minuto per IP.
- Nessun dato utente salvato; KaTeX e Plotly serviti dal sito stesso, senza CDN esterni.

## Pubblicazione online

Il modo più rapido e gratuito è [Render](https://render.com): *New → Blueprint* e scegli questo repository (`render.yaml` è già pronto).
Poi imposta `ENGLAB_SITE_URL` e collega un dominio (circa 10 €/anno).
Quando il traffico cresce conviene un VPS (es. Hetzner, circa 5 €/mese), dove l'immagine Docker gira così com'è.

Il piano completo per farlo crescere e guadagnare è in **[docs/MONETIZZAZIONE.md](docs/MONETIZZAZIONE.md)**.
