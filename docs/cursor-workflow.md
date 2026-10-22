# Cursor agent workflow

This phase connects the repository's two local MCP servers to Cursor and gives
the agent one explicit, versioned workflow for catalog synchronization.

## Prerequisites

The reference setup is Windows with a project virtual environment at `.venv`.
From the repository root, create or refresh it with:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install -e . --no-deps
```

The second command installs pinned third-party packages. The third installs this
repository in editable mode without asking pip to resolve different dependency
versions.

## Project MCP configuration

`.cursor/mcp.json` declares `metrics-mcp` and `env-mcp` as stdio servers. Cursor
expands `${workspaceFolder}`, so the committed configuration contains no user-
specific absolute path. Each server is started with the virtual environment's
Python and reads `${workspaceFolder}/dataset`.

After opening the repository folder in Cursor:

1. Reload the Cursor window so it discovers the newly committed project files.
2. Open **Cursor Settings > Tools & MCP** (called **Customize > MCPs** in some
   Cursor versions).
3. Approve and enable `metrics-mcp` and `env-mcp` if prompted.
4. Confirm that both servers are connected and expose their tools/resources.
5. If startup fails, open the Output panel with `Ctrl+Shift+U` and select
   **MCP Logs**. First verify that `.venv\Scripts\python.exe` exists and that the
   dependencies above were installed.

MCP tools require approval by default unless the user's Cursor execution policy
allows them. This repository does not commit a personal auto-approval policy.

## Running the Skill

Start a new Cursor Agent chat in this repository and invoke:

```text
/sync-catalog
```

If slash completion does not show it, explicitly attach the Skill from
`.cursor/skills/sync-catalog/SKILL.md`. The Skill reads the declarative rules,
collects evidence from both MCP servers, edits only the catalog, and calls the
read-only checker. It may make no more than three checker attempts.

The Skill deliberately forbids `catalog-check --write`. Write mode is a local
mechanical recovery tool, not evidence that an AI agent correctly composed MCP
facts and policy. The agent also leaves commit, push, and merge decisions to a
human.

## Expected clean-run result

When the committed catalog already matches the pinned snapshot, the checker
returns `valid: true` and the catalog diff remains empty. A later evaluation
phase will inject controlled faults, run the same Skill, and record repair
outcomes and guardrail violations.
