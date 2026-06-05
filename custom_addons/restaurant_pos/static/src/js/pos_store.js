/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { RestaurantAddonPopup } from "./restaurant_addon_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let product = vals.product_id;
        if (typeof product === "number") {
            product = this.data.models["product.product"].get(product);
        }

        let addonPayload = null;
        let extraPrice = 0;

        if (configure && product) {
            const tmplId = product.raw ? product.raw.product_tmpl_id : product.product_tmpl_id;
            const session = this.session;
            const addonMap = session && (session._restaurant_addon_map || (session.raw && session.raw._restaurant_addon_map) || {});

            if (addonMap && addonMap[tmplId] && addonMap[tmplId].length > 0) {
                // Product has restaurant add-ons
                addonPayload = await makeAwaitable(this.dialog, RestaurantAddonPopup, {
                    product: product,
                    addonGroups: addonMap[tmplId],
                });

                if (!addonPayload) {
                    // User canceled the addon popup. Abort add to cart.
                    return;
                }

                // Calculate the extra price to inject into the native logic
                for (const addon of addonPayload) {
                    extraPrice += (addon.additional_price || 0) * (addon.qty || 0);
                }

                // Inject into vals so the original addLineToOrder absorbs it natively.
                vals.price_extra = (vals.price_extra || 0) + extraPrice;
            }
        }

        // Call the native Odoo 18 addLineToOrder
        const line = await super.addLineToOrder(vals, order, opts, configure);

        // Attach the payload to the frontend orderline
        if (line && addonPayload) {
            line.restaurant_selected_addons = addonPayload;
        }

        return line;
    }
});
