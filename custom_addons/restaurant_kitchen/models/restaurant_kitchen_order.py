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
                raise ValidationError(_("sale_order and pos_order are reserved for future integrations and cannot be used in manual UC-E Step 2 creation."))

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
        raise UserError(_("Confirm is not implemented yet."))
