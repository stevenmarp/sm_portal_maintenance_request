import re
from urllib.parse import urlparse

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.http import Request
from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestPortalMaintenanceRequest(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_main = cls.env.ref('base.main_company')
        cls.company_other = cls.env['res.company'].create({
            'name': 'Portal Maintenance Other Company',
        })

        cls.portal_login_a = 'portal_pm_a'
        cls.portal_password_a = 'portal_pm_a'
        cls.portal_user_a = mail_new_test_user(
            cls.env,
            login=cls.portal_login_a,
            password=cls.portal_password_a,
            groups='base.group_portal',
            company_id=cls.company_main.id,
            email='portal_pm_a@example.com',
            name='Portal Maintenance A',
        )

        cls.portal_login_b = 'portal_pm_b'
        cls.portal_password_b = 'portal_pm_b'
        cls.portal_user_b = mail_new_test_user(
            cls.env,
            login=cls.portal_login_b,
            password=cls.portal_password_b,
            groups='base.group_portal',
            company_id=cls.company_main.id,
            email='portal_pm_b@example.com',
            name='Portal Maintenance B',
        )

        cls.equipment_main = cls.env['maintenance.equipment'].sudo().create({
            'name': 'Portal Main Company Equipment',
            'company_id': cls.company_main.id,
        })
        cls.equipment_other = cls.env['maintenance.equipment'].sudo().create({
            'name': 'Portal Other Company Equipment',
            'company_id': cls.company_other.id,
        })

        cls.done_stage = cls.env['maintenance.stage'].search([('done', '=', True)], limit=1)
        if not cls.done_stage:
            cls.done_stage = cls.env['maintenance.stage'].create({
                'name': 'Done',
                'done': True,
            })

    def _csrf_token(self):
        return Request.csrf_token(self)

    def _create_request_via_portal(self, name, equipment_id=''):
        response = self.url_open(
            '/my/maintenance-requests/create',
            data={
                'csrf_token': self._csrf_token(),
                'name': name,
                'description': 'Created by portal maintenance HttpCase test',
                'equipment_id': equipment_id,
                'priority': '2',
                'maintenance_type': 'corrective',
            },
        )
        match = re.search(r'/my/maintenance-requests/(\d+)', response.url or '')
        self.assertTrue(match, f'Create route did not redirect to request detail. URL={response.url}')

        maintenance_request = self.env['maintenance.request'].sudo().browse(int(match.group(1)))
        self.assertTrue(maintenance_request.exists(), 'Created maintenance request does not exist')
        return maintenance_request, response

    def test_portal_home_shows_maintenance_requests_entry(self):
        self.authenticate(self.portal_login_a, self.portal_password_a)

        response = self.url_open('/my')

        self.assertEqual(response.status_code, 200)
        self.assertIn('/my/maintenance-requests', response.text)

    def test_create_request_sets_portal_fields(self):
        self.authenticate(self.portal_login_a, self.portal_password_a)

        maintenance_request, response = self._create_request_via_portal(
            'Portal Create Request Test',
            equipment_id=str(self.equipment_main.id),
        )

        self.assertTrue(maintenance_request.is_portal_request)
        self.assertEqual(maintenance_request.portal_user_id, self.portal_user_a)
        self.assertEqual(maintenance_request.company_id, self.company_main)
        self.assertEqual(maintenance_request.equipment_id, self.equipment_main)
        self.assertIn('Internal Discussion', response.text)

    def test_update_request_while_open(self):
        self.authenticate(self.portal_login_a, self.portal_password_a)

        maintenance_request, _response = self._create_request_via_portal('Portal Update Open Request Test')

        response = self.url_open(
            f'/my/maintenance-requests/{maintenance_request.id}/update',
            data={
                'csrf_token': self._csrf_token(),
                'name': 'Portal Updated Open Request Name',
                'description': 'Updated from portal maintenance HttpCase test',
                'equipment_id': '',
                'priority': '3',
                'maintenance_type': 'corrective',
            },
        )

        maintenance_request.invalidate_recordset()
        self.assertIn(f'/my/maintenance-requests/{maintenance_request.id}', response.url)
        self.assertEqual(maintenance_request.name, 'Portal Updated Open Request Name')
        self.assertEqual(maintenance_request.priority, '3')

    def test_update_rejected_for_done_or_cancelled_requests(self):
        self.authenticate(self.portal_login_a, self.portal_password_a)

        done_request, _response = self._create_request_via_portal('Portal Done Request Update Block Test')
        done_original_name = done_request.name
        done_request.write({'stage_id': self.done_stage.id})

        done_response = self.url_open(
            f'/my/maintenance-requests/{done_request.id}/update',
            data={
                'csrf_token': self._csrf_token(),
                'name': 'Should Not Update Done Request',
                'description': 'This update should be rejected',
                'equipment_id': '',
                'priority': '1',
                'maintenance_type': 'preventive',
            },
        )

        done_request.invalidate_recordset()
        self.assertIn(f'/my/maintenance-requests/{done_request.id}', done_response.url)
        self.assertEqual(done_request.name, done_original_name)

        cancelled_request, _response = self._create_request_via_portal('Portal Cancelled Request Update Block Test')
        cancelled_original_name = cancelled_request.name
        cancelled_request.write({'archive': True})

        cancelled_response = self.url_open(
            f'/my/maintenance-requests/{cancelled_request.id}/update',
            data={
                'csrf_token': self._csrf_token(),
                'name': 'Should Not Update Cancelled Request',
                'description': 'This update should be rejected',
                'equipment_id': '',
                'priority': '1',
                'maintenance_type': 'preventive',
            },
        )

        cancelled_request.invalidate_recordset()
        self.assertIn(f'/my/maintenance-requests/{cancelled_request.id}', cancelled_response.url)
        self.assertEqual(cancelled_request.name, cancelled_original_name)

    def test_user_cannot_access_other_user_request(self):
        foreign_request = self.env['maintenance.request'].sudo().create({
            'name': 'Portal Foreign Request Access Test',
            'is_portal_request': True,
            'portal_user_id': self.portal_user_b.id,
            'company_id': self.company_main.id,
        })

        self.authenticate(self.portal_login_a, self.portal_password_a)

        response = self.url_open(f'/my/maintenance-requests/{foreign_request.id}')
        response_path = urlparse(response.url).path.rstrip('/')

        self.assertEqual(response_path, '/my/maintenance-requests')
        self.assertNotIn('Portal Foreign Request Access Test', response.text)

    def test_cross_company_equipment_hidden_and_rejected(self):
        self.authenticate(self.portal_login_a, self.portal_password_a)

        new_form_response = self.url_open('/my/maintenance-requests/new')
        self.assertIn(self.equipment_main.display_name, new_form_response.text)
        self.assertNotIn(self.equipment_other.display_name, new_form_response.text)

        blocked_name = 'Portal Cross Company Equipment Block Test'
        create_response = self.url_open(
            '/my/maintenance-requests/create',
            data={
                'csrf_token': self._csrf_token(),
                'name': blocked_name,
                'description': 'Attempt to force equipment from another company',
                'equipment_id': str(self.equipment_other.id),
                'priority': '2',
                'maintenance_type': 'corrective',
            },
        )

        create_path = urlparse(create_response.url).path
        blocked_request = self.env['maintenance.request'].sudo().search([
            ('name', '=', blocked_name),
            ('is_portal_request', '=', True),
            ('portal_user_id', '=', self.portal_user_a.id),
        ])

        self.assertEqual(create_path, '/my/maintenance-requests/create')
        self.assertIn('Selected equipment is not available.', create_response.text)
        self.assertFalse(blocked_request)
