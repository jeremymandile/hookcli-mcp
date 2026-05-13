import pytest
from hookcli_mcp.core.validator import HookValidator


def test_validator_blocks_rm_rf():
    validator = HookValidator()
    report = validator.validate("rm -rf /", {})
    assert not report.valid
    assert not report.security_pass
    assert any("Recursive root deletion" in e for e in report.errors)


def test_validator_blocks_sudo():
    validator = HookValidator()
    report = validator.validate("sudo apt update", {})
    assert not report.valid
    assert not report.security_pass


def test_validator_renders_template():
    validator = HookValidator(secrets={"API_KEY": "secret123"})
    report = validator.validate("echo {{ secret.API_KEY }}", {})
    assert report.valid
    assert "secret123" in (report.rendered_command or "")


def test_validator_safe_command():
    validator = HookValidator()
    report = validator.validate("echo 'hello world'", {})
    assert report.valid
    assert report.security_pass


@pytest.mark.asyncio
async def test_validation_sandbox_no_network():
    """Sandbox must have no network egress."""
    from hookcli_mcp.sandbox.validate import run_validation_sandbox
    result = await run_validation_sandbox("curl -s --max-time 2 http://example.com || echo BLOCKED", timeout=10)
    # Either curl is missing or network is blocked; command should not succeed with real data
    assert result["network_allowed"] is False
