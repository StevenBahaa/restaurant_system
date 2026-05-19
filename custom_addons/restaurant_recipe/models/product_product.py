from odoo.exceptions import ValidationError
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = "product.product"

    variant_recipe_line_ids = fields.One2many(
        comodel_name="restaurant.variant.recipe.line",
        inverse_name="product_id",
        string="Variant Recipe Override",
    )

    variant_recipe_cost = fields.Float(
        string="Variant Recipe Cost",
        compute="_compute_variant_recipe_cost",
        store=True,
        readonly=True,
    )

    has_variant_recipe_override = fields.Boolean(
        string="Has Variant Recipe Override",
        compute="_compute_has_variant_recipe_override",
        store=True,
    )

    final_recipe_cost = fields.Float(
        string="Final Recipe Cost",
        compute="_compute_final_recipe_cost",
        store=True,
        readonly=True,
    )

    variant_food_cost_percent = fields.Float(
        string="Variant Food Cost %",
        compute="_compute_variant_food_cost_percent",
        store=True,
        readonly=True,
    )   

    @api.depends("variant_recipe_line_ids.line_cost")
    def _compute_variant_recipe_cost(self):
        for product in self:
            product.variant_recipe_cost = sum(product.variant_recipe_line_ids.mapped("line_cost"))

    @api.depends("variant_recipe_line_ids")
    def _compute_has_variant_recipe_override(self):
        for product in self:
            product.has_variant_recipe_override = bool(product.variant_recipe_line_ids)

    @api.depends(
        "variant_recipe_line_ids",
        "variant_recipe_line_ids.ingredient_product_id",
        "variant_recipe_line_ids.line_cost",
        "product_tmpl_id.recipe_ids",
        "product_tmpl_id.recipe_ids.state",
        "product_tmpl_id.recipe_ids.active",
        "product_tmpl_id.recipe_ids.recipe_line_ids",
        "product_tmpl_id.recipe_ids.recipe_line_ids.ingredient_product_id",
        "product_tmpl_id.recipe_ids.recipe_line_ids.line_cost",
    )
    def _compute_final_recipe_cost(self):
        for product in self:
            approved_recipe = product.product_tmpl_id.recipe_ids.filtered(
                lambda recipe: recipe.active and recipe.state == "approved"
            )[:1]

            if not approved_recipe:
                product.final_recipe_cost = product.variant_recipe_cost
                continue

            template_cost = approved_recipe.total_cost

            overridden_ingredient_ids = product.variant_recipe_line_ids.mapped(
                "ingredient_product_id"
            ).ids

            overridden_template_lines = approved_recipe.recipe_line_ids.filtered(
                lambda line: line.ingredient_product_id.id in overridden_ingredient_ids
            )

            overridden_template_cost = sum(overridden_template_lines.mapped("line_cost"))

            product.final_recipe_cost = (
                template_cost
                - overridden_template_cost
                + product.variant_recipe_cost
            )

    @api.depends("final_recipe_cost", "lst_price")
    def _compute_variant_food_cost_percent(self):
        for product in self:
            if product.lst_price:
                product.variant_food_cost_percent = (
                    product.final_recipe_cost / product.lst_price
                ) * 100
            else:
                product.variant_food_cost_percent = 0.0
    
    @api.constrains(
        "lst_price",
        "final_recipe_cost",
        "product_tmpl_id",
    )
    def _check_variant_price_above_recipe_cost(self):
        for product in self:
            if (
                product.product_tmpl_id.is_menu_item
                and product.final_recipe_cost > 0
                and product.lst_price < product.final_recipe_cost
            ):
                raise ValidationError(
                    "Variant sales price cannot be lower than its final recipe cost."
                )
    
class RestaurantVariantRecipeLine(models.Model):
    _name = "restaurant.variant.recipe.line"
    _description = "Restaurant Variant Recipe Line"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Variant",
        required=True,
        ondelete="cascade",
    )

    ingredient_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Ingredient",
        required=True,
        domain=[
            ("restaurant_product_type", "=", "ingredient"),
        ],
    )

    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
    )

    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        required=True,
    )

    wastage_percent = fields.Float(
        string="Wastage %",
        default=0.0,
    )

    actual_quantity = fields.Float(
        string="Actual Quantity",
        compute="_compute_actual_quantity",
        store=True,
        readonly=True,
    )

    ingredient_cost = fields.Float(
        string="Ingredient Cost",
        compute="_compute_ingredient_cost",
        store=True,
        readonly=True,
    )

    line_cost = fields.Float(
        string="Line Cost",
        compute="_compute_line_cost",
        store=True,
        readonly=True,
    )

    notes = fields.Text(string="Notes")

    @api.depends("quantity", "wastage_percent")
    def _compute_actual_quantity(self):
        for line in self:
            line.actual_quantity = line.quantity + (
                line.quantity * line.wastage_percent / 100.0
            )

    @api.depends("ingredient_product_id")
    def _compute_ingredient_cost(self):
        for line in self:
            line.ingredient_cost = line.ingredient_product_id.standard_price or 0.0

    @api.depends("actual_quantity", "ingredient_cost")
    def _compute_line_cost(self):
        for line in self:
            line.line_cost = line.actual_quantity * line.ingredient_cost

    @api.onchange("ingredient_product_id")
    def _onchange_ingredient_product_id(self):
        for line in self:
            if line.ingredient_product_id:
                line.uom_id = line.ingredient_product_id.uom_id

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Variant recipe quantity must be greater than zero.")

    @api.constrains("wastage_percent")
    def _check_wastage_percent(self):
        for line in self:
            if line.wastage_percent < 0 or line.wastage_percent >= 100:
                raise ValidationError("Wastage percentage must be between 0 and 99.")

    @api.constrains("product_id", "ingredient_product_id")
    def _check_duplicate_ingredient(self):
        for line in self:
            duplicate = self.search([
                ("product_id", "=", line.product_id.id),
                ("ingredient_product_id", "=", line.ingredient_product_id.id),
                ("id", "!=", line.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    "The same ingredient cannot be added multiple times to the same variant recipe."
                )