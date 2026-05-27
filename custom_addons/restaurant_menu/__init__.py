# pyrefly: ignore [missing-import]
from odoo import api, SUPERUSER_ID
from . import models

def post_init_hook(env):
    """
    Backfill timezone for any existing branches that have NULL tz
    """
    branches = env['restaurant.branch'].search([('tz', '=', False)])
    if branches:
        branches.write({'tz': 'Africa/Cairo'})
from . import wizard