# Security Guidelines

All code generated for this web application must be security-focused. Treat security as a default, not an afterthought.

## Core Principles

- **Never trust input.** Validate, sanitize, and encode all data crossing a trust boundary (user input, URL params, headers, cookies, file uploads, third-party APIs).
- **Least privilege.** Code, services, database users, and API tokens get only the permissions they need.
- **Fail closed.** On error, deny access and log — never default to allow.
- **Defense in depth.** Don't rely on a single control. Validate at the edge, in business logic, and at the data layer.

## Input Handling & Output

- Validate all input with allowlists (type, length, format, range). Reject, don't sanitize, when possible.
- Use parameterized queries / prepared statements / ORMs for all database access. Never concatenate user input into SQL, shell commands, or template strings.
- Context-aware output encoding: HTML-escape for HTML, JS-escape for inline scripts, URL-encode for URLs.
- Never use `eval`, `Function()`, `dangerouslySetInnerHTML`, `innerHTML`, or equivalents with user-influenced data.
- Validate and constrain file uploads: type, size, extension, content; store outside the web root; generate new filenames.

## Authentication & Sessions

- Use a vetted library for auth — do not roll your own.
- Hash passwords with bcrypt, scrypt, or Argon2id. Never MD5/SHA-1/SHA-256 alone.
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax` or `Strict`, short expiry, rotate on login/privilege change.
- Implement rate limiting and lockout on auth endpoints.
- Use MFA where the threat model warrants it.

## Authorization

- Check authorization on every request, server-side, on every protected resource — including object-level checks (does _this user_ own _this record_?).
- Never rely on hidden fields, client-side checks, or obscure URLs as access control.
- Default deny: explicit allow rules only.

## Secrets & Configuration

- No secrets in source code, comments, logs, error messages, or client-side code. Ever.
- Load secrets from environment variables or a secrets manager. Add `.env` and equivalents to `.gitignore`.
- Rotate credentials; do not reuse them across environments.
- Different secrets for dev / staging / prod.

## Transport & Storage

- HTTPS everywhere. Set HSTS. Redirect HTTP → HTTPS.
- Encrypt sensitive data at rest. Use the platform's KMS or a vetted library — not custom crypto.
- Use modern, library-default algorithms (AES-GCM, ChaCha20-Poly1305). Never DES, RC4, ECB mode, or custom cipher constructions.

## HTTP Security Headers

Set on all responses:

- `Content-Security-Policy` (strict, no `unsafe-inline` / `unsafe-eval` unless justified)
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: DENY` or CSP `frame-ancestors`

## CSRF & CORS

- Use anti-CSRF tokens or `SameSite` cookies for state-changing requests.
- CORS: explicit allowlist of origins. Never `Access-Control-Allow-Origin: *` with credentials.

## Dependencies

- Pin versions. Use a lockfile.
- Prefer well-maintained libraries with active security response.
- Run dependency vulnerability scans (e.g. `npm audit`, `pip-audit`, Dependabot/Snyk equivalents) and treat criticals as blockers.
- Don't add a dependency to avoid writing five lines.

## Logging & Errors

- Log security events: auth attempts, authz failures, input validation failures, admin actions.
- Never log secrets, tokens, full PII, full payment data, or session IDs.
- Show generic error messages to users. Detailed errors and stack traces stay server-side.

## Things to Flag, Not Silently Do

When generating code, **stop and call out** if a request would require:

- Disabling TLS verification, CORS, CSP, or auth checks
- Storing or transmitting secrets in client code
- Building SQL/HTML/shell strings from user input
- Custom cryptography
- Bypassing an existing authorization check

Suggest the secure alternative instead.

## OWASP Top 10 Awareness

Generated code should not introduce: broken access control, cryptographic failures, injection, insecure design, security misconfiguration, vulnerable components, authentication failures, software/data integrity failures, logging failures, or SSRF. When a change touches one of these areas, note the consideration in comments or the response.