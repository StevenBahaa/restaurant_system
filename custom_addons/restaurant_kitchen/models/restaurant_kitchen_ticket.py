from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class RestaurantKitchenTicket(models.Model):
    _name = 'restaurant.kitchen.ticket'
    _description = 'Kitchen Ticket'
    _order = 'state, id desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, default='/', readonly=True, copy=False)
    order_id = fields.Many2one('restaurant.kitchen.order', string='Order', required=True, ondelete='cascade', index=True)
    branch_id = fields.Many2one('restaurant.branch', related='order_id.branch_id', store=True, readonly=True, index=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True, index=True)
    station_id = fields.Many2one('restaurant.kitchen.station', string='Station', required=True, ondelete='restrict', index=True, tracking=True)
    
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='waiting', tracking=True)
    
    line_ids = fields.One2many('restaurant.kitchen.ticket.line', 'ticket_id', string='Ticket Lines')
    expected_prep_time = fields.Float(string='Expected Prep Time', readonly=True, default=0.0)
    started_at = fields.Datetime(string='Started At', readonly=True)
    ready_at = fields.Datetime(string='Ready At', readonly=True)
    cancelled_at = fields.Datetime(string='Cancelled At', readonly=True)
    note = fields.Text(string='Note')
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('station_id', 'company_id')
    def _check_station_company(self):
        for ticket in self:
            if ticket.station_id and ticket.company_id and ticket.station_id.company_id:
                if ticket.station_id.company_id != ticket.company_id:
                    raise ValidationError(_("Ticket station company must match ticket company."))

    @api.constrains('station_id', 'branch_id')
    def _check_station_branch(self):
        for ticket in self:
            if ticket.station_id and ticket.branch_id and ticket.station_id.branch_ids:
                if ticket.branch_id.id not in ticket.station_id.branch_ids.ids:
                    raise ValidationError(_("Ticket branch must be within the allowed branches for the selected station."))

    @api.constrains('order_id')
    def _check_order_state(self):
        for ticket in self:
            if ticket.order_id and ticket.order_id.state not in ('confirmed', 'in_preparation', 'ready'):
                raise ValidationError(_("Tickets can only be created for confirmed, in preparation, or ready orders."))

    def _check_branch_operation_access(self):
        """Reuse kitchen order branch access logic."""
        for ticket in self:
            if ticket.order_id:
                ticket.order_id._check_branch_operation_access()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.kitchen.ticket') or '/'
        records = super().create(vals_list)
        return records

class RestaurantKitchenTicketLine(models.Model):
    _name = 'restaurant.kitchen.ticket.line'
    _description = 'Kitchen Ticket Line'
    _order = 'sequence, id'

    ticket_id = fields.Many2one('restaurant.kitchen.ticket', string='Ticket', required=True, ondelete='cascade', index=True)
    order_line_id = fields.Many2one('restaurant.kitchen.order.line', string='Order Line', required=True, ondelete='restrict', index=True)
    order_id = fields.Many2one('restaurant.kitchen.order', related='ticket_id.order_id', store=True, readonly=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', related='order_line_id.product_tmpl_id', store=True, readonly=True)
    branch_id = fields.Many2one('restaurant.branch', related='ticket_id.branch_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', related='ticket_id.company_id', store=True, readonly=True)
    
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    expected_prep_time = fields.Float(string='Expected Prep Time', readonly=True, default=0.0)
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='waiting')
    note = fields.Text(string='Note')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Ticket line quantity must be strictly positive."))

    @api.constrains('order_line_id', 'ticket_id')
    def _check_order_line_consistency(self):
        # Step 6 intentionally requires order lines to be available before ticket line creation.
        # Future routing steps should preserve this invariant.
        for line in self:
            if line.order_line_id and line.ticket_id:
                if line.order_line_id.order_id != line.ticket_id.order_id:
                    raise ValidationError(_("The selected order line belongs to a different order than the ticket's order."))
                if line.order_line_id.availability_status != 'available':
                    raise ValidationError(_("Cannot create a ticket line for an unavailable order line."))
                if line.order_line_id.order_id.state == 'draft':
                    raise ValidationError(_("Cannot create a ticket line for a draft order."))

    def _check_ticket_state_for_changes(self):
        for line in self:
            if line.ticket_id.state != 'waiting':
                raise UserError(_("Ticket lines can only be modified when the ticket is in 'Waiting' state."))

    @api.model_create_multi
    def create(self, vals_list):
        # Validate ticket state before creating ticket lines.
        ticket_ids = [vals.get('ticket_id') for vals in vals_list if vals.get('ticket_id')]
        if ticket_ids:
            tickets = self.env['restaurant.kitchen.ticket'].browse(ticket_ids)
            for ticket in tickets:
                if ticket.state != 'waiting':
                    raise UserError(_("Ticket lines can only be created when the ticket is in 'Waiting' state."))
        return super().create(vals_list)

    def write(self, vals):
        self._check_ticket_state_for_changes()
        # Also check if moving to another ticket, though usually not allowed via UI
        if 'ticket_id' in vals:
            new_ticket = self.env['restaurant.kitchen.ticket'].browse(vals['ticket_id'])
            if new_ticket.state != 'waiting':
                raise UserError(_("Ticket lines can only be moved to a ticket in 'Waiting' state."))
        return super().write(vals)

    def unlink(self):
        self._check_ticket_state_for_changes()
        return super().unlink()
