import re
import shlex
from pathlib import Path
from typing import Dict, Any, Optional, List

import jinja2
import jsonschema
from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    rendered_command: Optional[str] = None
    security_pass: bool = True


# ── Regex fast pre-filter (catches obvious attacks before shell parsing) ───────
_DANGEROUS_RE = [
    (r"\brm\s+-rf\s+(/\s*|\*\s*)", "Recursive root deletion"),
    (r"\bsudo\s+", "Privilege escalation (sudo)"),
    (r">\s*/etc/(passwd|shadow|hosts)\b", "Critical system file overwrite"),
    (r"\bchmod\s+777\s+/\b", "Insecure permissions on root path"),
]

# ── Policy: allow-listed binaries that may run inside the sandbox ──────────────
# Extend this set as your hook library grows.
ALLOWED_BINARIES: frozenset[str] = frozenset({
    "sh", "bash", "echo", "printf", "cat", "grep", "sed", "awk",
    "jq", "curl", "wget", "python3", "python", "node",
    "sleep", "timeout", "date", "env", "true", "false",
    "hookcli",  # the project's own CLI
})


class HookValidator:
    def __init__(self, schema: Optional[Dict[str, Any]] = None, secrets: Optional[Dict[str, str]] = None):
        self.schema = schema
        self.secrets = secrets or {}

    def validate(self, command: str, payload: Dict[str, Any]) -> ValidationReport:
        report = ValidationReport()

        # ── Step 1: Template rendering ─────────────────────────────────────────
        try:
            env = jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=False, trim_blocks=True)
            template = env.from_string(command)
            report.rendered_command = template.render(
                event=payload,
                secret=lambda k: self.secrets.get(k, f"<UNRESOLVED:{k}>"),
            )
        except jinja2.TemplateSyntaxError as e:
            report.valid = False
            report.errors.append(f"Template syntax error: {e}")
            return report
        except jinja2.UndefinedError as e:
            report.valid = False
            report.errors.append(f"Template undefined variable: {e}")
            return report
        except Exception as e:
            report.valid = False
            report.errors.append(f"Template rendering failed: {e}")
            return report

        rendered = report.rendered_command or ""

        # ── Step 2: Regex fast pre-filter ──────────────────────────────────────
        for pattern, msg in _DANGEROUS_RE:
            if re.search(pattern, rendered, re.IGNORECASE):
                report.valid = False
                report.security_pass = False
                report.errors.append(f"Security guard (regex): {msg}")
                return report

        # ── Step 3: Allow-list policy via shell token parsing ──────────────────
        try:
            parts = shlex.split(rendered)
            if not parts:
                report.valid = False
                report.errors.append("Empty command after template rendering")
                return report

            # Extract the binary name (ignore path prefix — sandbox Alpine image)
            binary = Path(parts[0]).name
            if binary not in ALLOWED_BINARIES:
                report.valid = False
                report.security_pass = False
                report.errors.append(
                    f"Binary '{binary}' is not in the allow-list. "
                    f"Permitted: {', '.join(sorted(ALLOWED_BINARIES))}"
                )
                return report
        except ValueError as e:
            # shlex.split raises ValueError on unmatched quotes
            report.valid = False
            report.errors.append(f"Shell parse error (unmatched quotes?): {e}")
            return report

        # ── Step 4: Payload schema validation ──────────────────────────────────
        if self.schema:
            try:
                jsonschema.validate(instance=payload, schema=self.schema)
            except jsonschema.exceptions.ValidationError as e:
                report.valid = False
                report.errors.append(f"Payload schema mismatch: {e.message}")
            except Exception as e:
                report.valid = False
                report.errors.append(f"Schema validation error: {e}")

        # ── Step 5: Soft warnings ──────────────────────────────────────────────
        if "<UNRESOLVED:" in rendered:
            keys = re.findall(r"<UNRESOLVED:([^>]+)>", rendered)
            report.warnings.append(f"Unresolved secret(s): {', '.join(keys)}")
        if re.search(r"(password|token|key)\s*=\s*[\"'][^\"']{4,}[\"']", rendered, re.IGNORECASE):
            report.warnings.append("Potential hardcoded credential in rendered command")

        return report
