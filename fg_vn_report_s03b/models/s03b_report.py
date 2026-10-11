from odoo import _, api, models
from odoo.tools import SQL

from .s03b_pdf import S03bPDF

NON_ACCOUNTING_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')
# value of the account type filter -> pattern of `account.account.account_type`
ACCOUNT_TYPE_PATTERNS = {
    'asset': 'asset_%',
    'liability': 'liability_%',
    'equity': 'equity%',
    'income': 'income%',
    'expense': 'expense%',
}
EMPTY_ACCOUNTS = ('hide', 'with_balance', 'all')


def _is_off_balance(code, account_type):
    """ Off-balance accounts: the Odoo account type, or a code starting with
    '0' (charts migrated from earlier versions). """
    return account_type == 'off_balance' or (code or '').startswith('0')


def _split_balance(balance):
    """ A balance (debit - credit) on its side. """
    return {
        'debit': balance if balance > 0 else 0.0,
        'credit': -balance if balance < 0 else 0.0,
    }


class S03bReport(models.AbstractModel):
    """ General ledger (Sổ cái tài khoản, form S03b-DNN): for each account,
    the opening balance, the journal items of the period with their
    counterpart accounts, and the closing balance. """
    _name = 'vn.report.s03b'
    _inherit = 'vn.abstract.report'
    _description = 'General Ledger (S03b-DNN)'

    # ==================== REPORT DEFINITION ====================

    def _get_report_name(self):
        return _("GENERAL LEDGER")

    def _get_report_code(self):
        return _("Form No. S03b-DNN")

    def _get_export_filename_code(self, options):
        return 'S03b-DNN'

    def _get_columns(self):
        return [
            {'name': 'date', 'label': _("Date"), 'type': 'char', 'width': 90},
            {'name': 'move_name', 'label': _("Voucher No."), 'type': 'char', 'width': 120},
            {'name': 'description', 'label': _("Description"), 'type': 'char', 'width': 600},
            {'name': 'counterpart_account', 'label': _("Counterpart Account"), 'type': 'char', 'width': 110},
            {'name': 'debit', 'label': _("Debit"), 'type': 'monetary', 'width': 130},
            {'name': 'credit', 'label': _("Credit"), 'type': 'monetary', 'width': 130},
        ]

    def _get_pdf_rl_renderer(self):
        return S03bPDF

    # ==================== OPTIONS ====================

    def _get_company(self, options):
        return self.env['res.company'].browse(options.get('company_id') or self.env.company.id)

    def _get_hidden_account_ids(self, options):
        """ Ids of the transfer accounts the company hides (Circular 133). """
        return self._get_company(options)._fg_get_hidden_transfer_accounts().ids

    def _get_empty_accounts(self, options):
        """ What to do with the accounts without journal items in the period:
        'hide' them, keep those 'with_balance', or keep them 'all'. """
        value = options.get('empty_accounts')
        if value in EMPTY_ACCOUNTS:
            return value
        # option of the versions before 20.0
        return 'all' if options.get('show_zero_balance') else 'hide'

    def _is_split(self, options):
        return bool(options.get('split_counterparts'))

    def _get_accounts(self, options):
        """ The accounts the ledger is asked for, ordered by code.

        :return: list of dicts {id, code, name, account_type}
        """
        company = self._get_company(options)
        domain = [('company_ids', 'in', company.ids)]
        if options.get('account_ids'):
            domain.append(('id', 'in', options['account_ids']))
        pattern = ACCOUNT_TYPE_PATTERNS.get(options.get('account_type'))
        if pattern:
            domain.append(('account_type', '=like', pattern))
        accounts = self.env['account.account'].with_company(company).search(domain)
        result = [
            {'id': account.id, 'code': account.code or '', 'name': account.name, 'account_type': account.account_type}
            for account in accounts
        ]
        result.sort(key=lambda account: account['code'])
        return result

    # ==================== SQL ====================
    #
    # Every query reads `account_move_line line`, which stores the date, state,
    # company, journal and name of its entry, and has an index on
    # (account_id, date). No query is run per account.

    def _flush(self):
        """ The figures are read with SQL: write the pending changes first. """
        for model in ('account.move.line', 'account.move', 'account.account', 'account.move.line.ctp'):
            self.env[model].flush_model()

    def _get_item_conditions(self, options, account_ids):
        """ Conditions on the journal items of the ledger, whatever their
        date: posted, of the company, on the accounts, with an amount, and
        matching the partner and journal filters. """
        conditions = [SQL(
            """line.company_id = %s AND line.parent_state = 'posted' AND line.account_id = ANY(%s)
               AND (line.display_type IS NULL OR line.display_type NOT IN %s)
               AND (line.debit != 0 OR line.credit != 0)""",
            self._get_company(options).id, list(account_ids), NON_ACCOUNTING_DISPLAY_TYPES,
        )]
        if options.get('partner_ids'):
            conditions.append(SQL("line.partner_id = ANY(%s)", list(options['partner_ids'])))
        if options.get('journal_ids'):
            conditions.append(SQL("line.journal_id = ANY(%s)", list(options['journal_ids'])))
        return SQL(" AND ").join(conditions)

    def _get_period_conditions(self, options, account_ids):
        return SQL(
            "%s AND line.date >= %s AND line.date <= %s",
            self._get_item_conditions(options, account_ids),
            options['date']['date_from'], options['date']['date_to'],
        )

    def _get_account_code_sql(self, options, alias):
        # the code of an account is stored per root company
        return SQL("%s.code_store->>%s", SQL.identifier(alias), str(self._get_company(options).root_id.id))

    def _count_lines(self, options):
        """ Journal items of the period on the accounts of the ledger. With
        the counterparts split, the ledger has more lines than that: this is
        the cheap count used to decide how to load and whether to print. """
        account_ids = [account['id'] for account in self._get_accounts(options)]
        if not account_ids:
            return 0
        self._flush()
        return self.env.execute_query(SQL(
            "SELECT COUNT(*) FROM account_move_line line WHERE %s",
            self._get_period_conditions(options, account_ids),
        ))[0][0]

    def _get_account_figures(self, options, account_ids):
        """ Opening balance, totals of the period and count of items of every
        account, in one query.

        :return: {account_id: {opening, debit, credit, line_count}} for the
            accounts having journal items up to the end of the period;
            `opening` is debit - credit before the period
        """
        if not account_ids:
            return {}
        self._flush()
        date_from = options['date']['date_from']
        rows = self.env.execute_query(SQL(
            """
            SELECT line.account_id,
                   COALESCE(SUM(line.balance) FILTER (WHERE line.date < %(date_from)s), 0),
                   COALESCE(SUM(line.debit) FILTER (WHERE line.date >= %(date_from)s), 0),
                   COALESCE(SUM(line.credit) FILTER (WHERE line.date >= %(date_from)s), 0),
                   COUNT(*) FILTER (WHERE line.date >= %(date_from)s)
              FROM account_move_line line
             WHERE %(conditions)s
               AND line.date <= %(date_to)s
          GROUP BY line.account_id
            """,
            date_from=date_from,
            date_to=options['date']['date_to'],
            conditions=self._get_item_conditions(options, account_ids),
        ))
        return {
            account_id: {'opening': opening, 'debit': debit, 'credit': credit, 'line_count': line_count}
            for account_id, opening, debit, credit, line_count in rows
        }

    def _get_rows_sql(self, options, account_ids):
        """ Query of the rows of the ledger for the given accounts: one row
        per journal item, or one row per counterpart account of each item
        when the counterparts are split.

        Columns: line_id, account_id, move_id, date, move_name, name, debit,
        credit, counterpart_ids (array of account ids), part_code (code of
        the counterpart account of a split row, to order them).
        """
        conditions = self._get_period_conditions(options, account_ids)
        if not self._is_split(options):
            return SQL(
                """
                SELECT line.id AS line_id, line.account_id, line.move_id, line.date,
                       line.move_name, line.name, line.debit, line.credit,
                       ARRAY(SELECT rel.account_id
                               FROM account_move_line_countered_account_rel rel
                              WHERE rel.aml_id = line.id) AS counterpart_ids,
                       NULL::varchar AS part_code
                  FROM account_move_line line
                 WHERE %s
                """,
                conditions,
            )
        # An item is split along `account.move.line.ctp`: the pairs having the
        # same counterpart account are summed, and what is not countered (no
        # counterpart, or a partial one) makes a last row without account, so
        # that the rows of an item always add up to its amount.
        return SQL(
            """
            WITH items AS (
                SELECT line.id AS line_id, line.account_id, line.move_id, line.date,
                       line.move_name, line.name, line.debit, line.credit
                  FROM account_move_line line
                 WHERE %(conditions)s
            ),
            pairs AS (
                SELECT items.line_id, ctp.cr_account_id AS counterpart_id, SUM(ctp.countered_amt) AS amount
                  FROM items
                  JOIN account_move_line_ctp ctp ON ctp.dr_aml_id = items.line_id
              GROUP BY items.line_id, ctp.cr_account_id
             UNION ALL
                SELECT items.line_id, ctp.dr_account_id, SUM(ctp.countered_amt)
                  FROM items
                  JOIN account_move_line_ctp ctp ON ctp.cr_aml_id = items.line_id
              GROUP BY items.line_id, ctp.dr_account_id
            ),
            parts AS (
                SELECT line_id, counterpart_id, amount FROM pairs
             UNION ALL
                SELECT items.line_id, NULL, items.debit + items.credit - COALESCE(countered.amount, 0)
                  FROM items
             LEFT JOIN (SELECT line_id, SUM(amount) AS amount FROM pairs GROUP BY line_id) countered
                    ON countered.line_id = items.line_id
                 WHERE items.debit + items.credit - COALESCE(countered.amount, 0) != 0
            )
            SELECT items.line_id, items.account_id, items.move_id, items.date,
                   items.move_name, items.name,
                   CASE WHEN items.debit != 0 THEN parts.amount ELSE 0 END AS debit,
                   CASE WHEN items.debit != 0 THEN 0 ELSE parts.amount END AS credit,
                   CASE WHEN parts.counterpart_id IS NULL THEN ARRAY[]::integer[]
                        ELSE ARRAY[parts.counterpart_id] END AS counterpart_ids,
                   %(part_code)s AS part_code
              FROM parts
              JOIN items ON items.line_id = parts.line_id
         LEFT JOIN account_account counterpart ON counterpart.id = parts.counterpart_id
            """,
            conditions=conditions,
            part_code=self._get_account_code_sql(options, 'counterpart'),
        )

    def _get_row_counts(self, options, account_ids):
        """ Exact count of rows per account, when the counterparts are split. """
        rows = self.env.execute_query(SQL(
            "SELECT rows.account_id, COUNT(*) FROM (%s) rows GROUP BY rows.account_id",
            self._get_rows_sql(options, account_ids),
        ))
        return dict(rows)

    def _query_rows(self, options, account_ids, offset=None, limit=None):
        """ Read the rows of the ledger, ordered by account, date, voucher
        number and entry order. `offset` and `limit` page through the rows of
        a single account.

        :return: (rows, balance_before) with `balance_before` the sum of
            debit - credit of the rows skipped by `offset`
        """
        self._flush()
        rows_sql = self._get_rows_sql(options, account_ids)
        order = SQL("rows.account_id, rows.date, rows.move_name, rows.line_id, rows.part_code NULLS LAST")
        balance_before = 0.0
        if offset:
            balance_before = self.env.execute_query(SQL(
                """
                SELECT COALESCE(SUM(skipped.debit - skipped.credit), 0)
                  FROM (SELECT rows.debit, rows.credit FROM (%s) rows ORDER BY %s LIMIT %s) skipped
                """,
                rows_sql, order, offset,
            ))[0][0]
        rows = self.env.execute_query_dict(SQL(
            """
            SELECT rows.*,
                   move.invoice_date,
                   COALESCE(NULLIF(rows.name, ''), move.ref, '') AS description
              FROM (%(rows)s) rows
              JOIN account_move move ON move.id = rows.move_id
          ORDER BY %(order)s
             %(paging)s
            """,
            rows=rows_sql,
            order=order,
            paging=SQL("LIMIT %s OFFSET %s", limit, offset or 0) if limit else SQL(),
        ))
        return rows, balance_before

    # ==================== HIDDEN TRANSFER ACCOUNTS ====================

    def _get_real_counterparts(self, line_ids, hidden_account_ids):
        """ For the journal items whose counterpart is a hidden transfer
        account, find the accounts at the other end of the transfer.

        Cash deposited at the bank: CASH/001 Dr 113 / Cr 1111 and BANK/001
        Dr 1121 / Cr 113, the two items on 113 being reconciled. The real
        counterpart of the 1111 item is 1121. Three steps:

        1. the counterpart item of the journal item that is on a hidden
           account (the 113 item of CASH/001);
        2. the item reconciled with it, on the same account and on the
           opposite side (the 113 item of BANK/001); the side condition keeps
           out the other cash entries merged into the same bank entry;
        3. the counterpart accounts of that item (1121).

        A hidden item that is not fully reconciled has no other end: its
        account stays the counterpart, so that the pending amount is visible.

        :return: {(line id, hidden account id): [real account ids]}
        """
        if not line_ids or not hidden_account_ids:
            return {}
        rows = self.env.execute_query(SQL(
            """
            WITH hidden_pairs AS (
                SELECT ctp.dr_aml_id AS source_id, ctp.cr_aml_id AS hidden_line_id
                  FROM account_move_line_ctp ctp
                 WHERE ctp.dr_aml_id = ANY(%(line_ids)s) AND ctp.cr_account_id = ANY(%(hidden_ids)s)
             UNION ALL
                SELECT ctp.cr_aml_id, ctp.dr_aml_id
                  FROM account_move_line_ctp ctp
                 WHERE ctp.cr_aml_id = ANY(%(line_ids)s) AND ctp.dr_account_id = ANY(%(hidden_ids)s)
            )
            SELECT pair.source_id, hidden.account_id, ARRAY_AGG(DISTINCT rel.account_id)
              FROM hidden_pairs pair
              JOIN account_move_line hidden ON hidden.id = pair.hidden_line_id
              JOIN account_move_line other
                ON other.full_reconcile_id = hidden.full_reconcile_id
               AND other.id != hidden.id
               AND other.account_id = hidden.account_id
               AND (
                    (hidden.credit > 0 AND other.debit > 0)
                    OR (hidden.debit > 0 AND other.credit > 0)
               )
              JOIN account_move_line_countered_account_rel rel ON rel.aml_id = other.id
             WHERE hidden.full_reconcile_id IS NOT NULL
               AND NOT rel.account_id = ANY(%(hidden_ids)s)
          GROUP BY pair.source_id, hidden.account_id
            """,
            line_ids=list(line_ids),
            hidden_ids=list(hidden_account_ids),
        ))
        return {(line_id, account_id): real_ids for line_id, account_id, real_ids in rows}

    def _get_linked_move_names(self, move_ids, hidden_account_ids):
        """ Numbers to print for the entries meeting on a hidden transfer
        account ("BANK/001 (CASH/001)"); the other entries are not returned. """
        if not move_ids or not hidden_account_ids:
            return {}
        linked_ids = [move_id for move_id, in self.env.execute_query(SQL(
            """
            SELECT DISTINCT line.move_id
              FROM account_move_line line
             WHERE line.move_id = ANY(%s)
               AND line.account_id = ANY(%s)
               AND line.full_reconcile_id IS NOT NULL
            """,
            list(move_ids), list(hidden_account_ids),
        ))]
        links = self.env['account.move'].browse(linked_ids)._fg_get_transfer_links()
        return {move_id: link['display_name'] for move_id, link in links.items()}

    # ==================== LINES ====================

    def _format_date_display(self, date, invoice_date):
        """ The accounting date, followed by the invoice date in brackets
        when they differ. """
        if not date:
            return ''
        text = date.strftime('%Y/%m/%d')
        if invoice_date and invoice_date != date:
            text += " (%s)" % invoice_date.strftime('%Y/%m/%d')
        return text

    def _rows_to_lines(self, options, rows, balances):
        """ Turn the rows read by `_query_rows` into report lines.

        :param dict balances: {account_id: balance before the first row};
            updated with the balance after the last row of each account
        :return: {account_id: [lines]}
        """
        hidden_account_ids = set(self._get_hidden_account_ids(options))
        real_counterparts = {}
        move_names = {}
        if hidden_account_ids:
            real_counterparts = self._get_real_counterparts(
                {row['line_id'] for row in rows if hidden_account_ids.intersection(row['counterpart_ids'])},
                hidden_account_ids,
            )
            move_names = self._get_linked_move_names({row['move_id'] for row in rows}, hidden_account_ids)

        counterpart_ids_by_row = []
        for row in rows:
            counterpart_ids = set()
            for account_id in row['counterpart_ids']:
                counterpart_ids.update(real_counterparts.get((row['line_id'], account_id), [account_id]))
            counterpart_ids_by_row.append(counterpart_ids)
        codes = self._get_account_codes(options, set().union(*counterpart_ids_by_row) if rows else set())

        lines = {}
        for row, counterpart_ids in zip(rows, counterpart_ids_by_row):
            account_id = row['account_id']
            balances[account_id] = balances.get(account_id, 0.0) + row['debit'] - row['credit']
            line_id = 'line_%s' % row['line_id']
            if self._is_split(options):
                # an item makes several lines: one per counterpart account
                line_id += '_%s' % (row['counterpart_ids'][0] if row['counterpart_ids'] else 0)
            lines.setdefault(account_id, []).append({
                'id': line_id,
                'move_id': row['move_id'],
                'date': row['date'],
                'date_display': self._format_date_display(row['date'], row['invoice_date']),
                'move_name': move_names.get(row['move_id']) or row['move_name'] or '',
                'description': row['description'],
                'counterpart_account': ', '.join(sorted(codes[account_id] for account_id in counterpart_ids)),
                'debit': row['debit'],
                'credit': row['credit'],
                # running balance (debit - credit); no column prints it
                'balance': balances[account_id],
            })
        return lines

    def _get_account_codes(self, options, account_ids):
        if not account_ids:
            return {}
        rows = self.env.execute_query(SQL(
            "SELECT account.id, COALESCE(%s, '') FROM account_account account WHERE account.id = ANY(%s)",
            self._get_account_code_sql(options, 'account'), list(account_ids),
        ))
        return dict(rows)

    def _get_groups(self, options):
        """ The accounts of the ledger with their figures, without lines.

        An account is in the ledger when it has journal items in the period,
        or according to the option on the accounts without items. Off-balance
        accounts and hidden transfer accounts are in only when they have an
        opening or a closing balance, unless the user selected the accounts.
        """
        accounts = self._get_accounts(options)
        account_ids = [account['id'] for account in accounts]
        figures = self._get_account_figures(options, account_ids)
        empty_accounts = self._get_empty_accounts(options)
        hidden_account_ids = set(self._get_hidden_account_ids(options))
        selected = bool(options.get('account_ids'))

        groups = []
        for account in accounts:
            values = figures.get(account['id'], {'opening': 0.0, 'debit': 0.0, 'credit': 0.0, 'line_count': 0})
            opening = values['opening']
            closing = opening + values['debit'] - values['credit']
            if not values['line_count'] and not (
                empty_accounts == 'all' or (empty_accounts == 'with_balance' and opening)
            ):
                continue
            if not selected and not (opening or closing) and (
                account['id'] in hidden_account_ids or _is_off_balance(account['code'], account['account_type'])
            ):
                continue
            name = "%s - %s" % (account['code'], account['name'])
            groups.append({
                'id': 'account_%s' % account['id'],
                'account_id': account['id'],
                'code': account['code'],
                'name': name,
                'label': _("Account: %s", name),
                'opening': _split_balance(opening),
                'opening_balance': opening,
                'total': {'debit': values['debit'], 'credit': values['credit']},
                'closing': _split_balance(closing),
                'opening_label': _("Opening balance"),
                'total_label': _("Total of the period"),
                'closing_label': _("Closing balance"),
                'line_count': values['line_count'],
            })

        if self._is_split(options) and groups:
            counts = self._get_row_counts(options, [group['account_id'] for group in groups])
            for group in groups:
                group['line_count'] = counts.get(group['account_id'], 0)
        return groups

    @api.model
    def _get_lines(self, options):
        groups = self._get_groups(options)
        account_ids = [group['account_id'] for group in groups if group['line_count']]
        lines = {}
        if account_ids:
            rows, _balance = self._query_rows(options, account_ids)
            balances = {group['account_id']: group['opening_balance'] for group in groups}
            lines = self._rows_to_lines(options, rows, balances)
        for group in groups:
            group['lines'] = lines.get(group['account_id'], [])
        return groups

    # Long ledgers are loaded account by account: see the base report.

    def _get_group_summaries(self, options):
        return self._get_groups(options)

    def _get_group_lines(self, options, group_id, offset, limit):
        try:
            account_id = int(str(group_id).removeprefix('account_'))
        except ValueError:
            return []
        accounts = [account for account in self._get_accounts(options) if account['id'] == account_id]
        if not accounts:
            return []
        rows, balance_before = self._query_rows(options, [account_id], offset=offset, limit=limit)
        figures = self._get_account_figures(options, [account_id]).get(account_id, {})
        balances = {account_id: figures.get('opening', 0.0) + balance_before}
        return self._rows_to_lines(options, rows, balances).get(account_id, [])

    # ==================== DRILL DOWN ====================

    def _get_drill_down_action(self, options, params):
        """ A line opens its journal entry; an account opens its journal
        items of the period, with the filters of the ledger. """
        if params.get('move_id'):
            return {
                'type': 'ir.actions.act_window',
                'name': _("Journal Entry"),
                'res_model': 'account.move',
                'res_id': params['move_id'],
                'view_mode': 'form',
                'target': 'current',
            }
        if not params.get('account_id'):
            return False
        domain = [
            ('account_id', '=', params['account_id']),
            ('date', '>=', options['date']['date_from']),
            ('date', '<=', options['date']['date_to']),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', self._get_company(options).id),
        ]
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))
        if options.get('journal_ids'):
            domain.append(('journal_id', 'in', options['journal_ids']))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Items"),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    # ==================== XLSX EXPORT ====================

    def _should_xlsx_split_by_group(self):
        return True

    def _format_xlsx_group_label(self, group):
        return group['label']

    def _group_to_xlsx_rows(self, group):
        rows = [{
            'type': 'opening',
            'cells': ['', '', group['opening_label'], '', group['opening']['debit'], group['opening']['credit']],
        }]
        rows += [
            {
                'type': 'data',
                'cells': [
                    line['date_display'], line['move_name'], line['description'],
                    line['counterpart_account'], line['debit'], line['credit'],
                ],
            }
            for line in group['lines']
        ]
        rows.append({
            'type': 'group_total',
            'cells': ['', '', group['total_label'], '', group['total']['debit'], group['total']['credit']],
        })
        rows.append({
            'type': 'closing',
            'cells': ['', '', group['closing_label'], '', group['closing']['debit'], group['closing']['credit']],
        })
        return rows

    def _set_xlsx_column_widths(self, sheet, columns):
        for column, width in enumerate((14, 16, 55, 14, 15, 15)):
            sheet.set_column(column, column, width)
