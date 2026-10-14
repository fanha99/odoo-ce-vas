from odoo import models
from odoo.tools import SQL


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _fg_get_document_numbers(self):
        """ The voucher numbers the accounting books print for the entries,
        following the settings of their journal.

        :return: {move id: number}
        """
        if not self.ids:
            return {}
        self.flush_model(['name', 'ref', 'journal_id'])
        number, join = self.env['account.journal']._fg_get_document_number_query('move', 'name')
        rows = self.env.execute_query(SQL(
            "SELECT move.id, %s FROM account_move move %s WHERE move.id = ANY(%s)",
            number, join, list(self.ids),
        ))
        return {move_id: number or '' for move_id, number in rows}
