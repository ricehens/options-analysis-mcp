# Security Policy

## Scope and boundary

This project is a local, single-user, read-only analysis service. It has no
order, transfer, or account-mutation contract. A change that adds such a
capability requires a separate threat model and must not be disguised as a data
provider extension.

## Secrets

- Keep client IDs, application secrets, OAuth callbacks/codes, tokens, account
  identifiers, and captured private responses out of Git, chat, MCP arguments,
  screenshots, logs, and fixtures.
- Put Schwab application settings in the ignored local `.env` file.
- Tokens default outside the repository and are atomically written with user-
  only permissions on POSIX systems.
- Do not put secrets in MCP-host JSON. Start the server with the repository as
  its working directory so it can read the ignored `.env` locally.
- Revoke the developer application and delete the local token file if exposure
  is suspected. Create a new application secret before reauthorizing.

## Network behavior

The Schwab gateway exposes GET only, does not follow redirects, applies a
timeout, bounds attempts and response bytes, retries only transient reads, and
never includes upstream response bodies in errors. OAuth token POSTs exist only
inside the authorization component.

The browser never receives Schwab client credentials or OAuth tokens. Its
FastAPI facade binds to `127.0.0.1`, is read-only, and allows development CORS
requests only from `127.0.0.1:5173` and `localhost:5173`. Do not expose the API
on a LAN or public interface without adding TLS, authentication, origin/host
validation, and a separate deployment threat model.

The production UI is served from the same loopback origin as the API. Responses
set a restrictive same-origin content security policy, deny framing, disable
MIME sniffing, and omit referrer data. These headers reduce browser attack
surface but do not turn the local single-user service into a safe hosted app.

Watchlist symbols are stored in a separate SQLite state file outside the source
repository. Its parent directory is created user-only and its file mode is
forced to user read/write on POSIX systems. The state database contains no
Schwab tokens and must never become a general credential store.

## Reporting a vulnerability

Report security concerns privately to the repository owner. Do not open a
public issue containing a credential, token, callback URL, account number,
private response, or exploit payload. Include only synthetic reproduction data.
