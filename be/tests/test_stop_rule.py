"""Unit tests for stop_rule engine."""
import pytest
from datetime import datetime, timedelta
from app.engines.stop_rule import evaluate_stop_rule, StopInput, StopOutput, LoanStatus, EMI


@pytest.fixture
def policy():
    """Mock policy dict."""
    return {
        "stop_rule": {
            "missed_emis_threshold": 2,
            "consecutive_or_cumulative": "cumulative",
        }
    }


def test_stop_rule_no_missed_emis(policy):
    """No missed EMIs → loan is active."""
    emis = [
        EMI(due_date="2024-01-01", paid_date="2024-01-01", status="on_time"),
        EMI(due_date="2024-02-01", paid_date="2024-02-01", status="on_time"),
        EMI(due_date="2024-03-01", paid_date="2024-03-01", status="on_time"),
    ]
    input_data = StopInput(emis=emis)
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.ACTIVE
    assert result.missed_emi_count == 0
    assert result.action_open_review is False
    assert "active" in result.reasoning.lower()


def test_stop_rule_one_missed_emi(policy):
    """One missed EMI → amber warning."""
    emis = [
        EMI(due_date="2024-01-01", paid_date="2024-01-01", status="on_time"),
        EMI(due_date="2024-02-01", paid_date=None, status="missed"),
        EMI(due_date="2024-03-01", paid_date="2024-03-01", status="on_time"),
    ]
    input_data = StopInput(emis=emis)
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.AMBER
    assert result.missed_emi_count == 1
    assert result.action_open_review is False
    assert "warning" in result.reasoning.lower()
    assert "one more" in result.reasoning.lower()


def test_stop_rule_two_missed_emis_frozen(policy):
    """Two missed EMIs → loan frozen, review opened."""
    emis = [
        EMI(due_date="2024-01-01", paid_date="2024-01-01", status="on_time"),
        EMI(due_date="2024-02-01", paid_date=None, status="missed"),
        EMI(due_date="2024-03-01", paid_date=None, status="missed"),
    ]
    input_data = StopInput(emis=emis)
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.FROZEN
    assert result.missed_emi_count == 2
    assert result.action_open_review is True
    assert "frozen" in result.reasoning.lower()


def test_stop_rule_three_missed_emis_still_frozen(policy):
    """Three missed EMIs → still frozen (doesn't change after 2)."""
    emis = [
        EMI(due_date="2024-01-01", paid_date="2024-01-01", status="on_time"),
        EMI(due_date="2024-02-01", paid_date=None, status="missed"),
        EMI(due_date="2024-03-01", paid_date=None, status="missed"),
        EMI(due_date="2024-04-01", paid_date=None, status="missed"),
    ]
    input_data = StopInput(emis=emis)
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.FROZEN
    assert result.missed_emi_count == 3
    assert result.action_open_review is True


def test_stop_rule_mixed_on_time_and_missed(policy):
    """Mixed: some on-time, some missed → count only missed."""
    emis = [
        EMI(due_date="2024-01-01", paid_date="2024-01-01", status="on_time"),
        EMI(due_date="2024-02-01", paid_date="2024-02-15", status="late"),  # Late is not missed
        EMI(due_date="2024-03-01", paid_date=None, status="missed"),
        EMI(due_date="2024-04-01", paid_date="2024-04-01", status="on_time"),
        EMI(due_date="2024-05-01", paid_date=None, status="missed"),
    ]
    input_data = StopInput(emis=emis)
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.FROZEN
    assert result.missed_emi_count == 2


def test_stop_rule_empty_emi_list(policy):
    """Empty EMI list → loan is active (no missed yet)."""
    input_data = StopInput(emis=[])
    result = evaluate_stop_rule(input_data, policy)
    
    assert result.status == LoanStatus.ACTIVE
    assert result.missed_emi_count == 0
