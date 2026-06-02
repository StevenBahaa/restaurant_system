import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class RestaurantKitchenOrder(models.Model):
    _inherit = 'restaurant.kitchen.order'

    source_type = fields.Selection(
        selection_add=[("pos_order", "POS Order")],
        ondelete={"pos_order": "set default"},
    )

    cancelled_from_pos_order_id = fields.Many2one("pos.order", string="Cancelled From POS Refund Order", readonly=True, copy=False, index=True)
    cancellation_source = fields.Selection([("manual", "Manual"), ("pos_refund", "POS Refund")], string="Cancellation Source", readonly=True, copy=False)
    cancellation_reason = fields.Text(string="Cancellation Reason", readonly=True, copy=False)
    cancelled_at = fields.Datetime(string="Cancelled At", readonly=True, copy=False)
    cancelled_by_id = fields.Many2one("res.users", string="Cancelled By", readonly=True, copy=False)
    recall_required = fields.Boolean(string="Recall Required", readonly=True, copy=False)
    recall_note = fields.Text(string="Recall Note", readonly=True, copy=False)

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

    def _safe_auto_dispatch_from_pos(self):
        results = []
        for order in self:
            result = {
                "kitchen_order_id": order.id,
                "dispatched": False,
                "reason_code": "unknown",
                "reason": "Unknown state",
            }
            try:
                eligibility = order._get_auto_dispatch_eligibility_payload()
                if not eligibility.get("eligible"):
                    _logger.info("Auto-dispatch skipped for Kitchen Order %s: %s - %s", order.id, eligibility.get("reason_code"), eligibility.get("reason"))
                    result.update({
                        "reason_code": eligibility.get("reason_code", "skipped"),
                        "reason": eligibility.get("reason", "Skipped by eligibility checks"),
                    })
                    results.append(result)
                    continue

                _logger.info("Auto-dispatch started for Kitchen Order %s", order.id)
                with self.env.cr.savepoint():
                    order.action_confirm()
                    order.action_generate_tickets()
                _logger.info("Auto-dispatch success for Kitchen Order %s", order.id)
                
                result.update({
                    "dispatched": True,
                    "reason_code": "dispatched",
                    "reason": "Kitchen order confirmed and tickets generated.",
                })
            except Exception as e:
                _logger.warning("Auto-dispatch failure with exception for Kitchen Order %s: %s", order.id, e, exc_info=True)
                result.update({
                    "reason_code": "dispatch_exception",
                    "reason": str(e),
                })
            results.append(result)
        return results

    def _build_recall_note(self, refund_pos_order, refund_lines=None):
        lines_text = []
        lines = refund_lines if refund_lines else refund_pos_order.lines
        for line in lines:
            lines_text.append(f"- {line.product_id.display_name}: {abs(line.qty)} refunded")
            
        pos_ref = refund_pos_order.pos_reference or refund_pos_order.name
        note = f"POS Refund Order: {pos_ref}\n"
        
        if "refunded_order_id" in refund_pos_order._fields and refund_pos_order.refunded_order_id:
            orig_ref = refund_pos_order.refunded_order_id.pos_reference or refund_pos_order.refunded_order_id.name
            note += f"Original Order: {orig_ref}\n"
            
        if lines_text:
            note += "Items affected:\n" + "\n".join(lines_text)
        return note

    def _apply_pos_refund_recall(self, refund_pos_order, refund_lines=None):
        results = []
        for order in self:
            result = {
                "kitchen_order_id": order.id,
                "processed": False,
                "reason_code": "unknown",
                "reason": "Unknown state",
                "tickets_updated": [],
            }

            pos_ref = refund_pos_order.pos_reference or refund_pos_order.name
            if order.cancelled_from_pos_order_id == refund_pos_order or (order.recall_note and pos_ref in order.recall_note):
                result.update({
                    "reason_code": "already_processed",
                    "reason": "Order already processed for this refund.",
                })
                results.append(result)
                continue

            if order.state == "cancelled":
                result.update({
                    "reason_code": "already_cancelled",
                    "reason": "Order is already cancelled.",
                })
                results.append(result)
                continue

            note = self._build_recall_note(refund_pos_order, refund_lines)
            metadata = {
                'cancelled_from_pos_order_id': refund_pos_order.id,
                'cancellation_source': 'pos_refund',
                'cancellation_reason': note,
                'cancelled_at': fields.Datetime.now(),
                'cancelled_by_id': self.env.user.id,
            }
            order_metadata = {k: v for k, v in metadata.items() if k in order._fields}

            if order.state == "draft":
                order.write(order_metadata)
                cancel_success = False
                if hasattr(order, 'action_cancel'):
                    try:
                        with self.env.cr.savepoint():
                            order.action_cancel()
                            cancel_success = True
                    except Exception as e:
                        _logger.warning("Order action_cancel rejected for order %s: %s", order.id, e, exc_info=True)
                        cancel_success = False
                        
                if cancel_success:
                    result.update({
                        "processed": True,
                        "reason_code": "cancelled_draft",
                        "reason": "Draft order cancelled.",
                    })
                else:
                    result.update({
                        "processed": True,
                        "reason_code": "metadata_only_cancel_not_supported",
                        "reason": "Draft order metadata written, but action_cancel not supported.",
                    })
                results.append(result)
                continue

            recall_metadata = metadata.copy()
            recall_metadata.update({
                'recall_required': True,
                'recall_note': f"Review Required: {note}" if order.state == "ready" else note,
            })
            order_recall_metadata = {k: v for k, v in recall_metadata.items() if k in order._fields}
            order.write(order_recall_metadata)

            tickets_updated = []
            for ticket in order.ticket_ids:
                if ticket.state == "cancelled":
                    continue
                
                ticket_metadata = {k: v for k, v in recall_metadata.items() if k in ticket._fields}
                
                if ticket.state == "waiting":
                    ticket.write(ticket_metadata)
                    if hasattr(ticket, 'action_cancel'):
                        try:
                            with self.env.cr.savepoint():
                                ticket.action_cancel()
                        except Exception as e:
                            _logger.warning("Ticket action_cancel rejected for ticket %s: %s", ticket.id, e, exc_info=True)
                            # Fallback to just metadata applied
                            pass
                    tickets_updated.append(ticket.id)
                elif ticket.state in ("in_progress", "ready"):
                    ticket.write(ticket_metadata)
                    tickets_updated.append(ticket.id)

            result.update({
                "processed": True,
                "reason_code": "recall_flagged",
                "reason": "Order flagged for recall.",
                "tickets_updated": tickets_updated,
            })
            results.append(result)

        return results

    def _safe_apply_pos_refund_recall(self, refund_pos_order, refund_lines=None, trigger=False):
        results = []
        for order in self:
            try:
                with self.env.cr.savepoint():
                    res = order._apply_pos_refund_recall(refund_pos_order, refund_lines)
                    results.extend(res)
            except Exception as e:
                _logger.error(
                    "Kitchen refund recall failed safely for POS Order %s (Kitchen Order ID: %s, Trigger: %s). Error: %s",
                    refund_pos_order.name,
                    order.id,
                    trigger,
                    e,
                    exc_info=True,
                )
                results.append({
                    "kitchen_order_id": order.id,
                    "processed": False,
                    "reason_code": "exception",
                    "reason": str(e),
                    "tickets_updated": [],
                })
        return results
