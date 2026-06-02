{
    'name': 'Restaurant POS Kitchen Integration',
    'version': '18.0.1.0.0',
    'category': 'Restaurant ERP',
    'summary': 'Integration bridge between POS Orders and Kitchen Preparation Orders',
    'author': 'Antigravity',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'restaurant_pos',
        'restaurant_kitchen',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
        'views/restaurant_kitchen_order_views.xml',
        'views/restaurant_kitchen_ticket_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
