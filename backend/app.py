from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.triage import DATA_PATH, evaluate_examples, triage_ticket


BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(
    title="Renewable Operations | Maintenance Triage",
    description="Rule-based maintenance-ticket classification, severity assessment, retrieval, and routing.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class TicketRequest(BaseModel):
    description: str = Field(min_length=8, max_length=2000)
    asset_type: str = Field(default="unknown", min_length=1, max_length=40)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "maintenance-ticket-triage"}


@app.get("/api/tickets")
def list_tickets() -> list[dict[str, Any]]:
    frame = pd.read_csv(DATA_PATH).fillna("")
    tickets = []
    for row in frame.to_dict(orient="records"):
        prediction = triage_ticket(row["description"], row["asset_type"])
        tickets.append(
            {
                "ticket_id": row["ticket_id"],
                "asset_type": row["asset_type"],
                "description": row["description"],
                "severity": prediction["severity"],
                "category": prediction["category"],
                "disposition": prediction["disposition"],
            }
        )
    return tickets


@app.post("/api/triage")
def run_triage(ticket: TicketRequest) -> dict[str, Any]:
    try:
        return triage_ticket(ticket.description, ticket.asset_type)
    except Exception as error:
        raise HTTPException(status_code=500, detail="Ticket triage failed.") from error


@app.get("/api/metrics")
def metrics() -> dict[str, Any]:
    return evaluate_examples()


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str) -> FileResponse:
        requested = (FRONTEND_DIST / path).resolve()
        if path and requested.is_relative_to(FRONTEND_DIST.resolve()) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/", include_in_schema=False)
    def frontend_not_built() -> dict[str, str]:
        return {
            "message": "Frontend build not found. Run the Vite development server from frontend/.",
            "api_docs": "/docs",
        }