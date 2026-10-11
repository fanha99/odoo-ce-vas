import io
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import xlsxwriter

from odoo import _, api, fields, models

DEFAULT_TIMEZONE = 'Asia/Ho_Chi_Minh'
DEFAULT_REPORT_LANG = 'vi_VN'


class AbstractVNReport(models.AbstractModel):
    """ Base of the Vietnamese accounting reports. A report inherits this model
    and overrides the hooks it needs.
    """
    _name = 'vn.abstract.report'
    _inherit = 'vn.report.access.mixin'
    _description = 'Vietnam Abstract Report'

    # ==================== TIMEZONE HELPERS ====================

    def _get_user_timezone(self):
        """ Timezone of the user, Asia/Ho_Chi_Minh (GMT+7) when not set. """
        try:
            return ZoneInfo(self.env.user.tz or DEFAULT_TIMEZONE)
        except (ZoneInfoNotFoundError, ValueError):
            return ZoneInfo(DEFAULT_TIMEZONE)

    def _convert_date_to_utc_range(self, date_from_str, date_to_str):
        """ Convert a date range in the user's timezone into UTC datetimes, to
        query datetime fields.

        For 2024-01-01 to 2024-01-31 in GMT+7:
        - from: 2023-12-31 17:00:00 UTC (start of 01/01 in GMT+7)
        - to:   2024-01-31 16:59:59 UTC (end of 31/01 in GMT+7)

        :param str date_from_str: '2024-01-01'
        :param str date_to_str: '2024-01-31'
        :return: (datetime_from_utc, datetime_to_utc), both timezone-aware
        """
        user_tz = self._get_user_timezone()
        utc_tz = ZoneInfo('UTC')

        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')

        datetime_from_local = datetime.combine(date_from, time.min, tzinfo=user_tz)
        datetime_to_local = datetime.combine(date_to, time.max, tzinfo=user_tz)

        return datetime_from_local.astimezone(utc_tz), datetime_to_local.astimezone(utc_tz)

    def _get_utc_datetime_range(self, options):
        """ UTC datetime range of the report period, for queries on datetime
        fields (stock moves).

        :return: {'date_from': datetime, 'date_to': datetime}
        """
        datetime_from_utc, datetime_to_utc = self._convert_date_to_utc_range(
            options['date']['date_from'], options['date']['date_to'],
        )
        return {
            'date_from': datetime_from_utc,
            'date_to': datetime_to_utc,
        }

    # ==================== HOOKS TO OVERRIDE ====================

    def _get_report_name(self):
        """ Override: title of the report. """
        raise NotImplementedError("Subclass must implement _get_report_name()")

    def _get_report_code(self):
        """ Override: code of the legal form (e.g. S06-DNN). """
        raise NotImplementedError("Subclass must implement _get_report_code()")

    def _get_export_filename_code(self, options):
        """ Code used in the name of the exported files. Override when it
        depends on the options. """
        return self._get_report_code()

    def _get_columns(self):
        """ Override: list of the columns of the report. """
        raise NotImplementedError("Subclass must implement _get_columns()")

    @api.model
    def _get_lines(self, options):
        """ Override: figures of the report. """
        raise NotImplementedError("Subclass must implement _get_lines()")

    # ==================== OPTIONS ====================

    def _get_default_options(self, previous_options=None):
        """ Complete the options with their default values. """
        options = previous_options.copy() if previous_options else {}

        if 'date' not in options:
            today = fields.Date.context_today(self)
            options['date'] = {
                'date_from': today.replace(day=1).strftime('%Y-%m-%d'),
                'date_to': today.strftime('%Y-%m-%d'),
                'mode': 'range',
            }

        if 'company_id' not in options:
            options['company_id'] = self.env.company.id

        if 'show_zero_balance' not in options:
            options['show_zero_balance'] = False

        return self._get_custom_options(options)

    def _get_custom_options(self, options):
        """ Hook: add the options of the report. """
        return options

    # ==================== REPORT LANGUAGE ====================

    def _get_report_languages(self):
        """ Languages a report can be displayed and printed in.

        :return: list of (code, name) of the installed languages
        """
        return self.env['res.lang'].get_installed()

    def _get_report_lang(self, options):
        """ Language of the report: `options['lang']` when it is an installed
        language, else Vietnamese when installed, else the user's language.
        The accounting books are Vietnamese legal forms, hence the default.
        """
        installed = {code for code, _name in self._get_report_languages()}
        lang = (options or {}).get('lang')
        if lang in installed:
            return lang
        if DEFAULT_REPORT_LANG in installed:
            return DEFAULT_REPORT_LANG
        return self.env.lang or self.env.user.lang

    def _with_report_lang(self, options):
        """ Return `self` in the language of the report, so that everything
        computed from it (labels, account names, exports) is in that language.
        """
        return self.with_context(lang=self._get_report_lang(options))

    # ==================== REPORT DATA ====================

    @api.model
    def get_report_data(self, options=None):
        """ Main API: return the header, the columns and the lines of the
        report, in the language of the report.
        """
        options = self._get_default_options(options or {})
        self._check_report_access(options)
        self = self._with_report_lang(options)
        options['lang'] = self.env.lang
        return self._build_report_data(options)

    def _build_report_data(self, options):
        """ Build the result of `get_report_data()`. `self` is in the language
        of the report and the access is checked: this is the method to extend
        to add or change data.
        """
        company = self.env['res.company'].browse(options['company_id'])

        return {
            'options': options,
            'languages': [
                {'code': code, 'name': name}
                for code, name in self._get_report_languages()
            ],
            'company': {
                'id': company.id,
                'name': company.name,
                'vat': company.vat or '',
                'address': company.street or '',
                'currency_id': company.currency_id.id,
            },
            'header': {
                'title': self._get_report_name(),
                'template_code': self._get_report_code(),
                'date_from': options['date']['date_from'],
                'date_to': options['date']['date_to'],
            },
            'lines': self._get_lines(options),
            'columns': self._get_columns(),
        }

    # ==================== DRILL DOWN ====================

    @api.model
    def action_drill_down(self, options, params):
        """ Return the action opening the details of a line. """
        self._check_report_access(options)
        action = self._with_report_lang(options)._get_drill_down_action(options, params)

        # complete the action so that the web client can run it
        if action and isinstance(action, dict):
            if 'views' not in action and 'view_mode' in action:
                action['views'] = [
                    (False, mode.strip())
                    for mode in action['view_mode'].split(',')
                ]
            if 'target' not in action:
                action['target'] = 'current'

        return action

    def _get_drill_down_action(self, options, params):
        """ Hook: drill-down action of the report. """
        return False

    # ==================== EXPORT XLSX ====================
    #
    # Row-typed framework (mirrors the PDF renderer):
    # - The report provides typed rows through _groups_to_xlsx_rows() (single
    #   sheet) or _group_to_xlsx_rows() (one sheet per group).
    # - Each row: {'type': RT_*, 'cells': [raw values], 'span_all': bool, ...}
    # - The base writes everything: workbook, formats, header, column headers,
    #   rows, widths.
    # - Colors match the PDF: header #4472C4, group #D9E1F2, highlight #E2EFDA.

    # Row style mapping (matches the row types of pdf_renderer.py)
    _XLSX_ROW_STYLES = {
        'data':         'data',
        'group_hdr':    'group',
        'group_total':  'highlight',
        'grand_total':  'highlight',
        'opening':      'highlight',
        'closing':      'highlight',
        'carry_fwd':    'highlight',
        'brought_fwd':  'highlight',
        'off_balance':  'off_balance',
    }

    def _should_xlsx_split_by_group(self):
        """ Override -> True to write each group on its own sheet. """
        return False

    def _format_xlsx_sheet_name(self, group):
        """ Sheet name of a group. Excel: 31 characters at most, none of
        / \\ * ? [ ] : """
        name = group.get('name') or group.get('code') or 'Sheet'
        name = str(name)[:31]
        for ch in '/\\*?[]:':
            name = name.replace(ch, '-')
        return name

    def _groups_to_xlsx_rows(self, groups):
        """ Single sheet: flat list of row dicts. Override when
        _should_xlsx_split_by_group() is False. """
        rows = []
        for group in groups:
            rows.extend(self._group_to_xlsx_rows(group))
        return rows

    def _group_to_xlsx_rows(self, group):
        """ One sheet per group: rows of one group. Override when
        _should_xlsx_split_by_group() is True. """
        return []

    @api.model
    def get_xlsx(self, options):
        """ Return the report as the content of an .xlsx file. """
        options = self._get_default_options(options or {})
        # access is checked by get_report_data()
        self = self._with_report_lang(options)
        data = self.get_report_data(options)
        columns = data['columns']
        groups = data.get('lines', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        formats = self._get_xlsx_formats(workbook)

        if self._should_xlsx_split_by_group() and groups:
            sheet_names = set()
            for group in groups:
                sheet_name = self._unique_sheet_name(self._format_xlsx_sheet_name(group), sheet_names)
                sheet = workbook.add_worksheet(sheet_name)
                self._write_xlsx_sheet(sheet, data, columns, formats, self._group_to_xlsx_rows(group), group)
        else:
            sheet = workbook.add_worksheet('Sheet1')
            self._write_xlsx_sheet(sheet, data, columns, formats, self._groups_to_xlsx_rows(groups), None)

        workbook.close()
        output.seek(0)
        return output.read()

    @staticmethod
    def _unique_sheet_name(name, used):
        original, counter = name, 1
        # Excel compares sheet names case-insensitively
        while name.lower() in used:
            name = f"{original[:28]}_{counter}"
            counter += 1
        used.add(name.lower())
        return name

    def _write_xlsx_sheet(self, sheet, data, columns, formats, rows, group):
        row_idx = self._write_xlsx_header(sheet, data, formats, group)
        row_idx = self._write_xlsx_column_headers(sheet, columns, formats, row_idx)
        row_idx = self._write_xlsx_rows(sheet, rows, columns, formats, row_idx)
        self._set_xlsx_column_widths(sheet, columns)

    def _get_xlsx_formats(self, workbook):
        """ Minimal set of formats; colors match the PDF. """
        base_text = {'border': 1, 'font_size': 10, 'valign': 'vcenter'}
        bold      = {'bold': True}
        right     = {'align': 'right'}
        num_int   = {'num_format': '#,##0'}
        num_dec   = {'num_format': '#,##0.00'}

        def make(*dicts):
            f = {}
            for d in dicts:
                f.update(d)
            return workbook.add_format(f)

        return {
            'title':  make({'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter', 'center_across': True}),
            'header': make(base_text, bold,
                           {'bg_color': '#4472C4', 'font_color': 'white',
                            'align': 'center', 'text_wrap': True}),

            # Normal data row
            'data':      make(base_text),
            'data_int':  make(base_text, right, num_int),
            'data_dec':  make(base_text, right, num_dec),

            # Group header (#D9E1F2), bold
            'group':     make(base_text, bold, {'bg_color': '#D9E1F2'}),
            'group_int': make(base_text, bold, right, num_int, {'bg_color': '#D9E1F2'}),
            'group_dec': make(base_text, bold, right, num_dec, {'bg_color': '#D9E1F2'}),

            # Highlight: opening/closing/total/carry (#E2EFDA), bold
            'highlight':     make(base_text, bold, {'bg_color': '#E2EFDA'}),
            'highlight_int': make(base_text, bold, right, num_int, {'bg_color': '#E2EFDA'}),
            'highlight_dec': make(base_text, bold, right, num_dec, {'bg_color': '#E2EFDA'}),

            # Off-balance accounts (#FCE4D6), not bold, to tell them from groups and totals
            'off_balance':     make(base_text, {'bg_color': '#FCE4D6'}),
            'off_balance_int': make(base_text, right, num_int, {'bg_color': '#FCE4D6'}),
            'off_balance_dec': make(base_text, right, num_dec, {'bg_color': '#FCE4D6'}),
        }

    def _pick_xlsx_format(self, row_type, col_type, formats):
        style = self._XLSX_ROW_STYLES.get(row_type, 'data')
        if col_type in ('monetary', 'number', 'integer'):
            return formats[f'{style}_int']
        if col_type == 'float':
            return formats[f'{style}_dec']
        return formats[style]

    def _write_xlsx_header(self, sheet, data, formats, group=None):
        """ Title and period. Override to add lines above the column headers. """
        num_cols = max(len(data['columns']), 1)
        last     = num_cols - 1
        hdr      = data['header']

        sheet.write(0, 0, hdr.get('title', ''), formats['title'])
        for col in range(1, num_cols):
            sheet.write(0, col, '', formats['title'])

        period = _(
            "From %(date_from)s to %(date_to)s",
            date_from=hdr.get('date_from', ''), date_to=hdr.get('date_to', ''),
        )
        sheet.write(1, 0, period, formats['title'])
        for col in range(1, num_cols):
            sheet.write(1, col, '', formats['title'])

        next_row = 2
        if group is not None:
            label = self._format_xlsx_group_label(group)
            if label:
                sheet.merge_range(next_row, 0, next_row, last, label, formats['group'])
                next_row += 1
        return next_row + 1  # blank line before the column headers

    def _format_xlsx_group_label(self, group):
        """ Override to show a label of the group at the top of its sheet
        ('Account: ...', 'Product: ...'). Return '' to skip it. """
        return ''

    def _write_xlsx_column_headers(self, sheet, columns, formats, row):
        for col, column in enumerate(columns):
            sheet.write(row, col, column.get('label', ''), formats['header'])
        return row + 1

    def _write_xlsx_rows(self, sheet, rows, columns, formats, row_idx):
        n_cols = len(columns)
        for row in rows:
            cells = row.get('cells') or []
            rt    = row.get('type', 'data')

            if row.get('span_all'):
                style = self._XLSX_ROW_STYLES.get(rt, 'data')
                label = next((c for c in cells if c not in (None, '')), '')
                sheet.merge_range(row_idx, 0, row_idx, n_cols - 1, label, formats[style])
            else:
                for col_idx in range(n_cols):
                    cell = cells[col_idx] if col_idx < len(cells) else ''
                    col_type = columns[col_idx].get('type', 'char')
                    fmt = self._pick_xlsx_format(rt, col_type, formats)
                    if col_type in ('monetary', 'float'):
                        sheet.write(row_idx, col_idx,
                                    cell if cell not in (None, '', 0) else '',
                                    fmt)
                    else:
                        sheet.write(row_idx, col_idx, cell if cell is not None else '', fmt)
            row_idx += 1
        return row_idx

    def _set_xlsx_column_widths(self, sheet, columns):
        for col, column in enumerate(columns):
            sheet.set_column(col, col, column.get('width', 100) / 7)

    # ==================== EXPORT PDF ====================

    @api.model
    def get_pdf_rl(self, options):
        """ Return the report as a PDF built with ReportLab (running totals
        carried from page to page). """
        options = self._get_default_options(options or {})
        # access is checked by get_report_data()
        self = self._with_report_lang(options)
        data = self.get_report_data(options)
        renderer_cls = self._get_pdf_rl_renderer()
        if not renderer_cls:
            raise NotImplementedError("Subclass must implement _get_pdf_rl_renderer()")
        return renderer_cls(data, self.env).render()

    def _get_pdf_rl_renderer(self):
        """ Override: renderer class (subclass of FanhaReportPDF). """
        return None

    # ==================== UTILITY METHODS ====================

    def _format_date(self, date_value):
        """ Format a date for display. """
        if not date_value:
            return ''
        if isinstance(date_value, str):
            return date_value[:10]
        return date_value.strftime('%Y/%m/%d')

    def _format_number(self, value, precision=2):
        """ Round a number for display. """
        if value is None or value == '':
            return ''
        return round(float(value), precision)
