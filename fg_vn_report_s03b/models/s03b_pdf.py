from reportlab.lib.units import mm

from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_CLOSING, RT_DATA, RT_OPENING, FanhaReportPDF,
)

# Column widths. A4 landscape: 273 mm available (297 - 2 x 12);
# A4 portrait: 186 mm available (210 - 2 x 12).
COLUMN_WIDTHS = {
    'landscape': (18, 30, 135, 20, 35, 35),
    'portrait': (18, 26, 74, 16, 26, 26),
}
COLUMN_ALIGNS = ('C', 'L', 'L', 'C', 'R', 'R')
LABEL_COLUMN = 2
DEBIT_COLUMN, CREDIT_COLUMN = 4, 5


class S03bPDF(FanhaReportPDF):
    """ PDF of the general ledger, form S03b-DNN. Each account starts on a
    new page, with its name in the header of its pages; the amounts are
    carried from page to page within the account. """

    def _get_col_specs(self):
        _ = self.env._
        labels = (
            _("Date"), _("Voucher No."), _("Description"),
            _("Counterpart Account"), _("Debit"), _("Credit"),
        )
        widths = COLUMN_WIDTHS['portrait' if self.orientation == 'portrait' else 'landscape']
        return [
            {'label': label, 'width': width * mm, 'align': align}
            for label, width, align in zip(labels, widths, COLUMN_ALIGNS)
        ]

    def _get_carry_cols(self):
        return [DEBIT_COLUMN, CREDIT_COLUMN]

    def _get_carry_label_col(self):
        return LABEL_COLUMN

    def _should_paginate_by_group(self):
        return True

    def _should_add_journal_info_section(self):
        return True

    def _format_group_label(self, group):
        return group['label']

    def _summary_row(self, row_type, label, amounts, **extra):
        cells = [''] * len(self._col_specs)
        cells[LABEL_COLUMN] = label
        cells[DEBIT_COLUMN] = self.fmt_number(amounts['debit'])
        cells[CREDIT_COLUMN] = self.fmt_number(amounts['credit'])
        return {'type': row_type, 'cells': cells, 'height': None, 'monetary': {}, **extra}

    def _group_to_rows(self, group):
        rows = [self._summary_row(RT_OPENING, group['opening_label'], group['opening'])]
        for line in group['lines']:
            rows.append({
                'type': RT_DATA,
                'cells': [
                    line['date_display'],
                    line['move_name'],
                    line['description'],
                    line['counterpart_account'],
                    self.fmt_number(line['debit']),
                    self.fmt_number(line['credit']),
                ],
                'height': None,
                'monetary': {DEBIT_COLUMN: line['debit'], CREDIT_COLUMN: line['credit']},
            })
        # the total of the period stays on the page of the closing balance
        rows.append(self._summary_row(
            RT_CLOSING, group['total_label'], group['total'], keep_with_next=True))
        rows.append(self._summary_row(RT_CLOSING, group['closing_label'], group['closing']))
        return rows

    def _groups_to_rows(self, groups):
        return [row for group in groups for row in self._group_to_rows(group)]
