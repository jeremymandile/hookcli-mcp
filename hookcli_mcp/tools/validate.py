from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from hookcli_mcp.core.validator import HookValidator
from hookcli_mcp.sandbox.validate import run_validation_sandbox

router = APIRouter(tags=["validate"])


class ValidateRequest(BaseModel):
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None
    secrets: Dict[str, str] = Field(default_factory=dict)
    allow_network: bool = False
    timeout_sec: int = Field(default=30, ge=1, le=120)


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    rendered_command: Optional[str]
    execution: Optional[Dict[str, Any]] = None
    security_pass: bool = True


@router.post("", response_model=ValidateResponse)
async def hook_validate(req: ValidateRequest) -> ValidateResponse:
    validator = HookValidator(schema=req.schema, secrets=req.secrets)
    report = validator.validate(req.command, req.payload)

    errors = report.errors.copy()
    warnings = report.warnings.copy()
    valid = report.valid
    execution = None

    if valid and report.rendered_command:
        execution = await run_validation_sandbox(report.rendered_command, req.timeout_sec)
        if not execution.get("success", False):
            valid = False
            errors.append(
                f"Dry-run failed (exit {execution.get('exit_code', -1)}): {execution.get('stderr', '')[:200]}"
            )

    return ValidateResponse(
        valid=valid,
        errors=errors,
        warnings=warnings,
        rendered_command=report.rendered_command,
        execution=execution,
        security_pass=report.security_pass,
    )
