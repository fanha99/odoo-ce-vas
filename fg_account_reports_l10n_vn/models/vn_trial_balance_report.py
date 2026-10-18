# -*- coding: utf-8 -*-
from odoo import api, models, _, fields
import logging

_logger = logging.getLogger(__name__)

class VNTrialBalanceCustomHandler(models.AbstractModel):
    _name = 'vn.account.trial.balance.report.handler'
    _inherit = 'account.trial.balance.report.handler'
    _description = 'Vietnam Trial Balance Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if not previous_options:
            options['unfold_all'] = True

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals)
        if not lines:
            return lines

        total_line = lines[-1]

        #xử lý tài khoản 133,  331
        for account_code in ['131', '331']:
            for line in lines:
                if account_code == line[1]['name'][:3]:
                    for idx, col in enumerate(line[1]['columns']):
                        column_group_key = col.get('column_group_key', '')
                        if column_group_key:
                            if "filter" not in column_group_key :
                                import ast
                                # Convert string to tuple/dict
                                try:
                                    # Guard against excessively large inputs (DoS)
                                    if len(column_group_key) > 2048:
                                        _logger.warning("column_group_key too large, skipping")
                                        continue
                                    key_parts = ast.literal_eval(column_group_key)
                                    # Validate structure before deep indexing
                                    if (not isinstance(key_parts, (list, tuple)) or
                                            len(key_parts) < 1 or
                                            not isinstance(key_parts[0], (list, tuple)) or len(key_parts[0]) < 2 or
                                            not isinstance(key_parts[0][1], (list, tuple)) or len(key_parts[0][1]) < 1 or
                                            not isinstance(key_parts[0][1][0], (list, tuple)) or len(key_parts[0][1][0]) < 2 or
                                            not isinstance(key_parts[0][1][0][1], (list, tuple)) or len(key_parts[0][1][0][1]) < 2 or
                                            not isinstance(key_parts[0][1][0][1][1], (list, tuple)) or len(key_parts[0][1][0][1][1]) < 2):
                                        _logger.warning("column_group_key has unexpected structure, skipping")
                                        continue
                                    date_to = key_parts[0][1][0][1][1][1]
                                    _logger.info(f"Found dates, to: {date_to}")
                                except Exception as e:
                                    _logger.error(f"Error parsing column_group_key: {str(e)}")
                                    continue
                                value = float(col.get('no_format', 0.0))
                                new_value = self.env['account.report']._get_account_balance(account_code, date_to, options, col['expression_label'])['result']
                                if new_value is None:
                                    new_value = 0.0
                                else:
                                    new_value = float(new_value)
                                #_logger.info(f"{account_code}Found dates, to: {date_to}, value: {value}, new_value: {new_value}, {col['expression_label']}")
                                diff = new_value - value
                                if diff != 0:
                                    col['no_format'] += diff
                                    # Update formatted value
                                    formatted_value = self.env['account.report']._format_value(
                                            options, col['no_format'], figure_type='monetary')
                                    col['name'] = formatted_value
                                    col['is_zero'] = self.env.company.currency_id.is_zero(col['no_format'])

                                    total_line[1]['columns'][idx]['no_format'] += diff
                                    formatted_value = self.env['account.report']._format_value(
                                            options, total_line[1]['columns'][idx]['no_format'], figure_type='monetary')
                                    total_line[1]['columns'][idx]['name'] = formatted_value
                                    total_line[1]['columns'][idx]['is_zero'] = self.env.company.currency_id.is_zero(col['no_format'])

        # Loại tài khoản code "10" khi và chỉ khi debit == credit
        currency = self.env.company.currency_id
        excluded_totals = {}
        filtered_lines = []
        for line in lines[:-1]:
            code = line[1].get('name', '').split()[0]
            if code == '10':
                cols = line[1].get('columns', [])
                total_debit  = sum(float(c.get('no_format') or 0.0) for c in cols if c.get('expression_label') == 'debit')
                total_credit = sum(float(c.get('no_format') or 0.0) for c in cols if c.get('expression_label') == 'credit')
                if currency.is_zero(total_debit - total_credit):
                    for idx, col in enumerate(cols):
                        excluded_totals[idx] = excluded_totals.get(idx, 0.0) + float(col.get('no_format') or 0.0)
                    continue
            filtered_lines.append(line)

        for idx, col in enumerate(total_line[1].get('columns', [])):
            subtract = excluded_totals.get(idx, 0.0)
            if subtract:
                col['no_format'] = float(col.get('no_format') or 0.0) - subtract
                col['name'] = self.env['account.report']._format_value(
                    options, col['no_format'], figure_type='monetary')
                col['is_zero'] = self.env.company.currency_id.is_zero(col['no_format'])

        filtered_lines.append(total_line)
        return filtered_lines
