# Restaurant & Cloud Kitchen ERP — Project Rules & Engineering Constitution

## 1. Project Identity

This repository is a Restaurant & Cloud Kitchen ERP built on Odoo 18 Community.

The project targets:
- realistic restaurant operations
- cloud kitchen workflows
- Egyptian market business cases
- scalable ERP-grade architecture
- backend/domain-first implementation
- POS integration later
- acceptance-criteria-driven development

## 2. Technical Environment

- Odoo 18 Community
- Python
- XML
- Odoo ORM
- PostgreSQL through Odoo
- Windows development environment
- No Docker unless explicitly approved later
- Use Windows CMD command style in documentation
- Use Odoo 18 XML syntax
- Use `<list>`, not `<tree>`
- Repository: https://github.com/StevenBahaa/restaurant_system.git

## 3. General Working Method

- Do not write code immediately.
- Analyze the requirement first.
- Explain the business reason before implementation.
- Review each UC from:
  - business perspective
  - ERP perspective
  - Odoo perspective
  - data model perspective
  - security perspective
  - operational perspective
- Implement step by step.
- Never implement a full UC in one large uncontrolled change.
- Each step must be reviewed before moving to the next.

## 4. Scope Control Rules

- Backend/domain configuration comes first.
- POS frontend/code is out of scope unless explicitly approved.
- Kitchen routing is out of scope unless explicitly approved.
- Stock-linked availability is out of scope unless explicitly approved.
- Branch pricing is separate from branch availability.
- Do not mix future integration logic into current backend steps.
- Do not overbuild.
- Do not create models, fields, menus, actions, wizards, reports, or extra security groups unless they are required for the current approved step.
- Avoid shortcuts that will create technical debt.
- Prefer reusable architecture over quick hacks.
- Keep each UC focused on its actual business purpose.
- If a requested feature belongs to a later integration phase, document it as future scope instead of implementing it early.
- Do not implement “nice to have” features unless explicitly approved.
- Do not silently expand the scope of a step.
- If the requirement is ambiguous, stop and ask for clarification before coding.
- If a bug is discovered outside the current scope, document it first and ask before fixing it.

## 5. Architecture Principles

- Use Odoo standard models where they correctly represent the business meaning.
- Create custom models only when Odoo standard models do not express the restaurant business concept clearly.
- Do not duplicate product identity unnecessarily.
- Do not create separate products per branch just to handle availability or pricing.
- Do not mix different business meanings into one model.
- Keep template-level logic on `product.template`.
- Keep variant-level logic on `product.product`.
- Use separate line models for separate business concepts.

Examples of separate business concepts that must remain separate:
- recipe lines
- add-on ingredient lines
- variant recipe override lines
- combo component lines
- branch availability logs
- future branch pricing rules

- Prefer resolver methods for context-dependent logic.
- Avoid stored computed fields when the value depends on branch, date, user, POS session, warehouse, or runtime context.
- Keep backend rules reusable for future POS, kitchen, stock, and reporting integrations.
- Do not hardcode operational decisions if they should be configurable.
- Prefer explicit business fields over unclear generic fields.
- Avoid fragile logic inside views; business rules belong in Python/backend logic.
- Keep `create()` and `write()` methods readable by extracting helper methods when logic grows.
- Avoid creating one large method that mixes validation, security, audit logging, and calculations without helper methods.
- Business logic should be explainable and testable.

## 6. Odoo Coding Rules

- Use the Odoo ORM properly.
- Use Python constraints for business validation.
- Use SQL constraints for database-level uniqueness.
- Use `onchange` for UX cleanup only, not as the source of truth.
- Backend `create`, `write`, and `unlink` enforcement is required for critical business rules.
- UI invisibility is not security.
- XML `groups` are not enough for security.
- Avoid `sudo()` unless there is a clear system-owned reason.
- If `sudo()` is used, document why.
- System-generated audit logs may use `sudo()` if users are not allowed to create logs manually.
- Do not bypass security in business writes.
- Do not use POS code unless explicitly approved.
- Use Odoo 18 view syntax.
- Use `<list>`, not `<tree>`.
- Keep XML inheritance stable and avoid risky XPath expressions when possible.
- When XPath is uncertain, inspect the original Odoo view before modifying.
- Avoid duplicate inherited views that do the same job.
- Avoid adding unnecessary menus/actions.
- Do not create stored computed fields unless there is a clear reporting/search reason.
- Use clear method names that express business meaning.
- Keep validation messages understandable for business users.
- Do not make business logic depend only on frontend behavior.
- Always update `__manifest__.py`, imports, security CSV/XML, and views consistently.
- When adding a new model, include:
  - Python model file
  - import in `models/__init__.py`
  - access rights if needed
  - views if needed
  - manifest references
- When adding a wizard, use `models.TransientModel`.
- When adding security groups, load the security XML before views that reference the groups.
- When extending product behavior, respect existing product classification, recipes, add-ons, variants, combos, and branch availability logic.

## 7. Security Rules

- Security must be enforced in backend methods, not only views.
- Record rules and ACLs should be used where appropriate.
- Business-sensitive changes must be protected in `create`, `write`, and `unlink`.
- Failed `AccessError` operations must not create audit logs.
- Security tests in Odoo shell must avoid superuser false positives.
- Use `env(user=user, su=False)` when testing permission behavior.
- Normal internal users should not get operational manager permissions by default.
- Branch managers should only manage their assigned branch scope.
- Operations managers may manage all branch-level configuration when explicitly designed.
- Do not use `sudo()` for product/business writes unless explicitly approved.
- If a wizard performs business writes, it should normally call the target model without `sudo()` so existing security remains the source of truth.
- Menu visibility is not enough; direct backend access must also be blocked.
- Log models may be read-only for users while allowing system-created logs through controlled backend logic.
- When creating new security groups, avoid duplicates if equivalent groups already exist.
- Security XML must be loaded before views that reference its groups.
- Security rules must be tested using dedicated users, not only administrator users.
- A successful security implementation must verify both allowed and blocked scenarios.
- Failed blocked writes should not leave partial data or misleading audit logs.

## 8. Audit / Logging Rules

- Important operational changes should be auditable.
- Audit logs should capture:
  - changed user
  - changed datetime
  - old values
  - new values
  - readable summary
- Logs should not be created for unrelated writes.
- Logs should not be created when final values are identical to old values.
- Logs should usually be readonly to users.
- System can create logs programmatically.
- Audit log creation should not break legitimate user actions.
- Capture old values before the write.
- Capture new values after final cleanup/write.
- Create logs only when effective final values differ from old values.
- Use readable labels and names in logs where possible.
- Keep audit summaries concise and understandable.
- Avoid noisy logs that reduce audit value.
- If a log is created through `sudo()`, the reason must be that users are not allowed to manually create audit records.
- Audit logs should not be used as the main business state.
- Audit logs should reflect changes; they should not drive operational behavior.
- Do not create logs for failed validations or failed access checks.

## 9. Product Modeling Philosophy

Prepared meals:
- are consumable menu items
- are sold in POS later
- are not stock-tracked as finished goods
- consume stock-tracked ingredients through recipes

Ingredients:
- are storable
- are purchased
- are inventory tracked
- are not sold by default

Packaging:
- is inventory tracked when needed
- may be consumed by orders later
- should not be mixed with menu item logic

Semi-finished items:
- can represent intermediate preparation
- may be used inside recipes
- should not be confused with final menu items

Ready items:
- may be purchased and sold
- may have `standard_price`
- may optionally have approved recipe costing if internally portioned or prepared

Combo meals:
- are `product.template` records with `restaurant_product_type = combo`
- are not separate product identity models
- combo structure belongs in a separate component line model
- combo pricing and cost calculations should be resolved from components
- combo POS behavior is future integration unless explicitly approved

General product philosophy:
- Do not duplicate the same product for every branch.
- Do not duplicate the same product for every price scenario.
- Product identity should remain stable.
- Operational differences should be modeled with rules, lines, or configuration layers.
- `product.template` is the correct place for template-level restaurant rules.
- `product.product` is the correct place for variant-specific rules.
- Do not confuse menu availability, pricing, stock availability, kitchen routing, and POS display; these are different business concerns.

## 10. Costing Rules

- Approved recipe cost has priority over product `standard_price`.
- If an approved recipe exists for a product, use `recipe.recipe_cost`.
- If no approved recipe exists, fallback to product `standard_price`.
- Ready items may still use approved recipe cost if they have approved recipes.
- Cost warning is a soft guardrail, not a blocking validation, unless explicitly approved otherwise.
- Do not add margin/profit fields unless explicitly requested and approved.
- Cost calculations should be explainable and traceable.
- Wastage must be considered where the recipe logic supports it.
- Combo cost should be calculated from component costs.
- Add-on cost should be calculated separately from product list price.
- Additional add-on price is contextual and should not overwrite the product’s normal `list_price`.
- Costing should not depend on POS code.
- Cost resolver logic should be reusable by future reports and POS integrations.
- Cost calculations should not silently ignore missing configuration.
- If a cost is estimated or fallback-based, the logic should be clear in code and tests.

## 11. Branch Rules

- `restaurant.branch` is the business branch/location entity.
- A branch is not necessarily the same as:
  - company
  - warehouse
  - POS config
- Current design uses one primary warehouse per branch.
- Do not overbuild multiple warehouses per branch unless a future UC requires it.
- Branch availability answers: “Can this product be offered in this branch?”
- Branch pricing answers: “What price should this product have in this branch?”
- These are separate business concerns and should not be mixed.
- Branch availability should not duplicate products.
- Branch pricing should not duplicate products.
- Branch rules should be backend/domain first.
- POS should consume branch rules later, not define them.
- Branch managers should only manage rules related to their assigned branches.
- Operations managers can manage all branch-level configuration when the UC requires it.
- Branch/date-specific values should usually be resolved by methods, not stored globally.
- Branch rule changes should be auditable when operationally important.
- Availability, pricing, stock, schedule, and kitchen routing should remain separate layers.
- Do not use branch availability rules to represent price differences.
- Do not use branch pricing rules to represent stock unavailability.

## 12. Testing Rules

- Every implementation step should have manual or scripted verification.
- Every completed UC must have a final QA report.
- QA reports should be stored under:
  `docs/tests/`
- Test reports should include:
  - environment
  - scope
  - test data
  - test summary table
  - detailed test cases
  - bugs found
  - final verdict
- Do not mark a UC complete unless critical tests pass.
- Critical areas include:
  - validation
  - security
  - resolver logic
  - audit logging
  - regression against previous UCs
  - module upgrade
- Automated/scripted tests should not replace manual UI checks where UI behavior matters.
- Manual tests should be written clearly enough for another tester to reproduce.
- For security tests, avoid superuser false positives.
- For Odoo shell security tests, use `env(user=user, su=False)`.
- Failed access/security operations should be verified to not create audit logs.
- Regression tests must include previous completed features when the current UC touches shared views/models.
- Module upgrade must be tested after changes.
- XML parse errors, missing imports, missing ACLs, and broken views must block UC closure.
- Do not mark a UC as passed if critical security or validation tests fail.

## 13. Manual Test Style

Each manual test should include:
- Test ID
- Scenario
- Preconditions
- Steps
- Expected Result
- Actual Result
- Status
- Notes

Final verdict should be one of:
- PASSED
- PASSED WITH MINOR ISSUES
- FAILED

Manual test cases should be grouped by area, for example:
- data model
- validation
- resolver
- security
- audit logs
- UX
- regression

Manual test language should be clear and business-readable.
Do not write vague test cases such as “check it works.”
Always define the expected result.
When a test fails, document:
- exact steps to reproduce
- expected behavior
- actual behavior
- suspected file/model/view
- recommended fix direction

## 14. Command Conventions

Use Windows CMD command style when documenting commands.

Common module upgrade commands:
```cmd
python odoo-bin -c conf\odoo.conf -d restaurant_system -u restaurant_menu
```

## 15. Agent Workflow Rules

- Agents should not implement broad UCs without step approval.
- Agents should receive one step prompt at a time.
- Agents must stop after the requested step.
- Agents must provide:
  - files changed
  - models changed
  - views changed
  - security changes
  - tests run
  - issues found
- Agents must not silently fix bugs outside scope.
- If a bug is discovered, document it first and ask for approval before fixing unless the user explicitly asks to fix it.
- Agents must not add POS, stock, pricing, kitchen, reporting, or integration features unless the current step explicitly asks for them.
- Agents must not continue to the next step automatically.
- Agents must not create extra models, menus, actions, or wizards unless requested in the step.
- Agents must respect Odoo 18 syntax.
- Agents must use `<list>`, not `<tree>`.
- Agents must avoid overbuilding.
- Agents must preserve previous UC behavior.
- Agents must run or describe verification after each implementation.
- Agents must create final QA reports at the end of each UC when requested.
- Agents should read `docs/PROJECT_RULES.md` before starting new work.
- Agents should confirm scope before coding when the requirement is ambiguous.
- Agents should not treat future integration requirements as current implementation scope.
- Agents should not use `sudo()` to bypass security unless explicitly approved or clearly justified for system-owned actions such as audit log creation.
- Agents should document any assumptions they make.
- Agents should keep implementation aligned with the approved design and acceptance criteria.
- Agents must not create implementation plans or test files unless explicitly told to do so by the user.
- Agents may create an implementation plan without being requested only if they do not understand the user's prompt or requirements and need to clarify the scope before writing code.

### 15.1 Odoo MCP Server Runtime Inspection Rules

1. The configured MCP server is:
   odoo-restaurant

2. The MCP server is connected to:
   Odoo URL: http://localhost:8070
   Database: restaurant_system

3. The Odoo server must be started using the restaurant-specific config that includes:
   dbfilter = ^restaurant_system$

4. MCP is allowed only for safe runtime inspection unless I explicitly approve otherwise.

5. MCP default mode is read-only.

6. The agent must not:
   - create records through MCP
   - update records through MCP
   - delete records through MCP
   - call destructive model methods
   - modify accounting records
   - modify stock valuation records
   - modify POS orders
   - modify users
   - modify access rights
   - modify security rules
   - expose or print the API key
   - use YOLO mode
   - bypass the MCP whitelist using /xmlrpc/2/common

7. Before using MCP, the agent must verify the connection by listing MCP-enabled models.

8. The expected MCP-enabled models should be limited to the configured whitelist, including models such as:
   - product.template
   - product.product
   - stock.warehouse
   - restaurant.branch
   - restaurant.recipe
   - restaurant.recipe.line
   - restaurant.addon.group
   - restaurant.addon.item
   - restaurant.addon.item.ingredient
   - restaurant.product.addon.group
   - restaurant.combo.line
   - restaurant.kitchen.station
   - restaurant.product.kitchen.station.line
   - restaurant.branch.price.line
   - restaurant.branch.stock.override
   - restaurant.branch.price.history
   - restaurant.branch.availability.log
   - restaurant.variant.recipe.line

9. If MCP returns hundreds of Odoo models, this means the agent bypassed the MCP whitelist incorrectly. The agent must stop and report the problem.

10. If MCP is unavailable, the agent must stop and report the issue. It must not silently fall back to standard Odoo XML-RPC.

11. MCP should be used only to inspect live/runtime data, such as:
   - checking configured products
   - checking restaurant recipes
   - checking branch records
   - checking kitchen station assignments
   - checking combo lines
   - checking add-on groups and items
   - validating runtime data before or after manual tests

12. Code analysis and implementation must still follow:
   - PROJECT_RULES.md
   - the local Odoo Development Skill
   - Odoo 18 backend-first architecture
   - acceptance-criteria-driven workflow

13. MCP does not replace code review, manual tests, or upgrade tests.

## 16. Completed Backend Foundation Summary

The following backend/domain areas have been completed:
- Product classification
- Recipe management
- Add-ons
- Variant recipe overrides
- UC-07 Combo Meals
- UC-08 Branch-Specific Availability
- UC-09 Branch-Specific Pricing
- UC-10 Define Preparation Time & Kitchen Station
- UC-11 Control Stock-Linked Availability

## 17. Technical Learnings (UC-08 & UC-09)

- **Wizard Actions**: Avoid using `display_notification` with a nested `next` action (e.g., `act_window_close`). It is unreliable in Odoo 18 Community. Instead, return standard actions like `{"type": "ir.actions.act_window_close"}` directly.
- **Multi-Company Security**: Do not rely purely on `ir.rule`. Explicitly enforce company scoping in Python logic using `user.company_ids` or `env.companies` where appropriate.
- **Cross-Compute Dependencies**: Avoid putting computed fields inside the `@api.depends` of another computed field within the same model if possible, to prevent cache invalidation/double-compute issues. Inline the logic if safe.
- **Deterministic Tie-Breaking**: When resolving overlapping configuration rules (e.g., pricing, availability), enforce strict deterministic sorting: `date_from` (descending) -> `sequence` (ascending) -> `id` (descending).
- **Search Domains on One2many**: If adding a custom `search=` method for a boolean computed field that looks across a `One2many` relation, always explicitly filter for active child records (e.g., `[('line_ids.active', '=', True)]`).
- **Complex Subqueries**: For search methods that require evaluating dates or complex states on child records (e.g., `date_from > today`), use a safe subquery (`self.env[...].search(...)` and return `[('id', 'in', ...)]`) rather than chaining dot-notation in a single domain, which can cause cross-record ORM bugs.

## 18. Current Next Direction

Next planned UC:
UC-12

Purpose:
[To be defined by user in next prompt]

Expected future direction:
- POS integrations
- Kitchen routing workflows
- Customer ordering UI
