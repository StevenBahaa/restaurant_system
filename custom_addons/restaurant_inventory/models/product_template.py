from odoo import models, api, fields
from odoo.fields import Datetime

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_active_stock_override_for_branch(self, branch):
        """
        Return active override for product/branch/company at current time.
        """
        self.ensure_one()
        now = Datetime.now()
        domain = [
            ("product_tmpl_id", "=", self.id),
            ("branch_id", "=", branch.id),
            ("company_id", "=", branch.company_id.id),
            ("active", "=", True),
            ("date_from", "<=", now),
            "|",
            ("date_to", "=", False),
            ("date_to", ">=", now),
        ]
        # Overlaps are prevented by constraints, but we limit=1 and order by most recent just in case
        return self.env["restaurant.branch.stock.override"].search(domain, order="date_from desc, id desc", limit=1)

    def _get_branch_stock_location(self, branch):
        """
        Return branch.warehouse_id.lot_stock_id.
        """
        self.ensure_one()
        if branch.warehouse_id and branch.warehouse_id.lot_stock_id:
            return branch.warehouse_id.lot_stock_id
        return self.env["stock.location"]

    def _get_available_qty_in_location(self, product, location):
        """
        Return stock quantity available at that location for a product.product.
        """
        self.ensure_one()
        if not product or not location:
            return 0.0

        quants = self.env["stock.quant"].search([
            ("product_id", "=", product.id),
            ("location_id", "child_of", location.id),
        ])
        
        # Available quantity = sum(quantity - reserved_quantity)
        available_qty = sum(quant.quantity - quant.reserved_quantity for quant in quants)
        return available_qty

    def _get_recipe_stock_requirements(self, quantity=1):
        """
        Return critical ingredient requirements for this product based on approved active recipe.
        Returns a list of dicts.
        """
        self.ensure_one()
        requirements = []
        
        recipe = self._get_approved_recipe_for_product(self)
        if not recipe:
            return requirements
            
        for line in recipe.recipe_line_ids:
            if not line.is_critical:
                continue
                
            # required quantity uses actual_quantity which includes wastage
            req_qty = line.actual_quantity * quantity
            
            # The ingredient is a product.template. We need the product.product for stock.quant
            ingredient_tmpl = line.ingredient_product_id
            ingredient_product = ingredient_tmpl.product_variant_id
            
            if not ingredient_product:
                continue

            requirements.append({
                "product_id": ingredient_product.id,
                "product_name": ingredient_product.display_name,
                "product_tmpl": ingredient_tmpl,
                "product_product": ingredient_product,
                "required_qty": req_qty,
                "uom_id": line.uom_id,
                "uom_name": line.uom_id.name,
            })
            
        return requirements

    def _get_stock_availability_for_branch(self, branch, quantity=1):
        """
        Return the main structured stock availability payload for a product at a branch.
        """
        self.ensure_one()
        
        payload = {
            "is_available": True,
            "reason": "",
            "reason_code": "",
            "product_tmpl_id": self.id,
            "branch_id": branch.id,
            "company_id": branch.company_id.id,
            "manual_override": False,
            "override_id": False,
            "blocking_ingredients": [],
            "warnings": [],
        }

        # 1. Manual Override check
        override = self._get_active_stock_override_for_branch(branch)
        if override:
            payload["is_available"] = override.is_available
            payload["reason"] = override.reason
            payload["reason_code"] = "manual_override"
            payload["manual_override"] = True
            payload["override_id"] = override.id
            return payload
            
        # 2. Product type behavior
        if getattr(self, "restaurant_product_type", None) not in ["prepared_meal", "beverage", "ready_item", "combo"]:
            payload["reason_code"] = "not_applicable"
            return payload
            
        if self.restaurant_product_type == "combo":
            return payload
            
        if self.restaurant_product_type == "ready_item":
            return payload

        # For prepared_meal and beverage
        recipe = self._get_approved_recipe_for_product(self)
        
        if not recipe:
            if self.restaurant_product_type == "prepared_meal":
                payload["is_available"] = False
                payload["reason"] = "Unavailable — Missing approved recipe."
                payload["reason_code"] = "missing_approved_recipe"
                return payload
            elif self.restaurant_product_type == "beverage":
                return payload

        # 3. Branch Stock Location check
        location = self._get_branch_stock_location(branch)
        if not location:
            payload["is_available"] = False
            payload["reason"] = "Unavailable — branch stock location is not configured."
            payload["reason_code"] = "missing_branch_stock_location"
            return payload
            
        # 4. Evaluate Recipe Requirements
        requirements = self._get_recipe_stock_requirements(quantity=quantity)
        
        for req in requirements:
            ingredient = req["product_product"]
            req_qty_recipe_uom = req["required_qty"]
            recipe_uom = req["uom_id"]
            
            # Stock is tracked in the ingredient's default UoM
            stock_uom = ingredient.uom_id
            
            if recipe_uom != stock_uom:
                req_qty_stock_uom = recipe_uom._compute_quantity(req_qty_recipe_uom, stock_uom)
            else:
                req_qty_stock_uom = req_qty_recipe_uom
                
            # Check stock
            available_qty = self._get_available_qty_in_location(ingredient, location)
            
            if available_qty < req_qty_stock_uom:
                # Add to blocking ingredients
                payload["blocking_ingredients"].append({
                    "product_id": ingredient.id,
                    "product_name": ingredient.display_name,
                    "required_qty": req_qty_stock_uom,
                    "available_qty": available_qty,
                    "uom_name": stock_uom.name,
                })
                
        if payload["blocking_ingredients"]:
            payload["is_available"] = False
            first_blocker = payload["blocking_ingredients"][0]
            payload["reason"] = f"Unavailable — {first_blocker['product_name']} out of stock."
            payload["reason_code"] = "critical_ingredient_out_of_stock"
            
        return payload
