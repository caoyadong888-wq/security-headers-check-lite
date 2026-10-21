#!/usr/bin/env python3
"""Lite header check: presence, exact allowed values, and duplicates.

No max-age floor, no CSP substring rules, no JSON report, and no Chinese
CLI. The full checker adds those. This file still refuses any host that is
not loopback and still does not follow redirects.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http import client as http_client

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class UsageError(Exception):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="check_headers_lite.py")
    parser.add_argument("--url", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--timeout", type=float, default=3.0)
    return parser.parse_args(argv)


def load_policy(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise UsageError(f"policy file: {exc.__class__.__name__}") from exc
    except json.JSONDecodeError as exc:
        raise UsageError(f"policy is not JSON: {exc.msg}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list) or not data["rules"]:
        raise UsageError("policy rules must be a non-empty list")
    for rule in data["rules"]:
        if not isinstance(rule, dict):
            raise UsageError("rule must be an object")
        if not isinstance(rule.get("id"), str) or not rule["id"]:
            raise UsageError("rule needs an id")
        if not isinstance(rule.get("header"), str) or not rule["header"]:
            raise UsageError("rule needs a header")
        allowed = rule.get("allowed_values")
        if allowed is not None and (
            not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed)
        ):
            raise UsageError("allowed_values must be a list of strings")
    if not isinstance(data.get("name", "lite"), str):
        raise UsageError("policy name must be a string")
    return data


def fetch(url: str, timeout: float) -> tuple[int, list[tuple[str, str]]]:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "http":
        raise UsageError("only http is supported")
    if parts.username is not None or parts.password is not None:
        raise UsageError("userinfo is not allowed in the URL")
    host = parts.hostname
    if host is None or host.lower() not in LOOPBACK:
        raise UsageError("host is not loopback")
    port = parts.port or 80
    path = parts.path or "/"
    if parts.query:
        path = path + "?" + parts.query
    connect = "127.0.0.1" if host.lower() == "localhost" else host
    connection = http_client.HTTPConnection(connect, port, timeout=timeout)
    try:
        try:
            connection.request(
                "GET",
                path,
                headers={"Host": host, "User-Agent": "security-headers-check-lite/1.0", "Connection": "close"},
            )
            response = connection.getresponse()
            status = response.status
            headers = response.getheaders()
            response.read(65536)
        except UsageError:
            raise
        except Exception as exc:
            raise UsageError(f"request failed: {exc.__class__.__name__}") from exc
    finally:
        connection.close()
    return status, headers


def evaluate(headers: list[tuple[str, str]], policy: dict) -> list[dict]:
    grouped: dict[str, list[str]] = {}
    for name, value in headers:
        grouped.setdefault(name.lower(), []).append(value.strip())
    findings = []
    for rule in policy["rules"]:
        values = grouped.get(rule["header"].lower(), [])
        reasons: list[str] = []
        if not values:
            reasons.append("missing")
        else:
            if len(values) > 1:
                reasons.append("duplicate")
            allowed = rule.get("allowed_values")
            if allowed is not None:
                permitted = {item.lower() for item in allowed}
                for value in values:
                    if value.lower() not in permitted:
                        reasons.append("value")
                        break
        status = "PASS" if not reasons else "FAIL"
        findings.append(
            {
                "id": rule["id"],
                "header": rule["header"],
                "status": status,
                "reasons": reasons,
                "values": values,
            }
        )
    return findings


def render(url: str, status: int, policy: dict, findings: list[dict]) -> str:
    counts = {"pass": 0, "fail": 0}
    for item in findings:
        counts[item["status"].lower()] += 1
    result = "FAIL" if counts["fail"] else "PASS"
    lines = [
        "banner: local security header check (lite)",
        f"target: {url}",
        f"http_status: {status}",
        f"policy: {policy.get('name', 'lite')}",
    ]
    for item in findings:
        reason_text = ",".join(item["reasons"]) if item["reasons"] else "-"
        lines.append(f"- [{item['status']}] {item['id']} {item['header']} reasons={reason_text}")
        for value in item["values"]:
            lines.append(f"  value: {value}")
    lines.append(f"summary: pass={counts['pass']} fail={counts['fail']}")
    lines.append(f"result: {result}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(list(sys.argv[1:] if argv is None else argv))
        if args.timeout <= 0:
            raise UsageError("timeout must be greater than 0")
        policy = load_policy(args.policy)
        status, headers = fetch(args.url, args.timeout)
        findings = evaluate(headers, policy)
        sys.stdout.write(render(args.url, status, policy, findings))
        return 1 if any(item["status"] == "FAIL" for item in findings) else 0
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
