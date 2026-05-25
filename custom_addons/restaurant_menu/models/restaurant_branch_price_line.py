# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

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

    @api.depends('product_tmpl_id.company_id')
    def _compute_allowed_branch_ids(self):
        for record in self:
            domain = [('active', '=', True)]
            if record.product_tmpl_id and record.product_tmpl_id.company_id:
                domain.append(('company_id', 'in', [False, record.product_tmpl_id.company_id.id]))
            record.allowed_branch_ids = self.env['restaurant.branch'].search(domain)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_tmpl_id'):
                product_tmpl = self.env['product.template'].browse(vals['product_tmpl_id'])
                vals['company_id'] = product_tmpl.company_id.id or self.env.company.id
            elif not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def write(self, vals):
        if 'product_tmpl_id' in vals:
            product_tmpl = self.env['product.template'].browse(vals['product_tmpl_id'])
            vals['company_id'] = product_tmpl.company_id.id or self.env.company.id
        elif 'company_id' in vals and not vals.get('company_id'):
            vals['company_id'] = self.env.company.id
        return super().write(vals)

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
