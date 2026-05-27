{
    "name": "Restaurant Menu Management",
    "version": "18.0.1.0.0",
    "summary": "Restaurant menu item identity management",
    "description": """
Restaurant & Cloud Kitchen ERP - Menu Management

Phase 1 - UC-01:
- Mark products as restaurant menu items
- Add Arabic product name

Phase 1 - UC-08 to UC-12:
- Branch Availability
- Branch-Specific Pricing
- Kitchen Station & Preparation Time
- Stock-Linked Availability
- Menu Scheduling Rules
    """,
    "category": "Restaurant",
    "author": "Steven Bahaa",
    "license": "LGPL-3",
    "depends": [
        "restaurant_base",
        "stock",
        "point_of_sale"
    ],
    "data": [
        "security/restaurant_menu_security.xml",
        "security/ir.model.access.csv",
        "data/restaurant_schedule_day_data.xml",
        "views/restaurant_schedule_rule_views.xml",
        "views/restaurant_schedule_override_views.xml",
        "views/restaurant_branch_views.xml",
        "views/product_template_views.xml",
        "views/pos_category_views.xml",
        "views/restaurant_addon_views.xml",
        "wizard/restaurant_branch_availability_bulk_wizard_views.xml",
        "wizard/restaurant_branch_price_bulk_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}