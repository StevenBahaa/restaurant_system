from odoo.exceptions import ValidationError
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_menu_item = fields.Boolean(
        string='Is Menu Item',
        default=False,
        help="Enable this option when the product is sold as a restaurant menu item.",
    )

    arabic_name = fields.Char(
        string='Arabic Name',
        help="Arabic display name used for Arabic receipts, local UI, and restaurant operations.",
    )

    branch_availability_mode = fields.Selection(
        [
            ("all_branches", "All Branches"),
            ("selected_branches", "Selected Branches Only"),
            ("excluded_branches", "All Branches Except Excluded"),
        ],
        string="Branch Availability Mode",
        default="all_branches",
        required=True,
        tracking=True,
    )
    branch_available_ids = fields.Many2many(
        "restaurant.branch",
        "restaurant_product_branch_available_rel",
        "product_tmpl_id",
        "branch_id",
        string="Available Branches",
    )
    branch_excluded_ids = fields.Many2many(
        "restaurant.branch",
        "restaurant_product_branch_excluded_rel",
        "product_tmpl_id",
        "branch_id",
        string="Excluded Branches",
    )
    branch_available_from = fields.Date(
        string="Available From",
        tracking=True,
    )
    branch_available_until = fields.Date(
        string="Available Until",
        tracking=True,
    )
    branch_unavailable_reason = fields.Text(
        string="Branch Availability Status Reason",
        tracking=True,
    )
    branch_availability_last_changed_by = fields.Many2one(
        "res.users",
        string="Availability Last Changed By",
        readonly=True,
    )
    branch_availability_last_changed_on = fields.Datetime(
        string="Availability Last Changed On",
        readonly=True,
    )
    branch_availability_log_ids = fields.One2many(
        "restaurant.branch.availability.log",
        "product_tmpl_id",
        string="Branch Availability Logs",
        readonly=True,
    )

    branch_availability_summary = fields.Char(
        string="Branch Availability Summary",
        compute="_compute_branch_availability_summary",
    )
    branch_availability_has_restriction = fields.Boolean(
        string="Branch Availability Has Restriction",
        compute="_compute_branch_availability_has_restriction",
    )
    branch_availability_date_summary = fields.Char(
        string="Branch Availability Date Summary",
        compute="_compute_branch_availability_date_summary",
    )


    restaurant_product_type = fields.Selection(
        [
            ("prepared_meal", "Prepared Meal"),
            ("combo", "Combo Meal"),
            ("beverage", "Beverage"),
            ("ready_item", "Ready Item"),
            ("ingredient", "Ingredient"),
            ("packaging", "Packaging Item"),
            ("semi_finished", "Semi-Finished"),
        ],
        string="Restaurant Product Type",
        default="prepared_meal",
        help="Operational restaurant classification used for menu, kitchen, recipe, inventory, and reporting workflows.",
    )

    product_addon_group_ids = fields.One2many(
        comodel_name="restaurant.product.addon.group",
        inverse_name="product_tmpl_id",
        string="Add-on Groups",
    )   

    combo_component_line_ids = fields.One2many(
        "restaurant.combo.line",
        "combo_product_tmpl_id",
        string="Combo Components",
        tracking=True,
    )

    combo_component_count = fields.Integer(
        string="Combo Component Count",
        compute="_compute_combo_totals",
        store=True, 
        tracking=True,
    )

    combo_individual_total_price = fields.Float(
        string="Individual Components Total",
        compute="_compute_combo_totals",
        store=True,
        tracking=True,
    )

    combo_saving_amount = fields.Float(
        string="Combo Saving",
        compute="_compute_combo_totals",
        store=True,
        tracking=True,
    )

    combo_is_valid = fields.Boolean(
        string="Combo Is Valid",
        compute="_compute_combo_validation",
        store=True,
        tracking=True,
    )

    combo_validation_message = fields.Char(
        string="Combo Validity Message",
        compute="_compute_combo_validation",
        store=True,
    )

    combo_is_available = fields.Boolean(
        string="Combo Available",
        compute="_compute_combo_availability",
        store=True,
    )

    combo_unavailable_reason = fields.Text(
        string="Combo Unavailable Reason",
        compute="_compute_combo_availability",
        store=True,
    )

    combo_total_cost = fields.Float(
        string="Combo Total Cost",
        compute="_compute_combo_cost",
        store=True,
    )

    combo_food_cost_percentage = fields.Float(
        string="Combo Food Cost %",
        compute="_compute_combo_cost",
        store=True,
    )

    combo_cost_warning = fields.Boolean(
        string="Combo Cost Warning",
        compute="_compute_combo_cost_warning",
        store=True,
    )

    combo_cost_warning_message = fields.Text(
        string="Combo Cost Warning Message",
        compute="_compute_combo_cost_warning",
        store=True,
    )

    @api.depends(
        "restaurant_product_type",
        "combo_total_cost",
        "combo_food_cost_percentage",
        "list_price",
    )
    def _compute_combo_cost_warning(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_cost_warning = False
                product.combo_cost_warning_message = False
            else:
                if product.combo_food_cost_percentage > 60.0:
                    product.combo_cost_warning = True
                    product.combo_cost_warning_message = "Combo food cost percentage is high. Review the combo price or component costs."
                else:
                    product.combo_cost_warning = False
                    product.combo_cost_warning_message = False


    @api.depends(
        "restaurant_product_type",
        "list_price",
        "combo_component_line_ids",
        "combo_component_line_ids.quantity",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.standard_price",
    )
    def _compute_combo_cost(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_total_cost = 0.0
                product.combo_food_cost_percentage = 0.0
                continue

            total_cost = 0.0

            for line in product.combo_component_line_ids:
                component_cost = product._get_combo_component_resolved_cost(
                    line.component_product_tmpl_id
                )
                total_cost += component_cost * line.quantity

            product.combo_total_cost = total_cost

            if product.list_price > 0:
                product.combo_food_cost_percentage = (total_cost / product.list_price) * 100
            else:
                product.combo_food_cost_percentage = 0.0
    

    def _get_combo_component_resolved_cost(self, component_product):
        self.ensure_one()
        if not component_product:
            return 0.0
        return component_product.standard_price
    @api.depends(
        "restaurant_product_type",
        "combo_is_valid",
        "combo_validation_message",
        "combo_component_line_ids",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.active",
        "combo_component_line_ids.component_product_tmpl_id.sale_ok",
    )
    def _compute_combo_availability(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_is_available = True
                product.combo_unavailable_reason = False
                continue

            availability = product._get_combo_availability_status()

            product.combo_is_available = availability["available"]
            product.combo_unavailable_reason = availability["reason"]

    @api.depends(
        "restaurant_product_type",
        "sale_ok",
        "active",
        "list_price",
        "combo_component_line_ids",
        "combo_component_line_ids.component_product_tmpl_id",
        "combo_component_line_ids.component_product_tmpl_id.active",
        "combo_component_line_ids.component_product_tmpl_id.is_menu_item",
        "combo_component_line_ids.component_product_tmpl_id.restaurant_product_type",
        "combo_component_line_ids.quantity",
    )
    def _compute_combo_validation(self):
        allowed_types = {"prepared_meal", "beverage", "ready_item"}

        for product in self :
            message=[]

            if product.restaurant_product_type != "combo":
                product.combo_is_valid = True
                product.combo_validation_message = False
                continue

            if product.list_price <=0:
                message.append("Combo price must be greater than zero.")
            
            if not product.sale_ok:
                message.append("Combo must be sellable.")
            
            if len(product.combo_component_line_ids) <2:
                message.append("Combo must contain at least 2 components.")

            for line in product.combo_component_line_ids:
                component= line.component_product_tmpl_id

                if not component:
                    message.append("Each combo line must have a component product.")
                    continue

                if not component.active:
                    message.append(f"Component '{component.display_name}' is archived.")
                
                if not component.is_menu_item:
                    message.append(f"Component '{component.display_name}' must be a menu item.")

                if component.restaurant_product_type not in allowed_types:
                    message.append(
                        f"Component '{component.display_name}' has invalid restaurant product type."
                    )   
                
                if line.quantity <= 0:
                    message.append(f"Component '{component.display_name}' quantity must be greater than zero.")

            product.combo_is_valid = not bool(message)
            product.combo_validation_message = "\n".join(message) if message else False
            
                
                

            

    @api.onchange("restaurant_product_type")
    def _onchange_restaurant_product_type(self):
        for product in self:
            if product.restaurant_product_type == "prepared_meal":
                product.sale_ok = True
                product.purchase_ok = False
                product.available_in_pos = True
                product.is_menu_item = True
                product.is_storable = False

            elif product.restaurant_product_type == "ingredient":
                product.sale_ok = False
                product.purchase_ok = True
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "packaging":
                product.sale_ok = False
                product.purchase_ok = True
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "semi_finished":
                product.sale_ok = False
                product.purchase_ok = False
                product.available_in_pos = False
                product.is_menu_item = False
                product.is_storable = True

            elif product.restaurant_product_type == "beverage":
                product.sale_ok = True
                product.purchase_ok = True
                product.available_in_pos = True
                product.is_menu_item = True

            elif product.restaurant_product_type == "ready_item":
                product.sale_ok = True
                product.purchase_ok = True
                product.available_in_pos = True
                product.is_menu_item = True
    
    @api.depends(
        "restaurant_product_type",
        "list_price",
        "combo_component_line_ids",
        "combo_component_line_ids.quantity",
        "combo_component_line_ids.component_product_tmpl_id.list_price",
    )
    def _compute_combo_totals(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                product.combo_component_count = 0
                product.combo_individual_total_price = 0.0
                product.combo_saving_amount = 0.0
                continue

            total = 0.0
            count = 0

            for line in product.combo_component_line_ids:
                count += 1
                total += line.component_product_tmpl_id.list_price * line.quantity

            product.combo_component_count = count
            product.combo_individual_total_price = total
            product.combo_saving_amount = total - product.list_price

    
    @api.constrains("restaurant_product_type", "list_price")
    def _check_combo_price_positive(self):
        for product in self:
            if product.restaurant_product_type == "combo" and product.list_price <= 0:
                raise ValidationError("Combo price must be greater than zero.")

    @api.onchange('branch_availability_mode')
    def _onchange_branch_availability_mode(self):
        if self.branch_availability_mode == 'all_branches':
            self.branch_available_ids = [(5, 0, 0)]
            self.branch_excluded_ids = [(5, 0, 0)]
        elif self.branch_availability_mode == 'selected_branches':
            self.branch_excluded_ids = [(5, 0, 0)]
        elif self.branch_availability_mode == 'excluded_branches':
            self.branch_available_ids = [(5, 0, 0)]

    @api.constrains('branch_available_from', 'branch_available_until')
    def _check_branch_availability_from_until(self):
        for product in self:
            if product.branch_available_from and product.branch_available_until:
                if product.branch_available_from > product.branch_available_until:
                    raise ValidationError("Available From date must be before or equal to Available Until date.")

    @api.constrains('branch_availability_mode', 'branch_available_ids', 'branch_excluded_ids')
    def _check_branch_availability_requirements(self):
        for product in self:
            if product.branch_availability_mode == 'selected_branches' and not product.branch_available_ids:
                raise ValidationError("At least one branch must be selected for 'Selected Branches Only' availability mode.")
            if product.branch_availability_mode == 'excluded_branches' and not product.branch_excluded_ids:
                raise ValidationError("At least one branch must be excluded for 'All Branches Except Excluded' availability mode.")

    @api.constrains('branch_available_ids', 'branch_excluded_ids')
    def _check_branch_availability_no_overlap(self):
        for product in self:
            overlap = set(product.branch_available_ids.ids) & set(product.branch_excluded_ids.ids)
            if overlap:
                raise ValidationError("Available and Excluded branches must not overlap.")

    @api.constrains('branch_available_ids', 'branch_excluded_ids')
    def _check_branch_active_only(self):
        for product in self.with_context(active_test=False):
            if any(not b.active for b in product.branch_available_ids):
                raise ValidationError("Archived branches cannot be used as available branches.")
            if any(not b.active for b in product.branch_excluded_ids):
                raise ValidationError("Archived branches cannot be used as excluded branches.")

    @api.constrains('company_id', 'branch_available_ids', 'branch_excluded_ids')
    def _check_branch_company_consistency(self):
        for product in self.with_context(active_test=False):
            if product.company_id:
                for branch in product.branch_available_ids:
                    if branch.company_id != product.company_id:
                        raise ValidationError("Branch availability branches must belong to the same company as the product.")
                for branch in product.branch_excluded_ids:
                    if branch.company_id != product.company_id:
                        raise ValidationError("Branch availability branches must belong to the same company as the product.")

    def _check_combo_operational_validity(self):
        for product in self:
            if product.restaurant_product_type != "combo":
                continue

            product._compute_combo_validation()

            if not product.combo_is_valid:
                raise ValidationError(
                    product.combo_validation_message or "Combo meal is not operationally valid."
                )

        return True

    def _get_branch_availability_fields(self):
        return {
            "branch_availability_mode",
            "branch_available_ids",
            "branch_excluded_ids",
            "branch_available_from",
            "branch_available_until",
            "branch_unavailable_reason",
        }

    def _user_can_manage_all_branch_availability(self):
        return self.env.user.has_group("restaurant_base.group_restaurant_operations_manager") or self.env.su

    def _get_user_managed_branches(self):
        return self.env["restaurant.branch"].search([("manager_user_ids", "in", self.env.user.id)])

    def _extract_affected_branch_ids(self, command_list):
        if not command_list:
            return set()
        branch_ids = set()
        for command in command_list:
            if command[0] in (4, 6):
                if command[0] == 6:
                    branch_ids.update(command[2])
                else:
                    branch_ids.add(command[1])
            elif command[0] == 3:
                branch_ids.add(command[1])
        return branch_ids

    def _check_user_can_modify_branch_availability(self, vals, is_create=False):
        availability_fields = self._get_branch_availability_fields()
        if not any(f in vals for f in availability_fields):
            return

        if self._user_can_manage_all_branch_availability():
            return

        is_branch_manager = self.env.user.has_group("restaurant_base.group_restaurant_branch_manager")
        if not is_branch_manager:
            raise ValidationError("You do not have permission to modify branch availability.")

        managed_branches = self._get_user_managed_branches()

        if is_create:
            mode = vals.get("branch_availability_mode", "all_branches")
            if mode == "all_branches":
                raise ValidationError("Branch Managers cannot use 'All Branches' mode.")
            
            new_available_ids = self._extract_affected_branch_ids(vals.get("branch_available_ids", []))
            new_excluded_ids = self._extract_affected_branch_ids(vals.get("branch_excluded_ids", []))
            
            affected_branches = self.env["restaurant.branch"].browse(list(new_available_ids | new_excluded_ids))
            unmanaged = affected_branches - managed_branches
            if unmanaged:
                raise ValidationError(f"You can only modify availability for branches you manage. Unmanaged: {', '.join(unmanaged.mapped('name'))}")
        else:
            for record in self:
                mode = vals.get("branch_availability_mode", record.branch_availability_mode)
                if mode == "all_branches":
                    raise ValidationError("Branch Managers cannot use 'All Branches' mode.")

                affected_branches = self.env["restaurant.branch"].browse()
                affected_branches |= record.branch_available_ids
                affected_branches |= record.branch_excluded_ids

                new_available_ids = self._extract_affected_branch_ids(vals.get("branch_available_ids", []))
                new_excluded_ids = self._extract_affected_branch_ids(vals.get("branch_excluded_ids", []))

                affected_branches |= self.env["restaurant.branch"].browse(list(new_available_ids | new_excluded_ids))

                unmanaged = affected_branches - managed_branches
                if unmanaged:
                    raise ValidationError(f"You can only modify availability for branches you manage. Unmanaged: {', '.join(unmanaged.mapped('name'))}")

    def write(self, vals):
        self._check_user_can_modify_branch_availability(vals, is_create=False)

        availability_fields = self._get_branch_availability_fields()

        has_availability_changes = any(f in vals for f in availability_fields)
        
        old_snapshots = {}
        if has_availability_changes:
            vals["branch_availability_last_changed_by"] = self.env.user.id
            vals["branch_availability_last_changed_on"] = fields.Datetime.now()
            for record in self:
                old_snapshots[record.id] = record._get_availability_snapshot()

        res = super().write(vals)

        if has_availability_changes:
            for record in self:
                clean_vals = {}
                if record.branch_availability_mode == "all_branches":
                    if record.branch_available_ids:
                        clean_vals["branch_available_ids"] = [(5, 0, 0)]
                    if record.branch_excluded_ids:
                        clean_vals["branch_excluded_ids"] = [(5, 0, 0)]
                elif record.branch_availability_mode == "selected_branches":
                    if record.branch_excluded_ids:
                        clean_vals["branch_excluded_ids"] = [(5, 0, 0)]
                elif record.branch_availability_mode == "excluded_branches":
                    if record.branch_available_ids:
                        clean_vals["branch_available_ids"] = [(5, 0, 0)]

                if clean_vals:
                    super(ProductTemplate, record).write(clean_vals)

            for record in self:
                old_snap = old_snapshots.get(record.id)
                if old_snap:
                    new_snap = record._get_availability_snapshot()
                    record._create_availability_log(old_snap, new_snap)

        validation_trigger_fields = {
            "active",
            "sale_ok",
            "list_price",
            "restaurant_product_type",
            "combo_component_line_ids",
        }

        protected_combo_fields = {
            "restaurant_product_type",
            "combo_component_line_ids",
        }

        for product in self:
            if product.restaurant_product_type == "combo":
                if protected_combo_fields.intersection(vals.keys()):
                    if product._is_combo_operationally_used():
                        raise ValidationError(
                            "You cannot modify combo structure after operational usage."
                        )

                if product.active and validation_trigger_fields.intersection(vals.keys()):
                    product._check_combo_operational_validity()

        return res


    @api.model_create_multi
    def create(self, vals_list):
        availability_fields = self._get_branch_availability_fields()

        for vals in vals_list:
            self._check_user_can_modify_branch_availability(vals, is_create=True)
            mode = vals.get("branch_availability_mode", "all_branches")
            if mode == "all_branches":
                vals["branch_available_ids"] = [(5, 0, 0)]
                vals["branch_excluded_ids"] = [(5, 0, 0)]
            elif mode == "selected_branches":
                vals["branch_excluded_ids"] = [(5, 0, 0)]
            elif mode == "excluded_branches":
                vals["branch_available_ids"] = [(5, 0, 0)]

            if any(f in vals for f in availability_fields):
                vals["branch_availability_last_changed_by"] = self.env.user.id
                vals["branch_availability_last_changed_on"] = fields.Datetime.now()

        products = super().create(vals_list)

        for product in products:
            if product.restaurant_product_type == "combo" and product.active:
                product._check_combo_operational_validity()

        return products

    
    def _is_combo_operationally_used(self):
        self.ensure_one()
        return False
    
    def unlink(self):
        for product in self:
            if product.restaurant_product_type == "combo" and product._is_combo_operationally_used():
                raise ValidationError(
                    "You cannot delete a combo meal after it has been used operationally. Archive it instead."
                )

        return super().unlink()

    def _get_combo_component_lines(self):
        self.ensure_one()

        if self.restaurant_product_type != "combo":
            return self.env["restaurant.combo.line"]

        return self.combo_component_line_ids.sorted(lambda line: (line.sequence, line.id))

    def _get_combo_component_products(self):
        self.ensure_one()

        return self._get_combo_component_lines().mapped("component_product_tmpl_id")

    def _get_combo_individual_total_price(self):
        self.ensure_one()

        total = 0.0
        for line in self._get_combo_component_lines():
            total += line.component_product_tmpl_id.list_price * line.quantity

        return total

    def _get_combo_saving_amount(self):
        self.ensure_one()

        return self._get_combo_individual_total_price() - self.list_price

    def _prepare_combo_operational_payload(self):
        self.ensure_one()
        self._check_combo_operational_validity()
        availability = self._get_combo_availability_status()

        payload = {
            "combo_product_tmpl_id": self.id,
            "combo_name": self.display_name,
            "combo_price": self.list_price,
            "individual_total_price": self._get_combo_individual_total_price(),
            "saving_amount": self._get_combo_saving_amount(),
            "is_available": availability["available"],
            "unavailable_reason": availability["reason"] or "",
            "components": [],
        }

        for line in self._get_combo_component_lines():
            payload["components"].append({
                "line_id": line.id,
                "component_product_tmpl_id": line.component_product_tmpl_id.id,
                "component_name": line.component_product_tmpl_id.display_name,
                "quantity": line.quantity,
                "allow_customization": line.allow_customization,
                "is_swappable": line.is_swappable,
                "allowed_substitute_product_tmpl_ids": line.allowed_substitute_product_ids.ids,
                "is_upgradeable": line.is_upgradeable,
                "upgrade_price": line.upgrade_price,
                "notes": line.notes or "",
            })

        return payload
    
    def _get_combo_availability_status(self):
        self.ensure_one()

        if self.restaurant_product_type != "combo":
            return {
                "available": True,
                "reason": False,
            }

        if not self.combo_is_valid:
            return {
                "available": False,
                "reason": self.combo_validation_message or "Combo meal is not operationally valid.",
            }

        unavailable_reasons = []

        for line in self._get_combo_component_lines():
            component = line.component_product_tmpl_id

            if not component:
                unavailable_reasons.append("Combo contains an empty component line.")
                continue

            if not component.sale_ok:
                unavailable_reasons.append(
                    f"Component '{component.display_name}' is not sellable."
                )

        if unavailable_reasons:
            return {
                "available": False,
                "reason": "\n".join(unavailable_reasons),
            }

        return {
            "available": True,
            "reason": False,
        }

    # ──────────────────────────────────────────────────────────────────
    # UC-08 Step 3 — Branch Availability Resolver
    # ──────────────────────────────────────────────────────────────────

    def _is_available_in_branch(self, branch, check_date=None):

        self.ensure_one()

        if check_date is None:
            check_date = fields.Date.context_today(self)

        # A) Product must be active
        if not self.active:
            return False

        # B) Product must be sellable
        if not self.sale_ok:
            return False

        # C) Branch must be provided
        if not branch:
            return False

        branch.ensure_one()

        # D) Branch must be active
        if not branch.active:
            return False

        # Company mismatch check
        if self.company_id and branch.company_id != self.company_id:
            return False

        # E) Date range checks
        if self.branch_available_from and check_date < self.branch_available_from:
            return False
        if self.branch_available_until and check_date > self.branch_available_until:
            return False

        # F) Mode checks
        if self.branch_availability_mode == "all_branches":
            return True
        if self.branch_availability_mode == "selected_branches":
            return branch in self.branch_available_ids
        if self.branch_availability_mode == "excluded_branches":
            return branch not in self.branch_excluded_ids

        # G) Fallback
        return False

    def _get_branch_unavailability_reason(self, branch, check_date=None):
        self.ensure_one()

        if check_date is None:
            check_date = fields.Date.context_today(self)

        # A) Archived product
        if not self.active:
            return "Product is archived."

        # B) Not sellable
        if not self.sale_ok:
            return "Product is not sellable."

        # C) Missing branch
        if not branch:
            return "Branch is required."
        
        branch.ensure_one()

        # D) Archived branch
        if not branch.active:
            return "Branch is archived."

        # Company mismatch check
        if self.company_id and branch.company_id != self.company_id:
            return "Branch belongs to a different company than the product."

        # E) Date range
        if self.branch_available_from and check_date < self.branch_available_from:
            return "Product is not available before %s." % self.branch_available_from

        if self.branch_available_until and check_date > self.branch_available_until:
            return "Product is not available after %s." % self.branch_available_until

        # F-G) Mode checks
        if self.branch_availability_mode == "selected_branches":
            if branch not in self.branch_available_ids:
                return self.branch_unavailable_reason or "Product is not available in this branch."

        if self.branch_availability_mode == "excluded_branches":
            if branch in self.branch_excluded_ids:
                return self.branch_unavailable_reason or "Product is excluded from this branch."

        # Available — no reason
        if self._is_available_in_branch(branch, check_date):
            return False

        # I) Fallback
        return "Product is not available in this branch."


    def _get_branch_availability_payload(self, branch, check_date=None):
        self.ensure_one()
        if branch:
            branch.ensure_one() 
        available = self._is_available_in_branch(branch, check_date)
        reason = self._get_branch_unavailability_reason(branch, check_date) if not available else ""
        return {
            "product_tmpl_id": self.id,
            "branch_id": branch.id if branch else False,
            "available": available,
            "reason": reason or "",
            "mode": self.branch_availability_mode,
        }

    # ──────────────────────────────────────────────────────────────────
    # UC-08 Step 5 — Branch Availability Logging Helpers
    # ──────────────────────────────────────────────────────────────────

    def _format_branch_names(self, branches):
        if not branches:
            return ""
        names = sorted(branches.with_context(active_test=False).mapped("name"))
        return ", ".join(names)

    @api.depends("branch_availability_mode", "branch_available_ids.name", "branch_excluded_ids.name")
    def _compute_branch_availability_summary(self):
        for record in self:
            if record.branch_availability_mode == "all_branches":
                record.branch_availability_summary = "Available in all branches"
            elif record.branch_availability_mode == "selected_branches":
                branches = record._format_branch_names(record.branch_available_ids)
                record.branch_availability_summary = f"Available only in: {branches}"
            elif record.branch_availability_mode == "excluded_branches":
                branches = record._format_branch_names(record.branch_excluded_ids)
                record.branch_availability_summary = f"Available in all branches except: {branches}"
            else:
                record.branch_availability_summary = ""

    @api.depends("branch_availability_mode", "branch_available_from", "branch_available_until")
    def _compute_branch_availability_has_restriction(self):
        for record in self:
            record.branch_availability_has_restriction = (
                record.branch_availability_mode != "all_branches"
                or bool(record.branch_available_from)
                or bool(record.branch_available_until)
            )

    @api.depends("branch_available_from", "branch_available_until")
    def _compute_branch_availability_date_summary(self):
        for record in self:
            if record.branch_available_from and record.branch_available_until:
                record.branch_availability_date_summary = f"Available from {record.branch_available_from} until {record.branch_available_until}"
            elif record.branch_available_from:
                record.branch_availability_date_summary = f"Available from {record.branch_available_from}"
            elif record.branch_available_until:
                record.branch_availability_date_summary = f"Available until {record.branch_available_until}"
            else:
                record.branch_availability_date_summary = False

    def _get_availability_mode_label(self, mode):
        labels = {
            "all_branches": "Available in All Branches",
            "selected_branches": "Available Only in Selected Branches",
            "excluded_branches": "All Branches Except Excluded",
        }
        return labels.get(mode, mode)

    def _get_availability_snapshot(self):
        self.ensure_one()
        record_wf = self.with_context(active_test=False)
        return {
            "mode": record_wf.branch_availability_mode,
            "available_branches": self._format_branch_names(record_wf.branch_available_ids),
            "excluded_branches": self._format_branch_names(record_wf.branch_excluded_ids),
            "available_from": record_wf.branch_available_from,
            "available_until": record_wf.branch_available_until,
            "unavailable_reason": record_wf.branch_unavailable_reason or "",
        }

    def _create_availability_log(self, old_snapshot, new_snapshot):
        self.ensure_one()
        
        mode_changed = old_snapshot["mode"] != new_snapshot["mode"]
        available_changed = old_snapshot["available_branches"] != new_snapshot["available_branches"]
        excluded_changed = old_snapshot["excluded_branches"] != new_snapshot["excluded_branches"]
        from_changed = old_snapshot["available_from"] != new_snapshot["available_from"]
        until_changed = old_snapshot["available_until"] != new_snapshot["available_until"]
        reason_changed = old_snapshot["unavailable_reason"] != new_snapshot["unavailable_reason"]

        if not (mode_changed or available_changed or excluded_changed or from_changed or until_changed or reason_changed):
            return False

        summary_parts = []
        if mode_changed:
            summary_parts.append(
                f"Mode changed from '{self._get_availability_mode_label(old_snapshot['mode'])}' to '{self._get_availability_mode_label(new_snapshot['mode'])}'."
            )
        if available_changed:
            summary_parts.append(
                f"Available branches changed from '{old_snapshot['available_branches']}' to '{new_snapshot['available_branches']}'."
            )
        if excluded_changed:
            summary_parts.append(
                f"Excluded branches changed from '{old_snapshot['excluded_branches']}' to '{new_snapshot['excluded_branches']}'."
            )
        if from_changed:
            old_from = old_snapshot['available_from']
            new_from = new_snapshot['available_from']
            summary_parts.append(
                f"Available From changed from '{old_from or ''}' to '{new_from or ''}'."
            )
        if until_changed:
            old_until = old_snapshot['available_until']
            new_until = new_snapshot['available_until']
            summary_parts.append(
                f"Available Until changed from '{old_until or ''}' to '{new_until or ''}'."
            )
        if reason_changed:
            summary_parts.append(
                f"Unavailable reason changed from '{old_snapshot['unavailable_reason']}' to '{new_snapshot['unavailable_reason']}'."
            )

        change_summary = " ".join(summary_parts)

        return self.env["restaurant.branch.availability.log"].sudo().create({
            "product_tmpl_id": self.id,
            "changed_by_id": self.env.user.id,
            "changed_on": fields.Datetime.now(),
            "old_mode": self._get_availability_mode_label(old_snapshot["mode"]),
            "new_mode": self._get_availability_mode_label(new_snapshot["mode"]),
            "old_available_branch_names": old_snapshot["available_branches"],
            "new_available_branch_names": new_snapshot["available_branches"],
            "old_excluded_branch_names": old_snapshot["excluded_branches"],
            "new_excluded_branch_names": new_snapshot["excluded_branches"],
            "old_available_from": old_snapshot["available_from"],
            "new_available_from": new_snapshot["available_from"],
            "old_available_until": old_snapshot["available_until"],
            "new_available_until": new_snapshot["available_until"],
            "old_unavailable_reason": old_snapshot["unavailable_reason"],
            "new_unavailable_reason": new_snapshot["unavailable_reason"],
            "change_summary": change_summary,
        })

