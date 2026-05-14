from odoo.exceptions import ValidationError
from odoo import models, fields, api

class RestaurantRecipe(models.Model):
    _name = "restaurant.recipe"
    _description = "Restaurant Recipe"


    name = fields.Char(
        string="Recipe Name",
        required=True,
    )
    
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        help="Product this recipe is for.",
        domain=[
            ("is_menu_item", "=", True),
            ("restaurant_product_type", "=", "prepared_meal"),
        ],
    )

    recipe_line_ids = fields.One2many(
        comodel_name="restaurant.recipe.line",
        inverse_name="recipe_id",
        string="Recipe Lines",
    )
    
    total_cost = fields.Float(
        string="Recipe Cost",
        compute="_compute_total_cost",
        store=True,
        readonly=True,
    )
    
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Enable or disable this recipe.",
    )



class RestaurantRecipeLine(models.Model):
    _name = "restaurant.recipe.line"
    _description = "Restaurant Recipe Line"

    recipe_id = fields.Many2one(
        "restaurant.recipe",
        string="Recipe",
        required=True,
        ondelete="cascade",
    )

    ingredient_product_id = fields.Many2one(
        "product.template",
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
    
    notes = fields.Text(
        string="Notes",
    )

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

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Recipe ingredient quantity must be greater than zero.")

    @api.constrains("wastage_percent")
    def _check_wastage_percent(self):
        for line in self:
            if line.wastage_percent < 0 or line.wastage_percent >= 100:
                raise ValidationError("Wastage percentage must be between 0 and 99.")
    

