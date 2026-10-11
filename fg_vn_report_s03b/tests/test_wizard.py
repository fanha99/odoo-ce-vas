import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from freezegun import freeze_time

from odoo.tests import Form, new_test_user, tagged

from .common import S03bCommon


@tagged('post_install', '-at_install')
class TestS03bWizard(S03bCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = new_test_user(
            cls.env, login='fg_s03b_accountant', groups='account.group_account_user',
        )
        cls.Wizard = cls.env['vn.report.s03b.wizard'].with_user(cls.accountant)

    @freeze_time('2026-05-20')
    def test_defaults(self):
        wizard = self.Wizard.create({})
        self.assertEqual((wizard.date_from, wizard.date_to), (date(2026, 4, 1), date(2026, 6, 30)))
        self.assertEqual(wizard.orientation, 'portrait')
        self.assertEqual(wizard.account_type, 'all')
        self.assertEqual(wizard.empty_accounts, 'hide')
        self.assertFalse(wizard.split_counterparts)

    def test_options(self):
        wizard = self.Wizard.create({
            'date_from': '2026-01-01', 'date_to': '2026-01-31', 'report_lang': 'en_US',
            'account_ids': self.accounts['131'].ids,
            'account_type': 'asset',
            'partner_ids': self.partner_a.ids,
            'journal_ids': self.bank_journal.ids,
            'empty_accounts': 'with_balance',
            'split_counterparts': True,
        })
        options = wizard._get_report_options()
        self.assertEqual(options['account_ids'], self.accounts['131'].ids)
        self.assertEqual(options['account_type'], 'asset')
        self.assertEqual(options['partner_ids'], self.partner_a.ids)
        self.assertEqual(options['journal_ids'], self.bank_journal.ids)
        self.assertEqual(options['empty_accounts'], 'with_balance')
        self.assertTrue(options['split_counterparts'])
        self.assertNotIn('show_zero_balance', options)

        action = wizard.action_view_report()
        self.assertEqual(action['tag'], 'vn_report_s03b')
        self.assertEqual(action['name'], "General Ledger")
        for method, export_format in (('action_export_xlsx', 'xlsx'), ('action_export_pdf_rl', 'pdf_rl')):
            url = urlparse(getattr(wizard, method)()['url'])
            self.assertEqual(url.path, f'/vn_report/vn.report.s03b/export/{export_format}')
            self.assertEqual(json.loads(parse_qs(url.query)['options'][0]), options)

    def test_options_open_the_report(self):
        wizard = self.Wizard.create({'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        data = self.env['vn.report.s03b'].with_user(self.accountant).get_report_data(
            wizard._get_report_options())
        self.assertIn('131', [group['code'] for group in data['lines']])

    def test_form(self):
        with Form(self.Wizard) as form:
            form.empty_accounts = 'all'
            form.split_counterparts = True
            form.account_ids.add(self.accounts['131'])
        options = form.record._get_report_options()
        self.assertEqual(options['empty_accounts'], 'all')
        self.assertTrue(options['split_counterparts'])
