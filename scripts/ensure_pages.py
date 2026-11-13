#!/usr/bin/env python3
"""确保 GitHub Pages 已启用（`build_type=workflow`），必要时补触发一次部署。

凭据只从环境变量 `GITHUB_TOKEN` 读（CNB 密钥仓库 imports 注入），不写值、不打印。
幂等：已启用则直接退出；权限不足只警告、不阻塞同步流水线，由人工在 Settings 启用。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

REPO = "h1s97x/altdatahub-docs"
API = f"https://api.github.com/repos/{REPO}"


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN 未注入")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "altdatahub-docs-ci",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return response.status, json.loads(raw) if raw else {}


def main() -> int:
    try:
        request("GET", "/pages")
        print("GitHub Pages already enabled; nothing to do")
        return 0
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print(f"WARN: cannot check Pages status (HTTP {exc.code}); enable manually in Settings")
            return 0
    except Exception as exc:  # noqa: BLE001 - 不该让仓库设置问题阻塞文档同步
        print(f"WARN: cannot check Pages status ({type(exc).__name__}); enable manually")
        return 0

    try:
        request("POST", "/pages", {"build_type": "workflow"})
        print("GitHub Pages enabled (build_type=workflow)")
    except urllib.error.HTTPError as exc:
        print(
            f"WARN: enable Pages failed (HTTP {exc.code}); "
            "enable manually: Settings -> Pages -> Build and deployment -> Source: GitHub Actions"
        )
        return 0

    try:
        request("POST", "/actions/workflows/pages.yml/dispatches", {"ref": "main"})
        print("dispatched Deploy docs to GitHub Pages")
    except urllib.error.HTTPError as exc:
        print(f"WARN: dispatch failed (HTTP {exc.code}); rerun the workflow manually")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
