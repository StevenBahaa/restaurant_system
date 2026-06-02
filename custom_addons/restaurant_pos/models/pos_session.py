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
            
            _logger.info(
                "restaurant_pos: Evaluating availability for %d POS products on Branch ID: %s (Session ID: %s)", 
                len(products), 
                branch.id if branch else 'None', 
                self.id
            )
            
            # Build availability payload map natively leveraging UC-I Step 2
            availability_map = {}
            if products:
                availability_map = products._get_pos_availability_payload_bulk(
                    branch=branch,
                    quantity=1,
                )
            
            # Safely inject directly into the target serialization hook
            session_data_bucket[0]["_restaurant_availability_map"] = availability_map
            
        except Exception:
            _logger.error(
                "restaurant_pos: Critical injection crash inside POS load_data. Original response returned unchanged.", 
                exc_info=True
            )
        
        return response
