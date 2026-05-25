# UC-09 Branch-Specific Pricing: Final QA / Test Report

**Date:** 2026-05-25
**Scope:** Backend and Domain Implementation (Steps 1 through 8)

## 1. Scope
This QA report covers the end-to-end backend validation of UC-09 (Branch-Specific Pricing) for the Restaurant & Cloud Kitchen ERP built on Odoo 18 Community. This encompasses the data model, price resolution logic, validations, overlap protection, below-cost warnings, audit logging, security rules, the bulk update wizard, and backend UX polish.

## 2. Tested Files & Features
The following core files were validated against business rules:
- `models/restaurant_branch_price_line.py` (Model, validation, below-cost logic)
- `models/restaurant_branch_price_history.py` (Audit logging model)
- `models/product_template_price.py` (Price resolver, helper fields, UX compute methods)
- `wizard/restaurant_branch_price_bulk_wizard.py` (Bulk update logic)
- `security/ir.model.access.csv` & `security/restaurant_security.xml` (Access control)
- `views/product_template_views.xml` (Form tabs, kanban badges, search filters)
- `views/restaurant_branch_price_bulk_wizard_views.xml` (Wizard UI)

## 3. Manual Test Cases Validated

### Model Foundation & UX
- **[PASS]** `restaurant.branch.price.line` and history models exist and link correctly.
- **[PASS]** "Branch Pricing" tab renders securely inside `product.template` for menu items only.
- **[PASS]** UX Banners dynamically reflect rule counts, scheduled future rules, and below-cost warnings.
- **[PASS]** Kanban badges ("Branch Pricing", "Below Cost", "Future Price") appear properly without breaking non-menu views.
- **[PASS]** Monetary fields dynamically resolve currencies correctly.

### Basic Validations
- **[PASS]** Attempting to save a price <= 0 raises a ValidationError.
- **[PASS]** Start Date > End Date raises a ValidationError.
- **[PASS]** Missing both Branch and Channel raises a ValidationError.
- **[PASS]** Branch compatibility with `product.company_id` is strictly enforced.

### Resolver Logic
- **[PASS]** `_get_matching_branch_price_rule` resolves the correct rule using deterministic priority:
  1. Branch + Channel
  2. Channel only
  3. Branch only
  4. Global `list_price`
- **[PASS]** Tie-breaking works accurately (latest `date_from` -> lowest `sequence` -> latest `id`).
- **[PASS]** Expired rules and future rules are correctly ignored when resolving the current active price.

### Overlap Prevention
- **[PASS]** Overlapping dates for the identical Branch/Channel/Product combination block save.
- **[PASS]** Identical combinations with non-overlapping dates save successfully.

### Below-Cost Warning
- **[PASS]** Dynamically evaluates against `standard_price` (or recipe cost if enabled).
- **[PASS]** Triggers UI warning decoration and form banner.
- **[PASS]** Does not block the record save, acting as a non-intrusive warning.

### Price History (Audit Log)
- **[PASS]** Logs track creation, price changes, date changes, and active/archive toggles securely.
- **[PASS]** Note-only updates do not clutter the audit log.
- **[PASS]** Failed validations correctly rollback and do not produce ghost history lines.
- **[PASS]** List UI is compact; technical fields are hidden.

### Security
- **[PASS]** Pricing Managers & Operations Managers can edit/create/unlink rules and use the bulk wizard.
- **[PASS]** Branch Managers & Company Availability Managers are restricted to read-only views for pricing.
- **[PASS]** Model `write`/`create` overrides protect the One2many fields from unauthorized nested saves.

### Bulk Update Wizard
- **[PASS]** Mode toggles (Fixed Price, Amount +/-, Percentage +/-) compute accurate base prices.
- **[PASS]** Overlaps are elegantly caught by model validation.
- **[PASS]** Exact matches update existing rules rather than duplicating them.
- **[PASS]** The wizard closes securely without unreliable client actions.

## 4. Shell Test Cases Evaluated
During QA, `env(user=user, su=False)` was used extensively to simulate non-superuser interactions.
- **[PASS]** Multi-company context tests confirmed `user.company_ids` restrictions apply to branch visibility inside the wizard and the underlying lines.
- **[PASS]** Read/write operations evaluated successfully under strictly unprivileged contexts.

## 5. Pass/Fail Result per Area
| Area | Status |
|---|---|
| Foundation & UX | **PASS** |
| Validation & Overlaps | **PASS** |
| Price Resolver | **PASS** |
| Below-Cost Logic | **PASS** |
| Audit History | **PASS** |
| Access Control | **PASS** |
| Bulk Wizard | **PASS** |
| Multi-Company Rules | **PASS** |

## 6. Bugs Found
No new functional bugs were discovered during Step 9 QA. 
*(Note: Step 8 identified and patched minor UX issues and search domain bugs prior to final QA execution).*

## 7. Bugs Fixed During QA
None required during Step 9. All systems stable.

## 8. Remaining Out-of-Scope Items
- **POS Integration**: Fetching and applying the resolved branch prices inside the Point of Sale session is pending.
- **Frontend / Customer Ordering UI**: Webshop/e-commerce integration is pending.
- **OWL / JS**: No frontend interface components have been customized.

## 9. Final Verdict
**UC-09 backend/domain PASSED.** 
The Branch-Specific Pricing backend architecture is robust, secure, and ready for frontend integration.
