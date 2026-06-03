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

    def _get_pos_addon_payload_bulk(self):
        """
        Returns a POS-safe payload of active add-on configurations for the current recordset.
        Explicitly excludes all cost, ingredient, stock, and accounting internals.

        Returns:
            dict: {product_tmpl_id: [group_payload, ...]}
        """
        payload = {product.id: [] for product in self}

        if not self:
            return payload

        ProductAddonGroup = self.env["restaurant.product.addon.group"]

        domain = [
            ("product_tmpl_id", "in", self.ids),
            ("active", "=", True),
            ("addon_group_id.active", "=", True),
        ]

        product_groups = ProductAddonGroup.search(
            domain,
            order="product_tmpl_id, sequence, id",
        )

        for p_group in product_groups:
            active_items = p_group.addon_group_id.addon_item_ids.filtered(
                lambda item: item.active
            ).sorted(
                key=lambda item: (item.product_tmpl_id.display_name or "", item.id)
            )

            if not active_items:
                continue

            items_payload = []
            for item in active_items:
                items_payload.append({
                    "addon_item_id": item.id,
                    "product_tmpl_id": item.product_tmpl_id.id,
                    "display_name": item.product_tmpl_id.display_name,
                    "additional_price": item.additional_price,
                    "max_quantity": item.max_quantity,
                    "kitchen_note": item.kitchen_note or "",
                })

            group_payload = {
                "product_addon_group_id": p_group.id,
                "sequence": p_group.sequence,
                "addon_group_id": p_group.addon_group_id.id,
                "addon_group_name": p_group.addon_group_id.name,
                "required": p_group.required,
                "min_selection": p_group.min_selection,
                "max_selection": p_group.max_selection,
                "items": items_payload,
            }

            payload[p_group.product_tmpl_id.id].append(group_payload)

        return payload

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
