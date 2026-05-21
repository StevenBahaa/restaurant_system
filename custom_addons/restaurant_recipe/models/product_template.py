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

    has_approved_recipe = fields.Boolean(
        string="Has Approved Recipe",
        compute="_compute_has_approved_recipe",
        store=True,
    )

    @api.depends(
        "recipe_ids",
        "recipe_ids.state",
        "recipe_ids.active",
        )
    def _compute_has_approved_recipe(self):
        for product in self:
            product.has_approved_recipe = bool(
                product.recipe_ids.filtered(
                    lambda recipe: recipe.active and recipe.state == "approved"
                )
            )

    @api.depends("recipe_ids")
    def _compute_recipe_count(self):
        for product in self:
            product.recipe_count = len(product.recipe_ids)

    @api.depends("recipe_ids.total_cost")
    def _compute_recipe_cost(self):
        for product in self:
            active_recipe = product.recipe_ids.filtered(
                lambda recipe: recipe.active and recipe.state == "approved"
            )[:1]
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

    def _get_combo_component_resolved_cost(self, component_product):
        self.ensure_one()
        if not component_product:
            return 0.0

        if component_product.restaurant_product_type in ("prepared_meal", "beverage"):
            approved_recipe = self._get_approved_recipe_for_product(component_product)
            if approved_recipe:
                return approved_recipe.total_cost

        return super()._get_combo_component_resolved_cost(component_product)

    def _get_approved_recipe_for_product(self, product_tmpl):
        self.ensure_one()
        if not product_tmpl:
            return self.env["restaurant.recipe"]

        return self.env["restaurant.recipe"].search([
            ("product_tmpl_id", "=", product_tmpl.id),
            ("state", "=", "approved"),
        ], limit=1)