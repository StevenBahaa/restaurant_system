from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RestaurantScheduleOverride(models.Model):
    _name = "restaurant.schedule.override"
    _description = "Restaurant Manual Schedule Override"
    _order = "date_from desc, id desc"

    name = fields.Char(
        string="Override Label",
        compute="_compute_name",
        store=True,
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        domain=[("is_menu_item", "=", True)],
        index=True,
    )
    branch_id = fields.Many2one(
        "restaurant.branch",
        string="Branch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    override_type = fields.Selection(
        [
            ("force_available", "Force Available"),
            ("force_unavailable", "Force Unavailable"),
        ],
        string="Override Type",
        required=True,
    )
    reason = fields.Text(
        string="Reason",
        required=True,
        help="Reason for this manual schedule override. Required and must not be blank.",
    )
    date_from = fields.Datetime(
        string="Valid From",
        required=True,
        default=fields.Datetime.now,
    )
    date_to = fields.Datetime(
        string="Valid Until",
        help="Leave empty for an open-ended override. If set, must be after Valid From.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    note = fields.Text(
        string="Internal Notes",
        help="Optional internal notes. Not displayed in override reason.",
    )

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------

    @api.depends("branch_id", "product_tmpl_id", "override_type")
    def _compute_name(self):
        type_labels = {
            "force_available": "Force Available",
            "force_unavailable": "Force Unavailable",
        }
        for rec in self:
            branch = rec.branch_id.name or ""
            product = rec.product_tmpl_id.display_name or ""
            otype = type_labels.get(rec.override_type, "")
            rec.name = " / ".join(filter(None, [branch, product, otype])) or "Draft Override"

    # -------------------------------------------------------------------------
    # ORM overrides
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "reason" in vals and vals["reason"]:
                vals["reason"] = vals["reason"].strip()
        return super().create(vals_list)

    def write(self, vals):
        if "reason" in vals and vals["reason"]:
            vals["reason"] = vals["reason"].strip()
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("branch_id", "company_id")
    def _check_branch_company_match(self):
        for rec in self:
            if rec.branch_id and rec.company_id:
                if rec.branch_id.company_id != rec.company_id:
                    raise ValidationError(
                        "The selected branch belongs to company "
                        f"'{rec.branch_id.company_id.name}', but the override "
                        f"company is '{rec.company_id.name}'. "
                        "Branch and company must match."
                    )

    @api.constrains("product_tmpl_id")
    def _check_product_is_menu_item(self):
        for rec in self:
            if rec.product_tmpl_id and not rec.product_tmpl_id.is_menu_item:
                raise ValidationError(
                    f"Product '{rec.product_tmpl_id.display_name}' is not a menu item. "
                    "Schedule overrides can only be applied to menu items "
                    "(is_menu_item = True)."
                )

    @api.constrains("product_tmpl_id", "company_id")
    def _check_product_company_match(self):
        for rec in self:
            product = rec.product_tmpl_id
            if product and product.company_id and product.company_id != rec.company_id:
                raise ValidationError(
                    f"Product '{product.display_name}' belongs to company "
                    f"'{product.company_id.name}'. "
                    f"It cannot be overridden under company '{rec.company_id.name}'. "
                    "Shared products (no company) are allowed across companies."
                )

    @api.constrains("reason")
    def _check_reason_not_blank(self):
        for rec in self:
            if not rec.reason or not rec.reason.strip():
                raise ValidationError(
                    "Override reason cannot be empty or whitespace only. "
                    "Please provide a meaningful reason for this override."
                )

    @api.constrains("date_from", "date_to")
    def _check_date_range(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to <= rec.date_from:
                raise ValidationError(
                    "'Valid Until' must be strictly after 'Valid From'. "
                    "Please correct the date range."
                )

    @api.constrains(
        "product_tmpl_id", "branch_id", "company_id", "date_from", "date_to", "active"
    )
    def _check_no_overlapping_active_overrides(self):
        """Prevent overlapping active overrides for the same product/branch/company."""
        for rec in self:
            if not rec.active:
                continue
            # Use a direct SQL query to check for overlapping active overrides
            # without flushing pending writes (which causes phantom records
            # when the constraint is about to raise a ValidationError).
            sql = """
                SELECT id, name, date_from, date_to
                FROM restaurant_schedule_override
                WHERE id != %(id)s
                  AND product_tmpl_id = %(product_id)s
                  AND branch_id = %(branch_id)s
                  AND company_id = %(company_id)s
                  AND active = TRUE
            """
            params = {
                'id': rec.id or 0,
                'product_id': rec.product_tmpl_id.id,
                'branch_id': rec.branch_id.id,
                'company_id': rec.company_id.id,
            }
            self.env.cr.execute(sql, params)
            existing_rows = self.env.cr.fetchall()
            for (other_id, other_name, other_from, other_to) in existing_rows:
                if self._date_windows_overlap(
                    rec.date_from, rec.date_to, other_from, other_to
                ):
                    raise ValidationError(
                        f"An active schedule override already exists for product "
                        f"'{rec.product_tmpl_id.display_name}' at branch "
                        f"'{rec.branch_id.name}' with overlapping validity dates "
                        f"(existing: {other_name}). "
                        "Please deactivate or expire the existing override first."
                    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _date_windows_overlap(self, from_a, to_a, from_b, to_b):
        """Returns True if two datetime windows overlap.
        None end date means open-ended (no expiry).
        Normalizes timezone-aware datetimes (e.g. from psycopg2) to naive UTC.
        """
        def _naive(dt):
            if dt is None:
                return None
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                import pytz
                return dt.astimezone(pytz.utc).replace(tzinfo=None)
            return dt

        from_a = _naive(from_a)
        to_a = _naive(to_a)
        from_b = _naive(from_b)
        to_b = _naive(to_b)

        # A ends before B starts → no overlap
        if to_a and to_a <= from_b:
            return False
        # B ends before A starts → no overlap
        if to_b and to_b <= from_a:
            return False
        return True
