# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError

class RestaurantBranchPriceBulkWizard(models.TransientModel):
    _name = "restaurant.branch.price.bulk.wizard"
    _description = "Bulk Branch/Channel Price Update Wizard"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Products",
        required=True,
        domain="[('is_menu_item', '=', True)]",
    )
    branch_id = fields.Many2one(
        "restaurant.branch",
        string="Branch",
    )
    channel = fields.Selection(
        [
            ("dine_in", "Dine-In"),
            ("takeaway", "Takeaway"),
            ("delivery_app", "Delivery App"),
        ],
        string="Channel",
    )
    update_mode = fields.Selection(
        [
            ("set_fixed_price", "Set Fixed Price"),
            ("increase_fixed_amount", "Increase by Fixed Amount"),
            ("decrease_fixed_amount", "Decrease by Fixed Amount"),
            ("increase_percentage", "Increase by Percentage"),
            ("decrease_percentage", "Decrease by Percentage"),
        ],
        string="Update Mode",
        required=True,
        default="set_fixed_price",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    fixed_price = fields.Monetary(string="Fixed Price", currency_field="currency_id")
    amount = fields.Monetary(string="Amount", currency_field="currency_id")
    percentage = fields.Float(string="Percentage (%)")

    date_from = fields.Date(string="Start Date")
    date_until = fields.Date(string="End Date")
    note = fields.Text(string="Internal Note")

    product_count = fields.Integer(
        compute="_compute_product_count",
        string="Product Count",
    )

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_tmpl_ids)

    def _check_wizard_permissions(self):
        if self.env.su:
            return
        if not (self.env.user.has_group("restaurant_base.group_restaurant_operations_manager") or
                self.env.user.has_group("restaurant_menu.group_restaurant_pricing_manager")):
            raise AccessError("You do not have permission to bulk update branch/channel pricing.")

    def action_apply_price_update(self):
        self.ensure_one()
        self._check_wizard_permissions()

        # 1. Product requirement
        if not self.product_tmpl_ids:
            raise ValidationError("Please select at least one product.")

        # 2. Scope requirement
        if not self.branch_id and not self.channel:
            raise ValidationError("At least one of Branch or Channel must be set.")

        # 3. Dates validation
        if self.date_from and self.date_until and self.date_from > self.date_until:
            raise ValidationError("Start Date cannot be after End Date.")

        # 4, 5, 6. Value validation
        if self.update_mode == "set_fixed_price" and self.fixed_price <= 0:
            raise ValidationError("Fixed Price must be greater than zero.")
        if self.update_mode in ["increase_fixed_amount", "decrease_fixed_amount"] and self.amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        if self.update_mode in ["increase_percentage", "decrease_percentage"] and self.percentage <= 0:
            raise ValidationError("Percentage must be greater than zero.")

        # 9. Branch validations
        if self.branch_id:
            if not self.branch_id.active:
                raise ValidationError("Selected branch is archived.")
            
            if not self.env.su and self.branch_id.company_id.id not in self.env.user.company_ids.ids:
                raise ValidationError(f"You cannot set pricing for branch '{self.branch_id.name}' because it belongs to a company you do not have access to.")

            # Validate branch compatibility with every selected product
            for product in self.product_tmpl_ids:
                if product.company_id and product.company_id.id != self.branch_id.company_id.id:
                    raise ValidationError(f"Product '{product.name}' belongs to company '{product.company_id.name}', which is incompatible with branch '{self.branch_id.name}'.")

        price_line_model = self.env["restaurant.branch.price.line"]

        for product in self.product_tmpl_ids:
            # 1. Determine base price
            final_price = 0.0
            if self.update_mode == "set_fixed_price":
                final_price = self.fixed_price
            else:
                price_date = self.date_from or fields.Date.context_today(self)
                base_price = product._get_price_for_branch(
                    branch=self.branch_id,
                    channel=self.channel,
                    price_date=price_date
                )
                
                if self.update_mode == "increase_fixed_amount":
                    final_price = base_price + self.amount
                elif self.update_mode == "decrease_fixed_amount":
                    final_price = base_price - self.amount
                elif self.update_mode == "increase_percentage":
                    final_price = base_price * (1 + (self.percentage / 100.0))
                elif self.update_mode == "decrease_percentage":
                    final_price = base_price * (1 - (self.percentage / 100.0))

            if final_price <= 0:
                raise ValidationError(f"The resulting price for product '{product.name}' is zero or negative ({final_price}). Price must be strictly positive.")

            # 3. Look for exact matching rule
            domain = [
                ("product_tmpl_id", "=", product.id),
                ("branch_id", "=", self.branch_id.id),
                ("channel", "=", self.channel),
                ("date_from", "=", self.date_from),
                ("date_until", "=", self.date_until),
                ("active", "=", True)
            ]
            exact_match = price_line_model.search(domain, limit=1)

            # Do not use sudo for pricing writes, allow normal ORM to trigger history/security
            if exact_match:
                write_vals = {"price": final_price}
                if self.note:
                    write_vals["note"] = self.note
                exact_match.write(write_vals)
            else:
                create_vals = {
                    "product_tmpl_id": product.id,
                    "branch_id": self.branch_id.id,
                    "channel": self.channel,
                    "price": final_price,
                    "date_from": self.date_from,
                    "date_until": self.date_until,
                }
                if self.note:
                    create_vals["note"] = self.note
                price_line_model.create(create_vals)

        return {"type": "ir.actions.act_window_close"}
