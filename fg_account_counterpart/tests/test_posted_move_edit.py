from odoo import Command
from odoo.tests import tagged

from .common import CounterpartCommon


@tagged('post_install', '-at_install')
class TestPostedMoveEdit(CounterpartCommon):
    """ The items of a posted entry can be replaced without posting it again:
    the bank reconciliation replaces the suspense item of the statement entry
    by the real counterpart item. The counterparts must follow. """

    def _statement_entry(self):
        # 3388 plays the suspense account of the bank journal
        return self._create_entry([('3388', 100, 0), ('112', 0, 100)])

    def _replace_suspense_item(self, move, lines):
        suspense_item = self._line(move, '3388')
        move.with_context(force_delete=True, skip_readonly_check=True).write({
            'line_ids': [Command.delete(suspense_item.id)] + [
                Command.create({'account_id': self._account(code).id, 'debit': debit, 'credit': credit})
                for code, debit, credit in lines
            ],
        })

    def test_counterparts_on_post(self):
        move = self._statement_entry()
        self.assertCounterparts(move, [('3388', '112', 100)])
        self.assertEqual(move.countered_status, 'fully')

    def test_item_replaced_on_posted_entry(self):
        move = self._statement_entry()
        self._replace_suspense_item(move, [('6421', 100, 0)])

        self.assertEqual(move.state, 'posted')
        self.assertCounterparts(move, [('6421', '112', 100)])
        self.assertEqual(self._line(move, '112').countered_account_ids, self._account('6421'))
        self.assertEqual(self._line(move, '6421').countered_account_ids, self._account('112'))
        self.assertEqual(move.countered_status, 'fully')

    def test_item_replaced_by_two_items(self):
        move = self._statement_entry()
        self._replace_suspense_item(move, [('6421', 60, 0), ('6427', 40, 0)])

        self.assertCounterparts(move, [('6421', '112', 60), ('6427', '112', 40)])
        self.assertEqual(move.countered_status, 'fully')

    def test_remaining_item_status_is_not_stale(self):
        """ Whatever happens to the counterparts, the stored status of the item
        left on the entry must match its counterpart records. """
        move = self._statement_entry()
        self._replace_suspense_item(move, [('6421', 100, 0)])

        bank_item = self._line(move, '112')
        self.env.flush_all()
        self.env.invalidate_all()
        has_counterpart = bool(self._counterparts(move).filtered(
            lambda ctp: bank_item in (ctp.dr_aml_id, ctp.cr_aml_id)))
        self.assertEqual(bank_item.countered_status == 'fully', has_counterpart)
        self.assertEqual(bool(bank_item.countered_amt), has_counterpart)

    def test_generation_repairs_the_entry(self):
        """ Even if nothing regenerates the counterparts when the items change,
        the generation run afterwards on the entry must complete it. """
        move = self._statement_entry()
        self._replace_suspense_item(move, [('6421', 100, 0)])

        move._ctp_generate()
        self.assertCounterparts(move, [('6421', '112', 100)])
        self.assertEqual(move.countered_status, 'fully')
