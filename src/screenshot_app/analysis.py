"""Provider-neutral OCR and visual classification results.

The adapter deliberately keeps extracted evidence separate from generated
interpretation. A production provider can implement the same protocol later.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class Evidence:
    text: str
    kind: str = "ocr"
    confidence: float = 0.0
    provenance: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    status: str
    category: str | None
    confidence: float
    evidence: tuple[Evidence, ...]
    sensitive: bool
    review_required: bool
    model: str
    processed_at: str
    interpretation: dict[str, str] = field(default_factory=dict)


class Analyzer(Protocol):
    def analyze(self, *, source_id: str, ocr_text: str, visual_labels: list[str] | None = None) -> AnalysisResult: ...


class DeterministicAnalyzer:
    """Offline adapter for integration tests and the first vertical slice."""

    model = "mock-ocr-classifier/1"
    _sensitive_terms = ("password", "passcode", "carta di credito", "medical", "private")
    _categories = {
        "spotify": "music", "album": "music", "libro": "books", "book": "books",
        "event": "events", "concerto": "events", "map": "places", "mappa": "places",
    }

    def analyze(self, *, source_id: str, ocr_text: str, visual_labels: list[str] | None = None) -> AnalysisResult:
        text = ocr_text.strip()
        lowered = text.casefold()
        labels = [label.casefold() for label in (visual_labels or [])]
        sensitive = any(term in lowered for term in self._sensitive_terms)
        category = next((value for key, value in self._categories.items() if key in lowered or key in labels), None)
        confidence = 0.98 if text and category else (0.82 if text else 0.0)
        review = sensitive or confidence < 0.8
        evidence = (Evidence(text=text, confidence=0.98, provenance=f"ocr:{source_id}"),) if text else ()
        return AnalysisResult(
            status="review_required" if review else "completed",
            category=category,
            confidence=confidence,
            evidence=evidence,
            sensitive=sensitive,
            review_required=review,
            model=self.model,
            processed_at=datetime.now(timezone.utc).isoformat(),
            interpretation={"source_id": source_id},
        )
