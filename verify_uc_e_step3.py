import traceback

env = self.env
try:
    print("Test 1: Verify Menus")
    root_menu = env.ref('restaurant_base.restaurant_root_menu')
    kitchen_menu = env.ref('restaurant_kitchen.menu_restaurant_kitchen_root')
    order_menu = env.ref('restaurant_kitchen.menu_restaurant_kitchen_order')
    assert root_menu, "Root menu missing"
    assert kitchen_menu.parent_id == root_menu, "Kitchen menu parent is not root"
    assert order_menu.parent_id == kitchen_menu, "Order menu parent is not Kitchen"
    print("PASS: Menus exist and hierarchy is correct.")

    print("Test 2: Verify Action")
    action = env.ref('restaurant_kitchen.action_restaurant_kitchen_order')
    assert action.res_model == 'restaurant.kitchen.order', "Action res_model is wrong"
    print("PASS: Action exists.")

    print("Test 3: Verify Views")
    list_view = env.ref('restaurant_kitchen.view_restaurant_kitchen_order_list')
    form_view = env.ref('restaurant_kitchen.view_restaurant_kitchen_order_form')
    search_view = env.ref('restaurant_kitchen.view_restaurant_kitchen_order_search')
    assert list_view and form_view and search_view, "Views missing"
    print("PASS: Views exist.")

    print("Test 4: Verify Product Domain for Shared Products")
    # Using the domain from the XML
    company = env['res.company'].search([], limit=1)
    domain = [
        ('active', '=', True), 
        ('is_menu_item', '=', True), 
        ('restaurant_product_type', 'in', ['prepared_meal', 'beverage', 'ready_item']), 
        '|', ('company_id', '=', False), ('company_id', '=', company.id)
    ]
    products = env['product.template'].search(domain)
    # Check if there's any shared product
    shared_products = products.filtered(lambda p: not p.company_id)
    assert len(shared_products) > 0, "No shared products found using domain, domain might be broken"
    print("PASS: Product domain finds shared products.")

    print("ALL TESTS PASSED")

except Exception as e:
    print(f"EXCEPTION: {e}")
    traceback.print_exc()
