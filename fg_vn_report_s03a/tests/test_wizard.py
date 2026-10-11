import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, new_test_user, tagged

from .common import S03aCommon


@tagged('post_install', '-at_install')
class TestS03aWizard(S03aCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = new_test_user(
            cls.env, login='fg_s03a_accountant', groups='account.group_account_user',
        )
        cls.Wizard = cls.env['vn.report.s03a.wizard'].with_user(cls.accountant)

    @freeze_time('2026-05-20')
    def test_defaults(self):
        wizard = self.Wizard.create({})
        self.assertEqual((wizard.date_from, wizard.date_to), (date(2026, 4, 1), date(2026, 6, 30)))
        self.assertEqual(wizard.orientation, 'portrait')
        self.assertEqual(wizard.move_type, 'all')
        self.assertFalse(wizard.journal_ids)

    def test_options(self):
        wizard = self.Wizard.create({
            'date_from': '2026-01-01', 'date_to': '2026-01-31', 'report_lang': 'en_US',
            'journal_ids': self.bank_journal.ids,
            'account_ids': self.accounts['131'].ids,
            'partner_ids': self.partner_a.ids,
            'move_type': 'entry',
        })
        options = wizard._get_report_options()
        self.assertEqual(options['journal_ids'], self.bank_journal.ids)
        self.assertEqual(options['account_ids'], self.accounts['131'].ids)
        self.assertEqual(options['partner_ids'], self.partner_a.ids)
        self.assertEqual(options['move_type'], 'entry')
        self.assertEqual(options['lang'], 'en_US')

        action = wizard.action_view_report()
        self.assertEqual(action['tag'], 'vn_report_s03a')
        self.assertEqual(action['name'], "General Journal")
        self.assertTrue(action['context']['report_token'])

        for method, export_format in (('action_export_xlsx', 'xlsx'), ('action_export_pdf_rl', 'pdf_rl')):
            url = urlparse(getattr(wizard, method)()['url'])
            self.assertEqual(url.path, f'/vn_report/vn.report.s03a/export/{export_format}')
            self.assertEqual(json.loads(parse_qs(url.query)['options'][0]), options)

    def test_options_open_the_report(self):
        self._post('2026-01-05', [('131', 110, 0), ('511', 0, 110)])
        wizard = self.Wizard.create({'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        data = self.env['vn.report.s03a'].with_user(self.accountant).get_report_data(
            wizard._get_report_options())
        self.assertEqual(len(data['lines'][0]['lines']), 2)

    def test_dates_are_checked(self):
        wizard = self.Wizard.create({'date_from': '2026-02-01', 'date_to': '2026-01-31'})
        with self.assertRaises(UserError):
            wizard.action_view_report()

    def test_form(self):
        with Form(self.Wizard) as form:
            form.move_type = 'out_invoice'
            form.journal_ids.add(self.bank_journal)
        self.assertEqual(form.record._get_report_options()['move_type'], 'out_invoice')
