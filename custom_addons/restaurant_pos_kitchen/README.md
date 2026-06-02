# Restaurant POS Kitchen Integration

## Purpose
This module acts as the integration bridge between the financial POS (`restaurant_pos`) and the operational backend kitchen (`restaurant_kitchen`). It allows POS orders to automatically generate Kitchen Preparation Orders based on branch and channel-specific configurations.

## Scope
- POS → Kitchen integration will be implemented in later steps.
- **No POS frontend** in this module yet.
- **No accounting/payment/stock side effects.**
- Follows strict Odoo 18 Multi-Company rules and relies heavily on `base.group_user` isolation.

## Dependencies
- `point_of_sale`
- `restaurant_pos`
- `restaurant_kitchen`
*(Does not depend directly on `restaurant_menu` or stock/accounting).*

## Status
Step 2 skeleton only.
