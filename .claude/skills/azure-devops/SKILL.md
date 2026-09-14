---
name: azure-devops
description: Work with an on-premises Azure DevOps Server 2022 collection over its REST API — search, read, create and update work items (including type-specific fields such as Acceptance Criteria), read and comment on pull requests, and triage failed build pipelines. Use whenever the user refers to work items, user stories, features, bugs, backlog items, sprints, pull requests, or builds on a self-hosted Azure DevOps / TFS server.
---

# Azure DevOps Server (on-premises)

All calls go through `scripts/ado.py`, a dependency-free Python 3 client
(`python3 scripts/ado.py …`; use `python` if `python3` is unavailable). Paths below are
relative to this skill's directory.

Git operations are out of scope — use the `git` CLI for clone, diff, branch and commit.
This skill covers only what the REST API alone can provide.

## Setup

Four environment variables drive everything:

| Variable | Required | Meaning |
| --- | --- | --- |
| `ADO_ORG_URL` | yes | Collection URL, e.g. `https://tfs.example.com/tfs/DefaultCollection` |
| `ADO_PAT` | yes | Personal access token |
| `ADO_PROJECT` | no | Default team project (`--project` overrides per call) |
| `ADO_CA_BUNDLE` | no | CA bundle path for a privately-signed server certificate |

Verify connectivity before anything else:

```
python3 scripts/ado.py wit types
```

A list of work item types means the URL, PAT and TLS trust are all correct. Anything else —
see "Troubleshooting" in `references/recipes.md`.

## Field discovery comes first

Work item fields differ per type and per project. `Acceptance Criteria` exists on User Story
but not on Bug or Task, and on-premises process templates are frequently customised, so the
field set on this server is not necessarily the stock Agile set.

Never guess a reference name. Before creating or updating a work item of a type you have not
handled yet in this session:

1. Check `references/fields/` for a `<project>.<type>.md` file and read it if present.
2. If absent or stale, generate it:
   ```
   python3 scripts/ado.py wit describe-type --type "User Story" --save
   ```
   This writes a table of display name, reference name, type, required flag and allowed
   values into `references/fields/`, plus the type's valid states.

Two rules fall out of that table:

- A field whose type is `html` (`System.Description`,
  `Microsoft.VSTS.Common.AcceptanceCriteria`, `Microsoft.VSTS.TCM.ReproSteps`) loses plain
  newlines. Write it with `--field-multiline`, which escapes the text and converts newlines
  to `<br>`. Use `--field` for every other type.
- `System.State` accepts only the states listed for that type. Do not assume
  `New/Active/Resolved/Closed`.

Cached files can go stale after a process-template change. Regenerate when a write fails with
HTTP 400 naming an unknown field.

## Work items

```
wit types                                 # types available in the project
wit describe-type --type "Bug" --save     # fields, states, allowed values
wit query --wiql "SELECT …"               # WIQL search, resolves ids to fields in one step
wit get 1234 5678 [--relations]           # fetch by id, all fields
wit create --type "User Story" --title …  # create
wit update 1234 --state Active            # update
wit comment 1234 --text "…"               # append a comment
wit comments 1234                         # read the discussion
```

`--field`, `--field-multiline`, `--title`, `--text`, `--description` and `--wiql` all accept
`@path` to read the value from a file — use it for anything long or multi-line rather than
fighting shell quoting.

`wit query` returns the columns named in the query's `SELECT` clause. Narrow the `SELECT`
rather than filtering afterwards; a broad query over a large backlog returns a lot of text.
See `references/recipes.md` for WIQL patterns.

## Pull requests

```
pr list --repo <repo> [--status active] [--target main]
pr get <id> --repo <repo>
pr threads <id> --repo <repo> [--unresolved-only]
pr comment <id> --repo <repo> --text "…" [--file path --line N] [--thread N]
pr create --repo <repo> --source <branch> --target <branch> --title "…"
```

`--thread` replies inside an existing thread; `--file`/`--line` opens a new thread anchored to
a line of the diff; neither opens a top-level thread. Branch names may omit `refs/heads/`.

Completing or abandoning a pull request, voting, and overriding branch policies are
deliberately absent. Those are irreversible from the agent's side — surface the pull request
URL and let a human act.

## Builds

```
build definitions [--name <filter>]
build list [--definition <id>] [--result failed] [--branch main]
build get <id>
build logs <id> [--fetch] [--tail 200] [--log <logId>]
```

`build logs <id>` alone lists the failed steps and their recorded error messages, which is
usually enough to diagnose a failure. Add `--fetch` only when the messages are not specific
enough; it downloads the last `--tail` lines of each failed step's log. Full logs are large —
raise `--tail` gradually rather than passing `--tail 0`.

Triggering runs is out of scope.

## Anything else

`scripts/ado.py request <METHOD> <path>` calls any endpoint directly, with auth, collection
URL, TLS and `api-version` already handled:

```
python3 scripts/ado.py request GET /wit/workitems/1234 --query '$expand=relations'
python3 scripts/ado.py request POST /wit/wiql --data @query.json
```

`path` is relative to `_apis`. Add `--collection-level` to drop the project segment, and
`--api-version-override` for routes that need a preview version.

## Reference

- `references/recipes.md` — WIQL patterns, common flows, troubleshooting
- `references/fields/` — generated per-project, per-type field tables
