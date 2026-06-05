from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    restaurant_addon_details = fields.Json(
        string='Selected Add-ons',
        help="JSON payload containing selected add-ons from POS frontend."
    )

    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if "restaurant_addon_details" not in fields:
            fields.append("restaurant_addon_details")
        return fields

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'restaurant_addon_details' in vals:
                vals['restaurant_addon_details'] = self._sanitize_addon_details(vals['restaurant_addon_details'])
        return super().create(vals_list)

    def write(self, vals):
        if 'restaurant_addon_details' in vals:
            vals['restaurant_addon_details'] = self._sanitize_addon_details(vals['restaurant_addon_details'])
        return super().write(vals)

    @api.model
    def _sanitize_addon_details(self, payload):
        if not payload:
            return []
            
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                _logger.warning("Invalid JSON string in restaurant_addon_details")
                return []
                
        if not isinstance(payload, list):
            _logger.warning("restaurant_addon_details payload is not a list")
            return []

        allowed_keys = {
            'addon_item_id': int,
            'display_name': str,
            'qty': (int, float),
            'additional_price': (int, float),
            'kitchen_note': str,
            'addon_group_id': int,
            'product_addon_group_id': int
        }

        sanitized_list = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            
            sanitized_item = {}
            for key, expected_type in allowed_keys.items():
                if key in item:
                    val = item[key]
                    if val is not None:
                        try:
                            # Coerce type safely
                            if expected_type == str:
                                sanitized_item[key] = str(val)
                            elif expected_type == int:
                                sanitized_item[key] = int(val)
                            elif expected_type == (int, float):
                                sanitized_item[key] = float(val)
                        except (ValueError, TypeError):
                            pass
            
            if sanitized_item:
                sanitized_list.append(sanitized_item)

        return sanitized_list
