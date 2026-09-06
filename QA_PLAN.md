## BORI-8 QA plan and traceability

### Executable coverage

| Acceptance criterion | Test | Result | Scope |
|---|---|---|---|
| 1. Preserve source bytes, identity, hash, capture metadata and provenance | `test_batch_import_is_byte_preserving_and_provenance_stable` | Pass | Implemented ingestion API |
| 2. Detect duplicates without overwriting originals | `test_duplicate_retry_keeps_first_original_and_manifest_row` | Pass | Implemented ingestion API |
| 2. Handle missing/partial inputs safely | `test_missing_partial_input_fails_without_creating_manifest_or_original` | Pass | Missing-file boundary; retry queue not implemented |
| 3. Produce OCR and multimodal derivatives | — | Not implemented | No processing pipeline exists in this checkout |
| 4. Search OCR/category/entity/tag/date and link to originals | — | Not implemented | No metadata/search API exists |
| 5. Accept/edit/reject/merge classifications | — | Not implemented | No review persistence API exists |
| 6. Confidence, rationale, model/version and processing time | — | Not implemented | No AI-derived schema exists |
| 7. Isolate sensitive evidence | `test_sensitive_zone_is_not_an_ordinary_original_zone` | Pass | Storage zones exist; application access policy is still required |
| 8. Keyboard/screen-reader review UX | Existing `index.html` smoke review; no automated browser test | Partial | Import UI has labels/live alert; classification review UI absent |
| 9. Versioned derivatives and original preservation | — | Not implemented | Derivatives directory exists but no versioning writer exists |
| 10. Regression coverage | `tests/test_mvp_e2e.py`, `tests/test_ingest.py`, `tests/test_storage.py`, `app.test.js` | Pass locally | Coverage is limited to delivered components |

### Required follow-up before MVP go

Implement and test the missing OCR/vision processing, searchable metadata, human review actions, explainability fields, derivative versioning, retry/failure state model, and sensitive-access boundary. Add browser-level keyboard and screen-reader assertions for the review flow.

### Go/no-go

**NO-GO for the complete BORI-8 MVP integration.** The delivered ingestion/storage slice is regression-tested and passes, but criteria 3–6 and 9 are absent and criteria 7–8 are only partially covered. This is a product-scope blocker, not a test failure to be suppressed.
