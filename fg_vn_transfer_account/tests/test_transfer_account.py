from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestTransferAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.transfer_account = cls.company.transfer_account_id
        cls.other_account = cls.env['account.account'].create({
            'code': 'FGT1131',
            'name': "Outstanding Receipts (test)",
            'account_type': 'asset_current',
            'reconcile': True,
        })

    def test_setting_off_returns_nothing(self):
        self.company.fg_hidden_transfer_account_ids = self.transfer_account
        self.assertFalse(self.company.fg_hide_transfer_account)
        self.assertFalse(self.company._fg_get_hidden_transfer_accounts())

    def test_setting_on_returns_selected_accounts(self):
        accounts = self.transfer_account + self.other_account
        self.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': accounts.ids,
        })
        self.assertEqual(self.company._fg_get_hidden_transfer_accounts(), accounts)

    def test_setting_on_without_account_returns_nothing(self):
        self.company.fg_hide_transfer_account = True
        self.assertFalse(self.company._fg_get_hidden_transfer_accounts())

    def test_setting_is_per_company(self):
        other_company = self.setup_other_company()['company']
        self.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': self.transfer_account.ids,
        })
        self.assertFalse(other_company.fg_hide_transfer_account)
        self.assertFalse(other_company._fg_get_hidden_transfer_accounts())

    def test_account_of_another_company_is_rejected(self):
        other_company = self.setup_other_company()['company']
        with self.assertRaises(UserError):
            self.company.fg_hidden_transfer_account_ids = other_company.transfer_account_id

    def test_settings_form_prefills_transfer_account(self):
        self.assertTrue(self.transfer_account)
        with Form(self.env['res.config.settings']) as settings:
            self.assertFalse(settings.fg_hidden_transfer_account_ids[:])
            settings.fg_hide_transfer_account = True
            self.assertEqual(settings.fg_hidden_transfer_account_ids[:], self.transfer_account)
            settings.fg_hidden_transfer_account_ids.add(self.other_account)
        settings.record.execute()
        self.assertTrue(self.company.fg_hide_transfer_account)
        self.assertEqual(
            self.company._fg_get_hidden_transfer_accounts(),
            self.transfer_account + self.other_account,
        )

    def test_settings_form_keeps_existing_selection(self):
        self.company.fg_hidden_transfer_account_ids = self.other_account
        with Form(self.env['res.config.settings']) as settings:
            settings.fg_hide_transfer_account = True
            self.assertEqual(settings.fg_hidden_transfer_account_ids[:], self.other_account)

    def test_fill_hidden_transfer_accounts(self):
        """ Upgrade from 19.0: the setting is on and no account is selected. """
        other_company = self.setup_other_company()['company']
        self.company.fg_hide_transfer_account = True
        companies = self.company + other_company
        companies._fg_fill_hidden_transfer_accounts()
        self.assertEqual(self.company.fg_hidden_transfer_account_ids, self.transfer_account)
        self.assertFalse(other_company.fg_hidden_transfer_account_ids)

        # an existing selection is left untouched
        self.company.fg_hidden_transfer_account_ids = self.other_account
        companies._fg_fill_hidden_transfer_accounts()
        self.assertEqual(self.company.fg_hidden_transfer_account_ids, self.other_account)
