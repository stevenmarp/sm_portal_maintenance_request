19.0.1.1.0 (2026-04-24)
~~~~~~~~~~~~~~~~~~~~~~~

* Hardened portal create/update routes with explicit validation/access error handling.
* Restricted equipment selection in portal forms to current active company (and shared equipment).
* Centralized request editability guard for consistent behavior across detail/update routes.
* Added Odoo HttpCase post-install tests for portal flow and security edge cases.
* Added optional E2E smoke script under ``tests/e2e`` with environment-based credentials.

19.0.1.0.0 (2026-04-23)
~~~~~~~~~~~~~~~~~~~~~~~

* Initial release.
* Portal dashboard with request counter.
* Create, view, update maintenance requests from portal.
* List view with search, sort, filter, group by.
* Discussion thread (chatter) on request detail.
* Backend visibility with "Portal Requests" filter.
* Record-level security: portal users see only own requests.
