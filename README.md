# HTTP Security Headers Checker (lite)

## English

### Purpose

A free slice of the header checker. It requests one loopback URL and reports whether `Strict-Transport-Security` is present, and whether `X-Frame-Options` and `X-Content-Type-Options` match an allow-list. It does not parse `max-age`, it does not look at CSP substrings, and it does not print Chinese or JSON. Duplicate fields fail. Redirects are not followed. Hosts other than `127.0.0.1`, `localhost`, and `::1` are refused.

The sample mailbox in the full guide is `ops@example.com`. This subset does not call off-box addresses.

### Deliverables

- `deliverables/check_headers_lite.py` — presence and allowed-value report.
- `deliverables/baseline_policy.json` — three-header example policy.
- `deliverables/fixture_server.py` — loopback server for `<slug>.txt` files.
- `examples/fixtures/good.txt` — HSTS, `DENY`, and `nosniff`.
- `examples/fixtures/missing.txt` — no security headers.
- `examples/run_demo.sh` — grades both fixtures.

### Quick start

```bash
bash examples/run_demo.sh
```

Exit 0 means every rule passed. Exit 1 means a header was missing, duplicated, or outside the allow-list. Exit 2 is a bad argument, a bad policy, or a socket error. Python 3.9 or newer, standard library only. No network.

## 中文

### 用途

安全响应头检查的免费子集。它请求一个回环 URL，报告 `Strict-Transport-Security` 是否存在，以及 `X-Frame-Options` 和 `X-Content-Type-Options` 是否落在允许列表里。它不解析 `max-age`，不检查 CSP 子串，也不输出中文或 JSON。重复的字段算失败。不跟随重定向。`127.0.0.1`、`localhost` 和 `::1` 以外的主机会被拒绝。

完整指南里的示例邮箱是 `ops@example.com`。这个子集不会访问外网地址。

### 交付清单

- `deliverables/check_headers_lite.py` — 存在性与允许值报告。
- `deliverables/baseline_policy.json` — 三项响应头的示例策略。
- `deliverables/fixture_server.py` — 为 `<slug>.txt` 提供服务的回环服务器。
- `examples/fixtures/good.txt` — 含 HSTS、`DENY` 和 `nosniff`。
- `examples/fixtures/missing.txt` — 没有安全响应头。
- `examples/run_demo.sh` — 给两份夹具打分。

### 快速开始

```bash
bash examples/run_demo.sh
```

退出码 0 表示每条规则都通过。退出码 1 表示响应头缺失、重复或不在允许列表中。退出码 2 是参数、策略或套接字错误。需要 Python 3.9 或更新版本，只要标准库。不需要网络。

Full version: GUMROAD_URL
