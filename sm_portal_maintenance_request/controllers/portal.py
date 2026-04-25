from collections import OrderedDict
from itertools import groupby as itertools_groupby

from odoo import _, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class PortalMaintenanceRequest(CustomerPortal):

    def _portal_request_domain(self):
        return [
            ('is_portal_request', '=', True),
            ('portal_user_id', '=', request.env.user.id),
        ]

    def _portal_equipment_domain(self):
        company_id = request.env.company.id
        return ['|', ('company_id', '=', False), ('company_id', '=', company_id)]

    def _can_edit_request(self, maintenance_request):
        return (
            bool(maintenance_request)
            and not maintenance_request.archive
            and not maintenance_request.sudo().stage_id.done
        )

    def _format_portal_form_error(self, err, fallback):
        message = str(err) if err else ''
        return message or fallback

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'maintenance_request_count' in counters:
            maintenance_request = request.env['maintenance.request']
            values['maintenance_request_count'] = maintenance_request.search_count(
                self._portal_request_domain()
            ) if maintenance_request.has_access('read') else 0
        return values

    def _maintenance_sortings(self):
        return OrderedDict([
            ('date', {'label': _('Newest'), 'order': 'request_date desc, id desc'}),
            ('name', {'label': _('Subject'), 'order': 'name asc'}),
            ('stage', {'label': _('Stage'), 'order': 'stage_id asc'}),
            ('priority', {'label': _('Priority'), 'order': 'priority desc, id desc'}),
        ])

    def _maintenance_filters(self):
        return OrderedDict([
            ('all', {'label': _('All'), 'domain': []}),
            ('open', {'label': _('Open'), 'domain': [('archive', '=', False), ('stage_id.done', '=', False)]}),
            ('done', {'label': _('Done'), 'domain': [('archive', '=', False), ('stage_id.done', '=', True)]}),
            ('cancelled', {'label': _('Cancelled'), 'domain': [('archive', '=', True)]}),
        ])

    def _maintenance_groupby(self):
        return OrderedDict([
            ('none', {'label': _('None'), 'field': False}),
            ('stage', {'label': _('Stage'), 'field': 'stage_id'}),
            ('priority', {'label': _('Priority'), 'field': 'priority'}),
            ('maintenance_type', {'label': _('Type'), 'field': 'maintenance_type'}),
        ])

    def _maintenance_search_inputs(self):
        return OrderedDict([
            ('all', {'input': 'all', 'label': _('Search in All')}),
            ('name', {'input': 'name', 'label': _('Search in Subject')}),
            ('description', {'input': 'description', 'label': _('Search in Description')}),
            ('equipment', {'input': 'equipment', 'label': _('Search in Equipment')}),
        ])

    def _maintenance_search_domain(self, search_in, search):
        if search_in == 'name':
            return [('name', 'ilike', search)]
        if search_in == 'description':
            return [('description', 'ilike', search)]
        if search_in == 'equipment':
            return [('equipment_id.name', 'ilike', search)]
        return ['|', '|', ('name', 'ilike', search), ('description', 'ilike', search), ('equipment_id.name', 'ilike', search)]

    def _priority_options(self):
        return request.env['maintenance.request']._fields['priority']._description_selection(request.env)

    def _maintenance_type_options(self):
        return request.env['maintenance.request']._fields['maintenance_type']._description_selection(request.env)

    def _priority_label_map(self):
        return OrderedDict((key, label) for key, label in self._priority_options())

    def _maintenance_type_label_map(self):
        return OrderedDict((key, label) for key, label in self._maintenance_type_options())

    def _group_requests(self, maintenance_requests, groupby_key):
        if groupby_key == 'none':
            return [{'label': False, 'records': maintenance_requests}]

        priority_map = self._priority_label_map()
        maintenance_type_map = self._maintenance_type_label_map()

        if groupby_key == 'stage':
            key_func = lambda rec: rec.sudo().stage_id.display_name or _('No Stage')
        elif groupby_key == 'priority':
            key_func = lambda rec: priority_map.get(rec.priority or '0', _('No Priority'))
        elif groupby_key == 'maintenance_type':
            key_func = lambda rec: maintenance_type_map.get(rec.maintenance_type, _('No Type'))
        else:
            return [{'label': False, 'records': maintenance_requests}]

        grouped = []
        for label, records in itertools_groupby(maintenance_requests, key=key_func):
            grouped.append({'label': label, 'records': list(records)})
        return grouped

    def _prepare_form_values(self, values, maintenance_request=None, form_data=None, form_errors=None):
        data = {
            'name': '',
            'description': '',
            'equipment_id': False,
            'priority': '2',
            'maintenance_type': 'corrective',
        }

        if maintenance_request:
            maintenance_request_sudo = maintenance_request.sudo()
            data.update({
                'name': maintenance_request.name or '',
                'description': maintenance_request.description or '',
                'equipment_id': maintenance_request_sudo.equipment_id.id or False,
                'priority': maintenance_request.priority or '2',
                'maintenance_type': maintenance_request.maintenance_type or 'corrective',
            })

        if form_data:
            data.update(form_data)

        values.update({
            'form_data': data,
            'form_errors': form_errors or [],
            'equipment_options': request.env['maintenance.equipment'].sudo().search(
                self._portal_equipment_domain(), order='name asc'
            ),
            'priority_options': self._priority_options(),
            'maintenance_type_options': self._maintenance_type_options(),
        })
        return values

    def _extract_form_values(self, post):
        equipment_input = (post.get('equipment_id') or '').strip()
        form_data = {
            'name': (post.get('name') or '').strip(),
            'description': (post.get('description') or '').strip(),
            'equipment_id': equipment_input,
            'priority': (post.get('priority') or '').strip(),
            'maintenance_type': (post.get('maintenance_type') or '').strip(),
        }

        values = {}
        errors = []

        if not form_data['name']:
            errors.append(_('Subject is required.'))
        else:
            values['name'] = form_data['name']

        values['description'] = form_data['description']

        priority_map = self._priority_label_map()
        default_priority = '2' if '2' in priority_map else next(iter(priority_map), '0')
        priority_value = form_data['priority'] or default_priority
        if priority_value not in priority_map:
            errors.append(_('Invalid priority selected.'))
            priority_value = default_priority
            form_data['priority'] = priority_value
        values['priority'] = priority_value

        maintenance_type_map = self._maintenance_type_label_map()
        default_type = 'corrective' if 'corrective' in maintenance_type_map else next(iter(maintenance_type_map), '')
        maintenance_type_value = form_data['maintenance_type'] or default_type
        if maintenance_type_value not in maintenance_type_map:
            errors.append(_('Invalid maintenance type selected.'))
            maintenance_type_value = default_type
            form_data['maintenance_type'] = maintenance_type_value
        values['maintenance_type'] = maintenance_type_value

        equipment_value = False
        if equipment_input:
            try:
                equipment_id = int(equipment_input)
            except (TypeError, ValueError):
                errors.append(_('Invalid equipment selected.'))
            else:
                equipment = request.env['maintenance.equipment'].sudo().search(
                    [('id', '=', equipment_id)] + self._portal_equipment_domain(),
                    limit=1,
                )
                if not equipment:
                    errors.append(_('Selected equipment is not available.'))
                else:
                    equipment_value = equipment.id
                    form_data['equipment_id'] = equipment.id
        else:
            form_data['equipment_id'] = False
        values['equipment_id'] = equipment_value

        return form_data, values, errors

    def _get_portal_request(self, maintenance_request_id):
        return request.env['maintenance.request'].search(
            self._portal_request_domain() + [('id', '=', maintenance_request_id)],
            limit=1,
        )

    @http.route(
        ['/my/maintenance-requests', '/my/maintenance-requests/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_maintenance_requests(
        self, page=1, sortby=None, filterby=None, groupby=None,
        search=None, search_in='all', **kw
    ):
        maintenance_request = request.env['maintenance.request']
        if not maintenance_request.has_access('read'):
            return request.redirect('/my')

        sortings = self._maintenance_sortings()
        filters = self._maintenance_filters()
        groupings = self._maintenance_groupby()
        search_inputs = self._maintenance_search_inputs()

        sortby = sortby if sortby in sortings else 'date'
        filterby = filterby if filterby in filters else 'all'
        groupby = groupby if groupby in groupings else 'none'
        search_in = search_in if search_in in search_inputs else 'all'

        domain = list(self._portal_request_domain()) + list(filters[filterby]['domain'])
        if search:
            domain += self._maintenance_search_domain(search_in, search)

        sort_order = sortings[sortby]['order']
        group_field = groupings[groupby]['field']
        order = '%s, %s' % (group_field, sort_order) if group_field else sort_order

        request_count = maintenance_request.search_count(domain)
        pager = portal_pager(
            url='/my/maintenance-requests',
            total=request_count,
            page=page,
            step=self._items_per_page,
            url_args={
                'sortby': sortby,
                'filterby': filterby,
                'groupby': groupby,
                'search': search,
                'search_in': search_in,
            },
        )

        maintenance_requests = maintenance_request.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset'],
        )
        request.session['my_maintenance_requests_history'] = maintenance_requests.ids[:100]

        values = self._prepare_portal_layout_values()
        values.update({
            'maintenance_requests': maintenance_requests,
            'grouped_requests': self._group_requests(maintenance_requests, groupby),
            'page_name': 'maintenance_requests',
            'default_url': '/my/maintenance-requests',
            'pager': pager,
            'searchbar_sortings': sortings,
            'searchbar_filters': filters,
            'searchbar_groupby': groupings,
            'searchbar_inputs': search_inputs,
            'sortby': sortby,
            'filterby': filterby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search or '',
            'priority_label_map': self._priority_label_map(),
            'maintenance_type_label_map': self._maintenance_type_label_map(),
        })
        return request.render(
            'sm_portal_maintenance_request.portal_my_maintenance_requests', values
        )

    @http.route('/my/maintenance-requests/new', type='http', auth='user', website=True)
    def portal_maintenance_request_new(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update({'page_name': 'maintenance_request_new'})
        self._prepare_form_values(values)
        return request.render(
            'sm_portal_maintenance_request.portal_maintenance_request_create', values
        )

    @http.route(
        '/my/maintenance-requests/create',
        type='http', auth='user', website=True, methods=['POST'], csrf=True,
    )
    def portal_maintenance_request_create(self, **post):
        form_data, create_vals, form_errors = self._extract_form_values(post)

        if form_errors:
            values = self._prepare_portal_layout_values()
            values.update({'page_name': 'maintenance_request_new'})
            self._prepare_form_values(values, form_data=form_data, form_errors=form_errors)
            return request.render(
                'sm_portal_maintenance_request.portal_maintenance_request_create', values
            )

        create_vals.update({
            'portal_user_id': request.env.user.id,
            'company_id': request.env.company.id,
            'is_portal_request': True,
        })
        try:
            maintenance_request = request.env['maintenance.request'].sudo().create(create_vals)
            maintenance_request.message_subscribe(partner_ids=[request.env.user.partner_id.id])
        except (AccessError, UserError, ValidationError) as err:
            form_errors.append(
                self._format_portal_form_error(
                    err,
                    _('Unable to create the maintenance request. Please check your input and try again.'),
                )
            )
            values = self._prepare_portal_layout_values()
            values.update({'page_name': 'maintenance_request_new'})
            self._prepare_form_values(values, form_data=form_data, form_errors=form_errors)
            return request.render(
                'sm_portal_maintenance_request.portal_maintenance_request_create', values
            )

        return request.redirect(
            '/my/maintenance-requests/%s?success=created' % maintenance_request.id
        )

    @http.route(
        '/my/maintenance-requests/<int:maintenance_request_id>',
        type='http', auth='user', website=True,
    )
    def portal_maintenance_request_page(self, maintenance_request_id, **kw):
        maintenance_request = self._get_portal_request(maintenance_request_id)
        if not maintenance_request:
            return request.redirect('/my/maintenance-requests')

        can_edit = self._can_edit_request(maintenance_request)

        values = self._prepare_portal_layout_values()
        values.update({
            'maintenance_request': maintenance_request,
            'page_name': 'maintenance_request',
            'can_edit_request': can_edit,
            'priority_label_map': self._priority_label_map(),
            'maintenance_type_label_map': self._maintenance_type_label_map(),
            'success_message': (
                _('Maintenance request created successfully.')
                if kw.get('success') == 'created'
                else _('Maintenance request updated successfully.')
                if kw.get('success') == 'updated'
                else False
            ),
        })
        self._prepare_form_values(values, maintenance_request=maintenance_request)

        values = self._get_page_view_values(
            maintenance_request,
            None,
            values,
            'my_maintenance_requests_history',
            False,
            **kw
        )
        return request.render(
            'sm_portal_maintenance_request.portal_maintenance_request_page', values
        )

    @http.route(
        '/my/maintenance-requests/<int:maintenance_request_id>/update',
        type='http', auth='user', website=True, methods=['POST'], csrf=True,
    )
    def portal_maintenance_request_update(self, maintenance_request_id, **post):
        maintenance_request = self._get_portal_request(maintenance_request_id)
        if not maintenance_request:
            return request.redirect('/my/maintenance-requests')

        if not self._can_edit_request(maintenance_request):
            return request.redirect('/my/maintenance-requests/%s' % maintenance_request.id)

        form_data, write_vals, form_errors = self._extract_form_values(post)
        if form_errors:
            values = self._prepare_portal_layout_values()
            values.update({
                'maintenance_request': maintenance_request,
                'page_name': 'maintenance_request',
                'can_edit_request': True,
                'priority_label_map': self._priority_label_map(),
                'maintenance_type_label_map': self._maintenance_type_label_map(),
            })
            self._prepare_form_values(
                values,
                maintenance_request=maintenance_request,
                form_data=form_data,
                form_errors=form_errors,
            )
            values = self._get_page_view_values(
                maintenance_request,
                None,
                values,
                'my_maintenance_requests_history',
                False,
            )
            return request.render(
                'sm_portal_maintenance_request.portal_maintenance_request_page', values
            )

        try:
            maintenance_request.sudo().write(write_vals)
        except (AccessError, UserError, ValidationError) as err:
            form_errors = [
                self._format_portal_form_error(
                    err,
                    _('Unable to update the maintenance request. Please check your input and try again.'),
                )
            ]
            values = self._prepare_portal_layout_values()
            values.update({
                'maintenance_request': maintenance_request,
                'page_name': 'maintenance_request',
                'can_edit_request': True,
                'priority_label_map': self._priority_label_map(),
                'maintenance_type_label_map': self._maintenance_type_label_map(),
            })
            self._prepare_form_values(
                values,
                maintenance_request=maintenance_request,
                form_data=form_data,
                form_errors=form_errors,
            )
            values = self._get_page_view_values(
                maintenance_request,
                None,
                values,
                'my_maintenance_requests_history',
                False,
            )
            return request.render(
                'sm_portal_maintenance_request.portal_maintenance_request_page', values
            )
        return request.redirect('/my/maintenance-requests/%s?success=updated' % maintenance_request.id)
