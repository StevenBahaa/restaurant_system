# UC-12 Configure Menu Scheduling — Final QA Report

## 2. Environment
- **Odoo version:** 18.0 Community
- **Database name:** restaurant_system
- **Tested module:** restaurant_menu
- **Related modules:**
  - restaurant_base
  - restaurant_recipe
  - restaurant_inventory
  - restaurant_kitchen
  - stock
  - point_of_sale (categories)
- **Upgrade command:**
  `python C:\odoo18\odoo-bin -c C:\odoo18\conf\odoo.conf -d restaurant_system -u restaurant_menu`

## 3. Scope
Validate UC-12 backend/domain behavior including:
1. Schedule days & Schedule rules
2. Branch timezone
3. Product & Category schedule assignments
4. Branch-specific and company-wide schedule lines
5. Shared product support
6. Category parent gate & Product OR logic
7. Timezone conversion, date range, day-of-week, and midnight crossing logic
8. Manual schedule overrides
9. Security & Multi-company isolation
10. Regression against UC-08/UC-09/UC-10/UC-11

## 4. Out-of-Scope Confirmation
- **No** POS/OWL/JS/product loader changes.
- **No** cron or automatic refreshes added.
- **No** order validation implemented.
- **No** stock deduction changes.
- **No** global combined availability resolver created.
- **No** stored runtime availability fields on `product.template`.
- **No** modification of UC-08, UC-09, UC-10, or UC-11 behavior.

## 5. Implemented Components Summary
- **Models Added:**
  - `restaurant.schedule.day`: 7 seed records (Codes 0-6).
  - `restaurant.schedule.rule`: Core rule definitions.
  - `restaurant.product.schedule.line`: Assignment lines for products.
  - `restaurant.category.schedule.line`: Assignment lines for pos.category.
  - `restaurant.schedule.override`: Manual override priority model.
- **Fields Added:**
  - `tz` (timezone) on `restaurant.branch`.
- **Backend Methods Added:**
  - `_get_evaluation_tz`, `_localize_datetime`, `_evaluate_schedule_rule`, `_evaluate_category_schedule`, `_get_active_schedule_override`, `_get_schedule_availability`, `_get_schedule_availability_payload` on `product.template`.
- **Security:**
  - `group_restaurant_operations_manager`: Full CRUD.
  - `base.group_user`: Read-only.
  - Strict multi-company record rules based on `company_id`.

## 6. Test Data Used
- Test company, multi-company environment.
- Multiple branches with different timezones (e.g., Africa/Cairo, UTC).
- Menu items, shared menu items, non-menu products.
- Various schedule rules (Breakfast, Midnight, Date-Only).
- Overlapping and non-overlapping manual schedule overrides.

## 7. Test Summary Table
| Metric | Count |
|--------|-------|
| Total Tests | 58 |
| Passed | 58 |
| Failed | 0 |
| Blocked | 0 |
| Minor Issues | 0 |
| Critical Issues | 0 |

## 8. Detailed Test Cases

### A. Module / Installation / Scope
- **TEST-01 — Module upgrade:** PASS. Upgrade succeeds without XML/Python/ACL errors.
- **TEST-02 — No out-of-scope files:** PASS. Codebase conforms strictly to backend/domain scope.

### B. Schedule Rule Foundation
- **TEST-03 — Schedule days seeded:** PASS. 7 records, codes 0-6.
- **TEST-04 — Basic breakfast schedule rule:** PASS. Evaluates time ranges properly.
- **TEST-05 — Date-only seasonal schedule:** PASS.
- **TEST-06 — Empty unrestricted rule blocked:** PASS. ValidationError enforces at least one restriction.
- **TEST-07 — Invalid time range blocked:** PASS. Start/end bounds checked.
- **TEST-08 — Midnight boundary valid:** PASS. (e.g. 22:00 - 00:00).
- **TEST-09 — Invalid date range blocked:** PASS.

### C. Branch Timezone
- **TEST-10 — Branch timezone exists:** PASS. `tz` field added to branch.
- **TEST-11 — Resolver uses branch timezone first:** PASS. Cascades `branch.tz` -> `branch.company_id...tz` -> `env.user.tz` -> `'UTC'`.

### D. Product Schedule Assignment
- **TEST-12 — Product scheduling tab/assignment exists:** PASS. Menu item can receive schedule lines.
- **TEST-13 — Shared product schedule assignment:** PASS. `product.company_id=False` handles company-scoped lines well.
- **TEST-14 — Company-specific product mismatch blocked:** PASS.
- **TEST-15 — Product branch-specific schedule:** PASS. `branch_id` is optional and properly scoped.
- **TEST-16 — Product branch/company mismatch blocked:** PASS.
- **TEST-17 — Duplicate active product schedule line blocked:** PASS.

### E. Category Schedule Assignment
- **TEST-18 — Category scheduling tab/assignment exists:** PASS. `pos.category` acts as target.
- **TEST-19 — Category branch/company mismatch blocked:** PASS.
- **TEST-20 — Duplicate active category schedule line blocked:** PASS.
- **TEST-21 — Category company isolation:** PASS. Isolation enforced at the assignment line layer.

### F. Schedule Resolver
- **TEST-22 — No schedule means available:** PASS.
- **TEST-23 — Category parent gate blocks product:** PASS. If category schedule exists and doesn't match, product is blocked.
- **TEST-24 — Category passes then product schedule evaluated:** PASS.
- **TEST-25 — Product schedule OR logic:** PASS. Available if any active product rule matches.
- **TEST-26 — Branch-specific line filtering:** PASS. Evaluates global and matching branch lines only.
- **TEST-27 — Archived schedule rules ignored:** PASS.
- **TEST-28 — Archived assignment lines ignored:** PASS.
- **TEST-29 — Date range evaluation:** PASS. Inclusive bounds.
- **TEST-30 — Day-of-week evaluation:** PASS.
- **TEST-31 — Midnight crossing evaluation:** PASS. Handled correctly via previous-day modulo logic.
- **TEST-32 — Timezone conversion:** PASS. `at_datetime` correctly localized.

### G. Manual Schedule Override
- **TEST-33 — Create force available override:** PASS.
- **TEST-34 — Create force unavailable override:** PASS.
- **TEST-35 — Empty reason blocked:** PASS.
- **TEST-36 — Product must be menu item:** PASS.
- **TEST-37 — Branch/company mismatch blocked:** PASS.
- **TEST-38 — Product/company mismatch blocked:** PASS.
- **TEST-39 — Invalid override date range blocked:** PASS.
- **TEST-40 — Overlapping active override blocked:** PASS. Enforced via DB SQL check to bypass ORM cache issues.
- **TEST-41 — Non-overlapping override allowed:** PASS.
- **TEST-42 — Force available override priority:** PASS. Resolver catches priority 1 override, returns available.
- **TEST-43 — Force unavailable override priority:** PASS. Resolver catches priority 1 override, returns unavailable.
- **TEST-44 — Expired override ignored:** PASS.
- **TEST-45 — No branch context ignores override:** PASS.

### H. Security
- **TEST-46 to TEST-51 — Operations Manager vs Normal User:** PASS. `base.group_user` restricted to read-only; `group_restaurant_operations_manager` has full CRUD on rules, lines, and overrides.
- **TEST-52 — Multi-company record rules:** PASS. `company_ids` strictly enforced.

### I. Regression
- **TEST-53 — UC-08 branch availability unchanged:** PASS.
- **TEST-54 — UC-09 branch pricing unchanged:** PASS.
- **TEST-55 — UC-10 kitchen/prep-time unchanged:** PASS.
- **TEST-56 — UC-11 stock availability unchanged:** PASS.
- **TEST-57 — Product form regression:** PASS. All tabs load without XML view errors.
- **TEST-58 — Category form regression:** PASS. All fields load without XML view errors.

## 9. Bugs/Issues Found (and Resolved during Implementation)
1. **Timezone Offset Bug:** `psycopg2` returned timezone-aware datetimes, causing comparison crashes against Odoo's naive UTC format. Resolved by writing a `_naive()` datetime normalizer.
2. **ORM Phantom Records (Midnight Crossing / Overlaps):** Standard `@api.constrains` flushed uncommitted records to the DB mid-transaction, causing overlap constraint logic to trip on itself. Fixed by transitioning the active overlap check to a direct SQL query `self.env.cr.execute(sql, params)`.

## 10. Implementation Review Questions
1. **Does the resolver use branch.tz before user.tz?** Yes, via cascading fallback in `_get_evaluation_tz`.
2. **Does it use rule.day_ids, not raw day strings?** Yes, logic resolves `day_ids.mapped('code')`.
3. **Does midnight crossing use previous-day logic?** Yes, it relies on `(local_dt.weekday() - 1) % 7` when checking a window that crosses midnight.
4. **Does category schedule act as parent gate?** Yes, if the category has rules, the product is blocked unless a category rule passes.
5. **Does product schedule use OR logic?** Yes.
6. **Does branch=None exclude branch-specific lines?** Yes, falling back to global `branch_id=False` lines.
7. **Does shared product scheduling work without forcing product.company_id?** Yes, rules isolate cleanly based on the assignment line company.
8. **Does override apply before category/product schedules?** Yes, it serves as the Priority 1 check in the payload evaluation.
9. **Does override affect only UC-12 schedule layer?** Yes, it operates completely isolated from stock, pricing, and UC-08 availability.
10. **Are archived schedule rules and inactive assignment lines ignored?** Yes, strict `active=True` domains are applied to both.
11. **Are record rules company-safe?** Yes, multi-company isolation is enforced with strict XML `ir.rule` definitions.
12. **Is sudo avoided?** Yes, zero `sudo()` usage in the implementation.

## 11. Final Verdict
**PASSED**

All tests successfully evaluate green across Steps 2-5 implementation scripts and final module integration. The backend properly implements and isolates the UC-12 menu schedule domain logic.

## 12. Recommended Next Step
Proceed to UC-13 (if defined) or mark UC-12 as completely closed for the backend implementation phase. No further work is required in this module for UC-12 backend logic.
