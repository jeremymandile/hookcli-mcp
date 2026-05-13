import re
import jinja2
import jsonschema
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    rendered_command: Optional[str] = None
    security_pass: bool = True


DANGEROUS_PATTERNS = [
    (r"\brm\s+-rf\s+(/\s*|\*\s*)", "Recursive root deletion detected"),
    (r"\bsudo\s+", "Privilege escalation (sudo) detected"),
    (r">\s*/etc/(passwd|shadow|hosts)\b", "Critical system file overwrite detected"),
    (r"\bchmod\s+777\s+/\b", "Insecure permissions on root detected"),
    (r"\bcurl.*-o\s+/(bin|sbin|usr/sbin)/", "Remote binary download to system path detected"),
]


class HookValidator:
    def __init__(self, schema: Optional[Dict[str, Any]] = None, secrets: Optional[Dict[str, str]] = None):
        self.schema = schema
        self.secrets = secrets or {}

    def validate(self, command: str, payload: Dict[str, Any]) -> ValidationReport:
        report = ValidationReport(valid=True)

        try:
            env = jinja2.Environment(loader=jinja2.BaseLoader(), autoescape=False, trim_blocks=True)
            template = env.from_string(command)
            report.rendered_command = template.render(event=payload, secret=self.secrets)
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

        for pattern, msg in DANGEROUS_PATTERNS:
            if re.search(pattern, report.rendered_command, re.IGNORECASE):
                report.valid = False
                report.security_pass = False
                report.errors.append(f"Security guard blocked: {msg}")
                return report

        if self.schema:
            try:
                jsonschema.validate(instance=payload, schema=self.schema)
            except jsonschema.exceptions.ValidationError as e:
                report.valid = False
                report.errors.append(f"Payload schema mismatch: {e.message}")
            except Exception as e:
                report.valid = False
                report.errors.append(f"Schema validation error: {e}")

        if "{{secret:}}" in command:
            report.warnings.append("Empty secret placeholder: {{secret:}} will resolve to empty string")
        if re.search(r"(password|token|key)\s*=\s*[\"'][^\"']{4,}[\"']", report.rendered_command or "", re.IGNORECASE):
            report.warnings.append("Potential hardcoded credential in rendered command")

        return report
