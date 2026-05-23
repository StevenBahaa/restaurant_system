# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantBranch(models.Model):
    _name = "restaurant.branch"
    _description = "Restaurant Branch"
    _order = "name"
    _rec_name = "name"

    name = fields.Char(string="Branch Name", required=True)
    code = fields.Char(
        string="Branch Code",
        required=True,
        help="Short unique code used for branch identification.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        help="Main warehouse or stock location representing this branch.",
    )
    manager_user_ids = fields.Many2many(
        "res.users",
        string="Branch Managers",
    )
    notes = fields.Text(string="Notes")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Branch code must be unique."),
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "Branch name must be unique per company.",
        ),
    ]

    @api.constrains("name", "code")
    def _check_name_code_whitespace(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError("Branch name should not be empty or whitespace.")
            if not record.code or not record.code.strip():
                raise ValidationError("Branch code should not be empty or whitespace.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "code" in vals and isinstance(vals["code"], str):
                vals["code"] = vals["code"].strip().upper()
            if "name" in vals and isinstance(vals["name"], str):
                vals["name"] = vals["name"].strip()
        return super(RestaurantBranch, self).create(vals_list)

    def write(self, vals):
        if "code" in vals and isinstance(vals["code"], str):
            vals["code"] = vals["code"].strip().upper()
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].strip()
        return super(RestaurantBranch, self).write(vals)
