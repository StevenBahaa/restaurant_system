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
        ondelete='cascade'
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
                raise ValidationError("Price must be greater than 0.")

    @api.constrains('date_from', 'date_until')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_until and record.date_from > record.date_until:
                raise ValidationError("Start Date cannot be after End Date.")

    @api.constrains('product_tmpl_id')
    def _check_product_is_menu_item(self):
        for record in self:
            if record.product_tmpl_id and not record.product_tmpl_id.is_menu_item:
                raise ValidationError("Pricing rules can only be set for menu items.")

    @api.constrains('branch_id')
    def _check_branch_active(self):
        for record in self:
            if record.branch_id and not record.branch_id.active:
                raise ValidationError("The selected branch must be active.")

    @api.constrains('branch_id', 'channel')
    def _check_branch_or_channel(self):
        for record in self:
            if not record.branch_id and not record.channel:
                raise ValidationError("At least one of Branch or Channel must be set.")
