from calendar import monthrange
from datetime import timedelta
from xml.dom import minidom
from xml.etree import ElementTree as ET

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from .cdps_pdf import RT_OFF_BALANCE, CDPSPdf

BALANCE_FIELDS = (
    'opening_debit', 'opening_credit',
    'debit', 'credit',
    'closing_debit', 'closing_credit',
)
RESIDUAL_FIELDS = ('opening_debit', 'opening_credit', 'closing_debit', 'closing_credit')
PREV_FIELDS = tuple(f'prev_{fname}' for fname in BALANCE_FIELDS)
# Receivable and payable accounts whose balance is split by partner
PARTNER_ACCOUNT_PREFIXES = ('131', '331')


def _is_off_balance(code, account_type):
    """ Off-balance accounts: the Odoo account type, or a code starting with
    '0' (charts migrated from earlier versions). """
    return account_type == 'off_balance' or (code or '').startswith('0')


def _is_month_end(day):
    return day.day == monthrange(day.year, day.month)[1]


def _month_end(day):
    return day.replace(day=monthrange(day.year, day.month)[1])


class CDPSReport(models.AbstractModel):
    """ Trial balance (Bảng cân đối số phát sinh), with comparison to another
    period. """
    _name = 'vn.report.cdps'
    _inherit = 'vn.abstract.report'
    _description = 'Trial Balance'

    # ==================== REPORT DEFINITION ====================

    def _get_report_name(self):
        return _("TRIAL BALANCE")

    def _get_report_code(self):
        return 'Trial Balance'

    def _get_columns(self):
        return [
            {'name': 'code', 'label': _("Account"), 'type': 'char', 'width': 80},
            {'name': 'name', 'label': _("Account Name"), 'type': 'char', 'width': 250},
            {'name': 'opening_debit', 'label': _("Opening Debit"), 'type': 'monetary', 'width': 120},
            {'name': 'opening_credit', 'label': _("Opening Credit"), 'type': 'monetary', 'width': 120},
            {'name': 'debit', 'label': _("Debit"), 'type': 'monetary', 'width': 120},
            {'name': 'credit', 'label': _("Credit"), 'type': 'monetary', 'width': 120},
            {'name': 'closing_debit', 'label': _("Closing Debit"), 'type': 'monetary', 'width': 120},
            {'name': 'closing_credit', 'label': _("Closing Credit"), 'type': 'monetary', 'width': 120},
        ]

    def _get_comparison_columns(self):
        return [
            {'name': 'prev_closing_debit', 'label': _("Compared Closing Debit"), 'type': 'monetary', 'width': 110},
            {'name': 'prev_closing_credit', 'label': _("Compared Closing Credit"), 'type': 'monetary', 'width': 110},
            {'name': 'variance', 'label': _("Variance"), 'type': 'monetary', 'width': 110},
            {'name': 'variance_percent', 'label': '%', 'type': 'char', 'width': 60},
        ]

    def _get_pdf_rl_renderer(self):
        return CDPSPdf

    def _build_report_data(self, options):
        """ Add the comparison columns when a period is compared. """
        data = super()._build_report_data(options)
        lines = data.get('lines', [])
        if lines and lines[0].get('has_comparison'):
            data['columns'].extend(self._get_comparison_columns())
        return data

    # ==================== HIDDEN TRANSFER ACCOUNTS ====================

    def _get_hidden_transfer_ids(self, company):
        """ Ids of the accounts the company chose to hide when they have no
        balance (Circular 133: the chart has no account 113). """
        return set(company._fg_get_hidden_transfer_accounts().ids)

    # ==================== COMPARISON PERIOD ====================

    def _get_comparison_dates(self, date_from, date_to, comparison_type, options=None):
        """ Return the (date_from, date_to) of the compared period, or
        (None, None) when nothing is compared. """
        if comparison_type == 'previous_period':
            if date_from.day == 1 and _is_month_end(date_to):
                # whole months: the same number of whole months just before
                months = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month + 1
                return date_from - relativedelta(months=months), date_from - timedelta(days=1)
            # else the same number of days just before
            days = (date_to - date_from).days + 1
            prev_date_to = date_from - timedelta(days=1)
            return prev_date_to - timedelta(days=days - 1), prev_date_to

        if comparison_type == 'same_period_last_year':
            prev_date_to = date_to - relativedelta(years=1)
            if _is_month_end(date_to):
                prev_date_to = _month_end(prev_date_to)
            return date_from - relativedelta(years=1), prev_date_to

        if comparison_type == 'custom':
            options = options or {}
            prev_date_from = fields.Date.to_date(options.get('comparison_date_from'))
            prev_date_to = fields.Date.to_date(options.get('comparison_date_to'))
            if not prev_date_from or not prev_date_to:
                raise UserError(_("Please set the start and end dates of the compared period."))
            if prev_date_from > prev_date_to:
                raise UserError(_("The start date of the compared period must be before its end date."))
            return prev_date_from, prev_date_to

        return None, None

    def _get_comparison_label(self, comparison_type, prev_date_from, prev_date_to):
        if not prev_date_from or not prev_date_to:
            return ''
        labels = {
            'previous_period': _("Previous period"),
            'same_period_last_year': _("Same period last year"),
            'custom': _("Compared period"),
        }
        return "%s (%s - %s)" % (
            labels.get(comparison_type, _("Compared period")),
            prev_date_from.strftime('%d/%m/%Y'),
            prev_date_to.strftime('%d/%m/%Y'),
        )

    # ==================== BALANCES ====================

    def _flush_report_models(self):
        """ The figures are read with SQL: write the pending changes first. """
        self.env['account.move.line'].flush_model()
        self.env['account.account'].flush_model()

    def _compute_account_balances(self, date_from, date_to, company, account_ids=None):
        """ Opening balance, movements and closing balance of the active
        accounts of the company, from the posted journal items.

        The balance is on the debit side when debit exceeds credit, else on the
        credit side. For the receivable and payable accounts 131 and 331 it is
        computed per partner and not netted: the partners with a debit balance
        make the debit balance of the account, the others its credit balance.

        :return: {account_id: {account_id, code, name, account_type,
            parent_path, + BALANCE_FIELDS}}
        """
        self._flush_report_models()
        # `code` is stored per root company in the jsonb `code_store`; `name`
        # is a translated jsonb
        rows = self.env.execute_query_dict(SQL(
            """
            SELECT aa.id AS account_id,
                   aa.code_store->>%(root_id)s AS code,
                   COALESCE(aa.name->>%(lang)s, aa.name->>'en_US') AS name,
                   aa.account_type,
                   aa.parent_path,
                   COALESCE(SUM(aml.debit) FILTER (WHERE aml.date < %(date_from)s), 0) AS opening_debit,
                   COALESCE(SUM(aml.credit) FILTER (WHERE aml.date < %(date_from)s), 0) AS opening_credit,
                   COALESCE(SUM(aml.debit) FILTER (WHERE aml.date >= %(date_from)s), 0) AS debit,
                   COALESCE(SUM(aml.credit) FILTER (WHERE aml.date >= %(date_from)s), 0) AS credit
              FROM account_account aa
              JOIN account_account_res_company_rel rel
                ON rel.account_account_id = aa.id
               AND rel.res_company_id = %(company_id)s
         LEFT JOIN account_move_line aml
                ON aml.account_id = aa.id
               AND aml.parent_state = 'posted'
               AND aml.company_id = %(company_id)s
               AND aml.date <= %(date_to)s
             WHERE aa.active
               AND aa.code_store->>%(root_id)s IS NOT NULL
               %(account_filter)s
          GROUP BY aa.id
          ORDER BY code
            """,
            root_id=str(company.root_id.id),
            lang=self.env.lang or 'en_US',
            date_from=date_from,
            date_to=date_to,
            company_id=company.id,
            account_filter=SQL("AND aa.id IN %s", tuple(account_ids)) if account_ids else SQL(),
        ))

        partner_account_ids = [
            row['account_id'] for row in rows
            if row['code'].startswith(PARTNER_ACCOUNT_PREFIXES)
        ]
        partner_balances = self._compute_partner_balances(
            date_from, date_to, company, partner_account_ids,
        )

        result = {}
        for row in rows:
            account_id = row['account_id']
            if account_id in partner_balances:
                balances = partner_balances[account_id]
            else:
                opening = row['opening_debit'] - row['opening_credit']
                closing = opening + row['debit'] - row['credit']
                balances = {
                    'opening_debit': opening if opening > 0 else 0.0,
                    'opening_credit': -opening if opening < 0 else 0.0,
                    'closing_debit': closing if closing > 0 else 0.0,
                    'closing_credit': -closing if closing < 0 else 0.0,
                }
            result[account_id] = {
                'account_id': account_id,
                'code': row['code'],
                'name': row['name'] or '',
                'account_type': row['account_type'],
                'parent_path': row['parent_path'] or '',
                'debit': row['debit'],
                'credit': row['credit'],
                **balances,
            }
        return result

    def _compute_partner_balances(self, date_from, date_to, company, account_ids):
        """ Opening and closing balances of the given accounts, computed per
        partner then summed by side.

        :return: {account_id: {opening_debit, opening_credit, closing_debit, closing_credit}}
        """
        result = {
            account_id: dict.fromkeys(RESIDUAL_FIELDS, 0.0)
            for account_id in account_ids
        }
        if not account_ids:
            return result

        rows = self.env.execute_query(SQL(
            """
            SELECT aml.account_id,
                   COALESCE(SUM(aml.balance) FILTER (WHERE aml.date < %(date_from)s), 0) AS opening,
                   COALESCE(SUM(aml.balance), 0) AS closing
              FROM account_move_line aml
             WHERE aml.account_id IN %(account_ids)s
               AND aml.parent_state = 'posted'
               AND aml.company_id = %(company_id)s
               AND aml.date <= %(date_to)s
          GROUP BY aml.account_id, aml.partner_id
            """,
            date_from=date_from,
            date_to=date_to,
            company_id=company.id,
            account_ids=tuple(account_ids),
        ))
        for account_id, opening, closing in rows:
            balances = result[account_id]
            if opening > 0:
                balances['opening_debit'] += opening
            elif opening < 0:
                balances['opening_credit'] -= opening
            if closing > 0:
                balances['closing_debit'] += closing
            elif closing < 0:
                balances['closing_credit'] -= closing
        return result

    # ==================== LINES ====================

    @api.model
    def _get_lines(self, options):
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        company = self.env['res.company'].browse(options.get('company_id') or self.env.company.id)
        account_ids = options.get('account_ids') or None

        # the wizard sends hierarchy / show_zero_balance, the filters of the
        # screen show_hierarchy / hide_zero. The account level of the screen
        # (options['account_level']) is not read: it only hides rows there.
        show_hierarchy = bool(options.get('show_hierarchy', options.get('hierarchy', False)))
        if 'hide_zero' in options:
            show_zero = not options['hide_zero']
        else:
            show_zero = bool(options.get('show_zero_balance', False))
        comparison_type = options.get('comparison_type') or 'none'

        current = self._compute_account_balances(date_from, date_to, company, account_ids)

        prev_date_from, prev_date_to = self._get_comparison_dates(
            date_from, date_to, comparison_type, options,
        )
        has_comparison = bool(prev_date_from and prev_date_to)
        compared = {}
        if has_comparison:
            compared = self._compute_account_balances(prev_date_from, prev_date_to, company, account_ids)

        # Own figures of every account that can be displayed. Off-balance
        # accounts and hidden transfer accounts are dropped when they have no
        # opening nor closing balance, whatever their movements: once
        # reconciled, the transaction is over.
        hidden_transfer_ids = self._get_hidden_transfer_ids(company)
        accounts = {}
        for account_id, data in current.items():
            off_balance = _is_off_balance(data['code'], data['account_type'])
            if off_balance or account_id in hidden_transfer_ids:
                if not any(data[fname] for fname in RESIDUAL_FIELDS):
                    continue
            prev = compared.get(account_id, {})
            accounts[account_id] = {
                'id': 'account_%s' % account_id,
                'account_id': account_id,
                'code': data['code'],
                'name': data['name'],
                'account_type': data['account_type'],
                'is_off_balance': off_balance,
                'parent_path': data['parent_path'],
                **{fname: data[fname] for fname in BALANCE_FIELDS},
                **{f'prev_{fname}': prev.get(fname, 0) for fname in BALANCE_FIELDS},
            }

        # The grand total sums the own figures of the accounts: a parent
        # account and its children are never counted twice.
        totals = dict.fromkeys(BALANCE_FIELDS + PREV_FIELDS, 0)
        for account in accounts.values():
            for fname in totals:
                totals[fname] += account[fname]

        if show_hierarchy:
            lines = self._get_hierarchy_lines(accounts, show_zero)
        else:
            lines = self._get_flat_lines(accounts, show_zero)

        for line in lines:
            del line['parent_path']
            if has_comparison:
                line['variance'], line['variance_percent'] = self._get_variance(line)

        return [{
            'id': 'trial_balance',
            'name': _("Trial Balance"),
            'lines': lines,
            'totals': totals,
            'total_label': _("TOTAL"),
            'has_comparison': has_comparison,
            'show_hierarchy': show_hierarchy,
            'comparison_label': self._get_comparison_label(comparison_type, prev_date_from, prev_date_to),
        }]

    @staticmethod
    def _has_figures(line):
        return any(line[fname] for fname in BALANCE_FIELDS)

    @staticmethod
    def _get_variance(line):
        """ Variance of the closing balance against the compared period, and
        its percentage. """
        prev = line['prev_closing_debit'] - line['prev_closing_credit']
        curr = line['closing_debit'] - line['closing_credit']
        diff = curr - prev
        if prev:
            return diff, diff / abs(prev) * 100
        # nothing to compare with: the whole balance is the variance
        return diff, (100.0 if diff > 0 else -100.0) if diff else 0.0

    def _get_flat_lines(self, accounts, show_zero):
        """ One line per account with its own figures, ordered by code. """
        lines = []
        for account in sorted(accounts.values(), key=lambda a: a['code']):
            if show_zero or account['is_off_balance'] or self._has_figures(account):
                lines.append({
                    **account,
                    'level': 0,
                    'parent_id': None,
                    'is_parent': False,
                    'has_children': False,
                })
        return lines

    def _build_account_tree(self, accounts):
        """ Link the accounts along `account.account.parent_id`.

        The parent of an account is its nearest ancestor among `accounts`: an
        ancestor that is archived, dropped or out of the selection is skipped.

        :return: (children, roots) with `children` {account_id: [account_id]}
        """
        children = {account_id: [] for account_id in accounts}
        roots = []
        for account_id, account in accounts.items():
            ancestors = [int(i) for i in account['parent_path'].split('/') if i][:-1]
            parent_id = next((i for i in reversed(ancestors) if i in accounts), None)
            if parent_id:
                children[parent_id].append(account_id)
            else:
                roots.append(account_id)
        return children, roots

    def _get_hierarchy_lines(self, accounts, show_zero):
        """ Lines in the order of the account tree. The line of a parent
        account carries its own figures plus those of all its descendants. """
        children, roots = self._build_account_tree(accounts)
        summed = BALANCE_FIELDS + PREV_FIELDS

        def code_of(account_id):
            return accounts[account_id]['code']

        def build(account_id, level, parent_line_id):
            line = {**accounts[account_id], 'level': level, 'parent_id': parent_line_id}
            child_lines = []
            has_children = False
            for child_id in sorted(children[account_id], key=code_of):
                descendant_lines = build(child_id, level + 1, line['id'])
                if descendant_lines:
                    has_children = True
                    child_lines += descendant_lines
                    for fname in summed:
                        line[fname] += descendant_lines[0][fname]
            line['is_parent'] = line['has_children'] = has_children
            if not (show_zero or has_children or line['is_off_balance'] or self._has_figures(line)):
                return []
            return [line, *child_lines]

        lines = []
        for account_id in sorted(roots, key=code_of):
            lines += build(account_id, 0, None)
        return lines

    # ==================== DRILL DOWN ====================

    def _get_drill_down_action(self, options, params):
        """ Posted journal items of the account in the period. For a parent
        account, those of its child accounts too. """
        if not params.get('account_id'):
            return False
        domain = [
            ('account_id', 'child_of', params['account_id']),
            ('date', '>=', options['date']['date_from']),
            ('date', '<=', options['date']['date_to']),
            ('parent_state', '=', 'posted'),
            ('company_id', '=', options.get('company_id') or self.env.company.id),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _("Journal Items"),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    # ==================== XLSX EXPORT ====================

    def _groups_to_xlsx_rows(self, groups):
        if not groups:
            return []
        report = groups[0]
        totals = report.get('totals', {})
        has_comparison = report.get('has_comparison', False)

        rows = []
        for line in report.get('lines', []):
            cells = [
                ' ' * (line['level'] * 3) + line['code'],
                line['name'],
                *(line[fname] for fname in BALANCE_FIELDS),
            ]
            if has_comparison:
                cells += [
                    line['prev_closing_debit'],
                    line['prev_closing_credit'],
                    line['variance'],
                    f"{line['variance_percent']:+.1f}%",
                ]
            if line['is_parent']:
                row_type = 'group_hdr'
            elif line['is_off_balance']:
                row_type = RT_OFF_BALANCE
            else:
                row_type = 'data'
            rows.append({'type': row_type, 'cells': cells})

        total_cells = ['', report.get('total_label', ''), *(totals.get(fname, 0) for fname in BALANCE_FIELDS)]
        if has_comparison:
            total_cells += [totals.get('prev_closing_debit', 0), totals.get('prev_closing_credit', 0), '', '']
        rows.append({'type': 'grand_total', 'cells': total_cells})
        return rows

    # ==================== XML EXPORT ====================

    @api.model
    def get_xml(self, options):
        """ Return the XML appendix F01-CDTK (PL_CDTK) as bytes.

        It lists every active account with a code of 3 characters or more,
        without figures too, whatever the filters of the report. Off-balance
        accounts are left out. The tag of a parent account carries its own
        figures plus those of its descendants; `tongCong` sums the own figures
        of the accounts.
        """
        options = self._get_default_options(options or {})
        self._check_report_access(options)
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        company = self.env['res.company'].browse(options['company_id'])

        accounts = {
            account_id: data
            for account_id, data in self._compute_account_balances(date_from, date_to, company).items()
            if not _is_off_balance(data['code'], data['account_type'])
        }

        # a hidden transfer account without balance is not part of the total
        hidden_transfer_ids = self._get_hidden_transfer_ids(company)
        totals = dict.fromkeys(BALANCE_FIELDS, 0)
        for account_id, data in accounts.items():
            if len(data['code'].strip()) < 3:
                continue
            if account_id in hidden_transfer_ids and not any(data[fname] for fname in RESIDUAL_FIELDS):
                continue
            for fname in BALANCE_FIELDS:
                totals[fname] += data[fname]

        # own figures summed up to the ancestors
        summed = {account_id: {fname: data[fname] for fname in BALANCE_FIELDS} for account_id, data in accounts.items()}
        for account_id, data in accounts.items():
            for ancestor_id in [int(i) for i in data['parent_path'].split('/') if i][:-1]:
                if ancestor_id in summed:
                    for fname in BALANCE_FIELDS:
                        summed[ancestor_id][fname] += data[fname]

        values = {}
        for account_id, data in accounts.items():
            code = data['code'].strip()
            if len(code) >= 3:
                tag = 'ct' + ''.join(char for char in code if char.isalnum())
                values[tag] = summed[account_id]
        items = sorted(values.items()) + [('tongCong', totals)]

        root = ET.Element('PL_CDTK')
        sections = (
            ('SoDuDauKy', 'opening_debit', 'opening_credit'),
            ('SoPhatSinhTrongKy', 'debit', 'credit'),
            ('SoDuCuoiKy', 'closing_debit', 'closing_credit'),
        )
        for section_tag, debit_field, credit_field in sections:
            section = ET.SubElement(root, section_tag)
            debit_node = ET.SubElement(section, 'No')
            credit_node = ET.SubElement(section, 'Co')
            for tag, figures in items:
                ET.SubElement(debit_node, tag).text = str(int(round(figures[debit_field])))
                ET.SubElement(credit_node, tag).text = str(int(round(figures[credit_field])))

        document = minidom.parseString(ET.tostring(root, encoding='unicode'))
        return document.toprettyxml(indent='  ', encoding='utf-8')
