{
    "name": "Restaurant Kitchen",
    "version": "18.0.1.0.0",
    "summary": "Kitchen station and routing foundation",
    "description": "Foundation module for kitchen stations and routing.",
    "category": "Restaurant",
    "author": "Steven Bahaa",
    "license": "LGPL-3",
    "depends": [
        "restaurant_base",
        "restaurant_menu",
        "restaurant_inventory",
        "mail"
    ],
    "data": [
        "data/restaurant_kitchen_sequences.xml",
        "security/restaurant_kitchen_security.xml",
        "security/ir.model.access.csv",
        "views/restaurant_kitchen_order_views.xml",
        "views/restaurant_kitchen_station_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
