from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestS03bUi(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env['account.account']
        cls.receivable = Account.create({
            'code': 'FGT131', 'name': "FGT Receivable", 'account_type': 'asset_receivable', 'reconcile': True,
        })
        cls.income = Account.create({'code': 'FGT511', 'name': "FGT Income", 'account_type': 'income'})
        cls.vat = Account.create({'code': 'FGT3331', 'name': "FGT VAT", 'account_type': 'liability_current'})
        cls.today = fields.Date.context_today(cls.env.user)
        cls.journal = cls.company_data['default_journal_misc']
        # the current quarter is the default period of the wizard
        cls._entries(3, "FGT Sale")

    @classmethod
    def _entries(cls, count, label):
        cls.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': cls.today,
                'journal_id': cls.journal.id,
                'line_ids': [
                    Command.create({'account_id': cls.receivable.id, 'name': f"{label} {index}", 'debit': 110}),
                    Command.create({'account_id': cls.income.id, 'name': f"{label} {index}", 'credit': 100}),
                    Command.create({'account_id': cls.vat.id, 'name': f"{label} {index}", 'credit': 10}),
                ],
            }
            for index in range(count)
        ]).action_post()

    def test_s03b_report_tour(self):
        self.start_tour(
            '/odoo/action-fg_vn_report_s03b.action_vn_report_s03b_wizard',
            'fg_vn_report_s03b_tour',
            login=self.env.user.login,
        )

    def test_s03b_lazy_report_tour(self):
        """ A ledger over the threshold comes folded and loads the journal
        items of an account when it is unfolded. """
        self._entries(12, "FGT Bulk")   # 15 entries, 45 lines
        set_param = self.env['ir.config_parameter'].sudo().set_int
        set_param('fg_vn_accounting_reports.lazy_line_threshold', 10)
        set_param('fg_vn_accounting_reports.lazy_chunk_size', 10)
        self.start_tour(
            '/odoo/action-fg_vn_report_s03b.action_vn_report_s03b_wizard',
            'fg_vn_report_s03b_lazy_tour',
            login=self.env.user.login,
        )
