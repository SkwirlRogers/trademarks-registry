#!/bin/bash
# NuttNeptune Tool Runner

set -e

GITHUB_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN}}"
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN or GH_TOKEN env var required"
    exit 1
fi

export GITHUB_TOKEN

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<EOF
NuttNeptune Tool Runner

Usage: $0 <command> [options]

Commands:
  trademark-generate <name> [--count N] [--type TYPE]
      Generate trademark candidates for a product name
      Types: tool, kit, package, subscription, platform (default: tool)

  trademark-search <name>
      Search trademark availability (USPTO, domain, social)

  trademark-suite <product-name> [--type TYPE]
      Generate full trademark suite for a product

  github-sync
      Sync trademark registry with GitHub

  github-search <query>
      Search trademark registry

  github-license --product NAME [--type TYPE]
      Create a new license

  github-validate --license-id ID --machine FINGERPRINT
      Validate a license for a machine

  github-register
      Register trademark (manual - use trademark_generator.py)

  github-sync
      Sync and show registry stats

Examples:
  $0 trademark-generate "SuperTool" --count 20 --type tool
  $0 trademark-search "NuttNeptune SuperTool"
  $0 trademark-suite "SuperTool" --type tool
  $0 github-sync
  $0 github-search "NuttNeptune"
  $0 github-license --product "SuperTool" --type tool
  $0 github-validate --license-id ABC123 --machine "machine-fingerprint"
EOF
}

cd "$TOOL_DIR"

case "${1:-}" in
    trademark-generate)
        shift
        python3 trademark_generator.py generate "$@"
        ;;
    trademark-search)
        shift
        python3 trademark_generator.py search "$@"
        ;;
    trademark-suite)
        shift
        python3 trademark_generator.py suite "$@"
        ;;
    trademark-register)
        shift
        python3 trademark_generator.py register "$@"
        ;;
    github-sync)
        python3 github_storage.py sync
        ;;
    github-search)
        shift
        python3 github_storage.py search "$@"
        ;;
    github-license)
        shift
        python3 github_storage.py license "$@"
        ;;
    github-validate)
        shift
        python3 github_storage.py validate "$@"
        ;;
    github-register)
        python3 github_storage.py register "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac