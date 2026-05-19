from odoo.exceptions import ValidationError
from odoo import models, fields, api

class RestaurantAddonGroup(models.Model):
    _name = "restaurant.addon.group"
    _description = "Restaurant Add-on Group"
    
    name = fields.Char(
        string="Add-on Group Name",
        required=True,
    )
    
    active = fields.Boolean(
        default=True,
    )

    addon_item_ids = fields.One2many(
        comodel_name="restaurant.addon.item",
        inverse_name="addon_group_id",
        string="Add-ons",
    )

    used_in_operations = fields.Boolean(
        string="Used in Operations",
        default=False,
        readonly=True,
    )

    def unlink(self):
        for group in self:
            if group.used_in_operations:
                raise ValidationError(
                    "You cannot delete an add-on group that was already used in operations. Archive it instead."
                )
        return super().unlink()

    def write(self, vals):
        protected_fields = {
            "name",
            "addon_item_ids",
        }

        for group in self:
            if group.used_in_operations and protected_fields.intersection(vals.keys()):
                raise ValidationError(
                    "You cannot modify an add-on group that was already used in operations. Archive it instead."
                )

        return super().write(vals)
    @api.constrains("addon_item_ids", "active")
    def _check_active_addon_items(self):
        for group in self:
            if not group.active:
                continue

            active_items = group.addon_item_ids.filtered(lambda item: item.active)

            if not active_items:
                raise ValidationError(
                    "An active add-on group must contain at least one active add-on item."
                )

class RestaurantAddonItem(models.Model):
    _name = "restaurant.addon.item"
    _description = "Restaurant Add-on Item"

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Add-on Product",
        required=True,
        domain=[
           ("restaurant_product_type", "in", ["ready_item", "beverage", "prepared_meal"]),
        ],
    )

    name = fields.Char(
        string="Add-on Name",
        related="product_tmpl_id.name",
        store=True,
        readonly=True,
    )   

    addon_group_id = fields.Many2one(
        comodel_name="restaurant.addon.group",
        string="Add-on Group",
        required=True,
        ondelete="cascade",
    )

    additional_price = fields.Float(
        string="Additional Price",
        default=0.0,
    )

    max_quantity = fields.Integer(
        string="Maximum Quantity",
        default=1,
    )

    kitchen_note = fields.Char(
        string="Kitchen Note",
    )

    active = fields.Boolean(
        default=True,
    )

    ingredient_line_ids = fields.One2many(
        comodel_name="restaurant.addon.item.ingredient",
        inverse_name="addon_item_id",
        string="Ingredient Consumption",
    )   

    addon_cost = fields.Float(
        string="Add-on Cost",
        compute="_compute_addon_cost",
        store=True,
        readonly=True,
    )

    used_in_operations = fields.Boolean(
        string="Used in Operations",
        default=False,
        readonly=True,
    )

    def unlink(self):
        for item in self:
            if item.used_in_operations:
                raise ValidationError(
                    "You cannot delete an add-on item that was already used in operations. Archive it instead."
                )
        return super().unlink() 

    def write(self, vals):
        protected_fields = {
            "product_tmpl_id",
            "additional_price",
            "max_quantity",
            "kitchen_note",
            "ingredient_line_ids",
        }

        for item in self:
            if item.used_in_operations and protected_fields.intersection(vals.keys()):
                raise ValidationError(
                    "You cannot modify an add-on item that was already used in operations. Archive it instead."
                )

        return super().write(vals)

    @api.depends("ingredient_line_ids.line_cost")
    def _compute_addon_cost(self):
        for item in self:
            item.addon_cost = sum(item.ingredient_line_ids.mapped("line_cost")) 

    @api.constrains("max_quantity")
    def _check_max_quantity(self):
        for addon in self:
            if addon.max_quantity < 1:
                raise ValidationError("Maximum quantity must be at least 1.")

    @api.constrains("additional_price")
    def _check_additional_price(self):
        for addon in self:
            if addon.additional_price < 0:
                raise ValidationError("Additional price cannot be negative.")

    @api.constrains("addon_group_id", "product_tmpl_id")
    def _check_unique_product_per_group(self):
        for item in self:
            duplicate = self.search([
                ("addon_group_id", "=", item.addon_group_id.id),
                ("product_tmpl_id", "=", item.product_tmpl_id.id),
                ("id", "!=", item.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    "This add-on product is already added to this add-on group."
                )

class RestaurantProductAddonGroup(models.Model):
    _name = "restaurant.product.addon.group"
    _description = "Restaurant Product Add-on Group"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
    )

    active = fields.Boolean(
        default=True,
    )

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Menu Item",
        required=True,
        ondelete="cascade",
        domain=[
            ("is_menu_item", "=", True),
        ],
    )

    addon_group_id = fields.Many2one(
        comodel_name="restaurant.addon.group",
        string="Add-on Group",
        required=True,
        ondelete="restrict",
    )

    addon_item_ids = fields.One2many(
       related="addon_group_id.addon_item_ids",
        string="Add-on Items",
        readonly=True,
    )

    required = fields.Boolean(
        string="Required",
        default=False,
    )

    min_selection = fields.Integer(
        string="Minimum Selection",
        default=0,
    )

    max_selection = fields.Integer(
        string="Maximum Selection",
        default=1,
    )

    used_in_operations = fields.Boolean(
        string="Used in Operations",
        default=False,
        readonly=True,
    )

    def unlink(self):
        for record in self:
            if record.used_in_operations:
                raise ValidationError(
                    "You cannot delete a product add-on configuration that was already used in operations. Disable it instead."
                )

        return super().unlink()


    def write(self, vals):
        protected_fields = {
            "product_tmpl_id",
            "addon_group_id",
        }

        for record in self:
            if record.used_in_operations and protected_fields.intersection(vals.keys()):
                raise ValidationError(
                    "You cannot change the product or add-on group for a configuration that was already used in operations. Disable it and create a new configuration instead."
                )

        return super().write(vals)

    @api.constrains("required", "min_selection", "max_selection")
    def _check_selection_rules(self):
        for record in self:
            if record.min_selection < 0:
                raise ValidationError("Minimum selection cannot be negative.")

            if record.max_selection < 0:
                raise ValidationError("Maximum selection cannot be negative.")

            if record.max_selection and record.min_selection > record.max_selection:
                raise ValidationError(
                    "Minimum selection cannot be greater than maximum selection."
                )

            if record.required and record.min_selection <= 0:
                raise ValidationError(
                    "Required add-on groups must have a minimum selection greater than zero."
                )

            if not record.required and record.min_selection > 0:
                raise ValidationError(
                    "Optional add-on groups must have a minimum selection of zero."
                )

    @api.constrains("product_tmpl_id", "addon_group_id")
    def _check_unique_group_per_product(self):
        for record in self:
            duplicate = self.search([
                ("product_tmpl_id", "=", record.product_tmpl_id.id),
                ("addon_group_id", "=", record.addon_group_id.id),
                ("id", "!=", record.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    "This add-on group is already assigned to the menu item."
                )

class RestaurantAddonItemIngredient(models.Model):
    _name = "restaurant.addon.item.ingredient"
    _description = "Restaurant Add-on Item Ingredient"

    addon_item_id = fields.Many2one(
        comodel_name="restaurant.addon.item",
        string="Add-on Item",
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

    @api.depends("ingredient_product_id")
    def _compute_ingredient_cost(self):
        for line in self:
            line.ingredient_cost = line.ingredient_product_id.standard_price or 0.0


    @api.depends("actual_quantity", "ingredient_cost")
    def _compute_line_cost(self):
        for line in self:
            line.line_cost = line.actual_quantity * line.ingredient_cost  

    @api.depends("quantity", "wastage_percent")
    def _compute_actual_quantity(self):
        for line in self:
            line.actual_quantity = line.quantity + (
                line.quantity * line.wastage_percent / 100.0
            )

    @api.onchange("ingredient_product_id")
    def _onchange_ingredient_product_id(self):
        for line in self:
            if line.ingredient_product_id:
                line.uom_id = line.ingredient_product_id.uom_id

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Ingredient quantity must be greater than zero.")

    @api.constrains("wastage_percent")
    def _check_wastage_percent(self):
        for line in self:
            if line.wastage_percent < 0 or line.wastage_percent >= 100:
                raise ValidationError("Wastage percentage must be between 0 and 99.")

    def write(self, vals):
        for line in self:
            if line.addon_item_id.used_in_operations:
                raise ValidationError(
                    "You cannot modify ingredient consumption for an add-on item already used in operations."
                )

        return super().write(vals)


    def unlink(self):
        for line in self:
            if line.addon_item_id.used_in_operations:
                raise ValidationError(
                    "You cannot delete ingredient consumption for an add-on item already used in operations."
                )

        return super().unlink()