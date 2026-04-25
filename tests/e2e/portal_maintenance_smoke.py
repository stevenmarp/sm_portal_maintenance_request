import os
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar
import urllib.error

BASE = os.getenv("SM_PM_BASE_URL", "http://127.0.0.1:8019").rstrip("/")
DB = os.getenv("SM_PM_DB", "odoo_19")
LOGIN = os.getenv("SM_PM_LOGIN")
PASSWORD = os.getenv("SM_PM_PASSWORD")


def extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not m:
        raise RuntimeError("csrf_token not found")
    return m.group(1)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if code in (303,) and new_req is not None:
            new_req.data = None
            new_req.method = "GET"
        return new_req


def fetch_text(opener, url, data=None):
    if data is not None:
        data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    try:
        with opener.open(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.geturl(), body
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code} at {url} (final={getattr(err, 'url', url)}) body_head={body[:200]}")


def assert_true(cond, message):
    if not cond:
        raise AssertionError(message)


def main():
    if not LOGIN or not PASSWORD:
        raise RuntimeError(
            "Missing environment variables. Required: SM_PM_LOGIN and SM_PM_PASSWORD "
            "(optional: SM_PM_BASE_URL, SM_PM_DB)."
        )

    request_name = "E2E Portal Request"
    updated_request_name = "E2E Portal Request Updated"

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        SafeRedirectHandler,
        urllib.request.HTTPCookieProcessor(cj),
    )

    # 1) Login
    print("STEP|login_page")
    login_url, login_html = fetch_text(opener, f"{BASE}/web/login?db={DB}")
    csrf = extract_csrf(login_html)

    print("STEP|login_post")
    _, post_login_html = fetch_text(
        opener,
        f"{BASE}/web/login",
        data={
            "csrf_token": csrf,
            "db": DB,
            "login": LOGIN,
            "password": PASSWORD,
        },
    )

    print("STEP|portal_home")
    my_url, my_html = fetch_text(opener, f"{BASE}/my")
    assert_true("/my/maintenance-requests" in my_html, "Portal home does not show maintenance request entry")

    # 2) Open create form
    print("STEP|new_form")
    new_url, new_html = fetch_text(opener, f"{BASE}/my/maintenance-requests/new")
    assert_true("Create Maintenance Request" in new_html, "Create page not loaded")
    csrf_new = extract_csrf(new_html)

    # 3) Create request
    print("STEP|create_post")
    created_url, created_html = fetch_text(
        opener,
        f"{BASE}/my/maintenance-requests/create",
        data={
            "csrf_token": csrf_new,
            "name": request_name,
            "description": "Created by automated end-to-end portal test",
            "equipment_id": "",
            "priority": "2",
            "maintenance_type": "corrective",
        },
    )

    m_id = re.search(r"/my/maintenance-requests/(\d+)", created_url)
    assert_true(bool(m_id), f"Create did not redirect to detail page. URL={created_url}")
    req_id = m_id.group(1)
    assert_true("Internal Discussion" in created_html, "Detail page missing internal discussion block")

    # 4) Update request
    print("STEP|update_post")
    csrf_detail = extract_csrf(created_html)
    updated_url, updated_html = fetch_text(
        opener,
        f"{BASE}/my/maintenance-requests/{req_id}/update",
        data={
            "csrf_token": csrf_detail,
            "name": updated_request_name,
            "description": "Updated by automated end-to-end portal test",
            "equipment_id": "",
            "priority": "3",
            "maintenance_type": "corrective",
        },
    )

    assert_true(f"/my/maintenance-requests/{req_id}" in updated_url, "Update did not stay on detail route")
    assert_true("updated successfully" in updated_html.lower(), "Update success message not found")

    # 5) Verify list page reflects update
    print("STEP|list_verify")
    list_url, list_html = fetch_text(opener, f"{BASE}/my/maintenance-requests")
    assert_true(updated_request_name in list_html, "Updated request name not visible in list")

    print(f"E2E_OK|request_id={req_id}|user={LOGIN}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"E2E_FAIL|{exc}")
        sys.exit(1)
