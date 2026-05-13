# Changelog

All notable changes to **Hook CLI MCP** will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Added
- `hook_validate` dry-run executor with template rendering, schema validation, and regex security guards
- Human-in-the-loop approval state machine with Slack/Teams webhook verification
- OpenTelemetry auto-instrumentation for FastAPI and MCP tool calls
- Prometheus metrics endpoint with `hook_execution_duration_seconds` histogram
- GitHub Actions CI pipeline (lint, async tests, SAST, dependency scan, Docker build)
- `docker-compose.yml` with Redis, OTel Collector, Jaeger, and Prometheus

### Changed
- Python 3.12+ baseline for optimal `asyncio` and OpenTelemetry SDK support
- Replaced sync Docker SDK calls with `asyncio.to_thread()` + `asyncio.Queue` for SSE streaming
- MCP transport defaults to `stdio` with HTTP/SSE fallback

### Security
- Enforced `cap_drop=ALL`, read-only root FS, and seccomp whitelist for all sandbox containers
- HMAC-SHA256 signature verification for Slack webhook callbacks
- Masked secrets using `{{secret:NAME}}` placeholder resolution
