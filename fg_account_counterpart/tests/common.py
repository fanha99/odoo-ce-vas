from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class CounterpartCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data['default_journal_misc']

    @classmethod
    def _create_account(cls, code, account_type='asset_current'):
        return cls.env['account.account'].create({
            'code': code,
            'name': f"Test {code}",
            'account_type': account_type,
        })

    @classmethod
    def _create_entry(cls, lines, post=True):
        """ Create a miscellaneous entry.

        :param lines: list of (account, debit, credit)
        """
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.journal.id,
            'date': '2026-01-15',
            'line_ids': [
                Command.create({'account_id': account.id, 'debit': debit, 'credit': credit})
                for account, debit, credit in lines
            ],
        })
        if post:
            move.action_post()
        return move

    def assertCounterparts(self, move, expected):
        """ Check the counterparts of `move`.

        :param expected: list of (debit account code, credit account code, amount)
        """
        counterparts = self.env['account.move.line.ctp'].search([('move_id', '=', move.id)])
        self.assertCountEqual(
            [(ctp.dr_account_id.code, ctp.cr_account_id.code, ctp.countered_amt) for ctp in counterparts],
            expected,
        )
