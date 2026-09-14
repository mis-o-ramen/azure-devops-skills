# azure-devops-skills

An agent skill for operating an **on-premises Azure DevOps Server 2022** collection:
work items, pull requests, and build pipelines.

## Layout

```
.claude/skills/azure-devops/
├── SKILL.md                  # entry point loaded by the agent
├── scripts/ado.py            # REST client, Python 3 standard library only
└── references/
    ├── recipes.md            # WIQL patterns, common flows, troubleshooting
    └── fields/               # generated per-project, per-type field tables
```

## Works with both Claude and GitHub Copilot

One copy serves both. GitHub Copilot reads repository skills from `.github/skills`,
`.claude/skills` and `.agents/skills`, so the directory above is picked up as-is by Copilot
coding agent, Copilot CLI and Copilot agent mode in VS Code, as well as by Claude Code.

`SKILL.md` therefore stays tool-agnostic: it instructs the agent to run the bundled script and
never names a vendor-specific tool.

## Setup

```sh
export ADO_ORG_URL="https://tfs.example.com/tfs/DefaultCollection"
export ADO_PAT="<personal access token>"
export ADO_PROJECT="My Project"
export ADO_CA_BUNDLE="/etc/ssl/certs/internal-ca.pem"   # if the server uses a private CA
```

PAT scopes: *Work Items (read & write)*, *Code (read & write)* for pull requests,
*Build (read)* for pipeline triage.

Confirm connectivity:

```sh
python3 .claude/skills/azure-devops/scripts/ado.py wit types
```

## Scope

| Included | Excluded |
| --- | --- |
| Work items: WIQL search, read, create, update, comment, field/state discovery | Attachments, link hierarchies, custom process authoring |
| Pull requests: list, read, review threads, comment, create | Completing, abandoning, voting, policy overrides |
| Builds: definitions, runs, status, failed-step logs | Triggering runs, variable groups, approvals |
| Any other endpoint via `ado.py request` | Git operations — use the `git` CLI |

Irreversible actions are left out by design; the skill surfaces the URL so a human can act.
