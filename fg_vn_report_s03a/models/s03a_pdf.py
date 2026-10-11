from reportlab.lib.units import mm

from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_DATA, RT_GRAND_TOTAL, FanhaReportPDF,
)

# Column widths. A4 landscape: 273 mm available (297 - 2 x 12);
# A4 portrait: 186 mm available (210 - 2 x 12).
COLUMN_WIDTHS = {
    'landscape': (20, 35, 110, 14, 14, 40, 40),
    'portrait': (18, 26, 72, 10, 10, 25, 25),
}
COLUMN_ALIGNS = ('C', 'L', 'L', 'C', 'C', 'R', 'R')
DEBIT_COLUMN, CREDIT_COLUMN = 5, 6
LABEL_COLUMN = 2  # Description: wide enough for the carried forward labels


class S03aPDF(FanhaReportPDF):
    """ PDF of the general journal, form S03a-DNN: both amounts are carried
    from page to page, and the book ends with its page count. """

    def _get_col_specs(self):
        _ = self.env._
        labels = (
            _("Date"), _("Voucher No."), _("Description"),
            _("Debit Account"), _("Credit Account"), _("Debit"), _("Credit"),
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

    def _should_add_journal_info_section(self):
        return True

    def _groups_to_rows(self, groups):
        if not groups:
            return []
        group = groups[0]
        rows = []
        for line in group['lines']:
            debit, credit = line['debit'], line['credit']
            rows.append({
                'type': RT_DATA,
                'cells': [
                    line['date_display'],
                    line['move_name'],
                    line['description'],
                    line['account_code'] if debit else '',
                    line['account_code'] if credit else '',
                    self.fmt_number(debit),
                    self.fmt_number(credit),
                ],
                'height': None,
                'monetary': {DEBIT_COLUMN: debit, CREDIT_COLUMN: credit},
            })

        cells = [''] * len(self._col_specs)
        cells[LABEL_COLUMN] = group['total_label']
        cells[DEBIT_COLUMN] = self.fmt_number(group['total']['debit'])
        cells[CREDIT_COLUMN] = self.fmt_number(group['total']['credit'])
        rows.append({'type': RT_GRAND_TOTAL, 'cells': cells, 'height': None, 'monetary': {}})
        return rows
