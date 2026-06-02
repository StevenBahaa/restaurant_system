/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get restaurantAvailabilityDebugLoaded() {
        // Step 2: Safe debug getter skeleton. UI is completely unchanged.
        return true;
    }
});
