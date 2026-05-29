import sys
import datetime
import traceback

def run_tests(env):
    results = []
    failed_records = []
    
    def log_pass(test_name):
        results.append(f"[PASS] {test_name}")
        
    def log_fail(test_name, details, record=None):
        results.append(f"[FAIL] {test_name}: {details}")
        if record:
            failed_records.append(record)

    def log_warn(test_name, details, record=None):
        results.append(f"[WARN] {test_name}: {details}")
        if record:
            failed_records.append(record)
        
    def check(condition, test_name, fail_msg, record=None):
        if condition:
            log_pass(test_name)
        else:
            log_fail(test_name, fail_msg, record)
            
    print("Starting Deep Verification...")

    # A. Company / Branch / Warehouse Integrity
    company = env['res.company'].search([('name', '=', 'DEMO - Salsa Restaurant Group')], limit=1)
    check(bool(company), "A: Company Exists", "DEMO - Salsa Restaurant Group not found")
    
    branches = env['restaurant.branch'].search([('company_id', '=', company.id)])
    branch_names = branches.mapped('name')
    check("DEMO - Nasr City Branch" in branch_names, "A: Nasr City Branch Exists", "Not found")
    check("DEMO - Maadi Cloud Kitchen" in branch_names, "A: Maadi Branch Exists", "Not found")
    check("DEMO - Asyut Branch" in branch_names, "A: Asyut Branch Exists", "Not found")
    
    for b in branches:
        check(b.active, f"A: Branch {b.name} active", "Inactive", b.name)
        check(b.company_id.id == company.id, f"A: Branch {b.name} company", "Mismatch", b.name)
        check(bool(b.warehouse_id), f"A: Branch {b.name} warehouse set", "Missing WH", b.name)
        if b.warehouse_id:
            check(b.warehouse_id.company_id.id == company.id, f"A: WH {b.warehouse_id.name} company", "Mismatch", b.warehouse_id.name)
            check(bool(b.warehouse_id.lot_stock_id), f"A: WH {b.warehouse_id.name} lot_stock_id", "Missing", b.warehouse_id.name)
            # check not default unused warehouse
            check("default" not in b.warehouse_id.name.lower() or "unused" not in b.warehouse_id.name.lower(), f"A: Branch not using default WH", "Used default", b.name)

    # B. Demo Users / Security Groups
    ops_mgr = env['res.users'].search([('name', '=', 'DEMO Operations Manager')], limit=1)
    check(bool(ops_mgr) and ops_mgr.has_group('restaurant_base.group_restaurant_operations_manager'), "B: Ops Manager", "Missing or wrong group")
    for mgr_name, branch_name in [("DEMO Nasr City Manager", "DEMO - Nasr City Branch"), 
                                  ("DEMO Maadi Manager", "DEMO - Maadi Cloud Kitchen"), 
                                  ("DEMO Asyut Manager", "DEMO - Asyut Branch")]:
        u = env['res.users'].search([('name', '=', mgr_name)], limit=1)
        check(bool(u) and u.has_group('restaurant_base.group_restaurant_branch_manager'), f"B: {mgr_name} role", "Missing or wrong group", mgr_name)
        b = env['restaurant.branch'].search([('name', '=', branch_name)], limit=1)
        if b and u:
            # If project uses manager_user_ids:
            if hasattr(b, 'manager_user_ids'):
                check(u.id in b.manager_user_ids.ids, f"B: {mgr_name} assigned to {branch_name}", "Not assigned", mgr_name)

    # C. Product Classification Integrity
    demo_products = env['product.template'].search([('name', 'like', '[DEMO]%')])
    for pt in demo_products:
        p_type = getattr(pt, 'restaurant_product_type', False)
        # 1. Ingredients
        if p_type == 'ingredient':
            check(not pt.is_menu_item, "C: Ingredient is_menu_item=False", "Is menu item", pt.name)
            check(pt.purchase_ok, "C: Ingredient purchase_ok=True", "Cannot purchase", pt.name)
            if pt.type == 'product': # if stock tracked
                pass
        # 2. Packaging
        elif p_type == 'packaging':
            check(not pt.is_menu_item, "C: Packaging is_menu_item=False", "Is menu item", pt.name)
            check(pt.purchase_ok, "C: Packaging purchase_ok=True", "Cannot purchase", pt.name)
            check(not pt.sale_ok, "C: Packaging sale_ok=False", "Can sell", pt.name)
        # 3. Menu
        elif pt.is_menu_item:
            check(pt.sale_ok, "C: Menu item sale_ok=True", "Cannot sell", pt.name)
            check(p_type in ['prepared_meal', 'beverage', 'ready_item', 'combo'], "C: Menu item type", f"Invalid type {p_type}", pt.name)
        # 4. Direct sale
        if pt.name in ['[DEMO] Cola Can', '[DEMO] Bottled Water', '[DEMO] Chocolate Brownie', '[DEMO] Packaged Chips']:
            check(pt.type == 'product', "C: Direct sale is storable", "Not storable", pt.name)

    # D. Recipe Integrity
    req_recipes = ["[DEMO] Classic Beef Burger", "[DEMO] Crispy Chicken Sandwich", "[DEMO] Double Smash Burger", "[DEMO] Grilled Chicken Meal", "[DEMO] Chicken Shawarma Wrap", "[DEMO] Koshary Bowl", "[DEMO] Kofta Rice Bowl", "[DEMO] Falafel Sandwich", "[DEMO] French Fries", "[DEMO] Fresh Mango Juice", "[DEMO] Lemon Mint Juice", "[DEMO] Turkish Coffee"]
    Recipe = env.get('restaurant.recipe')
    if Recipe:
        for name in req_recipes:
            pt = env['product.template'].search([('name', '=', name)], limit=1)
            r = Recipe.search([('product_tmpl_id', '=', pt.id), ('active', '=', True)], limit=1)
            check(bool(r), f"D: Recipe exists for {name}", "Missing", name)
            if r:
                if hasattr(r, 'state'):
                    check(r.state == 'approved', f"D: Recipe {name} approved", "Not approved", name)
                check(len(r.recipe_line_ids) > 0, f"D: Recipe {name} has lines", "No lines", name)
                for line in r.recipe_line_ids:
                    check(line.quantity > 0, f"D: Recipe {name} line qty > 0", "Zero/neg qty", name)
                    check(bool(line.uom_id), f"D: Recipe {name} line uom", "No UoM", name)
                try:
                    if hasattr(r, '_compute_total_cost'):
                        r._compute_total_cost()
                    check(True, f"D: Recipe {name} cost computation", "OK")
                except Exception as e:
                    log_fail(f"D: Recipe {name} cost computation", str(e), name)
    
    # E. Add-ons
    AddonGroup = env.get('restaurant.addon.group')
    if AddonGroup:
        for g_name in ['Burger Add-ons', 'Sandwich Add-ons', 'Bowl Add-ons', 'Beverage Add-ons']:
            ag = AddonGroup.search([('name', '=', g_name), ('active', '=', True)], limit=1)
            check(bool(ag), f"E: Addon group {g_name} exists/active", "Missing/Inactive", g_name)
            if ag:
                check(len(ag.item_ids) > 0, f"E: Addon group {g_name} has items", "Empty", g_name)
                for item in ag.item_ids:
                    check(item.product_id.name.startswith('[DEMO]'), f"E: Addon item {item.product_id.name}", "Not a demo product")
                    
    # F. Combo
    for c_name in ["[DEMO] Beef Burger Meal", "[DEMO] Crispy Chicken Meal", "[DEMO] Egyptian Bowl Combo", "[DEMO] Family Burger Box"]:
        pt = env['product.template'].search([('name', '=', c_name)], limit=1)
        if pt:
            check(pt.is_menu_item, f"F: Combo {c_name} is menu item", "False", c_name)
            if hasattr(pt, 'combo_line_ids'):
                check(len(pt.combo_line_ids) > 0, f"F: Combo {c_name} has lines", "Empty", c_name)

    # G. Kitchen Station
    Station = env.get('restaurant.kitchen.station')
    if Station:
        for s_type in ['prep', 'bar', 'packaging']:
            st = Station.search([('station_type', '=', s_type)])
            check(len(st) > 0, f"G: Kitchen station {s_type}", "Missing")
            
    # H & I. Branch Availability / Pricing
    # Just checking there are records
    if env.get('restaurant.product.branch.availability'):
        check(env['restaurant.product.branch.availability'].search_count([]) > 0, "H: Branch Availability Rules Exist", "Missing")
    if env.get('restaurant.product.branch.price'):
        check(env['restaurant.product.branch.price'].search_count([]) > 0, "I: Branch Pricing Lines Exist", "Missing")

    # J. Stock
    maadi = env['restaurant.branch'].search([('name', '=', 'DEMO - Maadi Cloud Kitchen')], limit=1)
    asyut = env['restaurant.branch'].search([('name', '=', 'DEMO - Asyut Branch')], limit=1)
    
    cb = env['product.product'].search([('name', '=', '[DEMO] Chicken Breast')], limit=1)
    if cb and maadi and maadi.warehouse_id:
        qty = sum(env['stock.quant'].search([('location_id', 'child_of', maadi.warehouse_id.lot_stock_id.id), ('product_id', '=', cb.id)]).mapped('quantity'))
        check(qty <= 0, "J: Maadi Chicken Breast shortage", f"Has stock: {qty}", cb.name)

    bp = env['product.product'].search([('name', '=', '[DEMO] Beef Patty')], limit=1)
    if bp and asyut and asyut.warehouse_id:
        qty = sum(env['stock.quant'].search([('location_id', 'child_of', asyut.warehouse_id.lot_stock_id.id), ('product_id', '=', bp.id)]).mapped('quantity'))
        check(qty <= 0, "J: Asyut Beef Patty shortage", f"Has stock: {qty}", bp.name)

    # L. Unified Availability Resolver
    ProductTemplate = env['product.template']
    if hasattr(ProductTemplate, '_get_unified_availability_payload'):
        nasr = env['restaurant.branch'].search([('name', '=', 'DEMO - Nasr City Branch')], limit=1)
        dt_14 = datetime.datetime.now().replace(hour=14, minute=0, second=0)
        dt_09 = datetime.datetime.now().replace(hour=9, minute=0, second=0)
        
        burger = env['product.template'].search([('name', '=', '[DEMO] Classic Beef Burger')], limit=1)
        if burger and nasr:
            payload = burger._get_unified_availability_payload(branch=nasr, at_datetime=dt_14, evaluate_all=True)
            check('is_available' in payload, "L: Payload has is_available", "Missing")
            
    # M. Dashboard Wizard
    Wizard = env.get('restaurant.branch.menu.status.wizard')
    if Wizard:
        check(True, "M: Dashboard Wizard Exists", "")

    # N. SQL Checks
    env.cr.execute("SELECT name, count(*) FROM product_template WHERE CAST(name AS TEXT) LIKE '%[DEMO]%' GROUP BY name HAVING count(*) > 1")
    dups = env.cr.fetchall()
    check(not dups, "N: No Duplicate DEMO Products", str(dups))

    print("--- VERIFICATION RESULTS ---")
    passes = len([r for r in results if r.startswith("[PASS]")])
    fails = len([r for r in results if r.startswith("[FAIL]")])
    warns = len([r for r in results if r.startswith("[WARN]")])
    
    for r in results:
        print(r)
        
    print(f"\nTOTAL PASS: {passes}")
    print(f"TOTAL WARN: {warns}")
    print(f"TOTAL FAIL: {fails}")

if __name__ == '__main__':
    run_tests(env)
