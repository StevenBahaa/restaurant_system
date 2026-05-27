from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantCategoryScheduleLine(models.Model):
    _name = "restaurant.category.schedule.line"
    _description = "Restaurant Category Schedule Line"
    _order = "sequence, id"

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    category_id = fields.Many2one(
        "pos.category",
        string="Category",
        required=True,
        ondelete="cascade",
        index=True,
    )
    schedule_rule_id = fields.Many2one(
        "restaurant.schedule.rule",
        string="Schedule Rule",
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    branch_id = fields.Many2one(
        "restaurant.branch",
        string="Branch",
        help="Leave empty to apply this schedule to all branches of the company.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )

    # Note: No create/write overrides for company_id synchronization exist here because 
    # pos.category is not company-scoped. Lines derive company_id from context or defaults.

    @api.constrains('category_id', 'schedule_rule_id', 'company_id', 'branch_id')
    def _check_company_consistency(self):
        for record in self:
            if record.schedule_rule_id.company_id and record.company_id != record.schedule_rule_id.company_id:
                raise ValidationError(
                    f"The schedule rule company ({record.schedule_rule_id.company_id.name}) "
                    f"must match the schedule line company ({record.company_id.name})."
                )

            if record.branch_id and record.branch_id.company_id:
                if record.company_id != record.branch_id.company_id:
                    raise ValidationError(
                        f"The branch company ({record.branch_id.company_id.name}) "
                        f"must match the line company ({record.company_id.name})."
                    )

    @api.constrains('category_id', 'schedule_rule_id', 'company_id', 'branch_id', 'active')
    def _check_unique_assignment(self):
        for record in self:
            if not record.active:
                continue
            
            domain = [
                ('id', '!=', record.id),
                ('category_id', '=', record.category_id.id),
                ('schedule_rule_id', '=', record.schedule_rule_id.id),
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id if record.branch_id else False),
                ('active', '=', True),
            ]
            if self.search_count(domain):
                raise ValidationError("A schedule line for this category, rule, company, and branch already exists.")
