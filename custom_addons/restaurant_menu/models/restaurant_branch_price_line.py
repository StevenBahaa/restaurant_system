# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError

class RestaurantBranchPriceLine(models.Model):
    _name = 'restaurant.branch.price.line'
    _description = 'Branch and Channel Price Rule'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        domain="[('is_menu_item', '=', True)]"
    )
    branch_id = fields.Many2one(
        'restaurant.branch',
        string='Branch'
    )
    channel = fields.Selection(
        [
            ('dine_in', 'Dine-In'),
            ('takeaway', 'Takeaway'),
            ('delivery_app', 'Delivery App'),
        ],
        string='Channel'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    price = fields.Monetary(
        string='Price',
        required=True,
        currency_field='currency_id'
    )
    date_from = fields.Date(
        string='Start Date'
    )
    date_until = fields.Date(
        string='End Date'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    note = fields.Text(
        string='Internal Note'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    allowed_branch_ids = fields.Many2many(
        'restaurant.branch',
        compute='_compute_allowed_branch_ids'
    )
    cost_reference = fields.Monetary(
        string='Cost Reference',
        compute='_compute_below_cost_fields',
        currency_field='currency_id'
    )
    is_below_cost = fields.Boolean(
        string='Is Below Cost',
        compute='_compute_below_cost_fields'
    )
    below_cost_warning_message = fields.Char(
        string='Warning Message',
        compute='_compute_below_cost_fields'
    )

    @api.depends('price', 'product_tmpl_id', 'product_tmpl_id.standard_price')
    def _compute_below_cost_fields(self):
        for record in self:
            cost = 0.0
            product = record.product_tmpl_id
            if product:
                has_recipe = getattr(product, 'has_approved_recipe', False)
                recipe_cost = getattr(product, 'recipe_cost', 0.0)
                if has_recipe:
                    cost = recipe_cost
                else:
                    cost = product.standard_price

            record.cost_reference = cost
            if cost > 0 and record.price < cost:
                record.is_below_cost = True
                record.below_cost_warning_message = "Price is below current cost."
            else:
                record.is_below_cost = False
                record.below_cost_warning_message = ""

    @api.depends('product_tmpl_id.company_id')
    def _compute_allowed_branch_ids(self):
        for record in self:
            domain = [('active', '=', True)]
            if record.product_tmpl_id and record.product_tmpl_id.company_id:
                domain.append(('company_id', 'in', [False, record.product_tmpl_id.company_id.id]))
            record.allowed_branch_ids = self.env['restaurant.branch'].search(domain)

    def _check_pricing_permissions(self):
        if self.env.su:
            return
        if not (self.env.user.has_group('restaurant_base.group_restaurant_operations_manager') or
                self.env.user.has_group('restaurant_menu.group_restaurant_pricing_manager')):
            raise AccessError("You do not have permission to modify branch/channel pricing.")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_pricing_permissions()
        for vals in vals_list:
            branch_id = vals.get('branch_id')
            product_tmpl_id = vals.get('product_tmpl_id')
            branch = self.env['restaurant.branch'].browse(branch_id) if branch_id else self.env['restaurant.branch']
            product_tmpl = self.env['product.template'].browse(product_tmpl_id) if product_tmpl_id else self.env['product.template']
            
            vals['company_id'] = (
                branch.company_id.id or 
                product_tmpl.company_id.id or 
                vals.get('company_id') or 
                self.env.company.id
            )
        
        records = super().create(vals_list)
        
        for record in records:
            company_id = record.company_id.id or self.env.company.id
            currency_id = record.currency_id.id or record.company_id.currency_id.id or self.env.company.currency_id.id
            history_vals = {
                'product_tmpl_id': record.product_tmpl_id.id,
                'price_line_id': record.id,
                'branch_id': record.branch_id.id,
                'channel': record.channel,
                'new_price': record.price,
                'new_date_from': record.date_from,
                'new_date_until': record.date_until,
                'new_active': record.active,
                'company_id': company_id,
                'currency_id': currency_id,
                'changed_by_id': self.env.user.id,
                'changed_on': fields.Datetime.now(),
                'change_summary': 'Created branch/channel price rule.',
            }
            self.env['restaurant.branch.price.history'].sudo().create(history_vals)
            
        return records

    def write(self, vals):
        self._check_pricing_permissions()
        
        # If there are changes to branch_id or product_tmpl_id, we determine company_id dynamically.
        # If self has multiple records, we check if they would get different company_ids.
        # If they do, we write to each record individually to trigger correct history and company setup.
        if 'branch_id' in vals or 'product_tmpl_id' in vals:
            if len(self) > 1:
                # Check if companies would differ
                companies = {}
                for record in self:
                    branch_id = vals.get('branch_id', record.branch_id.id)
                    product_tmpl_id = vals.get('product_tmpl_id', record.product_tmpl_id.id)
                    branch = self.env['restaurant.branch'].browse(branch_id) if branch_id else self.env['restaurant.branch']
                    product_tmpl = self.env['product.template'].browse(product_tmpl_id) if product_tmpl_id else self.env['product.template']
                    
                    company = (
                        branch.company_id.id or
                        product_tmpl.company_id.id or
                        self.env.company.id
                    )
                    companies[record.id] = company
                
                # If they are all the same, we can do a single write
                if len(set(companies.values())) == 1:
                    vals['company_id'] = list(companies.values())[0]
                else:
                    # Write individually to trigger history and constraint rules properly
                    res = True
                    for record in self:
                        record_vals = vals.copy()
                        record_vals['company_id'] = companies[record.id]
                        res = res and record.write(record_vals)
                    return res
            else:
                # Single record write
                record = self
                branch_id = vals.get('branch_id', record.branch_id.id)
                product_tmpl_id = vals.get('product_tmpl_id', record.product_tmpl_id.id)
                branch = self.env['restaurant.branch'].browse(branch_id) if branch_id else self.env['restaurant.branch']
                product_tmpl = self.env['product.template'].browse(product_tmpl_id) if product_tmpl_id else self.env['product.template']
                
                vals['company_id'] = (
                    branch.company_id.id or
                    product_tmpl.company_id.id or
                    self.env.company.id
                )
        elif 'company_id' in vals and not vals.get('company_id'):
            vals['company_id'] = self.env.company.id

        tracked_fields = ['price', 'branch_id', 'channel', 'date_from', 'date_until', 'active']
        
        if not any(f in vals for f in tracked_fields):
            return super().write(vals)
            
        old_values = {}
        for record in self:
            old_values[record.id] = {
                'price': record.price,
                'branch_id': record.branch_id.id,
                'channel': record.channel,
                'date_from': record.date_from,
                'date_until': record.date_until,
                'active': record.active,
            }
            
        res = super().write(vals)
        
        for record in self:
            old_vals = old_values[record.id]
            changed_fields = []
            
            for f in tracked_fields:
                old_v = old_vals[f]
                new_v = record[f]
                if f == 'branch_id':
                    new_v = new_v.id
                if old_v != new_v:
                    changed_fields.append(f)
                    
            if not changed_fields:
                continue
                
            summary_parts = []
            for f in changed_fields:
                summary_parts.append(f"Changed {f}")
            summary = ", ".join(summary_parts)
            
            company_id = record.company_id.id or self.env.company.id
            currency_id = record.currency_id.id or record.company_id.currency_id.id or self.env.company.currency_id.id
            history_vals = {
                'product_tmpl_id': record.product_tmpl_id.id,
                'price_line_id': record.id,
                'branch_id': record.branch_id.id,
                'channel': record.channel,
                'old_price': old_vals['price'],
                'new_price': record.price,
                'old_date_from': old_vals['date_from'],
                'new_date_from': record.date_from,
                'old_date_until': old_vals['date_until'],
                'new_date_until': record.date_until,
                'old_active': old_vals['active'],
                'new_active': record.active,
                'company_id': company_id,
                'currency_id': currency_id,
                'changed_by_id': self.env.user.id,
                'changed_on': fields.Datetime.now(),
                'change_summary': summary,
            }
            self.env['restaurant.branch.price.history'].sudo().create(history_vals)
            
        return res

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price <= 0:
                raise ValidationError("Price must be greater than zero.")

    @api.constrains('date_from', 'date_until')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_until and record.date_from > record.date_until:
                raise ValidationError("Start Date cannot be after End Date.")

    @api.constrains('product_tmpl_id')
    def _check_product_is_menu_item(self):
        for record in self:
            if record.product_tmpl_id and not record.product_tmpl_id.is_menu_item:
                raise ValidationError("Branch pricing can only be configured for menu products.")

    @api.constrains('product_tmpl_id', 'active', 'price', 'branch_id', 'channel', 'date_from', 'date_until')
    def _check_product_active(self):
        for record in self:
            if record.active and record.product_tmpl_id and not record.product_tmpl_id.active:
                raise ValidationError("Archived products cannot receive active branch pricing rules.")

    @api.constrains('branch_id')
    def _check_branch_active(self):
        for record in self:
            if record.branch_id and not record.branch_id.active:
                raise ValidationError("Selected branch is archived.")

    @api.constrains('branch_id', 'product_tmpl_id')
    def _check_branch_company(self):
        for record in self:
            if record.branch_id and record.product_tmpl_id and record.product_tmpl_id.company_id:
                branch_company = getattr(record.branch_id, 'company_id', False)
                if branch_company and branch_company.id != record.product_tmpl_id.company_id.id:
                    raise ValidationError("Selected branch belongs to a different company than the product.")

    @api.constrains('branch_id', 'channel')
    def _check_branch_or_channel(self):
        for record in self:
            if not record.branch_id and not record.channel:
                raise ValidationError("At least one of Branch or Channel must be set.")

    @api.constrains('product_tmpl_id', 'branch_id', 'channel', 'date_from', 'date_until', 'active')
    def _check_overlap(self):
        for record in self:
            if not record.active:
                continue
            
            domain = [
                ('id', '!=', record.id),
                ('product_tmpl_id', '=', record.product_tmpl_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('channel', '=', record.channel),
                ('active', '=', True),
            ]
            
            if record.date_from:
                domain += ['|', ('date_until', '=', False), ('date_until', '>=', record.date_from)]
            
            if record.date_until:
                domain += ['|', ('date_from', '=', False), ('date_from', '<=', record.date_until)]
                
            overlaps = self.search(domain, limit=1)
            if overlaps:
                raise ValidationError("Another active price rule already overlaps this product, branch, channel, and date range.")

    def unlink(self):
        self._check_pricing_permissions()
        return super().unlink()
