from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_pos_availability_payload_bulk(self, branch=None, quantity=1, at_datetime=None):
        """
        Evaluate availability for a recordset of product.product for POS frontend mapping.
        Returns a dictionary keyed by product ID (string) with the availability state.
        """
        at_datetime = at_datetime or fields.Datetime.now()
        checked_at_str = fields.Datetime.to_string(at_datetime)
        payload_map = {}

        if not branch:
            # Fast path: No branch configured on POS config
            for product in self:
                payload_map[str(product.id)] = {
                    "product_id": product.id,
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "branch_id": False,
                    "is_available": False,
                    "availability_state": "unknown",
                    "reason_code": "branch_not_configured",
                    "reason": "No restaurant branch configured for this POS session.",
                    "checked_at": checked_at_str,
                }
            return payload_map

        for product in self:
            try:
                product_tmpl = product.product_tmpl_id
                
                # Call existing template helper
                source_payload = product_tmpl._get_pos_availability_payload(
                    branch=branch,
                    quantity=quantity,
                    at_datetime=at_datetime,
                )

                # Normalize payload
                availability_state = source_payload.get("availability_state") or source_payload.get("state") or "unknown"
                reason_code = source_payload.get("reason_code") or "unknown"
                reason = source_payload.get("reason") or "Unknown evaluation."

                payload_map[str(product.id)] = {
                    "product_id": product.id,
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "branch_id": branch.id,
                    "is_available": bool(source_payload.get("is_available")),
                    "availability_state": availability_state,
                    "reason_code": reason_code,
                    "reason": reason,
                    "checked_at": checked_at_str,
                }
            except Exception as e:
                _logger.error(
                    "POS Availability Bulk Resolver crashed for Product %s (Template %s) on Branch %s",
                    product.id,
                    product.product_tmpl_id.id,
                    branch.id,
                    exc_info=True
                )
                payload_map[str(product.id)] = {
                    "product_id": product.id,
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "branch_id": branch.id,
                    "is_available": False,
                    "availability_state": "unknown",
                    "reason_code": "evaluation_error",
                    "reason": "Availability evaluation failed for this product.",
                    "checked_at": checked_at_str,
                }

        return payload_map
