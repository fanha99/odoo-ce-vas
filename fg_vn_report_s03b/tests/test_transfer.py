from odoo.tests import tagged

from .common import S03bCommon


@tagged('post_install', '-at_install')
class TestS03bTransfer(S03bCommon):
    """ Hidden transfer accounts: the ledgers show the account at the other
    end of the transfer (readme, section 4). """

    def _deposit_lines(self, account, moves, **options):
        move_ids = moves.ids
        return [
            (line['move_name'], line['counterpart_account'], line['debit'], line['credit'])
            for line in self._ledger(account, **options)['lines']
            if line['move_id'] in move_ids
        ]

    def test_setting_off_shows_the_transfer_account(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        self.assertEqual(
            self._deposit_lines(self.cash, cash_move), [(cash_move.name, self.transfer.code, 0, 100)])
        self.assertEqual(
            self._deposit_lines(self.bank, bank_move), [(bank_move.name, self.transfer.code, 100, 0)])
        # the transfer account has its ledger, though it is back to zero
        self.assertEqual(len(self._ledger(self.transfer)['lines']), 2)

    def test_real_counterpart_on_both_ends(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        self._hide_transfer_account()
        name = f"{bank_move.name} ({cash_move.name})"
        self.assertEqual(self._deposit_lines(self.cash, cash_move), [(name, self.bank.code, 0, 100)])
        self.assertEqual(self._deposit_lines(self.bank, bank_move), [(name, self.cash.code, 100, 0)])

    def test_hidden_account_has_no_ledger_when_back_to_zero(self):
        self._deposit('2026-01-10', 100)
        self._hide_transfer_account()
        self.assertNotIn(self.transfer.code, self._groups())
        self.assertNotIn(self.transfer.code, self._groups(empty_accounts='all'))
        # unless the user asks for that account
        self.assertEqual(len(self._ledger(self.transfer, account_ids=self.transfer.ids)['lines']), 2)

    def test_item_not_reconciled_keeps_the_transfer_account(self):
        cash_move, _bank_move = self._deposit('2026-01-10', 100, reconcile=False)
        self._hide_transfer_account()
        self.assertEqual(
            self._deposit_lines(self.cash, cash_move), [(cash_move.name, self.transfer.code, 0, 100)])

    def test_pending_transfer_keeps_the_ledger_of_the_hidden_account(self):
        """ Money left the cash box and has not reached the bank yet. """
        cash_move = self._post('2026-01-10', [
            (self.transfer, 100, 0), (self.cash, 0, 100),
        ], journal=self.cash_journal)
        self._hide_transfer_account()
        ledger = self._ledger(self.transfer)
        self.assertEqual(ledger['closing'], {'debit': 100, 'credit': 0})
        self.assertEqual([line['move_id'] for line in ledger['lines']], [cash_move.id])

    def test_several_cash_entries_for_one_bank_entry(self):
        """ The real counterpart of a cash entry is the bank account, not the
        cash account of the other cash entry merged into the same deposit. """
        first = self._post('2026-01-10', [(self.transfer, 100, 0), (self.cash, 0, 100)], journal=self.cash_journal)
        second = self._post('2026-01-10', [(self.transfer, 50, 0), (self.cash, 0, 50)], journal=self.cash_journal)
        bank_move = self._post('2026-01-10', [(self.bank, 150, 0), (self.transfer, 0, 150)], journal=self.bank_journal)
        moves = first + second + bank_move
        moves.line_ids.filtered(lambda line: line.account_id == self.transfer).reconcile()
        self._hide_transfer_account()

        name = f"{bank_move.name} ({first.name}, {second.name})"
        self.assertEqual(self._deposit_lines(self.cash, first + second), [
            (name, self.bank.code, 0, 100),
            (name, self.bank.code, 0, 50),
        ])
        self.assertEqual(self._deposit_lines(self.bank, bank_move), [(name, self.cash.code, 150, 0)])

    def test_other_counterparts_are_kept(self):
        """ An entry with a transfer item and another counterpart. """
        cash_move = self._post('2026-01-10', [
            (self.transfer, 100, 0), ('642', 20, 0), (self.cash, 0, 120),
        ], journal=self.cash_journal)
        bank_move = self._post('2026-01-10', [
            (self.bank, 100, 0), (self.transfer, 0, 100),
        ], journal=self.bank_journal)
        (cash_move + bank_move).line_ids.filtered(lambda line: line.account_id == self.transfer).reconcile()
        self._hide_transfer_account()
        counterparts = self._deposit_lines(self.cash, cash_move)[0][1]
        self.assertEqual(counterparts, ', '.join(sorted([self.bank.code, '642'])))

    def test_split_counterparts_with_a_hidden_account(self):
        cash_move = self._post('2026-01-10', [
            (self.transfer, 100, 0), ('642', 20, 0), (self.cash, 0, 120),
        ], journal=self.cash_journal)
        bank_move = self._post('2026-01-10', [
            (self.bank, 100, 0), (self.transfer, 0, 100),
        ], journal=self.bank_journal)
        (cash_move + bank_move).line_ids.filtered(lambda line: line.account_id == self.transfer).reconcile()
        self._hide_transfer_account()
        lines = self._deposit_lines(self.cash, cash_move, split_counterparts=True)
        self.assertEqual(
            sorted((counterpart, credit) for _name, counterpart, _debit, credit in lines),
            sorted([(self.bank.code, 100), ('642', 20)]),
        )

    def test_two_hidden_accounts(self):
        outstanding = self.env['account.account'].create({
            'code': '1131', 'name': "Outstanding Receipts", 'account_type': 'asset_current', 'reconcile': True,
        })
        receipt = self._post('2026-01-15', [
            (outstanding, 30, 0), ('131', 0, 30, {'partner_id': self.partner_a.id}),
        ])
        statement = self._post('2026-01-15', [
            (self.bank, 30, 0), (outstanding, 0, 30),
        ], journal=self.bank_journal)
        (receipt + statement).line_ids.filtered(lambda line: line.account_id == outstanding).reconcile()
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        self._hide_transfer_account(self.transfer + outstanding)

        name = f"{statement.name} ({receipt.name})"
        self.assertEqual(self._deposit_lines('131', receipt), [(name, self.bank.code, 0, 30)])
        self.assertEqual(self._deposit_lines(self.bank, statement), [(name, '131', 30, 0)])
        self.assertEqual(
            self._deposit_lines(self.bank, bank_move),
            [(f"{bank_move.name} ({cash_move.name})", self.cash.code, 100, 0)],
        )
        self.assertNotIn('1131', self._groups())
