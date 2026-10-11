from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestS03aUi(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env['account.account']
        cls.receivable = Account.create({
            'code': 'FGT131', 'name': "FGT Receivable", 'account_type': 'asset_receivable', 'reconcile': True,
        })
        cls.income = Account.create({'code': 'FGT511', 'name': "FGT Income", 'account_type': 'income'})
        cls.today = fields.Date.context_today(cls.env.user)
        cls.journal = cls.company_data['default_journal_misc']
        # the current quarter is the default period of the wizard
        cls._entries(4, "FGT Sale")

    @classmethod
    def _entries(cls, count, label):
        cls.env['account.move'].create([
            {
                'move_type': 'entry',
                'date': cls.today,
                'journal_id': cls.journal.id,
                'line_ids': [
                    Command.create({'account_id': cls.receivable.id, 'name': f"{label} {index}", 'debit': 100 + index}),
                    Command.create({'account_id': cls.income.id, 'name': f"{label} {index}", 'credit': 100 + index}),
                ],
            }
            for index in range(count)
        ]).action_post()

    def test_s03a_report_tour(self):
        self.start_tour(
            '/odoo/action-fg_vn_report_s03a.action_vn_report_s03a_wizard',
            'fg_vn_report_s03a_tour',
            login=self.env.user.login,
        )

    def test_s03a_lazy_report_tour(self):
        """ A journal over the threshold is loaded by chunks. """
        self._entries(12, "FGT Bulk")   # 32 lines in all
        set_param = self.env['ir.config_parameter'].sudo().set_int
        set_param('fg_vn_accounting_reports.lazy_line_threshold', 10)
        set_param('fg_vn_accounting_reports.lazy_chunk_size', 10)
        self.start_tour(
            '/odoo/action-fg_vn_report_s03a.action_vn_report_s03a_wizard',
            'fg_vn_report_s03a_lazy_tour',
            login=self.env.user.login,
        )
