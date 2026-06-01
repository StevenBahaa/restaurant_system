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
        ('sale_order', 'Sale Order'),
        ('pos_order', 'POS Order')
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

    @api.constrains('source_type')
    def _check_source_type(self):
        for order in self:
            if order.source_type != 'manual_demo':
                raise ValidationError(_("Only Manual Demo source is currently available from this screen. Sales Order and POS Order sources are reserved for future integrations."))

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
                if line.availability_status == 'not_checked':
                    raise UserError(_("Please check availability before confirming this kitchen preparation order."))
                elif line.availability_status == 'unavailable':
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
