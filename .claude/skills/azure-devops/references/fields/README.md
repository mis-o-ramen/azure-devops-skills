# Generated field references

`wit describe-type --type "<type>" --save` writes `<project>.<type>.md` here: a table of
every field on that work item type with its display name, reference name, data type, required
flag and allowed values, plus the type's valid states.

These files are server-specific. On-premises process templates are routinely customised, so
what one Azure DevOps Server reports is not what another reports. Commit them if the team
shares a single server; regenerate them after any process-template change.

A write that fails with HTTP 400 naming an unknown field means the file is stale.
