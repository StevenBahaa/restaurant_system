# Restaurant & Cloud Kitchen ERP — Project Plan

**Platform:** Odoo 18 Community  
**Repository:** https://github.com/StevenBahaa/restaurant_system.git  
**Last Updated:** 2026-06-02

---

## Overview

This project builds a full Restaurant & Cloud Kitchen ERP on Odoo 18 Community, targeting realistic Egyptian market restaurant operations. The development follows a strict backend-domain-first approach, with POS and frontend integrations planned for later phases.

---

## Module Architecture

| Module | Purpose | Status |
|---|---|---|
| `restaurant_base` | Core branch, company, and shared infrastructure | ✅ Complete |
| `restaurant_menu` | Product classification, recipes, add-ons, variants, combos | ✅ Complete |
| `restaurant_recipe` | Recipe management and cost resolution | ✅ Complete |
| `restaurant_inventory` | Branch stock overrides and stock-linked availability | ✅ Complete |
| `restaurant_kitchen` | Kitchen Preparation Orders, Tickets, Station Routing | ✅ Complete |
| `restaurant_analytics` | Reporting and dashboards | 🔲 Planned |
| `restaurant_pos` | POS integration and kitchen screen frontend | 🔲 Planned |
| `restaurant_delivery` | Delivery and catering order integration | 🔲 Planned |
| `restaurant_procurement` | Automated procurement from kitchen consumption | 🔲 Planned |
| `restaurant_accountability` | Financial accountability and audit layer | 🔲 Planned |
| `restaurant_securit` | Custom security groups and access rules | ✅ Complete |

---

## Completed Use Cases

| ID | Title | Module | Closed |
|---|---|---|---|
| UC-07 | Combo Meals | `restaurant_menu` | ✅ |
| UC-08 | Branch-Specific Availability | `restaurant_menu` / `restaurant_base` | ✅ |
| UC-09 | Branch-Specific Pricing | `restaurant_menu` / `restaurant_base` | ✅ |
| UC-10 | Define Preparation Time & Kitchen Station | `restaurant_menu` | ✅ |
| UC-11 | Control Stock-Linked Availability | `restaurant_inventory` | ✅ |
| UC-12 | Configure Menu Scheduling | `restaurant_menu` | ✅ |
| UC-D | Demo Data Verification & Setup | All | ✅ |
| UC-A | Unified Menu Availability Resolver | `restaurant_menu` | ✅ |
| UC-B | Branch Menu Status Dashboard | `restaurant_base` / `restaurant_menu` | ✅ |
| UC-E | Kitchen Preparation Orders & Ticket Routing | `restaurant_kitchen` | ✅ |
| UC-G | POS Order to Kitchen Integration | `restaurant_pos_kitchen` | ✅ |
| UC-H | Kitchen Auto Dispatch Policy | `restaurant_pos_kitchen` | ✅ |
| UC-I | POS Availability Backend Loader | `restaurant_pos` | ✅ |
| UC-J | POS UI Badges (Frontend Consumption) | `restaurant_pos` | ✅ |
| UC-K | Cancellation & Void Workflows | `restaurant_pos_kitchen` | ✅ |

---

## UC-E Kitchen Workflow — Detailed Summary

**Approved Plan:** `docs/plans/UC-E_kitchen_order_ticket_routing_plan.md`  
**Verification Report:** `docs/tests/UC-E_kitchen_workflow_verification_report.md`  
**Deep Verification Script:** `custom_addons/restaurant_kitchen/scripts/verify_uc_e_kitchen_workflow_deep.py`

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Kitchen Preparation Order Base Model | ✅ |
| Step 2 | Kitchen Preparation Order Lines | ✅ |
| Step 3 | Backend UI | ✅ |
| Step 4 | Check Availability Action | ✅ |
| Step 5 | Confirm Order Validation | ✅ |
| Step 6 | Kitchen Ticket Base Models | ✅ |
| Step 7 | Generate Kitchen Tickets from Confirmed Orders | ✅ |
| Step 8 | Kitchen Ticket Workflow | ✅ |
| Step 9 | Final UX Polish & Deep Verification | ✅ |

### Key Models Introduced

| Model | Description |
|---|---|
| `restaurant.kitchen.order` | Kitchen Preparation Order — the operational preparation document |
| `restaurant.kitchen.order.line` | Individual item lines within a preparation order |
| `restaurant.kitchen.ticket` | Station-level kitchen ticket routed from a confirmed order |
| `restaurant.kitchen.ticket.line` | Individual ticket lines linked to order lines |
| `restaurant.kitchen.station` | Kitchen preparation stations (Grill, Prep, Cold, etc.) |
| `restaurant.product.kitchen.station.line` | Station routing assignment per product per company |

### Business Workflow

```
Draft Order
  → Check Availability   (action_check_availability)
  → Confirmed Order      (action_confirm)
  → Generate Tickets     (action_generate_tickets)
  → Tickets: Waiting
      → In Progress      (action_start)
      → Ready            (action_mark_ready)
      OR
      → Cancelled        (action_cancel)
  → Order: in_preparation / ready
```

### Test Results (Deep Verification)

| Test | Scenario | Result |
|---|---|---|
| TEST-01 | Draft Order Creation | ✅ PASS |
| TEST-02 | Availability Check | ✅ PASS |
| TEST-03 | Confirm Validation | ✅ PASS |
| TEST-04 | Generate Tickets | ✅ PASS |
| TEST-05 | Ticket Workflow | ✅ PASS |
| TEST-06 | No-Station Item | ✅ PASS |
| TEST-07 | Duplicate Generation Blocked | ✅ PASS |
| TEST-08 | Unavailable Order Blocked | ✅ PASS |
| TEST-09 | Line Locking | ✅ PASS |
| TEST-10 | Ticket Invalid Transitions | ✅ PASS |
| TEST-11 | Bulk Action No Partial Write | ✅ PASS |
| TEST-12 | Security Behavior | ⚠️ PARTIAL (manual verification deferred) |
| TEST-13 | No Side Effects | ✅ PASS |

---

## UC-G POS Order to Kitchen Integration — Detailed Summary

**Approved Plan:** `docs/plans/UC-G_pos_order_to_kitchen_integration_plan.md`  
**Verification Report:** `docs/tests/UC-G_pos_order_to_kitchen_integration_test_report.md`  

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Architecture Plan | ✅ |
| Step 2 | `restaurant_pos_kitchen` Module Skeleton | ✅ |
| Step 3 | Kitchen Source Support | ✅ |
| Step 4 | POS Config Kitchen Channel/Policy | ✅ |
| Step 4B | POS Order Channel/Policy Snapshot Fields | ✅ |
| Step 5 | POS to Kitchen Creation Helper | ✅ |
| Step 6 | POS Lifecycle Hook Integration | ✅ |
| Step 7 | Final QA / End-to-End Verification Report | ✅ |

### Key Models Extended

| Model | Extension |
|---|---|
| `pos.config` | Added defaults for `restaurant_order_channel` and `kitchen_send_policy`. |
| `pos.order` | Snapshotted configuration fields, added safe backend kitchen creation helper and lifecycle hooks. |
| `restaurant.kitchen.order` | Expanded `source_type` to natively support `pos_order` integration. |

### Test Results

| Test | Scenario | Result |
|---|---|---|
| TEST-01 | Create kitchen order from valid POS order | ✅ PASS |
| TEST-02 | Duplicate prevention across hooks | ✅ PASS |
| TEST-03 | Missing branch handled safely | ✅ PASS |
| TEST-04 | No menu lines prevent creation | ✅ PASS |
| TEST-05 | Negative/refund line ignored | ✅ PASS |
| TEST-06 | Manual policy skips creation | ✅ PASS |
| TEST-07 | Order-level overrides preserved | ✅ PASS |
| TEST-08 | Availability check safe wrapper | ✅ PASS |
| TEST-09 | No financial/stock side effects | ✅ PASS |

---

## UC-H Kitchen Auto Dispatch Policy — Detailed Summary

**Approved Plan:** `docs/plans/UC-H_kitchen_auto_dispatch_policy_plan.md`  
**Verification Report:** `docs/tests/UC-H_auto_dispatch_shell_verification_report.md`  
**Final UI Report:** `docs/tests/UC-H_auto_dispatch_final_report.md`

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Dispatch Policy on `pos.config` | ✅ |
| Step 2 | Dispatch Policy Snapshot on `pos.order` | ✅ |
| Step 3 | Kitchen Auto-Dispatch Eligibility Helper | ✅ |
| Step 4 | Auto-Dispatch Integration with Savepoint | ✅ |
| Step 5 | Deep Shell Verification (17 states) | ✅ |
| Step 6 | JS-RPC Mock Verification (`sync_from_ui`) | ✅ |

### Key Business Workflow

```
POS Order Sync (JS UI)
  → Native PosOrder._process_order hooks
  → KitchenOrder generated in Draft
  → Evaluate Kitchen Dispatch Policy
      → 'manual': Halts in Draft for review
      → 'auto_dispatch': Evaluates Eligibility (Stock, Routing, Schedules)
           → Blocked? Logs warning to chatter, remains Draft.
           → Eligible? Atomic Savepoint triggers confirm & tickets.
```

### Test Results

| Test Suite | Coverage | Result |
|---|---|---|
| Deep Shell Validation | 17 operational rules covering routing & availability | ✅ PASS |
| JS-RPC Mock (V18 `sync_from_ui`) | 5 UI integration behaviors & savepoint reliability | ✅ PASS |

---

## UC-I POS Availability Backend Loader — Detailed Summary

**Approved Plan:** `docs/plans/UC-I_pos_availability_backend_loader_plan.md`  
**Verification Report:** `docs/tests/UC-I_pos_availability_backend_loader_report.md`  

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Inspect & Confirm Odoo 18 POS Loader Hook | ✅ |
| Step 2 | Add Backend Bulk Availability Resolver | ✅ |
| Step 3 | Inject Availability Map into Session Response | ✅ |
| Step 4 | Final Backend Loader QA and Report | ✅ |

### Key Architecture Introduced

- **Hook Interception:** Intercepted the native `pos.session.load_data()` returning pipeline.
- **Bulk Resolver:** Implemented `ProductProduct._get_pos_availability_payload_bulk` to rapidly index all POS products against the branch configuration in a single sequence.
- **Payload Schema:** Injected a localized `_restaurant_availability_map` directly into `response["pos.session"]["data"][0]`, bypassing expensive per-record ORM compute triggers and minimizing JSON expansion.
- **Crash Safeties:** Complete Try/Except wrapping inside `pos.session` combined with per-product exception isolation ensures the POS login process remains 100% immune to custom backend logic crashes.

### Test Results

| Test Suite | Coverage | Result |
|---|---|---|
| Injection QA Matrix | Payload mapping, key alignment, exception trapping, and fallback structural verification (8 points) | ✅ PASS |

---

## UC-J POS UI Badges (Frontend) — Detailed Summary

**Approved Plan:** `docs/plans/UC-J_pos_availability_badges_plan.md`  
**Verification Report:** `docs/tests/UC-J_pos_availability_badges_verification_report.md`  

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Architecture Inspection & Plan | ✅ |
| Step 2 | Add POS Asset Skeleton & Verify Asset Loading | ✅ |
| Step 3 | XML Template Extension | ✅ |
| Step 4 | JS Component Availability Logic | ✅ |
| Step 5 | UI/UX Polish & SCSS | ✅ |
| Step 6 | UI & Payload Deep Verification | ✅ |

### Key Architecture Introduced

- **Component Patching:** Extended Odoo 18's native `ProductCard` component dynamically using `@web/core/utils/patch` to inject reactive getters that consume the `pos.session` availability payload instantaneously without RPC overhead.
- **Safe Template Inheritance:** Inherited `point_of_sale.ProductCard` via XML extension, utilizing a highly defensive `//article` XPath to safely bypass dynamic `t-attf-class` compile-time failures.
- **Non-Blocking UI Design:** Constructed an absolutely positioned `.restaurant-pos-availability-badge` overlay that strictly enforces `pointer-events: none` to guarantee the cashier's touch targets remain fully intact.

### Test Results

| Test Suite | Coverage | Result |
|---|---|---|
| UI Logic Validation | Reason code mapping, fallback evaluations, and click protection | ✅ PASS |
| End-to-End Payload Check | Verified explicit payload extraction handling for active and unmapped states (e.g., `schedule_unavailable`, `not_menu_item`) | ✅ PASS |

---

## UC-K Cancellation & Void Workflows — Detailed Summary

**Approved Plan:** `docs/plans/UC-K_pos_refund_kitchen_cancellation_plan.md`  

### Steps Completed

| Step | Title | Status |
|---|---|---|
| Step 1 | Architecture Inspection & Plan | ✅ |
| Step 2 | Add POS Refund Cancellation / Recall Metadata Fields and Backend Views | ✅ |
| Step 3 | Implement Kitchen Cancellation / Recall Service Helper | ✅ |
| Step 4 | Detect POS Refund Orders and Trigger Safe Kitchen Recall Service | ✅ |

### Key Architecture Introduced

- **Cross-Model Field Filtering:** Dynamically constructed field mappers using `target._fields` dict comprehensions to blindly, yet safely, funnel metadata strings from a POS scope into backend ticket models without crashing.
- **Savepoint Action Wrappers:** Implemented a defensively nested `env.cr.savepoint()` around native `.action_cancel()` triggers. Caught native `Exception` rejections internally so we dynamically downgrade hard-cancellations to soft `recall_required` flags without throwing unhandled exceptions that break offline POS synchronization.
- **Targeted Sudo Queries:** Safely resolved the backend kitchen order targets spanning independent branch boundaries using surgically precise `sudo().search()` wrappers strictly bound to finding the corresponding `source_res_id`.
- **Payload Multi-Origin Filtering:** Extensively mapped `pos.order` refund loops so multi-order refunds structurally decouple their lines and only funnel correctly aligned product queries to specific back-of-house tickets.

### Test Results

| Test Suite | Coverage | Result |
|---|---|---|
| Shell Field Verification | Order filtering, exact `action_cancel()` gate states, duplicate repulsions, missing backend data | ✅ PASS |
| Multi-Refund Boundary | Asserted that overlapping refund lines isolated per target order strictly retained their independent recall notes without mixing quantities. | ✅ PASS |

---

## Known Limitations & Deferred Scope

The following items are **intentionally out of scope** for all currently completed UCs. They are documented here for planning purposes:

| Item | Deferred To |
|---|---|
| `sale.order` integration with Kitchen Orders | Future UC |
| Stock deduction on kitchen confirmation | Future UC |
| Ingredient stock moves from preparation | Future UC |
| Combo component-level kitchen routing | Future UC |
| Custom Kitchen Display Screen (OWL/POS) | Future UC |
| Accounting / Invoice / Payment / Tax integration | Future UC |
| Live stock availability during availability check | Future UC |
| Full multi-user UI security testing | Pre-production manual test |

---

## Planned Future Use Cases

| ID | Title | Depends On | Priority |
|---|---|---|---|
| UC-L | Manual Availability Refresh | UC-I | Medium |
| UC-M | Combo Component Routing | UC-E, UC-07 | Medium |
| UC-N | Stock Deduction from Kitchen Orders | UC-E, UC-11 | Medium |
| UC-O | Custom Kitchen Display Screen (OWL) | UC-H | Low |
| UC-P | Sale Order to Kitchen Order Integration | UC-E | Medium |
| UC-Q | Accounting & Invoice from Kitchen | UC-E | Low |

> **Note:** UC IDs are provisional. Confirm ordering and priority with user before starting each UC.

---

## Technical Learnings Registry

| Area | Key Learning |
|---|---|
| Wizard Actions | Avoid nested `display_notification` + `act_window_close`. Return single action directly. |
| Multi-Company Security | Enforce company scoping in Python logic, not only `ir.rule`. |
| Cross-Compute Dependencies | Avoid `@api.depends` chains within the same model — inline the logic. |
| Deterministic Tie-Breaking | Sort overlapping config rules: `date_from` DESC → `sequence` ASC → `id` DESC. |
| One2many Search Domains | Filter active child records explicitly in custom `search=` methods. |
| ORM Savepoints | Wrap expected-to-fail test writes in `env.cr.savepoint()` blocks in shell tests. |
| Timezone-Aware Datetimes | Normalize psycopg2 timezone-aware datetimes to naive UTC before Odoo field comparisons. |
| Midnight-Crossing Schedules | Use `(weekday - 1) % 7` to correctly attribute early-morning hours to the previous day's schedule. |
| Storable Product (Odoo 18) | Use `is_storable = True` (not `type == 'product'`) to identify stock-tracked items. |
| Multi-Record Workflow Safety | Validate entire recordset before writing — never validate-then-write in the same loop. |
| Tracked Field Assignment | Use `record.write({...})` (not `record.field = value`) when `tracking=True` is set. |
| `allowed_fields` Bypass Pattern | Document the bypass set with an inline comment naming the callers that are permitted to bypass the write guard. |
| State Cascade Helper | Centralize parent state recomputation in a single `_recompute_*_state()` method. |
| No-Station Routing | Skip no-station items silently; mark `routing_status = no_station_required`; auto-ready the order if all items fall into this category. |
| Odoo 18 `sync_from_ui` Payload | Flatten the JSON payload, strip the `data` wrapper, and map legacy properties (`uid` -> `uuid`, `statement_ids` -> `payment_ids`). |
| Atomic Savepoints | Use `env.cr.savepoint()` wrapped in a `try/except` inside integration lifecycle hooks to seamlessly rollback dead/faulty physical integrations (like ticket prints) without breaking offline UI synchronization. |
| Odoo 18 Session Injection | Extend Odoo 18 POS load payloads by intercepting `super().load_data()` on `pos.session` and mutating the returned dictionary map instead of defining ORM computed fields per model. |
| Backend Crash Isolation | When injecting external datasets into critical boot paths (`load_data`), aggressively wrap all operations in `try/except Exception` blocks to guarantee the baseline Odoo dictionary reliably returns to the user regardless of custom backend logic crashes. |
| POS Refund Linkage | In Odoo 18, use `refunded_orderline_id` to reliably trace negative refund lines back to their original sale. |
| Filtered Dict Updates | Filter external metadata keys via `{k: v for k, v in payload.items() if k in target._fields}` to bypass missing-field `ValueError` crashes. |
| Targeted `sudo()` for Reads | Use `sudo().search()` strictly for read queries when bridging external contexts (e.g. cross-branch cashier refunds) to resolve backend tickets natively blocked by standard ACLs. |
| Atomic Action Wrappers | Encapsulate native workflow hooks (`action_cancel()`) inside `env.cr.savepoint()` + `try/except Exception` to prevent internal state validations from rolling back earlier structural metadata commits. |
