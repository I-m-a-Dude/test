# Licenta Pediatric Segmentation Demo

## Functionalități

* **Upload fișier NIfTI** (`.nii`, `.nii.gz`) prin endpoint FastAPI
* **Preprocesare** volum 3D (normalizare intensități, resampling la rezoluție standard, crop/padding)
* **Inferență model de segmentare** (model salvat) pentru extragerea regiunilor țintă
* **Postprocesare** rezultat (smooth, reconstrucție și export în același format NIfTI)
* **Descărcare fișier segmentat** prin API

## Arhitectură

Am ales o **arhitectură monolitică modulară, pe straturi (layered)**, pentru că:

* În contextul demo‑ului de licență oferă un setup simplu de dezvoltat și de rulat (un singur container, un singur punct de deploy).
* Permite separarea clară a responsabilităților:

  * **api/** – definirea endpoint‑urilor și validare HTTP
  * **services/** – orchestrare flux de lucru (preproc → inferență → postproc)
  * **models/** – wrapper pentru încărcarea și rularea modelului salvat
  * **core/** – configurări și logging
  * **utils/** – funcții I/O, manipulare fișiere NIfTI
* Este ușor de testat (module independente), documentat și, ulterior, scalabil (se poate extrage un serviciu dedicat de inferență dacă e necesar).

## Structura proiectului

Pentru a menține fișierele din fiecare folder cât mai simple și ușor de înțeles, poți urma aceste principii:

1. **Separa responsabilitățile clar**:
   - Fiecare fișier ar trebui să aibă o singură responsabilitate clar definită.
   - Evită să combini funcționalități multiple într-un singur fișier.

2. **Minimizează numărul de fișiere**:
   - Dacă un folder conține mai multe fișiere mici, încearcă să le grupezi logic într-un singur fișier, dacă este posibil și nu afectează claritatea.

3. **Documentează codul**:
   - Adaugă comentarii concise și clare pentru a explica scopul fiecărui fișier și funcție.

4. **Structură modulară**:
   - În fiecare folder, păstrează fișierele organizate astfel încât să reflecte fluxul aplicației (de exemplu, `preprocessing.py`, `inference.py`, `postprocessing.py` în `services/`).

5. **Evită redundanța**:
   - Reutilizează funcții comune printr-un modul `utils/` sau similar, în loc să le duplici în mai multe fișiere.

6. **Exemple pentru fiecare folder**:
   - `api/`: Un fișier per endpoint sau grup logic de endpoint-uri (ex. `upload.py`, `download.py`).
   - `services/`: Un fișier pentru fiecare etapă majoră a fluxului (ex. `preprocessing.py`, `inference.py`, `postprocessing.py`).
   - `models/`: Un fișier pentru fiecare model sau tip de model (ex. `segresnet.py`).
   - `core/`: Fișiere pentru configurare și logging (ex. `config.py`, `logger.py`).
   - `utils/`: Funcții generale (ex. `nifti_io.py`, `file_utils.py`).

Astfel, vei avea o structură clară, cu fișiere puține și ușor de înțeles.


```
project-root/
├── src/
│   ├── api/           # Endpoints FastAPI
│   ├── services/      # Preprocesare, inferență, postprocesare
│   ├── models/        # Wrapper model
│   ├── core/          # Config, logging
│   ├── utils/         # I/O NIfTI (nibabel)
│   └── main.py        # Instanțiere FastAPI
│
├── tests/             # Teste unitare și de integrare
├── docs/              # Documentație suplimentară (architecture.md)
├── Dockerfile         # Containerizare (Python + FastAPI + model)
├── requirements.txt   # Dependențe Python
├── .env.example       # Variabile de mediu (cale model, port, etc.)
└── README.md          # Descriere proiect
```

## Dependențe principale

* `fastapi` & `uvicorn` – server ASGI
* `torch` (sau `tensorflow`) – framework ML pentru inferență
* `nibabel` – citire/scriere volume NIfTI
* `numpy` – procesare numerică
* `python-multipart` – suport upload fișiere
* `pydantic` – validare date FastAPI
* `pytest` – testare

---

Acest setup oferă un echilibru între simplitate și claritate, ideal pentru demo-ul de licență și demonstrarea fluxului complet de la upload la segmentare și download.

## Flux de lucru

Fluxul complet al aplicației urmează pașii de mai jos:

1. **Recepție și validare fișier**

   * Frontend-ul React trimite un fișier NIfTI (`.nii`/`.nii.gz`) la endpoint-ul `/upload`.
   * FastAPI validează tipul și dimensiunea fișierului.

2. **Preprocesare**

   * Se citește volumul folosind `nibabel`.
   * Se normalizează intensitățile și se resamplează la rezoluție standard.
   * Se aplică crop sau padding pentru dimensiuni uniforme.

3. **Inferență**

   * Modelul salvat este încărcat din calea specificată în configurație.
   * Se rulează inferența pe volumul preprocesat pentru segmentare.

4. **Postprocesare**

   * Se aplică smooth și filtru morfologic pentru rafinarea segmentării.
   * Se reconstruieste volumul și se salvează într-un fișier NIfTI nou.

5. **Returnarea rezultatului**

   * API generează un răspuns cu fișierul segmentat, disponibil pentru descărcare pe frontend.

Acest workflow modular asigură claritate, testabilitate și posibilitatea de extindere ulterioară.
