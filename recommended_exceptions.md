# Recommended Cortex XDR/XSIAM Exceptions for Claude Code Generated Tools

Recommended legacy exception rules for environments running tools built and operated by Claude Code. Scoped to macOS and Linux only.

---

## Claude Code Runtime

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Claude Code CLI | macOS | `/Users/*/.claude/*` | 2 | Claude Code config, worktrees, session data |
| Claude Code CLI | Linux | `/home/*/.claude/*` | 2 | Claude Code config, worktrees, session data |
| Claude Code Binary (npm global) | macOS | `/Users/*/lib/node_modules/@anthropic-ai/claude-code/*` | 2 | npm global install path |
| Claude Code Binary (npm global) | Linux | `/usr/lib/node_modules/@anthropic-ai/claude-code/*` | 2 | npm global install path |
| Claude Code Standalone | macOS | `/usr/local/bin/claude` | 2 | Standalone binary |
| Claude Code Standalone | Linux | `/usr/local/bin/claude` | 2 | Standalone binary |

## Node.js Runtime

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Node.js Runtime | macOS | `/usr/local/bin/node;/usr/local/lib/node_modules/*` | 2 | Required by Claude Code CLI |
| Node.js Runtime | Linux | `/usr/bin/node;/usr/lib/node_modules/*` | 2 | Required by Claude Code CLI |

## Git Operations

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Git | macOS | `/usr/bin/git;/usr/local/bin/git;/Library/Developer/CommandLineTools/usr/bin/git` | 2 | Used by Claude Code for worktrees and version control |
| Git | Linux | `/usr/bin/git;/usr/lib/git-core/*` | 2 | Used by Claude Code for worktrees and version control |

## MCP Servers

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| MCP Server Processes | macOS | `/Users/*/.claude/mcp/*;/Users/*/*/mcp-server*` | 2 | MCP server binaries and configs |
| MCP Server Processes | Linux | `/home/*/.claude/mcp/*;/home/*/*/mcp-server*` | 2 | MCP server binaries and configs |
| npx MCP Servers | macOS | `/Users/*/.npm/_npx/*` | 2 | npx-launched MCP servers |
| npx MCP Servers | Linux | `/home/*/.npm/_npx/*` | 2 | npx-launched MCP servers |

---

## Deployment Notes

- **Module 2** = Malware Protection (most common for path-based folder allow-listing)
- Use `get-modules` to confirm available modules on your tenant before uploading
- Scope rules to `PROFILE` with specific profile IDs rather than `TENANT` when possible
- Review and narrow wildcard paths for production environments
- These are recommendations — audit against your organization's security policy before applying

## Quick Start

To convert these into a CSV for bulk upload, use the column format from `exceptions.csv.example`:

```
NAME,DESCRIPTION,PLATFORM,PATHS,MODULES,SCOPE,PROFILE_IDS,STATUS
Claude Code CLI,Claude Code config and session data,AGENT_OS_MACOS,/Users/*/.claude/*,2,TENANT,,ENABLED
```

Then upload:

```bash
python3 bulk_exceptions.py upload exceptions.csv --validate
```
