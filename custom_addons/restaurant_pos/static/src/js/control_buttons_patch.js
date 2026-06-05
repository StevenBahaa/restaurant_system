/** @odoo-module **/

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.availabilityState = useState({ isRefreshing: false });
    },
    
    async clickRefreshAvailability() {
        if (this.availabilityState.isRefreshing) return;
        this.availabilityState.isRefreshing = true;

        try {
            const response = await this.env.services.orm.call(
                "pos.session",
                "action_refresh_restaurant_availability",
                [[this.pos.session.id]]
            );
            
            this.pos.setRestaurantAvailabilityMap(response || {});
            
            if (response && Object.keys(response).length > 0) {
                this.env.services.notification.add(_t("Availability refreshed."), { type: "success" });
            } else {
                this.env.services.notification.add(_t("Availability refreshed, but no products were returned."), { type: "warning" });
            }
        } catch (error) {
            this.env.services.notification.add(_t("Failed to refresh availability. You may be offline."), { type: "danger" });
            console.error("Availability refresh failed:", error);
        } finally {
            this.availabilityState.isRefreshing = false;
        }
    }
});
