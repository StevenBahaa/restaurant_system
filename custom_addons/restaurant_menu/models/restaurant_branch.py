import pytz
from odoo import models, fields, api

class RestaurantBranch(models.Model):
    _inherit = "restaurant.branch"

    tz = fields.Selection(
        selection="_tz_get",
        string="Timezone",
        required=True,
        default="Africa/Cairo",
        help="Timezone for the branch operations and scheduling.",
    )

    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in pytz.all_timezones]
