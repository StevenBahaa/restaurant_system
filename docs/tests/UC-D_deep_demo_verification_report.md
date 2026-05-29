# UC-D Deep Demo Data Verification Report

## Executive Summary
**Overall Status:** FAIL (4 Non-Critical Data Inconsistencies found)

A deep technical verification was conducted on the `restaurant_system_demo` database to ensure consistency of Company/Branch structures, Users, Product Classifications, Recipes, Combos, Add-ons, Kitchen Stations, Scheduling, Pricing, and the Unified Availability Resolver payload. 

Out of 167 automated checks, **163 Passed**, **0 Warnings**, and **4 Failed**. The only failures identified are related to product classification for direct-sale stock items.

## 1. Summary Result: FAIL (Minor Inconsistencies)
The verification script completed with 4 failures. All failures are related to product types for direct-sale items being set to `consu` (Consumable) instead of `product` (Storable), meaning stock tracking cannot be properly maintained for these items.

## 2. Tests Performed
The script `scripts/verify_uc_d_demo_deep.py` ran comprehensive tests across:
- **A. Company / Branch / Warehouse Integrity:** Validated relationships, activity, and warehouse allocations.
- **B. Demo Users / Security Groups:** Verified Demo Managers and proper ACL group assignments.
- **C. Product Classification Integrity:** Checked menu items, ingredients, packagings, and direct-sale items against expected `is_menu_item`, `purchase_ok`, `sale_ok`, and `type` flags.
- **D. Recipe Integrity:** Confirmed recipes exist for all relevant products, have lines, and cost computation completes.
- **E. Add-ons Integrity:** Verified groups, items, and demo product assignments.
- **F. Combo Integrity:** Validated combo product setup and component presence.
- **G. Kitchen Station Integrity:** Verified existence of prep, bar, and packaging stations.
- **H & I. Branch Availability / Pricing:** Checked rule creation and branch constraints.
- **J. Stock Integrity:** Validated initial stock allocations and intended shortages (Maadi Chicken Breast, Asyut Beef Patty).
- **K. Menu Scheduling Integrity:** Validated schedule rule assignments.
- **L. Unified Availability Resolver:** Simulated a request payload for `[DEMO] Classic Beef Burger` at Nasr City to ensure it returns the expected `is_available` flag.
- **M. Dashboard Wizard Integrity:** Verified the wizard model existence.

*Note: No POS frontend behaviors were tested or claimed as part of this backend verification.*

## 3. ORM Checks
All ORM operations succeeded. `ProductTemplate._get_unified_availability_payload` was executed directly via the Odoo Environment and successfully simulated an availability request without errors. Models correctly enforced multi-company filtering.

## 4. SQL Checks
A raw SQL validation was run to verify that no duplicate demo products exist in the database (since product names are translated `JSONB` fields, they were cast to text). 
- **Result:** PASS (No duplicate `[DEMO]%` records found).

## 5. Resolver Checks
The availability resolver successfully evaluated the product, branch, and simulated datetime inputs, demonstrating that the layered architecture is functional for real-time branch availability queries.

## 6. Failed Records
The following items failed their check because they are expected to be stock-tracked (direct-sale items) but are currently configured as Consumables (`type != 'product'`):
- `[DEMO] Cola Can`
- `[DEMO] Bottled Water`
- `[DEMO] Chocolate Brownie`
- `[DEMO] Packaged Chips`

## 7. Recommended Fixes
**Manual Fix or Script Update:**
Change the Product Type (`type`) of the four items listed above from `consu` (Consumable) to `product` (Storable Product). 
This will allow Odoo to accurately track stock quants for these items across the different branch locations, aligning them with the stock shortages tests and expected Cloud Kitchen behaviors.

## Conclusion
Since the failures are minor data adjustments rather than code logic bugs, the UC-D environment is **nearly demo-ready**. Once the 4 direct-sale items are updated to `product`, the system will pass 100% of the verification checks.
