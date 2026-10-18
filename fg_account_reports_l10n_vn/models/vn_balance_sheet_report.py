from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class VNBalanceSheetReportHandler(models.AbstractModel):
    """Custom handler for Vietnamese Balance Sheet Report.
    
    This handler modifies the report to:
    - Parse line names with format: "name|code|note"
    - Display name, code (Mã số), and note (Thuyết minh) in separate columns
    - These columns only appear ONCE regardless of comparison periods
    """
    _name = 'vn.balance.sheet.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Vietnamese Balance Sheet Report Handler'

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        """Post-process lines to parse name|code|note format.
        
        For each line:
        - Parse the line name with format "name|code|note"
        - Split into separate fields
        - Add code and note as new column values at the beginning of line['columns']
        """

        for line in lines:
            original_name = line.get('name', '')
            
            # Parse format: name|code|note
            parts = str(original_name).split('|')
            
            # Extract parts (with defaults for missing parts)
            clean_name = parts[0].strip() if len(parts) > 0 else ''
            code_value = parts[1].strip() if len(parts) > 1 else ''
            note_value = parts[2].strip() if len(parts) > 2 else ''
            
            # Update line name (just the name part)
            line['name'] = clean_name
            
            # Create the code column cell - this needs to match custom_columns_subheaders
            code_cell = {
                'name': code_value,
                'no_format': code_value,
                'figure_type': 'string',
                'is_zero': not code_value,
                'blank_if_zero': False,
            }
            
            # Create the note column cell
            note_cell = {
                'name': note_value,
                'no_format': note_value,
                'figure_type': 'string',
                'is_zero': not note_value,
                'blank_if_zero': False,
            }
            
            # Insert cells at the beginning of columns (code first, then note)
            if 'columns' in line:
                line['columns'] = [code_cell, note_cell] + line['columns']
        
        return lines

    def _get_custom_display_config(self):
        """Override to add custom CSS class and custom PDF export template"""
        return {
            'css_custom_class': 'vn_balance_sheet_report',
            'pdf_export': {
                'pdf_export_main_table_header': 'fg_account_reports_l10n_vn.vn_pdf_export_main_table_header',
            },
        }