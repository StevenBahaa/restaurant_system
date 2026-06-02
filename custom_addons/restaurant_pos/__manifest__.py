{
    "name": "Restaurant POS Integration",
    "version": "18.0.1.0.0",
    "summary": "POS branch binding and availability foundation for Restaurant ERP",
    "description": """
        Optional integration module that connects Odoo POS (Point of Sale) with the
        Restaurant ERP branch and availability system.

        Features (planned across UC-F and later UCs):
        - Bind each pos.config to a restaurant.branch
        - Evaluate branch-aware menu availability in POS context
        - Auto-generate Kitchen Preparation Orders from POS orders (future UC)
        - Branch-aware pricing in POS (future UC)
        - POS Kitchen Display Screen (future UC)

        Core restaurant modules (restaurant_base, restaurant_menu, restaurant_inventory,
        restaurant_kitchen) remain installable and usable WITHOUT this module.
    """,
    "category": "Restaurant",
    "author": "Steven Bahaa",
    "website": "https://github.com/StevenBahaa/restaurant_system",
    "license": "LGPL-3",
    "depends": [
        "restaurant_base",       # restaurant.branch, security groups
        "restaurant_menu",       # product.template extensions, branch availability layers
        "restaurant_inventory",  # _get_unified_availability_payload resolver (confirmed in restaurant_inventory/models/product_template.py)
        "point_of_sale",         # pos.config, pos.session, pos.order, pos.order.line
        # NOTE: restaurant_kitchen is intentionally excluded.
        # Kitchen integration will be handled in a later UC via a bridge module or extension.
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "restaurant_pos/static/src/js/product_card.js",
            "restaurant_pos/static/src/xml/product_card.xml",
            "restaurant_pos/static/src/scss/product_card.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
