# -*- coding: utf-8 -*-
import io
import json
import base64
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class AccountJournalItemsReportWizard(models.TransientModel):
    _name = 'account.journal.items.report.wizard'
    _description = 'Wizard Chi tiết bút toán theo tài khoản'

    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Đến ngày',
        required=True,
        default=fields.Date.today
    )
    account_ids = fields.Many2many(
        'account.account',
        'account_journal_items_report_account_rel',
        'wizard_id',
        'account_id',
        string='Tài khoản',
    )
    all_accounts = fields.Boolean(
        string='Tất cả tài khoản',
        default=False
    )
    journal_ids = fields.Many2many(
        'account.journal',
        'account_journal_items_report_journal_rel',
        'wizard_id',
        'journal_id',
        string='Sổ nhật ký',
        default=lambda self: self.env['account.journal'].with_context(active_test=False).search([
            ('company_id', '=', self.env.company.id)
        ])
    )
    state_filter = fields.Selection([
        ('all', 'Tất cả'),
        ('posted', 'Đã ghi sổ (Posted)'),
        ('draft', 'Nháp (Draft)'),
    ], string='Trạng thái', default='posted', required=True)
    
    skip_no_transaction = fields.Boolean(
        string='Bỏ qua TK không phát sinh',
        default=True,
        help='Không in những tài khoản không có giao dịch trong kỳ'
    )
    max_accounts_per_pdf = fields.Integer(
        string='Số TK tối đa / file PDF',
        default=50,
        help='Giới hạn số tài khoản mỗi file PDF để tránh timeout. 0 = không giới hạn'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
        required=True
    )
    # Field để lưu data tạm thời cho PDF report
    report_data_json = fields.Text(string='Report Data JSON')

    @api.onchange('all_accounts')
    def _onchange_all_accounts(self):
        if self.all_accounts:
            self.account_ids = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Cập nhật danh sách journals khi đổi công ty - bao gồm cả archived"""
        self.journal_ids = self.env['account.journal'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id)
        ])

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_('Ngày bắt đầu phải nhỏ hơn ngày kết thúc!'))

    def _get_accounts(self):
        """Lấy danh sách tài khoản cần báo cáo"""
        if self.all_accounts:
            return self.env['account.account'].search([
                ('company_id', '=', self.company_id.id)
            ], order='code')
        elif self.account_ids:
            return self.account_ids.sorted(key=lambda a: a.code)
        else:
            raise UserError(_('Vui lòng chọn ít nhất một tài khoản hoặc chọn "Tất cả tài khoản"!'))

    def _get_state_domain(self):
        """Trả về domain cho state filter"""
        if self.state_filter == 'posted':
            return [('parent_state', '=', 'posted')]
        elif self.state_filter == 'draft':
            return [('parent_state', '=', 'draft')]
        else:
            return [('parent_state', 'in', ['posted', 'draft'])]

    def _get_opening_balance(self, account):
        """Tính số dư đầu kỳ từ account.move.line"""
        domain = [
            ('account_id', '=', account.id),
            ('company_id', '=', self.company_id.id),
            ('date', '<', self.date_from),
        ]
        # Thêm filter theo journals
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        # Thêm filter theo state
        domain += self._get_state_domain()
        
        self.env.cr.execute("""
            SELECT 
                COALESCE(SUM(aml.debit), 0) as debit,
                COALESCE(SUM(aml.credit), 0) as credit,
                COALESCE(SUM(aml.balance), 0) as balance
            FROM account_move_line aml
            WHERE aml.account_id = %s
                AND aml.company_id = %s
                AND aml.date < %s
                AND aml.journal_id IN %s
                AND aml.parent_state IN %s
        """, (
            account.id, 
            self.company_id.id, 
            self.date_from,
            tuple(self.journal_ids.ids) if self.journal_ids else (0,),
            ('posted',) if self.state_filter == 'posted' else 
            ('draft',) if self.state_filter == 'draft' else ('posted', 'draft')
        ))
        result = self.env.cr.fetchone()
        return {
            'debit': result[0] if result else 0,
            'credit': result[1] if result else 0,
            'balance': result[2] if result else 0,
        }

    def _get_journal_items(self, account):
        """Lấy các dòng journal items trong kỳ"""
        domain = [
            ('account_id', '=', account.id),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        # Thêm filter theo journals
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        # Thêm filter theo state
        domain += self._get_state_domain()

        lines = self.env['account.move.line'].search(domain, order='date, journal_id, ref')

        items = []
        for line in lines:
            # Format date
            date_str = line.date.strftime('%Y/%m/%d') if line.date else ''
            
            # Invoice date: lấy invoice_date, nếu không có thì lấy date
            invoice_date = line.move_id.invoice_date or line.date
            invoice_date_str = invoice_date.strftime('%Y/%m/%d') if invoice_date else ''
            
            # TKDU: lấy ctp_account_ids.code, phân cách bằng dấu phẩy
            ctp_accounts = ''
            if hasattr(line, 'ctp_account_ids') and line.ctp_account_ids:
                ctp_accounts = ', '.join(line.ctp_account_ids.mapped('code'))
            
            items.append({
                'date': date_str,
                'move_name': line.move_id.name or '',
                'invoice_date': invoice_date_str,
                'name': line.name or '',
                'ctp_accounts': ctp_accounts,
                'debit': line.debit,
                'credit': line.credit,
            })
        return items

    def _has_transaction(self, account):
        """Kiểm tra tài khoản có giao dịch trong kỳ không"""
        domain = [
            ('account_id', '=', account.id),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        domain += self._get_state_domain()
        
        return self.env['account.move.line'].search_count(domain) > 0

    def _prepare_report_data(self):
        """Chuẩn bị dữ liệu cho báo cáo"""
        accounts = self._get_accounts()
        
        state_label = {
            'all': 'Tất cả',
            'posted': 'Đã ghi sổ',
            'draft': 'Nháp',
        }
        
        report_data = {
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'company': self.company_id.name,
            'state_filter': state_label.get(self.state_filter, ''),
            'journals': ', '.join(self.journal_ids.mapped('name')) if self.journal_ids else 'Tất cả',
            'accounts': [],
        }

        for account in accounts:
            # Kiểm tra nếu bỏ qua TK không phát sinh
            if self.skip_no_transaction and not self._has_transaction(account):
                continue
                
            opening = self._get_opening_balance(account)
            items = self._get_journal_items(account)
            
            # Tính tổng phát sinh trong kỳ
            total_debit = sum(m['debit'] for m in items)
            total_credit = sum(m['credit'] for m in items)
            
            # Tính số dư cuối kỳ
            closing_balance = opening['balance'] + total_debit - total_credit

            account_data = {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'opening_debit': opening['debit'],
                'opening_credit': opening['credit'],
                'opening_balance': opening['balance'],
                'items': items,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'closing_balance': closing_balance,
            }
            report_data['accounts'].append(account_data)

        return report_data

    def action_view_report(self):
        """Mở báo cáo HTML preview"""
        self.ensure_one()
        
        if not self.journal_ids:
            raise UserError(_('Vui lòng chọn ít nhất một sổ nhật ký!'))
        
        report_data = self._prepare_report_data()
        
        if not report_data['accounts']:
            raise UserError(_('Không có tài khoản nào có giao dịch trong kỳ!'))
        
        # Tính running balance
        for account in report_data.get('accounts', []):
            running_balance = account['opening_balance']
            for item in account['items']:
                running_balance += item['debit'] - item['credit']
                item['running_balance'] = running_balance
        
        # Lưu data vào wizard
        self.write({'report_data_json': json.dumps(report_data)})
        
        # Mở HTML report preview
        return self.env.ref('account_journal_items_report.action_report_journal_items_html').report_action(
            self, data={'wizard_id': self.id}
        )

    def action_print_pdf(self):
        """In báo cáo PDF"""
        self.ensure_one()
        
        if not self.journal_ids:
            raise UserError(_('Vui lòng chọn ít nhất một sổ nhật ký!'))
        
        report_data = self._prepare_report_data()
        
        if not report_data['accounts']:
            raise UserError(_('Không có tài khoản nào có giao dịch trong kỳ!'))
        
        total_accounts = len(report_data['accounts'])
        max_per_pdf = self.max_accounts_per_pdf or 0
        
        # Nếu có giới hạn và số TK vượt quá, tạo file ZIP chứa nhiều PDF
        if max_per_pdf > 0 and total_accounts > max_per_pdf:
            return self._generate_multiple_pdfs(report_data, max_per_pdf)
        
        # Tính running balance
        for account in report_data.get('accounts', []):
            running_balance = account['opening_balance']
            for item in account['items']:
                running_balance += item['debit'] - item['credit']
                item['running_balance'] = running_balance
        
        # Lưu data vào wizard để report đọc lại
        self.write({'report_data_json': json.dumps(report_data)})
        
        # Tăng timeout cho wkhtmltopdf thông qua context
        return self.env.ref('account_journal_items_report.action_report_journal_items').with_context(
            report_timeout=600  # 10 phút
        ).report_action(self, data={'wizard_id': self.id})

    def _generate_multiple_pdfs(self, report_data, max_per_pdf):
        """Tạo nhiều file PDF và đóng gói thành ZIP"""
        import zipfile
        
        accounts = report_data['accounts']
        total_accounts = len(accounts)
        num_files = (total_accounts + max_per_pdf - 1) // max_per_pdf
        
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i in range(num_files):
                start_idx = i * max_per_pdf
                end_idx = min((i + 1) * max_per_pdf, total_accounts)
                
                # Tạo subset data
                subset_data = {
                    'date_from': report_data['date_from'],
                    'date_to': report_data['date_to'],
                    'company': report_data['company'],
                    'state_filter': report_data['state_filter'],
                    'journals': report_data['journals'],
                    'accounts': accounts[start_idx:end_idx],
                }
                
                # Tính running balance cho subset
                for account in subset_data['accounts']:
                    running_balance = account['opening_balance']
                    for item in account['items']:
                        running_balance += item['debit'] - item['credit']
                        item['running_balance'] = running_balance
                
                # Lưu data và tạo PDF
                self.write({'report_data_json': json.dumps(subset_data)})
                
                # Render PDF
                report = self.env.ref('account_journal_items_report.action_report_journal_items')
                pdf_content, _ = report.with_context(report_timeout=300)._render_qweb_pdf(
                    report.report_name, [self.id], data={'wizard_id': self.id}
                )
                
                # Thêm vào ZIP
                filename = f'Bao_cao_but_toan_phan_{i+1}_of_{num_files}.pdf'
                zipf.writestr(filename, pdf_content)
        
        output.seek(0)
        zip_data = output.read()
        
        # Tạo attachment
        filename = f'Chi_tiet_but_toan_{self.date_from}_{self.date_to}.zip'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(zip_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/zip',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _generate_xlsx_data(self, report_data=None):
        """Tạo dữ liệu Excel, trả về bytes"""
        if not xlsxwriter:
            raise UserError(_('Thư viện xlsxwriter chưa được cài đặt!'))
        
        if report_data is None:
            report_data = self._prepare_report_data()
            # Tính running balance
            for account in report_data.get('accounts', []):
                running_balance = account['opening_balance']
                for item in account['items']:
                    running_balance += item['debit'] - item['credit']
                    item['running_balance'] = running_balance
        
        if not report_data.get('accounts'):
            raise UserError(_('Không có tài khoản nào có giao dịch trong kỳ!'))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Định dạng
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })
        subtitle_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
        })
        col_header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'font_size': 10,
            'border': 1,
            'text_wrap': True,
        })
        text_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1,
        })
        text_center_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1,
        })
        number_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0',
            'font_size': 10,
            'border': 1,
        })
        total_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0',
            'border': 1,
            'font_size': 10,
            'bg_color': '#E8E8E8',
        })
        total_text_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#E8E8E8',
        })
        opening_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'border': 1,
            'bg_color': '#F5F5F5',
        })
        opening_value_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0',
            'font_size': 10,
            'border': 1,
            'bg_color': '#F5F5F5',
        })

        sheet_names_used = {}
        
        for account in report_data['accounts']:
            # Tạo sheet mới cho mỗi tài khoản
            base_name = (account.get('code') or account.get('name', 'Account'))[:28]
            base_name = base_name.replace('/', '-').replace('\\', '-').replace('*', '-').replace('?', '-').replace('[', '-').replace(']', '-')
            
            # Đảm bảo tên sheet là duy nhất
            sheet_name = base_name
            if sheet_name in sheet_names_used:
                sheet_names_used[sheet_name] += 1
                sheet_name = f"{base_name[:25]}_{sheet_names_used[sheet_name]}"
            else:
                sheet_names_used[sheet_name] = 0
            
            worksheet = workbook.add_worksheet(sheet_name[:31])

            # Set column widths - cấu trúc mới: Ngày, Số CT, Ngày CT, Diễn giải, TKĐƯ, Nợ, Có, Số dư
            worksheet.set_column('A:A', 11)   # Ngày
            worksheet.set_column('B:B', 15)   # Số chứng từ
            worksheet.set_column('C:C', 11)   # Ngày CT
            worksheet.set_column('D:D', 40)   # Diễn giải
            worksheet.set_column('E:E', 15)   # TKĐƯ
            worksheet.set_column('F:F', 15)   # Nợ
            worksheet.set_column('G:G', 15)   # Có

            row = 0

            # Tiêu đề
            worksheet.merge_range(row, 0, row, 6, 'CHI TIẾT BÚT TOÁN THEO TÀI KHOẢN', title_format)
            row += 1
            worksheet.merge_range(row, 0, row, 6, f'Tài khoản: {account.get("code", "")} - {account.get("name", "")}', subtitle_format)
            row += 1
            worksheet.merge_range(row, 0, row, 6, 
                f'Từ ngày: {report_data.get("date_from", "")} - Đến ngày: {report_data.get("date_to", "")}', subtitle_format)
            row += 2

            # Header columns - cấu trúc mới
            headers = ['Ngày', 'Số CT', 'Ngày CT', 'Diễn giải', 'TKĐƯ', 'Nợ', 'Có']
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, col_header_format)
            row += 1

            # Dòng số dư đầu kỳ
            running_balance = account.get('opening_balance', 0)
            worksheet.write(row, 0, '', opening_format)
            worksheet.write(row, 1, '', opening_format)
            worksheet.write(row, 2, '', opening_format)
            worksheet.write(row, 3, 'Số dư đầu kỳ', opening_format)
            worksheet.write(row, 4, '', opening_format)
            if running_balance >= 0:
                worksheet.write(row, 5, running_balance, opening_value_format)
                worksheet.write(row, 6, '', opening_value_format)
            else:
                worksheet.write(row, 5, '', opening_value_format)
                worksheet.write(row, 6, abs(running_balance), opening_value_format)
            row += 1

            # Chi tiết các giao dịch
            for item in account.get('items', []):
                running_balance += item.get('debit', 0) - item.get('credit', 0)
                
                worksheet.write(row, 0, item.get('date', ''), text_center_format)
                worksheet.write(row, 1, item.get('move_name', ''), text_format)
                worksheet.write(row, 2, item.get('invoice_date', ''), text_center_format)
                worksheet.write(row, 3, item.get('name', ''), text_format)
                worksheet.write(row, 4, item.get('ctp_accounts', ''), text_format)
                worksheet.write(row, 5, item.get('debit', 0) or '', number_format)
                worksheet.write(row, 6, item.get('credit', 0) or '', number_format)
                row += 1

            # Dòng tổng cộng
            worksheet.write(row, 0, '', opening_format)
            worksheet.write(row, 1, '', opening_format)
            worksheet.write(row, 2, '', opening_format)
            worksheet.write(row, 3, 'Tổng cộng phát sinh', opening_format)
            worksheet.write(row, 4, '', opening_format)
            worksheet.write(row, 5, account.get('total_debit', 0), opening_value_format)
            worksheet.write(row, 6, account.get('total_credit', 0), opening_value_format)

            # Dòng tổng cộng
            worksheet.write(row, 0, '', total_text_format)
            worksheet.write(row, 1, '', total_text_format)
            worksheet.write(row, 2, '', total_text_format)
            worksheet.write(row, 3, 'Số dư cuối kỳ', total_text_format)
            worksheet.write(row, 4, '', total_text_format)
            if account.get('closing_balance', 0) >= 0:
                worksheet.write(row, 5, account.get('closing_balance', 0), total_format)
                worksheet.write(row, 6, '', total_format)
            else:
                worksheet.write(row, 5, '', total_format)
                worksheet.write(row, 6, abs(account.get('closing_balance', 0)), total_format)

        workbook.close()
        output.seek(0)
        return output.read()

    def action_export_xlsx(self):
        """Xuất báo cáo Excel"""
        self.ensure_one()
        
        if not self.journal_ids:
            raise UserError(_('Vui lòng chọn ít nhất một sổ nhật ký!'))
        
        # Lấy report data từ JSON nếu có, hoặc tạo mới
        if self.report_data_json:
            report_data = json.loads(self.report_data_json)
        else:
            report_data = None
        
        xlsx_data = self._generate_xlsx_data(report_data)

        # Tạo attachment
        filename = f'Chi_tiet_but_toan_{self.date_from}_{self.date_to}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class AccountJournalItemsReportPdf(models.AbstractModel):
    _name = 'report.account_journal_items_report.report_journal_items'
    _description = 'Chi Tiết bút toán PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_data = {'accounts': [], 'date_from': '', 'date_to': '', 'company': '', 'state_filter': '', 'journals': ''}
        
        # Lấy wizard_id từ data hoặc docids
        wizard_id = data.get('wizard_id') if data else None
        if not wizard_id and docids:
            wizard_id = docids[0]
        
        if wizard_id:
            wizard = self.env['account.journal.items.report.wizard'].browse(wizard_id)
            if wizard.exists():
                if wizard.report_data_json:
                    report_data = json.loads(wizard.report_data_json)
                else:
                    # Tạo data mới nếu chưa có
                    report_data = wizard._prepare_report_data()
                    # Tính running balance
                    for account in report_data.get('accounts', []):
                        running_balance = account['opening_balance']
                        for item in account['items']:
                            running_balance += item['debit'] - item['credit']
                            item['running_balance'] = running_balance
                    # Lưu lại để lần sau dùng
                    wizard.write({'report_data_json': json.dumps(report_data)})
        
        # Đảm bảo luôn có key accounts
        if 'accounts' not in report_data:
            report_data['accounts'] = []
        
        # Tính toán running balance cho mỗi tài khoản
        for account in report_data.get('accounts', []):
            if account.get('items') and 'running_balance' not in account['items'][0]:
                running_balance = account.get('opening_balance', 0)
                for item in account.get('items', []):
                    running_balance += item.get('debit', 0) - item.get('credit', 0)
                    item['running_balance'] = running_balance

        return {
            'doc_ids': docids,
            'doc_model': 'account.journal.items.report.wizard',
            'docs': self.env['account.journal.items.report.wizard'].browse(docids if docids else []),
            'data': report_data,
            'company': self.env.company,
        }


class AccountJournalItemsReportHtml(models.AbstractModel):
    _name = 'report.account_journal_items_report.report_journal_items_html'
    _description = 'Chi Tiết bút toán HTML Preview'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_data = {'accounts': [], 'date_from': '', 'date_to': '', 'company': '', 'state_filter': '', 'journals': ''}
        
        # Lấy wizard_id từ data hoặc docids
        wizard_id = data.get('wizard_id') if data else None
        if not wizard_id and docids:
            wizard_id = docids[0]
        
        if wizard_id:
            wizard = self.env['account.journal.items.report.wizard'].browse(wizard_id)
            if wizard.exists():
                if wizard.report_data_json:
                    report_data = json.loads(wizard.report_data_json)
                else:
                    # Tạo data mới nếu chưa có
                    report_data = wizard._prepare_report_data()
                    # Tính running balance
                    for account in report_data.get('accounts', []):
                        running_balance = account.get('opening_balance', 0)
                        for item in account.get('items', []):
                            running_balance += item.get('debit', 0) - item.get('credit', 0)
                            item['running_balance'] = running_balance
                    # Lưu lại
                    wizard.write({'report_data_json': json.dumps(report_data)})
        
        # Đảm bảo luôn có key accounts
        if 'accounts' not in report_data:
            report_data['accounts'] = []
        
        # Tính toán running balance nếu chưa có
        for account in report_data.get('accounts', []):
            if account.get('items') and 'running_balance' not in account['items'][0]:
                running_balance = account.get('opening_balance', 0)
                for item in account.get('items', []):
                    running_balance += item.get('debit', 0) - item.get('credit', 0)
                    item['running_balance'] = running_balance

        return {
            'doc_ids': docids,
            'doc_model': 'account.journal.items.report.wizard',
            'docs': self.env['account.journal.items.report.wizard'].browse(docids if docids else [wizard_id] if wizard_id else []),
            'data': report_data,
            'company': self.env.company,
        }
