from odoo import api, fields, models

class RestaurantKitchenOrder(models.Model):
    _inherit = 'restaurant.kitchen.order'

    source_type = fields.Selection(
        selection_add=[("pos_order", "POS Order")],
        ondelete={"pos_order": "set default"},
    )

    @api.model
    def _find_existing_source_order(self, source_type, source_model, source_res_id):
        if not source_res_id:
            return self.env['restaurant.kitchen.order']
        return self.search([
            ('source_type', '=', source_type),
            ('source_model', '=', source_model),
            ('source_res_id', '=', source_res_id),
        ], limit=1)

    def _get_auto_dispatch_eligibility_payload(self):
        self.ensure_one()
        payload = {
            "kitchen_order_id": self.id,
            "eligible": True,
            "reason_code": "eligible",
            "reason": "Order is eligible for auto-dispatch.",
            "blocking_reasons": [],
            "warnings": [],
        }

        if self.state != "draft":
            payload.update({"eligible": False, "reason_code": "not_draft", "reason": "Order must be in draft state."})
            return payload

        if self.source_type != "pos_order":
            payload.update({"eligible": False, "reason_code": "not_pos_order", "reason": "Only POS orders can be auto-dispatched."})
            return payload

        if self.ticket_ids or self.tickets_generated:
            payload.update({"eligible": False, "reason_code": "already_has_tickets", "reason": "Order already has tickets."})
            return payload

        if not self.line_ids:
            payload.update({"eligible": False, "reason_code": "missing_lines", "reason": "Order has no lines."})
            return payload

        if not self.availability_checked:
            payload.update({"eligible": False, "reason_code": "availability_not_checked", "reason": "Availability must be checked before dispatch."})
            return payload

        if any(line.availability_status != "available" for line in self.line_ids):
            payload.update({"eligible": False, "reason_code": "unavailable_lines", "reason": "One or more lines are unavailable."})
            for line in self.line_ids.filtered(lambda l: l.availability_status != "available"):
                reason = line.reason or "No reason provided"
                code = line.reason_code or "unknown"
                payload["blocking_reasons"].append(f"{line.product_tmpl_id.display_name}: {code} - {reason}")
            return payload

        routing_required_types = {"prepared_meal", "beverage"}

        for line in self.line_ids:
            product = line.product_tmpl_id
            if product.restaurant_product_type == "combo":
                payload.update({"eligible": False, "reason_code": "combo_routing_deferred", "reason": "Combo component routing is deferred."})
                payload["blocking_reasons"].append(f"{product.display_name}: Combo routing is not supported yet.")
                return payload

            if product.restaurant_product_type in routing_required_types:
                station_lines = []
                if hasattr(product, "_get_active_kitchen_station_lines"):
                    station_lines = product._get_active_kitchen_station_lines(company=self.company_id, branch=self.branch_id)
                
                if not station_lines:
                    payload.update({"eligible": False, "reason_code": "missing_routing", "reason": "One or more items are missing required kitchen routing."})
                    payload["blocking_reasons"].append(f"{product.display_name}: No active kitchen station assigned.")
                    return payload
            else:
                payload["warnings"].append(f"{product.display_name}: No kitchen station required for product type {product.restaurant_product_type}.")

        return payload

    def _can_auto_dispatch(self):
        self.ensure_one()
        return self._get_auto_dispatch_eligibility_payload().get("eligible", False)
