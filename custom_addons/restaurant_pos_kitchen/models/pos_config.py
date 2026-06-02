from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    restaurant_order_channel = fields.Selection(
        [
            ("dine_in", "Dine-in / Restaurant"),
            ("takeaway", "Takeaway"),
            ("delivery_app", "Delivery App"),
        ],
        string="Restaurant Order Channel",
        default="dine_in",
        required=True,
        help="Operational channel for this POS configuration. Used to determine when orders should be sent to the kitchen.",
    )

    kitchen_send_policy = fields.Selection(
        [
            ("manual", "Manual"),
            ("on_order_create", "On Order Creation / Sync"),
            ("on_payment_validation", "On Payment / Validation"),
        ],
        string="Kitchen Send Policy",
        default="on_payment_validation",
        required=True,
        help="Controls when this POS configuration should create kitchen preparation orders.",
    )

    kitchen_dispatch_policy = fields.Selection(
        [
            ("manual", "Manual Review"),
            ("auto_dispatch", "Auto Dispatch If Available"),
        ],
        string="Kitchen Dispatch Policy",
        default="manual",
        required=True,
        help="Controls whether POS-created Kitchen Orders remain for manual review or are automatically confirmed and dispatched when fully available and routable.",
    )

    @api.onchange("restaurant_order_channel")
    def _onchange_restaurant_order_channel(self):
        for config in self:
            if config.restaurant_order_channel == "delivery_app":
                config.kitchen_send_policy = "on_order_create"
            elif config.restaurant_order_channel in ("dine_in", "takeaway"):
                config.kitchen_send_policy = "on_payment_validation"

    def _get_kitchen_send_policy(self):
        self.ensure_one()
        return self.kitchen_send_policy

    def _get_kitchen_dispatch_policy(self):
        self.ensure_one()
        return self.kitchen_dispatch_policy

    def _should_auto_dispatch_kitchen_order(self):
        self.ensure_one()
        return self.kitchen_dispatch_policy == "auto_dispatch"

    def _should_create_kitchen_order_on_create(self):
        self.ensure_one()
        return self.kitchen_send_policy == "on_order_create"

    def _should_create_kitchen_order_on_payment(self):
        self.ensure_one()
        return self.kitchen_send_policy == "on_payment_validation"

    def _is_kitchen_auto_send_enabled(self):
        self.ensure_one()
        return self.kitchen_send_policy != "manual"
