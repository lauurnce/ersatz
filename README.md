# Ersatz

Replacement parts you can verify.

Ersatz checks form, fit and function replacements for discontinued LDO regulators and op-amps. Every value links to the provider response or datasheet page it came from. Results are not engineering sign-off: every replacement must be validated by an engineer.

Status: scaffold only. No lookup or verify feature works yet.

## Development

Requirements: uv, Python 3.12, Node 24 and pnpm.

```
make setup      # install Python and web dependencies and the git hooks
make all        # lint, typecheck, Python tests and web tests
make api-dev    # API on http://localhost:8000/health
make web-dev    # web app on http://localhost:3000
uv run ersatz version
```

Copy .env.example to .env for provider and model keys. No key is needed to run the tests.
