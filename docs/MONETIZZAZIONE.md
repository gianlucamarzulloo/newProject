# Piano per far crescere EngLab e guadagnarci

Le cifre di seguito sono **stime indicative**, non promesse: dipendono quasi solo da quante persone usano il sito.

## Come si guadagna

| Fonte | Quando attivarla | Ordine di grandezza |
|---|---|---|
| **Google AdSense** (banner già predisposti) | dopo qualche settimana online, con contenuti indicizzati | circa 1–4 € ogni 1000 pagine viste in Italia (RPM) |
| **Donazioni** (Ko-fi / Buy Me a Coffee, pulsante già presente) | da subito | pochi euro al mese all'inizio, crescono intorno agli esami |
| **Versione Premium** (fase 3) | quando ci sono utenti abituali | 2–4 €/mese o "pass sessione d'esame" |
| **Affiliazioni** (Amazon: libri di esercizi, calcolatrici) | con la crescita del traffico | piccole percentuali sulle vendite |

In pratica: **10.000 pagine viste al mese ≈ 10–40 €**, **100.000 ≈ 100–400 €** di sola pubblicità.
Il traffico degli studenti ha picchi forti nelle sessioni d'esame (gennaio-febbraio, giugno-luglio, settembre).

## Fase 1: online e utile (settimana 1-2)

- [ ] Creare un account su [Render](https://render.com) e fare il deploy (vedi README): è gratis.
- [ ] Comprare un dominio `.it` o `.com` (circa 10 €/anno), es. `englab.it` o `esercizisvolti-ing.it`, e collegarlo.
- [ ] Impostare `ENGLAB_SITE_URL` con il dominio definitivo.
- [ ] Registrare il sito su [Google Search Console](https://search.google.com/search-console) e inviare `/sitemap.xml`.
- [ ] Creare una pagina Ko-fi o Buy Me a Coffee e impostare `ENGLAB_DONATE_URL`.
- [ ] (Facoltativo) [Plausible](https://plausible.io) o un'alternativa senza cookie per sapere quali strumenti vengono usati.

## Fase 2: portare utenti (mese 1-3)

Il vantaggio è che **sei tu stesso il pubblico**: sai dove si trovano gli studenti di ingegneria.

1. **Gruppi del corso** (WhatsApp/Telegram/Discord): condividi i link agli esercizi svolti con il pulsante
   *Condividi*. Un link che risolve l'esercizio su cui tutti sono bloccati porta visite vere.
2. **Reddit e forum**: r/ingegneria, r/Universitaly, gruppi Facebook di matricole. Rispondi alle domande
   con un link al passaggio, senza spam.
3. **Video brevi** (TikTok, Reels, Shorts): registra lo schermo mentre il sito risolve uno studio di funzione
   o mostra il fenomeno di Runge. Il contenuto "esercizio d'esame risolto in 30 secondi" funziona bene.
4. **SEO**: ogni pagina ha già titolo, descrizione, dati strutturati e teoria. Per crescere su Google servono
   **pagine di esercizi svolti** (es. "studio di funzione di ln(x)/x svolto"): sono ricerche specifiche con poca
   concorrenza. Prossimo sviluppo consigliato: generare automaticamente queste pagine dagli esempi.
5. **Rappresentanti degli studenti e tutor**: proponi il sito come strumento di verifica per gli esercizi.

## Fase 3: attivare la pubblicità

Requisiti di AdSense: avere **almeno 18 anni**, un dominio proprio e contenuti originali sufficienti.

- [ ] Richiedere l'account su [Google AdSense](https://adsense.google.com) e aggiungere il sito.
- [ ] Impostare `ENGLAB_ADSENSE_CLIENT` (es. `ca-pub-…`): il sito pubblica da solo `ads.txt` e lo script di verifica.
- [ ] **Obbligatorio in UE**: attivare in AdSense *Privacy e messaggi → GDPR*, che mostra il banner del consenso
  (piattaforma di consenso certificata, gratuita).
- [ ] Creare un'unità pubblicitaria "display" responsive e impostare `ENGLAB_ADSENSE_SLOT`.
  I banner compaiono sotto i risultati e nelle pagine di sezione, non sopra il form, per non peggiorare l'uso.
- [ ] Completare la pagina `/privacy` (il testo attuale è un modello da adattare) e impostare `ENGLAB_CONTACT_EMAIL`.

## Fase 4: Premium (quando ci sono utenti che tornano)

Idee per funzioni a pagamento che il gratuito non ha (i calcoli base restano gratis, altrimenti si perde il traffico SEO):

- **Generatore di esercizi** con soluzione, per argomento e difficoltà ("10 integrali per parti").
- **Simulazione d'esame** a tempo, con correzione.
- **Export PDF** pulito degli esercizi svolti, senza pubblicità.
- Storico e raccolte personali di esercizi.

Pagamenti semplici con Stripe Payment Links o Lemon Squeezy (gestisce anche l'IVA UE), senza scrivere un sistema di pagamento.

## Aspetti fiscali (da verificare)

I guadagni vanno dichiarati. Finché sono piccoli e occasionali di solito rientrano nei "redditi diversi"
della dichiarazione dei redditi; se l'attività diventa continuativa può servire la partita IVA (regime forfettario).
**Chiedi a un CAF o a un commercialista** prima di superare qualche centinaio di euro: è una consulenza veloce e
spesso economica.

## Costi

| Voce | Costo |
|---|---|
| Hosting Render (piano free) | 0 € (il sito si "addormenta" dopo 15 minuti senza visite: il primo caricamento è lento) |
| Hosting quando cresce (Render Starter o VPS Hetzner) | circa 5–7 €/mese |
| Dominio | circa 10 €/anno |
