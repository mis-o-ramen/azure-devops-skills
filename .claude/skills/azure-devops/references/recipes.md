# Recipes and troubleshooting

Every command below is prefixed with `python3 scripts/ado.py`.

## WIQL

WIQL is SQL-like but restricted: no `JOIN`, no `SELECT *`, and the `SELECT` list decides which
fields come back. Reference names, not display names, go in the query.

Work items assigned to the current user and not closed:

```
wit query --wiql "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.AssignedTo] = @me
  AND [System.State] NOT IN ('Closed', 'Removed')
ORDER BY [System.ChangedDate] DESC"
```

Everything in the current sprint:

```
wit query --wiql "SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = @project
  AND [System.IterationPath] = @currentIteration
ORDER BY [System.Id]"
```

Children of one work item (a one-hop link query; the client extracts the target ids):

```
wit query --wiql "SELECT [System.Id] FROM WorkItemLinks
WHERE [Source].[System.Id] = 1234
  AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
MODE (MustContain)"
```

Useful macros: `@me`, `@project`, `@today`, `@currentIteration`. Date arithmetic uses
`@today - 7`.

Put long queries in a file and pass `--wiql @query.wiql` instead of quoting them inline.

## Creating a User Story with acceptance criteria

Generate the field reference first, then write the HTML fields with `--field-multiline`:

```
wit describe-type --type "User Story" --save

wit create --type "User Story" \
  --title "Bulk-export invoices as CSV" \
  --field-multiline "System.Description=@description.txt" \
  --field-multiline "Microsoft.VSTS.Common.AcceptanceCriteria=@criteria.txt" \
  --field "Microsoft.VSTS.Scheduling.StoryPoints=5" \
  --area "MyProject\\Billing" \
  --iteration "MyProject\\Sprint 42"
```

`--field-multiline` escapes `<`, `>` and `&` and turns newlines into `<br>`. Pass real HTML
through `--field` when you want markup preserved.

Field names vary by type. Frequently useful reference names on the stock Agile template:

| Field | Reference name | Types |
| --- | --- | --- |
| Description | `System.Description` | all |
| Acceptance Criteria | `Microsoft.VSTS.Common.AcceptanceCriteria` | User Story |
| Repro Steps | `Microsoft.VSTS.TCM.ReproSteps` | Bug |
| System Info | `Microsoft.VSTS.TCM.SystemInfo` | Bug |
| Story Points | `Microsoft.VSTS.Scheduling.StoryPoints` | User Story |
| Effort | `Microsoft.VSTS.Scheduling.Effort` | Product Backlog Item |
| Remaining Work | `Microsoft.VSTS.Scheduling.RemainingWork` | Task |
| Priority | `Microsoft.VSTS.Common.Priority` | most |
| Business Value | `Microsoft.VSTS.Common.BusinessValue` | Feature, Epic |

Treat this table as a hint for where to look, never as the answer. The generated file in
`references/fields/` is the authority for this server.

## Responding to pull request review comments

```
pr threads 812 --repo billing-api --unresolved-only
```

Each thread carries a `threadId`, the file path and line it is anchored to, and its comments.
Reply into the thread the reviewer opened rather than starting a new one:

```
pr comment 812 --repo billing-api --thread 7 --text "Fixed in the latest push."
```

## Triaging a failed build

```
build list --result failed --top 5
build logs 9271
```

`build logs` without flags prints each failed step with the errors the agent recorded. Only
when those are too vague:

```
build logs 9271 --fetch --tail 300
```

## Linking work to a pull request

```
pr create --repo billing-api --source feature/csv-export --target main \
  --title "Bulk CSV export" --description @pr-body.md --work-item 1234
```

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `ADO_ORG_URL is not set` | The collection URL is missing. It ends with the collection name, e.g. `/tfs/DefaultCollection`, not the server root. |
| HTTP 401, or an HTML sign-in page | PAT is wrong or expired, or basic-auth PATs are disabled on the server. |
| HTTP 403 | PAT is valid but lacks the scope. Work item writes need *Work Items (read & write)*; pull request comments need *Code (read & write)*; build logs need *Build (read)*. |
| HTTP 404 on a valid-looking path | Wrong project or collection, or the route needs a preview api-version. Retry with `request … --api-version-override 7.0-preview.3`. |
| HTTP 400 naming an unknown field | The reference name does not exist on that work item type. Regenerate with `wit describe-type --save`. |
| `CERTIFICATE_VERIFY_FAILED` | Point `ADO_CA_BUNDLE` at the internal CA bundle. `ADO_TLS_INSECURE=1` disables verification and is a last resort. |
| Connection refused or a timeout to an internal host | `HTTPS_PROXY` is being applied to the internal server. Add the host to `NO_PROXY`. |
| A comment posted but does not appear as a discussion entry | `wit comment` writes `System.History`, which renders in the work item's Discussion. Check the correct work item id. |

## API version

Azure DevOps Server 2022 serves `api-version=7.0`, which every command uses by default. Work
item comments are only reachable at `7.0-preview.3`; `wit comments` already accounts for that.
Endpoints documented for `7.1` or later are not available on this server — use `7.0` or the
matching preview.
