"""Perform a read-only IAAA and elective login diagnostic.

This script never prints credentials/tokens, requests a captcha, or submits an
election. It only logs in and reads pages that the main program needs.
"""

import argparse
import random
import sys
import time
from pathlib import Path

from requests import RequestException


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from autoelective.environ import Environ  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-c", "--config", help="path to config.ini")
    parser.add_argument(
        "--scan-pages",
        type=int,
        default=0,
        metavar="N",
        help="read up to N supply/cancel pages to locate configured targets",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="ignore environment proxies for PKU requests",
    )
    args = parser.parse_args()

    environment = Environ()
    environment.config_ini = args.config

    from autoelective.config import AutoElectiveConfig

    config = AutoElectiveConfig()
    if config.iaaa_id.upper().endswith("_HERE") or config.iaaa_password.upper().endswith("_HERE"):
        print("FAILED before login: IAAA credentials are still placeholders")
        return 2

    # Diagnostics must never dump authenticated requests or send notifications,
    # regardless of the user's normal runtime settings.
    config._config.set("client", "debug_print_request", "false")
    config._config.set("client", "debug_dump_request", "false")
    config._config.set("notification", "disable_push", "true")

    from autoelective.const import USER_AGENT_LIST
    from autoelective.elective import ElectiveClient
    from autoelective.exceptions import AutoElectiveException
    from autoelective.iaaa import IAAAClient
    from autoelective.parser import get_courses, get_courses_with_detail, get_sida, get_tables, get_title

    user_agent = random.choice(USER_AGENT_LIST)
    iaaa = IAAAClient(timeout=config.iaaa_client_timeout)
    elective = ElectiveClient(id="diagnostic", timeout=config.elective_client_timeout)
    if args.direct:
        iaaa._session.trust_env = False
        elective._session.trust_env = False
    iaaa.set_user_agent(user_agent)
    elective.set_user_agent(user_agent)

    stage = "IAAA OAuth entry"
    try:
        response = iaaa.oauth_home()
        print("OK  IAAA OAuth entry: HTTP %s, TLS certificate verified" % response.status_code)

        stage = "IAAA credential login"
        response = iaaa.oauth_login(config.iaaa_id, config.iaaa_password)
        token = response.json().get("token")
        if not token:
            print("FAILED IAAA credential login: successful response did not contain a token")
            return 1
        print("OK  IAAA credential login: authentication token received")

        stage = "elective SSO login"
        response = elective.sso_login(token)
        if config.is_dual_degree:
            stage = "elective dual-degree identity selection"
            response = elective.sso_login_dual_degree(
                get_sida(response), config.identity, response.url
            )
        title = get_title(response._tree) or "(no title)"
        print(
            "OK  elective SSO login: HTTP %s, title=%s, session cookie(s)=%d"
            % (response.status_code, title, len(elective._session.cookies))
        )

        stage = "elective help page"
        response = elective.get_HelpController()
        print(
            "OK  elective help page: HTTP %s, title=%s"
            % (response.status_code, get_title(response._tree) or "(no title)")
        )

        stage = "supply/cancel page"
        if config.supply_cancel_page == 1:
            response = elective.get_SupplyCancel(config.iaaa_id)
        else:
            elective.get_SupplyCancel(config.iaaa_id)
            response = elective.get_supplement(
                config.iaaa_id, page=config.supply_cancel_page
            )
        tables = get_tables(response._tree)
        if len(tables) < 2:
            print("FAILED supply/cancel page: parser found fewer than two course tables")
            return 1
        selected = get_courses(tables[1])
        planned = get_courses_with_detail(tables[0])
        print(
            "OK  supply/cancel page: HTTP %s, parser found %d planned and %d selected course(s)"
            % (response.status_code, len(planned), len(selected))
        )

        pages = {config.supply_cancel_page: planned}
        if args.scan_pages > 0:
            signatures = {
                tuple((course.name, course.class_no, course.school) for course in planned)
            }
            for page in range(1, args.scan_pages + 1):
                if page == config.supply_cancel_page:
                    continue
                time.sleep(1)
                stage = "supply/cancel page %d" % page
                try:
                    if page == 1:
                        page_response = elective.get_SupplyCancel(config.iaaa_id)
                    else:
                        page_response = elective.get_supplement(config.iaaa_id, page=page)
                    page_tables = get_tables(page_response._tree)
                    if len(page_tables) < 2:
                        break
                    page_courses = get_courses_with_detail(page_tables[0])
                except AutoElectiveException:
                    break

                signature = tuple(
                    (course.name, course.class_no, course.school) for course in page_courses
                )
                if not signature or signature in signatures:
                    break
                signatures.add(signature)
                pages[page] = page_courses
                print("OK  supply/cancel page %d: parser found %d planned course(s)" % (
                    page, len(page_courses)
                ))
                if len(page_courses) < 20:
                    break

        missing = False
        for course_id, target in config.courses.items():
            if target in selected:
                print("OK  target %s: already selected (%s, class %s)" % (
                    course_id, target.name, target.class_no
                ))
                continue

            exact_matches = [
                (page, course)
                for page, courses in pages.items()
                for course in courses
                if course == target
            ]
            if not exact_matches:
                missing = True
                same_name = [
                    (page, course)
                    for page, courses in pages.items()
                    for course in courses
                    if course.name == target.name
                ]
                if same_name:
                    for page, candidate in same_name:
                        print(
                            "FAILED target %s: same name on page %d uses class=%s, school=%s"
                            % (course_id, page, candidate.class_no, candidate.school)
                        )
                else:
                    print(
                        "FAILED target %s: not found by exact match in scanned pages"
                        % course_id
                    )
                continue

            page, match = exact_matches[0]
            state = "available" if match.is_available() else "full"
            print(
                "OK  target %s: page %d, %s (%s, class %s, selected/limit %d/%d, remaining %d)"
                % (
                    course_id,
                    page,
                    state,
                    match.name,
                    match.class_no,
                    match.used_quota,
                    match.max_quota,
                    match.remaining_quota,
                )
            )

        return 1 if missing else 0

    except AutoElectiveException as exc:
        print("FAILED %s: %s: %s" % (stage, exc.__class__.__name__, exc))
        return 1
    except RequestException as exc:
        print("FAILED %s: %s (request details redacted)" % (stage, exc.__class__.__name__))
        return 1
    except Exception as exc:
        print("FAILED %s: %s: %s" % (stage, exc.__class__.__name__, exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
