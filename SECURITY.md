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

## Reporting a vulnerability

Report security concerns privately to the repository owner. Do not open a
public issue containing a credential, token, callback URL, account number,
private response, or exploit payload. Include only synthetic reproduction data.
