from email.policy import default
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_menu_item = fields.Boolean(
        string='Is Menu Item',
        default=False,
        help="Enable this option when the product is sold as a restaurant menu item.",
    )

    arabic_name = fields.Char(
        string='Arabic Name',
        help="Arabic display name used for Arabic receipts, local UI, and restaurant operations.",
    )

    restaurant_product_type = fields.Selection(
        [
            ("prepared_meal", "Prepared Meal"),
            ("beverage", "Beverage"),
            ("ready_item", "Ready Item"),
            ("ingredient", "Ingredient"),
            ("packaging", "Packaging Item"),
            ("semi_finished", "Semi-Finished"),
        ],
        string="Restaurant Product Type",
        default="prepared_meal",
        help="Operational restaurant classification used for menu, kitchen, recipe, inventory, and reporting workflows.",
    )

    addon_group_ids = fields.Many2many(
        comodel_name="restaurant.addon.group",
        relation="product_template_restaurant_addon_group_rel",
        column1="product_tmpl_id",
        column2="addon_group_id",
        string="Add-on Groups",
        help="Add-on groups available for this menu item.",
    )
