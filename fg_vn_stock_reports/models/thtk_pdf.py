from reportlab.lib.units import mm

from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_DATA, RT_GRAND_TOTAL, RT_GROUP_HDR, RT_GROUP_TOTAL, FanhaReportPDF,
)

# Column widths. A4 landscape: 273 mm available (297 - 2 x 12);
# A4 portrait: 186 mm available (210 - 2 x 12).
COLUMN_WIDTHS = {
    'landscape': (19, 70, 12, 18, 25, 18, 25, 18, 25, 18, 25),
    'portrait': (16, 48, 10, 12, 18, 12, 18, 12, 18, 12, 10),
}
COLUMN_ALIGNS = ('C', 'L', 'C', 'R', 'R', 'R', 'R', 'R', 'R', 'R', 'R')
COLUMN_TYPES = ('char', 'char', 'char') + ('float', 'monetary') * 4


class ThtkPDF(FanhaReportPDF):
    """ PDF of the stock summary: one row per product, optionally grouped by
    location. The column headers are repeated on every page; no amount is
    carried from page to page. """

    def _get_col_specs(self):
        _ = self.env._
        labels = (
            _("Code"), _("Product"), _("UoM"),
            _("Opening Qty"), _("Opening Value"), _("Qty In"), _("Value In"),
            _("Qty Out"), _("Value Out"), _("Closing Qty"), _("Closing Value"),
        )
        widths = COLUMN_WIDTHS['portrait' if self.orientation == 'portrait' else 'landscape']
        return [
            {'label': label, 'width': width * mm, 'align': align, 'type': col_type}
            for label, width, align, col_type in zip(labels, widths, COLUMN_ALIGNS, COLUMN_TYPES)
        ]

    def _get_carry_cols(self):
        return []

    def _groups_to_rows(self, groups):
        rows = []
        n = len(self._col_specs)

        if not groups:
            return rows

        data = groups[0]

        def _line_cells(line):
            return [
                line.get('product_id', '') or '',
                line.get('name', '') or '',
                line.get('uom', '') or '',
                self.fmt_number(line.get('opening_qty', 0) or 0, 2),
                self.fmt_number(line.get('opening_value', 0) or 0),
                self.fmt_number(line.get('in_qty', 0) or 0, 2),
                self.fmt_number(line.get('in_value', 0) or 0),
                self.fmt_number(line.get('out_qty', 0) or 0, 2),
                self.fmt_number(line.get('out_value', 0) or 0),
                self.fmt_number(line.get('closing_qty', 0) or 0, 2),
                self.fmt_number(line.get('closing_value', 0) or 0),
            ]

        def _total_cells(group):
            totals = group.get('totals', {})
            cells = [''] * n
            cells[1] = group['total_label']
            cells[3] = self.fmt_number(totals.get('opening_qty', 0) or 0, 2)
            cells[4] = self.fmt_number(totals.get('opening_value', 0) or 0)
            cells[5] = self.fmt_number(totals.get('in_qty', 0) or 0, 2)
            cells[6] = self.fmt_number(totals.get('in_value', 0) or 0)
            cells[7] = self.fmt_number(totals.get('out_qty', 0) or 0, 2)
            cells[8] = self.fmt_number(totals.get('out_value', 0) or 0)
            cells[9] = self.fmt_number(totals.get('closing_qty', 0) or 0, 2)
            cells[10] = self.fmt_number(totals.get('closing_value', 0) or 0)
            return cells

        def _row(row_type, cells, **extra):
            return {'type': row_type, 'cells': cells, 'height': None, 'monetary': {}, **extra}

        if data.get('group_by_location'):
            for loc in data.get('groups', []):
                cells = [''] * n
                cells[0] = loc.get('location_name', '')
                rows.append(_row(RT_GROUP_HDR, cells, span_all=True))
                rows.extend(_row(RT_DATA, _line_cells(line)) for line in loc.get('lines', []))
                rows.append(_row(RT_GROUP_TOTAL, _total_cells(loc)))
        else:
            rows.extend(_row(RT_DATA, _line_cells(line)) for line in data.get('lines', []))

        rows.append(_row(RT_GRAND_TOTAL, _total_cells(data)))
        return rows
