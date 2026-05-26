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
            dupes = self.search(domain)
            if dupes:
                print(f"DUPE FOUND: self={line} id={line.id} dupes={dupes} dupe_ids={dupes.ids}")
                raise ValidationError("This kitchen station is already assigned to this product for the selected company.")
            
            duplicates_in_batch = self.filtered(
                lambda l: l.id != line.id
                and l.active
                and l.product_tmpl_id == line.product_tmpl_id
                and l.company_id == line.company_id
                and l.station_id == line.station_id
            )
            if duplicates_in_batch:
                print(f"BATCH DUPE: self={line} batch={duplicates_in_batch}")
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

    def _revalidate_products_kitchen_governance(self, products):
        """Helper to revalidate parent products after their assignment lines change."""
        if products:
            products._check_prepared_meal_station_governance()

    def write(self, vals):
        """Revalidate parent product governance if validity-affecting fields are modified."""
        products = self.mapped("product_tmpl_id")
        # Also capture new product if it is being moved to another product
        if "product_tmpl_id" in vals and vals["product_tmpl_id"]:
            products |= self.env["product.template"].browse(vals["product_tmpl_id"])
            
        result = super().write(vals)
        
        _validity_fields = {"active", "station_id", "company_id", "expected_prep_time", "product_tmpl_id"}
        if _validity_fields & vals.keys():
            self._revalidate_products_kitchen_governance(products)
            
        return result

    def unlink(self):
        """Revalidate parent product governance after unlinking."""
        products = self.mapped("product_tmpl_id")
        result = super().unlink()
        self._revalidate_products_kitchen_governance(products)
        return result
