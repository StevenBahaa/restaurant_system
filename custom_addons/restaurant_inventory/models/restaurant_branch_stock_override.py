from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantBranchStockOverride(models.Model):
    _name = "restaurant.branch.stock.override"
    _description = "Branch Stock Override"
    _order = "date_from desc, id desc"

    name = fields.Char(
        string="Reference",
        compute="_compute_name",
        store=True,
    )
    branch_id = fields.Many2one(
        "restaurant.branch",
        string="Branch",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        domain="[('is_menu_item', '=', True)]",
    )
    is_available = fields.Boolean(
        string="Force Available",
        required=True,
        default=False,
    )
    reason = fields.Text(
        string="Reason",
        required=True,
    )
    date_from = fields.Datetime(
        string="Date From",
        default=fields.Datetime.now,
        required=True,
    )
    date_to = fields.Datetime(
        string="Date To",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    note = fields.Text(
        string="Internal Notes",
    )

    @api.depends("branch_id", "product_tmpl_id", "is_available")
    def _compute_name(self):
        for rec in self:
            if rec.branch_id and rec.product_tmpl_id:
                status = "Available" if rec.is_available else "Unavailable"
                rec.name = f"{rec.branch_id.name} / {rec.product_tmpl_id.name} / {status}"
            else:
                rec.name = "New Override"

    @api.constrains("company_id", "branch_id")
    def _check_company_branch(self):
        for rec in self:
            if rec.branch_id.company_id and rec.company_id != rec.branch_id.company_id:
                raise ValidationError("Branch company must match override company.")

    @api.constrains("company_id", "product_tmpl_id")
    def _check_company_product(self):
        for rec in self:
            if rec.product_tmpl_id.company_id and rec.product_tmpl_id.company_id != rec.company_id:
                raise ValidationError("Product company must match override company or be shared (False).")

    @api.constrains("product_tmpl_id")
    def _check_menu_item(self):
        for rec in self:
            if not rec.product_tmpl_id.is_menu_item:
                raise ValidationError("Override can only be applied to menu items.")

    @api.constrains("reason")
    def _check_reason_not_empty(self):
        for rec in self:
            if not rec.reason or not str(rec.reason).strip():
                raise ValidationError("A valid reason is required for the override.")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to <= rec.date_from:
                raise ValidationError("Date To must be strictly greater than Date From.")

    @api.constrains("branch_id", "product_tmpl_id", "date_from", "date_to", "active", "company_id")
    def _check_overlap(self):
        for rec in self:
            if not rec.active:
                continue
            
            domain = [
                ("id", "!=", rec.id),
                ("branch_id", "=", rec.branch_id.id),
                ("product_tmpl_id", "=", rec.product_tmpl_id.id),
                ("company_id", "=", rec.company_id.id),
                ("active", "=", True),
            ]
            
            overrides = self.search(domain)
            for other in overrides:
                start1 = rec.date_from
                end1 = rec.date_to
                start2 = other.date_from
                end2 = other.date_to
                
                if not end1 and not end2:
                    raise ValidationError("Overlapping active overrides found for this branch and product.")
                elif not end1:
                    if start1 < end2:
                        raise ValidationError("Overlapping active overrides found for this branch and product.")
                elif not end2:
                    if start2 < end1:
                        raise ValidationError("Overlapping active overrides found for this branch and product.")
                else:
                    if start1 < end2 and start2 < end1:
                        raise ValidationError("Overlapping active overrides found for this branch and product.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "reason" in vals and isinstance(vals["reason"], str):
                vals["reason"] = vals["reason"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if "reason" in vals and isinstance(vals["reason"], str):
            vals["reason"] = vals["reason"].strip()
        return super().write(vals)
