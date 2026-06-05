from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    branch_id = fields.Many2one(
        "restaurant.branch",
        string="Restaurant Branch",
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        ondelete="restrict",
        help="Restaurant branch served by this POS configuration. Used for branch-aware product availability and future kitchen integration.",
    )

    restaurant_block_unavailable_products = fields.Boolean(
        string="Block Unavailable Products",
        default=False,
        help="If enabled, unavailable or unscheduled products cannot be added to the POS cart. If disabled, cashiers will only receive a warning and may continue."
    )

    @api.constrains('branch_id', 'company_id')
    def _check_branch_company(self):
        for config in self:
            if config.branch_id and config.company_id:
                if config.branch_id.company_id != config.company_id:
                    raise ValidationError(_(
                        "The selected branch '%s' belongs to company '%s', "
                        "but this POS is configured for company '%s'. "
                        "The branch and POS must belong to the same company."
                    ) % (
                        config.branch_id.name,
                        config.branch_id.company_id.name,
                        config.company_id.name,
                    ))

    @api.constrains('branch_id')
    def _check_branch_active(self):
        for config in self:
            if config.branch_id and not config.branch_id.active:
                raise ValidationError(_(
                    "The selected branch '%s' is archived. "
                    "Please select an active branch."
                ) % config.branch_id.name)

    @api.onchange('company_id')
    def _onchange_company_clear_branch(self):
        """Clear branch when company changes to avoid stale cross-company selection."""
        if self.branch_id and self.branch_id.company_id != self.company_id:
            self.branch_id = False

    def _get_restaurant_branch(self):
        """Return the restaurant.branch linked to this POS config, or an empty recordset."""
        self.ensure_one()
        return self.branch_id or self.env['restaurant.branch'].browse()

    def _has_restaurant_branch(self):
        """Check if this POS config is linked to a restaurant branch."""
        self.ensure_one()
        return bool(self.branch_id)

    def _get_product_pos_availability_payload(self, product, quantity=1.0, at_datetime=None):
        """Return POS availability payload for a product in this POS config branch context."""
        self.ensure_one()
        branch = self._get_restaurant_branch()
        if not branch:
            # Fallback safe payload if POS has no branch assigned
            return {
                "product_tmpl_id": product.product_tmpl_id.id if product._name == 'product.product' else product.id,
                "product_name": product.display_name,
                "branch_id": False,
                "branch_name": False,
                "company_id": False,
                "is_available": False,
                "available": False,
                "availability_state": "unknown",
                "reason_code": "branch_not_configured",
                "reason": "POS configuration has no restaurant branch assigned.",
                "checked_at": fields.Datetime.now(),
                "source_payload": {},
            }

        product_tmpl = product.product_tmpl_id if product._name == 'product.product' else product
        return product_tmpl._get_pos_availability_payload(
            branch=branch,
            quantity=quantity,
            at_datetime=at_datetime,
        )
