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

        return super().create(vals_list)
