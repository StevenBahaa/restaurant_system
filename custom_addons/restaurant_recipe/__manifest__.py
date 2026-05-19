{
    "name": "Restaurant Recipe Engine",
    "version": "18.0.1.0.0",
    "summary": "Recipe and ingredient costing engine for restaurant products",
    "category": "Restaurant",
    "author": "Steven Bahaa",
    "license": "LGPL-3",
    "depends": [
        "restaurant_base",
        "restaurant_menu",
        "uom",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/restaurant_recipe_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}