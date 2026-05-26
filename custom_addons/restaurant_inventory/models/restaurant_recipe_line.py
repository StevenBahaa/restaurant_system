from odoo import models, fields

class RestaurantRecipeLine(models.Model):
    _inherit = "restaurant.recipe.line"

    is_critical = fields.Boolean(
        string="Critical for Availability",
        default=True,
        help="If enabled, this ingredient blocks product availability when insufficient at the branch stock location.",
    )
