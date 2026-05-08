from __future__ import annotations

from syncguard.extractor.extractor import InvariantExtractor


def test_extracts_type_contract(sample_project) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    assert any(inv.invariant_type == "type_contract" and inv.evidence.get("field") == "user_id" for inv in invariants)


def test_extracts_response_shape(sample_project) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    assert any(inv.invariant_type == "data_shape" and inv.evidence.get("shape") == ["data", "links", "meta"] for inv in invariants)


def test_extracts_migration_behavior(sample_project) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    assert any(inv.invariant_type == "behavioral" and inv.scope == "migrations" for inv in invariants)


def test_min_confidence_filters(sample_project) -> None:
    assert InvariantExtractor(min_confidence=1.1).extract(sample_project) == []
