from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class RestaurantKitchenOrderLine(models.Model):
    _name = 'restaurant.kitchen.order.line'
    _description = 'Kitchen Preparation Order Line'
    _order = 'sequence, id'

    order_id = fields.Many2one('restaurant.kitchen.order', string='Order', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, index=True)
    
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    branch_id = fields.Many2one('restaurant.branch', related='order_id.branch_id', store=True, readonly=True)
    
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    expected_prep_time = fields.Float(string='Expected Prep Time', readonly=True, default=0.0)
    
    availability_status = fields.Selection([
        ('not_checked', 'Not Checked'),
        ('available', 'Available'),
        ('unavailable', 'Unavailable')
    ], string='Availability Status', required=True, default='not_checked')
    
    reason_code = fields.Char(string='Reason Code', readonly=True)
    reason = fields.Text(string='Reason', readonly=True)
    
    routing_status = fields.Selection([
        ('not_routed', 'Not Routed'),
        ('routed', 'Routed'),
        ('no_station_required', 'No Station Required')
    ], string='Routing Status', required=True, default='not_routed')
    
    routing_note = fields.Char(string='Routing Note')
    note = fields.Text(string='Note')
    sequence = fields.Integer(string='Sequence', default=10)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Order lines quantity must be > 0."))

    @api.constrains('product_tmpl_id', 'company_id')
    def _check_product_validity(self):
        for line in self:
            product = line.product_tmpl_id
            if not product.active:
                raise ValidationError(_("Product must be active."))
            if not product.is_menu_item:
                raise ValidationError(_("Product must be a menu item."))
            if product.restaurant_product_type not in ['prepared_meal', 'beverage', 'ready_item', 'combo']:
                raise ValidationError(_("Product must be a prepared meal, beverage, ready item, or combo."))
            if product.company_id and line.company_id and product.company_id != line.company_id:
                raise ValidationError(_("Company-specific products must match the order company."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'order_id' in vals:
                order = self.env['restaurant.kitchen.order'].browse(vals['order_id'])
                if order.state != 'draft':
                    raise ValidationError(_("Order lines can only be created when the order is in draft state."))
                vals.update({
                    'availability_status': 'not_checked',
                    'reason_code': False,
                    'reason': False,
                    'expected_prep_time': 0.0,
                })
        
        records = super().create(vals_list)
        
        draft_orders = records.mapped('order_id').filtered(lambda o: o.state == 'draft')
        draft_orders.write({
            'availability_checked': False,
            'last_availability_check_on': False,
        })
        return records

    def write(self, vals):
        # Only routing fields may be updated on confirmed order lines.
        # These fields are set by action_generate_tickets() after confirmation.
        allowed_fields = {'routing_status', 'routing_note'}
        is_only_routing = all(k in allowed_fields for k in vals.keys())
        for line in self:
            if line.order_id.state != 'draft' and not is_only_routing:
                raise ValidationError(_("Order lines can only be modified when the order is in draft state."))
                
        write_vals = dict(vals)
        needs_reset = 'product_tmpl_id' in vals or 'quantity' in vals
        if needs_reset:
            write_vals.update({
                'availability_status': 'not_checked',
                'reason_code': False,
                'reason': False,
                'expected_prep_time': 0.0,
                'routing_status': 'not_routed',
                'routing_note': False,
            })
            
        res = super().write(write_vals)
        
        if needs_reset:
            draft_orders = self.mapped('order_id').filtered(lambda o: o.state == 'draft')
            draft_orders.write({
                'availability_checked': False,
                'last_availability_check_on': False,
            })
        return res

    def unlink(self):
        non_draft_lines = self.filtered(lambda l: l.order_id.state != 'draft')
        if non_draft_lines:
            raise ValidationError(_("Order lines can only be deleted when the order is in draft state."))
            
        draft_orders = self.mapped('order_id')
        res = super().unlink()
        
        draft_orders.write({
            'availability_checked': False,
            'last_availability_check_on': False,
        })
        return res
