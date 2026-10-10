from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

ACCOUNT_TYPES = {
    '1': 'asset_current',
    '2': 'asset_non_current',
    '3': 'liability_current',
    '5': 'income',
    '6': 'expense',
}


ACCOUNT_CODES = [
    '111', '112', '131', '1331', '153', '156', '242',
    '331', '33311', '3383', '3384', '3386', '3388',
    '511', '515', '627', '632', '6411', '6421', '6427',
]


class CounterpartCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data['default_journal_misc']
        cls.currency = cls.company_data['currency']
        accounts = cls.env['account.account'].create([
            {
                'code': f"CTP{code}",
                'name': f"Test {code}",
                'account_type': ACCOUNT_TYPES[code[0]],
            }
            for code in ACCOUNT_CODES
        ])
        cls.accounts = dict(zip(ACCOUNT_CODES, accounts))

    @classmethod
    def _account(cls, code):
        """ Return the test account with the given Vietnamese account number. """
        return cls.accounts[code]

    @classmethod
    def _create_entry(cls, lines, post=True):
        """ Create a miscellaneous entry.

        :param lines: list of (account number, debit, credit[, partner]); the
            journal items are created in that order, hence with ascending ids
        """
        line_vals = []
        for code, debit, credit, *partner in lines:
            line_vals.append(Command.create({
                'account_id': cls._account(code).id,
                'partner_id': partner[0].id if partner else False,
                'debit': debit,
                'credit': credit,
            }))
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.journal.id,
            'date': '2026-01-15',
            'line_ids': line_vals,
        })
        if post:
            move.action_post()
        return move

    @classmethod
    def _line(cls, move, code):
        """ Return the journal item of `move` on the given account number. """
        return move.line_ids.filtered(lambda line: line.account_id == cls._account(code))

    def _counterparts(self, move):
        return self.env['account.move.line.ctp'].search([('move_id', '=', move.id)])

    def assertCounterparts(self, move, expected):
        """ Check the counterparts of `move`.

        :param expected: list of (debit account number, credit account number, amount)
        """
        self.assertCountEqual(
            [
                (ctp.dr_account_id.code[3:], ctp.cr_account_id.code[3:], ctp.countered_amt)
                for ctp in self._counterparts(move)
            ],
            expected,
        )
