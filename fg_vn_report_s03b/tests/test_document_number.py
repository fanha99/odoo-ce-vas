from odoo.tests import tagged

from .common import S03bCommon


@tagged('post_install', '-at_install')
class TestS03bDocumentNumber(S03bCommon):
    """ The voucher number follows the settings of the journal, and the
    ledger is ordered as the general journal: by the number printed. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # all on the same day; the bank references are not in the entry order
        cls.bank_first = cls._post(
            '2026-01-15', [(cls.bank, 100, 0), ('511', 0, 100)], journal=cls.bank_journal, ref="GBC-0042")
        cls.bank_second = cls._post(
            '2026-01-15', [(cls.bank, 200, 0), ('511', 0, 200)], journal=cls.bank_journal, ref="GBC-0015")
        cls.cash_first = cls._post('2026-01-15', [('642', 3, 0), (cls.cash, 0, 3)], journal=cls.cash_journal)
        cls.cash_second = cls._post('2026-01-15', [('642', 4, 0), (cls.cash, 0, 4)], journal=cls.cash_journal)
        cls.cash_number = cls.cash_first.name.rsplit('/', 1)[0]
        cls.test_moves = cls.bank_first + cls.bank_second + cls.cash_first + cls.cash_second

    @classmethod
    def _use_the_settings(cls):
        cls.bank_journal.fg_use_ref_as_doc_no = True
        cls.cash_journal.fg_truncate_seq_as_doc_no = True

    def _moves(self, account, **options):
        """ The lines of the test entries as (move id, number), in order. """
        return [
            (line['move_id'], line['move_name'])
            for line in self._ledger(account, **options)['lines']
            if line['move_id'] in self.test_moves.ids
        ]

    def test_settings_off(self):
        self.assertEqual(self._moves(self.bank), [
            (self.bank_first.id, self.bank_first.name),
            (self.bank_second.id, self.bank_second.name),
        ])

    def test_lines_are_in_the_order_of_the_number_printed(self):
        self._use_the_settings()
        self.assertEqual(self._moves(self.bank), [
            (self.bank_second.id, "GBC-0015"),
            (self.bank_first.id, "GBC-0042"),
        ])
        # same number printed: in the order of their own number
        self.assertEqual(self._moves(self.cash), [
            (self.cash_first.id, self.cash_number),
            (self.cash_second.id, self.cash_number),
        ])

    def test_running_balance_follows_the_order(self):
        self._use_the_settings()
        lines = self._ledger(self.bank)['lines']
        opening = self._ledger(self.bank)['opening']
        balance = opening['debit'] - opening['credit']
        for line in lines:
            balance += line['debit'] - line['credit']
            self.assertEqual(line['balance'], balance)

    def test_split_counterparts(self):
        self._use_the_settings()
        self.assertEqual(self._moves(self.bank, split_counterparts=True), [
            (self.bank_second.id, "GBC-0015"),
            (self.bank_first.id, "GBC-0042"),
        ])

    def test_linked_entries(self):
        cash_move, bank_move = self._deposit('2026-01-20', 500)
        bank_move.ref = "GBC-0050"
        self._use_the_settings()
        self._hide_transfer_account()
        name = f"GBC-0050 ({self.cash_number})"
        for account, move in ((self.bank, bank_move), (self.cash, cash_move)):
            self.assertEqual(
                [line['move_name'] for line in self._ledger(account)['lines'] if line['move_id'] == move.id],
                [name],
            )
