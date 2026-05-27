from odoo import models, fields

class RestaurantScheduleDay(models.Model):
    _name = "restaurant.schedule.day"
    _description = "Restaurant Schedule Day"
    _order = "code"

    code = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string="Day Code", required=True)
    name = fields.Char(string="Day Name", required=True, translate=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Day code must be unique!'),
    ]
