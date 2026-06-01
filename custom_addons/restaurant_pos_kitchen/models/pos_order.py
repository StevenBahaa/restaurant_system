from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    restaurant_order_channel = fields.Selection(
        [
            ("dine_in", "Dine-in / Restaurant"),
            ("takeaway", "Takeaway"),
            ("delivery_app", "Delivery App"),
        ],
        string="Restaurant Order Channel",
        copy=False,
        help="Actual operational channel for this POS order. Defaults from POS configuration.",
    )

    kitchen_send_policy = fields.Selection(
        [
            ("manual", "Manual"),
            ("on_order_create", "On Order Creation / Sync"),
            ("on_payment_validation", "On Payment / Validation"),
        ],
        string="Kitchen Send Policy",
        copy=False,
        help="Actual kitchen send policy for this POS order. Defaults from POS configuration.",
    )

    restaurant_branch_id = fields.Many2one(
        "restaurant.branch",
        string="Restaurant Branch",
        copy=False,
        readonly=True,
        index=True,
        help="Restaurant branch resolved from the POS configuration at order level.",
    )

    def _get_restaurant_order_channel(self):
        self.ensure_one()
        return self.restaurant_order_channel or self.config_id.restaurant_order_channel

    def _get_kitchen_send_policy(self):
        self.ensure_one()
        return self.kitchen_send_policy or self.config_id.kitchen_send_policy

    def _get_restaurant_branch(self):
        self.ensure_one()
        return self.restaurant_branch_id or self.config_id.branch_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env["pos.config"]

            if vals.get("config_id"):
                config = self.env["pos.config"].browse(vals["config_id"])
            elif vals.get("session_id"):
                session = self.env["pos.session"].browse(vals["session_id"])
                config = session.config_id

            if config:
                if not vals.get("restaurant_order_channel") and config.restaurant_order_channel:
                    vals["restaurant_order_channel"] = config.restaurant_order_channel
                if not vals.get("kitchen_send_policy") and config.kitchen_send_policy:
                    vals["kitchen_send_policy"] = config.kitchen_send_policy
                if not vals.get("restaurant_branch_id") and config.branch_id:
                    vals["restaurant_branch_id"] = config.branch_id.id

        return super().create(vals_list)

    @api.onchange("session_id", "config_id")
    def _onchange_config_id_restaurant_defaults(self):
        for order in self:
            config = order.config_id or order.session_id.config_id
            if not config:
                continue

            if not order.restaurant_order_channel:
                order.restaurant_order_channel = config.restaurant_order_channel
            if not order.kitchen_send_policy:
                order.kitchen_send_policy = config.kitchen_send_policy
            if not order.restaurant_branch_id and config.branch_id:
                order.restaurant_branch_id = config.branch_id