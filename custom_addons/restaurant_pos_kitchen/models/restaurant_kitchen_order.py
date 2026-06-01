from odoo import api, fields, models

class RestaurantKitchenOrder(models.Model):
    _inherit = 'restaurant.kitchen.order'

    source_type = fields.Selection(
        selection_add=[("pos_order", "POS Order")],
        ondelete={"pos_order": "set default"},
    )

    @api.model
    def _find_existing_source_order(self, source_type, source_model, source_res_id):
        if not source_res_id:
            return self.env['restaurant.kitchen.order']
        return self.search([
            ('source_type', '=', source_type),
            ('source_model', '=', source_model),
            ('source_res_id', '=', source_res_id),
        ], limit=1)
