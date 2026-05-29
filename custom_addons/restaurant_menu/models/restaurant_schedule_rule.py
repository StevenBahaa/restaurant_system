from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantScheduleRule(models.Model):
    _name = "restaurant.schedule.rule"
    _description = "Restaurant Menu Schedule Rule"
    _order = "name, id"

    name = fields.Char(string="Schedule Name", required=True)
    day_ids = fields.Many2many(
        "restaurant.schedule.day",
        string="Days of Week",
        help="Select days of the week when this rule applies. If left empty, it applies to all days.",
    )
    start_time = fields.Float(
        string="Start Time",
        help="Start time in 24h format (e.g. 13:30 is 13.5).",
    )
    end_time = fields.Float(
        string="End Time",
        help="End time in 24h format (e.g. 15:00 is 15.0).",
    )
    date_from = fields.Date(
        string="Start Date",
        help="Optional start date for seasonal schedules (inclusive).",
    )
    date_to = fields.Date(
        string="End Date",
        help="Optional end date for seasonal schedules (inclusive).",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    note = fields.Text(
        string="Notes",
    )
    product_count = fields.Integer(
        string='Products Count',
        compute='_compute_product_count',
    )

    def _compute_product_count(self):
        for record in self:
            count = self.env['restaurant.product.schedule.line'].search_count([
                ('schedule_rule_id', '=', record.id),
                ('active', '=', True),
            ])
            record.product_count = count

    def action_open_assign_wizard(self):
        self.ensure_one()
        return {
            'name': 'Assign to Products',
            'type': 'ir.actions.act_window',
            'res_model': 'restaurant.schedule.rule.assign.products.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_schedule_rule_id': self.id,
            }
        }

    def action_view_assigned_products(self):
        self.ensure_one()
        lines = self.env['restaurant.product.schedule.line'].search([
            ('schedule_rule_id', '=', self.id),
            ('active', '=', True),
        ])
        product_tmpl_ids = lines.mapped('product_tmpl_id').ids
        return {
            'name': 'Assigned Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', product_tmpl_ids)],
            'target': 'current',
        }


    @api.constrains('name', 'start_time', 'end_time', 'date_from', 'date_to', 'day_ids')
    def _check_schedule_rules(self):
        for record in self:
            # Treat both being 0.0 as "no time restriction"
            has_time = (record.start_time != 0.0 or record.end_time != 0.0)

            if has_time:
                # Check ranges: 0.0 <= time < 24.0
                if not (0.0 <= record.start_time < 24.0):
                    raise ValidationError("Start time must be between 0.0 and 24.0 (exclusive).")
                if not (0.0 <= record.end_time < 24.0):
                    raise ValidationError("End time must be between 0.0 and 24.0 (exclusive).")

                # Equal check: reject if equal
                if record.start_time == record.end_time:
                    raise ValidationError("Start time and end time cannot be equal.")

            # Date range validation
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError("Start date cannot be after end date.")

            # Rule completeness check
            has_days = bool(record.day_ids)
            has_date = bool(record.date_from or record.date_to)

            # A rule with only day_ids and no time/date restriction is valid:
            # it means "these items are available all day on selected days"
            if not (has_days or has_time or has_date):
                raise ValidationError(
                    "The schedule rule must have at least one restriction (days of week, time window, or date range)."
                )
