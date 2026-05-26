from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    kitchen_station_line_ids = fields.One2many(
        "restaurant.product.kitchen.station.line",
        "product_tmpl_id",
        string="Kitchen Station Assignments"
    )

    # -------------------------------------------------------------------------
    # Shared validity predicate
    # -------------------------------------------------------------------------

    def _is_valid_kitchen_station_line(self, line, required_company):
        """Return True if a station line satisfies all validity criteria.

        Used by both the prep-time resolver and the governance check so
        the criteria stay in a single place and cannot silently diverge.
        """
        return (
            line.active
            and line.station_id.active
            and line.expected_prep_time > 0
            and line.company_id == required_company
        )

    # -------------------------------------------------------------------------
    # Prep-time resolvers
    # -------------------------------------------------------------------------

    def _get_active_kitchen_station_lines(self, company=None, branch=None):
        """Return active station lines applicable to this product.

        Args:
            company: res.company record to filter by. Defaults to env.company.
            branch:  restaurant.branch record. When supplied:
                     - stations with empty branch_ids apply to all company branches.
                     - stations whose branch_ids contain the branch are included.
                     - stations restricted to other branches are excluded.
                     If branch.company_id does not match the target company, an
                     empty recordset is returned immediately.
        """
        self.ensure_one()
        target_company = company or self.env.company

        if branch and branch.company_id and branch.company_id != target_company:
            return self.env["restaurant.product.kitchen.station.line"]

        lines = self.kitchen_station_line_ids.filtered(
            lambda l: self._is_valid_kitchen_station_line(l, target_company)
        )

        if branch:
            lines = lines.filtered(
                lambda l: not l.station_id.branch_ids or branch in l.station_id.branch_ids
            )

        return lines

    def _get_expected_prep_time(self, company=None, branch=None):
        """Return the maximum expected_prep_time across applicable station lines.

        Returns 0 for product types that do not use station assignment
        (combo, ingredient, packaging, semi_finished) and for products
        with no applicable lines.

        Note: combo component prep-time resolving is future scope and is
        intentionally not implemented in this step.
        """
        self.ensure_one()
        allowed_types = ["prepared_meal", "beverage", "ready_item"]
        if self.restaurant_product_type not in allowed_types:
            return 0

        lines = self._get_active_kitchen_station_lines(company=company, branch=branch)
        if lines:
            return max(lines.mapped("expected_prep_time"))
        return 0

    def _get_kitchen_station_payload(self, company=None, branch=None):
        """Return a structured payload for future POS/KDS/order-routing use.

        The payload is backend-only. It is not wired to any POS, order, or
        real-time routing model in this step.

        Return shape::

            {
                "product_tmpl_id": <int>,
                "expected_prep_time": <int>,   # max across applicable lines
                "station_lines": [
                    {
                        "station_id": <int>,
                        "station_name": <str>,
                        "station_code": <str>,
                        "expected_prep_time": <int>,
                        "sequence": <int>,
                    },
                    ...
                ],
            }

        Lines are sorted deterministically by (sequence, id).
        """
        self.ensure_one()
        lines = self._get_active_kitchen_station_lines(company=company, branch=branch)
        sorted_lines = lines.sorted(key=lambda l: (l.sequence, l.id))

        return {
            "product_tmpl_id": self.id,
            "expected_prep_time": self._get_expected_prep_time(company=company, branch=branch),
            "station_lines": [
                {
                    "station_id": line.station_id.id,
                    "station_name": line.station_id.name,
                    "station_code": line.station_id.code,
                    "expected_prep_time": line.expected_prep_time,
                    "sequence": line.sequence,
                }
                for line in sorted_lines
            ],
        }

    # -------------------------------------------------------------------------
    # Governance
    # -------------------------------------------------------------------------

    def _check_prepared_meal_station_governance(self):
        """Validate prepared_meal station requirements for operationally sellable products.

        A product is considered operationally sellable when available_in_pos=True
        or sale_ok=True, as established by restaurant_menu.product_template_base.

        This method is called from write() only. create() is intentionally
        excluded so that new prepared_meal records can be saved as configuration
        drafts before stations are configured.
        """
        for product in self:
            if product.restaurant_product_type != "prepared_meal":
                continue
            if not (product.available_in_pos or product.sale_ok):
                continue
            required_company = product.company_id or self.env.company
            valid_lines = product.kitchen_station_line_ids.filtered(
                lambda l: self._is_valid_kitchen_station_line(l, required_company)
            )
            if not valid_lines:
                raise ValidationError(
                    "Prepared meals must have at least one active kitchen station "
                    "assignment before they can be made available for sale."
                )

    def write(self, vals):
        """Override write to enforce kitchen station governance.

        Governance fires only when one of the relevant fields is explicitly
        written. create() is not overridden, so new products can be saved
        freely as draft/configuration records.
        """
        result = super().write(vals)
        _governance_fields = {
            "available_in_pos",
            "sale_ok",
            "restaurant_product_type",
            "kitchen_station_line_ids",
            "company_id",
        }
        if _governance_fields & vals.keys():
            self._check_prepared_meal_station_governance()
        return result
