from hookcli_mcp.core.validator import HookValidator


def test_blocks_rm_rf():
    v = HookValidator()
    r = v.validate("rm -rf /", {})
    assert not r.valid
    assert not r.security_pass


def test_blocks_sudo():
    v = HookValidator()
    r = v.validate("sudo rm -f /etc/hosts", {})
    assert not r.valid


def test_renders_event_fields():
    v = HookValidator()
    r = v.validate("echo {{ event.id }}", {"id": "evt_123"})
    assert r.valid
    assert r.rendered_command == "echo evt_123"


def test_renders_secrets():
    v = HookValidator(secrets={"STRIPE_KEY": "sk_test_abc"})
    r = v.validate("curl -H 'Auth: {{ secret.STRIPE_KEY }}'", {})
    assert r.valid
    assert "sk_test_abc" in (r.rendered_command or "")


def test_schema_mismatch():
    schema = {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}
    v = HookValidator(schema=schema)
    r = v.validate("echo ok", {"amount": "not-a-number"})
    assert not r.valid
    assert any("schema" in e.lower() for e in r.errors)
