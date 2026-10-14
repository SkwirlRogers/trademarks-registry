# NuttNeptune Trademark Registry

Official trademark registry for NuttNeptune products (tools, kits, packages, subscriptions, platforms).

## Structure

- `registry.json` — Main registry (trademarks, suites, licenses, registrations)
- `trademark_generator.py` — CLI for generation, search, registration
- `github_storage.py` — GitHub-backed storage module
- `run_tools.sh` — Unified runner script

## Usage

```bash
export GITHUB_TOKEN=ghp_xxx
./run_tools.sh trademark-suite "SuperTool" --type tool
./run_tools.sh trademark-search "NuttNeptune SuperTool"
./run_tools.sh github-sync
```

## Product Types

| Type | USPTO Classes | Description |
|------|---------------|-------------|
| Tool | 9, 42 | Computer software for automation and productivity |
| Kit | 9, 16, 42 | Downloadable software kits and templates |
| Package | 9, 42 | Bundled software packages and suites |
| Subscription | 9, 35, 42 | SaaS subscription services |
| Platform | 9, 35, 42, 45 | Platform as a service (PaaS) |

## Trademark Statuses

- `idea` — Concept phase
- `searching` — USPTO/domain/social checks in progress
- `filed` — Application submitted
- `published` — Published for opposition
- `registered` — Registered (®)
- `abandoned` — Abandoned
- `opposed` — Opposition filed