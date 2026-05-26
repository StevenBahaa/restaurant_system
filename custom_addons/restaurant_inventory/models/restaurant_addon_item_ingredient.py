from odoo import models, fields

class RestaurantAddonItemIngredient(models.Model):
    _inherit = "restaurant.addon.item.ingredient"

    is_critical = fields.Boolean(
        string="Critical for Availability",
        default=True,
        help="If enabled, this add-on ingredient blocks add-on availability when insufficient at the branch stock location.",
    )
