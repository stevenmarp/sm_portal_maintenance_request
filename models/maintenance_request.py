from odoo import fields, models


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    _mail_post_access = 'read'

    is_portal_request = fields.Boolean(
        string='Created From Portal',
        default=False,
        copy=False,
        readonly=True,
        index=True,
    )
    portal_user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        copy=False,
        readonly=True,
        index=True,
    )
