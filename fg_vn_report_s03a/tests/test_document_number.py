from odoo.tests import tagged

from .common import S03aCommon


@tagged('post_install', '-at_install')
class TestS03aDocumentNumber(S03aCommon):
    """ The voucher number follows the settings of the journal: the reference
    instead of the number, or the number without its trailing sequence
    (readme, section 2). """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # all on the same day; the bank references are not in the entry order
        cls.bank_first = cls._post(
            '2026-01-10', [(cls.bank, 100, 0), ('511', 0, 100)], journal=cls.bank_journal, ref="GBC-0042")
        cls.bank_second = cls._post(
            '2026-01-10', [(cls.bank, 200, 0), ('511', 0, 200)], journal=cls.bank_journal, ref="GBC-0015")
        cls.cash_first = cls._post('2026-01-10', [('642', 3, 0), (cls.cash, 0, 3)], journal=cls.cash_journal)
        cls.cash_second = cls._post('2026-01-10', [('642', 4, 0), (cls.cash, 0, 4)], journal=cls.cash_journal)
        cls.cash_number = cls.cash_first.name.rsplit('/', 1)[0]

    @classmethod
    def _use_the_settings(cls):
        cls.bank_journal.fg_use_ref_as_doc_no = True
        cls.cash_journal.fg_truncate_seq_as_doc_no = True

    def _moves(self, **options):
        """ The entries of the journal as (move id, number), in order. """
        moves = []
        for line in self._lines(**options):
            if (line['move_id'], line['move_name']) not in moves:
                moves.append((line['move_id'], line['move_name']))
        return moves

    def test_settings_off(self):
        self.assertEqual(
            {name for _move_id, name in self._moves()},
            set((self.bank_first + self.bank_second + self.cash_first + self.cash_second).mapped('name')),
        )

    def test_number_printed(self):
        self._use_the_settings()
        self.assertEqual(dict(self._moves()), {
            self.bank_first.id: "GBC-0042",
            self.bank_second.id: "GBC-0015",
            self.cash_first.id: self.cash_number,
            self.cash_second.id: self.cash_number,
        })

    def test_entry_without_reference_keeps_its_number(self):
        self._use_the_settings()
        self.bank_first.ref = False
        self.assertEqual(dict(self._moves())[self.bank_first.id], self.bank_first.name)

    def test_entries_are_in_the_order_of_the_number_printed(self):
        self._use_the_settings()
        moves = self._moves()
        self.assertEqual(moves, sorted(moves, key=lambda move: move[1]))
        move_ids = [move_id for move_id, _name in moves]
        self.assertLess(move_ids.index(self.bank_second.id), move_ids.index(self.bank_first.id))
        # same number printed: in the order of their own number
        self.assertEqual(move_ids.index(self.cash_second.id), move_ids.index(self.cash_first.id) + 1)

    def test_search_bears_on_the_number_printed(self):
        self._use_the_settings()
        self.assertEqual({line['move_id'] for line in self._lines(search="gbc-0015")}, {self.bank_second.id})
        self.assertEqual(self._lines(search=self.bank_second.name), [])
        self.assertEqual(self._group(search="gbc-0015")['total'], {'debit': 200, 'credit': 200})

    def test_linked_entries(self):
        cash_move, bank_move = self._deposit('2026-01-20', 500)
        bank_move.ref = "GBC-0050"
        self._use_the_settings()
        self._hide_transfer_account()
        self.assertEqual(
            {name for move_id, name in self._moves() if move_id in (cash_move + bank_move).ids},
            {f"GBC-0050 ({self.cash_number})"},
        )
