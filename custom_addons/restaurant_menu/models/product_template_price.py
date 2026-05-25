# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    branch_price_line_ids = fields.One2many(
        'restaurant.branch.price.line',
        'product_tmpl_id',
        string='Branch Pricing Rules'
    )
