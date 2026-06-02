# Data Center Radar - Processo ricerca nuovi progetti

## Obiettivo

Consolidare un processo ripetibile per individuare, validare e promuovere nuovi progetti data center in Italia usando fonti commerciali, autorizzative e tecniche.

Il processo distingue tre livelli:

- candidati grezzi;
- candidati validati o classificati;
- progetti promossi nel master e nella dashboard.

## Fonti principali

### Fonti commerciali / discovery

- DataCenterMap Italia
- siti operatori
- comunicati stampa operatori
- pagine campus / data center
- LinkedIn operatori, GC, EPC, contractor e societa di ingegneria
- Google Maps / ubicazioni commerciali

Operatori prioritari:

- Vantage
- STACK Infrastructure
- CloudHQ
- Retelit
- CyrusOne
- NTT / GDC
- VIRTUS
- hscale
- Equinix
- Microsoft
- AWS
- Aruba
- Noovle
- Data4
- Apto
- MIX

### Fonti autorizzative / pubbliche

- MASE VIA / VAS
- Regione Lombardia VIA / VAS
- portali regionali equivalenti
- Comuni
- SUAP
- albi pretori
- PGT
- piani attuativi
- varianti urbanistiche
- avvisi pubblici

### Fonti tecniche / commerciali avanzate

- GC / EPC / contractor
- progettisti
- societa di ingegneria
- societa impiantistiche
- operatori energia / district cooling
- potenza IT
- MWt / sistemi emergenza / gruppi elettrogeni
- superficie lotto / superficie costruita
- stato lavori

## Livelli del processo

### 1. Discovery

Raccoglie candidati da fonti esterne.

Un candidato puo entrare anche se incompleto, purche abbia almeno nome progetto o asset, operatore o fonte chiara, e localizzazione almeno comunale.

Output atteso:

- data/input/external_sources/datacenter_discovery_candidates.csv

Campi consigliati:

- candidate_name
- operator_or_main_subject
- city
- region
- source_type
- source_name
- source_url
- raw_status
- raw_power
- raw_area
- raw_address
- discovered_at
- notes

### 2. Normalizzazione e deduplica

Serve a distinguere nuovo candidato, child facility, espansione, enrichment di progetto esistente, asset operativo esistente, possibile duplicato o record da review manuale.

Esempi:

- STACK MIL08B va trattato come child/enrichment, non come nuovo master autonomo.
- STACK MIL04A va trattato come sotto-facility / enrichment.
- MIX Data Center va trattato come asset esistente/reference.
- Un record con solo fonte commerciale forte resta tracked_review.

Campi chiave:

- operator_or_main_subject
- city
- region
- address
- campus_codes
- authorization_proponent
- mase_object_ids
- dcm_source_url

### 3. Validation queue

Per ogni candidato si verificano cinque layer:

- operator_site
- regional_via_vas
- municipality_suap_albo
- mase
- contractor_gc

Per ogni layer si tracciano checked, result_status, evidence_type, result_title, result_url, evidence_note e next_action.

Classi readiness:

- ready_with_gc
- ready_missing_gc
- partial_public_confirmation
- operator_confirmed_only
- existing_project_child_or_enrichment
- existing_operational_reference
- pending_validation
- weak_or_no_public_evidence
- not_validated

Bucket dashboard:

- promotion_ready
- near_ready
- tracked_review
- do_not_promote

### 4. Promotion draft

Produce il file intermedio commerciale:

- data/output/external_sources/datacentermap_promotion_draft.csv

Regole:

- promotion_ready entra nella Vista immediata progetti;
- near_ready entra ma con qualita dati parziale;
- tracked_review resta in tabella generale come record da monitorare;
- do_not_promote resta archivio interno.

### 5. Master e schede progetto

Il master strutturato resta:

- docs/dc_project_fused_master.json

Le schede progetto vengono generate con template unico da:

- docs/dc_project_fused_master.json
- data/output/external_sources/datacentermap_promotion_draft.csv

Script:

- app/external_sources/generate_project_pages_unified.py

Output:

- docs/projects/*.html

## Pipeline operativa

La pipeline unica e:

- app/external_sources/datacenter_discovery_pipeline.py

Esegue in sequenza:

1. export review facts;
2. probe regionale;
3. curator regionale;
4. report enriched;
5. DataCenterMap probe;
6. DataCenterMap curator;
7. export nuovi candidati DataCenterMap;
8. validation queue;
9. validation summary;
10. promotion draft;
11. external candidates page;
12. unified project pages;
13. promotion homepage;
14. normalizzazione termini homepage.

## Frequenza consigliata

### Settimanale

- DataCenterMap
- siti operatori
- comunicati stampa
- LinkedIn operatori / contractor

### Quindicinale

- MASE
- Regione Lombardia / portali regionali
- Comuni / SUAP / albi pretori prioritari

### Mensile

- review tracked_review
- deduplica manuale
- promozione / declassamento candidati
- pulizia record child/enrichment

## Regola decisionale finale

| Caso | Destinazione |
|---|---|
| Operatore + MASE/Comune/Regione | master / Vista immediata |
| Operatore + fonte commerciale forte | tracked_review |
| Solo DataCenterMap | tracked_review |
| Asset esistente | existing reference |
| Child facility | enrichment, non nuovo master |
| GC identificato | priorita commerciale piu alta |
| MASE senza dati commerciali | progetto valido ma incompleto |

## Comandi standard

- .\.venv\Scripts\python.exe -m app.external_sources.datacenter_discovery_pipeline
- .\.venv\Scripts\python.exe -m app.external_sources.datacenter_discovery_pipeline --dry-run
- .\.venv\Scripts\python.exe -m app.external_sources.datacenter_discovery_pipeline --start-at datacentermap_validation_queue
