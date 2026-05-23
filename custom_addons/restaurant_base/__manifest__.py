{
    "name": "Restaurant Base",
    "version": "18.0.1.0.0",
    "summary": "Core menus and shared foundations for Restaurant ERP",
    "category": "Restaurant",
    "author": "Steven Bahaa",
    "license": "LGPL-3",
    "depends": ["base", "product", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/restaurant_menus.xml",
        "views/restaurant_branch_views.xml",
    ],
    "installable": True,
    "application": True,
}