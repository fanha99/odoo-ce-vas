# -*- coding: utf-8 -*-
# Copyright 2024 Fanha Giang
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class StockValuationReportXlsx(models.AbstractModel):
    """XLSX Export for Stock Valuation Report."""

    _name = "report.fg_stock_reports_l10n_vn_ce.report_stock_valuation_xlsx"
    _description = "Stock Valuation Report XLSX"
    _inherit = "report.report_xlsx.abstract"

    def _get_report_name(self, report, data=False):
        """Get report name for the Excel file."""
        return _("Báo cáo Xuất Nhập Tồn")

    def _get_report_columns(self, report):
        """Define columns for the report."""
        return {
            0: {"header": _("STT"), "field": "sequence", "width": 5},
            1: {"header": _("Mã sản phẩm"), "field": "default_code", "width": 15},
            2: {"header": _("Tên sản phẩm"), "field": "product_name", "width": 40},
            3: {"header": _("ĐVT"), "field": "uom_name", "width": 10},
            4: {"header": _("SL Đầu kỳ"), "field": "opening_qty", "width": 12, "type": "number"},
            5: {"header": _("GT Đầu kỳ"), "field": "opening_value", "width": 15, "type": "amount"},
            6: {"header": _("SL Nhập"), "field": "increase_qty", "width": 12, "type": "number"},
            7: {"header": _("GT Nhập"), "field": "increase_value", "width": 15, "type": "amount"},
            8: {"header": _("SL Xuất"), "field": "decrease_qty", "width": 12, "type": "number"},
            9: {"header": _("GT Xuất"), "field": "decrease_value", "width": 15, "type": "amount"},
            10: {"header": _("SL Cuối kỳ"), "field": "closing_qty", "width": 12, "type": "number"},
            11: {"header": _("GT Cuối kỳ"), "field": "closing_value", "width": 15, "type": "amount"},
        }

    def _get_report_filters(self, report):
        """Get report filters for display."""
        return [
            [_("Từ ngày"), str(report.date_from)],
            [_("Đến ngày"), str(report.date_to)],
            [_("Công ty"), report.company_id.name],
        ]

    def _define_formats(self, workbook):
        """Define all formats used in the report."""
        formats = {}
        
        # Title format
        formats['title'] = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        # Header format
        formats['header'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'text_wrap': True,
        })
        
        # Filter format
        formats['filter_title'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
        })
        formats['filter_value'] = workbook.add_format({
            'font_size': 10,
        })
        
        # Data formats
        formats['text'] = workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
        })
        formats['text_center'] = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })
        formats['number'] = workbook.add_format({
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00',
        })
        formats['amount'] = workbook.add_format({
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0',
        })
        
        # Category format
        formats['category'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#E2EFDA',
            'border': 1,
        })
        formats['category_number'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'bg_color': '#E2EFDA',
            'border': 1,
            'num_format': '#,##0.00',
        })
        formats['category_amount'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'bg_color': '#E2EFDA',
            'border': 1,
            'num_format': '#,##0',
        })
        
        # Total format
        formats['total'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#FFF2CC',
            'border': 1,
        })
        formats['total_number'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'bg_color': '#FFF2CC',
            'border': 1,
            'num_format': '#,##0.00',
        })
        formats['total_amount'] = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'bg_color': '#FFF2CC',
            'border': 1,
            'num_format': '#,##0',
        })
        
        return formats

    def generate_xlsx_report(self, workbook, data, objects):
        """Generate the XLSX report."""
        report_model = self.env['report.fg_stock_reports_l10n_vn_ce.report_stock_valuation']
        report_data = report_model._get_report_values(None, data)
        
        wizard = objects
        report_lines = report_data.get('report_lines', [])
        totals = report_data.get('totals', {})
        
        # Create worksheet
        sheet = workbook.add_worksheet(_("Xuất Nhập Tồn"))
        
        # Define formats
        formats = self._define_formats(workbook)
        
        # Set column widths
        columns = self._get_report_columns(None)
        for col_pos, col_info in columns.items():
            sheet.set_column(col_pos, col_pos, col_info.get('width', 10))
        
        row_pos = 0
        
        # Title
        sheet.merge_range(
            row_pos, 0, row_pos, 11,
            _("BÁO CÁO XUẤT NHẬP TỒN"),
            formats['title']
        )
        row_pos += 2
        
        # Filters
        filters = self._get_report_filters(wizard)
        for filter_name, filter_value in filters:
            sheet.write(row_pos, 0, filter_name + ":", formats['filter_title'])
            sheet.write(row_pos, 1, filter_value, formats['filter_value'])
            row_pos += 1
        row_pos += 1
        
        # Headers
        for col_pos, col_info in columns.items():
            sheet.write(row_pos, col_pos, col_info['header'], formats['header'])
        row_pos += 1
        
        # Data lines
        sequence = 0
        for line in report_lines:
            line_type = line.get('type', 'product')
            
            if line_type == 'category':
                # Category row
                sheet.write(row_pos, 0, '', formats['category'])
                sheet.merge_range(
                    row_pos, 1, row_pos, 3,
                    line.get('name', ''),
                    formats['category']
                )
                sheet.write(row_pos, 4, line.get('opening_qty', 0), formats['category_number'])
                sheet.write(row_pos, 5, line.get('opening_value', 0), formats['category_amount'])
                sheet.write(row_pos, 6, line.get('increase_qty', 0), formats['category_number'])
                sheet.write(row_pos, 7, line.get('increase_value', 0), formats['category_amount'])
                sheet.write(row_pos, 8, line.get('decrease_qty', 0), formats['category_number'])
                sheet.write(row_pos, 9, line.get('decrease_value', 0), formats['category_amount'])
                sheet.write(row_pos, 10, line.get('closing_qty', 0), formats['category_number'])
                sheet.write(row_pos, 11, line.get('closing_value', 0), formats['category_amount'])
            else:
                # Product row
                sequence += 1
                sheet.write(row_pos, 0, sequence, formats['text_center'])
                sheet.write(row_pos, 1, line.get('default_code', ''), formats['text'])
                sheet.write(row_pos, 2, line.get('product_name', ''), formats['text'])
                sheet.write(row_pos, 3, line.get('uom_name', ''), formats['text_center'])
                sheet.write(row_pos, 4, line.get('opening_qty', 0), formats['number'])
                sheet.write(row_pos, 5, line.get('opening_value', 0), formats['amount'])
                sheet.write(row_pos, 6, line.get('increase_qty', 0), formats['number'])
                sheet.write(row_pos, 7, line.get('increase_value', 0), formats['amount'])
                sheet.write(row_pos, 8, line.get('decrease_qty', 0), formats['number'])
                sheet.write(row_pos, 9, line.get('decrease_value', 0), formats['amount'])
                sheet.write(row_pos, 10, line.get('closing_qty', 0), formats['number'])
                sheet.write(row_pos, 11, line.get('closing_value', 0), formats['amount'])
            
            row_pos += 1
        
        # Total row
        sheet.write(row_pos, 0, '', formats['total'])
        sheet.merge_range(row_pos, 1, row_pos, 3, _("TỔNG CỘNG"), formats['total'])
        sheet.write(row_pos, 4, totals.get('opening_qty', 0), formats['total_number'])
        sheet.write(row_pos, 5, totals.get('opening_value', 0), formats['total_amount'])
        sheet.write(row_pos, 6, totals.get('increase_qty', 0), formats['total_number'])
        sheet.write(row_pos, 7, totals.get('increase_value', 0), formats['total_amount'])
        sheet.write(row_pos, 8, totals.get('decrease_qty', 0), formats['total_number'])
        sheet.write(row_pos, 9, totals.get('decrease_value', 0), formats['total_amount'])
        sheet.write(row_pos, 10, totals.get('closing_qty', 0), formats['total_number'])
        sheet.write(row_pos, 11, totals.get('closing_value', 0), formats['total_amount'])
