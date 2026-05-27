from . import models

def post_init_hook(env):
    """
    Ensure existing recipe lines and add-on ingredient lines 
    have is_critical=True.
    """
    recipe_lines = env['restaurant.recipe.line'].with_context(active_test=False).search([('is_critical', '!=', True)])
    if recipe_lines:
        recipe_lines.write({'is_critical': True})
        
    addon_lines = env['restaurant.addon.item.ingredient'].with_context(active_test=False).search([('is_critical', '!=', True)])
    if addon_lines:
        addon_lines.write({'is_critical': True})
