from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import new_test_user, tagged

from .common import CounterpartCommon

M = 1_000_000


@tagged('post_install', '-at_install')
class TestCounterpart(CounterpartCommon):

    # Allocation ---------------------------------------------------------------

    def test_one_debit_one_credit(self):
        """ Readme 3.1, customer payment: Dr 112 55M / Cr 131 55M, same partner
        -> one counterpart of 55M (pass 1). """
        move = self._create_entry([
            ('112', 55 * M, 0, self.partner_a),
            ('131', 0, 55 * M, self.partner_a),
        ])
        self.assertCounterparts(move, [('112', '131', 55 * M)])

    def test_one_debit_many_credits(self):
        """ Readme 3.2, customer invoice: Dr 131 110M / Cr 511 100M, Cr 33311 10M
        -> 100M and 10M (pass 2). """
        move = self._create_entry([
            ('131', 110 * M, 0, self.partner_a),
            ('511', 0, 100 * M, self.partner_a),
            ('33311', 0, 10 * M, self.partner_a),
        ])
        self.assertCounterparts(move, [
            ('131', '511', 100 * M),
            ('131', '33311', 10 * M),
        ])

    def test_many_debits_one_credit(self):
        """ Readme 3.3, vendor bill: Dr 156 40M, Dr 1331 4M / Cr 331 44M
        -> 40M and 4M (pass 2). """
        move = self._create_entry([
            ('156', 40 * M, 0, self.partner_b),
            ('1331', 4 * M, 0, self.partner_b),
            ('331', 0, 44 * M, self.partner_b),
        ])
        self.assertCounterparts(move, [
            ('156', '331', 40 * M),
            ('1331', '331', 4 * M),
        ])

    def test_many_debits_many_credits(self):
        """ Readme 3.5, employer insurance: Dr 6421 12.9M, Dr 6411 8.6M /
        Cr 3383 17.5M, Cr 3384 3M, Cr 3386 1M, no partner
        -> 10.5M, 1.8M, 0.6M and 7M, 1.2M, 0.4M (pass 2). """
        move = self._create_entry([
            ('6421', 12_900_000, 0),
            ('6411', 8_600_000, 0),
            ('3383', 0, 17_500_000),
            ('3384', 0, 3_000_000),
            ('3386', 0, 1_000_000),
        ])
        self.assertCounterparts(move, [
            ('6421', '3383', 10_500_000),
            ('6421', '3384', 1_800_000),
            ('6421', '3386', 600_000),
            ('6411', '3383', 7_000_000),
            ('6411', '3384', 1_200_000),
            ('6411', '3386', 400_000),
        ])

    def test_exact_match_same_partner(self):
        """ Readme 3.4, sale with cost of goods: Dr 131 110M, Cr 511 100M,
        Cr 33311 10M, Dr 632 70M, Cr 156 70M, same partner
        -> 632/156 70M in pass 1, then 131/511 100M and 131/33311 10M. """
        move = self._create_entry([
            ('131', 110 * M, 0, self.partner_a),
            ('511', 0, 100 * M, self.partner_a),
            ('33311', 0, 10 * M, self.partner_a),
            ('632', 70 * M, 0, self.partner_a),
            ('156', 0, 70 * M, self.partner_a),
        ])
        self.assertCounterparts(move, [
            ('632', '156', 70 * M),
            ('131', '511', 100 * M),
            ('131', '33311', 10 * M),
        ])

    def test_exact_match_adjacent_ignores_partner(self):
        """ Readme 3.7, pass 1 exception: Dr 331 20M (partner), Cr 112 20M (no
        partner), Dr 6427 3M, Cr 111 3M -> 331/112 20M and 6427/111 3M. """
        move = self._create_entry([
            ('331', 20 * M, 0, self.partner_b),
            ('112', 0, 20 * M),
            ('6427', 3 * M, 0),
            ('111', 0, 3 * M),
        ])
        self.assertCounterparts(move, [
            ('331', '112', 20 * M),
            ('6427', '111', 3 * M),
        ])

    def test_exact_amount_other_partner(self):
        """ Same amount but another partner (not adjacent): no one to one
        match, the debit item is split pro rata in pass 3. """
        move = self._create_entry([
            ('331', 20 * M, 0, self.partner_b),
            ('6427', 10 * M, 0),
            ('112', 0, 20 * M),
            ('3388', 0, 10 * M, self.partner_a),
        ])
        self.assertCounterparts(move, [
            ('6427', '112', 10 * M),    # pass 2, both without partner
            ('331', '112', 10 * M),     # pass 3
            ('331', '3388', 10 * M),    # pass 3
        ])

    def test_remainder_any_partner(self):
        """ Readme 3.6, one payment for two vendors: Dr 331 30M (partner B),
        Dr 331 20M (partner C) / Cr 112 50M (no partner)
        -> 30M and 20M in pass 3. """
        move = self._create_entry([
            ('331', 30 * M, 0, self.partner_a),
            ('331', 20 * M, 0, self.partner_b),
            ('112', 0, 50 * M),
        ])
        counterparts = self._counterparts(move)
        self.assertEqual(
            [(ctp.dr_aml_id.partner_id, ctp.cr_account_id, ctp.countered_amt) for ctp in counterparts.sorted('id')],
            [
                (self.partner_a, self._account('112'), 30 * M),
                (self.partner_b, self._account('112'), 20 * M),
            ],
        )

    def test_partner_group_prorata(self):
        """ Pass 2: a debit item is distributed over the credit items of its
        partner before any other credit item. """
        move = self._create_entry([
            ('131', 60 * M, 0, self.partner_a),
            ('511', 0, 40 * M, self.partner_a),
            ('3388', 0, 30 * M),
            ('33311', 0, 20 * M, self.partner_a),
            ('6427', 50 * M, 0),
            ('111', 0, 20 * M),
        ])
        self.assertCounterparts(move, [
            ('131', '511', 40 * M),
            ('131', '33311', 20 * M),
            ('6427', '3388', 30 * M),
            ('6427', '111', 20 * M),
        ])

    def test_rounding(self):
        """ A pro rata split that does not divide evenly: the rounding
        difference goes to the last credit item and every item adds up. """
        move = self._create_entry([
            ('6421', 100.0, 0),
            ('6411', 200.0, 0),
            ('242', 0, 100.01),
            ('153', 0, 100.01),
            ('3388', 0, 99.98),
        ])
        self.assertCounterparts(move, [
            ('6421', '242', 33.34),
            ('6421', '153', 33.34),
            ('6421', '3388', 33.32),    # 33.33 pro rata, less the rounding difference
            ('6411', '242', 66.67),
            ('6411', '153', 66.67),
            ('6411', '3388', 66.66),
        ])
        self.assertEqual(move.countered_status, 'fully')
        self.assertEqual(set(move.line_ids.mapped('countered_status')), {'fully'})

    def test_foreign_currency(self):
        """ countered_amt_currency follows the same split as countered_amt. """
        foreign = self.setup_other_currency('EUR', rates=[('2016-01-01', 0.5)])
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'date': '2026-01-15',
            'line_ids': [
                Command.create({
                    'account_id': self._account(code).id,
                    'currency_id': foreign.id,
                    'amount_currency': amount_currency,
                    'debit': max(amount_currency * 2, 0.0),
                    'credit': max(-amount_currency * 2, 0.0),
                })
                for code, amount_currency in [('131', 110.0), ('511', -100.0), ('33311', -10.0)]
            ],
        })
        move.action_post()
        self.assertCountEqual(
            [
                (ctp.cr_account_id.code[3:], ctp.countered_amt, ctp.countered_amt_currency, ctp.currency_id)
                for ctp in self._counterparts(move)
            ],
            [
                ('511', 200.0, 100.0, foreign),
                ('33311', 20.0, 10.0, foreign),
            ],
        )

    def test_storno(self):
        """ On hold (TODO(storno)): an entry with negative debit/credit items
        gets no counterpart and stays 'none'. """
        self.env.company.account_storno = True
        move = self._create_entry([
            ('632', -70.0, 0),
            ('156', 0, -70.0),
        ])
        self.assertEqual(move.line_ids.mapped('debit'), [-70.0, 0.0])
        self.assertFalse(self._counterparts(move))
        self.assertEqual(move.countered_status, 'none')

    def test_zero_and_note_lines_ignored(self):
        """ Zero-amount items and sections/notes get no counterpart and are
        'fully' countered. """
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        invoice.invoice_line_ids = [
            Command.create({'display_type': 'line_note', 'name': "A note"}),
            Command.create({'name': "Free sample", 'quantity': 1, 'price_unit': 0.0, 'tax_ids': False}),
        ]
        invoice.action_post()
        ignored = invoice.line_ids.filtered(lambda line: not line.debit and not line.credit)
        self.assertEqual(len(ignored), 2)
        self.assertEqual(ignored.mapped('countered_status'), ['fully', 'fully'])
        self.assertFalse(ignored.countered_aml_ids)
        self.assertEqual(invoice.countered_status, 'fully')

    def test_constraint_same_move_and_sides(self):
        """ A counterpart links a debit item with a credit item of one entry. """
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        other = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        Counterpart = self.env['account.move.line.ctp'].sudo()
        with self.assertRaises(ValidationError):
            Counterpart.create({
                'dr_aml_id': self._line(move, '112').id,
                'cr_aml_id': self._line(other, '131').id,
                'countered_amt': 55.0,
            })
        move._ctp_remove()
        with self.assertRaises(ValidationError):
            Counterpart.create({
                'dr_aml_id': self._line(move, '131').id,
                'cr_aml_id': self._line(move, '112').id,
                'countered_amt': 55.0,
            })

    # Computed fields ----------------------------------------------------------

    def test_line_fields(self):
        """ countered_aml_ids / countered_account_ids / countered_amt /
        countered_status of each item after posting (readme 3.2). """
        move = self._create_entry([
            ('131', 110 * M, 0, self.partner_a),
            ('511', 0, 100 * M, self.partner_a),
            ('33311', 0, 10 * M, self.partner_a),
        ])
        receivable = self._line(move, '131')
        revenue = self._line(move, '511')
        tax = self._line(move, '33311')
        self.assertEqual(receivable.countered_account_codes, 'CTP33311, CTP511')
        self.assertEqual(revenue.countered_account_codes, 'CTP131')
        self.assertRecordValues(receivable + revenue + tax, [
            {
                'countered_aml_ids': (revenue + tax).ids,
                'countered_account_ids': (self._account('511') + self._account('33311')).ids,
                'countered_amt': 110 * M,
                'countered_status': 'fully',
            },
            {
                'countered_aml_ids': receivable.ids,
                'countered_account_ids': self._account('131').ids,
                'countered_amt': 100 * M,
                'countered_status': 'fully',
            },
            {
                'countered_aml_ids': receivable.ids,
                'countered_account_ids': self._account('131').ids,
                'countered_amt': 10 * M,
                'countered_status': 'fully',
            },
        ])

    def test_partial_status(self):
        """ An item whose counterparts do not cover its amount is 'partially'
        countered, and so is its entry. """
        move = self._create_entry([
            ('131', 110.0, 0),
            ('511', 0, 100.0),
            ('33311', 0, 10.0),
        ])
        self._counterparts(move).filtered(lambda ctp: ctp.cr_account_id == self._account('33311')).sudo().unlink()
        self.assertEqual(self._line(move, '131').countered_status, 'partially')
        self.assertEqual(self._line(move, '131').countered_amt, 100.0)
        self.assertEqual(self._line(move, '511').countered_status, 'fully')
        self.assertEqual(self._line(move, '33311').countered_status, 'none')
        self.assertEqual(move.countered_status, 'partially')

        # Generating again completes the entry.
        move._ctp_generate()
        self.assertEqual(move.countered_status, 'fully')
        self.assertEqual(len(self._counterparts(move)), 2)

    def test_get_counterparts(self):
        """ _get_counterparts() on the items of the invoice of readme 3.2:
        131 -> [(511, 100M), (33311, 10M)], 511 -> [(131, 100M)],
        33311 -> [(131, 10M)]; an item without counterpart -> []. """
        move = self._create_entry([
            ('131', 110 * M, 0, self.partner_a),
            ('511', 0, 100 * M, self.partner_a),
            ('33311', 0, 10 * M, self.partner_a),
        ])
        draft = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)], post=False)
        receivable = self._line(move, '131')
        revenue = self._line(move, '511')
        tax = self._line(move, '33311')

        counterparts = (move.line_ids + draft.line_ids)._get_counterparts()
        self.assertEqual(counterparts[receivable.id], [
            {'aml': revenue, 'account': self._account('511'), 'account_code': 'CTP511',
             'amount': 100 * M, 'amount_currency': 100 * M},
            {'aml': tax, 'account': self._account('33311'), 'account_code': 'CTP33311',
             'amount': 10 * M, 'amount_currency': 10 * M},
        ])
        self.assertEqual(counterparts[revenue.id], [
            {'aml': receivable, 'account': self._account('131'), 'account_code': 'CTP131',
             'amount': 100 * M, 'amount_currency': 100 * M},
        ])
        self.assertEqual(counterparts[tax.id], [
            {'aml': receivable, 'account': self._account('131'), 'account_code': 'CTP131',
             'amount': 10 * M, 'amount_currency': 10 * M},
        ])
        for line in draft.line_ids:
            self.assertEqual(counterparts[line.id], [])

    def test_move_status(self):
        """ account.move.countered_status: none (draft) -> fully (posted). """
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)], post=False)
        self.assertEqual(move.countered_status, 'none')
        move.action_post()
        self.assertEqual(move.countered_status, 'fully')

    def test_account_change_on_posted_line(self):
        """ Changing the account of a posted item updates the countered
        accounts of its counterparts. """
        move = self._create_entry([
            ('131', 110.0, 0),
            ('511', 0, 100.0),
            ('33311', 0, 10.0),
        ])
        receivable = self._line(move, '131')
        self._line(move, '511').account_id = self._account('515')
        self.assertEqual(receivable.countered_account_ids, self._account('515') + self._account('33311'))
        self.assertEqual(self._counterparts(move).mapped('cr_account_id'), self._account('515') + self._account('33311'))

    # Lifecycle ----------------------------------------------------------------

    def test_reset_to_draft_removes_counterparts(self):
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        self.assertTrue(self._counterparts(move))
        move.button_draft()
        self.assertFalse(self._counterparts(move))
        self.assertEqual(move.countered_status, 'none')
        self.assertEqual(move.line_ids.mapped('countered_status'), ['none', 'none'])
        self.assertFalse(move.line_ids.countered_account_ids)
        self.assertEqual(move.line_ids.mapped('countered_account_codes'), ['', ''])

    def test_repost_regenerates_counterparts(self):
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        move.button_draft()
        move.line_ids = [
            Command.update(self._line(move, '112').id, {'debit': 60.0}),
            Command.update(self._line(move, '131').id, {'credit': 60.0}),
        ]
        move.action_post()
        self.assertCounterparts(move, [('112', '131', 60.0)])
        self.assertEqual(move.countered_status, 'fully')

    def test_regenerate(self):
        """ regenerate=True replaces the counterparts of fully countered entries. """
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        counterparts = self._counterparts(move)
        self.assertFalse(move._ctp_generate())
        self.assertEqual(self._counterparts(move), counterparts)
        created = move._ctp_generate(regenerate=True)
        self.assertEqual(len(created), 1)
        self.assertFalse(counterparts.exists())

    def test_actions(self):
        """ Counterparts can be opened from an entry and from an item, and
        regenerated from an entry. """
        move = self._create_entry([
            ('131', 110.0, 0),
            ('511', 0, 100.0),
            ('33311', 0, 10.0),
        ])
        counterparts = self._counterparts(move)
        Counterpart = self.env['account.move.line.ctp']

        action = move.action_view_counterparts()
        self.assertEqual(action['res_model'], 'account.move.line.ctp')
        self.assertEqual(Counterpart.search(action['domain']), counterparts)

        action = self._line(move, '511').action_view_counterparts()
        self.assertEqual(
            Counterpart.search(action['domain']),
            counterparts.filtered(lambda ctp: ctp.cr_account_id == self._account('511')),
        )

        draft = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)], post=False)
        (move + draft).action_ctp_regenerate()
        self.assertFalse(counterparts.exists())
        self.assertEqual(len(self._counterparts(move)), 2)
        self.assertFalse(self._counterparts(draft))

    def test_display_name(self):
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        self.assertEqual(self._counterparts(move).display_name, "CTP112 / CTP131: $\xa055.00")

    def test_invoice(self):
        """ A customer invoice with two product lines and a tax line. """
        invoice = self.init_invoice('out_invoice', products=self.product_a + self.product_b, post=True)
        receivable = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        credits = invoice.line_ids.filtered('credit')
        self.assertEqual(len(receivable), 1)
        self.assertGreater(len(credits), 2)

        self.assertEqual(invoice.countered_status, 'fully')
        self.assertEqual(receivable.countered_amt, invoice.amount_total)
        self.assertEqual(receivable.countered_aml_ids, credits)
        self.assertEqual(receivable.countered_account_ids, credits.account_id)
        for line in credits:
            self.assertEqual(line.countered_amt, line.credit)
            self.assertEqual(line.countered_account_ids, receivable.account_id)

    def test_post_as_invoicing_user(self):
        """ A user with only the Invoicing group can post: counterparts are
        created in sudo. """
        user = new_test_user(self.env, login='ctp_invoicing', groups='account.group_account_invoice')
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        invoice.with_user(user).action_post()
        self.assertEqual(invoice.countered_status, 'fully')
        self.assertTrue(self._counterparts(invoice))
