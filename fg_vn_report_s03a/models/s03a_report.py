from odoo import _, api, models
from odoo.tools import SQL

from .s03a_pdf import S03aPDF

# The journal is a single group of lines
GROUP_ID = 'journal'
NON_ACCOUNTING_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')
MOVE_TYPES = ('entry', 'out_invoice', 'in_invoice', 'out_refund', 'in_refund')


class S03aReport(models.AbstractModel):
    """ General journal (Sổ nhật ký chung, form S03a-DNN): the posted journal
    items of a period, in chronological order. """
    _name = 'vn.report.s03a'
    _inherit = 'vn.abstract.report'
    _description = 'General Journal (S03a-DNN)'

    # ==================== REPORT DEFINITION ====================

    def _get_report_name(self):
        return _("GENERAL JOURNAL")

    def _get_report_code(self):
        return _("Form No. S03a-DNN")

    def _get_export_filename_code(self, options):
        return 'S03a-DNN'

    def _get_columns(self):
        return [
            {'name': 'date', 'label': _("Date"), 'type': 'char', 'width': 85},
            {'name': 'move_name', 'label': _("Voucher No."), 'type': 'char', 'width': 120},
            {'name': 'description', 'label': _("Description"), 'type': 'char', 'width': 520},
            {'name': 'debit_account', 'label': _("Debit Account"), 'type': 'char', 'width': 80},
            {'name': 'credit_account', 'label': _("Credit Account"), 'type': 'char', 'width': 80},
            {'name': 'debit', 'label': _("Debit"), 'type': 'monetary', 'width': 130},
            {'name': 'credit', 'label': _("Credit"), 'type': 'monetary', 'width': 130},
        ]

    def _get_pdf_rl_renderer(self):
        return S03aPDF

    # ==================== SQL CONDITIONS ====================
    #
    # Every query reads `account_move_line line`, which stores the date, state,
    # company, journal and name of its entry: `account_move move` is joined
    # only when one of its own columns is needed.

    def _get_company(self, options):
        return self.env['res.company'].browse(options.get('company_id') or self.env.company.id)

    def _get_hidden_account_ids(self, options):
        """ Ids of the transfer accounts the company hides (Circular 133). """
        return self._get_company(options)._fg_get_hidden_transfer_accounts().ids

    def _get_move_type(self, options):
        move_type = options.get('move_type')
        return move_type if move_type in MOVE_TYPES else None

    def _get_move_conditions(self, options):
        """ Conditions selecting the entries of the journal. They never look
        at a single item, so that an entry is in or out as a whole. """
        conditions = [SQL(
            "line.company_id = %s AND line.parent_state = 'posted' AND line.date >= %s AND line.date <= %s",
            self._get_company(options).id, options['date']['date_from'], options['date']['date_to'],
        )]
        if options.get('journal_ids'):
            conditions.append(SQL("line.journal_id = ANY(%s)", list(options['journal_ids'])))
        if self._get_move_type(options):
            conditions.append(SQL("move.move_type = %s", self._get_move_type(options)))
        return SQL(" AND ").join(conditions)

    def _get_line_conditions(self, options):
        """ Conditions selecting the items shown among those of the entries:

        - accounting items with an amount (no section, note or zero item);
        - not a reconciled item on a hidden transfer account;
        - on the selected accounts and partners;
        - matching the text searched on the server.
        """
        conditions = [SQL(
            "(line.display_type IS NULL OR line.display_type NOT IN %s) AND (line.debit != 0 OR line.credit != 0)",
            NON_ACCOUNTING_DISPLAY_TYPES,
        )]
        hidden_account_ids = self._get_hidden_account_ids(options)
        if hidden_account_ids:
            conditions.append(SQL(
                "NOT (line.account_id = ANY(%s) AND line.full_reconcile_id IS NOT NULL)",
                hidden_account_ids,
            ))
        if options.get('account_ids'):
            conditions.append(SQL("line.account_id = ANY(%s)", list(options['account_ids'])))
        if options.get('partner_ids'):
            conditions.append(SQL("line.partner_id = ANY(%s)", list(options['partner_ids'])))
        search = (options.get('search') or '').strip()
        if search:
            pattern = '%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            conditions.append(SQL(
                "(line.move_name ILIKE %(pattern)s OR line.name ILIKE %(pattern)s OR %(code)s ILIKE %(pattern)s)",
                pattern=pattern, code=self._get_account_code_sql(options),
            ))
        return SQL(" AND ").join(conditions)

    def _get_account_code_sql(self, options):
        # the code of an account is stored per root company
        return SQL("account.code_store->>%s", str(self._get_company(options).root_id.id))

    def _get_from_sql(self, options, with_account=False):
        joins = [SQL("account_move_line line")]
        if self._get_move_type(options):
            joins.append(SQL("JOIN account_move move ON move.id = line.move_id"))
        if with_account or (options.get('search') or '').strip():
            joins.append(SQL("JOIN account_account account ON account.id = line.account_id"))
        return SQL(" ").join(joins)

    def _flush(self):
        """ The figures are read with SQL: write the pending changes first. """
        self.env['account.move.line'].flush_model()
        self.env['account.move'].flush_model()
        self.env['account.account'].flush_model()

    # ==================== QUERIES ====================

    def _count_lines(self, options):
        self._flush()
        return self.env.execute_query(SQL(
            "SELECT COUNT(*) FROM %s WHERE %s AND %s",
            self._get_from_sql(options),
            self._get_move_conditions(options),
            self._get_line_conditions(options),
        ))[0][0]

    def _get_totals(self, options):
        self._flush()
        debit, credit = self.env.execute_query(SQL(
            "SELECT COALESCE(SUM(line.debit), 0), COALESCE(SUM(line.credit), 0) FROM %s WHERE %s AND %s",
            self._get_from_sql(options),
            self._get_move_conditions(options),
            self._get_line_conditions(options),
        ))[0]
        return {'debit': debit, 'credit': credit}

    def _get_ordered_moves(self, options):
        """ The entries of the journal that have items to show, in the order
        of the journal.

        Entries are sorted by date then number. Those meeting on a hidden
        transfer account are numbered and placed as one operation, by
        `account.move._fg_get_transfer_links()`.

        :return: list of (move id, number to print, count of items shown)
        """
        self._flush()
        hidden_account_ids = self._get_hidden_account_ids(options)
        rows = self.env.execute_query(SQL(
            """
            SELECT line.move_id,
                   MIN(line.date),
                   MIN(line.move_name),
                   COUNT(*) FILTER (WHERE %(line_conditions)s),
                   COALESCE(BOOL_OR(line.account_id = ANY(%(hidden_account_ids)s)
                                    AND line.full_reconcile_id IS NOT NULL), FALSE)
              FROM %(from_sql)s
             WHERE %(move_conditions)s
          GROUP BY line.move_id
            HAVING COUNT(*) FILTER (WHERE %(line_conditions)s) > 0
            """,
            from_sql=self._get_from_sql(options),
            move_conditions=self._get_move_conditions(options),
            line_conditions=self._get_line_conditions(options),
            hidden_account_ids=hidden_account_ids,
        ))

        Move = self.env['account.move']
        linked_ids = [move_id for move_id, _date, _name, _count, linked in rows if linked]
        links = Move.browse(linked_ids)._fg_get_transfer_links()

        moves = []
        for move_id, date, name, line_count, _linked in rows:
            link = links.get(move_id)
            if link:
                moves.append((link['sort_key'], move_id, link['display_name'], line_count))
            else:
                moves.append((Move._fg_transfer_default_sort_key(date, name), move_id, name or '', line_count))
        moves.sort()
        return [(move_id, name, line_count) for _key, move_id, name, line_count in moves]

    def _query_lines(self, options, move_names):
        """ The items to show of the given entries, as report lines, in the
        order of `move_names` then in the order the items were entered.

        :param dict move_names: {move id: number to print}, ordered
        """
        if not move_names:
            return []
        self._flush()
        rows = self.env.execute_query_dict(SQL(
            """
            SELECT line.id,
                   line.move_id,
                   line.date,
                   move.invoice_date,
                   COALESCE(NULLIF(line.name, ''), move.ref, '') AS description,
                   %(account_code)s AS account_code,
                   line.debit,
                   line.credit
              FROM account_move_line line
              JOIN account_move move ON move.id = line.move_id
              JOIN account_account account ON account.id = line.account_id
             WHERE line.move_id = ANY(%(move_ids)s)
               AND %(line_conditions)s
          ORDER BY line.id
            """,
            account_code=self._get_account_code_sql(options),
            move_ids=list(move_names),
            line_conditions=self._get_line_conditions(options),
        ))
        lines_by_move = {}
        for row in rows:
            lines_by_move.setdefault(row['move_id'], []).append(row)

        lines = []
        for move_id, move_name in move_names.items():
            for row in lines_by_move.get(move_id, ()):
                lines.append({
                    'id': 'line_%s' % row['id'],
                    'move_id': move_id,
                    'date': row['date'],
                    'date_display': self._format_date_display(row['date'], row['invoice_date']),
                    'move_name': move_name,
                    'description': row['description'],
                    'account_code': row['account_code'] or '',
                    'debit': row['debit'],
                    'credit': row['credit'],
                })
        return lines

    def _format_date_display(self, date, invoice_date):
        """ The accounting date, followed by the invoice date in brackets
        when they differ. """
        if not date:
            return ''
        text = date.strftime('%Y/%m/%d')
        if invoice_date and invoice_date != date:
            text += " (%s)" % invoice_date.strftime('%Y/%m/%d')
        return text

    # ==================== LINES ====================

    def _get_group(self, options, line_count):
        return {
            'id': GROUP_ID,
            'name': '',
            'total': self._get_totals(options),
            'total_label': _("Total"),
            'line_count': line_count,
        }

    @api.model
    def _get_lines(self, options):
        moves = self._get_ordered_moves(options)
        lines = self._query_lines(options, {move_id: name for move_id, name, _count in moves})
        return [{**self._get_group(options, len(lines)), 'lines': lines}]

    # Long journals are loaded by chunks: see the base report.

    def _get_group_summaries(self, options):
        return [{**self._get_group(options, self._count_lines(options)), 'preload': True}]

    def _get_group_lines(self, options, group_id, offset, limit):
        """ The entries are sorted first, then only the items of the entries
        covering the chunk are read. An entry is never cut: the chunk ends
        with the entry that reaches `limit`. """
        move_names = {}
        position = taken = 0
        for move_id, name, line_count in self._get_ordered_moves(options):
            if position >= offset:
                move_names[move_id] = name
                taken += line_count
                if taken >= limit:
                    break
            position += line_count
        return self._query_lines(options, move_names)

    # ==================== DRILL DOWN ====================

    def _get_drill_down_action(self, options, params):
        if not params.get('move_id'):
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Entry"),
            'res_model': 'account.move',
            'res_id': params['move_id'],
            'view_mode': 'form',
            'target': 'current',
        }

    # ==================== XLSX EXPORT ====================

    def _groups_to_xlsx_rows(self, groups):
        if not groups:
            return []
        group = groups[0]
        rows = [
            {
                'type': 'data',
                'cells': [
                    line['date_display'],
                    line['move_name'],
                    line['description'],
                    line['account_code'] if line['debit'] else '',
                    line['account_code'] if line['credit'] else '',
                    line['debit'],
                    line['credit'],
                ],
            }
            for line in group['lines']
        ]
        rows.append({
            'type': 'grand_total',
            'cells': ['', '', group['total_label'], '', '', group['total']['debit'], group['total']['credit']],
        })
        return rows
