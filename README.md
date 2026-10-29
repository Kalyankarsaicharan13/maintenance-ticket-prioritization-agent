# Fielddesk | Maintenance triage

A local-first maintenance-ticket decision-support prototype for renewable-energy assets. The React interface uses a FastAPI service to classify an issue, assign a review priority, suggest a probable cause and next action, retrieve a similar bundled example, and route it to a responsible team.

## Run locally

Prerequisites: Python 3.10+ and Node.js 20+.

From the repository root, install the Python requirements and start the API:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

In a second terminal, start React:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). Vite proxies `/api` requests to FastAPI on port 8000. FastAPI's interactive API documentation is at `http://localhost:8000/docs`.

For a production-like local run, build React with `npm --prefix frontend ci` and `npm --prefix frontend run build`, then start `uvicorn backend.app:app --host 0.0.0.0 --port 8000` from the repository root. FastAPI serves `frontend/dist` when that build exists.

## API

- `GET /api/health`: service health check.
- `GET /api/tickets`: bundled queue with generated category, severity, and disposition.
- `POST /api/triage`: classify one ticket. JSON body: `{"description":"Inverter 4 tripping repeatedly after noon, high temperature alarm visible","asset_type":"solar"}`.
- `GET /api/metrics`: bundled-label comparison, with per-ticket results and an explicit in-sample warning.

Descriptions must contain 8–2,000 characters; `asset_type` is optional and defaults to `unknown`.

## Decision logic

1. Normalize ticket whitespace and combine the description with the asset type.
2. Apply explicit fault-pattern rules for inverter thermal alarms, gearbox vibration, inspection compliance, SCADA/data gaps, blade pitch faults, and grid curtailment. A matched rule supplies category, probable cause, recommended action, and a team route.
3. Assign severity using safety-first signal overrides, category-specific baselines, and conservative manual review when no known category matches. The prototype elevates explicit immediate safety/containment signals and worsening gearbox vibration/noise to critical.
4. Retrieve the closest bundled example using TF-IDF word and bigram cosine similarity. The retrieved ticket is evidence for comparison, not a model prediction or proof of root cause.
5. Return the decision, severity explanation, retrieval evidence, routing disposition, and a five-step tool trace. Unsupported issues go to `manual_review` with low confidence rather than receiving a guessed category.

The rules and routes are deterministic, inspectable, and run offline after dependencies are installed. Similarity-threshold confidence is heuristic, not calibrated. Severity is a triage suggestion and must be confirmed by an authorized operator against live asset condition, site procedures, and operational impact.

## Evaluation

Run the focused checks from the repository root:

```powershell
python -m unittest backend.test_triage -v
python -c "from backend.triage import evaluate_examples; print(evaluate_examples())"
```

The bundled CSV contains only six synthetic labeled tickets. The current rules match all six supplied category labels (6/6, 100%) and severity labels (6/6, 100%). This is an **in-sample rule check**, not a holdout test, cross-validation, or evidence of expected production performance; the examples informed the rules. No statistically meaningful generalization claim is possible with this dataset. Add independently labeled, site-reviewed tickets and report per-class precision, recall, F1, confusion matrices, and severity-specific safety review before operational use.

## Assumptions and limitations

- The dataset's target labels are treated as the expected answer for the six demonstrations; no additional site policy or asset telemetry is bundled.
- Category rules cover only the six fault families represented in the data. New failure modes, ambiguous descriptions, conflicting signals, and multi-fault tickets need human review.
- Severity uses text signals and category baselines only. It cannot see live alarms, redundancy, generation loss, work permits, isolation state, weather, or personnel exposure.
- Retrieval returns one of six examples, including for an unknown ticket; a low similarity does not make the example relevant. Similarity is shown to let the reviewer judge it.
- The UI/API are a prototype, not an authenticated or audited maintenance-management system. No work order is actually created or dispatched.

## Render deployment

The repository includes a multi-stage `Dockerfile` and `render.yaml`. The Docker build compiles the React app with Node 22, installs the Python dependencies, and copies both into one FastAPI web service. Render supplies `PORT`; the container uses it and serves the React build from FastAPI. No API keys or external services are required.

To deploy, push the repository to GitHub, then in Render choose **New + → Blueprint** and select this repository. Render reads `render.yaml` to create the Docker web service and configure the `/api/health` check. Alternatively, choose **New Web Service**, connect the repository, and select the Docker runtime with the repository root as the context. After deployment, open the generated `onrender.com` domain and verify `/api/health` returns `status: ok`, then open `/` to check the UI. Add the public deployment URL here after deployment; this workspace contains the Render configuration but has not performed a live deployment.

## Project layout

- `backend/triage.py`: deterministic classification, severity policy, TF-IDF retrieval, and example evaluation.
- `backend/app.py`: FastAPI endpoints and production static-file serving.
- `backend/test_triage.py`: focused unit tests.
- `frontend/src/`: React operations console and responsive styling.
- `data/maintenance_tickets.csv`: bundled synthetic examples.
- `Dockerfile` and `render.yaml`: Render Docker build, web service, and health check.

# Evaluation Rubric

Score each submission out of 100 using the same Greenko AI/ML intern screening philosophy.

| Area | Weight |
|---|---:|
| Problem understanding and energy-domain framing | 10 |
| Python implementation quality | 12 |
| AI/ML or GenAI method selection | 14 |
| Data preprocessing and feature engineering | 10 |
| RAG / retrieval / agentic workflow quality, where applicable | 12 |
| Evaluation metrics and validation approach | 12 |
| API/backend design | 8 |
| Frontend usability and explanation clarity | 8 |
| Documentation and reproducibility | 8 |
| Deployment readiness, including Render deployment step | 6 |

Strong submissions should clearly explain assumptions, limitations, failure cases, and next steps for productionization.
