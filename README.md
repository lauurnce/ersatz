# Ersatz

Replacement parts you can verify.

Ersatz checks form, fit and function replacements for discontinued LDO regulators and op-amps. Every value links to the provider response or datasheet page it came from. Results are not engineering sign-off: every replacement must be validated by an engineer.

Status: v0.1 in progress. The CLI works against Digi-Key with keys in .env.

## Usage

```
ersatz lookup MPN                          # provider record with its source
ersatz find MPN --top 5                    # ranked candidates with diffs
ersatz verify ORIGINAL CANDIDATE           # VERIFIED, PARTIAL, MISMATCH or NOT FOUND
pbpaste | ersatz check --original MPN      # check every part number in a chatbot answer
ersatz extract URL --category ldo          # cited values from one datasheet (calls a model)
```

Every command takes --json. Exit codes: 0 success or VERIFIED, 1 PARTIAL, 2 error, 3 MISMATCH, 4 NOT FOUND.

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
