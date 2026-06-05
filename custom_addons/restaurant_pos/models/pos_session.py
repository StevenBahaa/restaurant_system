from odoo import models
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = "pos.session"

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data=only_data)

        try:
            # Safely navigate to the pos.session response bucket
            session_data_bucket = response.get("pos.session", {}).get("data", [])
            if not session_data_bucket or not isinstance(session_data_bucket, list):
                _logger.warning("restaurant_pos: Missing or unexpectedly shaped pos.session data bucket. Aborting injection.")
                return response
            
            # Extract loaded products
            product_data = response.get("product.product", {}).get("data", [])
            product_ids = [p["id"] for p in product_data if isinstance(p, dict) and "id" in p]
            
            # Retrieve products safely
            products = self.env["product.product"].browse(product_ids).exists()
            
            # Resolve Branch securely
            branch = False
            if hasattr(self.config_id, '_get_restaurant_branch'):
                branch = self.config_id._get_restaurant_branch()
            elif hasattr(self.config_id, 'branch_id'):
                branch = self.config_id.branch_id
                
        except Exception:
            _logger.error("restaurant_pos: Initialization crash in load_data. Aborting map injections.", exc_info=True)
            return response

        # 1. Independent Availability Block
        try:
            _logger.info(
                "restaurant_pos: Evaluating availability for %d POS products on Branch ID: %s (Session ID: %s)", 
                len(products), 
                branch.id if branch else 'None', 
                self.id
            )
            availability_map = {}
            if products:
                availability_map = products._get_pos_availability_payload_bulk(
                    branch=branch,
                    quantity=1,
                )
            session_data_bucket[0]["_restaurant_availability_map"] = availability_map
        except Exception:
            _logger.error(
                "restaurant_pos: Failed to build _restaurant_availability_map for Session ID: %s. Continuing with empty map.",
                self.id,
                exc_info=True
            )
            session_data_bucket[0]["_restaurant_availability_map"] = {}

        # 2. Independent Add-on Block
        try:
            addon_map = {}
            if products:
                product_templates = products.mapped('product_tmpl_id')
                addon_map = product_templates._get_pos_addon_payload_bulk()
            session_data_bucket[0]["_restaurant_addon_map"] = addon_map
        except Exception:
            _logger.error(
                "restaurant_pos: Failed to build _restaurant_addon_map for Session ID: %s. Continuing with empty map.",
                self.id,
                exc_info=True
            )
            session_data_bucket[0]["_restaurant_addon_map"] = {}
        
        return response

    def action_refresh_restaurant_availability(self):
        self.ensure_one()
        try:
            branch = False
            if hasattr(self.config_id, '_get_restaurant_branch'):
                branch = self.config_id._get_restaurant_branch()
            elif hasattr(self.config_id, 'branch_id'):
                branch = self.config_id.branch_id

            # Safe standard POS product fetch
            domain = [('available_in_pos', '=', True)]
            if (
                hasattr(self.config_id, "limit_categories")
                and hasattr(self.config_id, "iface_available_categ_ids")
                and self.config_id.limit_categories
                and self.config_id.iface_available_categ_ids
            ):
                domain.append(("pos_categ_ids", "in", self.config_id.iface_available_categ_ids.ids))
            
            products = self.env['product.product'].search(domain)
            
            if not products:
                return {}

            _logger.info(
                "restaurant_pos: Manual refresh evaluating availability for %d POS products on Branch ID: %s (Session ID: %s)", 
                len(products), 
                branch.id if branch else 'None', 
                self.id
            )

            availability_map = products._get_pos_availability_payload_bulk(
                branch=branch,
                quantity=1,
            )
            return availability_map
        except Exception:
            _logger.error(
                "restaurant_pos: Failed to manually refresh availability for Session ID: %s",
                self.id,
                exc_info=True
            )
            return {}
