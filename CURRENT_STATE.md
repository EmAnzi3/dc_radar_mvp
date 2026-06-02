# CURRENT STATE â€” DC Radar MVP

## Obiettivo

Radar operativo per individuare e consolidare candidati/progetti data center e contatti commerciali collegati.

## Workflow operativo

Seed e fonti esterne; parsing MASE/Terna e fonti collegate; enrichment; costruzione dataset candidati; generazione dashboard/report.

## File e cartelle critiche

- app/
- scripts/
- data/
- docs/index.html
- reports/
- requirements.txt

## Cose da non rompere

- Non perdere candidati potenzialmente utili.
- Tenere distinta la pipeline principale dagli esperimenti esterni finchÃ© non sono integrati.
- Preservare leggibilitÃ  commerciale della dashboard.
- Evitare modifiche UI non richieste su colonne e filtri.

## Stato corrente

- Stato: da aggiornare dopo il prossimo giro operativo.
- Ultima verifica manuale: da compilare.
- Ultima pubblicazione: da compilare.
- Ultimo commit stabile noto: da compilare.

## Problemi aperti

- Da compilare.

## Prossimo passo consigliato

1. Eseguire `.\scripts\check_before_publish.ps1`.
2. Controllare `git status` e `git diff --check`.
3. Aggiornare questa pagina se cambia il workflow.
4. Committare con messaggio piccolo e tematico.

