from reportlab.lib.units import mm

from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_CLOSING, RT_DATA, RT_OPENING, FanhaReportPDF,
)

# Column widths. A4 landscape: 273 mm available (297 - 2 x 12);
# A4 portrait: 186 mm available (210 - 2 x 12).
COLUMN_WIDTHS = {
    'landscape': (18, 28, 73, 25, 18, 25, 18, 25, 18, 25),
    'portrait': (14, 20, 50, 16, 12, 18, 12, 18, 12, 14),
}
COLUMN_ALIGNS = ('C', 'L', 'L', 'R', 'R', 'R', 'R', 'R', 'R', 'R')
COLUMN_TYPES = ('date', 'char', 'char', 'float', 'float', 'monetary', 'float', 'monetary', 'float', 'monetary')


class S06PDF(FanhaReportPDF):
    """ PDF of the detailed stock ledger, form S06-DNN. Each product starts
    on a new page, with its label in the header of its pages; the quantities
    and values in and out are carried from page to page, and so is the
    running balance. """

    def _get_col_specs(self):
        _ = self.env._
        labels = (
            _("Date"), _("Voucher"), _("Description"), _("Unit Price"),
            _("Qty In"), _("Value In"), _("Qty Out"), _("Value Out"),
            _("Qty Balance"), _("Value Balance"),
        )
        widths = COLUMN_WIDTHS['portrait' if self.orientation == 'portrait' else 'landscape']
        return [
            {'label': label, 'width': width * mm, 'align': align, 'type': col_type}
            for label, width, align, col_type in zip(labels, widths, COLUMN_ALIGNS, COLUMN_TYPES)
        ]

    def _get_carry_cols(self):
        return [4, 5, 6, 7]  # quantities and values in and out

    def _get_carry_last_cols(self):
        return [8, 9]  # running balance

    def _get_carry_label_col(self):
        return 2  # description

    def _get_page_header_lines(self, page):
        """ With selected locations, the locations before the period. """
        lines = super()._get_page_header_lines(page)
        scope = self.hdr.get('scope_label')
        if scope and len(lines) > 2:
            lines[2]['text'] = self.env._(
                "%(scope)s, from %(date_from)s to %(date_to)s", scope=scope,
                date_from=self.hdr.get('date_from', ''), date_to=self.hdr.get('date_to', ''))
        return lines

    def _group_to_rows(self, group):
        """ Rows of one product; its label is in the page header. """
        rows = []
        n = len(self._col_specs)

        opening = group.get('opening', {})
        oq = opening.get('quantity', 0) or 0.0
        ov = opening.get('value', 0) or 0.0
        op = opening.get('unit_price', 0) or 0.0
        cells = [''] * n
        cells[2] = group['opening_label']
        cells[3] = self.fmt_number(op, 2) if op else ''
        cells[8] = self.fmt_number(oq, 2)
        cells[9] = self.fmt_number(ov)
        rows.append({
            'type': RT_OPENING,
            'cells': cells,
            'height': None,
            'monetary': {},
            'last_vals': {8: oq, 9: ov},
        })

        for line in group.get('lines', []):
            qi = line.get('qty_in', 0) or 0.0
            vi = line.get('value_in', 0) or 0.0
            qo = line.get('qty_out', 0) or 0.0
            vo = line.get('value_out', 0) or 0.0
            bq = line.get('balance_qty', 0) or 0.0
            bv = line.get('balance_value', 0) or 0.0
            up = line.get('unit_price', 0) or 0.0
            date_s = str(line['date'])[:10] if line.get('date') else ''
            cells = [
                date_s,
                line.get('reference') or '',
                line.get('description') or '',
                self.fmt_number(up, 2) if up else '',
                self.fmt_number(qi, 2) if qi else '',
                self.fmt_number(vi) if vi else '',
                self.fmt_number(qo, 2) if qo else '',
                self.fmt_number(vo) if vo else '',
                self.fmt_number(bq, 2),
                self.fmt_number(bv),
            ]
            rows.append({
                'type': RT_DATA,
                'cells': cells,
                'height': None,
                'monetary': {4: qi, 5: vi, 6: qo, 7: vo},
                'last_vals': {8: bq, 9: bv},
            })

        # total of the period and closing balance on one row
        total = group.get('total', {})
        closing = group.get('closing', {})
        cq = closing.get('quantity', 0) or 0.0
        cv = closing.get('value', 0) or 0.0
        cp = closing.get('unit_price', 0) or 0.0
        cells = [''] * n
        cells[2] = group['closing_label']
        cells[3] = self.fmt_number(cp, 2) if cp else ''
        cells[4] = self.fmt_number(total.get('qty_in', 0) or 0.0, 2)
        cells[5] = self.fmt_number(total.get('value_in', 0) or 0.0)
        cells[6] = self.fmt_number(total.get('qty_out', 0) or 0.0, 2)
        cells[7] = self.fmt_number(total.get('value_out', 0) or 0.0)
        cells[8] = self.fmt_number(cq, 2)
        cells[9] = self.fmt_number(cv)
        rows.append({
            'type': RT_CLOSING,
            'cells': cells,
            'height': None,
            'monetary': {},
            'last_vals': {8: cq, 9: cv},
        })

        return rows

    def _groups_to_rows(self, groups):
        return [row for group in groups for row in self._group_to_rows(group)]

    def _should_paginate_by_group(self):
        return True

    def _format_group_label(self, group):
        return group['label']
