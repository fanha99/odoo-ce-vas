from odoo import api, fields, models
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # How the accounting books number the entries of the journal. These are
    # presentation settings of the books, so they live with the base report:
    # every book depends on it.
    fg_use_ref_as_doc_no = fields.Boolean(
        string="Use Reference as Voucher Number",
        help="The accounting books (general journal, general ledger) print the reference "
             "of an entry instead of its number in the Voucher No. column. "
             "An entry without reference keeps its number.",
    )
    fg_truncate_seq_as_doc_no = fields.Boolean(
        string="Drop Trailing Sequence from Voucher Number",
        help="The accounting books (general journal, general ledger) drop the trailing "
             "sequence number of the voucher number. Example: BL/2025/12/16 is printed BL/2025/12.",
    )

    @api.model
    def _fg_get_document_number_query(self, alias='line', name_column='move_name'):
        """ The voucher number the accounting books print for an entry, as SQL.
        This is the only place holding the rule: the books sort, search and
        page on this expression, they never rework the number in Python.

        The entry is read from `alias`, a table having the columns
        `name_column`, `ref` and `journal_id`: `account_move_line` by default,
        or `account_move` with `name_column='name'`.

        :return: (number, join) with `number` the SQL expression and `join`
            the join it needs, to add after the table `alias`. When no journal
            uses the settings, the number is the plain column and there is no
            join: the queries of the books are then unchanged.
        """
        table = SQL.identifier(alias)
        name = SQL("%s.%s", table, SQL.identifier(name_column))
        if not self.sudo().with_context(active_test=False).search_count(
            ['|', ('fg_use_ref_as_doc_no', '=', True), ('fg_truncate_seq_as_doc_no', '=', True)],
            limit=1,
        ):
            return name, SQL()
        base = SQL(
            "CASE WHEN fg_journal.fg_use_ref_as_doc_no THEN COALESCE(NULLIF(%s.ref, ''), %s) ELSE %s END",
            table, name, name,
        )
        number = SQL(
            "CASE WHEN fg_journal.fg_truncate_seq_as_doc_no THEN regexp_replace(%s, '/[0-9]+$', '') ELSE %s END",
            base, base,
        )
        join = SQL("JOIN account_journal fg_journal ON fg_journal.id = %s.journal_id", table)
        return number, join
