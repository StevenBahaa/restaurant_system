/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

if (Orderline.props?.line?.shape && !Orderline.props.line.shape.restaurant_selected_addons) {
    Orderline.props.line.shape.restaurant_selected_addons = {
        type: Array,
        optional: true,
    };
}

patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.restaurant_selected_addons) {
            this.restaurant_selected_addons = [];
        }
    },
    
    can_be_merged_with(orderline) {
        if (
            (this.restaurant_selected_addons && this.restaurant_selected_addons.length > 0) ||
            (orderline.restaurant_selected_addons && orderline.restaurant_selected_addons.length > 0)
        ) {
            return false;
        }
        return super.can_be_merged_with(orderline);
    },

    serialize() {
        const res = super.serialize(...arguments);
        if (this.restaurant_selected_addons && this.restaurant_selected_addons.length > 0) {
            res.restaurant_addon_details = this.restaurant_selected_addons;
        }
        return res;
    },

    getDisplayData() {
        const data = super.getDisplayData();
        data.restaurant_selected_addons = (this.restaurant_selected_addons || []).map(addon => {
            return {
                ...addon,
                formatted_price: addon.additional_price > 0 
                    ? formatCurrency(addon.additional_price, this.currency) 
                    : ""
            };
        });
        return data;
    }
});
