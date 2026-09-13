from screenshot_app.analysis import DeterministicAnalyzer


def test_analysis_preserves_ocr_evidence_and_provenance():
    result = DeterministicAnalyzer().analyze(source_id="sha256:abc", ocr_text="Spotify playlist")
    assert result.status == "completed"
    assert result.category == "music"
    assert result.evidence[0].text == "Spotify playlist"
    assert result.evidence[0].provenance == "ocr:sha256:abc"
    assert result.model
    assert result.processed_at.endswith("+00:00")


def test_sensitive_text_is_never_completed_automatically():
    result = DeterministicAnalyzer().analyze(source_id="sha256:secret", ocr_text="private passcode")
    assert result.status == "review_required"
    assert result.sensitive is True
    assert result.review_required is True


def test_empty_or_ambiguous_input_requires_review():
    result = DeterministicAnalyzer().analyze(source_id="sha256:empty", ocr_text="")
    assert result.status == "review_required"
    assert result.category is None
