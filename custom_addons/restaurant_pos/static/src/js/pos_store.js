/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { RestaurantAddonPopup } from "./restaurant_addon_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        const sessionMap = this.session && (this.session._restaurant_availability_map || (this.session.raw && this.session.raw._restaurant_availability_map));
        this.restaurant_availability_map = { ...(sessionMap || {}) };
    },

    setRestaurantAvailabilityMap(newMap) {
        this.restaurant_availability_map = { ...(newMap || {}) };
    },

    _getRestaurantAvailabilityForProduct(product) {
        const availabilityMap = this.restaurant_availability_map || this.session?._restaurant_availability_map || this.session?.raw?._restaurant_availability_map || {};
        const productId = product?.id;
        return productId ? availabilityMap[productId] || availabilityMap[String(productId)] : undefined;
    },
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let product = vals.product_id;
        if (typeof product === "number") {
            product = this.data.models["product.product"].get(product);
        }

        let addonPayload = null;
        let extraPrice = 0;

        if (configure && product) {
            const tmplId = product.raw ? product.raw.product_tmpl_id : product.product_tmpl_id;
            
            const availability = this._getRestaurantAvailabilityForProduct(product);
            if (availability && availability.is_available === false) {
                const reason = availability.reason || _t("This product is currently unavailable.");
                const blockSale = this.config.restaurant_block_unavailable_products;

                if (blockSale) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Cannot Add Product"),
                        body: _t("%s cannot be added: %s", product.display_name, reason),
                    });
                    return;
                } else {
                    const isConfirmed = await new Promise((resolve) => {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Product Unavailable"),
                            body: _t("%s is marked as unavailable: %s. Do you want to continue adding it?", product.display_name, reason),
                            confirm: () => resolve(true),
                            cancel: () => resolve(false),
                            close: () => resolve(false),
                        });
                    });
                    if (!isConfirmed) {
                        return;
                    }
                }
            }

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
