from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCDPSUi(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('vi_VN')
        Account = cls.env['account.account']
        cash = Account.create({'code': '111', 'name': "FGT Cash", 'account_type': 'asset_cash'})
        cash.with_context(lang='vi_VN').name = "FGT Tiền mặt"
        cash_vnd = Account.create({
            'code': '1111', 'name': "FGT Cash VND", 'account_type': 'asset_cash', 'parent_id': cash.id,
        })
        equity = Account.create({'code': '411', 'name': "FGT Equity", 'account_type': 'equity'})
        expense = Account.create({'code': '642', 'name': "FGT Expense", 'account_type': 'expense'})

        today = fields.Date.context_today(cls.env.user)
        for debit_account, credit_account, amount in (
            (cash_vnd, equity, 1000),
            (cash, equity, 50),
            (expense, cash_vnd, 300),
        ):
            cls.env['account.move'].create({
                'move_type': 'entry',
                'date': today,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'line_ids': [
                    Command.create({'account_id': debit_account.id, 'debit': amount}),
                    Command.create({'account_id': credit_account.id, 'credit': amount}),
                ],
            }).action_post()

    def test_cdps_report_tour(self):
        self.start_tour(
            '/odoo/action-fg_vn_report_cdps.action_vn_report_cdps_wizard',
            'fg_vn_report_cdps_tour',
            login=self.env.user.login,
        )
