
import json
from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError

class RestaurantMenuStatusWizard(models.TransientModel):
    _name = "restaurant.menu.status.wizard"
    _description = "Branch Menu Status Wizard"

    branch_id = fields.Many2one("restaurant.branch", string="Branch", required=True)
    allowed_branch_ids = fields.Many2many(
        "restaurant.branch",
        string="Allowed Branches",
        compute="_compute_allowed_branch_ids",
    )
    at_datetime = fields.Datetime(
        string="Evaluation Datetime",
        default=fields.Datetime.now,
        required=True,
    )
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
    )
    evaluate_all = fields.Boolean(
        string="Evaluate All Layers",
        default=True,
    )
    line_ids = fields.One2many(
        "restaurant.menu.status.wizard.line",
        "wizard_id",
        string="Status Lines",
    )

    total_count = fields.Integer(string="Total Products", readonly=True)
    available_count = fields.Integer(string="Available Products", readonly=True)
    unavailable_count = fields.Integer(string="Unavailable Products", readonly=True)
    blocked_by_branch_count = fields.Integer(string="Blocked by Branch", readonly=True)
    blocked_by_schedule_count = fields.Integer(string="Blocked by Schedule", readonly=True)
    blocked_by_stock_count = fields.Integer(string="Blocked by Stock", readonly=True)
    schedule_manual_override_count = fields.Integer(
        string="Schedule Overrides",
        readonly=True,
    )
    stock_manual_override_count = fields.Integer(
        string="Stock Overrides",
        readonly=True,
    )

    @api.depends("branch_id")
    @api.depends_context("uid")
    def _compute_allowed_branch_ids(self):
        is_ops_manager = self.env.user.has_group(
            "restaurant_base.group_restaurant_operations_manager"
        )
        is_branch_manager = self.env.user.has_group(
            "restaurant_base.group_restaurant_branch_manager"
        )

        if is_ops_manager:
            allowed_branches = self.env["restaurant.branch"].search([
                ("company_id", "in", self.env.user.company_ids.ids)
            ])
        elif is_branch_manager:
            allowed_branches = self.env["restaurant.branch"].search([
                ("manager_user_ids", "in", self.env.user.id)
            ])
        else:
            allowed_branches = self.env["restaurant.branch"].browse()

        for wizard in self:
            wizard.allowed_branch_ids = allowed_branches


    def _check_branch_access(self):
        self.ensure_one()
        if not self.branch_id:
            raise ValidationError("A branch must be selected.")
        if self.branch_id not in self.allowed_branch_ids:
            raise AccessError("You are not allowed to evaluate this branch.")

    def _get_menu_product_domain(self):
        self.ensure_one()
        return [
            ("is_menu_item", "=", True),
            ("active", "=", True),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.branch_id.company_id.id),
            "|",
            ("sale_ok", "=", True),
            ("available_in_pos", "=", True),
        ]

    def action_evaluate(self):
        self.ensure_one()
        self._check_branch_access()

        # Remove existing lines
        self.line_ids.unlink()

        domain = self._get_menu_product_domain()
        products = self.env["product.template"].search(domain)

        lines_vals = []
        total_count = len(products)
        available_count = 0
        blocked_by_branch_count = 0
        blocked_by_schedule_count = 0
        blocked_by_stock_count = 0
        schedule_manual_override_count = 0
        stock_manual_override_count = 0

        for product in products:
            # Using sudo() because evaluating unified availability requires read-access
            # to internal/restricted models like pos.category and stock.location.
            # Security is enforced at the wizard level via _check_branch_access().
            payload = product.sudo()._get_unified_availability_payload(
                branch=self.branch_id,
                at_datetime=self.at_datetime,
                quantity=self.quantity,
                evaluate_all=self.evaluate_all,
            )

            is_available = payload.get("is_available", False)
            reason = payload.get("reason", "")
            reason_code = payload.get("reason_code", "")

            layers = payload.get("layers", {})
            branch_layer = layers.get("branch", {})
            schedule_layer = layers.get("schedule", {})
            stock_layer = layers.get("stock", {})

            branch_ok = branch_layer.get("is_available", False)
            schedule_ok = schedule_layer.get("is_available", False)
            stock_ok = stock_layer.get("is_available", False)

            schedule_manual_override = schedule_layer.get("manual_override", False)
            stock_manual_override = stock_layer.get("manual_override", False)

            blocking_reasons = payload.get("blocking_reasons", [])
            blocking_reasons_text = "\n".join(blocking_reasons) if blocking_reasons else ""

            # Safe serialization using dumps with custom defaults
            payload_json_str = json.dumps(
                payload,
                default=str,
                ensure_ascii=False,
                indent=2,
            )

            # Update counters
            if is_available:
                available_count += 1
            if not branch_ok:
                blocked_by_branch_count += 1
            if not schedule_ok:
                blocked_by_schedule_count += 1
            if not stock_ok:
                blocked_by_stock_count += 1
            if schedule_manual_override:
                schedule_manual_override_count += 1
            if stock_manual_override:
                stock_manual_override_count += 1

            lines_vals.append((0, 0, {
                "product_tmpl_id": product.id,
                "product_name": product.display_name,
                "is_available": is_available,
                "reason": reason,
                "reason_code": reason_code,
                "branch_available": branch_ok,
                "schedule_available": schedule_ok,
                "stock_available": stock_ok,
                "schedule_manual_override": schedule_manual_override,
                "stock_manual_override": stock_manual_override,
                "blocking_reasons_text": blocking_reasons_text,
                "payload_json": payload_json_str,
            }))

        self.write({
            "line_ids": lines_vals,
            "total_count": total_count,
            "available_count": available_count,
            "unavailable_count": total_count - available_count,
            "blocked_by_branch_count": blocked_by_branch_count,
            "blocked_by_schedule_count": blocked_by_schedule_count,
            "blocked_by_stock_count": blocked_by_stock_count,
            "schedule_manual_override_count": schedule_manual_override_count,
            "stock_manual_override_count": stock_manual_override_count,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "restaurant.menu.status.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


class RestaurantMenuStatusWizardLine(models.TransientModel):
    _name = "restaurant.menu.status.wizard.line"
    _description = "Branch Menu Status Wizard Line"

    wizard_id = fields.Many2one(
        "restaurant.menu.status.wizard",
        required=True,
        ondelete="cascade",
        string="Wizard",
    )
    product_tmpl_id = fields.Many2one("product.template", string="Product Template", readonly=True)
    product_name = fields.Char(string="Product Name", readonly=True)
    is_available = fields.Boolean(string="Available", readonly=True)
    reason = fields.Char(string="Reason", readonly=True)
    reason_code = fields.Char(string="Reason Code", readonly=True)
    branch_available = fields.Boolean(string="Branch Available", readonly=True)
    schedule_available = fields.Boolean(string="Schedule Available", readonly=True)
    stock_available = fields.Boolean(string="Stock Available", readonly=True)
    schedule_manual_override = fields.Boolean(string="Schedule Manual Override", readonly=True)
    stock_manual_override = fields.Boolean(string="Stock Manual Override", readonly=True)
    blocking_reasons_text = fields.Text(string="Blocking Reasons Text", readonly=True)
    payload_json = fields.Text(string="Payload JSON", readonly=True)
