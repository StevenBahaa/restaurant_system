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
            ("restaurant_product_type", "in", ["prepared_meal", "beverage", "ready_item", "semi_finished"]),
        ],
    )

    recipe_line_ids = fields.One2many(
        comodel_name="restaurant.recipe.line",
        inverse_name="recipe_id",
        string="Recipe Lines",
    )
    
    total_cost = fields.Monetary(
        string="Recipe Cost",
        compute="_compute_total_cost",
        store=True,
        readonly=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("approved", "Approved"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Enable or disable this recipe.",
    )

    version = fields.Integer(
        string="Version",
        readonly=True,
        copy=False,
    )   
    display_name = fields.Char(
        compute="_compute_display_name",
        recursive=True,
        store=False,
    )   

    effective_from = fields.Date(
        string="Effective From",
        default=fields.Date.context_today,
        required=True,
    )

    used_in_operations = fields.Boolean(
        string="Used in Operations",
        default=False,
        readonly=True,
        help="Indicates whether this recipe was already used in operational transactions.",
    )

    @api.constrains("effective_from")
    def _check_effective_from(self):
        for recipe in self:
            if not recipe.effective_from:
                raise ValidationError("Effective From date is required.")
    
    def action_approve(self):
        for recipe in self:
            old_approved_recipes = self.search([
                ("product_tmpl_id", "=", recipe.product_tmpl_id.id),
                ("state", "=", "approved"),
                ("active", "=", True),
                ("id", "!=", recipe.id),
            ])

            old_approved_recipes.write({
                "state": "draft",
            })

            recipe.state = "approved"

    def action_set_to_draft(self):
        for recipe in self:
            recipe.state = "draft"

    @api.depends("recipe_line_ids", "recipe_line_ids.line_cost")
    def _compute_total_cost(self):
        for recipe in self:
            recipe.total_cost = sum(recipe.recipe_line_ids.mapped("line_cost"))

    @api.constrains("product_tmpl_id", "state", "active")
    def _check_single_approved_recipe_per_product(self):
        for recipe in self:
            if recipe.state != "approved" or not recipe.active:
                continue

            duplicate_approved_recipe = self.search([
                ("product_tmpl_id", "=", recipe.product_tmpl_id.id),
                ("state", "=", "approved"),
                ("active", "=", True),
                ("id", "!=", recipe.id),
            ], limit=1)

            if duplicate_approved_recipe:
                raise ValidationError(
                    "Only one approved recipe is allowed per menu item."
                )

    @api.depends("name", "version", "state")
    def _compute_display_name(self):
        for recipe in self:
            version_text = f"V{recipe.version}" if recipe.version else "V?"

            state_text = recipe.state.capitalize() if recipe.state else "Unknown"

            recipe.display_name = (
                f"{recipe.name} - {version_text} [{state_text}]"
            )

    def action_create_new_version(self):
        self.ensure_one()

        new_recipe = self.create({
            "name": self.name,
            "product_tmpl_id": self.product_tmpl_id.id,
            "state": "draft",
            "active": True,
            "company_id": self.company_id.id,
            "recipe_line_ids": [
                (0, 0, {
                    "ingredient_product_id": line.ingredient_product_id.id,
                    "quantity": line.quantity,
                    "uom_id": line.uom_id.id,
                    "wastage_percent": line.wastage_percent,
                    "notes": line.notes,
                })
                for line in self.recipe_line_ids
            ],
        })

        return {
            "type": "ir.actions.act_window",
            "name": "New Recipe Version",
            "res_model": "restaurant.recipe",
            "res_id": new_recipe.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product_id = vals.get("product_tmpl_id")

            if product_id:
                latest_recipe = self.search(
                    [("product_tmpl_id", "=", product_id)],
                    order="version desc",
                    limit=1,
                )

                vals["version"] = (latest_recipe.version or 0) + 1 if latest_recipe else 1

        return super().create(vals_list)

    def unlink(self):
        for recipe in self:
            if recipe.used_in_operations:
                raise ValidationError(
                    "You cannot delete a recipe that was already used in operations. Archive it instead."
                )

        return super().unlink()

    def write(self, vals):
        protected_fields = {
            "name",
            "product_tmpl_id",
            "recipe_line_ids",
        }

        for recipe in self:
            if recipe.state == "approved" or recipe.used_in_operations:
                if protected_fields.intersection(vals.keys()):
                    raise ValidationError(
                        "You cannot modify an approved or operationally used recipe. Create a new version instead."
                    )

        return super().write(vals)



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
            ("restaurant_product_type", "in", ["ingredient", "packaging"]),
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

    @api.constrains("ingredient_product_id")
    def _check_duplicate_ingredient(self):
        for line in self:
            duplicates = self.search([
                ("recipe_id", "=", line.recipe_id.id),
                ("ingredient_product_id", "=", line.ingredient_product_id.id),
                ("id", "!=", line.id),
            ])

            if duplicates:
                raise ValidationError(
                    "The same ingredient cannot be added multiple times to the same recipe."
                )
    
    @api.depends("quantity", "wastage_percent")
    def _compute_actual_quantity(self):
        for line in self:
            line.actual_quantity = line.quantity + (
                line.quantity * line.wastage_percent / 100.0
            )

    @api.depends("ingredient_product_id", "ingredient_product_id.standard_price")
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
    
    @api.onchange("ingredient_product_id")
    def _onchange_ingredient_product_id(self):
        for line in self:
            if line.ingredient_product_id:
                line.uom_id = line.ingredient_product_id.uom_id

    @api.model_create_multi
    def create(self, vals_list):
        recipe_ids = [
            vals.get("recipe_id")
            for vals in vals_list
            if vals.get("recipe_id")
        ]

        recipes = self.env["restaurant.recipe"].browse(recipe_ids)

        for recipe in recipes:
            if recipe.state == "approved" or recipe.used_in_operations:
                raise ValidationError(
                    "You cannot add recipe lines to an approved or operationally used recipe. Create a new version instead."
                )

        return super().create(vals_list)

    def write(self, vals):
        for line in self:
            if line.recipe_id.state == "approved" or line.recipe_id.used_in_operations:
                raise ValidationError(
                    "You cannot modify recipe lines for an approved or operationally used recipe. Create a new version instead."
                )

        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.recipe_id.state == "approved" or line.recipe_id.used_in_operations:
                raise ValidationError(
                    "You cannot delete recipe lines from an approved or operationally used recipe. Create a new version instead."
                )

        return super().unlink()

    
    

