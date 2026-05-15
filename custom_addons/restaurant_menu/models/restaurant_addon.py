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

    mandatory = fields.Boolean(
        string="Mandatory Selection",
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

    addon_item_ids = fields.One2many(
        comodel_name="restaurant.addon.item",
        inverse_name="addon_group_id",
        string="Add-ons",
    )

    @api.constrains("min_selection", "max_selection")
    def _check_selection_limits(self):
        for group in self:
            if group.min_selection < 0:
                raise ValidationError("Minimum selection cannot be negative.")

            if group.max_selection < 0:
                raise ValidationError("Maximum selection cannot be negative.")

            if group.max_selection and group.min_selection > group.max_selection:
                raise ValidationError(
                    "Minimum selection cannot be greater than maximum selection."
                )

    @api.constrains("mandatory", "min_selection")
    def _check_mandatory_selection(self):
        for group in self:
            if group.mandatory and group.min_selection <= 0:
                raise ValidationError(
                    "Mandatory add-on groups must require at least one selection."
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

    required_override = fields.Boolean(
        string="Required Override",
        help="Override default mandatory behavior for this menu item.",
    )

    override_selection_rules = fields.Boolean(
        string="Override Selection Rules",
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

    effective_mandatory = fields.Boolean(
        string="Effective Mandatory",
        compute="_compute_effective_rules",
        store=True,
    )

    effective_min_selection = fields.Integer(
        string="Effective Minimum Selection",
        compute="_compute_effective_rules",
        store=True,
    )

    effective_max_selection = fields.Integer(
        string="Effective Maximum Selection",
        compute="_compute_effective_rules",
        store=True,
    )

    @api.depends(
        "required_override",
        "override_selection_rules",
        "min_selection",
        "max_selection",
        "addon_group_id.mandatory",
        "addon_group_id.min_selection",
        "addon_group_id.max_selection",
    )
    def _compute_effective_rules(self):
        for record in self:
            record.effective_mandatory = (
                record.required_override
                if record.required_override
                else record.addon_group_id.mandatory
            )

            if record.override_selection_rules:
                record.effective_min_selection = record.min_selection
                record.effective_max_selection = record.max_selection
            else:
                record.effective_min_selection = record.addon_group_id.min_selection
                record.effective_max_selection = record.addon_group_id.max_selection

    @api.constrains("override_selection_rules", "min_selection", "max_selection")
    def _check_product_selection_limits(self):
        for record in self:
            if not record.override_selection_rules:
                continue

            if record.min_selection < 0:
                raise ValidationError("Minimum selection cannot be negative.")

            if record.max_selection < 0:
                raise ValidationError("Maximum selection cannot be negative.")

            if record.max_selection and record.min_selection > record.max_selection:
                raise ValidationError(
                    "Minimum selection cannot be greater than maximum selection."
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