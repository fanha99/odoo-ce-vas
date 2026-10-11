from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from .common import REPORT_MODEL, FakeReportMixin


@tagged('post_install', '-at_install')
class TestReportAccess(FakeReportMixin, TransactionCase):

    def test_user_in_group_can_read(self):
        data = self.Report.get_report_data({})
        self.assertEqual(len(data['lines']), 2)

    def test_user_not_in_group_is_refused(self):
        Report = self.env[REPORT_MODEL].with_user(self.other_user)
        with self.assertRaises(AccessError):
            Report.get_report_data({})
        with self.assertRaises(AccessError):
            Report.get_xlsx({})
        with self.assertRaises(AccessError):
            Report.get_pdf_rl({})
        with self.assertRaises(AccessError):
            Report.action_drill_down({}, {'id': 1})

    def test_group_list_is_overridable(self):
        self.patch(
            self.registry[REPORT_MODEL], '_get_report_access_groups',
            lambda report: ['account.group_account_user', 'base.group_user'],
        )
        Report = self.env[REPORT_MODEL].with_user(self.other_user)
        self.assertTrue(Report.get_report_data({})['lines'])

    def test_company_out_of_reach_is_refused(self):
        other_company = self.env['res.company'].create({'name': "FG other company"})
        self.assertNotIn(other_company, self.report_user.company_ids)
        with self.assertRaises(AccessError):
            self.Report.get_report_data({'company_id': other_company.id})
        with self.assertRaises(AccessError):
            self.Report.action_drill_down({'company_id': other_company.id}, {'id': 1})

    def test_invalid_company_is_refused(self):
        with self.assertRaises(AccessError):
            self.Report.get_report_data({'company_id': 'abc'})

    def test_company_id_is_normalized(self):
        company = self.report_user.company_id
        data = self.Report.get_report_data({'company_id': str(company.id)})
        self.assertEqual(data['options']['company_id'], company.id)
        self.assertEqual(data['company']['id'], company.id)

    def test_superuser_bypasses_the_checks(self):
        other_company = self.env['res.company'].create({'name': "FG other company"})
        data = self.env[REPORT_MODEL].sudo().get_report_data({'company_id': other_company.id})
        self.assertEqual(data['company']['id'], other_company.id)
