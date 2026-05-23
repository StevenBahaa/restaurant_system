# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantBranchAvailabilityBulkWizard(models.TransientModel):
    _name = "restaurant.branch.availability.bulk.wizard"
    _description = "Bulk Branch Availability Wizard"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        string="Products",
        required=True,
        domain="[('is_menu_item', '=', True)]",
    )

    branch_availability_mode = fields.Selection(
        [
            ("all_branches", "Available in All Branches"),
            ("selected_branches", "Available Only in Selected Branches"),
            ("excluded_branches", "Available in All Except Selected Branches"),
        ],
        string="Branch Availability",
        required=True,
        default="all_branches",
    )

    branch_available_ids = fields.Many2many(
        "restaurant.branch",
        "branch_avail_bulk_wizard_available_rel",
        "wizard_id",
        "branch_id",
        string="Available Branches",
        domain="[('active', '=', True)]",
    )

    branch_excluded_ids = fields.Many2many(
        "restaurant.branch",
        "branch_avail_bulk_wizard_excluded_rel",
        "wizard_id",
        "branch_id",
        string="Excluded Branches",
        domain="[('active', '=', True)]",
    )

    branch_available_from = fields.Date(string="Available From")
    branch_available_until = fields.Date(string="Available Until")
    branch_unavailable_reason = fields.Text(string="Branch Unavailable Reason")

    apply_dates = fields.Boolean(
        string="Update Availability Dates",
        default=False,
        help="Enable this to update Available From/Until on selected products.",
    )

    apply_reason = fields.Boolean(
        string="Update Unavailable Reason",
        default=False,
        help="Enable this to update the branch unavailable reason on selected products.",
    )

    product_count = fields.Integer(
        compute="_compute_product_count",
        string="Product Count",
    )

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_tmpl_ids)

    @api.onchange("branch_availability_mode")
    def _onchange_branch_availability_mode(self):
        if self.branch_availability_mode == "all_branches":
            self.branch_available_ids = [(5, 0, 0)]
            self.branch_excluded_ids = [(5, 0, 0)]
        elif self.branch_availability_mode == "selected_branches":
            self.branch_excluded_ids = [(5, 0, 0)]
        elif self.branch_availability_mode == "excluded_branches":
            self.branch_available_ids = [(5, 0, 0)]

    def action_apply_branch_availability(self):
        self.ensure_one()
        if not self.product_tmpl_ids:
            raise ValidationError("Please select at least one product.")

        if self.branch_availability_mode == "selected_branches" and not self.branch_available_ids:
            raise ValidationError("At least one branch must be selected for 'Selected Branches Only' availability mode.")

        if self.branch_availability_mode == "excluded_branches" and not self.branch_excluded_ids:
            raise ValidationError("At least one branch must be excluded for 'All Branches Except Excluded' availability mode.")

        if self.apply_dates:
            if self.branch_available_from and self.branch_available_until:
                if self.branch_available_from > self.branch_available_until:
                    raise ValidationError("Available From date must be before or equal to Available Until date.")

        # Build values dictionary to apply
        vals = {
            "branch_availability_mode": self.branch_availability_mode,
        }

        if self.branch_availability_mode == "all_branches":
            vals["branch_available_ids"] = [(5, 0, 0)]
            vals["branch_excluded_ids"] = [(5, 0, 0)]
        elif self.branch_availability_mode == "selected_branches":
            vals["branch_available_ids"] = [(6, 0, self.branch_available_ids.ids)]
            vals["branch_excluded_ids"] = [(5, 0, 0)]
        elif self.branch_availability_mode == "excluded_branches":
            vals["branch_available_ids"] = [(5, 0, 0)]
            vals["branch_excluded_ids"] = [(6, 0, self.branch_excluded_ids.ids)]

        if self.apply_dates:
            vals["branch_available_from"] = self.branch_available_from
            vals["branch_available_until"] = self.branch_available_until

        if self.apply_reason:
            vals["branch_unavailable_reason"] = self.branch_unavailable_reason

        # Write to products (using regular write operation to trigger constraints and security)
        self.product_tmpl_ids.write(vals)

        return {"type": "ir.actions.act_window_close"}
