/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

export class RestaurantAddonPopup extends Component {
    static template = "restaurant_pos.RestaurantAddonPopup";
    static components = { Dialog, ProductInfoBanner };
    static props = {
        product: { type: Object, optional: true },
        addonGroups: { type: Array, optional: true },
        getPayload: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        const selections = {};
        const groups = this.props.addonGroups || [];
        
        // Initialize state securely without mutating the original prop
        groups.forEach(g => {
            if (g.items && Array.isArray(g.items)) {
                g.items.forEach(item => {
                    if (item && item.addon_item_id) {
                        selections[item.addon_item_id] = 0;
                    }
                });
            }
        });
        
        this.state = useState({
            selections: selections,
        });
    }

    // Safely sum up selected quantities across a specific add-on group
    getGroupQuantity(groupId) {
        let total = 0;
        const group = (this.props.addonGroups || []).find(g => g.addon_group_id === groupId);
        if (group && group.items) {
            group.items.forEach(item => {
                total += this.state.selections[item.addon_item_id] || 0;
            });
        }
        return total;
    }

    // Validate that all REQUIRED groups satisfy their min_selection
    isValid() {
        const groups = this.props.addonGroups || [];
        if (groups.length === 0) return true;
        
        for (const group of groups) {
            const qty = this.getGroupQuantity(group.addon_group_id);
            if (group.required && qty < group.min_selection) {
                return false;
            }
        }
        return true;
    }

    // Check if we can increment an item based on its max_quantity and the group's max_selection
    canAdd(group, item) {
        if (this.state.selections[item.addon_item_id] >= item.max_quantity) return false;
        if (group.max_selection > 0 && this.getGroupQuantity(group.addon_group_id) >= group.max_selection) return false;
        return true;
    }

    // Check if we can decrement an item
    canRemove(item) {
        return this.state.selections[item.addon_item_id] > 0;
    }

    increaseItem(group, item) {
        if (this.canAdd(group, item)) {
            this.state.selections[item.addon_item_id]++;
        }
    }

    decreaseItem(group, item) {
        if (this.canRemove(item)) {
            this.state.selections[item.addon_item_id]--;
        }
    }

    toggleItem(group, item) {
        if (this.state.selections[item.addon_item_id] > 0) {
            this.state.selections[item.addon_item_id] = 0;
        } else {
            if (this.canAdd(group, item)) {
                this.state.selections[item.addon_item_id] = 1;
            }
        }
    }

    _resolveGroupAndItem(ev) {
        const dataset = ev.currentTarget.dataset;
        const groupId = parseInt(dataset.groupId, 10);
        const itemId = parseInt(dataset.itemId, 10);
        
        const group = (this.props.addonGroups || []).find(g => g.addon_group_id === groupId);
        let item = null;
        if (group && group.items) {
            item = group.items.find(i => i.addon_item_id === itemId);
        }
        return { group, item };
    }

    onItemClick(ev) {
        const { group, item } = this._resolveGroupAndItem(ev);
        if (group && item && item.max_quantity === 1) {
            this.toggleItem(group, item);
        }
    }

    onIncreaseItem(ev) {
        const { group, item } = this._resolveGroupAndItem(ev);
        if (group && item) {
            this.increaseItem(group, item);
        }
    }

    onDecreaseItem(ev) {
        const { group, item } = this._resolveGroupAndItem(ev);
        if (group && item) {
            this.decreaseItem(group, item);
        }
    }

    onToggleItem(ev) {
        const { group, item } = this._resolveGroupAndItem(ev);
        if (group && item) {
            this.toggleItem(group, item);
        }
    }

    confirm() {
        if (!this.isValid()) return;
        
        const payload = [];
        const groups = this.props.addonGroups || [];
        
        // Build isolated return payload
        groups.forEach(group => {
            if (group.items) {
                group.items.forEach(item => {
                    const qty = this.state.selections[item.addon_item_id] || 0;
                    if (qty > 0) {
                        payload.push({
                            addon_item_id: item.addon_item_id,
                            display_name: item.display_name,
                            qty: qty,
                            additional_price: item.additional_price || 0,
                            kitchen_note: item.kitchen_note || "",
                            addon_group_id: group.addon_group_id,
                            product_addon_group_id: group.product_addon_group_id
                        });
                    }
                });
            }
        });
        
        if (this.props.getPayload) {
            this.props.getPayload(payload);
        }
        this.props.close();
    }
}
