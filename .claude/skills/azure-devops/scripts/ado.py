#!/usr/bin/env python3
"""Azure DevOps Server 2022 (on-premises) REST client.

Covers the Tier 1 surface: work items, pull requests, build pipelines.
Git operations are intentionally out of scope -- use the `git` CLI for those.

Configuration comes from environment variables:

    ADO_ORG_URL      Collection URL, e.g. https://tfs.example.com/tfs/DefaultCollection
    ADO_PAT          Personal access token
    ADO_PROJECT      Default team project (optional; --project overrides)
    ADO_CA_BUNDLE    Path to a CA bundle for a privately-signed server certificate
    ADO_TLS_INSECURE Set to 1 to skip certificate verification (last resort)
    ADO_TIMEOUT      Request timeout in seconds (default 60)
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_API_VERSION = "7.0"
# Work item comments live behind a preview route even on ADS 2022.
COMMENTS_API_VERSION = "7.0-preview.3"


class AdoError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# HTTP client
# --------------------------------------------------------------------------


class Client:
    def __init__(self, base_url, pat, project=None, ca_bundle=None,
                 insecure=False, timeout=60, api_version=DEFAULT_API_VERSION):
        if not base_url:
            raise AdoError("ADO_ORG_URL is not set. Expected the collection URL, "
                           "e.g. https://tfs.example.com/tfs/DefaultCollection")
        if not pat:
            raise AdoError("ADO_PAT is not set.")
        self.base_url = base_url.rstrip("/")
        self.pat = pat
        self.project = project
        self.api_version = api_version
        self.timeout = timeout
        self._opener = self._build_opener(ca_bundle, insecure)

    def _build_opener(self, ca_bundle, insecure):
        if insecure:
            ctx = ssl._create_unverified_context()
            print("WARNING: TLS certificate verification is disabled "
                  "(ADO_TLS_INSECURE=1).", file=sys.stderr)
        elif ca_bundle:
            ctx = ssl.create_default_context(cafile=ca_bundle)
        else:
            ctx = ssl.create_default_context()
        return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    def _auth_header(self):
        token = base64.b64encode(f":{self.pat}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def build_url(self, path, project=None, collection_level=False, query=None,
                  api_version=None):
        """`path` is relative to `_apis`, e.g. '/wit/workitems/123'."""
        parts = [self.base_url]
        if not collection_level:
            proj = project if project is not None else self.project
            if proj:
                parts.append(urllib.parse.quote(proj, safe=""))
        parts.append("_apis")
        url = "/".join(parts) + "/" + path.lstrip("/")

        params = dict(query or {})
        version = api_version or self.api_version
        if version:
            params.setdefault("api-version", version)
        params = {k: v for k, v in params.items() if v is not None}
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
        return url

    def request(self, method, path, project=None, collection_level=False,
                query=None, body=None, content_type="application/json",
                api_version=None, accept="application/json", raw=False):
        url = self.build_url(path, project=project, collection_level=collection_level,
                             query=query, api_version=api_version)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method.upper())
        req.add_header("Authorization", self._auth_header())
        req.add_header("Accept", accept)
        if data is not None:
            req.add_header("Content-Type", content_type)

        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                payload = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise AdoError(self._describe_http_error(exc, url)) from None
        except urllib.error.URLError as exc:
            raise AdoError(
                f"Could not reach {url}: {exc.reason}\n"
                "Check ADO_ORG_URL, VPN/network reach, and whether HTTPS_PROXY is "
                "being applied to an internal host (set NO_PROXY for it)."
            ) from None

        if raw or "json" not in ctype:
            return payload.decode("utf-8", errors="replace")
        if not payload:
            return {}
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def _describe_http_error(exc, url):
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        message = detail
        try:
            parsed = json.loads(detail)
            message = parsed.get("message") or detail
        except Exception:
            pass
        # An HTML body means the collection URL landed on a sign-in page.
        if message.lstrip().lower().startswith("<!doctype html") or "<html" in message.lower()[:200]:
            message = "(server returned an HTML page instead of JSON)"

        hints = {
            401: "PAT is invalid, expired, or not sent. Confirm ADO_PAT and that "
                 "basic-auth PATs are enabled on the server.",
            203: "The server returned a sign-in page. The PAT was rejected.",
            403: "PAT is valid but lacks the required scope for this operation.",
            404: "Wrong collection/project/id, or the endpoint does not exist at "
                 "this api-version. ADS 2022 is pinned to 7.0; some routes need a "
                 "-preview suffix.",
            400: "The request body was rejected. For work items, check that every "
                 "field reference name exists on that work item type "
                 "(run `wit describe-type`).",
        }
        hint = hints.get(exc.code, "")
        out = f"HTTP {exc.code} {exc.reason} for {url}"
        if message.strip():
            out += f"\n  server: {message.strip()[:1000]}"
        if hint:
            out += f"\n  hint: {hint}"
        return out


def client_from_args(args):
    return Client(
        base_url=os.environ.get("ADO_ORG_URL", ""),
        pat=os.environ.get("ADO_PAT", ""),
        project=args.project or os.environ.get("ADO_PROJECT"),
        ca_bundle=os.environ.get("ADO_CA_BUNDLE"),
        insecure=os.environ.get("ADO_TLS_INSECURE") == "1",
        timeout=int(os.environ.get("ADO_TIMEOUT", "60")),
        api_version=args.api_version,
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def emit(obj):
    if isinstance(obj, str):
        sys.stdout.write(obj if obj.endswith("\n") else obj + "\n")
    else:
        print(json.dumps(obj, indent=2, ensure_ascii=False))


def read_value(value):
    """`@path` reads the value from a file; everything else is literal."""
    if value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as handle:
            return handle.read()
    return value


def split_assignment(raw):
    if "=" not in raw:
        raise AdoError(f"Expected NAME=VALUE, got: {raw!r}")
    name, value = raw.split("=", 1)
    return name.strip(), read_value(value)


def to_html(text):
    """Plain text -> HTML for fields whose type is `html`."""
    escaped = html.escape(text, quote=False)
    return "<br>".join(escaped.split("\n"))


def build_patch(field_args, multiline_args, shortcuts, require=True):
    ops = []
    seen = []
    for raw in field_args or []:
        name, value = split_assignment(raw)
        ops.append({"op": "add", "path": f"/fields/{name}", "value": value})
        seen.append(name)
    for raw in multiline_args or []:
        name, value = split_assignment(raw)
        ops.append({"op": "add", "path": f"/fields/{name}", "value": to_html(value)})
        seen.append(name)
    for name, value in shortcuts.items():
        if value is not None:
            ops.append({"op": "add", "path": f"/fields/{name}", "value": value})
            seen.append(name)
    if require and not ops:
        raise AdoError("No fields given. Use --field / --field-multiline or a shortcut "
                       "such as --title/--state/--assign.")
    return ops


PATCH_CONTENT_TYPE = "application/json-patch+json"

# Links are directed from the item being patched: a *parent* is the reverse end
# of a hierarchy link. Only the parent direction is exposed here; every other
# link type goes through `request`.
PARENT_REL = "System.LinkTypes.Hierarchy-Reverse"


def _work_item_url(client, work_item_id):
    """The collection-level API url, which is the form relation values take."""
    return f"{client.base_url}/_apis/wit/workItems/{work_item_id}"


def _add_parent_op(client, parent_id):
    return {"op": "add", "path": "/relations/-",
            "value": {"rel": PARENT_REL, "url": _work_item_url(client, parent_id)}}


def _relation_target_id(relation):
    tail = (relation.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _parent_ops(client, work_item_id, parent_id):
    """Ops that make `parent_id` the parent of an existing work item.

    A work item holds at most one parent, so re-parenting has to drop the old
    link in the same patch. `remove` addresses a relation by index, which is
    only valid for the revision we read, hence the `test` on /rev: a concurrent
    edit makes the patch fail instead of unlinking whatever moved into the slot.
    Returns no ops when the link is already there.
    """
    data = client.request("GET", f"/wit/workitems/{work_item_id}",
                          collection_level=True, query={"$expand": "relations"})
    for index, relation in enumerate(data.get("relations") or []):
        if relation.get("rel") != PARENT_REL:
            continue
        if _relation_target_id(relation) == parent_id:
            return []
        return [{"op": "test", "path": "/rev", "value": data.get("rev")},
                {"op": "remove", "path": f"/relations/{index}"},
                _add_parent_op(client, parent_id)]
    return [_add_parent_op(client, parent_id)]


# --------------------------------------------------------------------------
# work items
# --------------------------------------------------------------------------


def wit_types(client, args):
    data = client.request("GET", "/wit/workitemtypes")
    emit([
        {"name": t.get("name"), "referenceName": t.get("referenceName"),
         "description": t.get("description")}
        for t in data.get("value", [])
    ])


def _field_catalog(client):
    """Collection-level field catalog: referenceName -> {type, readOnly, ...}."""
    data = client.request("GET", "/wit/fields", collection_level=True)
    return {f.get("referenceName"): f for f in data.get("value", [])}


def _describe_type(client, wit_type, project):
    quoted = urllib.parse.quote(wit_type, safe="")
    fields = client.request(
        "GET", f"/wit/workitemtypes/{quoted}/fields",
        project=project, query={"$expand": "allowedValues"},
    ).get("value", [])
    catalog = _field_catalog(client)
    try:
        states = client.request(
            "GET", f"/wit/workitemtypes/{quoted}/states", project=project
        ).get("value", [])
    except AdoError:
        states = []

    rows = []
    for field in fields:
        ref = field.get("referenceName")
        meta = catalog.get(ref, {})
        rows.append({
            "displayName": field.get("name") or meta.get("name"),
            "referenceName": ref,
            "type": meta.get("type"),
            "required": bool(field.get("alwaysRequired")),
            "readOnly": bool(meta.get("readOnly")),
            "allowedValues": field.get("allowedValues") or [],
            "defaultValue": field.get("defaultValue"),
        })
    rows.sort(key=lambda r: (not r["required"], r["referenceName"] or ""))
    return rows, [s.get("name") for s in states]


def _describe_markdown(client, wit_type, project, rows, states):
    proj = project or client.project or "(default project)"
    lines = [
        f"# {wit_type} — field reference",
        "",
        f"- Server: `{client.base_url}`",
        f"- Project: `{proj}`",
        f"- api-version: `{client.api_version}`",
        "",
        "Generated by `scripts/ado.py wit describe-type --save`. "
        "Regenerate after any process-template change; this file can go stale.",
        "",
        "## States",
        "",
        ("`" + "` → `".join(states) + "`") if states else "_(not reported by the server)_",
        "",
        "## Fields",
        "",
        "`type: html` fields must be written with `--field-multiline` (or real HTML); "
        "plain newlines are lost otherwise.",
        "",
        "| Display name | Reference name | Type | Required | Read-only | Allowed values |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        allowed = ", ".join(str(v) for v in row["allowedValues"][:12])
        if len(row["allowedValues"]) > 12:
            allowed += ", …"
        lines.append(
            "| {display} | `{ref}` | {type} | {req} | {ro} | {allowed} |".format(
                display=row["displayName"] or "",
                ref=row["referenceName"] or "",
                type=row["type"] or "",
                req="yes" if row["required"] else "",
                ro="yes" if row["readOnly"] else "",
                allowed=allowed,
            )
        )
    return "\n".join(lines) + "\n"


def _cache_path(project, wit_type):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(os.path.dirname(here), "references", "fields")
    os.makedirs(root, exist_ok=True)

    def slug(text):
        return "".join(c if c.isalnum() else "-" for c in (text or "default")).strip("-").lower()

    return os.path.join(root, f"{slug(project)}.{slug(wit_type)}.md")


def wit_describe_type(client, args):
    project = args.project or client.project
    rows, states = _describe_type(client, args.type, project)
    if args.json:
        emit({"type": args.type, "project": project, "states": states, "fields": rows})
        return
    markdown = _describe_markdown(client, args.type, project, rows, states)
    if args.save:
        path = _cache_path(project, args.type)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        print(f"Wrote {path}")
    else:
        emit(markdown)


def _fetch_work_items(client, ids, fields=None, expand_all=False, relations=False):
    if not ids:
        return []
    results = []
    for chunk_start in range(0, len(ids), 200):
        chunk = ids[chunk_start:chunk_start + 200]
        body = {"ids": chunk}
        if fields:
            body["fields"] = fields
        else:
            # `fields` and `$expand` are mutually exclusive on this endpoint.
            body["$expand"] = "all"
        data = client.request("POST", "/wit/workitemsbatch", collection_level=True, body=body)
        results.extend(data.get("value", []))
    out = []
    for item in results:
        entry = {"id": item.get("id"), "rev": item.get("rev"), "fields": item.get("fields", {})}
        if relations:
            entry["relations"] = [
                {"rel": r.get("rel"), "url": r.get("url"),
                 "comment": (r.get("attributes") or {}).get("comment")}
                for r in item.get("relations", []) or []
            ]
        out.append(entry)
    return out


def wit_get(client, args):
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    emit(_fetch_work_items(client, args.ids, fields=fields, relations=args.relations))


def wit_query(client, args):
    wiql = read_value(args.wiql)
    query = {"$top": args.top} if args.top else None
    data = client.request("POST", "/wit/wiql", body={"query": wiql}, query=query)

    ids = [w["id"] for w in data.get("workItems", []) if "id" in w]
    if not ids:
        # Tree / one-hop queries return workItemRelations instead.
        for rel in data.get("workItemRelations", []) or []:
            target = (rel.get("target") or {}).get("id")
            if target and target not in ids:
                ids.append(target)
    if not ids:
        emit({"count": 0, "workItems": []})
        return

    if args.ids_only:
        emit({"count": len(ids), "ids": ids})
        return

    fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    if fields is None and not args.expand_all:
        # Honour the SELECT clause of the WIQL query.
        columns = [c.get("referenceName") for c in data.get("columns", []) if c.get("referenceName")]
        fields = columns or None
    items = _fetch_work_items(client, ids, fields=fields)
    emit({"count": len(items), "workItems": items})


def wit_create(client, args):
    ops = build_patch(args.field, args.field_multiline, {
        "System.Title": args.title,
        "System.AssignedTo": args.assign,
        "System.AreaPath": args.area,
        "System.IterationPath": args.iteration,
    })
    if args.parent is not None:
        ops.append(_add_parent_op(client, args.parent))
    quoted = urllib.parse.quote(f"${args.type}", safe="")
    data = client.request("POST", f"/wit/workitems/{quoted}", body=ops,
                          content_type=PATCH_CONTENT_TYPE)
    emit({"id": data.get("id"), "rev": data.get("rev"),
          "url": data.get("_links", {}).get("html", {}).get("href"),
          "fields": data.get("fields", {})})


def wit_update(client, args):
    ops = build_patch(args.field, args.field_multiline, {
        "System.Title": args.title,
        "System.State": args.state,
        "System.AssignedTo": args.assign,
        "System.AreaPath": args.area,
        "System.IterationPath": args.iteration,
    }, require=args.parent is None)
    if args.parent is not None:
        # Ahead of the field ops so the /rev test is the first thing evaluated.
        ops = _parent_ops(client, args.id, args.parent) + ops
    if not ops:
        emit({"id": args.id, "parent": args.parent, "unchanged": True})
        return
    data = client.request("PATCH", f"/wit/workitems/{args.id}", collection_level=True,
                          body=ops, content_type=PATCH_CONTENT_TYPE)
    emit({"id": data.get("id"), "rev": data.get("rev"), "fields": data.get("fields", {})})


def wit_comment(client, args):
    # System.History is the portable way to append a comment on ADS 2022.
    text = read_value(args.text)
    ops = [{"op": "add", "path": "/fields/System.History", "value": to_html(text)}]
    data = client.request("PATCH", f"/wit/workitems/{args.id}", collection_level=True,
                          body=ops, content_type=PATCH_CONTENT_TYPE)
    emit({"id": data.get("id"), "rev": data.get("rev"), "commented": True})


def wit_comments(client, args):
    data = client.request("GET", f"/wit/workItems/{args.id}/comments",
                          api_version=COMMENTS_API_VERSION)
    emit([
        {"id": c.get("id"),
         "createdBy": (c.get("createdBy") or {}).get("displayName"),
         "createdDate": c.get("createdDate"),
         "text": c.get("text")}
        for c in data.get("comments", [])
    ])


# --------------------------------------------------------------------------
# pull requests
# --------------------------------------------------------------------------


def _ref(name):
    if not name:
        return name
    return name if name.startswith("refs/") else f"refs/heads/{name}"


def _repo_path(repo, suffix=""):
    return f"/git/repositories/{urllib.parse.quote(repo, safe='')}{suffix}"


def _pr_summary(pr):
    return {
        "pullRequestId": pr.get("pullRequestId"),
        "title": pr.get("title"),
        "status": pr.get("status"),
        "isDraft": pr.get("isDraft"),
        "createdBy": (pr.get("createdBy") or {}).get("displayName"),
        "sourceRefName": pr.get("sourceRefName"),
        "targetRefName": pr.get("targetRefName"),
        "mergeStatus": pr.get("mergeStatus"),
        "creationDate": pr.get("creationDate"),
        "repository": (pr.get("repository") or {}).get("name"),
    }


def pr_list(client, args):
    query = {
        "searchCriteria.status": args.status,
        "$top": args.top,
    }
    if args.target:
        query["searchCriteria.targetRefName"] = _ref(args.target)
    if args.creator:
        query["searchCriteria.creatorId"] = args.creator
    data = client.request("GET", _repo_path(args.repo, "/pullrequests"), query=query)
    emit({"count": data.get("count"), "value": [_pr_summary(p) for p in data.get("value", [])]})


def pr_get(client, args):
    data = client.request("GET", _repo_path(args.repo, f"/pullrequests/{args.id}"))
    if args.raw:
        emit(data)
        return
    summary = _pr_summary(data)
    summary["description"] = data.get("description")
    summary["reviewers"] = [
        {"displayName": r.get("displayName"), "vote": r.get("vote"),
         "isRequired": r.get("isRequired")}
        for r in data.get("reviewers", []) or []
    ]
    summary["lastMergeSourceCommit"] = (data.get("lastMergeSourceCommit") or {}).get("commitId")
    emit(summary)


def pr_threads(client, args):
    data = client.request("GET", _repo_path(args.repo, f"/pullRequests/{args.id}/threads"))
    threads = []
    for thread in data.get("value", []):
        if args.unresolved_only and thread.get("status") in (None, "closed", "fixed", "wontFix", "byDesign"):
            continue
        context = thread.get("threadContext") or {}
        threads.append({
            "threadId": thread.get("id"),
            "status": thread.get("status"),
            "filePath": context.get("filePath"),
            "line": ((context.get("rightFileStart") or context.get("leftFileStart") or {}).get("line")),
            "comments": [
                {"id": c.get("id"),
                 "author": (c.get("author") or {}).get("displayName"),
                 "publishedDate": c.get("publishedDate"),
                 "commentType": c.get("commentType"),
                 "content": c.get("content")}
                for c in thread.get("comments", []) or []
                if c.get("commentType") != "system" or args.include_system
            ],
        })
    threads = [t for t in threads if t["comments"]]
    emit({"count": len(threads), "threads": threads})


def pr_workitems(client, args):
    """Work items linked to the pull request, with their fields resolved."""
    data = client.request("GET", _repo_path(args.repo, f"/pullRequests/{args.id}/workitems"))
    ids = []
    for ref in data.get("value", []) or []:
        try:
            ids.append(int(ref.get("id")))
        except (TypeError, ValueError):
            continue
    if not ids:
        emit({"count": 0, "workItems": []})
        return
    if args.ids_only:
        emit({"count": len(ids), "ids": ids})
        return
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else None
    items = _fetch_work_items(client, ids, fields=fields)
    emit({"count": len(items), "workItems": items})


def pr_comment(client, args):
    text = read_value(args.text)
    if args.thread:
        data = client.request(
            "POST",
            _repo_path(args.repo, f"/pullRequests/{args.id}/threads/{args.thread}/comments"),
            body={"content": text, "commentType": "text"},
        )
        emit({"threadId": args.thread, "commentId": data.get("id")})
        return

    body = {"comments": [{"content": text, "commentType": "text"}], "status": "active"}
    if args.file:
        context = {"filePath": args.file}
        if args.line:
            context["rightFileStart"] = {"line": args.line, "offset": 1}
            context["rightFileEnd"] = {"line": args.line, "offset": 1}
        body["threadContext"] = context
    data = client.request("POST", _repo_path(args.repo, f"/pullRequests/{args.id}/threads"),
                          body=body)
    emit({"threadId": data.get("id"),
          "commentId": (data.get("comments") or [{}])[0].get("id")})


def pr_create(client, args):
    body = {
        "sourceRefName": _ref(args.source),
        "targetRefName": _ref(args.target),
        "title": args.title,
        "description": read_value(args.description) if args.description else "",
        "isDraft": bool(args.draft),
    }
    if args.reviewer:
        body["reviewers"] = [{"id": r} for r in args.reviewer]
    if args.work_item:
        body["workItemRefs"] = [{"id": str(w)} for w in args.work_item]
    data = client.request("POST", _repo_path(args.repo, "/pullrequests"), body=body)
    summary = _pr_summary(data)
    summary["url"] = (data.get("_links") or {}).get("web", {}).get("href")
    emit(summary)


# --------------------------------------------------------------------------
# builds
# --------------------------------------------------------------------------


def build_definitions(client, args):
    query = {"$top": args.top, "name": args.name}
    data = client.request("GET", "/build/definitions", query=query)
    emit([
        {"id": d.get("id"), "name": d.get("name"), "path": d.get("path"),
         "queueStatus": d.get("queueStatus")}
        for d in data.get("value", [])
    ])


def _build_summary(build):
    return {
        "id": build.get("id"),
        "buildNumber": build.get("buildNumber"),
        "definition": (build.get("definition") or {}).get("name"),
        "status": build.get("status"),
        "result": build.get("result"),
        "sourceBranch": build.get("sourceBranch"),
        "sourceVersion": build.get("sourceVersion"),
        "queueTime": build.get("queueTime"),
        "finishTime": build.get("finishTime"),
        "requestedFor": (build.get("requestedFor") or {}).get("displayName"),
    }


def build_list(client, args):
    query = {
        "$top": args.top,
        "definitions": args.definition,
        "statusFilter": args.status,
        "resultFilter": args.result,
        "branchName": _ref(args.branch) if args.branch else None,
        "queryOrder": "queueTimeDescending",
    }
    data = client.request("GET", "/build/builds", query=query)
    emit([_build_summary(b) for b in data.get("value", [])])


def build_get(client, args):
    data = client.request("GET", f"/build/builds/{args.id}")
    emit(_build_summary(data))


def _timeline_failures(client, build_id):
    data = client.request("GET", f"/build/builds/{build_id}/timeline")
    records = data.get("records", []) or []
    failed = [r for r in records if r.get("result") in ("failed", "canceled")]
    failed.sort(key=lambda r: r.get("order") or 0)
    return failed


def build_logs(client, args):
    if args.log:
        emit(_tail(_fetch_log(client, args.id, args.log), args.tail))
        return

    failed = _timeline_failures(client, args.id)
    if not failed:
        emit({"buildId": args.id, "failedRecords": [],
              "note": "No failed timeline records. The build may still be running, "
                      "or it succeeded."})
        return

    out = []
    for record in failed:
        entry = {
            "name": record.get("name"),
            "type": record.get("type"),
            "result": record.get("result"),
            "logId": (record.get("log") or {}).get("id"),
            "issues": [
                {"type": i.get("type"), "message": i.get("message")}
                for i in record.get("issues", []) or []
            ],
        }
        if args.fetch and entry["logId"]:
            try:
                entry["log"] = _tail(_fetch_log(client, args.id, entry["logId"]), args.tail)
            except AdoError as exc:
                entry["log"] = f"(could not fetch log: {exc})"
        out.append(entry)
    emit({"buildId": args.id, "failedRecords": out})


def _fetch_log(client, build_id, log_id):
    return client.request("GET", f"/build/builds/{build_id}/logs/{log_id}",
                          accept="text/plain", raw=True)


def _tail(text, lines):
    if not lines:
        return text
    split = text.splitlines()
    if len(split) <= lines:
        return text
    return "\n".join([f"... ({len(split) - lines} earlier lines omitted)"] + split[-lines:])


# --------------------------------------------------------------------------
# escape hatch
# --------------------------------------------------------------------------


def raw_request(client, args):
    query = {}
    for item in args.query or []:
        name, value = split_assignment(item)
        query[name] = value
    body = json.loads(read_value(args.data)) if args.data else None
    result = client.request(
        args.method, args.path, collection_level=args.collection_level,
        query=query or None, body=body,
        content_type=args.content_type,
        api_version=args.api_version_override,
    )
    emit(result)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _add_field_flags(parser):
    parser.add_argument("--field", action="append", metavar="REF=VALUE",
                        help="Set a field by reference name. Repeatable. "
                             "VALUE may be @path to read from a file.")
    parser.add_argument("--field-multiline", action="append", metavar="REF=VALUE",
                        help="Same, but converts plain text to HTML. Use for fields "
                             "whose type is `html` (Description, Acceptance Criteria, "
                             "Repro Steps).")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ado.py",
        description="Azure DevOps Server 2022 (on-prem) REST client.",
    )
    parser.add_argument("--project", help="Team project (overrides ADO_PROJECT).")
    parser.add_argument("--api-version", default=DEFAULT_API_VERSION,
                        help="Default api-version (ADS 2022 = 7.0).")
    groups = parser.add_subparsers(dest="group", required=True)

    # ---- work items ----
    wit = groups.add_parser("wit", help="Work items").add_subparsers(dest="cmd", required=True)

    p = wit.add_parser("types", help="List work item types in the project.")
    p.set_defaults(func=wit_types)

    p = wit.add_parser("describe-type",
                       help="Discover the fields and states of one work item type.")
    p.add_argument("--type", required=True, help='e.g. "User Story", "Feature", "Bug"')
    p.add_argument("--save", action="store_true",
                   help="Write a Markdown reference into references/fields/.")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    p.set_defaults(func=wit_describe_type)

    p = wit.add_parser("get", help="Fetch work items by id.")
    p.add_argument("ids", nargs="+", type=int)
    p.add_argument("--fields", help="Comma-separated reference names (default: all).")
    p.add_argument("--relations", action="store_true", help="Include links/relations.")
    p.set_defaults(func=wit_get)

    p = wit.add_parser("query", help="Run a WIQL query and fetch the matching items.")
    p.add_argument("--wiql", required=True, help="WIQL text, or @path to a file.")
    p.add_argument("--fields", help="Comma-separated reference names to return.")
    p.add_argument("--expand-all", action="store_true", help="Return every field.")
    p.add_argument("--ids-only", action="store_true", help="Return ids without a second call.")
    p.add_argument("--top", type=int, help="Cap the number of results.")
    p.set_defaults(func=wit_query)

    p = wit.add_parser("create", help="Create a work item.")
    p.add_argument("--type", required=True, help='e.g. "User Story"')
    p.add_argument("--title")
    p.add_argument("--assign", help="System.AssignedTo")
    p.add_argument("--area", help="System.AreaPath")
    p.add_argument("--iteration", help="System.IterationPath")
    p.add_argument("--parent", type=int, metavar="ID",
                   help="Create it as a child of this work item.")
    _add_field_flags(p)
    p.set_defaults(func=wit_create)

    p = wit.add_parser("update", help="Update a work item.")
    p.add_argument("id", type=int)
    p.add_argument("--title")
    p.add_argument("--state", help="System.State (values differ per type; check describe-type)")
    p.add_argument("--assign")
    p.add_argument("--area")
    p.add_argument("--iteration")
    p.add_argument("--parent", type=int, metavar="ID",
                   help="Make it a child of this work item, replacing any current parent.")
    _add_field_flags(p)
    p.set_defaults(func=wit_update)

    p = wit.add_parser("comment", help="Append a comment (via System.History).")
    p.add_argument("id", type=int)
    p.add_argument("--text", required=True, help="Comment text, or @path to a file.")
    p.set_defaults(func=wit_comment)

    p = wit.add_parser("comments", help="Read the comments on a work item.")
    p.add_argument("id", type=int)
    p.set_defaults(func=wit_comments)

    # ---- pull requests ----
    pr = groups.add_parser("pr", help="Pull requests").add_subparsers(dest="cmd", required=True)

    p = pr.add_parser("list", help="List pull requests.")
    p.add_argument("--repo", required=True)
    p.add_argument("--status", default="active",
                   choices=["active", "abandoned", "completed", "all"])
    p.add_argument("--target", help="Target branch (refs/heads/ is added if omitted).")
    p.add_argument("--creator", help="Creator identity id.")
    p.add_argument("--top", type=int, default=25)
    p.set_defaults(func=pr_list)

    p = pr.add_parser("get", help="Show one pull request.")
    p.add_argument("id", type=int)
    p.add_argument("--repo", required=True)
    p.add_argument("--raw", action="store_true")
    p.set_defaults(func=pr_get)

    p = pr.add_parser("threads", help="Read the review threads on a pull request.")
    p.add_argument("id", type=int)
    p.add_argument("--repo", required=True)
    p.add_argument("--unresolved-only", action="store_true")
    p.add_argument("--include-system", action="store_true",
                   help="Include system-generated comments.")
    p.set_defaults(func=pr_threads)

    p = pr.add_parser("workitems", help="Work items linked to a pull request.")
    p.add_argument("id", type=int)
    p.add_argument("--repo", required=True)
    p.add_argument("--fields", help="Comma-separated reference names (default: all).")
    p.add_argument("--ids-only", action="store_true")
    p.set_defaults(func=pr_workitems)

    p = pr.add_parser("comment", help="Post a comment on a pull request.")
    p.add_argument("id", type=int)
    p.add_argument("--repo", required=True)
    p.add_argument("--text", required=True, help="Comment text, or @path to a file.")
    p.add_argument("--thread", type=int, help="Reply into an existing thread.")
    p.add_argument("--file", help="Anchor a new thread to this file path.")
    p.add_argument("--line", type=int, help="Anchor a new thread to this line.")
    p.set_defaults(func=pr_comment)

    p = pr.add_parser("create", help="Create a pull request.")
    p.add_argument("--repo", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", help="Body text, or @path to a file.")
    p.add_argument("--draft", action="store_true")
    p.add_argument("--reviewer", action="append", help="Reviewer identity id. Repeatable.")
    p.add_argument("--work-item", action="append", type=int, help="Work item id to link.")
    p.set_defaults(func=pr_create)

    # ---- builds ----
    build = groups.add_parser("build", help="Build pipelines").add_subparsers(
        dest="cmd", required=True)

    p = build.add_parser("definitions", help="List build definitions.")
    p.add_argument("--name", help="Filter by name (wildcards allowed).")
    p.add_argument("--top", type=int, default=50)
    p.set_defaults(func=build_definitions)

    p = build.add_parser("list", help="List build runs, newest first.")
    p.add_argument("--definition", help="Definition id (comma-separated for several).")
    p.add_argument("--status", help="e.g. completed, inProgress, notStarted")
    p.add_argument("--result", help="e.g. failed, succeeded, partiallySucceeded")
    p.add_argument("--branch")
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(func=build_list)

    p = build.add_parser("get", help="Show one build run.")
    p.add_argument("id", type=int)
    p.set_defaults(func=build_get)

    p = build.add_parser("logs", help="Triage a failed build.")
    p.add_argument("id", type=int)
    p.add_argument("--fetch", action="store_true",
                   help="Also download the log of each failed step.")
    p.add_argument("--log", type=int, help="Download one specific log id instead.")
    p.add_argument("--tail", type=int, default=200,
                   help="Keep only the last N lines of each log (0 = whole log).")
    p.set_defaults(func=build_logs)

    # ---- escape hatch ----
    p = groups.add_parser("request", help="Call any REST endpoint directly.")
    p.add_argument("method")
    p.add_argument("path", help="Path relative to _apis, e.g. /wit/workitems/123")
    p.add_argument("--query", action="append", metavar="NAME=VALUE")
    p.add_argument("--data", help="JSON body, or @path to a file.")
    p.add_argument("--content-type", default="application/json")
    p.add_argument("--api-version-override", dest="api_version_override",
                   help="Override api-version for this call (e.g. 7.0-preview.3).")
    p.add_argument("--collection-level", action="store_true",
                   help="Omit the project segment from the URL.")
    p.set_defaults(func=raw_request)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        client = client_from_args(args)
        args.func(client, args)
    except AdoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
