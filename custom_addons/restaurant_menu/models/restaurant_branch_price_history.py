# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RestaurantBranchPriceHistory(models.Model):
    _name = 'restaurant.branch.price.history'
    _description = 'Branch Price History'
    _order = 'changed_on desc, id desc'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    price_line_id = fields.Many2one(
        'restaurant.branch.price.line',
        string='Price Rule',
        readonly=True,
        ondelete='set null'
    )
    branch_id = fields.Many2one(
        'restaurant.branch',
        string='Branch',
        readonly=True
    )
    channel = fields.Selection(
        [
            ('dine_in', 'Dine-In'),
            ('takeaway', 'Takeaway'),
            ('delivery_app', 'Delivery App'),
        ],
        string='Channel',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        readonly=True,
        precompute=True
    )

    @api.depends('company_id')
    def _compute_currency_id(self):
        for record in self:
            if record.company_id:
                record.currency_id = record.company_id.currency_id
            else:
                record.currency_id = self.env.company.currency_id
    old_price = fields.Monetary(
        string='Old Price',
        readonly=True,
        currency_field='currency_id'
    )
    new_price = fields.Monetary(
        string='New Price',
        readonly=True,
        currency_field='currency_id'
    )
    old_date_from = fields.Date(
        string='Old Start Date',
        readonly=True
    )
    new_date_from = fields.Date(
        string='New Start Date',
        readonly=True
    )
    old_date_until = fields.Date(
        string='Old End Date',
        readonly=True
    )
    new_date_until = fields.Date(
        string='New End Date',
        readonly=True
    )
    old_active = fields.Boolean(
        string='Old Active',
        readonly=True
    )
    new_active = fields.Boolean(
        string='New Active',
        readonly=True
    )
    changed_by_id = fields.Many2one(
        'res.users',
        string='Changed By',
        readonly=True
    )
    changed_on = fields.Datetime(
        string='Changed On',
        readonly=True
    )
    change_summary = fields.Char(
        string='Change Summary',
        readonly=True
    )
