from odoo.exceptions import ValidationError
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

    combo_component_line_ids = fields.One2many(
        "restaurant.combo.line",
        "combo_product_tmpl_id",
        string="Combo Components",
    )

    combo_component_count = fields.Integer(
        string="Combo Component Count",
        compute="_compute_combo_totals",
        store=True, 
    )

    combo_individual_total_price = fields.Float(
        string="Individual Components Total",
        compute="_compute_combo_totals",
        store=True,
    )

    combo_saving_amount = fields.Float(
        string="Combo Saving",
        compute="_compute_combo_totals",
        store=True,
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
    
    @api.depends(
        "restaurant_product_type",
        "list_price",
        "combo_component_line_ids.quantity",
        "combo_component_line_ids.component_product_tmpl_id.list_price",
    )
    def _compute_combo_totals(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_component_count = 0
                product.combo_individual_total_price = 0.0
                product.combo_saving_amount = 0.0
                continue

            total = 0.0
            count = 0

            for line in product.combo_component_line_ids:
                count += 1
                total += line.component_product_tmpl_id.list_price * line.quantity

            product.combo_component_count = count
            product.combo_individual_total_price = total
            product.combo_saving_amount = total - product.list_price

    
    @api.constrains("restaurant_product_type", "list_price")
    def _check_combo_price_positive(self):
        for product in self:
            if product.restaurant_product_type == "combo" and product.list_price <= 0:
                raise ValidationError("Combo price must be greater than zero.")


    def _check_combo_operational_validity(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                continue

            if len(product.combo_component_line_ids) < 2:
                raise ValidationError("A combo meal must contain at least 2 components.")

            if product.list_price <= 0:
                raise ValidationError("Combo price must be greater than zero.")

        return True