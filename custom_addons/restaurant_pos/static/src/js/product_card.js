/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get restaurantAvailability() {
        if (!this.env.services.pos) return null;
        
        // Prefer the reactive store map, fallback to session
        let map = this.env.services.pos.restaurant_availability_map;
        if (!map && this.env.services.pos.session) {
            map = this.env.services.pos.session._restaurant_availability_map || 
                  (this.env.services.pos.session.raw && this.env.services.pos.session.raw._restaurant_availability_map);
        }
        if (!map) return null;
        
        const productId = this.props.productId || (this.props.product && this.props.product.id);
        if (!productId) return null;
        
        return map[String(productId)] || null;
    },

    get shouldShowRestaurantAvailabilityBadge() {
        const availability = this.restaurantAvailability;
        if (!availability) return false;
        return availability.is_available === false;
    },

    get restaurantAvailabilityBadgeLabel() {
        const availability = this.restaurantAvailability;
        if (!availability) return "";
        
        const reason = availability.reason_code;
        switch (reason) {
            case "out_of_stock": return "Out of Stock";
            case "schedule_unavailable": return "Not Now";
            case "branch_unavailable": return "Not in Branch";
            case "branch_not_configured": return "Branch Missing";
            case "evaluation_error": return "Check Error";
            case "unknown": return "Unavailable";
            default: return "Unavailable";
        }
    },

    get restaurantAvailabilityBadgeClass() {
        const availability = this.restaurantAvailability;
        if (!availability) return "";
        
        const reason = availability.reason_code;
        switch (reason) {
            case "out_of_stock": return "restaurant-pos-availability-badge-danger";
            case "schedule_unavailable": return "restaurant-pos-availability-badge-warning";
            case "branch_unavailable": return "restaurant-pos-availability-badge-secondary";
            case "branch_not_configured": return "restaurant-pos-availability-badge-warning";
            case "evaluation_error": return "restaurant-pos-availability-badge-danger";
            case "unknown": return "restaurant-pos-availability-badge-secondary";
            default: return "restaurant-pos-availability-badge-secondary";
        }
    }
});
