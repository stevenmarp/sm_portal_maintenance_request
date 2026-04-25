# -*- coding: utf-8 -*-
{
    'name': 'Portal Maintenance Request',
    'version': '19.0.1.1.0',
    'category': 'Portal',
    'summary': 'Allow portal users to create, track, update, and discuss maintenance requests.',
    'description': """
Portal Maintenance Request
==========================

Let portal users create, view, update, and discuss their own maintenance
requests directly from the customer portal — no backend access needed.

**Key Features:**
- Portal dashboard with maintenance request counter
- Create maintenance requests from portal
- List view with search, sort, filter, and group by
- View request details with status badges
- Update previously created requests from portal
- Internal discussion thread through portal chatter
- Backend visibility with "Portal Requests" filter
- Portal requester tracking with automatic follower subscription
- Record-level security: users see only their own requests
- Server-side form validation for priority, type, and equipment
- Multi-company equipment visibility rules
- Breadcrumb and previous/next portal navigation
    """,
    'author': 'Steven Marp',
    'depends': ['maintenance', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/maintenance_views.xml',
        'views/portal_templates.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 39.13,
    'currency': 'USD',
}
