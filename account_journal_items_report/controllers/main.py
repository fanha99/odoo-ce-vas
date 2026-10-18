# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, content_disposition


class AccountJournalItemsReportController(http.Controller):

    @http.route('/account_journal_items_report/export_xlsx/<int:wizard_id>', type='http', auth='user')
    def export_xlsx(self, wizard_id, **kwargs):
        """Export Excel từ HTML preview - tái sử dụng method từ wizard"""
        wizard = request.env['account.journal.items.report.wizard'].browse(wizard_id)
        
        if not wizard.exists():
            return request.not_found()
        
        # Lấy report data từ JSON đã lưu
        if wizard.report_data_json:
            report_data = json.loads(wizard.report_data_json)
        else:
            report_data = None
        
        # Gọi method _generate_xlsx_data từ wizard
        try:
            xlsx_data = wizard._generate_xlsx_data(report_data)
        except Exception as e:
            return request.not_found()
        
        # Tạo response
        filename = f'So_cai_tk_S03b_{wizard.date_from}_{wizard.date_to}.xlsx'
        
        return request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
                ('Content-Length', len(xlsx_data)),
            ]
        )

    @http.route('/account_journal_items_report/print_pdf/<int:wizard_id>', type='http', auth='user')
    def print_pdf(self, wizard_id, **kwargs):
        """Print PDF từ HTML preview"""
        wizard = request.env['account.journal.items.report.wizard'].browse(wizard_id)
        
        if not wizard.exists():
            return request.not_found()
        
        # Đảm bảo data đã được lưu
        if not wizard.report_data_json:
            report_data = wizard._prepare_report_data()
            wizard.write({'report_data_json': json.dumps(report_data)})
        
        # Render PDF sử dụng report action
        report = request.env.ref('account_journal_items_report.action_report_journal_items')
        pdf_content, _ = report._render_qweb_pdf(
            report.report_name,
            [wizard_id],
            data={'wizard_id': wizard_id}
        )
        
        # Tạo response với PDF
        filename = f'So_cai_tk_S03b_{wizard.date_from}_{wizard.date_to}.pdf'
        
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', content_disposition(filename)),
                ('Content-Length', len(pdf_content)),
            ]
        )
