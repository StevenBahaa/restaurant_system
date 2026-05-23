# scripts/create_demo_data.py
import logging

_logger = logging.getLogger(__name__)

def create_or_update_product(env, name, product_type, standard_price=0.0, list_price=0.0, is_menu_item=False):
    product = env['product.template'].search([('name', '=', name)], limit=1)
    vals = {
        'restaurant_product_type': product_type,
        'standard_price': standard_price,
        'list_price': list_price,
        'is_menu_item': is_menu_item,
    }
    if product:
        product.write(vals)
        print(f"Updated product: {name}")
    else:
        vals['name'] = name
        product = env['product.template'].create(vals)
        print(f"Created product: {name}")
    return product

print("Starting demo data script...")

# 1. Bulk BBQ Sauce (Ingredient)
bulk_sauce = create_or_update_product(
    env,
    name="Bulk BBQ Sauce",
    product_type="ingredient",
    standard_price=5.0, # e.g. 5.0 per kg or unit
    list_price=0.0,
    is_menu_item=False
)

# 2. BBQ Sauce Cup Packaging (Packaging)
cup_packaging = create_or_update_product(
    env,
    name="BBQ Sauce Cup Packaging",
    product_type="packaging",
    standard_price=0.10,
    list_price=0.0,
    is_menu_item=False
)

# 3. BBQ Sauce Portion (Ready Item)
bbq_sauce_portion = create_or_update_product(
    env,
    name="BBQ Sauce Portion",
    product_type="ready_item",
    standard_price=0.0, # computed from recipe
    list_price=1.50,
    is_menu_item=True
)

# 4. Create Recipe
recipe = env['restaurant.recipe'].search([('product_tmpl_id', '=', bbq_sauce_portion.id)], limit=1)
if not recipe:
    recipe_vals = {
        'name': 'BBQ Sauce Portion Recipe',
        'product_tmpl_id': bbq_sauce_portion.id,
        'company_id': env.company.id,
        'state': 'draft',
        'recipe_line_ids': [
            (0, 0, {
                'ingredient_product_id': bulk_sauce.id,
                'quantity': 0.05,
                'uom_id': bulk_sauce.uom_id.id,
            }),
            (0, 0, {
                'ingredient_product_id': cup_packaging.id,
                'quantity': 1.0,
                'uom_id': cup_packaging.uom_id.id,
            }),
        ]
    }
    recipe = env['restaurant.recipe'].create(recipe_vals)
    print("Created recipe for BBQ Sauce Portion.")
    recipe.action_approve()
    print("Approved recipe.")
else:
    print("Recipe for BBQ Sauce Portion already exists.")

print("Demo data script finished successfully.")
env.cr.commit()
