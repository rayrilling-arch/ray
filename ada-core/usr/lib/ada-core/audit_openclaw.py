#!/usr/bin/env python3
"""Audit OpenClaw plugins/overrides; optionally fix routing to local Ada Core."""

from __future__ import annotations

import sys

from openclaw_audit import audit_openclaw, fix_all_openclaw, format_report


def main() -> int:
    if "--fix" in sys.argv:
        logs = fix_all_openclaw()
        for line in logs:
            print(line)
        if not logs:
            print("FIX_OK no changes needed")

    report = audit_openclaw()
    print(format_report(report))
    failures = [issue for issue in report.issues if issue.severity == "fail"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
