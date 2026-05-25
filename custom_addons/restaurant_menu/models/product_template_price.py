# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    branch_price_line_ids = fields.One2many(
        'restaurant.branch.price.line',
        'product_tmpl_id',
        string='Branch Pricing Rules'
    )
    branch_price_history_ids = fields.One2many(
        'restaurant.branch.price.history',
        'product_tmpl_id',
        string='Price History'
    )

    def write(self, vals):
        if 'branch_price_line_ids' in vals:
            if not self.env.su and not (
                self.env.user.has_group('restaurant_base.group_restaurant_operations_manager') or
                self.env.user.has_group('restaurant_menu.group_restaurant_pricing_manager')
            ):
                raise AccessError("You do not have permission to modify branch/channel pricing.")
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'branch_price_line_ids' in vals:
                if not self.env.su and not (
                    self.env.user.has_group('restaurant_base.group_restaurant_operations_manager') or
                    self.env.user.has_group('restaurant_menu.group_restaurant_pricing_manager')
                ):
                    raise AccessError("You do not have permission to modify branch/channel pricing.")
        return super().create(vals_list)
    branch_pricing_has_below_cost = fields.Boolean(
        string='Has Below-Cost Prices',
        compute='_compute_branch_pricing_below_cost',
        store=False,
    )
    branch_pricing_below_cost_count = fields.Integer(
        string='Below-Cost Price Count',
        compute='_compute_branch_pricing_below_cost',
        store=False,
    )
    branch_pricing_rule_count = fields.Integer(
        string='Active Branch Pricing Rules Count',
        compute='_compute_branch_pricing_summary',
        store=False,
    )
    branch_pricing_has_active_rules = fields.Boolean(
        string='Has Active Branch Pricing',
        compute='_compute_branch_pricing_summary',
        search='_search_branch_pricing_has_active_rules',
        store=False,
    )
    branch_pricing_has_future_rules = fields.Boolean(
        string='Has Scheduled Future Pricing',
        compute='_compute_branch_pricing_summary',
        search='_search_branch_pricing_has_future_rules',
        store=False,
    )
    branch_pricing_summary = fields.Char(
        string='Branch Pricing Summary',
        compute='_compute_branch_pricing_summary',
        store=False,
    )

    @api.depends('branch_price_line_ids.active', 'branch_price_line_ids.date_from', 'branch_pricing_has_below_cost', 'branch_pricing_below_cost_count')
    def _compute_branch_pricing_summary(self):
        today = fields.Date.context_today(self)
        for record in self:
            active_lines = record.branch_price_line_ids.filtered(lambda l: l.active)
            rule_count = len(active_lines)
            has_future = any(l.date_from and l.date_from > today for l in active_lines)
            
            record.branch_pricing_rule_count = rule_count
            record.branch_pricing_has_active_rules = rule_count > 0
            record.branch_pricing_has_future_rules = has_future

            if rule_count == 0:
                record.branch_pricing_summary = "No branch/channel pricing overrides"
            else:
                parts = [f"{rule_count} active pricing rule{'s' if rule_count != 1 else ''}"]
                if record.branch_pricing_below_cost_count > 0:
                    parts.append(f"{record.branch_pricing_below_cost_count} below-cost warning{'s' if record.branch_pricing_below_cost_count != 1 else ''}")
                if has_future:
                    parts.append("scheduled future price changes")
                record.branch_pricing_summary = ", ".join(parts)

    def _search_branch_pricing_has_active_rules(self, operator, value):
        if operator == '=' and value:
            return [('branch_price_line_ids', '!=', False)]
        elif operator == '=' and not value:
            return [('branch_price_line_ids', '=', False)]
        return []

    def _search_branch_pricing_has_future_rules(self, operator, value):
        today = fields.Date.context_today(self)
        if operator == '=' and value:
            return [('branch_price_line_ids.date_from', '>', today)]
        elif operator == '=' and not value:
            return ['|', ('branch_price_line_ids', '=', False), ('branch_price_line_ids.date_from', '<=', today)]
        return []

    @api.depends('branch_price_line_ids.is_below_cost', 'branch_price_line_ids.active')
    def _compute_branch_pricing_below_cost(self):
        for record in self:
            below_cost_lines = record.branch_price_line_ids.filtered(lambda l: l.active and l.is_below_cost)
            record.branch_pricing_below_cost_count = len(below_cost_lines)
            record.branch_pricing_has_below_cost = len(below_cost_lines) > 0

    def _get_matching_branch_price_rule(self, branch=None, channel=None, price_date=None):
        self.ensure_one()

        allow_branch_rules = False
        if branch and branch.active:
            allow_branch_rules = True
            branch_company = getattr(branch, 'company_id', False)
            if self.company_id and branch_company and self.company_id.id != branch_company.id:
                allow_branch_rules = False

        if not price_date:
            price_date = fields.Date.context_today(self)

        rules = self.branch_price_line_ids.filtered(lambda r: r.active)

        valid_rules = rules.filtered(
            lambda r: (not r.date_from or r.date_from <= price_date) and
                      (not r.date_until or r.date_until >= price_date)
        )

        if not valid_rules:
            return None, 'global'

        branch_channel_rules = valid_rules.filtered(lambda r: r.branch_id.id == branch.id and r.channel == channel) if allow_branch_rules and channel else self.env['restaurant.branch.price.line']
        channel_rules = valid_rules.filtered(lambda r: not r.branch_id and r.channel == channel) if channel else self.env['restaurant.branch.price.line']
        branch_rules = valid_rules.filtered(lambda r: r.branch_id.id == branch.id and not r.channel) if allow_branch_rules else self.env['restaurant.branch.price.line']

        def sort_key(rule):
            date_val = -rule.date_from.toordinal() if rule.date_from else 0
            rule_id = rule.id if isinstance(rule.id, int) else 0
            return (date_val, rule.sequence, -rule_id)

        if branch_channel_rules:
            return branch_channel_rules.sorted(key=sort_key)[0], 'branch_channel'

        if channel_rules:
            return channel_rules.sorted(key=sort_key)[0], 'channel'

        if branch_rules:
            return branch_rules.sorted(key=sort_key)[0], 'branch'

        return None, 'global'

    def _get_branch_price_payload(self, branch=None, channel=None, price_date=None):
        self.ensure_one()
        rule, source = self._get_matching_branch_price_rule(branch, channel, price_date)

        if rule:
            price = rule.price
            rule_id = rule.id
            currency_id = rule.currency_id.id
        else:
            price = self.list_price
            rule_id = False
            currency_id = self.currency_id.id or self.company_id.currency_id.id or self.env.company.currency_id.id

        return {
            "product_tmpl_id": self.id,
            "branch_id": branch.id if branch else False,
            "channel": channel or False,
            "price": price,
            "source": source,
            "rule_id": rule_id,
            "currency_id": currency_id
        }

    def _get_price_for_branch(self, branch=None, channel=None, price_date=None):
        self.ensure_one()
        payload = self._get_branch_price_payload(branch, channel, price_date)
        return payload.get('price', self.list_price)
