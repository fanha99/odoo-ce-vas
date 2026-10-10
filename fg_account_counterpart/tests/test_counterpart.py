from odoo.tests import tagged

from .common import CounterpartCommon

TODO = "fg_account_counterpart: counterpart engine not implemented yet"


@tagged('post_install', '-at_install')
class TestCounterpart(CounterpartCommon):

    # Allocation ---------------------------------------------------------------

    def test_one_debit_one_credit(self):
        """ Readme 3.1, customer payment: Dr 112 55M / Cr 131 55M, same partner
        -> one counterpart of 55M (pass 1). """
        self.skipTest(TODO)

    def test_one_debit_many_credits(self):
        """ Readme 3.2, customer invoice: Dr 131 110M / Cr 511 100M, Cr 33311 10M
        -> 100M and 10M (pass 2). """
        self.skipTest(TODO)

    def test_many_debits_one_credit(self):
        """ Readme 3.3, vendor bill: Dr 156 40M, Dr 1331 4M / Cr 331 44M
        -> 40M and 4M (pass 2). """
        self.skipTest(TODO)

    def test_many_debits_many_credits(self):
        """ Readme 3.5, employer insurance: Dr 6421 12.9M, Dr 6411 8.6M /
        Cr 3383 17.5M, Cr 3384 3M, Cr 3386 1M, no partner
        -> 10.5M, 1.8M, 0.6M and 7M, 1.2M, 0.4M (pass 2). """
        self.skipTest(TODO)

    def test_exact_match_same_partner(self):
        """ Readme 3.4, sale with cost of goods: Dr 131 110M, Cr 511 100M,
        Cr 33311 10M, Dr 632 70M, Cr 156 70M, same partner
        -> 632/156 70M in pass 1, then 131/511 100M and 131/33311 10M. """
        self.skipTest(TODO)

    def test_exact_match_adjacent_ignores_partner(self):
        """ Readme 3.7, pass 1 exception: Dr 331 20M (partner), Cr 112 20M (no
        partner), Dr 6427 3M, Cr 111 3M -> 331/112 20M and 6427/111 3M. """
        self.skipTest(TODO)

    def test_exact_amount_other_partner(self):
        """ Same amount but another partner (not adjacent): no one to one
        match, the debit item is split pro rata in pass 3. """
        self.skipTest(TODO)

    def test_remainder_any_partner(self):
        """ Readme 3.6, one payment for two vendors: Dr 331 30M (partner B),
        Dr 331 20M (partner C) / Cr 112 50M (no partner)
        -> 30M and 20M in pass 3. """
        self.skipTest(TODO)

    def test_partner_group_prorata(self):
        """ Pass 2: a debit item is distributed over the credit items of its
        partner before any other credit item. """
        self.skipTest(TODO)

    def test_rounding(self):
        """ A pro rata split that does not divide evenly: the rounding
        difference goes to the last credit item and every item adds up. """
        self.skipTest(TODO)

    def test_foreign_currency(self):
        """ countered_amt_currency follows the same split as countered_amt. """
        self.skipTest(TODO)

    def test_storno(self):
        """ On hold (TODO(storno)): an entry with negative debit/credit items
        gets no counterpart and stays 'none'. """
        self.skipTest(TODO)

    def test_zero_and_note_lines_ignored(self):
        """ Zero-amount items and sections/notes get no counterpart and are
        'fully' countered. """
        self.skipTest(TODO)

    # Computed fields ----------------------------------------------------------

    def test_line_fields(self):
        """ countered_aml_ids / countered_account_ids / countered_amt /
        countered_status of each item after posting (README result tables). """
        self.skipTest(TODO)

    def test_get_counterparts(self):
        """ _get_counterparts() on the items of the invoice of readme 3.2:
        131 -> [(511, 100M), (33311, 10M)], 511 -> [(131, 100M)],
        33311 -> [(131, 10M)]; an item without counterpart -> []. """
        self.skipTest(TODO)

    def test_move_status(self):
        """ account.move.countered_status: none (draft) -> fully (posted). """
        self.skipTest(TODO)

    def test_account_change_on_posted_line(self):
        """ Changing the account of a posted item updates the countered
        accounts of its counterparts. """
        self.skipTest(TODO)

    # Lifecycle ----------------------------------------------------------------

    def test_reset_to_draft_removes_counterparts(self):
        self.skipTest(TODO)

    def test_repost_regenerates_counterparts(self):
        self.skipTest(TODO)

    def test_invoice(self):
        """ A customer invoice with two product lines and a tax line. """
        self.skipTest(TODO)

    def test_post_as_invoicing_user(self):
        """ A user with only the Invoicing group can post: counterparts are
        created in sudo. """
        self.skipTest(TODO)
