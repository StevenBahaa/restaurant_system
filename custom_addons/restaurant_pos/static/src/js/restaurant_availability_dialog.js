/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class RestaurantAvailabilityDialog extends Component {
    static template = "restaurant_pos.RestaurantAvailabilityDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: { type: Function, optional: true },
        title: { type: String, optional: true },
        product: { type: Object },
        availability: { type: Object, optional: true },
        mode: { type: String, validate: (v) => ["warning", "block"].includes(v) },
    };

    setup() {
        this.title = this.props.mode === 'block' ? _t("Cannot Add Product") : _t("Product Unavailable");
    }

    get productName() {
        return this.props.product?.display_name || _t("Selected product");
    }

    get reasonLabel() {
        const reason = this.props.availability?.reason_code;
        switch (reason) {
            case "out_of_stock": return _t("Out of Stock");
            case "schedule_unavailable": return _t("Not Now");
            case "branch_unavailable": return _t("Not in Branch");
            case "branch_not_configured": return _t("Branch Missing");
            case "evaluation_error": return _t("Check Error");
            case "unknown": return _t("Unavailable");
            default: return _t("Unavailable");
        }
    }

    get reasonText() {
        return this.props.availability?.reason || _t("This product is currently unavailable.");
    }

    get checkedAt() {
        return this.props.availability?.checked_at || "";
    }

    get isWarning() {
        return this.props.mode === 'warning';
    }

    get isBlock() {
        return this.props.mode === 'block';
    }

    confirm() {
        this.props.close(true);
    }

    cancel() {
        this.props.close(false);
    }
}
