# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

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
    allowed_branch_ids = fields.Many2many(
        "restaurant.branch",
        compute="_compute_allowed_branch_ids",
    )
    branch_availability_selectable_branch_ids = fields.Many2many(
        "restaurant.branch",
        compute="_compute_branch_availability_selectable_branch_ids",
    )
    can_edit_global_branch_availability = fields.Boolean(
        compute="_compute_can_edit_global_branch_availability",
    )

    def _compute_can_edit_global_branch_availability(self):
        can_edit = self.env.su or self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
        for record in self:
            record.can_edit_global_branch_availability = can_edit

    @api.depends("company_id")
    @api.depends_context("uid")
    def _compute_branch_availability_selectable_branch_ids(self):
        is_admin = self.env.su
        is_ops_manager = self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
        is_company_manager = self.env.user.has_group("restaurant_base.group_restaurant_company_availability_manager")
        is_branch_manager = self.env.user.has_group("restaurant_base.group_restaurant_branch_manager")

        for record in self:
            domain = [("active", "=", True)]
            if record.company_id:
                domain.append(("company_id", "=", record.company_id.id))

            if not is_admin:
                domain.append(("company_id", "in", self.env.user.company_ids.ids))

            if is_admin or is_ops_manager or is_company_manager:
                record.branch_availability_selectable_branch_ids = self.env["restaurant.branch"].search(domain)
            elif is_branch_manager:
                managed_domain = domain + [("manager_user_ids", "in", self.env.user.id)]
                record.branch_availability_selectable_branch_ids = self.env["restaurant.branch"].search(managed_domain)
            else:
                record.branch_availability_selectable_branch_ids = self.env["restaurant.branch"].browse()

    @api.depends("company_id")
    def _compute_allowed_branch_ids(self):
        for record in self:
            domain = [("active", "=", True)]
            if record.company_id:
                domain.append(("company_id", "in", [False, record.company_id.id]))
            record.allowed_branch_ids = self.env["restaurant.branch"].search(domain)

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

    def _get_branch_availability_fields(self):
        return {
            "branch_availability_mode",
            "branch_available_ids",
            "branch_excluded_ids",
            "branch_available_from",
            "branch_available_until",
            "branch_unavailable_reason",
        }

    def _resolve_m2m_commands(self, current_records, commands):
        if not commands:
            return current_records
        result = set(current_records.ids)
        for command in commands:
            if command[0] == 6:  # Replace all
                result = set(command[2])
            elif command[0] == 4:  # Add
                result.add(command[1])
            elif command[0] == 3:  # Remove (no delete)
                result.discard(command[1])
            elif command[0] == 5:  # Clear all
                result.clear()
        return self.env["restaurant.branch"].browse(list(result))

    def _check_user_can_modify_branch_availability_global(self, vals, is_create=False):
        availability_fields = self._get_branch_availability_fields()
        if not any(f in vals for f in availability_fields):
            return

        is_admin = self.env.su
        is_ops_manager = self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
        is_company_manager = self.env.user.has_group("restaurant_base.group_restaurant_company_availability_manager")
        is_branch_manager = self.env.user.has_group("restaurant_base.group_restaurant_branch_manager")

        if not (is_admin or is_ops_manager or is_company_manager or is_branch_manager):
            raise ValidationError("You do not have permission to modify branch availability.")

        records = self if not is_create else [self.env["product.template"]]
        global_fields = {"branch_availability_mode", "branch_available_from", "branch_available_until", "branch_unavailable_reason"}

        for record in records:
            for f in global_fields:
                if f in vals:
                    if is_create:
                        # Allow default mode 'all_branches' on create if not explicitly changed
                        if f == "branch_availability_mode" and vals[f] == "all_branches":
                            continue
                        if not (is_admin or is_ops_manager):
                            raise ValidationError("Only Operations Managers can set the branch availability mode, dates, and reason on creation.")
                    else:
                        if vals[f] != getattr(record, f):
                            if not (is_admin or is_ops_manager):
                                raise ValidationError("Only Operations Managers can change the branch availability mode, dates, and reason.")
            
            mode = vals.get("branch_availability_mode", record.branch_availability_mode if not is_create else "all_branches")
            if mode == "all_branches":
                if not (is_admin or is_ops_manager):
                    raise ValidationError("Only Operations Managers and Superusers can use 'All Branches' mode.")

    def _preserve_unmanaged_branches(self, record, vals):
        is_admin = self.env.su
        is_ops_manager = self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
        is_company_manager = self.env.user.has_group("restaurant_base.group_restaurant_company_availability_manager")
        is_branch_manager = self.env.user.has_group("restaurant_base.group_restaurant_branch_manager")

        for field_name in ["branch_available_ids", "branch_excluded_ids"]:
            if field_name not in vals:
                continue

            old_records = getattr(record, field_name)
            commands = vals[field_name]
            final_records = self._resolve_m2m_commands(old_records, commands)
            
            added = final_records - old_records
            removed = old_records - final_records

            # Validate Additions
            if not is_admin:
                out_of_company_adds = added.filtered(lambda b: b.company_id.id not in self.env.user.company_ids.ids)
                if out_of_company_adds:
                    raise ValidationError(f"You cannot add branches outside your allowed companies: {', '.join(out_of_company_adds.mapped('name'))}")

            if not (is_admin or is_ops_manager or is_company_manager) and is_branch_manager:
                unmanaged_adds = added.filtered(lambda b: self.env.user not in b.manager_user_ids)
                if unmanaged_adds:
                    raise ValidationError(f"You cannot add branches you do not manage: {', '.join(unmanaged_adds.mapped('name'))}")

            company_id = vals.get("company_id", record.company_id.id)
            if company_id:
                incompatible = added.filtered(lambda b: b.company_id.id != company_id)
                if incompatible:
                    raise ValidationError(f"Selected branches must belong to the same company as the product: {', '.join(incompatible.mapped('name'))}")

            # Preserve Removals
            preserved = self.env["restaurant.branch"]
            if not is_admin:
                preserved |= removed.filtered(lambda b: b.company_id.id not in self.env.user.company_ids.ids)
                
            if not (is_admin or is_ops_manager or is_company_manager) and is_branch_manager:
                preserved |= removed.filtered(lambda b: self.env.user not in b.manager_user_ids)

            if preserved:
                final_with_preserved = final_records | preserved
                vals[field_name] = [(6, 0, final_with_preserved.ids)]

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

    def write(self, vals):
        self._check_user_can_modify_branch_availability_global(vals, is_create=False)

        availability_fields = self._get_branch_availability_fields()
        has_availability_changes = any(f in vals for f in availability_fields)

        if not has_availability_changes:
            return super().write(vals)

        is_admin = self.env.su
        is_ops_manager = self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
        
        if not (is_admin or is_ops_manager) and ("branch_available_ids" in vals or "branch_excluded_ids" in vals):
            res = True
            for record in self:
                record_vals = vals.copy()
                self._preserve_unmanaged_branches(record, record_vals)
                
                old_snap = record._get_availability_snapshot()
                record_vals["branch_availability_last_changed_by"] = self.env.user.id
                record_vals["branch_availability_last_changed_on"] = fields.Datetime.now()
                
                super(ProductTemplate, record).write(record_vals)
                
                record._cleanup_availability_modes()
                new_snap = record._get_availability_snapshot()
                record._create_availability_log(old_snap, new_snap)
            return res

        old_snapshots = {}
        vals["branch_availability_last_changed_by"] = self.env.user.id
        vals["branch_availability_last_changed_on"] = fields.Datetime.now()
        for record in self:
            old_snapshots[record.id] = record._get_availability_snapshot()

        res = super().write(vals)

        for record in self:
            record._cleanup_availability_modes()
            old_snap = old_snapshots.get(record.id)
            if old_snap:
                new_snap = record._get_availability_snapshot()
                record._create_availability_log(old_snap, new_snap)

        return res

    def _cleanup_availability_modes(self):
        self.ensure_one()
        clean_vals = {}
        if self.branch_availability_mode == "all_branches":
            if self.branch_available_ids:
                clean_vals["branch_available_ids"] = [(5, 0, 0)]
            if self.branch_excluded_ids:
                clean_vals["branch_excluded_ids"] = [(5, 0, 0)]
        elif self.branch_availability_mode == "selected_branches":
            if self.branch_excluded_ids:
                clean_vals["branch_excluded_ids"] = [(5, 0, 0)]
        elif self.branch_availability_mode == "excluded_branches":
            if self.branch_available_ids:
                clean_vals["branch_available_ids"] = [(5, 0, 0)]

        if clean_vals:
            super(ProductTemplate, self).write(clean_vals)

    @api.model_create_multi
    def create(self, vals_list):
        availability_fields = self._get_branch_availability_fields()

        for vals in vals_list:
            self._check_user_can_modify_branch_availability_global(vals, is_create=True)
            mode = vals.get("branch_availability_mode", "all_branches")
            if mode == "all_branches":
                vals["branch_available_ids"] = [(5, 0, 0)]
                vals["branch_excluded_ids"] = [(5, 0, 0)]
            elif mode == "selected_branches":
                vals["branch_excluded_ids"] = [(5, 0, 0)]
            elif mode == "excluded_branches":
                vals["branch_available_ids"] = [(5, 0, 0)]

            # Check additions
            is_admin = self.env.su
            is_ops_manager = self.env.user.has_group("restaurant_base.group_restaurant_operations_manager")
            is_company_manager = self.env.user.has_group("restaurant_base.group_restaurant_company_availability_manager")
            is_branch_manager = self.env.user.has_group("restaurant_base.group_restaurant_branch_manager")

            for field_name in ["branch_available_ids", "branch_excluded_ids"]:
                if field_name in vals:
                    commands = vals[field_name]
                    final_records = self._resolve_m2m_commands(self.env["restaurant.branch"], commands)
                    
                    if not is_admin:
                        out_of_company_adds = final_records.filtered(lambda b: b.company_id.id not in self.env.user.company_ids.ids)
                        if out_of_company_adds:
                            raise ValidationError(f"You cannot add branches outside your allowed companies: {', '.join(out_of_company_adds.mapped('name'))}")

                    if not (is_admin or is_ops_manager or is_company_manager) and is_branch_manager:
                        unmanaged_adds = final_records.filtered(lambda b: self.env.user not in b.manager_user_ids)
                        if unmanaged_adds:
                            raise ValidationError(f"You cannot add branches you do not manage: {', '.join(unmanaged_adds.mapped('name'))}")

                    company_id = vals.get("company_id", False)
                    if company_id:
                        incompatible = final_records.filtered(lambda b: b.company_id.id != company_id)
                        if incompatible:
                            raise ValidationError(f"Selected branches must belong to the same company as the product: {', '.join(incompatible.mapped('name'))}")

            if any(f in vals for f in availability_fields):
                vals["branch_availability_last_changed_by"] = self.env.user.id
                vals["branch_availability_last_changed_on"] = fields.Datetime.now()

        return super().create(vals_list)
