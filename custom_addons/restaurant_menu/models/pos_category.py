from odoo import models, fields, api

class PosCategory(models.Model):
    _inherit = 'pos.category'

    is_restaurant_category = fields.Boolean(
        string="Restaurant Category",
        default=True,
        help="Enable this option for categories used in the restaurant menu.",
    )

    available_from = fields.Date(
        string="Available From",
        help="Optional start date for seasonal or temporary menu categories.",
    )

    available_until  = fields.Date(
        string="Available Until",
        help="Optional end date for seasonal or temporary menu categories.",
    )

    show_in_pos = fields.Boolean(
        string="Show in POS",
        default=True,
        help="Disable this option to hide this category from POS without archiving its products.",
    )