from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import SQL


@tagged('post_install', '-at_install')
class TestDocumentNumber(AccountTestInvoicingCommon):
    """ The voucher number printed on the accounting books follows the two
    settings of the journal. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.misc = cls.company_data['default_journal_misc']
        cls.cash = cls.company_data['default_journal_cash']

    def _entry(self, journal, ref=False, name=None):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            # the date fits the numbers given by the tests
            'date': '2025-12-10',
            'ref': ref,
            'line_ids': [
                Command.create({'account_id': self.company_data['default_account_expense'].id, 'debit': 10}),
                Command.create({'account_id': self.company_data['default_account_revenue'].id, 'credit': 10}),
            ],
        })
        move.action_post()
        if name:
            move.name = name
        return move

    def _number(self, move):
        return move._fg_get_document_numbers()[move.id]

    def test_settings_off(self):
        move = self._entry(self.misc, ref="HD 001")
        self.assertEqual(self._number(move), move.name)
        number, join = self.env['account.journal']._fg_get_document_number_query()
        # the books read the plain column, without joining the journals
        self.assertEqual(number, SQL("%s.%s", SQL.identifier('line'), SQL.identifier('move_name')))
        self.assertFalse(join)

    def test_reference_instead_of_number(self):
        with_ref = self._entry(self.misc, ref="HD 001")
        without_ref = self._entry(self.misc)
        empty_ref = self._entry(self.misc, ref="")
        other_journal = self._entry(self.cash, ref="PT 3")
        self.misc.fg_use_ref_as_doc_no = True
        self.assertEqual((with_ref + without_ref + empty_ref + other_journal)._fg_get_document_numbers(), {
            with_ref.id: "HD 001",
            without_ref.id: without_ref.name,
            empty_ref.id: empty_ref.name,
            other_journal.id: other_journal.name,
        })

    def test_trailing_sequence_is_dropped(self):
        self.misc.fg_truncate_seq_as_doc_no = True
        self.assertEqual(self._number(self._entry(self.misc, name="BL/2025/12/16")), "BL/2025/12")
        self.assertEqual(self._number(self._entry(self.misc, name="HD/7")), "HD")
        # only a trailing number after a slash is dropped
        self.assertEqual(self._number(self._entry(self.misc, name="BL/2025/DK")), "BL/2025/DK")
        self.assertEqual(self._number(self._entry(self.misc, name="BL2025")), "BL2025")
        # the journals without the setting are untouched
        self.assertEqual(self._number(self._entry(self.cash, name="PT/2025/12/16")), "PT/2025/12/16")

    def test_both_settings(self):
        self.misc.write({'fg_use_ref_as_doc_no': True, 'fg_truncate_seq_as_doc_no': True})
        self.assertEqual(self._number(self._entry(self.misc, ref="HD/7")), "HD")
        self.assertEqual(self._number(self._entry(self.misc, name="BL/2025/12/16")), "BL/2025/12")

    def test_line_query(self):
        """ The books read the number from the journal items. """
        move = self._entry(self.misc, ref="HD 001")
        self.misc.fg_use_ref_as_doc_no = True
        self.env.flush_all()
        number, join = self.env['account.journal']._fg_get_document_number_query()
        rows = self.env.execute_query(SQL(
            "SELECT DISTINCT %s FROM account_move_line line %s WHERE line.move_id = %s",
            number, join, move.id,
        ))
        self.assertEqual(rows, [("HD 001",)])

    def test_empty_recordset(self):
        self.assertEqual(self.env['account.move']._fg_get_document_numbers(), {})
