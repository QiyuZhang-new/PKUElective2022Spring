---
name: pku-autoelective-runner
description: Set up, configure, validate, test, run, monitor, stop, or troubleshoot this PKUElective2022Spring checkout. Use when an agent needs to operate the project after cloning QiyuZhang-new/PKUElective2022Spring from GitHub.
---

# PKU Autoelective Runner

Operate this repository safely after it has been cloned. Read the current
`README.md`, `requirements.txt`, `.gitignore`, `config.sample.ini`, and
`apikey.sample.json` before acting because repository behavior may change.

## Protect private data and external systems

- Treat `config.ini`, `apikey.json`, logs, caches, cookies, account IDs, passwords,
  and API credentials as private. Never print their values or ask the user to paste
  them into chat.
- Before secrets are entered, run
  `git check-ignore config.ini apikey.json log cache .venv`. Stop and repair
  `.gitignore` if any private path is not ignored.
- Never overwrite an existing `config.ini` or `apikey.json`.
- Do not perform a live login, paid captcha request, course-selection submission,
  or long-running launch without the user's explicit authorization for that action.
- Ask the user to confirm that automation is permitted by current university rules.
  This is an older project; do not promise compatibility with the live site.
- Run only one instance. `main.py --with-monitor` already contains the elective loop.

## Build the environment

Use the checkout supplied by the user. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

Prefer Python 3.10 or newer. Use the virtual environment's interpreter explicitly
in later commands so activation is unnecessary.

## Prepare private configuration

Only if the destination does not already exist, copy the templates on Windows:

```powershell
Copy-Item config.sample.ini config.ini
Copy-Item apikey.sample.json apikey.json
```

Use `cp` on macOS or Linux after checking that the destination is absent. Ask the
user to edit the copies locally without sharing their secret contents.

Project-specific facts:

- `[iaaa]` contains the PKU account ID and password.
- `[client] supply_cancel_pages = 1,2` monitors multiple comma-separated pages.
  The legacy singular `supply_cancel_page` is accepted, but prefer the plural key.
- Keep `elective_client_pool_size` small, normally `1` or `2`.
- Each `[course.*]` section needs a unique suffix and the exact course name, class,
  and school values expected by the site.
- `apikey.json` holds TTShitu credentials. Recognition is requested only after an
  available seat is observed. Voting uses three recognition requests per attempt,
  with at most 15 attempts for a course during that run.
- Leave optional notification integrations disabled unless the user requests them.

Do not infer missing course values or silently alter the user's course choices.
Explain validation errors without exposing private values.

## Validate offline first

On Windows:

```powershell
.\.venv\Scripts\python.exe main.py --check-config
```

Use `.venv/bin/python main.py --check-config` on macOS or Linux. This command must
not log in or call the captcha API. After source changes, also run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q autoelective main.py tools tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Test the network only when authorized

The connectivity diagnostic is read-only:

```powershell
.\.venv\Scripts\python.exe tools\check_connectivity.py
```

An explicitly authorized read-only IAAA login test is:

```powershell
.\.venv\Scripts\python.exe tools\check_login.py --direct
```

The login diagnostic must not request a captcha or submit a course choice. Report
status and error categories without reproducing credentials, cookies, or full
response bodies containing personal information.

PKU requests should bypass a general proxy. Before diagnostics or launch in Windows
PowerShell:

```powershell
$env:NO_PROXY = "localhost,127.0.0.1,.pku.edu.cn"
$env:no_proxy = $env:NO_PROXY
```

On macOS or Linux:

```bash
export NO_PROXY="localhost,127.0.0.1,.pku.edu.cn"
export no_proxy="$NO_PROXY"
```

## Launch, observe, and stop

After explicit authorization, launch on Windows with:

```powershell
.\.venv\Scripts\python.exe main.py --with-monitor
```

Use `.venv/bin/python main.py --with-monitor` on macOS or Linux. Keep the terminal
open. The monitor normally listens on localhost port 7074 and exposes
`/stat/loop`, `/stat/course`, and `/stat/error`.

Stop with `Ctrl+C`. To terminate a detached instance, first list command lines and
identify only Python processes invoking this checkout's `main.py`; terminate those
exact PIDs. Never kill all Python processes or an unrelated terminal host.

## Diagnose failures precisely

- After a long run, stale sessions or server-side changes may require a clean
  restart followed by an authorized read-only login test.
- Distinguish DNS, TCP, proxy, HTTP, IAAA authentication, elective-session, parsing,
  and captcha failures using observed evidence.
- Do not loop indefinitely in diagnostics. Respect the 15-attempt recognition cap
  and avoid paid recognition tests unless explicitly authorized.
- A local proxy may be used for GitHub only after permission; do not route PKU login
  traffic through it.

## Keep GitHub clean

Before committing or pushing, test and inspect `git status`. Stage only known-safe
source, tests, samples, documentation, and this repository skill. Confirm that
`config.ini`, `apikey.json`, `.venv`, `log`, and `cache` remain ignored and absent
from the staged list. Scan staged content for credentials without printing matches.
