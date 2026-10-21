"""Tests for the core data shapes. Each test names the rule it guards."""

import pytest

from pr_review.contracts import (
    AgentType,
    ContractError,
    Finding,
    Job,
    Review,
    Route,
    Severity,
    Span,
    Trigger,
    WorkKey,
    route,
)

KEY = WorkKey("acme/demo", 12, "a1b2c3d")


def finding(**over):
    d = dict(agent_type="security", severity="high", category="timing-attack",
             summary="Token compared with ==", file_path="auth/reset.py", line_start=40, line_end=40,
             confidence=0.9, rationale="== short-circuits; use hmac.compare_digest",
             evidence=[{"file_path": "auth/reset.py", "line_start": 38, "line_end": 42}])
    d.update(over)
    return Finding.from_dict(d)


# ---- Finding: untrusted input is parsed strictly, never guessed -----------------------------

def test_valid_finding_parses():
    f = finding()
    assert f.agent_type is AgentType.SECURITY and f.severity is Severity.HIGH
    assert f.location == Span("auth/reset.py", 40, 40)


@pytest.mark.parametrize("over", [
    {"confidence": 1.5}, {"confidence": -0.1}, {"confidence": "high"}, {"confidence": True},
    {"severity": "urgent"}, {"agent_type": "reviewer"},
    {"summary": ""}, {"rationale": "  "},
    {"line_start": 0}, {"line_start": 10, "line_end": 5}, {"line_start": "40"},
    {"file_path": "/etc/passwd"}, {"file_path": "../secrets.py"}, {"file_path": "C:/x.py"},
])
def test_malformed_finding_is_rejected(over):
    with pytest.raises(ContractError):
        finding(**over)


def test_missing_field_is_rejected():
    d = dict(agent_type="docs", severity="low", category="c", summary="s",
             file_path="a.py", line_start=1, line_end=1, rationale="r")   # no confidence
    with pytest.raises(ContractError, match="confidence"):
        Finding.from_dict(d)


def test_windows_separators_normalised():
    assert finding(file_path="auth\\reset.py", evidence=[]).location.file_path == "auth/reset.py"


# ---- Invariant every_posted_finding_is_grounded ---------------------------------------------

def test_grounded_when_location_and_evidence_inside_retrieved_context():
    assert finding().is_grounded([Span("auth/reset.py", 1, 80)])


def test_ungrounded_when_cited_file_never_retrieved():
    assert not finding().is_grounded([Span("auth/tokens.py", 1, 80)])


def test_ungrounded_when_lines_outside_retrieved_range():
    assert not finding().is_grounded([Span("auth/reset.py", 1, 39)])


def test_no_evidence_counts_as_ungrounded():
    assert not finding(evidence=[]).is_grounded([Span("auth/reset.py", 1, 80)])


# ---- WorkKey / Job: the duplicate-detection key (ingress F8/F9) -----------------------------

def test_work_key_string_and_sha_normalised():
    assert str(WorkKey("acme/demo", 12, "A1B2C3D")) == "acme/demo#12@a1b2c3d"


def test_same_work_same_key_regardless_of_delivery():
    j1 = Job(KEY, "delivery-1", Trigger.PULL_REQUEST, "2026-10-21T10:00:00Z")
    key2 = WorkKey("acme/demo", 12, "A1B2C3D")
    j2 = Job(key2, "delivery-2", Trigger.REVIEW_COMMAND, "2026-10-21T10:01:00Z")
    assert j1.work_key == j2.work_key


@pytest.mark.parametrize("args", [("acme", 12, "a1b2c3d"), ("acme/demo", 0, "a1b2c3d"),
                                  ("acme/demo", 12, "xyz"), ("acme/demo", True, "a1b2c3d")])
def test_bad_work_key_rejected(args):
    with pytest.raises(ContractError):
        WorkKey(*args)


# ---- route(): deterministic, never approves (invariant bot_never_approves_or_merges) ---------

def review(*fs, conf=0.95, partial=False):
    return Review(KEY, tuple(fs), conf, partial)


def test_no_threshold_means_everything_goes_to_a_human():
    assert route(review(finding(), conf=0.99), threshold=None) is Route.APPROVAL_QUEUE


def test_critical_always_escalates_even_when_confident():
    assert route(review(finding(severity="critical"), conf=0.99), threshold=0.5) is Route.ESCALATE


def test_partial_review_never_auto_posts():
    assert route(review(finding(), partial=True), threshold=0.5) is Route.APPROVAL_QUEUE


def test_threshold_splits_post_and_queue():
    assert route(review(finding(), conf=0.91), threshold=0.9) is Route.POST_COMMENT
    assert route(review(finding(), conf=0.89), threshold=0.9) is Route.APPROVAL_QUEUE


def test_there_is_no_approve_route():
    assert {r.value for r in Route} == {"post_comment", "approval_queue", "escalate"}
