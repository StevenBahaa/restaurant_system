# -*- coding: utf-8 -*-
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
            ("combo", "Combo Meal"),
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

    product_addon_group_ids = fields.One2many(
        comodel_name="restaurant.product.addon.group",
        inverse_name="product_tmpl_id",
        string="Add-on Groups",
    )

    product_schedule_line_ids = fields.One2many(
        comodel_name="restaurant.product.schedule.line",
        inverse_name="product_tmpl_id",
        string="Schedule Rules",
    )

    @api.onchange("restaurant_product_type")
    def _onchange_restaurant_product_type(self):
        for product in self:
            if product.restaurant_product_type == "prepared_meal":
                product.sale_ok = True
                product.purchase_ok = False
                product.available_in_pos = True
                product.is_menu_item = True
                product.is_storable = False

            elif product.restaurant_product_type == "ingredient":
                product.sale_ok = False
                product.purchase_ok = True
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "packaging":
                product.sale_ok = False
                product.purchase_ok = True
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "semi_finished":
                product.sale_ok = False
                product.purchase_ok = False
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "beverage":
                product.sale_ok = True
                product.purchase_ok = True
                product.available_in_pos = True
                product.is_menu_item = True

            elif product.restaurant_product_type == "ready_item":
                product.sale_ok = True
                product.purchase_ok = True
                product.available_in_pos = True
                product.is_menu_item = True
