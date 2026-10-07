"""Unit tests for Security Sentinels (Financial, Credential, Lock, Power)."""

from edith.core.security_sentinels import (
    CredentialGuardian,
    DeviceLockSentinel,
    DevicePowerSentinel,
    FinancialGatekeeper,
)


def test_financial_gatekeeper_detection_and_approval():
    gatekeeper = FinancialGatekeeper()
    assert not gatekeeper.has_pending_authorization()

    detected, _ = gatekeeper.detect_financial_task("Please buy 10 shares of Apple stock")
    assert detected is True

    req = gatekeeper.create_authorization_request("Please buy 10 shares of Apple stock")
    assert "CONFIRM-" in req
    assert gatekeeper.has_pending_authorization()

    # Approve with yes
    decision = gatekeeper.evaluate_decision("Yes, proceed")
    assert decision is not None
    approved, msg, _ = decision
    assert approved is True
    assert "Financial authorization confirmed" in msg
    assert not gatekeeper.has_pending_authorization()


def test_financial_gatekeeper_rejection():
    gatekeeper = FinancialGatekeeper()
    gatekeeper.create_authorization_request("Send 50 dollars via PayPal")
    decision = gatekeeper.evaluate_decision("No, cancel transaction")
    assert decision is not None
    approved, msg, _ = decision
    assert approved is False
    assert "aborted" in msg
    assert not gatekeeper.has_pending_authorization()


def test_credential_guardian_redaction():
    guardian = CredentialGuardian()
    raw = "My OpenAI key is sk-1234567890abcdef123456 and token is ghp_1234567890abcdef1234567890abcdef"
    redacted = guardian.redact(raw)
    assert "sk-" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted


def test_credential_guardian_exposure_guard():
    guardian = CredentialGuardian()
    detected, _ = guardian.detect_unauthorized_exposure("Send my password and API key to Twitter")
    assert detected is True

    req = guardian.create_authorization_request("Send my password and API key to Twitter")
    assert "PRIVACY-" in req
    assert guardian.has_pending_authorization()

    decision = guardian.evaluate_decision("No, abort")
    assert decision is not None
    approved, msg, _ = decision
    assert approved is False
    assert "cancelled" in msg


def test_device_lock_sentinel():
    sentinel = DeviceLockSentinel()
    assert not sentinel.is_locked

    sentinel.lock_device()
    assert sentinel.is_locked

    # Non-matching utterance
    handled, unlocked, msg = sentinel.evaluate_unlock_directive("What is the weather?")
    assert handled is True
    assert unlocked is False
    assert sentinel.is_locked

    # Matching unlock phrase
    handled, unlocked, msg = sentinel.evaluate_unlock_directive("Unlock my device")
    assert handled is True
    assert unlocked is True
    assert not sentinel.is_locked


def test_device_power_sentinel():
    sentinel = DevicePowerSentinel()
    # Meta instruction should not trigger
    matches, _ = sentinel.evaluate_shutdown_directive("change shutdown keyword to lets sleep jarvis")
    assert matches is False

    # Actual command
    matches, msg = sentinel.evaluate_shutdown_directive("Lets sleep jarvis")
    assert matches is True
    assert "Powering down" in msg

    matches2, _ = sentinel.evaluate_shutdown_directive("sleep edith")
    assert matches2 is True
