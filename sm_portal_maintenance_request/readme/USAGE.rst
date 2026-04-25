Creating a Request
~~~~~~~~~~~~~~~~~~

1. Log in as a portal user.
2. Go to **My Account → Maintenance Requests**.
3. Click **New Request**.
4. Fill in the form: subject, equipment (optional), type, priority, and description.
5. Click **Submit Request**.

Viewing & Tracking Requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The list view shows all your submitted requests with search, sort, filter, and group-by.
- Click any request to view its details: stage, priority, equipment, and description.
- Status badges show **Open**, **Done**, or **Cancelled** at a glance.

Updating a Request
~~~~~~~~~~~~~~~~~~

1. Open an existing request that is still **Open** (not done or cancelled).
2. Click **Update This Request** to expand the edit form.
3. Modify any field and click **Save Changes**.

Discussion Thread
~~~~~~~~~~~~~~~~~

- Each request detail page includes a chatter / message thread.
- Portal users can post messages and internal users can reply from the backend.

Optional E2E Smoke Test
~~~~~~~~~~~~~~~~~~~~~~~

Use the smoke script in ``tests/e2e`` to verify login, create, update, and list flows.

Required environment variables:

- ``SM_PM_LOGIN``
- ``SM_PM_PASSWORD``

Optional environment variables (defaults shown):

- ``SM_PM_BASE_URL`` (default: ``http://127.0.0.1:8019``)
- ``SM_PM_DB`` (default: ``odoo_19``)

Example run:

.. code-block:: bash

   export SM_PM_LOGIN='portal.e2e@example.com'
   export SM_PM_PASSWORD='your-password'
   export SM_PM_BASE_URL='http://127.0.0.1:8019'
   export SM_PM_DB='odoo_19'
   python3 sm_portal_maintenance_request/tests/e2e/portal_maintenance_smoke.py
