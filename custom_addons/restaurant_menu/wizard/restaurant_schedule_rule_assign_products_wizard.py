from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RestaurantScheduleRuleAssignProductsWizard(models.TransientModel):
    _name = 'restaurant.schedule.rule.assign.products.wizard'
    _description = 'Assign Schedule Rule to Products Wizard'

    schedule_rule_id = fields.Many2one(
        'restaurant.schedule.rule',
        string='Schedule Rule',
        required=True,
        readonly=True,
    )
    apply_mode = fields.Selection(
        [
            ('add_missing', 'Add Missing (Append rule to products without duplicates)'),
            ('replace_existing_for_products', 'Replace Existing (Remove all other rules and set this one)'),
            ('remove_from_products', 'Remove Rule (Remove this rule from selected products)'),
        ],
        string='Apply Mode',
        default='add_missing',
        required=True,
    )
    product_tmpl_ids = fields.Many2many(
        'product.template',
        'restaurant_schedule_rule_assign_product_rel',
        'wizard_id',
        'product_tmpl_id',
        string='Products',
        required=True,
    )
    allowed_product_tmpl_ids = fields.Many2many(
        'product.template',
        compute='_compute_allowed_product_tmpl_ids',
        string='Allowed Products',
    )

    @api.depends('schedule_rule_id')
    def _compute_allowed_product_tmpl_ids(self):
        for record in self:
            domain = [('is_menu_item', '=', True), ('active', '=', True)]
            rule = record.schedule_rule_id
            if rule and rule.company_id:
                domain.append(('company_id', 'in', [False, rule.company_id.id]))
            else:
                domain.append(('company_id', 'in', [False] + self.env.user.company_ids.ids))
            record.allowed_product_tmpl_ids = self.env['product.template'].search(domain)

    def action_apply(self):
        self.ensure_one()
        rule = self.schedule_rule_id
        
        # Enforce that only Operations Managers can execute bulk operations
        if not (self.env.su or self.env.user.has_group('restaurant_base.group_restaurant_operations_manager')):
            raise ValidationError("Only Operations Managers can assign schedules to products.")

        if self.apply_mode == 'add_missing':
            for product in self.product_tmpl_ids:
                line_company = rule.company_id or product.company_id or self.env.company
                existing = self.env['restaurant.product.schedule.line'].search([
                    ('product_tmpl_id', '=', product.id),
                    ('schedule_rule_id', '=', rule.id),
                    ('company_id', '=', line_company.id),
                    ('branch_id', '=', False),
                ], limit=1)
                
                if not existing:
                    self.env['restaurant.product.schedule.line'].create({
                        'product_tmpl_id': product.id,
                        'schedule_rule_id': rule.id,
                        'company_id': line_company.id,
                        'branch_id': False,
                        'active': True,
                    })
                elif not existing.active:
                    existing.write({'active': True})

        elif self.apply_mode == 'replace_existing_for_products':
            for product in self.product_tmpl_ids:
                existing_lines = self.env['restaurant.product.schedule.line'].search([
                    ('product_tmpl_id', '=', product.id),
                ])
                existing_lines.unlink()
                
                line_company = rule.company_id or product.company_id or self.env.company
                self.env['restaurant.product.schedule.line'].create({
                    'product_tmpl_id': product.id,
                    'schedule_rule_id': rule.id,
                    'company_id': line_company.id,
                    'branch_id': False,
                    'active': True,
                })

        elif self.apply_mode == 'remove_from_products':
            for product in self.product_tmpl_ids:
                existing_lines = self.env['restaurant.product.schedule.line'].search([
                    ('product_tmpl_id', '=', product.id),
                    ('schedule_rule_id', '=', rule.id),
                ])
                existing_lines.unlink()

        return {'type': 'ir.actions.act_window_close'}
