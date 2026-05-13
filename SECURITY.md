# Security Policy

## Reporting a Vulnerability

Email **security@hookcli.dev**. We respond within 48 hours. Do not open public issues for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Security Model

All CLI commands run in Docker containers with:
- Read-only root filesystem (`/tmp` writable)
- `seccomp` syscall whitelist
- `cap_drop=ALL`
- `network_mode="none"` during validation
- Memory and CPU limits

Commands are validated through `hook_validate` (template safety, regex guards, dry-run) before deployment. High-risk hooks require Slack/Teams approval. Secrets are never logged or exposed to AI clients.

## Best Practices

- Use `docker-socket-proxy` to limit Docker API exposure
- Rotate API keys and Slack tokens every 90 days
- Monitor audit logs for unexpected `hook_delete` or `secret_set` actions
- Review seccomp profiles when adding new CLI tools
