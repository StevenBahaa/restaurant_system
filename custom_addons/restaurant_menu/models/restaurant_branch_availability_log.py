# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RestaurantBranchAvailabilityLog(models.Model):
    _name = "restaurant.branch.availability.log"
    _description = "Branch Availability Change Log"
    _order = "changed_on desc, id desc"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    changed_by_id = fields.Many2one(
        "res.users",
        string="Changed By",
        required=True,
        default=lambda self: self.env.user,
    )
    changed_on = fields.Datetime(
        string="Changed On",
        required=True,
        default=fields.Datetime.now,
    )
    old_mode = fields.Char(string="Old Availability Mode")
    new_mode = fields.Char(string="New Availability Mode")
    old_available_branch_names = fields.Text(string="Old Available Branches")
    new_available_branch_names = fields.Text(string="New Available Branches")
    old_excluded_branch_names = fields.Text(string="Old Excluded Branches")
    new_excluded_branch_names = fields.Text(string="New Excluded Branches")
    old_available_from = fields.Date(string="Old Available From")
    new_available_from = fields.Date(string="New Available From")
    old_available_until = fields.Date(string="Old Available Until")
    new_available_until = fields.Date(string="New Available Until")
    old_unavailable_reason = fields.Text(string="Old Unavailable Reason")
    new_unavailable_reason = fields.Text(string="New Unavailable Reason")
    change_summary = fields.Text(string="Change Summary")
