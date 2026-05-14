from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    recipe_ids = fields.One2many(
        comodel_name="restaurant.recipe",
        inverse_name="product_tmpl_id",
        string="Recipes",
    )

    recipe_count = fields.Integer(
        string="Recipe Count",
        compute="_compute_recipe_count",
    )

    recipe_cost = fields.Monetary(
        string="Recipe Cost",
        compute="_compute_recipe_cost",
        currency_field="currency_id",
        store=True,
    )

    food_cost_percent = fields.Float(
        string="Food Cost %",
        compute="_compute_food_cost_percent",
        store=True,
    )

    @api.depends("recipe_ids")
    def _compute_recipe_count(self):
        for product in self:
            product.recipe_count = len(product.recipe_ids)

    @api.depends("recipe_ids.total_cost")
    def _compute_recipe_cost(self):
        for product in self:
            active_recipe = product.recipe_ids.filtered(lambda recipe: recipe.active)[:1]
            product.recipe_cost = active_recipe.total_cost if active_recipe else 0.0

    def action_view_recipes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Recipes",
            "res_model": "restaurant.recipe",
            "view_mode": "list,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "default_name": "%s Recipe" % self.name,
            },
        }

    @api.depends("recipe_cost", "list_price")
    def _compute_food_cost_percent(self):
        for product in self:
            if product.list_price:
                product.food_cost_percent = (product.recipe_cost / product.list_price) * 100
            else:
                product.food_cost_percent = 0.0 

    @api.constrains("list_price", "recipe_cost", "is_menu_item")
    def _check_recipe_cost_vs_sales_price(self):
        for product in self:
            if (
                product.is_menu_item
                and product.recipe_cost > 0
                and product.list_price < product.recipe_cost
            ):
                raise ValidationError(
                    "Sales price cannot be lower than recipe cost."
                )