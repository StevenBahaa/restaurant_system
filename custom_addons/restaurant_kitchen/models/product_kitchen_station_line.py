from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantProductKitchenStationLine(models.Model):
    _name = "restaurant.product.kitchen.station.line"
    _description = "Product Kitchen Station Assignment"
    _order = "sequence, id"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Menu Item",
        required=True,
        ondelete="cascade",
        index=True
    )
    station_id = fields.Many2one(
        "restaurant.kitchen.station",
        string="Kitchen Station",
        required=True,
        index=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    expected_prep_time = fields.Integer(
        string="Expected Prep Time (Minutes)",
        required=True
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text(string="Notes")

    @api.constrains("expected_prep_time")
    def _check_expected_prep_time(self):
        for line in self:
            if line.expected_prep_time <= 0:
                raise ValidationError("Expected preparation time must be greater than 0 minutes.")

    @api.constrains("station_id", "company_id")
    def _check_station_company(self):
        for line in self:
            if line.station_id and line.station_id.company_id != line.company_id:
                raise ValidationError("The selected kitchen station belongs to a different company.")

    @api.constrains("product_tmpl_id", "company_id")
    def _check_product_company(self):
        for line in self:
            if not line.product_tmpl_id or not line.company_id:
                continue
            if line.product_tmpl_id.company_id:
                if line.company_id != line.product_tmpl_id.company_id:
                    raise ValidationError("The selected company must match the product's company.")
            else:
                if line.company_id not in self.env.companies:
                    raise ValidationError("The selected company is not in your allowed companies.")

    @api.constrains("product_tmpl_id", "station_id", "company_id", "active")
    def _check_duplicate_assignment(self):
        for line in self:
            if not line.active or not line.product_tmpl_id or not line.station_id or not line.company_id:
                continue
            domain = [
                ("id", "!=", line.id),
                ("product_tmpl_id", "=", line.product_tmpl_id.id),
                ("company_id", "=", line.company_id.id),
                ("station_id", "=", line.station_id.id),
                ("active", "=", True),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError("This kitchen station is already assigned to this product for the selected company.")
            
            duplicates_in_batch = self.filtered(
                lambda l: l is not line
                and l.active
                and l.product_tmpl_id == line.product_tmpl_id
                and l.company_id == line.company_id
                and l.station_id == line.station_id
            )
            if duplicates_in_batch:
                raise ValidationError("This kitchen station is already assigned to this product for the selected company.")

    @api.constrains("station_id", "active")
    def _check_station_active(self):
        for line in self:
            if line.active and line.station_id and not line.station_id.active:
                raise ValidationError("Cannot assign an inactive kitchen station.")

    @api.constrains("product_tmpl_id")
    def _check_product_is_menu_item(self):
        for line in self:
            if line.product_tmpl_id and not line.product_tmpl_id.is_menu_item:
                raise ValidationError("Kitchen station assignments can only be configured for menu items.")

    @api.constrains("product_tmpl_id")
    def _check_product_type(self):
        allowed_types = ["prepared_meal", "beverage", "ready_item"]
        for line in self:
            if not line.product_tmpl_id:
                continue
            if line.product_tmpl_id.restaurant_product_type not in allowed_types:
                raise ValidationError("This product type cannot be assigned to kitchen stations.")
