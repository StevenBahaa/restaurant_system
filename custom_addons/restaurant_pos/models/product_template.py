from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_pos_availability_payload(self, branch=None, quantity=1.0, at_datetime=None):
        """
        Return a POS-context availability payload for this product.
        Wraps the unified resolver (_get_unified_availability_payload).
        """
        self.ensure_one()

        at_datetime = at_datetime or fields.Datetime.now()
        checked_at = at_datetime

        if not quantity or quantity <= 0:
            quantity = 1.0

        if not branch:
            return {
                "product_tmpl_id": self.id,
                "product_name": self.display_name,
                "branch_id": False,
                "branch_name": False,
                "company_id": False,
                "is_available": False,
                "available": False,  # frontend alias
                "availability_state": "unknown",
                "reason_code": "missing_pos_branch",
                "reason": "No branch context provided to evaluate POS availability.",
                "checked_at": checked_at,
                "source_payload": {},
            }

        # Call unified resolver
        unified = self._get_unified_availability_payload(
            branch=branch,
            at_datetime=at_datetime,
            quantity=quantity,
            evaluate_all=True,
        )

        is_available = unified.get("is_available", False)
        reason_code = unified.get("reason_code", "unknown")
        
        # Map state
        if is_available:
            state = "available"
        elif reason_code in ("out_of_stock", "critical_ingredient_out_of_stock", "missing_recipe"):
            state = "out_of_stock"
        elif reason_code == "schedule_unavailable":
            state = "schedule_unavailable"
        elif reason_code == "branch_unavailable":
            state = "branch_unavailable"
        elif reason_code == "branch_not_provided":
            state = "unknown"
        else:
            state = "unavailable"

        return {
            "product_tmpl_id": self.id,
            "product_name": self.display_name,
            "branch_id": branch.id,
            "branch_name": branch.display_name,
            "company_id": branch.company_id.id,
            "is_available": is_available,
            "available": is_available,  # frontend alias
            "availability_state": state,
            "reason_code": reason_code,
            "reason": unified.get("reason", ""),
            "checked_at": checked_at,
            "source_payload": unified,
        }
