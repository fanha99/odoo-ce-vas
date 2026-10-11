from odoo.tests import tagged

from .common import S03aCommon


@tagged('post_install', '-at_install')
class TestS03aTransfer(S03aCommon):
    """ Entries meeting on a hidden transfer account are shown as one
    operation (readme, section 3). """

    def test_setting_off_shows_the_four_items(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        summary = self._summary()
        self.assertEqual(len(summary), 4)
        self.assertEqual({name for name, *_rest in summary}, {cash_move.name, bank_move.name})
        self.assertIn(self.transfer.code, {code for _name, code, *_rest in summary})

    def test_deposit_is_shown_as_one_operation(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        self._hide_transfer_account()
        name = f"{bank_move.name} ({cash_move.name})"
        # the bank entry first, the items on the transfer account are gone
        self.assertEqual(self._summary(), [
            (name, self.bank.code, 100, 0),
            (name, self.cash.code, 0, 100),
        ])
        lines = self._lines()
        self.assertEqual([line['description'] for line in lines], ["Received", "Deposit"])
        self.assertEqual([line['move_id'] for line in lines], [bank_move.id, cash_move.id])
        self.assertEqual(self._group()['total'], {'debit': 100, 'credit': 100})

    def test_item_not_reconciled_stays(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100, reconcile=False)
        self._hide_transfer_account()
        summary = self._summary()
        self.assertEqual(len(summary), 4)
        self.assertEqual({name for name, *_rest in summary}, {cash_move.name, bank_move.name})

    def test_several_cash_entries_for_one_bank_entry(self):
        first = self._post('2026-01-10', [(self.transfer, 100, 0), (self.cash, 0, 100)], journal=self.cash_journal)
        second = self._post('2026-01-10', [(self.transfer, 50, 0), (self.cash, 0, 50)], journal=self.cash_journal)
        bank_move = self._post('2026-01-10', [(self.bank, 150, 0), (self.transfer, 0, 150)], journal=self.bank_journal)
        (first + second + bank_move).line_ids.filtered(
            lambda line: line.account_id == self.transfer).reconcile()
        self._hide_transfer_account()

        name = f"{bank_move.name} ({first.name}, {second.name})"
        self.assertEqual(self._summary(), [
            (name, self.bank.code, 150, 0),
            (name, self.cash.code, 0, 100),
            (name, self.cash.code, 0, 50),
        ])

    def test_pair_stays_together_among_other_entries(self):
        before = self._post('2026-01-10', [('642', 5, 0), (self.cash, 0, 5)])
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        after = self._post('2026-01-10', [('642', 6, 0), (self.cash, 0, 6)])
        self._hide_transfer_account()
        move_ids = [line['move_id'] for line in self._lines()]
        position = move_ids.index(bank_move.id)
        self.assertEqual(move_ids[position + 1], cash_move.id)
        self.assertIn(before.id, move_ids)
        self.assertIn(after.id, move_ids)

    def test_entries_on_different_days_stay_on_their_day(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100, bank_date='2026-01-12')
        between = self._post('2026-01-11', [('642', 5, 0), (self.cash, 0, 5)])
        self._hide_transfer_account()
        name = f"{cash_move.name} ({bank_move.name})"
        self.assertEqual(
            [(line['move_id'], line['move_name']) for line in self._lines()],
            [
                (cash_move.id, name),
                (between.id, between.name), (between.id, between.name),
                (bank_move.id, name),
            ],
        )

    def test_linked_entry_out_of_the_period(self):
        cash_move, bank_move = self._deposit('2026-01-31', 100, bank_date='2026-02-02')
        self._hide_transfer_account()
        name = f"{cash_move.name} ({bank_move.name})"
        self.assertEqual(self._summary(), [(name, self.cash.code, 0, 100)])
        # half of the operation is in the period: debit and credit differ
        self.assertEqual(self._group()['total'], {'debit': 0, 'credit': 100})

    def test_name_is_kept_when_the_hidden_items_are_filtered_out(self):
        cash_move, bank_move = self._deposit('2026-01-10', 100)
        self._hide_transfer_account()
        name = f"{bank_move.name} ({cash_move.name})"
        self.assertEqual(self._summary(account_ids=self.bank.ids), [(name, self.bank.code, 100, 0)])

    def test_two_hidden_accounts(self):
        outstanding = self.env['account.account'].create({
            'code': '1131', 'name': "Outstanding Receipts", 'account_type': 'asset_current', 'reconcile': True,
        })
        self._deposit('2026-01-10', 100)
        receipt = self._post('2026-01-15', [(outstanding, 30, 0), ('131', 0, 30)])
        statement = self._post('2026-01-15', [(self.bank, 30, 0), (outstanding, 0, 30)], journal=self.bank_journal)
        (receipt + statement).line_ids.filtered(lambda line: line.account_id == outstanding).reconcile()
        self._hide_transfer_account(self.transfer + outstanding)

        summary = self._summary()
        self.assertEqual(len(summary), 4)
        self.assertNotIn('1131', {code for _name, code, *_rest in summary})
        name = f"{statement.name} ({receipt.name})"
        self.assertEqual(summary[2:], [(name, self.bank.code, 30, 0), (name, '131', 0, 30)])
