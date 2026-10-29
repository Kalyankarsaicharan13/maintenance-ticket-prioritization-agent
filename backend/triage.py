"""Deterministic maintenance-ticket triage with example-based evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "maintenance_tickets.csv"


@dataclass(frozen=True)
class CategoryRule:
    category: str
    patterns: tuple[str, ...]
    root_cause: str
    next_action: str
    route_to: str
    baseline_severity: str


CATEGORY_RULES = (
    CategoryRule(
        "inverter_thermal",
        (r"\binverter\b", r"\b(overheat(?:ing)?|high temperature|thermal alarm|hot)\b"),
        "Possible inverter cooling or thermal-control fault.",
        "Check inverter alarms and cooling airflow; inspect filters and fans before resetting.",
        "Solar electrical maintenance",
        "high",
    ),
    CategoryRule(
        "gearbox_vibration",
        (r"\bgearbox\b", r"\b(vibrat\w*|abnormal noise|grinding)\b"),
        "Possible gearbox wear, lubrication issue, or developing mechanical fault.",
        "Review vibration trend and oil condition; arrange an engineering inspection before continued operation.",
        "Wind turbine mechanical team",
        "high",
    ),
    CategoryRule(
        "inspection_compliance",
        (r"\b(inspection|checklist|compliance|overdue)\b", r"\b(spillway|gate maintenance)\b"),
        "A required inspection or maintenance record may be incomplete or overdue.",
        "Confirm the inspection due date, assign a qualified inspector, and record completion evidence.",
        "Site operations and compliance",
        "medium",
    ),
    CategoryRule(
        "data_gap",
        (r"\b(scada|telemetry|sensor data|dashboard data)\b", r"\b(missing|data gap|not reporting|offline)\b"),
        "Possible communications, historian, or source-system data interruption.",
        "Check the source device, communications path, and historian ingestion; preserve the outage window.",
        "SCADA and controls support",
        "medium",
    ),
    CategoryRule(
        "pitch_system",
        (r"\b(blade pitch|pitch system|pitch error)\b", r"\b(blade|gust|pitch)\b"),
        "Possible pitch actuator, sensor, or control response fault after a wind event.",
        "Review turbine event logs and pitch-system alarms; inspect per the turbine safety procedure.",
        "Wind turbine controls team",
        "high",
    ),
    CategoryRule(
        "grid_curtailment",
        (r"\b(curtailment|grid instruction|dispatch instruction)\b", r"\b(generation dashboard|setpoint)\b"),
        "Possible mismatch between the grid dispatch instruction and operational reporting.",
        "Verify the active grid instruction against plant controls and generation reporting; escalate any dispatch mismatch.",
        "Grid operations and energy management",
        "medium",
    ),
)

CRITICAL_SIGNALS = re.compile(
    r"\b(fire|smoke|explosion|injur\w*|fatal\w*|electrocution|arc flash|structural collapse|"
    r"immediate danger|loss of containment)\b",
    re.IGNORECASE,
)
HIGH_SIGNALS = re.compile(
    r"\b(repeated(?:ly)? trip|high temperature alarm|blade pitch error|rapidly increasing)\b",
    re.IGNORECASE,
)
GEARBOX_CRITICAL = re.compile(
    r"\b(vibrat\w*|abnormal noise|grinding)\b.*\b(increas\w*|worsen\w*|abnormal|loud)\b|"
    r"\b(increas\w*|worsen\w*|abnormal|loud)\b.*\b(vibrat\w*|abnormal noise|grinding)\b",
    re.IGNORECASE,
)
NEGATED_BEFORE = re.compile(
    r"\b(?:no|without|denied|negative|ruled out|absence of|free of)\b"
    r"(?:[,\s]+(?!but\b|however\b|although\b|except\b)\w+){0,5}[,\s]*$|"
    r"\bnot\s+(?:(?:currently|presently|experiencing|showing|reporting|"
    r"observed|detected|present|active)\s*)$",
    re.IGNORECASE,
)
NEGATED_AFTER = re.compile(
    r"^\W*(?:\w+\W+){0,3}(?:not\s+(?:detected|observed|present|found|seen)|"
    r"ruled out|absent)\b",
    re.IGNORECASE,
)
RESOLVED_AFTER = re.compile(
    r"^\W*(?:\w+\W+){0,4}(?:cleared|resolved|inactive|deactivated|normal|"
    r"no longer active|no longer present|no longer occurring)\b",
    re.IGNORECASE,
)
CLAUSE_BOUNDARIES = re.compile(r"[.;!?\n]")


def load_examples() -> list[dict[str, str]]:
    frame = pd.read_csv(DATA_PATH).fillna("")
    return frame.to_dict(orient="records")


EXAMPLES = load_examples()
EXAMPLE_TEXTS = [f"{item['asset_type']} {item['description']}" for item in EXAMPLES]
VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
EXAMPLE_VECTORS = VECTORIZER.fit_transform(EXAMPLE_TEXTS)


def _is_negated(match: re.Match[str], text: str) -> bool:
    clause_start = 0
    for boundary in CLAUSE_BOUNDARIES.finditer(text, 0, match.start()):
        clause_start = boundary.end()
    before = text[max(clause_start, match.start() - 80) : match.start()]
    after = text[match.end() : match.end() + 80]
    return bool(
        NEGATED_BEFORE.search(before)
        or NEGATED_AFTER.search(after)
        or RESOLVED_AFTER.search(after)
    )


def _has_active_match(pattern: str | re.Pattern[str], text: str) -> bool:
    compiled = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, re.IGNORECASE)
    return any(not _is_negated(match, text) for match in compiled.finditer(text))


def _match_rule(text: str) -> CategoryRule | None:
    for rule in CATEGORY_RULES:
        if all(_has_active_match(pattern, text) for pattern in rule.patterns):
            return rule
    return None


def _severity(text: str, rule: CategoryRule | None) -> tuple[str, str]:
    if _has_active_match(CRITICAL_SIGNALS, text):
        return "critical", "An explicit immediate safety or containment signal was found."
    if rule and rule.category == "gearbox_vibration" and _has_active_match(GEARBOX_CRITICAL, text):
        return "critical", "Worsening gearbox vibration or abnormal noise warrants urgent inspection."
    if _has_active_match(HIGH_SIGNALS, text):
        return "high", "A repeated trip, thermal alarm, or pitch fault signal was found."
    if rule:
        return rule.baseline_severity, "Severity follows the category baseline; confirm against site impact and safety procedures."
    return "medium", "Insufficient context for automated severity; manual review is required."


def triage_ticket(description: str, asset_type: str = "unknown") -> dict[str, Any]:
    cleaned_description = " ".join(description.split())
    asset = " ".join(asset_type.split()) or "unknown"
    combined_text = f"{asset} {cleaned_description}".strip()
    rule = _match_rule(combined_text)
    severity, severity_reason = _severity(combined_text, rule)

    query_vector = VECTORIZER.transform([combined_text])
    similarities = cosine_similarity(query_vector, EXAMPLE_VECTORS).ravel()
    nearest_index = int(similarities.argmax())
    nearest = EXAMPLES[nearest_index]
    similarity = float(similarities[nearest_index])

    if rule:
        category = rule.category
        root_cause = rule.root_cause
        next_action = rule.next_action
        route_to = rule.route_to
        confidence = "high" if similarity >= 0.12 else "medium"
        disposition = "routed"
        matched_signals = [pattern for pattern in rule.patterns if _has_active_match(pattern, combined_text)]
    else:
        category = "manual_review"
        root_cause = "No supported fault pattern matched; the cause is undetermined."
        next_action = "Have the site team review the ticket and add asset, symptom, and operational-impact details."
        route_to = "Site maintenance coordinator"
        confidence = "low"
        disposition = "manual_review"
        matched_signals = []

    return {
        "asset_type": asset,
        "description": cleaned_description,
        "severity": severity,
        "severity_reason": severity_reason,
        "category": category,
        "probable_root_cause": root_cause,
        "next_action": next_action,
        "route_to": route_to,
        "confidence": confidence,
        "disposition": disposition,
        "agent_steps": [
            {"tool": "intake_normalization", "result": "Whitespace normalized; asset context included."},
            {"tool": "fault_pattern_rules", "result": f"Matched {category} using {len(matched_signals)} signal group(s)." if rule else "No supported category rule matched."},
            {"tool": "severity_policy", "result": f"Assigned {severity} severity. {severity_reason}"},
            {"tool": "example_retrieval", "result": f"Retrieved {nearest['ticket_id']} ({nearest['target_category']}) as the closest bundled example."},
            {"tool": "routing_policy", "result": f"{disposition.replace('_', ' ').capitalize()} to {route_to}."},
        ],
        "evidence": {
            "ticket_id": nearest["ticket_id"],
            "asset_type": nearest["asset_type"],
            "description": nearest["description"],
            "category": nearest["target_category"],
            "similarity": round(similarity, 3),
            "is_reference_example": True,
        },
        "limitations": [
            "This deterministic prototype is not a diagnosis or a substitute for site safety procedures.",
            "Similarity is retrieval relevance, not calibrated prediction confidence.",
            "Severity must be confirmed by an authorized operator using asset status and operational impact.",
        ],
    }


def evaluate_examples() -> dict[str, Any]:
    category_correct = 0
    severity_correct = 0
    results = []
    for example in EXAMPLES:
        prediction = triage_ticket(example["description"], example["asset_type"])
        category_match = prediction["category"] == example["target_category"]
        severity_match = prediction["severity"] == example["target_severity"]
        category_correct += int(category_match)
        severity_correct += int(severity_match)
        results.append(
            {
                "ticket_id": example["ticket_id"],
                "category_expected": example["target_category"],
                "category_predicted": prediction["category"],
                "category_match": category_match,
                "severity_expected": example["target_severity"],
                "severity_predicted": prediction["severity"],
                "severity_match": severity_match,
            }
        )
    count = len(EXAMPLES)
    return {
        "sample_count": count,
        "category_accuracy": category_correct / count if count else 0,
        "severity_accuracy": severity_correct / count if count else 0,
        "evaluation_type": "in-sample rule check; not an independent generalization estimate",
        "results": results,
    }