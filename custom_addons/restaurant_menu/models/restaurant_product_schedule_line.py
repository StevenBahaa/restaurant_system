from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantProductScheduleLine(models.Model):
    _name = "restaurant.product.schedule.line"
    _description = "Restaurant Product Schedule Line"
    _order = "sequence, id"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product Template",
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
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    @api.constrains('product_tmpl_id', 'schedule_rule_id', 'company_id', 'branch_id')
    def _check_company_consistency(self):
        for record in self:
            if record.schedule_rule_id.company_id:
                if record.company_id != record.schedule_rule_id.company_id:
                    raise ValidationError(
                        f"The schedule rule company ({record.schedule_rule_id.company_id.name}) "
                        f"must match the line company ({record.company_id.name})."
                    )
            
            if record.product_tmpl_id.company_id:
                if record.company_id != record.product_tmpl_id.company_id:
                    raise ValidationError(
                        f"The product company ({record.product_tmpl_id.company_id.name}) "
                        f"must match the line company ({record.company_id.name})."
                    )

            if record.branch_id and record.branch_id.company_id:
                if record.company_id != record.branch_id.company_id:
                    raise ValidationError(
                        f"The branch company ({record.branch_id.company_id.name}) "
                        f"must match the line company ({record.company_id.name})."
                    )

    @api.constrains('product_tmpl_id', 'schedule_rule_id', 'company_id', 'branch_id', 'active')
    def _check_unique_assignment(self):
        for record in self:
            if not record.active:
                continue
            
            domain = [
                ('id', '!=', record.id),
                ('product_tmpl_id', '=', record.product_tmpl_id.id),
                ('schedule_rule_id', '=', record.schedule_rule_id.id),
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id if record.branch_id else False),
                ('active', '=', True),
            ]
            if self.search_count(domain):
                raise ValidationError("A schedule line for this product, rule, company, and branch already exists.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_tmpl_id'):
                product = self.env['product.template'].browse(vals['product_tmpl_id'])
                if product.company_id:
                    vals['company_id'] = product.company_id.id
        return super().create(vals_list)

    def write(self, vals):
        if 'product_tmpl_id' in vals and vals.get('product_tmpl_id'):
            product = self.env['product.template'].browse(vals['product_tmpl_id'])
            if product.company_id:
                vals['company_id'] = product.company_id.id
        return super().write(vals)
