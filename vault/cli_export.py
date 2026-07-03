"""CLI handlers for one-way knowledge export commands."""

from __future__ import annotations

import sys

from .cli_context import _arg_value, _json_flags, _json_print, find_project_dir


def cmd_export(args):
    """One-way export commands for human-readable and portable knowledge bundles."""
    if args.export_target not in {"obsidian", "okf", "markdown", "json"}:
        print("error: export requires target: obsidian, okf, markdown, or json", file=sys.stderr)
        raise SystemExit(2)
    json_output, pretty_output = _json_flags(args)
    if args.export_target == "okf":
        from vault.okf import export_okf_bundle

        try:
            result = export_okf_bundle(
                project_dir=find_project_dir(),
                bundle_dir=args.bundle,
                category=args.category,
                tag=args.tag,
                layer=args.layer,
                limit=args.limit,
                min_trust=args.min_trust,
                include_private=args.include_private,
                include_restricted=args.include_restricted,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        if json_output:
            _json_print(result, pretty=pretty_output)
            return
        print(
            "OKF export: "
            f"matched={result['matched']} written={result['written']} "
            f"dry_run={result['dry_run']} bundle={result['bundle_dir']}"
        )
        for path in [*result["reserved_paths"], *result["paths"]][:12]:
            print(f"  {path}")
        total_paths = len(result["reserved_paths"]) + len(result["paths"])
        if total_paths > 12:
            print(f"  ... {total_paths - 12} more")
        return

    if args.export_target in {"markdown", "json"}:
        from vault.export_memory import export_memory_json, export_memory_markdown

        export_fn = export_memory_markdown if args.export_target == "markdown" else export_memory_json
        try:
            result = export_fn(
                project_dir=find_project_dir(),
                bundle_dir=args.bundle,
                category=args.category,
                tag=args.tag,
                layer=args.layer,
                limit=args.limit,
                min_trust=args.min_trust,
                include_private=args.include_private,
                include_restricted=args.include_restricted,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        if json_output:
            _json_print(result, pretty=pretty_output)
            return
        label = "Markdown" if args.export_target == "markdown" else "JSON"
        print(
            f"{label} export: "
            f"matched={result['matched']} written={result['written']} "
            f"dry_run={result['dry_run']} bundle={result['bundle_dir']}"
        )
        for path in result["paths"][:12]:
            print(f"  {path}")
        if len(result["paths"]) > 12:
            print(f"  ... {len(result['paths']) - 12} more")
        return

    from vault.export_obsidian import export_obsidian_vault

    include_review = _arg_value(args, "include_review_inbox", False) is True
    include_graph = _arg_value(args, "include_graph_overview", False) is True
    try:
        result = export_obsidian_vault(
            project_dir=find_project_dir(),
            vault_dir=args.vault,
            category=args.category,
            tag=args.tag,
            layer=args.layer,
            limit=args.limit,
            min_trust=args.min_trust,
            source=args.source,
            dry_run=args.dry_run,
            include_review_inbox=include_review,
            include_graph_overview=include_graph,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if json_output:
        _json_print({"ok": True, "status": "ok", **result}, pretty=pretty_output)
        return
    print(
        "Obsidian export: "
        f"matched={result['matched']} written={result['written']} "
        f"dry_run={result['dry_run']} vault={result['vault_dir']}"
    )
    for path in result["paths"][:10]:
        print(f"  {path}")
    if len(result["paths"]) > 10:
        print(f"  ... {len(result['paths']) - 10} more")
