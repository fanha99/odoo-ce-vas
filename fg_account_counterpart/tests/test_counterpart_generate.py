from odoo.tests import tagged

from .common import CounterpartCommon

TODO = "fg_account_counterpart: generator wizard not implemented yet"


@tagged('post_install', '-at_install')
class TestCounterpartGenerate(CounterpartCommon):

    def test_generate_missing(self):
        """ 'missing' mode only processes the entries not fully countered. """
        self.skipTest(TODO)

    def test_regenerate_all(self):
        """ 'all' mode replaces the existing counterparts. """
        self.skipTest(TODO)

    def test_journal_and_date_filters(self):
        self.skipTest(TODO)

    def test_draft_entries_skipped(self):
        self.skipTest(TODO)

    def test_batches(self):
        """ More entries than BATCH_SIZE are all processed. """
        self.skipTest(TODO)
