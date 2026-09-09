"""Read-only connectivity check for PKU elective and IAAA public entry pages."""

import re
import socket
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoelective.const import ElectiveURL, IAAAURL  # noqa: E402


TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def describe(name, response):
    title_match = TITLE_PATTERN.search(response.text)
    title = " ".join(title_match.group(1).split()) if title_match else "(no title)"
    redirects = " -> ".join(str(item.status_code) for item in response.history)
    if redirects:
        redirects += " -> "
    print(
        "%s: %s%s, final=%s, type=%s, title=%s"
        % (
            name,
            redirects,
            response.status_code,
            response.url,
            response.headers.get("Content-Type", "unknown"),
            title,
        )
    )


def main():
    targets = (
        ("elective-home", ElectiveURL.HomePage),
        (
            "iaaa-oauth",
            IAAAURL.OauthHomePage
            + "?appID=syllabus&appName=%E5%AD%A6%E7%94%9F%E9%80%89%E8%AF%BE%E7%B3%BB%E7%BB%9F"
            + "&redirectUrl=http%3A%2F%2Felective.pku.edu.cn%3A80%2Felective2008%2FssoLogin.do",
        ),
        ("elective-help", ElectiveURL.HelpController),
    )

    for host in (ElectiveURL.Host, IAAAURL.Host):
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443)})
        print("DNS %s: %s" % (host, ", ".join(addresses)))

    session = requests.Session()
    session.headers["User-Agent"] = "PKUAutoElective-connectivity-check/1.0"

    failed = False
    for name, url in targets:
        try:
            response = session.get(url, timeout=15, allow_redirects=True)
            describe(name, response)
            if response.status_code >= 400:
                failed = True
        except requests.RequestException as exc:
            failed = True
            print("%s: FAILED: %s" % (name, exc))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
