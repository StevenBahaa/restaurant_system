# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    combo_component_line_ids = fields.One2many(
        "restaurant.combo.line",
        "combo_product_tmpl_id",
        string="Combo Components",
        tracking=True,
    )

    combo_component_count = fields.Integer(
        string="Combo Component Count",
        compute="_compute_combo_totals",
        store=True, 
        tracking=True,
    )

    combo_individual_total_price = fields.Float(
        string="Individual Components Total",
        compute="_compute_combo_totals",
        store=True,
        tracking=True,
    )

    combo_saving_amount = fields.Float(
        string="Combo Saving",
        compute="_compute_combo_totals",
        store=True,
        tracking=True,
    )

    combo_is_valid = fields.Boolean(
        string="Combo Is Valid",
        compute="_compute_combo_validation",
        store=True,
        tracking=True,
    )

    combo_validation_message = fields.Char(
        string="Combo Validity Message",
        compute="_compute_combo_validation",
        store=True,
    )

    combo_is_available = fields.Boolean(
        string="Combo Available",
        compute="_compute_combo_availability",
        store=True,
    )

    combo_unavailable_reason = fields.Text(
        string="Combo Unavailable Reason",
        compute="_compute_combo_availability",
        store=True,
    )

    combo_total_cost = fields.Float(
        string="Combo Total Cost",
        compute="_compute_combo_cost",
        store=True,
    )

    combo_food_cost_percentage = fields.Float(
        string="Combo Food Cost %",
        compute="_compute_combo_cost",
        store=True,
    )

    combo_cost_warning = fields.Boolean(
        string="Combo Cost Warning",
        compute="_compute_combo_cost_warning",
        store=True,
    )

    combo_cost_warning_message = fields.Text(
        string="Combo Cost Warning Message",
        compute="_compute_combo_cost_warning",
        store=True,
    )

    @api.depends(
        "restaurant_product_type",
        "combo_total_cost",
        "combo_food_cost_percentage",
        "list_price",
    )
    def _compute_combo_cost_warning(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_cost_warning = False
                product.combo_cost_warning_message = False
            else:
                if product.combo_food_cost_percentage > 60.0:
                    product.combo_cost_warning = True
                    product.combo_cost_warning_message = "Combo food cost percentage is high. Review the combo price or component costs."
                else:
                    product.combo_cost_warning = False
                    product.combo_cost_warning_message = False

    @api.depends(
        "restaurant_product_type",
        "list_price",
        "combo_component_line_ids",
        "combo_component_line_ids.quantity",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.standard_price",
    )
    def _compute_combo_cost(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_total_cost = 0.0
                product.combo_food_cost_percentage = 0.0
                continue

            total_cost = 0.0

            for line in product.combo_component_line_ids:
                component_cost = product._get_combo_component_resolved_cost(
                    line.component_product_tmpl_id
                )
                total_cost += component_cost * line.quantity

            product.combo_total_cost = total_cost

            if product.list_price > 0:
                product.combo_food_cost_percentage = (total_cost / product.list_price) * 100
            else:
                product.combo_food_cost_percentage = 0.0

    def _get_combo_component_resolved_cost(self, component_product):
        self.ensure_one()
        if not component_product:
            return 0.0
        return component_product.standard_price

    @api.depends(
        "restaurant_product_type",
        "combo_is_valid",
        "combo_validation_message",
        "combo_component_line_ids",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.active",
        "combo_component_line_ids.component_product_tmpl_id.sale_ok",
    )
    def _compute_combo_availability(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_is_available = True
                product.combo_unavailable_reason = False
                continue

            availability = product._get_combo_availability_status()

            product.combo_is_available = availability["available"]
            product.combo_unavailable_reason = availability["reason"]

    @api.depends(
        "restaurant_product_type",
        "sale_ok",
        "active",
        "list_price",
        "combo_component_line_ids",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.active",
        "combo_component_line_ids.component_product_tmpl_id.is_menu_item",
        "combo_component_line_ids.component_product_tmpl_id.restaurant_product_type",
        "combo_component_line_ids.quantity",
    )
    def _compute_combo_validation(self):
        allowed_types = {"prepared_meal", "beverage", "ready_item"}

        for product in self:
            message = []

            if product.restaurant_product_type != "combo":
                product.combo_is_valid = True
                product.combo_validation_message = False
                continue

            if product.list_price <= 0:
                message.append("Combo price must be greater than zero.")
            
            if not product.sale_ok:
                message.append("Combo must be sellable.")
            
            if len(product.combo_component_line_ids) < 2:
                message.append("Combo must contain at least 2 components.")

            for line in product.combo_component_line_ids:
                component = line.component_product_tmpl_id

                if not component:
                    message.append("Each combo line must have a component product.")
                    continue

                if not component.active:
                    message.append(f"Component '{component.display_name}' is archived.")
                
                if not component.is_menu_item:
                    message.append(f"Component '{component.display_name}' must be a menu item.")

                if component.restaurant_product_type not in allowed_types:
                    message.append(
                        f"Component '{component.display_name}' has invalid restaurant product type."
                    )   
                
                if line.quantity <= 0:
                    message.append(f"Component '{component.display_name}' quantity must be greater than zero.")

            product.combo_is_valid = not bool(message)
            product.combo_validation_message = "\n".join(message) if message else False

    @api.depends(
        "restaurant_product_type",
        "list_price",
        "combo_component_line_ids",
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

            product._compute_combo_validation()

            if not product.combo_is_valid:
                raise ValidationError(
                    product.combo_validation_message or "Combo meal is not operationally valid."
                )

        return True

    def _is_combo_operationally_used(self):
        self.ensure_one()
        return False

    def unlink(self):
        for product in self:
            if product.restaurant_product_type == "combo" and product._is_combo_operationally_used():
                raise ValidationError(
                    "You cannot delete a combo meal after it has been used operationally. Archive it instead."
                )

        return super().unlink()

    def _get_combo_component_lines(self):
        self.ensure_one()

        if self.restaurant_product_type != "combo":
            return self.env["restaurant.combo.line"]

        return self.combo_component_line_ids.sorted(lambda line: (line.sequence, line.id))

    def _get_combo_component_products(self):
        self.ensure_one()

        return self._get_combo_component_lines().mapped("component_product_tmpl_id")

    def _get_combo_individual_total_price(self):
        self.ensure_one()

        total = 0.0
        for line in self._get_combo_component_lines():
            total += line.component_product_tmpl_id.list_price * line.quantity

        return total

    def _get_combo_saving_amount(self):
        self.ensure_one()

        return self._get_combo_individual_total_price() - self.list_price

    def _prepare_combo_operational_payload(self):
        self.ensure_one()
        self._check_combo_operational_validity()
        availability = self._get_combo_availability_status()

        payload = {
            "combo_product_tmpl_id": self.id,
            "combo_name": self.display_name,
            "combo_price": self.list_price,
            "individual_total_price": self._get_combo_individual_total_price(),
            "saving_amount": self._get_combo_saving_amount(),
            "is_available": availability["available"],
            "unavailable_reason": availability["reason"] or "",
            "components": [],
        }

        for line in self._get_combo_component_lines():
            payload["components"].append({
                "line_id": line.id,
                "component_product_tmpl_id": line.component_product_tmpl_id.id,
                "component_name": line.component_product_tmpl_id.display_name,
                "quantity": line.quantity,
                "allow_customization": line.allow_customization,
                "is_swappable": line.is_swappable,
                "allowed_substitute_product_tmpl_ids": line.allowed_substitute_product_ids.ids,
                "is_upgradeable": line.is_upgradeable,
                "upgrade_price": line.upgrade_price,
                "notes": line.notes or "",
            })

        return payload

    def _get_combo_availability_status(self):
        self.ensure_one()

        if self.restaurant_product_type != "combo":
            return {
                "available": True,
                "reason": False,
            }

        if not self.combo_is_valid:
            return {
                "available": False,
                "reason": self.combo_validation_message or "Combo meal is not operationally valid.",
            }

        unavailable_reasons = []

        for line in self._get_combo_component_lines():
            component = line.component_product_tmpl_id

            if not component:
                unavailable_reasons.append("Combo contains an empty component line.")
                continue

            if not component.sale_ok:
                unavailable_reasons.append(
                    f"Component '{component.display_name}' is not sellable."
                )

        if unavailable_reasons:
            return {
                "available": False,
                "reason": "\n".join(unavailable_reasons),
            }

        return {
            "available": True,
            "reason": False,
        }

    def write(self, vals):
        validation_trigger_fields = {
            "active",
            "sale_ok",
            "list_price",
            "restaurant_product_type",
            "combo_component_line_ids",
        }

        protected_combo_fields = {
            "restaurant_product_type",
            "combo_component_line_ids",
        }

        for product in self:
            if product.restaurant_product_type == "combo":
                if protected_combo_fields.intersection(vals.keys()):
                    if product._is_combo_operationally_used():
                        raise ValidationError(
                            "You cannot modify combo structure after operational usage."
                        )

        res = super().write(vals)

        for product in self:
            if product.restaurant_product_type == "combo":
                if product.active and validation_trigger_fields.intersection(vals.keys()):
                    product._check_combo_operational_validity()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for product in products:
            if product.restaurant_product_type == "combo" and product.active:
                product._check_combo_operational_validity()
        return products
