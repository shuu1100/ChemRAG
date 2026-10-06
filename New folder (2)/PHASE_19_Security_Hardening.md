# Phase 19 — Security Hardening

## Goal
Harden document processing, APIs, agent execution, and tenant boundaries.

## Prompt 19.1 — Document Security
Treat uploads as hostile. Implement MIME validation, size limits, malformed PDF handling, sandboxed processing, safe temporary directories, path traversal protection, resource limits, and timeouts.

## Prompt 19.2 — Prompt Injection Defense
Treat retrieved documents as untrusted evidence, not instructions. Implement document/content boundaries and test adversarial PDFs containing instructions such as “ignore previous instructions.” Ensure retrieved content cannot change system policy.

## Prompt 19.3 — API Security
Implement authentication-ready architecture, authorization, rate limiting, CORS restrictions, security headers, request limits, secret protection, tenant isolation, and audit logs. Never return stack traces in production.

## Exit Criteria
- Security tests pass.
- Malicious documents cannot execute arbitrary code.
- Prompt injection cannot bypass tool/safety policy.
