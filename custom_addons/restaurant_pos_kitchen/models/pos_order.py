import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    kitchen_dispatch_policy = fields.Selection(
        [
            ("manual", "Manual Review"),
            ("auto_dispatch", "Auto Dispatch If Available"),
        ],
        string="Kitchen Dispatch Policy",
        copy=False,
        help="Actual dispatch policy snapshot for this POS order. Defaults from POS configuration.",
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

    def _get_kitchen_dispatch_policy(self):
        self.ensure_one()
        return self.kitchen_dispatch_policy or self.config_id.kitchen_dispatch_policy

    def _should_auto_dispatch_kitchen_order(self):
        self.ensure_one()
        return self._get_kitchen_dispatch_policy() == "auto_dispatch"

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
                if not vals.get("kitchen_dispatch_policy") and config.kitchen_dispatch_policy:
                    vals["kitchen_dispatch_policy"] = config.kitchen_dispatch_policy
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
            if not order.kitchen_dispatch_policy:
                order.kitchen_dispatch_policy = config.kitchen_dispatch_policy
            if not order.restaurant_branch_id and config.branch_id:
                order.restaurant_branch_id = config.branch_id

    def _prepare_restaurant_kitchen_order_line_vals(self, pos_line):
        line_fields = self.env["restaurant.kitchen.order.line"]._fields
        if "product_tmpl_id" not in line_fields or "quantity" not in line_fields:
            _logger.warning("Missing mandatory target fields on restaurant.kitchen.order.line")
            return {}
            
        vals = {
            "product_tmpl_id": pos_line.product_id.product_tmpl_id.id,
            "quantity": pos_line.qty,
        }
        if "note" in line_fields:
            source_note = getattr(pos_line, "customer_note", False) or getattr(pos_line, "note", False)
            if source_note:
                vals["note"] = source_note
        return vals

    def _prepare_restaurant_kitchen_order_vals(self, branch, kitchen_lines_vals):
        order_fields = self.env["restaurant.kitchen.order"]._fields
        if "line_ids" not in order_fields:
            _logger.warning("Missing mandatory line_ids field on restaurant.kitchen.order")
            return {}
            
        company = self.company_id or branch.company_id
        
        vals = {
            "line_ids": [(0, 0, line_vals) for line_vals in kitchen_lines_vals]
        }
        if "source_type" in order_fields:
            vals["source_type"] = "pos_order"
        if "source_model" in order_fields:
            vals["source_model"] = "pos.order"
        if "source_res_id" in order_fields:
            vals["source_res_id"] = self.id
        if "source_reference" in order_fields:
            vals["source_reference"] = self.pos_reference or self.name
        if "branch_id" in order_fields:
            vals["branch_id"] = branch.id
        if "company_id" in order_fields:
            vals["company_id"] = company.id
        if "partner_id" in order_fields and self.partner_id:
            vals["partner_id"] = self.partner_id.id
        if "order_date" in order_fields:
            vals["order_date"] = self.date_order
        if "note" in order_fields:
            source_note = getattr(self, "note", False)
            if source_note:
                vals["note"] = source_note
            
        return vals

    def _create_restaurant_kitchen_order_from_pos(self):
        self.ensure_one()

        KitchenOrder = self.env["restaurant.kitchen.order"]

        # Duplicate prevention (sudo used to prevent false negatives if cashier lacks global read ACL)
        existing = KitchenOrder.sudo()._find_existing_source_order("pos_order", "pos.order", self.id)
        if existing:
            _logger.info("Kitchen order already exists for POS order %s (ID: %s).", self.name, existing.id)
            return existing

        # Policy check
        policy = self._get_kitchen_send_policy()
        if not policy or policy == "manual":
            _logger.info("Kitchen send policy is 'manual' (or unset) for POS order %s. Skipping creation.", self.name)
            return KitchenOrder.browse()

        # Branch resolution
        branch = self._get_restaurant_branch()
        if not branch:
            _logger.warning("No restaurant branch configured for POS order %s. Skipping kitchen order.", self.name)
            return KitchenOrder.browse()

        company = self.company_id or branch.company_id
        if branch.company_id and branch.company_id != company:
            _logger.warning("Branch company mismatch for POS order %s. Skipping kitchen order.", self.name)
            return KitchenOrder.browse()

        # Menu line filtering
        valid_lines = self.lines.filtered(
            lambda l: l.qty > 0 
            and l.product_id 
            and getattr(l.product_id.product_tmpl_id, "is_menu_item", False)
        )

        if not valid_lines:
            _logger.info("No valid menu lines found for POS order %s. Skipping kitchen order.", self.name)
            return KitchenOrder.browse()

        # Prepare values
        kitchen_lines_vals = [
            vals for vals in (self._prepare_restaurant_kitchen_order_line_vals(line) for line in valid_lines) 
            if vals
        ]
        
        if not kitchen_lines_vals:
            _logger.warning("No valid kitchen line values prepared for POS order %s. Skipping.", self.name)
            return KitchenOrder.browse()
            
        vals = self._prepare_restaurant_kitchen_order_vals(branch, kitchen_lines_vals)
        
        if not vals or "line_ids" not in vals:
            _logger.warning("Failed to prepare mandatory kitchen order values for POS order %s. Skipping.", self.name)
            return KitchenOrder.browse()

        # Isolated sudo create to allow cashiers to generate backend orders without full Kitchen App access
        new_order = KitchenOrder.sudo().create(vals)
        _logger.info("Successfully created kitchen order %s for POS order %s.", new_order.name, self.name)

        # Availability check wrapper
        availability_method = getattr(new_order, "action_check_availability", None)
        if callable(availability_method):
            try:
                availability_method()
            except Exception as e:
                _logger.warning("Availability check failed for kitchen order %s: %s", new_order.name, e)

        if self._should_auto_dispatch_kitchen_order():
            # Automated POS-to-kitchen dispatch may run under cashier users.
            # sudo is limited to Kitchen Order workflow execution while preserving business validations.
            new_order.sudo()._safe_auto_dispatch_from_pos()

        return new_order

    def _safe_create_restaurant_kitchen_order_from_pos(self, trigger=False):
        for order in self:
            try:
                order._create_restaurant_kitchen_order_from_pos()
            except Exception as e:
                _logger.error(
                    "Kitchen integration failed safely for POS Order %s (ID: %s, Trigger: %s). Error: %s",
                    order.name,
                    order.id,
                    trigger,
                    e,
                    exc_info=True,
                )

    @api.model
    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        if order_id:
            pos_order = self.browse(order_id)
            if pos_order.exists() and pos_order._get_kitchen_send_policy() == "on_order_create":
                pos_order._safe_create_restaurant_kitchen_order_from_pos(trigger="_process_order")
        return order_id

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        for order in self:
            if order._get_kitchen_send_policy() == "on_payment_validation":
                order._safe_create_restaurant_kitchen_order_from_pos(trigger="action_pos_order_paid")
        return res