from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantKitchenStation(models.Model):
    _name = "restaurant.kitchen.station"
    _description = "Kitchen Station"
    _order = "sequence, name"

    name = fields.Char(string="Station Name", required=True)
    code = fields.Char(
        string="Station Code",
        required=True,
        help="Unique short code for the station."
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )
    branch_ids = fields.Many2many(
        "restaurant.branch",
        string="Available in Branches",
        help="If empty, available in all branches of the company. If set, restricts availability."
    )
    station_type = fields.Selection(
        [
            ("prep", "Preparation"),
            ("bar", "Bar / Beverages"),
            ("packaging", "Packaging / Dispatch"),
            ("staging", "Staging / Ready")
        ],
        string="Station Type",
        required=True,
        default="prep"
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Notes")

    _sql_constraints = [
        ("code_company_uniq", "unique(code, company_id)", "Station code must be unique per company."),
        ("name_company_uniq", "unique(name, company_id)", "Station name must be unique per company."),
    ]

    @api.constrains("name", "code")
    def _check_name_code_whitespace(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError("Station name cannot be empty or whitespace.")
            if not record.code or not record.code.strip():
                raise ValidationError("Station code cannot be empty or whitespace.")

    @api.constrains("company_id", "branch_ids")
    def _check_branch_company_compatibility(self):
        for record in self:
            if record.branch_ids:
                invalid_branches = record.branch_ids.filtered(lambda b: b.company_id != record.company_id)
                if invalid_branches:
                    branch_names = ", ".join(invalid_branches.mapped("name"))
                    raise ValidationError(f"The following branches do not belong to the station's company ({record.company_id.name}): {branch_names}")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "code" in vals and isinstance(vals["code"], str):
                vals["code"] = vals["code"].strip().upper()
            if "name" in vals and isinstance(vals["name"], str):
                vals["name"] = vals["name"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals and isinstance(vals["code"], str):
            vals["code"] = vals["code"].strip().upper()
        if "name" in vals and isinstance(vals["name"], str):
            vals["name"] = vals["name"].strip()
        return super().write(vals)
