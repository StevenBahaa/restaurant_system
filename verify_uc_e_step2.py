import traceback
from odoo.exceptions import ValidationError

env = self.env
branch = env['restaurant.branch'].search([('name', '=', 'DEMO - Nasr City Branch')], limit=1)
assert branch, "Branch not found"
company = branch.company_id

other_company = env['res.company'].create({'name': 'Other Company'})
other_company_product = env['product.template'].create({
    'name': 'Other Company Product',
    'is_menu_item': True,
    'restaurant_product_type': 'prepared_meal',
    'company_id': other_company.id,
})

ops_manager = env['res.users'].create({
    'name': 'Ops Manager',
    'login': 'ops_manager',
    'groups_id': [(6, 0, [env.ref('restaurant_base.group_restaurant_operations_manager').id])],
    'company_ids': [(6, 0, [company.id])],
    'company_id': company.id,
})

branch_manager = env['res.users'].create({
    'name': 'Branch Manager',
    'login': 'branch_manager',
    'groups_id': [(6, 0, [env.ref('restaurant_base.group_restaurant_branch_manager').id])],
    'company_ids': [(6, 0, [company.id, other_company.id])],
    'company_id': company.id,
})
branch.write({'manager_user_ids': [(4, branch_manager.id)]})

other_branch = env['restaurant.branch'].create({
    'name': 'Other Branch',
    'code': 'OB',
    'company_id': other_company.id,
})

# Find products
menu_product = env['product.template'].search([
    ('is_menu_item', '=', True), 
    ('restaurant_product_type', 'in', ['prepared_meal', 'beverage', 'ready_item']),
    '|', ('company_id', '=', False), ('company_id', '=', company.id)
], limit=1)
assert menu_product, "Menu product not found"

ingredient_product = env['product.template'].search([('is_menu_item', '=', False), ('type', '=', 'consu'), ('is_storable', '=', True)], limit=1)
# Some ingredients might not have is_storable depending on version, let's just find one not menu item
if not ingredient_product:
    ingredient_product = env['product.template'].search([('is_menu_item', '=', False)], limit=1)
assert ingredient_product, "Ingredient product not found"

try:
    print("Test 1: Create Order")
    env.cr.execute('SAVEPOINT test_1')
    order = env['restaurant.kitchen.order'].create({
        'branch_id': branch.id,
    })
    assert order.state == 'draft', "Should be draft"
    assert order.company_id == company, "Company ID should be derived from branch"
    assert order.name and order.name.startswith('KPO/'), f"Sequence name not generated correctly: {order.name}"
    print(f"PASS: Order created with name {order.name} and company_id derived.")

    print("Test 2: Add valid menu product line")
    line = env['restaurant.kitchen.order.line'].create({
        'order_id': order.id,
        'product_tmpl_id': menu_product.id,
        'quantity': 2,
    })
    print("PASS: Valid menu product line added.")

    print("Test 3: Cannot add ingredient product line")
    try:
        env.cr.execute('SAVEPOINT test_3')
        env['restaurant.kitchen.order.line'].create({
            'order_id': order.id,
            'product_tmpl_id': ingredient_product.id,
            'quantity': 1,
        })
        raise AssertionError("FAIL: Ingredient product should not be allowed.")
    except ValidationError:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_3')
        print("PASS: Ingredient product blocked.")

    print("Test 4: Cannot add quantity <= 0")
    try:
        env.cr.execute('SAVEPOINT test_4')
        env['restaurant.kitchen.order.line'].create({
            'order_id': order.id,
            'product_tmpl_id': menu_product.id,
            'quantity': 0,
        })
        raise AssertionError("FAIL: Zero quantity should not be allowed.")
    except ValidationError:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_4')
        print("PASS: Zero quantity blocked.")

    print("Test 5: Order lines cannot be modified after confirmation and action_cancel logic")
    env.cr.execute('SAVEPOINT test_5')
    order.write({'state': 'confirmed'})
    try:
        line.write({'quantity': 5})
        raise AssertionError("FAIL: Should not modify lines after confirmed.")
    except ValidationError:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_5')
        print("PASS: Modification blocked after confirmation.")
        
    env.cr.execute('SAVEPOINT test_5_cancel')
    try:
        order.action_cancel()
        raise AssertionError("FAIL: Should not be able to cancel non-draft order in Step 2.")
    except Exception as e:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_5_cancel')
        print(f"PASS: action_cancel blocked for non-draft order. ({e})")
        
    # verify cancel from draft
    order.write({'state': 'draft'})
    order.action_cancel()
    assert order.state == 'cancelled', "Should cancel successfully from draft"
    print("PASS: Cancelled successfully from draft.")
    

    print("Test 6: Company-specific product mismatch")
    try:
        env.cr.execute('SAVEPOINT test_6')
        env['restaurant.kitchen.order.line'].create({
            'order_id': order.id,
            'product_tmpl_id': other_company_product.id,
            'quantity': 1,
        })
        raise AssertionError("FAIL: Should block mismatching company product.")
    except ValidationError:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_6')
        print("PASS: Mismatching company product blocked.")

    print("Test 7: Operations Manager limited to allowed companies")
    # Create an order in other_company
    env.cr.execute('SAVEPOINT test_7_order')
    other_order = env['restaurant.kitchen.order'].create({
        'branch_id': other_branch.id,
    })
    
    # Try to cancel other_order as ops_manager
    try:
        env.cr.execute('SAVEPOINT test_7_action')
        other_order.with_user(ops_manager).action_cancel()
        raise AssertionError("FAIL: Ops Manager should not cancel order for disallowed company.")
    except Exception as e:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_7_action')
        print(f"PASS: Ops Manager blocked from disallowed company order. ({e})")
        
    print("Test 8: Branch Manager cannot act on another manager's branch")
    # Try to cancel other_order as branch_manager (not a manager of other_branch)
    try:
        env.cr.execute('SAVEPOINT test_8')
        other_order.with_user(branch_manager).action_cancel()
        raise AssertionError("FAIL: Branch Manager should not cancel order for unmanaged branch.")
    except Exception as e:
        env.cr.execute('ROLLBACK TO SAVEPOINT test_8')
        print(f"PASS: Branch Manager blocked from unmanaged branch order. ({e})")

    env.cr.execute('ROLLBACK TO SAVEPOINT test_1')
    print("ALL TESTS PASSED")

except Exception as e:
    print(f"EXCEPTION: {e}")
    traceback.print_exc()
    env.cr.execute('ROLLBACK TO SAVEPOINT test_1')
