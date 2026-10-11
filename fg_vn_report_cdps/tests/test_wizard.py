import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, new_test_user, tagged

from .common import CDPSCommon


@tagged('post_install', '-at_install')
class TestCDPSWizard(CDPSCommon):
    """ Also covers the abstract wizard of fg_vn_accounting_reports, which
    cannot be instantiated by itself. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('vi_VN')
        cls.accountant = new_test_user(
            cls.env, login='fg_cdps_wizard_user', groups='account.group_account_user',
        )
        cls.Wizard = cls.env['vn.report.cdps.wizard'].with_user(cls.accountant)

    def _wizard(self, **values):
        return self.Wizard.create({'date_from': '2026-01-01', 'date_to': '2026-01-31', **values})

    @freeze_time('2026-02-10')
    def test_defaults(self):
        wizard = self.Wizard.create({})
        self.assertEqual((wizard.date_from, wizard.date_to), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(wizard.company_id, self.accountant.company_id)
        self.assertEqual(wizard.orientation, 'landscape')
        self.assertEqual(wizard.comparison_type, 'none')
        self.assertFalse(wizard.mirror_margin)
        self.assertEqual(wizard.gutter_mm, 6)
        self.assertFalse(wizard.show_zero_balance)
        self.assertFalse(wizard.hierarchy)

    def test_report_language_defaults_to_vietnamese(self):
        self.assertEqual(self.accountant.lang, 'en_US')
        self.assertEqual(self._wizard().report_lang, 'vi_VN')
        codes = [code for code, _name in self.Wizard._fields['report_lang']._description_selection(self.env)]
        self.assertIn('en_US', codes)
        self.assertIn('vi_VN', codes)

    def test_report_language_without_vietnamese(self):
        self.env['res.lang'].search([('code', '=', 'vi_VN')]).active = False
        self.assertEqual(self._wizard().report_lang, 'en_US')

    @freeze_time('2026-05-20')
    def test_quarter_defaults(self):
        self.assertEqual(self.Wizard._default_date_from_quarter(), date(2026, 4, 1))
        self.assertEqual(self.Wizard._default_date_to_quarter(), date(2026, 6, 30))

    def test_options(self):
        wizard = self._wizard(
            report_lang='en_US',
            account_ids=self.accounts['1111'].ids,
            comparison_type='custom',
            comparison_date_from='2025-01-01',
            comparison_date_to='2025-01-31',
            show_zero_balance=True,
            hierarchy=True,
            mirror_margin=True,
            gutter_mm=10,
        )
        self.assertEqual(wizard._get_report_options(), {
            'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31', 'mode': 'range'},
            'company_id': self.accountant.company_id.id,
            'show_zero_balance': True,
            'lang': 'en_US',
            'orientation': 'landscape',
            'mirror_margin': True,
            'gutter_mm': 10,
            'account_ids': self.accounts['1111'].ids,
            'comparison_type': 'custom',
            'comparison_date_from': '2025-01-01',
            'comparison_date_to': '2025-01-31',
            'hierarchy': True,
        })

    def test_view_report(self):
        wizard = self._wizard()
        action = wizard.action_view_report()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'vn_report_cdps')
        self.assertEqual(action['name'], "Trial Balance")
        self.assertEqual(action['context']['options'], wizard._get_report_options())
        # each opening has its own token
        self.assertNotEqual(
            action['context']['report_token'],
            wizard.action_view_report()['context']['report_token'],
        )
        # the options open the report
        data = self.env['vn.report.cdps'].with_user(self.accountant).get_report_data(
            action['context']['options'],
        )
        self.assertEqual(data['options']['lang'], 'vi_VN')
        self.assertTrue(data['lines'][0]['lines'])

    def test_export_actions(self):
        wizard = self._wizard(report_lang='en_US')
        for method, export_format in (
            ('action_export_xlsx', 'xlsx'),
            ('action_export_pdf_rl', 'pdf_rl'),
            ('action_export_xml', 'xml'),
        ):
            action = getattr(wizard, method)()
            self.assertEqual(action['type'], 'ir.actions.act_url')
            url = urlparse(action['url'])
            self.assertEqual(url.path, f'/vn_report/vn.report.cdps/export/{export_format}')
            options = json.loads(parse_qs(url.query)['options'][0])
            self.assertEqual(options, wizard._get_report_options())

    def test_dates_are_checked(self):
        wizard = self._wizard(date_from='2026-02-01', date_to='2026-01-31')
        for method in ('action_view_report', 'action_export_xlsx', 'action_export_pdf_rl', 'action_export_xml'):
            with self.assertRaises(UserError, msg=method):
                getattr(wizard, method)()

    def test_custom_comparison_is_checked(self):
        with self.assertRaises(UserError):
            self._wizard(comparison_type='custom').action_view_report()
        with self.assertRaises(UserError):
            self._wizard(
                comparison_type='custom',
                comparison_date_from='2025-02-01', comparison_date_to='2025-01-01',
            ).action_view_report()

    def test_form(self):
        with Form(self.Wizard) as form:
            form.comparison_type = 'custom'
            form.comparison_date_from = '2025-01-01'
            form.comparison_date_to = '2025-01-31'
            form.hierarchy = True
            form.account_ids.add(self.accounts['1111'])
        wizard = form.record
        self.assertEqual(wizard._get_report_options()['comparison_date_to'], '2025-01-31')
        self.assertEqual(wizard.account_ids, self.accounts['1111'])
