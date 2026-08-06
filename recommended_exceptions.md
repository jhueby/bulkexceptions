# Recommended Cortex XDR/XSIAM Exceptions for Claude Code Generated Tools

Recommended legacy exception rules for environments running tools built and operated by Claude Code. Organized by category with suggested module, scope, and platform.

---

## Claude Code Runtime

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Claude Code CLI | Windows | `C:\Users\*\.claude\*` | 2 | Claude Code config, worktrees, session data |
| Claude Code CLI | macOS | `/Users/*/.claude/*` | 2 | Claude Code config, worktrees, session data |
| Claude Code CLI | Linux | `/home/*/.claude/*` | 2 | Claude Code config, worktrees, session data |
| Claude Code Binary (npm global) | Windows | `C:\Users\*\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\*` | 2 | npm global install path |
| Claude Code Binary (npm global) | macOS | `/Users/*/lib/node_modules/@anthropic-ai/claude-code/*` | 2 | npm global install path |
| Claude Code Binary (npm global) | Linux | `/usr/lib/node_modules/@anthropic-ai/claude-code/*` | 2 | npm global install path |
| Claude Code Standalone | macOS | `/usr/local/bin/claude` | 2 | Standalone binary |
| Claude Code Standalone | Linux | `/usr/local/bin/claude` | 2 | Standalone binary |

## Node.js Runtime

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Node.js Runtime | Windows | `C:\Program Files\nodejs\*` | 2 | Node.js installation |
| Node.js Runtime | macOS | `/usr/local/bin/node;/usr/local/lib/node_modules/*` | 2 | Homebrew or manual install |
| Node.js Runtime (nvm) | macOS | `/Users/*/.nvm/versions/node/*` | 2 | nvm-managed installs |
| Node.js Runtime (nvm) | Linux | `/home/*/.nvm/versions/node/*` | 2 | nvm-managed installs |
| Node.js Runtime (fnm) | macOS | `/Users/*/Library/Application Support/fnm/node-versions/*` | 2 | fnm-managed installs |
| npm Cache | Windows | `C:\Users\*\AppData\Roaming\npm-cache\*;C:\Users\*\AppData\Roaming\npm\*` | 2 | npm global packages and cache |
| npm Cache | macOS | `/Users/*/.npm/*` | 2 | npm cache |
| npm Cache | Linux | `/home/*/.npm/*` | 2 | npm cache |

## Python Runtime

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Python Runtime | Windows | `C:\Python*\*;C:\Users\*\AppData\Local\Programs\Python\*` | 2 | System Python installs |
| Python Runtime | macOS | `/usr/bin/python3;/usr/local/bin/python3;/Library/Frameworks/Python.framework/*` | 2 | System and Homebrew Python |
| Python Runtime | Linux | `/usr/bin/python3;/usr/lib/python*` | 2 | System Python |
| Python venv/virtualenv | Windows | `C:\Users\*\*.venv\*;C:\Users\*\*\venv\*` | 2 | Virtual environments |
| Python venv/virtualenv | macOS | `/Users/*/.venv/*;/Users/*/*/venv/*` | 2 | Virtual environments |
| Python venv/virtualenv | Linux | `/home/*/.venv/*;/home/*/*/venv/*` | 2 | Virtual environments |
| pyenv | macOS | `/Users/*/.pyenv/*` | 2 | pyenv-managed installs |
| pyenv | Linux | `/home/*/.pyenv/*` | 2 | pyenv-managed installs |
| pip Cache | Windows | `C:\Users\*\AppData\Local\pip\*` | 2 | pip download cache |
| pip Cache | macOS | `/Users/*/Library/Caches/pip/*` | 2 | pip download cache |
| pip Cache | Linux | `/home/*/.cache/pip/*` | 2 | pip download cache |

## Git Operations

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Git | Windows | `C:\Program Files\Git\*;C:\Program Files (x86)\Git\*` | 2 | Git for Windows |
| Git | macOS | `/usr/bin/git;/usr/local/bin/git;/Library/Developer/CommandLineTools/usr/bin/git` | 2 | Xcode or Homebrew git |
| Git | Linux | `/usr/bin/git;/usr/lib/git-core/*` | 2 | System git |
| Git Hooks & Worktrees | Windows | `C:\Users\*\*\.git\*` | 2 | Git repo internals, hooks, worktrees |
| Git Hooks & Worktrees | macOS | `/Users/*/**/.git/*` | 2 | Git repo internals, hooks, worktrees |
| Git Hooks & Worktrees | Linux | `/home/*/**/.git/*` | 2 | Git repo internals, hooks, worktrees |

## Package Managers & Build Tools

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| Homebrew | macOS | `/usr/local/Cellar/*;/usr/local/bin/*;/opt/homebrew/*` | 2 | Homebrew packages and binaries |
| Cargo (Rust) | Windows | `C:\Users\*\.cargo\*` | 2 | Rust toolchain |
| Cargo (Rust) | macOS | `/Users/*/.cargo/*` | 2 | Rust toolchain |
| Cargo (Rust) | Linux | `/home/*/.cargo/*` | 2 | Rust toolchain |
| Go Toolchain | Windows | `C:\Users\*\go\*;C:\Program Files\Go\*` | 2 | Go modules and binaries |
| Go Toolchain | macOS | `/Users/*/go/*;/usr/local/go/*` | 2 | Go modules and binaries |
| Go Toolchain | Linux | `/home/*/go/*;/usr/local/go/*` | 2 | Go modules and binaries |

## Project Working Directories

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| node_modules | Windows | `C:\Users\*\*\node_modules\*` | 2 | npm/yarn/pnpm dependencies |
| node_modules | macOS | `/Users/*/*/node_modules/*` | 2 | npm/yarn/pnpm dependencies |
| node_modules | Linux | `/home/*/*/node_modules/*` | 2 | npm/yarn/pnpm dependencies |
| Build Output | Windows | `C:\Users\*\*\dist\*;C:\Users\*\*\build\*;C:\Users\*\*\.next\*` | 2 | Common build artifact directories |
| Build Output | macOS | `/Users/*/*/dist/*;/Users/*/*/build/*;/Users/*/*/.next/*` | 2 | Common build artifact directories |
| Build Output | Linux | `/home/*/*/dist/*;/home/*/*/build/*;/home/*/*/.next/*` | 2 | Common build artifact directories |
| Temp & Cache | Windows | `C:\Users\*\AppData\Local\Temp\*` | 2 | OS temp directory |
| Temp & Cache | macOS | `/private/var/folders/*/*/T/*;/private/tmp/*` | 2 | OS temp directories |
| Temp & Cache | Linux | `/tmp/*` | 2 | OS temp directory |

## MCP Servers

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| MCP Server Processes | macOS | `/Users/*/.claude/mcp/*;/Users/*/*/mcp-server*` | 2 | MCP server binaries and configs |
| MCP Server Processes | Linux | `/home/*/.claude/mcp/*;/home/*/*/mcp-server*` | 2 | MCP server binaries and configs |
| npx MCP Servers | macOS | `/Users/*/.npm/_npx/*` | 2 | npx-launched MCP servers |
| npx MCP Servers | Linux | `/home/*/.npm/_npx/*` | 2 | npx-launched MCP servers |

## IDEs and Editors (Claude Code Extensions)

| Name | Platform | Paths | Module | Notes |
|---|---|---|---|---|
| VS Code | Windows | `C:\Users\*\AppData\Local\Programs\Microsoft VS Code\*;C:\Users\*\.vscode\*` | 2 | VS Code and extensions |
| VS Code | macOS | `/Applications/Visual Studio Code.app/*;/Users/*/.vscode/*` | 2 | VS Code and extensions |
| JetBrains IDEs | Windows | `C:\Program Files\JetBrains\*;C:\Users\*\AppData\Local\JetBrains\*` | 2 | IntelliJ, PyCharm, WebStorm, etc. |
| JetBrains IDEs | macOS | `/Applications/IntelliJ*.app/*;/Applications/PyCharm*.app/*;/Applications/WebStorm*.app/*;/Users/*/Library/Application Support/JetBrains/*` | 2 | IntelliJ, PyCharm, WebStorm, etc. |

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
