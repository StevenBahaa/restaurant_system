import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class RestaurantKitchenTicket(models.Model):
    _inherit = 'restaurant.kitchen.ticket'

    cancelled_from_pos_order_id = fields.Many2one("pos.order", string="Cancelled From POS Refund Order", readonly=True, copy=False, index=True)
    cancellation_source = fields.Selection([("manual", "Manual"), ("pos_refund", "POS Refund")], string="Cancellation Source", readonly=True, copy=False)
    cancellation_reason = fields.Text(string="Cancellation Reason", readonly=True, copy=False)
    # cancelled_at already exists natively on restaurant.kitchen.ticket
    cancelled_by_id = fields.Many2one("res.users", string="Cancelled By", readonly=True, copy=False)
    recall_required = fields.Boolean(string="Recall Required", readonly=True, copy=False)
    recall_note = fields.Text(string="Recall Note", readonly=True, copy=False)
