from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError

class RestaurantKitchenOrder(models.Model):
    _name = 'restaurant.kitchen.order'
    _description = 'Kitchen Preparation Order'
    _order = 'order_date desc, id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, default='/', readonly=True, copy=False)
    source_type = fields.Selection([
        ('manual_demo', 'Manual Demo'),
    ], string='Source Type', required=True, default='manual_demo')
    source_model = fields.Char(string='Source Model', readonly=True, copy=False)
    source_res_id = fields.Integer(string='Source Record ID', readonly=True, copy=False)
    source_reference = fields.Char(string='Source Reference', readonly=True, copy=False)
    
    partner_id = fields.Many2one('res.partner', string='Customer')
    branch_id = fields.Many2one('restaurant.branch', string='Branch', required=True, index=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    
    order_date = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_preparation', 'In Preparation'),
        ('ready', 'Ready'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='draft', tracking=True)
    
    line_ids = fields.One2many('restaurant.kitchen.order.line', 'order_id', string='Order Lines')
    note = fields.Text(string='Note')
    
    availability_checked = fields.Boolean(string='Availability Checked', default=False)
    last_availability_check_on = fields.Datetime(string='Last Availability Check On', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    available_line_count = fields.Integer(string='Available Lines', compute='_compute_availability_counters')
    unavailable_line_count = fields.Integer(string='Unavailable Lines', compute='_compute_availability_counters')
    not_checked_line_count = fields.Integer(string='Not Checked Lines', compute='_compute_availability_counters')

    ticket_ids = fields.One2many('restaurant.kitchen.ticket', 'order_id', string='Tickets')
    ticket_count = fields.Integer(string='Ticket Count', compute='_compute_ticket_count')
    tickets_generated = fields.Boolean(string='Tickets Generated', default=False)
    tickets_generated_on = fields.Datetime(string='Tickets Generated On', readonly=True)

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        ticket_data = self.env['restaurant.kitchen.ticket']._read_group(
            [('order_id', 'in', self.ids)], ['order_id'], ['__count']
        )
        counts = {order.id: count for order, count in ticket_data}
        for order in self:
            order.ticket_count = counts.get(order.id, 0)

    @api.depends('line_ids.availability_status')
    def _compute_availability_counters(self):
        for order in self:
            order.available_line_count = len(order.line_ids.filtered(lambda l: l.availability_status == 'available'))
            order.unavailable_line_count = len(order.line_ids.filtered(lambda l: l.availability_status == 'unavailable'))
            order.not_checked_line_count = len(order.line_ids.filtered(lambda l: l.availability_status == 'not_checked'))

    @api.constrains('branch_id', 'company_id')
    def _check_branch_company(self):
        for order in self:
            if order.branch_id and order.company_id and order.branch_id.company_id:
                if order.branch_id.company_id != order.company_id:
                    raise ValidationError(_("Order branch company must match order company."))



    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.kitchen.order') or '/'
            
            if vals.get('branch_id'):
                branch = self.env['restaurant.branch'].browse(vals['branch_id'])
                if branch.company_id:
                    vals['company_id'] = branch.company_id.id
        
        records = super().create(vals_list)
        return records

    def write(self, vals):
        if 'branch_id' in vals:
            branch = self.env['restaurant.branch'].browse(vals['branch_id'])
            if branch.company_id:
                vals['company_id'] = branch.company_id.id

        res = super().write(vals)
        return res
        
    def _check_branch_operation_access(self):
        """Check that current user has branch-level access for this record's branch."""
        user = self.env.user
        if user.has_group('base.group_system'):
            return
            
        if user.has_group('restaurant_base.group_restaurant_operations_manager'):
            for record in self:
                if record.branch_id and record.branch_id.company_id and record.branch_id.company_id not in user.company_ids:
                    raise AccessError(_("You can only manage kitchen orders for branches belonging to your allowed companies."))
            return
            
        if not user.has_group('restaurant_base.group_restaurant_branch_manager'):
            raise AccessError(_("You must be a Branch Manager or higher to perform this action."))
            
        for record in self:
            if record.branch_id and user not in record.branch_id.manager_user_ids:
                raise AccessError(_("You can only manage orders for branches you manage."))

    def action_cancel(self):
        self._check_branch_operation_access()
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Cancellation from states other than draft will be handled in future workflow steps."))
        self.write({'state': 'cancelled'})
        
    def action_confirm(self):
        self._check_branch_operation_access()
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Only draft kitchen preparation orders can be confirmed."))
            if not order.branch_id:
                raise UserError(_("Branch is required to confirm the order."))
            if not order.line_ids:
                raise UserError(_("Cannot confirm an order without order lines."))
            if not order.availability_checked:
                raise UserError(_("Please check availability before confirming this kitchen preparation order."))
                
            unavailable_lines = []
            for line in order.line_ids:
                if line.availability_status == 'unavailable':
                    unavailable_lines.append(line)
                    
            if unavailable_lines:
                error_parts = []
                for line in unavailable_lines:
                    reason_code = line.reason_code or 'unknown'
                    reason = line.reason or 'No reason provided'
                    error_parts.append(f"- {line.product_tmpl_id.display_name}: {reason_code} — {reason}")
                error_msg = _("Cannot confirm this order because some lines are unavailable:\n%s") % "\n".join(error_parts)
                raise UserError(error_msg)
                
            order.write({'state': 'confirmed'})

    def _recompute_preparation_state(self):
        for order in self:
            if order.state in ('draft', 'cancelled'):
                continue
            
            if not order.ticket_ids:
                if order.tickets_generated and order.state != 'ready':
                    order.write({'state': 'ready'})
                continue

            all_tickets_done = all(t.state in ('ready', 'cancelled') for t in order.ticket_ids)
            any_ready = any(t.state == 'ready' for t in order.ticket_ids)
            any_in_progress = any(t.state == 'in_progress' for t in order.ticket_ids)
            any_waiting = any(t.state == 'waiting' for t in order.ticket_ids)

            if all_tickets_done and any_ready:
                order.write({'state': 'ready'})
            elif any_in_progress:
                order.write({'state': 'in_preparation'})
            elif any_waiting:
                order.write({'state': 'confirmed'})

    def action_check_availability(self):
        self.ensure_one()
        self._check_branch_operation_access()
        if self.state != 'draft':
            raise UserError(_("Availability can only be checked in draft state."))
        if not self.branch_id:
            raise UserError(_("Branch is required to check availability."))
        if not self.line_ids:
            raise UserError(_("At least one order line is required to check availability."))

        at_datetime = self.order_date or fields.Datetime.now()
        
        for line in self.line_ids:
            try:
                payload = line.product_tmpl_id._get_unified_availability_payload(
                    branch=self.branch_id,
                    at_datetime=at_datetime,
                    quantity=line.quantity,
                    evaluate_all=True,
                )
            except AttributeError:
                raise UserError(_("Missing unified availability resolver method on product.template."))
                
            prep_time = 0.0
            try:
                prep_time = line.product_tmpl_id._get_expected_prep_time(
                    company=self.company_id,
                    branch=self.branch_id,
                )
            except AttributeError:
                pass
                
            line.write({
                'availability_status': 'available' if payload.get('is_available') else 'unavailable',
                'reason_code': payload.get('reason_code'),
                'reason': payload.get('reason'),
                'expected_prep_time': prep_time,
            })
            
        self.write({
            'availability_checked': True,
            'last_availability_check_on': fields.Datetime.now(),
        })

    def action_generate_tickets(self):
        self._check_branch_operation_access()
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_("Only confirmed orders can generate tickets."))
            if not order.availability_checked:
                raise UserError(_("Availability must be checked before generating tickets."))
            if any(line.availability_status != 'available' for line in order.line_ids):
                raise UserError(_("Cannot generate tickets because some lines are not available."))
            if order.tickets_generated or order.ticket_ids:
                raise UserError(_("Tickets have already been generated for this order."))

            tickets_by_station = {}
            tickets_created = 0

            for line in order.line_ids:
                station_lines = line.product_tmpl_id._get_active_kitchen_station_lines(
                    company=order.company_id,
                    branch=order.branch_id,
                )

                if station_lines:
                    for s_line in station_lines:
                        station = s_line.station_id
                        if station.id not in tickets_by_station:
                            ticket = self.env['restaurant.kitchen.ticket'].create({
                                'order_id': order.id,
                                'station_id': station.id,
                            })
                            tickets_by_station[station.id] = ticket
                            tickets_created += 1
                        
                        ticket = tickets_by_station[station.id]
                        
                        self.env['restaurant.kitchen.ticket.line'].create({
                            'ticket_id': ticket.id,
                            'order_line_id': line.id,
                            'quantity': line.quantity,
                            'expected_prep_time': s_line.expected_prep_time or line.expected_prep_time,
                            'sequence': s_line.sequence,
                            'note': line.note,
                        })
                    
                    line.write({
                        'routing_status': 'routed',
                        'routing_note': False,
                    })
                else:
                    note = _("No kitchen station assignment is required for this item.")
                    if line.product_tmpl_id.restaurant_product_type == 'combo':
                        note = _("Combo component routing is deferred to a future UC.")
                    
                    line.write({
                        'routing_status': 'no_station_required',
                        'routing_note': note,
                    })
            
            for ticket in tickets_by_station.values():
                prep_times = ticket.line_ids.mapped('expected_prep_time')
                ticket.expected_prep_time = max(prep_times) if prep_times else 0.0

            if tickets_created > 0:
                order.write({
                    'tickets_generated': True,
                    'tickets_generated_on': fields.Datetime.now(),
                })
            else:
                order.write({
                    'state': 'ready',
                    'tickets_generated': True,
                    'tickets_generated_on': fields.Datetime.now(),
                })

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': _('Kitchen Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'restaurant.kitchen.ticket',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }
