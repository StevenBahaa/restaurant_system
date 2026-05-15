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

    name = fields.Char(
        string="Add-on Name",
        required=True,
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