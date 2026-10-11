from odoo.tests import tagged

from .common import S03bCommon


@tagged('post_install', '-at_install')
class TestS03bCounterparts(S03bCommon):

    def _drop_counterparts(self, move):
        self.env['account.move.line.ctp'].sudo().search([('move_id', '=', move.id)]).unlink()

    # ------------------------------------------------------- one line per item

    def test_single_counterpart(self):
        self.assertEqual(self._summary('511'), [(self.sale.name, '131', 0, 100)])
        self.assertEqual(self._summary('642'), [(self.expense.name, self.cash.code, 300, 0)])

    def test_several_counterparts_are_listed_in_code_order(self):
        self.assertEqual(self._summary('131'), [
            (self.sale.name, '33311, 511', 110, 0),
            (self.payment.name, self.bank.code, 0, 110),
        ])

    def test_item_without_counterpart(self):
        """ An entry posted before the counterpart module was installed. """
        self._drop_counterparts(self.sale)
        self.assertEqual(self._summary('131')[0], (self.sale.name, '', 110, 0))

    # ------------------------------------------- one line per counterpart account

    def test_split_by_counterpart_account(self):
        ledger = self._ledger('131', split_counterparts=True)
        self.assertEqual(
            [(line['move_name'], line['counterpart_account'], line['debit'], line['credit'])
             for line in ledger['lines']],
            [
                (self.sale.name, '33311', 10, 0),
                (self.sale.name, '511', 100, 0),
                (self.payment.name, self.bank.code, 0, 110),
            ],
        )
        self.assertEqual(ledger['line_count'], 3)
        # date, number and description are repeated; the ids are distinct
        first, second, _third = ledger['lines']
        self.assertEqual((first['date_display'], first['description']), (second['date_display'], second['description']))
        self.assertEqual(first['move_id'], second['move_id'])
        self.assertEqual(len({line['id'] for line in ledger['lines']}), 3)
        # the running balance goes row by row
        self.assertEqual([line['balance'] for line in ledger['lines']], [210, 310, 200])

    def test_split_does_not_change_the_figures_of_the_account(self):
        plain = self._groups()
        split = self._groups(split_counterparts=True)
        self.assertEqual(list(plain), list(split))
        for code, group in plain.items():
            for key in ('opening', 'total', 'closing'):
                self.assertEqual(split[code][key], group[key], f"{key} of {code}")
            self.assertEqual(
                sum(line['debit'] - line['credit'] for line in split[code]['lines']),
                sum(line['debit'] - line['credit'] for line in group['lines']),
            )

    def test_split_merges_the_pairs_with_the_same_counterpart_account(self):
        move = self._post('2026-01-15', [
            ('642', 100, 0, {'name': "Phone"}),
            ('642', 50, 0, {'name': "Internet"}),
            ('331', 0, 150, {'name': "Vendor", 'partner_id': self.partner_b.id}),
        ])
        payable = [
            (line['counterpart_account'], line['credit'])
            for line in self._ledger('331', split_counterparts=True)['lines']
            if line['move_id'] == move.id
        ]
        self.assertEqual(payable, [('642', 150)])

    def test_split_puts_what_is_not_countered_on_a_line_without_account(self):
        self._drop_counterparts(self.sale)
        lines = self._ledger('131', split_counterparts=True)['lines']
        self.assertEqual(
            [(line['counterpart_account'], line['debit']) for line in lines if line['move_id'] == self.sale.id],
            [('', 110)],
        )

    def test_split_of_a_partially_countered_item(self):
        ctp = self.env['account.move.line.ctp'].sudo().search([
            ('move_id', '=', self.sale.id), ('cr_account_id', '=', self.accounts['33311'].id),
        ])
        ctp.unlink()
        lines = self._ledger('131', split_counterparts=True)['lines']
        self.assertEqual(
            [(line['counterpart_account'], line['debit']) for line in lines if line['move_id'] == self.sale.id],
            [('511', 100), ('', 10)],
        )
