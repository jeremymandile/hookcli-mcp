from hookcli_mcp.core.validator import HookValidator, ALLOWED_BINARIES


def test_blocks_rm_rf():
    v = HookValidator()
    r = v.validate("rm -rf /", {})
    assert not r.valid
    assert not r.security_pass
    assert any("Recursive root deletion" in e for e in r.errors)


def test_blocks_sudo():
    v = HookValidator()
    r = v.validate("sudo apt update", {})
    assert not r.valid
    assert not r.security_pass


def test_blocks_unlisted_binary():
    v = HookValidator()
    r = v.validate("nmap -sV 10.0.0.1", {})
    assert not r.valid
    assert not r.security_pass
    assert any("allow-list" in e for e in r.errors)


def test_renders_event_fields():
    v = HookValidator()
    r = v.validate("echo {{ event.id }}", {"id": "evt_123"})
    assert r.valid
    assert r.rendered_command == "echo evt_123"


def test_renders_secrets():
    v = HookValidator(secrets={"STRIPE_KEY": "sk_test_abc"})
    r = v.validate("curl https://api.stripe.com -H 'Auth: {{ secret('STRIPE_KEY') }}'", {})
    assert r.valid
    assert "sk_test_abc" in (r.rendered_command or "")


def test_warns_on_unresolved_secret():
    v = HookValidator(secrets={})
    r = v.validate("curl https://api.example.com -H 'Auth: {{ secret('MISSING_KEY') }}'", {})
    assert any("UNRESOLVED" in w for w in r.warnings)


def test_schema_mismatch():
    schema = {"type": "object", "properties": {"amount": {"type": "integer"}}, "required": ["amount"]}
    v = HookValidator(schema=schema)
    r = v.validate("echo ok", {"amount": "not-a-number"})
    assert not r.valid
    assert any("schema" in e.lower() for e in r.errors)


def test_allowed_binaries_set():
    assert "echo" in ALLOWED_BINARIES
    assert "sh" in ALLOWED_BINARIES
    assert "curl" in ALLOWED_BINARIES
    assert "nmap" not in ALLOWED_BINARIES
    assert "nc" not in ALLOWED_BINARIES
