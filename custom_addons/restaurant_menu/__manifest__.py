{
    "name": "Restaurant Menu Management",
    "version": "18.0.1.0.0",
    "summary": "Restaurant menu item identity management",
    "description": """
Restaurant & Cloud Kitchen ERP - Menu Management

Phase 1 - UC-01:
- Mark products as restaurant menu items
- Add Arabic product name
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
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/pos_category_views.xml",
        "views/restaurant_addon_views.xml",
        "wizard/restaurant_branch_availability_bulk_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}