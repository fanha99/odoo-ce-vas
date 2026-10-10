from unittest.mock import patch

from odoo.tests import tagged

from .common import CounterpartCommon


@tagged('post_install', '-at_install')
class TestCounterpartGenerate(CounterpartCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['account.counterpart.generate']

    def _create_legacy_entry(self, **kwargs):
        """ A posted entry without counterparts, as if it had been posted
        before the module was installed. """
        move = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)], **kwargs)
        move._ctp_remove()
        self.assertEqual(move.countered_status, 'none')
        return move

    def test_generate_missing(self):
        """ 'missing' mode only processes the entries not fully countered. """
        countered = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        counterparts = self._counterparts(countered)
        legacy = self._create_legacy_entry()

        wizard = self.Wizard.create({'mode': 'missing'})
        self.assertEqual(wizard.move_count, 1)
        action = wizard.action_generate()

        self.assertEqual(action['params']['type'], 'success')
        self.assertCounterparts(legacy, [('112', '131', 55.0)])
        self.assertEqual(legacy.countered_status, 'fully')
        self.assertEqual(self._counterparts(countered), counterparts)
        self.assertEqual(wizard.move_count, 0)

    def test_regenerate_all(self):
        """ 'all' mode replaces the existing counterparts. """
        countered = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)])
        counterparts = self._counterparts(countered)
        legacy = self._create_legacy_entry()

        wizard = self.Wizard.create({'mode': 'all'})
        self.assertEqual(wizard.move_count, 2)
        wizard.action_generate()

        self.assertFalse(counterparts.exists())
        self.assertCounterparts(countered, [('112', '131', 55.0)])
        self.assertCounterparts(legacy, [('112', '131', 55.0)])

    def test_journal_and_date_filters(self):
        other_journal = self.journal.copy({'name': "Other Operations", 'code': 'CTPO'})
        in_journal = self._create_legacy_entry()
        in_other_journal = self._create_legacy_entry(journal=other_journal)
        earlier = self._create_legacy_entry(date='2025-06-30')

        wizard = self.Wizard.create({'journal_ids': other_journal.ids})
        self.assertEqual(wizard.move_count, 1)
        wizard.action_generate()
        self.assertTrue(self._counterparts(in_other_journal))
        self.assertFalse(self._counterparts(in_journal + earlier))

        wizard = self.Wizard.create({'date_from': '2025-06-01', 'date_to': '2025-12-31'})
        self.assertEqual(wizard.move_count, 1)
        wizard.action_generate()
        self.assertTrue(self._counterparts(earlier))
        self.assertFalse(self._counterparts(in_journal))

    def test_draft_entries_skipped(self):
        draft = self._create_entry([('112', 55.0, 0), ('131', 0, 55.0)], post=False)
        wizard = self.Wizard.create({'mode': 'all'})
        self.assertEqual(wizard.move_count, 0)
        wizard.action_generate()
        self.assertFalse(self._counterparts(draft))
        self.assertEqual(draft.countered_status, 'none')

    def test_batches(self):
        """ More entries than BATCH_SIZE are all processed. """
        moves = self.env['account.move']
        for _index in range(5):
            moves += self._create_legacy_entry()

        wizard = self.Wizard.create({})
        with patch.object(type(wizard), 'BATCH_SIZE', 2), \
                patch.object(type(wizard), '_generate_batch', autospec=True,
                             side_effect=type(wizard)._generate_batch) as generate_batch:
            wizard.action_generate()

        self.assertEqual(generate_batch.call_count, 3)
        self.assertEqual(moves.mapped('countered_status'), ['fully'] * 5)
        self.assertEqual(len(self._counterparts(moves)), 5)

    def test_legacy_items_without_amount(self):
        """ On an entry posted before the installation, the items with nothing
        to counter hold the column default 'none': the wizard fixes them. """
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        invoice.invoice_line_ids = [(0, 0, {'name': "Free sample", 'quantity': 1, 'price_unit': 0.0, 'tax_ids': False})]
        invoice.action_post()
        invoice._ctp_remove()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE account_move_line SET countered_status = 'none' WHERE move_id = %s", [invoice.id])
        self.env.invalidate_all()
        free_sample = invoice.line_ids.filtered(lambda line: line.name == "Free sample")
        self.assertEqual(free_sample.countered_status, 'none')

        self.Wizard.create({}).action_generate()

        self.assertEqual(free_sample.countered_status, 'fully')
        self.assertEqual(invoice.countered_status, 'fully')

    def test_unsupported_entries_reported(self):
        """ Entries left without counterparts (negative amounts) are reported. """
        self.env.company.account_storno = True
        storno = self._create_entry([('632', -70.0, 0), ('156', 0, -70.0)])

        action = self.Wizard.create({}).action_generate()

        self.assertEqual(action['params']['type'], 'warning')
        self.assertFalse(self._counterparts(storno))
