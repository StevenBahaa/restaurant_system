from operator import index
from typing import Sequence
from odoo import models, fields , api
from odoo.exceptions import ValidationError


class RestaurantComboLine(models.Model):
    _name = "restaurant.combo.line"
    _description = "Restaurant Combo Component Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence , id"



    
    sequence = fields.Integer(default=10)

    combo_product_tmpl_id = fields.Many2one(
        'product.template', 
        string='Combo Product', 
        required=True, 
        ondelete='cascade',
        index = True
    )
    
    component_product_tmpl_id = fields.Many2one(
        'product.template', 
        string='Component Product', 
        required=True, 
        ondelete='cascade',
        domain=[
            ("is_menu_item", "=", True),
            ("restaurant_product_type", "in", ["prepared_meal", "beverage", "ready_item"]),
        ],
    )

    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
    )

    allow_customization = fields.Boolean(
        string="Allow Customization",
        default=False,
    )

    is_swappable = fields.Boolean(
        string="Swappable",
        default=False,
    )

    allowed_substitute_product_ids = fields.Many2many(
        "product.template",
        "restaurant_combo_line_substitute_rel",
        "combo_line_id",
        "product_tmpl_id",
        string="Allowed Substitutes",
        domain=[
            ("is_menu_item", "=", True),
            ("restaurant_product_type", "in", ["prepared_meal", "beverage", "ready_item"]),
        ],
    )

    is_upgradeable = fields.Boolean(
        string="Upgradeable",
        default=False,
    )

    upgrade_price = fields.Float(
        string="Upgrade Price",
        default=0.0,
    )

    notes = fields.Text(string="Notes")



    @api.constrains("combo_product_tmpl_id", "component_product_tmpl_id")
    def _check_component_not_combo_itself(self):
        for record in self:
            if record.combo_product_tmpl_id and record.component_product_tmpl_id:
                if record.combo_product_tmpl_id == record.component_product_tmpl_id:
                    raise ValidationError("Combo product and component product cannot be the same.")    
    
    @api.constrains("quantity")
    def _check_quantity_positive(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("Quantity must be positive.")    


    
    @api.constrains("component_product_tmpl_id")
    def _check_component_operational_type(self):
        allowed_types = {"prepared_meal", "beverage", "ready_item"}

        for line in self:
            component = line.component_product_tmpl_id
            if not component:
                continue

            if not component.is_menu_item:
                raise ValidationError("Combo component must be a menu item.")

            if component.restaurant_product_type not in allowed_types:
                raise ValidationError(
                    "Combo component must be Prepared Meal, Beverage, or Ready Item."
                )

            if not component.active:
                raise ValidationError("Archived products cannot be used as combo components.")

    
    @api.constrains(
        "combo_product_tmpl_id",
        "component_product_tmpl_id",
        "allowed_substitute_product_ids",
    )
    def _check_substitute_operational_types(self):
        allowed_types = {"prepared_meal", "beverage", "ready_item"}

        for line in self:
            for product in line.allowed_substitute_product_ids:
                if product == line.component_product_tmpl_id:
                    raise ValidationError(
                        "Allowed substitutes cannot include the original component product."
                    )

                if product == line.combo_product_tmpl_id:
                    raise ValidationError(
                        "Allowed substitutes cannot include the combo product itself."
                    )

                if not product.is_menu_item:
                    raise ValidationError("Allowed substitutes must be menu items.")

                if product.restaurant_product_type not in allowed_types:
                    raise ValidationError(
                        "Allowed substitutes must be Prepared Meal, Beverage, or Ready Item."
                    )

                if not product.active:
                    raise ValidationError(
                        "Archived products cannot be used as allowed substitutes."
                    )
                    
    @api.constrains("combo_product_tmpl_id" , "component_product_tmpl_id")
    def _check_unique_component_per_combo(self):
        for line in self:
            if not line.combo_product_tmpl_id or not line.component_product_tmpl_id:
                continue

            duplicate = self.search_count([
                ("id", "!=", line.id),
                ("combo_product_tmpl_id", "=", line.combo_product_tmpl_id.id),
                ("component_product_tmpl_id", "=", line.component_product_tmpl_id.id),
            ])

            if duplicate:
                raise ValidationError(
                    "The same component cannot be added more than once to the same combo."
                )
            
    @api.onchange("is_swappable")
    def _onchange_is_swappable(self):
        for line in self:
            if not line.is_swappable:
                line.allowed_substitute_product_ids = [(5, 0, 0)]

    @api.onchange("is_upgradeable")
    def _onchange_is_upgradeable(self):
        for line in self:
            if not line.is_upgradeable:
                line.upgrade_price = 0.0

    @api.constrains("is_swappable", "allowed_substitute_product_ids")
    def _check_swappable_configuration(self):
        for line in self:
            if line.is_swappable and not line.allowed_substitute_product_ids:
                raise ValidationError(
                    "A swappable combo component must have at least one allowed substitute."
                )

            if not line.is_swappable and line.allowed_substitute_product_ids:
                raise ValidationError(
                    "Allowed substitutes can only be configured when the component is marked as swappable."
                )

    @api.constrains("is_upgradeable", "upgrade_price")
    def _check_upgrade_configuration(self):
        for line in self:
            if line.upgrade_price < 0:
                raise ValidationError("Upgrade price cannot be negative.")

            if line.is_upgradeable and line.upgrade_price <= 0:
                raise ValidationError(
                    "An upgradeable combo component must have an upgrade price greater than zero."
                )

            if not line.is_upgradeable and line.upgrade_price:
                raise ValidationError(
                    "Upgrade price can only be set when the component is marked as upgradeable."
                )
    
    def _is_operationally_used(self):
        """
        Future hook.
        Later this will check POS orders / sale orders / kitchen orders.
        For now, no combo line is considered used.
        """
        self.ensure_one()
        return False
    

    def unlink(self):
        for line in self:
            if line._is_operationally_used():
                raise ValidationError(
                    "You cannot delete a combo component after it has been used operationally."
                )

        return super().unlink()
        