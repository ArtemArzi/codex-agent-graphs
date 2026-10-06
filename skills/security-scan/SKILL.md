---
name: security-scan
description: Scan your Claude Code configuration (.claude/ directory) for security vulnerabilities, misconfigurations, and injection risks using AgentShield. Checks CLAUDE.md, settings.json, MCP servers, hooks, and agent definitions.
metadata:
  origin: ECC
---

# Security Scan Skill

Audit your Claude Code configuration for security issues using [AgentShield](https://github.com/affaan-m/agentshield).

## When to Activate

- Setting up a new Claude Code project
- After modifying `.claude/settings.json`, `CLAUDE.md`, or MCP configs
- Before committing configuration changes
- When onboarding to a new repository with existing Claude Code configs
- Periodic security hygiene checks

## What It Scans

| File | Checks |
|------|--------|
| `CLAUDE.md` | Hardcoded secrets, auto-run instructions, prompt injection patterns |
| `settings.json` | Overly permissive allow lists, missing deny lists, dangerous bypass flags |
| `mcp.json` | Risky MCP servers, hardcoded env secrets, npx supply chain risks |
| `hooks/` | Command injection via interpolation, data exfiltration, silent error suppression |
| `agents/*.md` | Unrestricted tool access, prompt injection surface, missing model specs |

## Prerequisites

Use an already installed, trusted AgentShield executable. Audit authorization
alone does not authorize package downloads, global installs or paid calls.
Check availability without `npx`, which can fetch and execute a missing package:

```bash
command -v ecc-agentshield
```

If absent, use a read-only source/configuration review and report the automated
scanner as unavailable. Installation is a separate authorized action; select a
reviewed version and verify its actual CLI before executing the examples below.
Do not enable tools, modify MCP bindings or weaken sandbox restrictions to scan.

## Usage

### Basic Scan

Run against the current project's `.claude/` directory:

```bash
# Scan current project
ecc-agentshield scan

# Scan a specific path
ecc-agentshield scan --path /path/to/.claude

# Scan with minimum severity filter
ecc-agentshield scan --min-severity medium
```

### Output Formats

```bash
# Terminal output (default) — colored report with grade
ecc-agentshield scan

# JSON — for CI/CD integration
ecc-agentshield scan --format json

# Markdown — for documentation
ecc-agentshield scan --format markdown

# HTML — self-contained dark-theme report
ecc-agentshield scan --format html > security-report.html
```

### Auto-Fix

Only when fixes are explicitly authorized, inspect the proposed changes first, back up affected files and validate the resulting permissions. A read-only scan never authorizes this command:

```bash
ecc-agentshield scan --fix
```

This will:
- Replace hardcoded secrets with environment variable references
- Tighten wildcard permissions to scoped alternatives
- Never modify manual-only suggestions

### Opus 4.6 Deep Analysis

Optional provider analysis sends configuration to an external service and may incur cost. Use only with explicit authority for the data transfer and spend; preserve host model routing. Otherwise keep review local:

```bash
# Requires ANTHROPIC_API_KEY
# Use an existing approved environment credential; never print its value.
ecc-agentshield scan --opus --stream
```

This runs:
1. **Attacker (Red Team)** — finds attack vectors
2. **Defender (Blue Team)** — recommends hardening
3. **Auditor (Final Verdict)** — synthesizes both perspectives

### Initialize Secure Config

Only for an explicitly requested setup, inspect existing configuration before scaffolding. Do not overwrite a working configuration during an audit:

```bash
ecc-agentshield init
```

Creates:
- `settings.json` with scoped permissions and deny list
- `CLAUDE.md` with security best practices
- `mcp.json` placeholder

### GitHub Action

Add to your CI pipeline:

```yaml
- uses: affaan-m/agentshield@v1
  with:
    path: '.'
    min-severity: 'medium'
    fail-on-findings: true
```

## Severity Levels

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 90-100 | Secure configuration |
| B | 75-89 | Minor issues |
| C | 60-74 | Needs attention |
| D | 40-59 | Significant risks |
| F | 0-39 | Critical vulnerabilities |

## Interpreting Results

### Critical Findings (fix immediately)
- Hardcoded API keys or tokens in config files
- `Bash(*)` in the allow list (unrestricted shell access)
- Command injection in hooks via `${file}` interpolation
- Shell-running MCP servers

### High Findings (fix before production)
- Auto-run instructions in CLAUDE.md (prompt injection vector)
- Missing deny lists in permissions
- Agents with unnecessary Bash access

### Medium Findings (recommended)
- Silent error suppression in hooks (`2>/dev/null`, `|| true`)
- Missing PreToolUse security hooks
- `npx -y` auto-install in MCP server configs

### Info Findings (awareness)
- Missing descriptions on MCP servers
- Prohibitive instructions correctly flagged as good practice

## Links

- **GitHub**: [github.com/affaan-m/agentshield](https://github.com/affaan-m/agentshield)
- **npm**: [npmjs.com/package/ecc-agentshield](https://www.npmjs.com/package/ecc-agentshield)
