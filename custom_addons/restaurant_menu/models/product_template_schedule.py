import pytz
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_evaluation_tz(self, branch=None):
        """Returns timezone string using 4-level fallback:
        1. branch.tz
        2. branch.company_id.resource_calendar_id.tz
        3. env.user.tz
        4. 'UTC'
        """
        if branch:
            if branch.tz:
                return branch.tz
            if branch.company_id and branch.company_id.resource_calendar_id and branch.company_id.resource_calendar_id.tz:
                return branch.company_id.resource_calendar_id.tz
        if self.env.user.tz:
            return self.env.user.tz
        return 'UTC'

    def _localize_datetime(self, at_datetime, branch=None):
        """Converts UTC datetime to localized datetime using resolved tz."""
        if not at_datetime:
            at_datetime = fields.Datetime.now()
        
        # Ensure it has UTC tz info if naive
        if at_datetime.tzinfo is None:
            at_datetime = pytz.utc.localize(at_datetime)
            
        tz_name = self._get_evaluation_tz(branch)
        target_tz = pytz.timezone(tz_name)
        return at_datetime.astimezone(target_tz)

    def _evaluate_schedule_rule(self, rule, local_dt):
        """Evaluates a single schedule rule against a localized datetime.
        Returns True if rule matches, False otherwise.
        """
        # 1. Date Range Check (inclusive, local date)
        local_date = local_dt.date()
        if rule.date_from and local_date < rule.date_from:
            return False
        if rule.date_to and local_date > rule.date_to:
            return False

        # 2. Time and Day Check
        has_time = (rule.start_time != 0.0 or rule.end_time != 0.0)
        current_time = local_dt.hour + local_dt.minute / 60.0

        if not has_time:
            # Case 1: No time restriction, day check on local_dt directly
            if not rule.day_ids:
                return True
            day_codes = rule.day_ids.mapped('code')
            return str(local_dt.weekday()) in day_codes

        elif rule.start_time < rule.end_time:
            # Case 2: Normal same-day window
            if not (rule.start_time <= current_time < rule.end_time):
                return False
            if not rule.day_ids:
                return True
            day_codes = rule.day_ids.mapped('code')
            return str(local_dt.weekday()) in day_codes

        else:
            # Case 3: Midnight crossing (start_time > end_time)
            # note: constraint blocks start_time == end_time
            in_window = False
            check_day = None

            if current_time >= rule.start_time:
                in_window = True
                check_day = local_dt.weekday()
            elif current_time < rule.end_time:
                in_window = True
                check_day = (local_dt.weekday() - 1) % 7

            if not in_window:
                return False

            if not rule.day_ids:
                return True

            day_codes = rule.day_ids.mapped('code')
            return str(check_day) in day_codes

    def _evaluate_category_schedule(self, category, eval_company, branch, local_dt):
        """Evaluates category schedule lines.
        Returns tuple: (bool_is_available, list_of_matched_line_ids)
        """
        domain = [
            ('category_id', '=', category.id),
            ('active', '=', True),
            ('schedule_rule_id.active', '=', True),
            ('company_id', '=', eval_company.id),
        ]
        if branch:
            domain.append(('branch_id', 'in', [False, branch.id]))
        else:
            domain.append(('branch_id', '=', False))

        lines = self.env['restaurant.category.schedule.line'].search(domain)
        if not lines:
            # Category has no active schedule lines, so it passes
            return True, []

        matched_line_ids = []
        for line in lines:
            if self._evaluate_schedule_rule(line.schedule_rule_id, local_dt):
                matched_line_ids.append(line.id)

        # If has active schedule lines and at least one matches -> passes
        if matched_line_ids:
            return True, matched_line_ids

        # If has active schedule lines and none match -> blocks
        return False, []

    def _get_active_schedule_override(self, branch, at_datetime=None):
        """Returns the active schedule override for this product+branch at the given datetime.
        Priority: most recent date_from, then highest id.
        Returns a recordset (empty if none found).
        """
        if not branch:
            return self.env['restaurant.schedule.override']

        if not at_datetime:
            at_datetime = fields.Datetime.now()

        eval_company = branch.company_id or self.env.company
        domain = [
            ('product_tmpl_id', '=', self.id),
            ('branch_id', '=', branch.id),
            ('company_id', '=', eval_company.id),
            ('active', '=', True),
            ('date_from', '<=', at_datetime),
            '|',
            ('date_to', '=', False),
            ('date_to', '>=', at_datetime),
        ]
        return self.env['restaurant.schedule.override'].search(
            domain, order='date_from desc, id desc', limit=1
        )

    def _get_schedule_availability(self, branch=None, at_datetime=None):
        """Returns bool indicating if product is schedule-available."""
        payload = self._get_schedule_availability_payload(branch=branch, at_datetime=at_datetime)
        return payload.get('is_available', False)

    def _get_schedule_availability_payload(self, branch=None, at_datetime=None):
        """Returns dict containing details of schedule availability evaluation."""
        self.ensure_one()

        if not at_datetime:
            at_datetime = fields.Datetime.now()

        local_dt = self._localize_datetime(at_datetime, branch=branch)
        eval_company = (branch.company_id or self.env.company) if branch else self.env.company

        # Initialize payload
        payload = {
            'product_tmpl_id': self.id,
            'is_available': False,
            'reason': '',
            'reason_code': '',
            'branch_id': branch.id if branch else False,
            'company_id': eval_company.id,
            'matched_schedule_ids': [],
            'matched_category_schedule_ids': [],
            'blocking_schedule_ids': [],
            'manual_override': False,
            'override_id': False,
            'override_type': False,
            'warnings': [],
        }

        # Priority 1: Manual Schedule Override (branch-specific only)
        if branch:
            override = self._get_active_schedule_override(branch, at_datetime=at_datetime)
            if override:
                if override.override_type == 'force_available':
                    payload['is_available'] = True
                    payload['reason'] = override.reason
                    payload['reason_code'] = 'manual_schedule_override_available'
                else:
                    payload['is_available'] = False
                    payload['reason'] = override.reason
                    payload['reason_code'] = 'manual_schedule_override_unavailable'
                payload['manual_override'] = True
                payload['override_id'] = override.id
                payload['override_type'] = override.override_type
                return payload
        else:
            payload['warnings'].append(
                "No branch context provided. Schedule override requires branch context. "
                "Continuing with global/company schedule logic."
            )

        # Step 1: Category Gate Logic
        # A product can belong to multiple categories via pos_categ_ids
        blocked_by_categories = self.env['pos.category']
        all_matched_category_line_ids = []

        if self.pos_categ_ids:
            for category in self.pos_categ_ids:
                is_cat_available, cat_matched_ids = self._evaluate_category_schedule(
                    category, eval_company, branch, local_dt
                )
                if not is_cat_available:
                    blocked_by_categories |= category
                else:
                    all_matched_category_line_ids.extend(cat_matched_ids)

        if blocked_by_categories:
            payload['is_available'] = False
            cat_names = ", ".join(blocked_by_categories.mapped('name'))
            payload['reason'] = f"Category gate blocked. Blocked by categories: {cat_names}."
            payload['reason_code'] = 'category_blocked'
            payload['matched_category_schedule_ids'] = []
            return payload

        # Categories passed, collect matched category IDs
        payload['matched_category_schedule_ids'] = list(set(all_matched_category_line_ids))

        # Step 2: Product Schedule Logic
        domain = [
            ('product_tmpl_id', '=', self.id),
            ('active', '=', True),
            ('schedule_rule_id.active', '=', True),
            ('company_id', '=', eval_company.id),
        ]
        if branch:
            domain.append(('branch_id', 'in', [False, branch.id]))
        else:
            domain.append(('branch_id', '=', False))

        product_lines = self.env['restaurant.product.schedule.line'].search(domain)
        if not product_lines:
            payload['is_available'] = True
            payload['reason'] = "Product has no active schedule rules. Available by default."
            payload['reason_code'] = 'no_schedule'
            return payload

        matched_product_line_ids = []
        for line in product_lines:
            if self._evaluate_schedule_rule(line.schedule_rule_id, local_dt):
                matched_product_line_ids.append(line.id)

        if matched_product_line_ids:
            payload['is_available'] = True
            payload['reason'] = "Available. Active product schedule rule matches current time."
            payload['reason_code'] = 'schedule_match'
            payload['matched_schedule_ids'] = matched_product_line_ids
        else:
            payload['is_available'] = False
            payload['reason'] = "Unavailable. Product has active schedule rules but none match current time."
            payload['reason_code'] = 'product_blocked'
            payload['matched_schedule_ids'] = []

        return payload