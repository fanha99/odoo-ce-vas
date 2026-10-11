from datetime import date

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTransferLinks(AccountTestInvoicingCommon):
    """ `account.move._fg_get_transfer_links()`: how the accounting books
    present the entries meeting on a hidden transfer account. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.cash_journal = cls.company_data['default_journal_cash']
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.cash = cls.cash_journal.default_account_id
        cls.bank = cls.bank_journal.default_account_id
        cls.transfer = cls.company.transfer_account_id
        cls.expense = cls.company_data['default_account_expense']
        cls.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': cls.transfer.ids,
        })

    def _entry(self, journal, debit_account, credit_account, amount=100, day='2026-01-10'):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': day,
            'journal_id': journal.id,
            'line_ids': [
                Command.create({'account_id': debit_account.id, 'debit': amount}),
                Command.create({'account_id': credit_account.id, 'credit': amount}),
            ],
        })
        move.action_post()
        return move

    def _reconcile(self, moves, account=None):
        account = account or self.transfer
        moves.line_ids.filtered(lambda line: line.account_id == account).reconcile()

    def _deposit(self, amount=100, cash_day='2026-01-10', bank_day='2026-01-10', reconcile=True):
        """ Cash deposited at the bank: the cash entry and the bank entry. """
        cash_move = self._entry(self.cash_journal, self.transfer, self.cash, amount, cash_day)
        bank_move = self._entry(self.bank_journal, self.bank, self.transfer, amount, bank_day)
        if reconcile:
            self._reconcile(cash_move + bank_move)
        return cash_move, bank_move

    def _hidden_lines(self, move, account=None):
        account = account or self.transfer
        return move.line_ids.filtered(lambda line: line.account_id == account).ids

    # ------------------------------------------------------------------ rules

    def test_entry_not_concerned(self):
        move = self._entry(self.misc_journal, self.expense, self.cash)
        self.assertEqual(move._fg_get_transfer_links(), {move.id: {
            'display_name': move.name,
            'sort_key': (date(2026, 1, 10), move.name, 2, '', move.name),
            'linked_move_ids': [],
            'hidden_line_ids': [],
        }})

    def test_one_deposit(self):
        cash_move, bank_move = self._deposit()
        links = (cash_move + bank_move)._fg_get_transfer_links()
        name = f"{bank_move.name} ({cash_move.name})"

        self.assertEqual(links[cash_move.id]['display_name'], name)
        self.assertEqual(links[bank_move.id]['display_name'], name)
        self.assertEqual(links[cash_move.id]['linked_move_ids'], [bank_move.id])
        self.assertEqual(links[bank_move.id]['linked_move_ids'], [cash_move.id])
        self.assertEqual(links[cash_move.id]['hidden_line_ids'], self._hidden_lines(cash_move))
        self.assertEqual(links[bank_move.id]['hidden_line_ids'], self._hidden_lines(bank_move))
        self.assertLess(
            links[bank_move.id]['sort_key'], links[cash_move.id]['sort_key'],
            "the bank entry comes before the cash entry",
        )

    def test_item_not_reconciled_is_shown(self):
        cash_move, bank_move = self._deposit(reconcile=False)
        links = (cash_move + bank_move)._fg_get_transfer_links()
        for move in cash_move + bank_move:
            self.assertEqual(links[move.id]['display_name'], move.name)
            self.assertEqual(links[move.id]['hidden_line_ids'], [])
            self.assertEqual(links[move.id]['linked_move_ids'], [])

    def test_item_partially_reconciled_is_shown(self):
        cash_move = self._entry(self.cash_journal, self.transfer, self.cash, 100)
        bank_move = self._entry(self.bank_journal, self.bank, self.transfer, 60)
        self._reconcile(cash_move + bank_move)
        links = (cash_move + bank_move)._fg_get_transfer_links()
        self.assertEqual(links[cash_move.id]['hidden_line_ids'], [])
        self.assertEqual(links[bank_move.id]['display_name'], bank_move.name)

    def test_several_cash_entries_for_one_bank_entry(self):
        first = self._entry(self.cash_journal, self.transfer, self.cash, 100)
        second = self._entry(self.cash_journal, self.transfer, self.cash, 50)
        bank_move = self._entry(self.bank_journal, self.bank, self.transfer, 150)
        moves = first + second + bank_move
        self._reconcile(moves)
        links = moves._fg_get_transfer_links()

        name = f"{bank_move.name} ({first.name}, {second.name})"
        for move in moves:
            self.assertEqual(links[move.id]['display_name'], name)
        # the two cash entries are on the same side: linked through the bank entry only
        self.assertEqual(links[first.id]['linked_move_ids'], sorted((second + bank_move).ids))
        ordered = sorted(moves, key=lambda move: links[move.id]['sort_key'])
        self.assertEqual(ordered[0], bank_move)

    def test_two_bank_entries(self):
        """ A transfer between two banks: the smallest account code first. """
        other_bank_journal = self.env['account.journal'].create({
            'name': "Second bank", 'type': 'bank', 'code': 'FGB2', 'company_id': self.company.id,
        })
        other_bank = other_bank_journal.default_account_id
        out_move = self._entry(self.bank_journal, self.transfer, self.bank)
        in_move = self._entry(other_bank_journal, other_bank, self.transfer)
        self._reconcile(out_move + in_move)
        links = (out_move + in_move)._fg_get_transfer_links()

        expected_first = out_move if self.bank.code < other_bank.code else in_move
        ordered = sorted(out_move + in_move, key=lambda move: links[move.id]['sort_key'])
        self.assertEqual(ordered[0], expected_first)
        self.assertTrue(links[out_move.id]['display_name'].startswith(expected_first.name))

    def test_entries_on_different_days(self):
        cash_move, bank_move = self._deposit(cash_day='2026-01-10', bank_day='2026-01-12')
        links = (cash_move + bank_move)._fg_get_transfer_links()

        # each entry stays on its own day, the earliest one is the main entry
        self.assertEqual(links[cash_move.id]['sort_key'][0], date(2026, 1, 10))
        self.assertEqual(links[bank_move.id]['sort_key'][0], date(2026, 1, 12))
        name = f"{cash_move.name} ({bank_move.name})"
        self.assertEqual(links[cash_move.id]['display_name'], name)
        self.assertEqual(links[bank_move.id]['display_name'], name)

    def test_linked_entry_out_of_the_recordset(self):
        cash_move, bank_move = self._deposit()
        links = cash_move._fg_get_transfer_links()
        self.assertEqual(list(links), [cash_move.id])
        self.assertEqual(links[cash_move.id]['display_name'], f"{bank_move.name} ({cash_move.name})")
        self.assertEqual(links[cash_move.id]['linked_move_ids'], [bank_move.id])
        # same name whichever entries are asked for
        self.assertEqual(
            bank_move._fg_get_transfer_links()[bank_move.id]['display_name'],
            links[cash_move.id]['display_name'],
        )

    def test_cluster_is_followed_out_of_the_recordset(self):
        """ Asked for one cash entry only, the name still lists the other cash
        entry, which is linked through the bank entry. """
        first = self._entry(self.cash_journal, self.transfer, self.cash, 100)
        second = self._entry(self.cash_journal, self.transfer, self.cash, 50)
        bank_move = self._entry(self.bank_journal, self.bank, self.transfer, 150)
        self._reconcile(first + second + bank_move)
        links = first._fg_get_transfer_links()
        self.assertEqual(
            links[first.id]['display_name'], f"{bank_move.name} ({first.name}, {second.name})",
        )

    def test_linked_entries_stay_together_among_others(self):
        before = self._entry(self.misc_journal, self.expense, self.cash)
        cash_move, bank_move = self._deposit()
        after = self._entry(self.misc_journal, self.expense, self.cash)
        moves = before + cash_move + bank_move + after
        links = moves._fg_get_transfer_links()
        ordered = sorted(moves, key=lambda move: links[move.id]['sort_key'])
        position = ordered.index(bank_move)
        self.assertEqual(ordered[position + 1], cash_move, "the pair is adjacent")

    # ---------------------------------------------------------------- setting

    def test_setting_off(self):
        cash_move, bank_move = self._deposit()
        self.company.fg_hide_transfer_account = False
        links = (cash_move + bank_move)._fg_get_transfer_links()
        for move in cash_move + bank_move:
            self.assertEqual(links[move.id]['display_name'], move.name)
            self.assertEqual(links[move.id]['hidden_line_ids'], [])

    def test_account_not_selected(self):
        cash_move, bank_move = self._deposit()
        self.company.fg_hidden_transfer_account_ids = self.expense
        links = (cash_move + bank_move)._fg_get_transfer_links()
        self.assertEqual(links[cash_move.id]['hidden_line_ids'], [])

    def test_two_hidden_accounts(self):
        outstanding = self.env['account.account'].create({
            'code': 'FGT1131', 'name': "Outstanding Receipts (test)",
            'account_type': 'asset_current', 'reconcile': True,
        })
        self.company.fg_hidden_transfer_account_ids = self.transfer + outstanding
        cash_move, bank_move = self._deposit()
        receipt = self._entry(self.misc_journal, outstanding, self.expense, 30)
        statement = self._entry(self.bank_journal, self.bank, outstanding, 30)
        self._reconcile(receipt + statement, outstanding)

        links = (cash_move + bank_move + receipt + statement)._fg_get_transfer_links()
        self.assertEqual(links[cash_move.id]['linked_move_ids'], [bank_move.id])
        self.assertEqual(links[receipt.id]['linked_move_ids'], [statement.id])
        self.assertEqual(links[receipt.id]['hidden_line_ids'], self._hidden_lines(receipt, outstanding))
        self.assertEqual(links[statement.id]['display_name'], f"{statement.name} ({receipt.name})")

    def test_empty_recordset(self):
        self.assertEqual(self.env['account.move']._fg_get_transfer_links(), {})

    def test_query_count_does_not_depend_on_the_number_of_entries(self):
        few = self.env['account.move']
        for _i in range(2):
            few += sum(self._deposit(), self.env['account.move'])
        many = few
        for _i in range(6):
            many += sum(self._deposit(), self.env['account.move'])
        self.env.flush_all()

        def count(moves):
            moves.invalidate_recordset()
            start = self.env.cr.sql_log_count
            moves._fg_get_transfer_links()
            return self.env.cr.sql_log_count - start

        count(few)  # warm up the caches that do not depend on the entries
        self.assertEqual(count(few), count(many))
