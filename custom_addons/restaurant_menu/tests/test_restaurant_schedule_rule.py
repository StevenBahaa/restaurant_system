from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError

@tagged('post_install', '-at_install')
class TestRestaurantScheduleRule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_main = cls.env.ref('base.main_company')
        
        # Find some days
        cls.day_mon = cls.env['restaurant.schedule.day'].search([('code', '=', '0')], limit=1)
        cls.day_tue = cls.env['restaurant.schedule.day'].search([('code', '=', '1')], limit=1)
        cls.day_wed = cls.env['restaurant.schedule.day'].search([('code', '=', '2')], limit=1)

        # Create branch
        cls.branch_cairo = cls.env['restaurant.branch'].create({
            'name': 'Cairo Branch',
            'code': 'CAI01',
            'company_id': cls.company_main.id,
            'tz': 'Africa/Cairo',
        })

        # Create basic user and manager user
        cls.group_ops_mgr = cls.env.ref('restaurant_base.group_restaurant_operations_manager')
        cls.user_ops_mgr = cls.env['res.users'].create({
            'name': 'Operations Manager',
            'login': 'ops_mgr_uc12',
            'email': 'ops_uc12@example.com',
            'groups_id': [(6, 0, [cls.group_ops_mgr.id])],
            'company_id': cls.company_main.id,
            'company_ids': [(6, 0, [cls.company_main.id])],
        })
        
        cls.user_basic = cls.env['res.users'].create({
            'name': 'Basic User',
            'login': 'basic_user_uc12',
            'email': 'basic_uc12@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
            'company_id': cls.company_main.id,
            'company_ids': [(6, 0, [cls.company_main.id])],
        })

    def test_01_days_loaded(self):
        """Test that Monday to Sunday records are correctly loaded from XML data"""
        days = self.env['restaurant.schedule.day'].search([])
        self.assertEqual(len(days), 7)
        self.assertEqual(sorted(days.mapped('code')), ['0', '1', '2', '3', '4', '5', '6'])

    def test_02_timezone_added_to_branch(self):
        """Test that the branch has the tz field and it defaults to Africa/Cairo"""
        self.assertEqual(self.branch_cairo.tz, 'Africa/Cairo')
        
        # Test creation of a branch with a different timezone
        branch_tokyo = self.env['restaurant.branch'].create({
            'name': 'Tokyo Branch',
            'code': 'TKY01',
            'company_id': self.company_main.id,
            'tz': 'Asia/Tokyo',
        })
        self.assertEqual(branch_tokyo.tz, 'Asia/Tokyo')

        # Test branch creation without explicit tz defaults to Africa/Cairo
        branch_default = self.env['restaurant.branch'].create({
            'name': 'Default TZ Branch',
            'code': 'DTZ01',
            'company_id': self.company_main.id,
        })
        self.assertEqual(branch_default.tz, 'Africa/Cairo')

    def test_03_create_valid_schedule_rules(self):
        """Test creating valid schedule rules"""
        # Rule with time restriction only
        rule1 = self.env['restaurant.schedule.rule'].create({
            'name': 'Lunch Time',
            'start_time': 12.0,
            'end_time': 15.5,
        })
        self.assertTrue(rule1.id)
        
        # Rule with day restriction only
        rule2 = self.env['restaurant.schedule.rule'].create({
            'name': 'Mondays Only',
            'day_ids': [(4, self.day_mon.id)],
        })
        self.assertTrue(rule2.id)

        # Rule with date range only
        rule3 = self.env['restaurant.schedule.rule'].create({
            'name': 'May Special',
            'date_from': '2026-05-01',
            'date_to': '2026-05-31',
        })
        self.assertTrue(rule3.id)

        # Rule crossing midnight
        rule4 = self.env['restaurant.schedule.rule'].create({
            'name': 'Late Night',
            'start_time': 23.0,
            'end_time': 4.0,
            'day_ids': [(4, self.day_mon.id)],
        })
        self.assertTrue(rule4.id)

        # Rule starting at exactly midnight (Bug 2 verification)
        rule_midnight = self.env['restaurant.schedule.rule'].create({
            'name': 'Midnight Start',
            'start_time': 0.0,
            'end_time': 4.0,
        })
        self.assertTrue(rule_midnight.id)
        
        # Rule with start time only (implicitly means noon to midnight, start_time=12.0, end_time=0.0)
        rule_noon_to_midnight = self.env['restaurant.schedule.rule'].create({
            'name': 'Noon to Midnight',
            'start_time': 12.0,
        })
        self.assertTrue(rule_noon_to_midnight.id)

        # Rule partial update (Bug 1 verification: write only one field)
        rule1.write({'start_time': 10.0})
        self.assertEqual(rule1.start_time, 10.0)
        self.assertEqual(rule1.end_time, 15.5)

    def test_04_invalid_schedule_rules(self):
        """Test that invalid schedule rules raise ValidationError"""
        # Empty rule
        with self.assertRaises(ValidationError):
            self.env['restaurant.schedule.rule'].create({
                'name': 'Empty Rule',
            })

        # Start time out of range
        with self.assertRaises(ValidationError):
            self.env['restaurant.schedule.rule'].create({
                'name': 'Invalid Start',
                'start_time': -1.0,
                'end_time': 12.0,
            })

        # End time out of range
        with self.assertRaises(ValidationError):
            self.env['restaurant.schedule.rule'].create({
                'name': 'Invalid End',
                'start_time': 12.0,
                'end_time': 24.5,
            })

        # Equal start and end
        with self.assertRaises(ValidationError):
            self.env['restaurant.schedule.rule'].create({
                'name': 'Equal Time',
                'start_time': 12.0,
                'end_time': 12.0,
            })

        # Invalid date range
        with self.assertRaises(ValidationError):
            self.env['restaurant.schedule.rule'].create({
                'name': 'Invalid Dates',
                'date_from': '2026-05-31',
                'date_to': '2026-05-01',
            })

    def test_05_security_access_rights(self):
        """Test ACL permissions for operations manager vs basic user"""
        # Operations manager should be able to create schedule rules
        rule = self.env['restaurant.schedule.rule'].with_user(self.user_ops_mgr).create({
            'name': 'Ops Mgr Rule',
            'start_time': 10.0,
            'end_time': 11.0,
        })
        self.assertTrue(rule.id)

        # Basic user should be able to read schedule rules
        rules = self.env['restaurant.schedule.rule'].with_user(self.user_basic).search([])
        self.assertTrue(len(rules) >= 1)
        self.assertTrue(rule.with_user(self.user_basic).read(['name']))

        # Basic user should NOT be able to create schedule rules
        with self.assertRaises(AccessError):
            self.env['restaurant.schedule.rule'].with_user(self.user_basic).create({
                'name': 'Basic User Rule',
                'start_time': 10.0,
                'end_time': 11.0,
            })

        # Basic user should NOT be able to write schedule rules
        with self.assertRaises(AccessError):
            rule.with_user(self.user_basic).write({'name': 'Hacked Name'})

        # Basic user should NOT be able to unlink schedule rules
        with self.assertRaises(AccessError):
            rule.with_user(self.user_basic).unlink()

    def test_06_multi_company_isolation(self):
        """Test multi-company record rules block access to other company's rules"""
        company2 = self.env['res.company'].create({'name': 'Second Company'})
        user_c2_ops = self.env['res.users'].create({
            'name': 'C2 Ops Manager',
            'login': 'c2_ops_mgr_uc12',
            'email': 'c2_ops_uc12@example.com',
            'groups_id': [(6, 0, [self.group_ops_mgr.id])],
            'company_id': company2.id,
            'company_ids': [(6, 0, [company2.id])],
        })

        # Create rule in company 2
        rule_c2 = self.env['restaurant.schedule.rule'].with_user(user_c2_ops).create({
            'name': 'Company 2 Rule',
            'start_time': 8.0,
            'end_time': 10.0,
            'company_id': company2.id,
        })
        self.assertTrue(rule_c2.id)

        # Operations Manager in main company should NOT find/see the rule in company 2
        rules = self.env['restaurant.schedule.rule'].with_user(self.user_ops_mgr).search([('id', '=', rule_c2.id)])
        self.assertFalse(rules)

        # Attempt to read company 2 rule by Company 1 manager should fail (AccessError)
        with self.assertRaises(AccessError):
            rule_c2.with_user(self.user_ops_mgr).read(['name'])
