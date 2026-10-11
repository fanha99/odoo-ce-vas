from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_DATA, RT_GRAND_TOTAL, RT_GROUP_HDR, FanhaReportPDF,
)

# Row type of the off-balance accounts, on a light orange background
RT_OFF_BALANCE = 'off_balance'

AMOUNT_FIELDS = (
    'opening_debit', 'opening_credit',
    'debit', 'credit',
    'closing_debit', 'closing_credit',
)


class CDPSPdf(FanhaReportPDF):
    """ PDF of the trial balance: no running totals carried from page to page,
    no signatures. """

    def __init__(self, report_data, env):
        lines = report_data.get('lines', [])
        self.has_comparison = lines[0].get('has_comparison', False) if lines else False
        super().__init__(report_data, env)

    def _get_col_specs(self):
        _ = self.env._
        if not self.has_comparison:
            return [
                {'label': _("Account"), 'width': 50, 'align': 'L'},
                {'label': _("Account Name"), 'width': 175, 'align': 'L'},
                {'label': _("Opening Debit"), 'width': 90, 'align': 'R'},
                {'label': _("Opening Credit"), 'width': 90, 'align': 'R'},
                {'label': _("Debit"), 'width': 90, 'align': 'R'},
                {'label': _("Credit"), 'width': 90, 'align': 'R'},
                {'label': _("Closing Debit"), 'width': 90, 'align': 'R'},
                {'label': _("Closing Credit"), 'width': 90, 'align': 'R'},
            ]
        return [
            {'label': _("Account"), 'width': 45, 'align': 'L'},
            {'label': _("Account Name"), 'width': 140, 'align': 'L'},
            {'label': _("Opening Debit"), 'width': 65, 'align': 'R'},
            {'label': _("Opening Credit"), 'width': 65, 'align': 'R'},
            {'label': _("Debit"), 'width': 65, 'align': 'R'},
            {'label': _("Credit"), 'width': 65, 'align': 'R'},
            {'label': _("Closing Debit"), 'width': 65, 'align': 'R'},
            {'label': _("Closing Credit"), 'width': 65, 'align': 'R'},
            {'label': _("Compared Closing Debit"), 'width': 65, 'align': 'R'},
            {'label': _("Compared Closing Credit"), 'width': 65, 'align': 'R'},
            {'label': _("Variance"), 'width': 68, 'align': 'R'},
            {'label': '%', 'width': 40, 'align': 'R'},
        ]

    def _get_carry_cols(self):
        return []

    def _should_add_signature_section(self):
        return False

    def _add_type_style_cmds(self, cmds, row_type, ri):
        if row_type == RT_OFF_BALANCE:
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_OFF_BALANCE)]
        else:
            super()._add_type_style_cmds(cmds, row_type, ri)

    def _groups_to_rows(self, groups):
        if not groups:
            return []
        report = groups[0]
        totals = report.get('totals', {})

        rows = []
        for line in report.get('lines', []):
            if line['is_parent']:
                row_type = RT_GROUP_HDR
            elif line['is_off_balance']:
                row_type = RT_OFF_BALANCE
            else:
                row_type = RT_DATA
            cells = [
                ' ' * (line['level'] * 3) + line['code'],
                line['name'],
                *(self.fmt_number(line[fname]) for fname in AMOUNT_FIELDS),
            ]
            if self.has_comparison:
                cells += [
                    self.fmt_number(line['prev_closing_debit']),
                    self.fmt_number(line['prev_closing_credit']),
                    self.fmt_number(line['variance']),
                    f"{line['variance_percent']:+.1f}%",
                ]
            rows.append({'type': row_type, 'cells': cells, 'height': None, 'monetary': {}})

        total_cells = [
            '', report.get('total_label', ''),
            *(self.fmt_number(totals.get(fname)) for fname in AMOUNT_FIELDS),
        ]
        if self.has_comparison:
            total_cells += [
                self.fmt_number(totals.get('prev_closing_debit')),
                self.fmt_number(totals.get('prev_closing_credit')),
                '', '',
            ]
        rows.append({'type': RT_GRAND_TOTAL, 'cells': total_cells, 'height': None, 'monetary': {}})
        return rows
