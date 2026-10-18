from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

_logger = logging.getLogger(__name__)


def _split_code_name_helper(display_name):
    """
    Helper method để tách code và name từ display_name
    Tương tự như account.account._split_code_name
    """
    if not display_name:
        return ('', '')

    # Tách theo dấu cách đầu tiên
    parts = display_name.split(' ', 1)
    if len(parts) == 2:
        code = parts[0]
        name = parts[1]
        # Xử lý trường hợp có dấu "-" sau code
        if name.startswith('- '):
            name = name[2:]  # Bỏ "- " ở đầu
        elif name.startswith('-'):
            name = name[1:].strip()  # Bỏ "-" và khoảng trắng
        return (code, name)
    else:
        # Không có code, toàn bộ là name
        return ('', display_name)

class AccountReport(models.Model):
    _inherit = 'account.report'

    def _init_options_buttons(self, options, previous_options=None):
        """Override để thêm button export XML cho Trial Balance"""
        super()._init_options_buttons(options, previous_options)
        
        # Chỉ thêm button cho Trial Balance report
        if self.env.ref('fg_account_reports_l10n_vn.vn_trial_balance_report', raise_if_not_found=False) and \
           self.id == self.env.ref('fg_account_reports_l10n_vn.vn_trial_balance_report').id:
            options['buttons'].append({
                'name': _('Export XML (CDTK)'),
                'sequence': 25,
                'action': 'export_file',
                'action_param': 'export_to_xml_cdtk',
                'file_export_type': _('XML'),
                'branch_allowed': True, 'always_show': True
            })

        # thêm button cho vn_b01b_dnn_tt133 report
        if self.env.ref('fg_account_reports_l10n_vn.vn_b01b_dnn_tt133', raise_if_not_found=False) and \
           self.id == self.env.ref('fg_account_reports_l10n_vn.vn_b01b_dnn_tt133').id:
            options['buttons'].append({
                'name': _('Export XML (B01b-DNN-TT133)'),
                'sequence': 25,
                'action': 'export_file',
                'action_param': 'export_to_xml_b01b_dnn_tt133',
                'file_export_type': _('XML'),
                'branch_allowed': True, 'always_show': True
            })

        # thêm button cho vn_b01b_dnn_tt133 report
        if self.env.ref('fg_account_reports_l10n_vn.vn_b02_dnn_tt133', raise_if_not_found=False) and \
           self.id == self.env.ref('fg_account_reports_l10n_vn.vn_b02_dnn_tt133').id:
            options['buttons'].append({
                'name': _('Export XML (B02-DNN-TT133)'),
                'sequence': 25,
                'action': 'export_file',
                'action_param': 'export_to_xml_b02_dnn_tt133',
                'file_export_type': _('XML'),
                'branch_allowed': True, 'always_show': True
            })

    def export_to_xml_b02_dnn_tt133(self, options):
        self.ensure_one()

        # Get all lines from Trial Balance
        print_mode_self = self.with_context(no_format=True)
        lines = print_mode_self._get_lines(options)

        # Generate XML
        xml_content = self._generate_xml(lines, 'PL_KQHDSXKD', 'ThuyetMinh', 'NamNay', 'NamTruoc')

        # Return file
        return {
            'file_name': self.get_default_report_filename(options, 'xml'),
            'file_content': xml_content.encode('utf-8'),
            'file_type': 'xml',
        }

    def export_to_xml_b01b_dnn_tt133(self, options):
        self.ensure_one()

        # Get all lines from Trial Balance
        print_mode_self = self.with_context(no_format=True)
        lines = print_mode_self._get_lines(options)

        # Generate XML
        xml_content = self._generate_xml(lines, 'CTieuTKhaiChinh', 'ThuyetMinh', 'SoCuoiNam', 'SoDauNam')

        # Return file
        return {
            'file_name': self.get_default_report_filename(options, 'xml'),
            'file_content': xml_content.encode('utf-8'),
            'file_type': 'xml',
        }

    def _generate_xml(self, lines, ten_root, thuyetminh, socuoinam, sodaunam):
        # Create root element
        root = ET.Element(ten_root)

        thuyetminh_root = ET.SubElement(root, thuyetminh)
        socuoinam_root = ET.SubElement(root, socuoinam)
        sodaunam_root = ET.SubElement(root, sodaunam)

        for line in lines:
            #get the no_format of the first column as the value for the account
            columns = line.get('columns', [])
            if not columns:
                continue

            code = columns[0].get('no_format', '')
            if code == '':
                continue
            note = columns[1].get('no_format', ' ')
            cuoinam = columns[2].get('no_format', 0.0)
            daunam = columns[3].get('no_format', 0.0)

            xml_tag = 'ct' + code.replace('.', '').replace('-', '').replace(' ', '')

            # Thuyetminh
            elem = ET.SubElement(thuyetminh_root, xml_tag)
            elem.text = note

            # cuoinam
            elem = ET.SubElement(socuoinam_root, xml_tag)
            elem.text = str(int(round(cuoinam)))

            # daunam
            elem = ET.SubElement(sodaunam_root, xml_tag)
            elem.text = str(int(round(daunam)))

        # Convert to string with pretty printing
        xml_string = ET.tostring(root, encoding='unicode')

        # Pretty print
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')

        # Remove extra blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)

        return pretty_xml

    def export_to_xml_cdtk(self, options):
        """
        Export Trial Balance to XML format for Cân đối tài khoản (CDTK)
        
        Structure:
        - SoDuDauKy (Initial Balance): No/Co
        - SoPhatSinhTrongKy (Period Movements): No/Co
        - SoDuCuoiKy (End Balance): No/Co
        
        Rules:
        - Only accounts with code >= 3 digits
        - Exclude archived accounts
        - Include all matching accounts even with zero balance
        """
        self.ensure_one()
        
        # Get all lines from Trial Balance
        print_mode_self = self.with_context(no_format=True)
        lines = print_mode_self._get_lines(options)
        
        # Filter and collect account data
        accounts_data = self._collect_accounts_data_for_xml(lines, options)
        
        if not accounts_data:
            raise UserError(_('No accounts found with code >= 3 digits. Please check your chart of accounts.'))
        
        # Generate XML
        xml_content = self._generate_xml_cdtk(accounts_data)
        
        # Return file
        return {
            'file_name': self.get_default_report_filename(options, 'xml'),
            'file_content': xml_content.encode('utf-8'),
            'file_type': 'xml',
        }

    def _collect_accounts_data_for_xml(self, lines, options):
        """
        Collect account data from Trial Balance lines
        
        Returns dict: {
            'account_code': {
                'initial_debit': float,
                'initial_credit': float,
                'period_debit': float,
                'period_credit': float,
                'end_debit': float,
                'end_credit': float,
            }
        }
        """
        accounts_data = {}
        
        # Find column indices for Initial Balance, Period, and End Balance
        init_debit_idx = None
        init_credit_idx = None
        period_debit_idx = None
        period_credit_idx = None
        end_debit_idx = None
        end_credit_idx = None
        
        # Parse column headers to find indices
        for idx, col in enumerate(options.get('columns', [])):
            expr_label = col.get('expression_label', '')
            col_name = col.get('name', '')
            
            # Initial Balance columns (first debit/credit)
            if init_debit_idx is None and expr_label == 'debit':
                init_debit_idx = idx
            elif init_credit_idx is None and expr_label == 'credit':
                init_credit_idx = idx
            # Period columns (middle debit/credit)
            elif period_debit_idx is None and expr_label == 'debit' and init_debit_idx is not None:
                period_debit_idx = idx
            elif period_credit_idx is None and expr_label == 'credit' and init_credit_idx is not None:
                period_credit_idx = idx
            # End Balance columns (last debit/credit)
            elif end_debit_idx is None and expr_label == 'debit' and period_debit_idx is not None:
                end_debit_idx = idx
            elif end_credit_idx is None and expr_label == 'credit' and period_credit_idx is not None:
                end_credit_idx = idx
        
        # Alternative: use reverse search for end balance
        if end_debit_idx is None or end_credit_idx is None:
            for idx in range(len(options.get('columns', [])) - 1, -1, -1):
                col = options['columns'][idx]
                expr_label = col.get('expression_label', '')
                if end_credit_idx is None and expr_label == 'credit':
                    end_credit_idx = idx
                elif end_debit_idx is None and expr_label == 'debit':
                    end_debit_idx = idx
                if end_debit_idx is not None and end_credit_idx is not None:
                    break
        
        # Process each line
        for line in lines:
            line_model, line_res_id = self._get_model_info_from_id(line['id'])

            if line_model == 'account.account':
                account = self.env['account.account'].browse(line_res_id)

                # Skip archived accounts
                if not account or account.deprecated:
                    continue

                # Skip accounts with code < 3 digits
                if not account.code or len(account.code.strip()) < 3:
                    continue

                # Clean account code (remove spaces, special chars)
                account_code = account.code.strip()

            if line_model == 'account.group':
                code_name = _split_code_name_helper(line['name'])
                account_code = code_name[0].strip() if code_name else ''
                if len(account_code) < 3:
                    continue

            if line['name'] == 'Total':
                account_code = 'tongCong'

            # Get column values
            columns = line.get('columns', [])
            
            def get_value(idx):
                """Safely get column value"""
                if idx is not None and idx < len(columns):
                    return columns[idx].get('no_format', 0.0) or 0.0
                return 0.0
            
            accounts_data[account_code] = {
                'initial_debit': get_value(init_debit_idx),
                'initial_credit': get_value(init_credit_idx),
                'period_debit': get_value(period_debit_idx),
                'period_credit': get_value(period_credit_idx),
                'end_debit': get_value(end_debit_idx),
                'end_credit': get_value(end_credit_idx),
            }

        # lấy tất cả các account có trong report, kể cả những account có số dư bằng 0, để đảm bảo báo cáo CDTK đầy đủ theo yêu cầu của cơ quan thuế
        accounts = self.env['account.account'].search([('code', '!=', False), ('deprecated', '=', False)])
        for account in accounts:
            if len(account.code.strip()) < 3:
                continue

            account_code = account.code.strip()
            if account_code not in accounts_data:
                accounts_data[account_code] = {
                    'initial_debit': 0.0,
                    'initial_credit': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0,
                    'end_debit': 0.0,
                    'end_credit': 0.0,
                }

        # lấy tất cả các account group trong report, kể cả những account có số dư bằng 0, để đảm bảo báo cáo CDTK đầy đủ theo yêu cầu của cơ quan thuế
        account_groups = self.env['account.group'].search([('code_prefix_start', '!=', False)])
        for group in account_groups:
            if len(group.code_prefix_start.strip()) < 3:
                continue

            account_code = group.code_prefix_start.strip()
            if account_code not in accounts_data:
                accounts_data[account_code] = {
                    'initial_debit': 0.0,
                    'initial_credit': 0.0,
                    'period_debit': 0.0,
                    'period_credit': 0.0,
                    'end_debit': 0.0,
                    'end_credit': 0.0,
                }

        # Sort by account code and return as ordered dict
        return accounts_data

    def _generate_xml_cdtk(self, accounts_data):
        """
        Generate XML content in CDTK format
        
        Structure:
        <PL_CDTK>
            <SoDuDauKy>
                <No><ct111>value</ct111>...</No>
                <Co><ct111>value</ct111>...</Co>
            </SoDuDauKy>
            <SoPhatSinhTrongKy>
                <No><ct111>value</ct111>...</No>
                <Co><ct111>value</ct111>...</Co>
            </SoPhatSinhTrongKy>
            <SoDuCuoiKy>
                <No><ct111>value</ct111>...</No>
                <Co><ct111>value</ct111>...</Co>
            </SoDuCuoiKy>
        </PL_CDTK>
        """
        # Create root element
        root = ET.Element('PL_CDTK')
        
        # Sort accounts by code
        sorted_accounts = sorted(accounts_data.items())
        
        # SoDuDauKy (Initial Balance)
        so_du_dau_ky = ET.SubElement(root, 'SoDuDauKy')
        no_dau_ky = ET.SubElement(so_du_dau_ky, 'No')
        co_dau_ky = ET.SubElement(so_du_dau_ky, 'Co')

        for account_code, data in sorted_accounts:
            # Format account code for XML tag (replace . with empty, - with empty)
            xml_tag = 'ct' + account_code.replace('.', '').replace('-', '').replace(' ', '')
            if account_code == 'tongCong':
                xml_tag = 'tongCong'

            # Initial Debit
            elem = ET.SubElement(no_dau_ky, xml_tag)
            elem.text = str(int(round(data['initial_debit'])))

            # Initial Credit
            elem = ET.SubElement(co_dau_ky, xml_tag)
            elem.text = str(int(round(data['initial_credit'])))

        # SoPhatSinhTrongKy (Period Movements)
        so_phat_sinh = ET.SubElement(root, 'SoPhatSinhTrongKy')
        no_phat_sinh = ET.SubElement(so_phat_sinh, 'No')
        co_phat_sinh = ET.SubElement(so_phat_sinh, 'Co')

        for account_code, data in sorted_accounts:
            xml_tag = 'ct' + account_code.replace('.', '').replace('-', '').replace(' ', '')
            if account_code == 'tongCong':
                xml_tag = 'tongCong'

            # Period Debit
            elem = ET.SubElement(no_phat_sinh, xml_tag)
            elem.text = str(int(round(data['period_debit'])))

            # Period Credit
            elem = ET.SubElement(co_phat_sinh, xml_tag)
            elem.text = str(int(round(data['period_credit'])))

        # SoDuCuoiKy (End Balance)
        so_du_cuoi_ky = ET.SubElement(root, 'SoDuCuoiKy')
        no_cuoi_ky = ET.SubElement(so_du_cuoi_ky, 'No')
        co_cuoi_ky = ET.SubElement(so_du_cuoi_ky, 'Co')

        for account_code, data in sorted_accounts:
            xml_tag = 'ct' + account_code.replace('.', '').replace('-', '').replace(' ', '')
            if account_code == 'tongCong':
                xml_tag = 'tongCong'

            # End Debit
            elem = ET.SubElement(no_cuoi_ky, xml_tag)
            elem.text = str(int(round(data['end_debit'])))

            # End Credit
            elem = ET.SubElement(co_cuoi_ky, xml_tag)
            elem.text = str(int(round(data['end_credit'])))

        # Convert to string with pretty printing
        xml_string = ET.tostring(root, encoding='unicode')
        
        # Pretty print
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
        
        # Remove extra blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)
        
        return pretty_xml

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        """
        Override để tách riêng code và name cho cả account.account và account.group
        khi export Trial Balance ra Excel
        """

        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        title_format = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        default_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12,
                                'num_format': '#,##0.00'}
        text_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12}
        date_format_props = {'font_name': 'Arial', 'font_color': '#666666', 'font_size': 12, 'num_format': 'yyyy-mm-dd'}
        workbook_formats = {
            0: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
            },
            1: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'default_indent': workbook.add_format(
                    {**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
                'date_indent': workbook.add_format(
                    {**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
            },
            2: {
                'default': workbook.add_format({**default_format_props, 'bold': True}),
                'text': workbook.add_format({**text_format_props, 'bold': True}),
                'date': workbook.add_format({**date_format_props, 'bold': True}),
                'initial': workbook.add_format(default_format_props),
                'total': workbook.add_format({**default_format_props, 'bold': True}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'indent': 2}),
                'initial_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 1}),
            },
            'default': {
                'default': workbook.add_format(default_format_props),
                'text': workbook.add_format(text_format_props),
                'date': workbook.add_format(date_format_props),
                'total': workbook.add_format(default_format_props),
                'default_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'indent': 2}),
            },
        }

        def get_format(content_type='default', level='default'):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats['default'],
                    'default_indent': workbook.add_format({**default_format_props, 'indent': level}),
                    'date_indent': workbook.add_format({**date_format_props, 'indent': level}),
                    'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': level - 1}),
                }

            level_formats = workbook_formats[level]
            if '_indent' in content_type and not level_formats.get(content_type):
                return level_formats.get('default_indent', level_formats.get(content_type.removesuffix('_indent'),
                                                                             level_formats['default']))
            return level_formats.get(content_type, level_formats['default'])

        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))

        # Tách code và name cho CẢ account.account VÀ account.group
        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            # Thêm điều kiện cho account.group
            if line_model in ('account.account', 'account.group'):
                # Tách code và name
                if line_model == 'account.account':
                    # Sử dụng method gốc của account nếu có
                    if hasattr(self.env['account.account'], '_split_code_name'):
                        account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(
                            line['name'])
                    else:
                        account_lines_split_names[line['id']] = _split_code_name_helper(line['name'])
                elif line_model == 'account.group':
                    # Tách code và name cho group bằng helper method
                    account_lines_split_names[line['id']] = _split_code_name_helper(line['name'])

        # Set column widths
        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 11)  # Code column
            sheet.set_column(1, 1, 50)  # Name column
        else:
            sheet.set_column(0, 0, 50)

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

        y_offset = 0
        x_offset = original_x_offset + 1

        # Add headers
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan',
                                               column_headers_render_data['level_colspan'][header_level_index])
                write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_format)
                x_offset += colspan
            if options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_format)
            y_offset += 1
            x_offset = original_x_offset + 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1
        x_offset = original_x_offset + 1

        if account_lines_split_names:
            # Add titles for Code and Account Name columns
            sheet.write(y_offset, x_offset - 2, _("Code"), title_format)
            sheet.write(y_offset, x_offset - 1, _("Account Name"), title_format)
        sheet.set_column(x_offset, x_offset + len(options['columns']), 10)

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_format)
            x_offset += colspan
        y_offset += 1

        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        # Disable bold styling for the max level
        max_level = max(line.get('level', -1) for line in lines) if lines else -1
        if max_level in {0, 1, 2}:
            for wb_format in (s for s in workbook_formats[max_level] if 'total' not in s):
                workbook_formats[max_level][wb_format].set_bold(False)

        # Add lines
        for y, line in enumerate(lines):
            level = line.get('level')
            if level == 0:
                y_offset += 1
            elif not level:
                level = 'default'

            line_id = self._parse_line_id(line.get('id'))
            is_initial_line = line_id[-1][0] == 'initial' if line_id else False
            is_total_line = line_id[-1][0] == 'total' if line_id else False

            # Determine cell format
            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format('text', level)

            if cell_type == 'date':
                cell_format = get_format('date_indent', level)
            elif is_initial_line:
                cell_format = get_format('initial_indent', level)
            elif is_total_line:
                cell_format = get_format('total_indent', level)
            else:
                cell_format = get_format('default_indent', level)

            x_offset = original_x_offset + 1

            # Viết code và name vào 2 cột riêng biệt cho cả account và group
            if lines[y]['id'] in account_lines_split_names:
                code, name = account_lines_split_names[lines[y]['id']]
                # Write code in column 0, name in column 1
                sheet.write(y + y_offset, 0, code, account_code_cell_format)
                sheet.write(y + y_offset, 1, name, cell_format)
            else:
                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, original_x_offset, cell_value, cell_format)

                if 'parent_id' in line and line['parent_id'] in account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, account_lines_split_names[line['parent_id']][0],
                                account_code_cell_format)
                elif account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, "", account_code_cell_format)

            # Write all remaining cells (columns with values)
            columns = line['columns']
            if options['show_growth_comparison'] and 'growth_comparison_data' in line:
                columns += [line['growth_comparison_data']]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)

                if cell_type == 'date':
                    cell_format = get_format('date', level)
                elif is_initial_line:
                    cell_format = get_format('initial', level)
                elif is_total_line:
                    cell_format = get_format('total', level)
                else:
                    cell_format = get_format('default', level)

                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, x + line.get('colspan', 1) - 1, cell_value, cell_format)

    def _get_account_balance(self, account_code, date_to, options, balance_type='credit'):
        """Generic method to get account balance for receivable or payable with group by partner.

        Args:
            account_code (str): The account code to search for
            date_to (str): The end date for the balance
            options (dict): The report options
            balance_type (str): Type of balance to return ('credit' or 'debit')

        Returns:
            dict: Result containing the requested balance
        """
        account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
        if not account:
            return {'result': 0.0}

        values = self._compute_account_balance(
            account_id=account.id,
            date=date_to,
            options=options
        )
        return {'result': values[balance_type]}

    def _compute_account_balance(self, account_id, date, options):
        """Compute debit and credit balances with group by partner for an account using optimized SQL.

        Args:
            account_id (int): Account ID
            date (str): The date to compute balance for
            options (dict): Report options containing journals and entry state

        Returns:
            dict: Contains 'debit' and 'credit' balances
        """
        journal_ids = tuple(int(journal['id']) for journal in options.get('journals', [])) or (0,)
        states = ('posted', 'draft') if options.get('all_entries') else ('posted',)

        query = """
            WITH partner_balance AS (
                SELECT
                    aml.partner_id, 
                    SUM(balance) as balance
                FROM
                    account_move_line AS aml
                WHERE
                    aml."date" <= %s
                    AND aml.account_id = %s
                    AND aml.journal_id IN %s
                    AND aml.parent_state IN %s
                GROUP BY
                    aml.partner_id
            )
            SELECT 
                SUM(CASE WHEN balance > 0 THEN balance ELSE 0 END) AS debit,
                SUM(CASE WHEN balance < 0 THEN -balance ELSE 0 END) AS credit
            FROM partner_balance
        """

        self.env.cr.execute(query, (date, account_id, journal_ids, states))
        return self.env.cr.dictfetchone() or {'debit': 0.0, 'credit': 0.0}

    def _report_custom_engine_331C_date_to(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_account_balance('331', options['date']['date_to'], options, 'credit')

    def _report_custom_engine_331D_date_to(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_account_balance('331', options['date']['date_to'], options, 'debit')

    def _report_custom_engine_131C_date_to(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_account_balance('131', options['date']['date_to'], options, 'credit')

    def _report_custom_engine_131D_date_to(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_account_balance('131', options['date']['date_to'], options, 'debit')

    def _get_counterpart_balance(self, account_code, counters_code, date_from, date_to, options, balance_type='balance'):
        """Custom report engine for testing with optimized account search and balance calculation."""
        # Validate account codes to prevent regex injection via SIMILAR TO pattern
        _code_re = re.compile(r'^[A-Za-z0-9]+$')
        if account_code and not _code_re.match(account_code):
            raise UserError(_("Invalid account code format: %s") % account_code)
        if counters_code and not _code_re.match(counters_code):
            raise UserError(_("Invalid account code format: %s") % counters_code)

        # Get accounts with a single optimized query using a CTE
        query = """
            WITH RECURSIVE
            account_tree AS (
                SELECT id, code FROM account_account 
                WHERE code SIMILAR TO %s
            )
            SELECT id, code FROM account_tree;
        """
        self.env.cr.execute(query, (f'({account_code}%|{counters_code}%)%',))
        account_rows = self.env.cr.dictfetchall()

        if not account_rows:
            return {'result': 0.0}

        accounts = self.env['account.account'].browse([row['id'] for row in account_rows])
        account_ids = accounts.filtered(lambda a: a.code.startswith(account_code))
        counter_ids = accounts - account_ids

        if not account_ids:
            return {'result': 0.0}

        value = self._compute_counterpart_balance(
            account_ids=account_ids,
            date_from=options['date']['date_from'],
            date_to=options['date']['date_to'],
            options=options,
            balance_type=balance_type,
            counter_ids=counter_ids
        )
        return {'result': value}

    def _compute_counterpart_balance(self, account_ids, date_from, date_to, options, balance_type='balance', counter_ids=None):
        if not account_ids or not counter_ids:
            return 0.0

        states = ('posted', 'draft') if options.get('all_entries') else ('posted',)
        journal_ids = tuple(int(journal['id']) for journal in options.get('journals', [])) or (0,)

        query = """           
                SELECT 
                    COALESCE(SUM(aml.debit), 0.0) as debit,
                    COALESCE(SUM(aml.credit), 0.0) as credit,
                    COALESCE(SUM(aml.debit - aml.credit), 0.0) as balance
                FROM account_move_line aml
                JOIN account_move_line_ctp rel ON rel.dr_aml_id = aml.id OR rel.cr_aml_id = aml.id
                JOIN account_move_line counter_aml ON 
                    (counter_aml.id = rel.cr_aml_id AND rel.dr_aml_id = aml.id) 
                    OR (counter_aml.id = rel.dr_aml_id AND rel.cr_aml_id = aml.id)
                WHERE aml.account_id = ANY(%s)
                    AND counter_aml.account_id = ANY(%s)
                    AND aml.date BETWEEN %s AND %s
                    AND aml.journal_id = ANY(%s)
                    AND aml.parent_state = ANY(%s)
        """

        try:
            self.env.cr.execute(query, (
                list(account_ids.ids),
                list(counter_ids.ids),
                date_from,
                date_to,
                list(journal_ids),
                list(states)
            ))
            result = self.env.cr.dictfetchone()
            return result[balance_type] if result else 0.0
        except Exception as e:
            _logger.error("Error computing counterpart balance: %s", str(e))
            return 0.0

    def _report_custom_engine_5111C_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('511', '', options['date']['date_to'], options['date']['date_to'], options, 'credit')

    def _report_custom_engine_515D911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('515', '911', options['date']['date_to'], options['date']['date_to'], options, 'debit')

    def _report_custom_engine_632C911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('632', '911', options['date']['date_to'], options['date']['date_to'], options, 'credit')

    def _report_custom_engine_511D111_112_113_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('632', '111|112|113', options['date']['date_to'], options['date']['date_to'], options, 'debit')

    def _report_custom_engine_635C911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('635', '911', options['date']['date_to'], options['date']['date_to'], options, 'credit')

    def _report_custom_engine_642C911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('642', '911', options['date']['date_to'], options['date']['date_to'], options, 'credit')

    def _report_custom_engine_711D911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('711', '911', options['date']['date_to'], options['date']['date_to'], options, 'debit')

    def _report_custom_engine_811C911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        return self._get_counterpart_balance('811', '911', options['date']['date_to'], options['date']['date_to'], options, 'credit')

    def _report_custom_engine_821B911_period(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        result = self._get_counterpart_balance('821', '911', options['date']['date_to'], options['date']['date_to'], options, 'balance')
        return {'result': -result['result']}

    def _report_custom_engine_ct01_b02(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """
        CT01 - Doanh thu bán hàng và cung cấp dịch vụ (B02-DNN-TT133).

        Công thức JSON:
            PhatsinhCO(511)
            - PhatsinhDU(911/511)                          -- Nợ 911 / Có 511 (hoàn nhập kết chuyển, hiếm gặp)
            - [CO_CKTM(511) + CO_GGHB(511) + CO_HBTL(511)] -- Có 511 có analytic giảm trừ (hoàn ngược deduction)
            - PhatsinhNO(511)                              -- toàn bộ Nợ 511
            + PhatsinhDU(511/911)                          -- Nợ 511 / Có 911 (kết chuyển doanh thu cuối kỳ)
            + [NO_CKTM(511) + NO_GGHB(511) + NO_HBTL(511)] -- Nợ 511 có analytic (cộng lại deductions)

        Rút gọn:
            = (CO_511 - CO_chitiet) - (NO_511 - NO_chitiet) - DU(911/511) + DU(511/911)
            ≈ CO_511 - CO_chitiet  (trong thực tế, NO_511_net ≈ DU(511/911))
        """
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        states = list({'posted', 'draft'} if options.get('all_entries') else {'posted'})
        company_ids = list(self.env.companies.ids)
        cr = self.env.cr

        # -- 1. Tổng CO(511) và NO(511) --
        cr.execute("""
            SELECT
                COALESCE(SUM(aml.credit), 0),
                COALESCE(SUM(aml.debit),  0)
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN account_move    am ON am.id = aml.move_id
            WHERE am.state      = ANY(%s)
              AND am.company_id = ANY(%s)
              AND aa.code LIKE '511%%'
              AND aml.date BETWEEN %s AND %s
        """, (states, company_ids, date_from, date_to))
        row = cr.fetchone()
        co_511 = float(row[0] or 0)
        no_511 = float(row[1] or 0)

        # -- 2. CO_chitiet và NO_chitiet (analytic CKTM / GGHB / HBTL) --
        analytic_codes = ['CKTM', 'GGHB', 'HBTL']
        cr.execute("""
            SELECT
                COALESCE(SUM(aml.credit), 0),
                COALESCE(SUM(aml.debit),  0)
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN account_move    am ON am.id = aml.move_id
            WHERE am.state      = ANY(%s)
              AND am.company_id = ANY(%s)
              AND aa.code LIKE '511%%'
              AND aml.date BETWEEN %s AND %s
              AND aml.analytic_distribution IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM account_analytic_account aaa
                  WHERE aaa.code = ANY(%s)
                    AND aml.analytic_distribution::text LIKE ('%%"' || aaa.id::text || '"%%')
              )
        """, (states, company_ids, date_from, date_to, analytic_codes))
        row = cr.fetchone()
        co_chitiet = float(row[0] or 0)
        no_chitiet = float(row[1] or 0)

        # -- 3. DU(911/511) và DU(511/911) qua bảng CTP --
        _CTP_SQL = """
            SELECT COALESCE(SUM(ctp.countered_amt), 0)
            FROM account_move_line_ctp ctp
            JOIN account_move_line aml_dr ON aml_dr.id = ctp.dr_aml_id
            JOIN account_account   aa_dr  ON aa_dr.id  = aml_dr.account_id
            JOIN account_move_line aml_cr ON aml_cr.id = ctp.cr_aml_id
            JOIN account_account   aa_cr  ON aa_cr.id  = aml_cr.account_id
            JOIN account_move      am     ON am.id     = aml_dr.move_id
            WHERE am.state      = ANY(%s)
              AND am.company_id = ANY(%s)
              AND aa_dr.code LIKE %s
              AND aa_cr.code LIKE %s
              AND aml_dr.date BETWEEN %s AND %s
        """
        cr.execute(_CTP_SQL, (states, company_ids, '911%', '511%', date_from, date_to))
        du_911_511 = float(cr.fetchone()[0] or 0)

        cr.execute(_CTP_SQL, (states, company_ids, '511%', '911%', date_from, date_to))
        du_511_911 = float(cr.fetchone()[0] or 0)

        result = co_511 - du_911_511 - co_chitiet - no_511 + du_511_911 + no_chitiet
        return {'result': result}

