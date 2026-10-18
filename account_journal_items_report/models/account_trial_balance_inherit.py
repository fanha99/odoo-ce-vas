# -*- coding: utf-8 -*-
import json
from odoo import models, api, _


class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _caret_options_initializer(self):
        """Override để thêm caret option mở báo cáo chi tiết bút toán"""
        caret_options = super()._caret_options_initializer()
        
        # Thêm action mới vào trial_balance caret options
        if 'trial_balance' in caret_options:
            caret_options['trial_balance'].append({
                'name': _("Sổ chi tiết TK (S03b)"),
                'action': 'action_open_journal_items_detail_report',
            })
        
        # Thêm caret options cho dòng Total
        caret_options['trial_balance_total'] = [
            {'name': _("Sổ chi tiết TK (S03b)"), 'action': 'action_open_s03b_all_accounts'},
        ]
        
        return caret_options

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """Override để thêm caret_options cho dòng Total"""
        # Gọi hàm gốc
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings)
        
        # Tìm dòng Total (dòng cuối cùng) và thêm caret_options
        lines_list = list(lines)
        if lines_list:
            # Dòng cuối cùng là Total line
            last_line = lines_list[-1]
            if last_line and len(last_line) > 1:
                last_line[1]['caret_options'] = 'trial_balance_total'
        
        return lines_list


class AccountReport(models.Model):
    _inherit = 'account.report'

    def action_open_journal_items_detail_report(self, options, params):
        """Mở báo cáo chi tiết bút toán HTML trực tiếp trong tab mới"""
        # Lấy thông tin account từ line_id
        record_model, record_id = self._get_model_info_from_id(params.get('line_id'))
        
        if record_model != 'account.account':
            return {'type': 'ir.actions.act_window_close'}
        
        account = self.env['account.account'].browse(record_id)
        if not account.exists():
            return {'type': 'ir.actions.act_window_close'}
        
        # Lấy thông tin từ options
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        
        # Xác định state filter từ options
        all_entries = options.get('all_entries', False)
        state_filter = 'all' if all_entries else 'posted'
        
        # Lấy danh sách journals đã chọn từ options (bao gồm cả archived journals)
        journal_ids = []
        if options.get('journals'):
            journal_ids = [
                journal['id'] 
                for journal in options['journals'] 
                if journal.get('selected', True)
            ]
        
        # Nếu không có journal nào được chọn, lấy tất cả journals của company (bao gồm archived)
        if not journal_ids:
            journal_ids = self.env['account.journal'].with_context(active_test=False).search([
                ('company_id', '=', self.env.company.id)
            ]).ids
        
        # Tạo wizard với các giá trị và chuẩn bị data
        # Dùng with_context(active_test=False) để có thể gán archived journals
        wizard = self.env['account.journal.items.report.wizard'].with_context(active_test=False).create({
            'date_from': date_from,
            'date_to': date_to,
            'account_ids': [(6, 0, [account.id])],
            'all_accounts': False,
            'journal_ids': [(6, 0, journal_ids)],
            'state_filter': state_filter,
            'skip_no_transaction': False,
            'company_id': self.env.company.id,
        })
        
        # Chuẩn bị report data và lưu vào wizard
        report_data = wizard._prepare_report_data()
        
        # Tính running balance
        for account_data in report_data.get('accounts', []):
            running_balance = account_data['opening_balance']
            for item in account_data['items']:
                running_balance += item['debit'] - item['credit']
                item['running_balance'] = running_balance
        
        wizard.write({'report_data_json': json.dumps(report_data)})
        
        # Mở URL trực tiếp trong tab mới
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/html/account_journal_items_report.report_journal_items_html/{wizard.id}',
            'target': 'new',
        }
		
    def action_open_s03b_all_accounts(self, options, params):
        """Mở báo cáo S03b với tất cả tài khoản - từ caret của Total line"""
        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        journal_ids = self._get_journal_ids_from_options(options)
        state_filter = self._get_state_filter_from_options(options)
        
        wizard = self.env['account.journal.items.report.wizard'].with_context(active_test=False).create({
            'date_from': date_from,
            'date_to': date_to,
            'all_accounts': True,
            'journal_ids': [(6, 0, journal_ids)],
            'state_filter': state_filter,
            'skip_no_transaction': True,
            'company_id': self.env.company.id,
        })
        
        report_data = wizard._prepare_report_data()
        wizard.write({'report_data_json': json.dumps(report_data)})
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/html/account_journal_items_report.report_journal_items_html/{wizard.id}',
            'target': 'new',
        }
