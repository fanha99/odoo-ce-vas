import csv

from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.models.chart_template import TEMPLATE_DATA_KEYS
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

# res.company fields of modules l10n_vn_tt133 does not depend on
OPTIONAL_COMPANY_FIELDS = {
    'deferred_expense_account_id', 'deferred_revenue_account_id', 'account_production_wip_account_id',
}

# code of each summary account: codes of its children (PLAN.md section 3.1)
SUMMARY_ACCOUNTS = {
    '111': {'1111', '1112'},
    '112': {'1121', '1122'},
    '128': {'1281', '1288'},
    '133': {'1331', '1332'},
    '136': {'1361', '1368'},
    '138': {'1381', '1386', '1388'},
    '211': {'2111', '2112', '2113'},
    '214': {'2141', '2142', '2143', '2147'},
    '228': {'2281', '2288'},
    '229': {'2291', '2292', '2293', '2294'},
    '241': {'2411', '2412', '2413'},
    '333': {'3331', '3332', '3333', '3334', '3335', '3336', '3337', '3338', '3339'},
    '3331': {'33311', '33312'},
    '3338': {'33381', '33382'},
    '336': {'3361', '3368'},
    '338': {'3381', '3382', '3383', '3384', '3385', '3386', '3387', '3388'},
    '341': {'3411', '3412'},
    '352': {'3521', '3522', '3524'},
    '353': {'3531', '3532', '3533', '3534'},
    '356': {'3561', '3562'},
    '411': {'4111', '4112', '4118'},
    '421': {'4211', '4212'},
    '511': {'5111', '5112', '5113', '5118'},
    '642': {'6421', '6422'},
}


@tagged('post_install', '-at_install')
class TestChartVnTT133(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('vn')
    @AccountTestInvoicingCommon.setup_chart_template('vn_tt133')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']

    def account(self, code, company=None):
        company = company or self.company
        account = self.env['account.account'].with_company(company).search([
            *self.env['account.account']._check_company_domain(company),
            ('code', '=', code),
        ])
        self.assertEqual(len(account), 1, f"one account {code} expected")
        return account

    def ref(self, xmlid, company=None):
        return self.env['account.chart.template'].with_company(company or self.company).ref(xmlid)

    def test_template_keys(self):
        """No key of the template is silently dropped by the loader."""
        data = self.env['account.chart.template']._get_chart_template_data('vn_tt133')
        self.assertLessEqual(set(data['template_data']), TEMPLATE_DATA_KEYS)
        company_keys = set(next(iter(data['res.company'].values()))) - {'__translation_module__'}
        self.assertLessEqual(company_keys - set(self.env['res.company']._fields), OPTIONAL_COMPANY_FIELDS)

    def test_load_on_new_company(self):
        company = self.env['res.company'].create({'name': 'TT133 new', 'country_id': self.env.ref('base.vn').id})
        self.env['account.chart.template'].try_loading('vn_tt133', company, install_demo=False)
        self.assertEqual(company.chart_template, 'vn_tt133')
        self.assertEqual(self.account('131', company).account_type, 'asset_receivable')
        # the taxes of l10n_vn, nothing more (no 5% import duty)
        with file_open('l10n_vn/data/template/account.tax-vn.csv') as f:
            vn_tax_xmlids = {row['id'] for row in csv.DictReader(f) if row['id']}
        taxes = self.env['account.tax'].with_context(active_test=False).search([('company_id', '=', company.id)])
        self.assertEqual(taxes, self.env['account.tax'].union(*(self.ref(xmlid, company) for xmlid in vn_tax_xmlids)))
        self.assertEqual(taxes.repartition_line_ids.account_id, self.account('1331', company) | self.account('33311', company))

    def test_codes_not_padded(self):
        codes = set(self.env['account.account'].search(
            self.env['account.account']._check_company_domain(self.company)).mapped('code'))
        for code in ('131', '911', '03', '031', '032', '021', '33311'):
            self.assertIn(code, codes)
        self.assertNotIn('1310', codes)
        self.assertNotIn('030', codes)

    def test_summary_accounts(self):
        for parent_code, child_codes in SUMMARY_ACCOUNTS.items():
            parent = self.account(parent_code)
            if len(parent_code) == 3:
                self.assertFalse(parent.parent_id, parent_code)
            for child_code in child_codes:
                self.assertEqual(self.account(child_code).parent_id, parent, child_code)
        self.assertEqual(self.account('3331').parent_id, self.account('333'))
        self.assertEqual(
            self.account('33311').parent_ids,
            self.account('333') | self.account('3331') | self.account('33311'),
        )
        # summary accounts holding receivables and payables are not reconcilable
        for code in ('136', '138', '336', '338'):
            self.assertFalse(self.account(code).reconcile, code)
            self.assertIn(self.account(code).account_type, ('asset_current', 'liability_current'))

    def test_technical_accounts(self):
        company = self.company
        transfer, receipts, payments, suspense = (self.account(code) for code in ('03', '031', '032', '021'))
        self.assertEqual(company.transfer_account_id, transfer)
        self.assertEqual(company.account_journal_suspense_account_id, suspense)
        self.assertEqual(self.ref('account_journal_payment_debit_account_id'), receipts)
        self.assertEqual(self.ref('account_journal_payment_credit_account_id'), payments)
        for account in (transfer, receipts, payments, suspense):
            self.assertFalse(account.parent_id, account.code)
            self.assertEqual(account.account_type, 'asset_current', account.code)
        self.assertTrue(transfer.reconcile)
        self.assertFalse(suspense.reconcile)

        bank_journal = self.company_data['default_journal_bank']
        self.assertEqual(bank_journal.default_account_id, self.account('1121'))
        self.assertEqual(bank_journal.suspense_account_id, suspense)
        self.assertNotEqual(bank_journal.suspense_account_id, bank_journal.default_account_id)

    def test_new_liquidity_journals(self):
        """New bank/cash accounts get a 4-digit code under 112/111 (not 12, 13...)."""
        # the test setup has already created a cash journal and a credit card
        # journal (bank prefix): 1113 and 1123 are taken
        self.assertEqual(self.company_data['default_journal_cash'].default_account_id.code, '1113')
        bank = self.env['account.journal'].create({'name': 'Bank 2', 'type': 'bank', 'code': 'BNK2', 'company_id': self.company.id})
        self.assertEqual(bank.default_account_id.code, '1124')
        self.assertEqual(bank.default_account_id.parent_id, self.account('112'))
        cash = self.env['account.journal'].create({'name': 'Cash 2', 'type': 'cash', 'code': 'CSH2', 'company_id': self.company.id})
        self.assertEqual(cash.default_account_id.code, '1114')
        self.assertEqual(cash.default_account_id.parent_id, self.account('111'))
        # the technical accounts stay out of 112
        self.assertFalse(self.account('021').parent_id)

    def test_company_defaults(self):
        company = self.company
        self.assertFalse(company.anglo_saxon_accounting)
        self.assertEqual(company.receivable_account_id, self.account('131'))
        self.assertEqual(company.payable_account_id, self.account('331'))
        self.assertEqual(company.income_account_id, self.account('5111'))
        self.assertEqual(company.expense_account_id, self.account('6421'))
        self.assertEqual(company.account_stock_valuation_id, self.account('156'))
        self.assertEqual(company.account_sale_tax_id, self.ref('tax_sale_vat10'))
        self.assertEqual(company.account_purchase_tax_id, self.ref('tax_purchase_vat10'))
        for code in ('152', '153', '155', '156'):
            self.assertEqual(self.account(code).account_stock_variation_id, self.account('632'), code)

    def test_vat_on_invoices(self):
        bill = self.init_invoice('in_invoice', taxes=self.ref('tax_purchase_vat10'), amounts=[1000.0], post=True)
        tax_line = bill.line_ids.filtered('tax_line_id')
        self.assertEqual(tax_line.account_id, self.account('1331'))
        self.assertEqual(tax_line.debit, 100.0)
        self.assertIn('MHND_VAT_10', tax_line.tax_tag_ids.mapped('name')[0])
        base_line = bill.invoice_line_ids
        self.assertIn('MHND_NET_10', base_line.tax_tag_ids.mapped('name')[0])

        invoice = self.init_invoice('out_invoice', taxes=self.ref('tax_sale_vat10'), amounts=[1000.0], post=True)
        tax_line = invoice.line_ids.filtered('tax_line_id')
        self.assertEqual(tax_line.account_id, self.account('33311'))
        self.assertEqual(tax_line.credit, 100.0)

        # imported VAT: the line amount is the customs value, only the VAT is due
        bill = self.init_invoice('in_invoice', taxes=self.ref('tax_purchase_import_vat10'), amounts=[1000.0], post=True)
        self.assertEqual(bill.amount_total, 100.0)
        vat_line = bill.line_ids.filtered(lambda line: line.account_id == self.account('1331'))
        self.assertEqual(vat_line.debit, 100.0)

    def test_tax_accounts_exist_in_tt133_chart(self):
        """Every account the l10n_vn taxes point to has a TT133 counterpart of the same code."""
        with file_open('l10n_vn/data/template/account.tax-vn.csv') as f:
            vn_accounts = {row['repartition_line_ids/account_id'] for row in csv.DictReader(f)} - {''}
        with file_open('l10n_vn/data/template/account.account-vn.csv') as f:
            vn_codes = {row['id']: row['code'] for row in csv.DictReader(f)}
        with file_open('l10n_vn_tt133/data/template/account.account-vn_tt133.csv') as f:
            tt133_codes = {row['id']: row['code'] for row in csv.DictReader(f)}
        for xmlid in vn_accounts:
            self.assertEqual(tt133_codes.get(f'vn133_{xmlid}'), vn_codes[xmlid], xmlid)
