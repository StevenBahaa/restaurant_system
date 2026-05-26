from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    kitchen_station_line_ids = fields.One2many(
        "restaurant.product.kitchen.station.line",
        "product_tmpl_id",
        string="Kitchen Station Assignments"
    )
