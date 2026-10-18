# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal


class StockReportCustomHandler(models.AbstractModel):
    _name = 'stock.report.custom.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Stock Valuation Layer Report Custom Handler'


    # =========================================================================
    # COLUMN GROUPS CONFIGURATION (giống Trial Balance)
    # Cấu trúc: Đầu kỳ (xa nhất) | Tăng/Giảm các kỳ | Cuối kỳ (gần nhất)
    # =========================================================================

    def _custom_options_initializer(self, report, options, previous_options=None):
        """
        Cấu trúc báo cáo khi có so sánh kỳ:
        - Không có comparison: Đầu kỳ | Tăng trong kỳ | Giảm trong kỳ | Cuối kỳ
        - Có 1 kỳ comparison: Đầu kỳ trước | Tăng kỳ trước | Giảm kỳ trước | Tăng kỳ này | Giảm kỳ này | Cuối kỳ
        
        Tương tự Trial Balance: Initial Balance (từ kỳ xa nhất) -> các kỳ ở giữa -> End Balance (kỳ gần nhất)
        """
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}
        left_side = {'column_headers': [], 'column_groups': {}, 'columns': []}
        right_side = {'column_headers': [], 'column_groups': {}, 'columns': []}
        uom_header = [{'name': '', 'colspan': 1}]  # Header riêng cho UOM với colspan=1
        uom_columns = [
            {
                'name': _('ĐVT'),
                'column_group_key': 'uom_column_group',
                'expression_label': 'uom',
                'sortable': False,
                'figure_type': 'string',
                'blank_if_zero': False,
            }
        ]

        # Xử lý comparison periods (nếu có) - đảo ngược thứ tự
        if options.get('comparison', {}).get('periods'):
            new_columns_order = []
            current_column = []
            current_column_group_key = options['columns'][-1]['column_group_key']

            for column in reversed(options['columns']):
                if current_column_group_key != column['column_group_key']:
                    current_column_group_key = column['column_group_key']
                    new_columns_order += current_column
                    current_column = []
                current_column.insert(0, column)
            new_columns_order += current_column

            options['columns'] = new_columns_order
            options['column_headers'][0][:] = reversed(options['column_headers'][0])

        # Tạo column group Đầu kỳ (bên trái - từ kỳ xa nhất)
        self._create_column_group_opening(report, options, previous_options, default_group_vals, left_side)
        
        # Tạo column group Cuối kỳ (bên phải - từ kỳ gần nhất)
        self._create_column_group_closing(report, options, previous_options, default_group_vals, right_side)

        # Cập nhật options
        # Thêm UOM header vào đầu, sau đó là left_side (đầu kỳ), rồi trong kỳ, cuối cùng là right_side (cuối kỳ)
        options['column_headers'][0] = uom_header + left_side['column_headers'] + options['column_headers'][0] + right_side['column_headers']
        options['column_groups'].update(left_side['column_groups'])
        options['column_groups'].update(right_side['column_groups'])
        options['columns'] = uom_columns + left_side['columns'] + options['columns'] + right_side['columns']
        options['ignore_totals_below_sections'] = True

        report._init_options_order_column(options, previous_options)

    def _create_column_group_opening(self, report, options, previous_options, default_group_vals, side_to_append):
        """
        Tạo column group cho Số dư đầu kỳ.
        Lấy từ kỳ xa nhất (nếu có comparison) hoặc kỳ hiện tại (nếu không có comparison).
        """
        comparison_periods = options.get('comparison', {}).get('periods', [])
        
        if comparison_periods:
            # Có comparison - lấy date_from từ kỳ xa nhất
            earliest_period = comparison_periods[-1]  # Kỳ xa nhất ở cuối list
            opening_date_from = earliest_period.get('date_from')
        else:
            # Không có comparison - lấy date_from từ kỳ hiện tại
            opening_date_from = options['date']['date_from']
        
        # Số dư đầu kỳ = tất cả trước ngày bắt đầu
        date_from_obj = fields.Date.from_string(opening_date_from)
        opening_date = (date_from_obj - timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        opening_forced_options = {
            'date': {
                'mode': 'single',
                'date_to': opening_date,
                'date_from': False,
            },
            'is_opening_balance': True,
        }

        header_element = [{'name': _("Đầu kỳ"), 'forced_options': opening_forced_options, 'colspan': 2}]
        column_headers = [header_element, *options['column_headers'][1:]]
        column_group_vals = report._generate_columns_group_vals_recursively(column_headers, default_group_vals)

        # Chỉ lấy 2 cột: opening_qty và opening_value
        columns, column_groups = self._build_opening_closing_columns(report, opening_forced_options, column_group_vals, 'opening')

        side_to_append['column_headers'] += header_element
        side_to_append['column_groups'] |= column_groups
        side_to_append['columns'] += columns

    def _create_column_group_closing(self, report, options, previous_options, default_group_vals, side_to_append):
        """
        Tạo column group cho Số dư cuối kỳ.
        Lấy từ kỳ gần nhất (kỳ hiện tại).
        """
        # Cuối kỳ luôn là cuối kỳ hiện tại
        end_date_to = options['date']['date_to']
        
        # date_from cho cuối kỳ - từ đầu kỳ xa nhất đến cuối kỳ hiện tại
        comparison_periods = options.get('comparison', {}).get('periods', [])
        if comparison_periods:
            end_date_from = comparison_periods[-1].get('date_from')
        else:
            end_date_from = options['date']['date_from']
        
        closing_forced_options = {
            'date': {
                'mode': 'range',
                'date_to': fields.Date.from_string(end_date_to).strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_from': fields.Date.from_string(end_date_from).strftime(DEFAULT_SERVER_DATE_FORMAT),
            },
            'is_closing_balance': True,
        }

        header_element = [{'name': _("Cuối kỳ"), 'forced_options': closing_forced_options, 'colspan': 2}]
        column_headers = [header_element, *options['column_headers'][1:]]
        column_group_vals = report._generate_columns_group_vals_recursively(column_headers, default_group_vals)

        # Chỉ lấy 2 cột: closing_qty và closing_value
        columns, column_groups = self._build_opening_closing_columns(report, closing_forced_options, column_group_vals, 'closing')

        side_to_append['column_headers'] += header_element
        side_to_append['column_groups'] |= column_groups
        side_to_append['columns'] += columns

    def _build_opening_closing_columns(self, report, forced_options, column_group_vals, balance_type):
        """
        Build columns cho Opening hoặc Closing balance.
        Chỉ tạo 2 cột: qty và value.
        """
        columns = []
        column_groups = {}
        
        for column_group_val in column_group_vals:
            column_group_key = str(report._get_dict_hashable_key_tuple(column_group_val))
            
            column_groups[column_group_key] = {
                'forced_options': column_group_val.get('forced_options', {}),
                'forced_domain': [],
            }
            
            # Chỉ tạo 2 cột cho opening/closing
            columns.append({
                'name': _('Số lượng'),
                'column_group_key': column_group_key,
                'expression_label': f'{balance_type}_qty',
                'sortable': True,
                'figure_type': 'float',
                'blank_if_zero': False,
            })
            columns.append({
                'name': _('Giá trị'),
                'column_group_key': column_group_key,
                'expression_label': f'{balance_type}_value',
                'sortable': True,
                'figure_type': 'monetary',
                'blank_if_zero': False,
            })
        
        return columns, column_groups

    # =========================================================================
    # DYNAMIC LINES GENERATOR
    # =========================================================================

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """Generate dynamic lines for stock valuation report with support for comparison periods"""
        
        # Xóa warning về unposted journal entries vì báo cáo này dựa trên stock valuation layer
        if warnings is not None and 'account_reports.common_warning_draft_in_period' in warnings:
            del warnings['account_reports.common_warning_draft_in_period']
        
        # Phân tích column groups để xác định các periods
        column_groups_info = self._analyze_column_groups(options)
        
        if not column_groups_info:
            return []
        
        # Lấy tất cả product_ids liên quan
        all_product_ids = self._get_all_relevant_product_ids(column_groups_info)
        
        if not all_product_ids:
            return []
        
        # Lấy thông tin products
        products_info = self._get_products_info(all_product_ids)
        
        # Lấy dữ liệu cho từng column group
        products_data = self._fetch_data_for_all_column_groups(column_groups_info, all_product_ids, products_info)
        
        # Generate report lines
        return self._generate_lines_from_data(report, options, products_data, column_groups_info)

    def _analyze_column_groups(self, options):
        """
        Phân tích column_groups để xác định loại và date range của từng group.
        Returns: dict với column_group_key là key
        """
        column_groups_info = {}
        column_groups = options.get('column_groups', {})
        
        for group_key, group_data in column_groups.items():
            forced_options = group_data.get('forced_options', {})
            date_info = forced_options.get('date', {})
            
            info = {
                'key': group_key,
                'date_from': date_info.get('date_from'),
                'date_to': date_info.get('date_to'),
                'is_opening': forced_options.get('is_opening_balance', False),
                'is_closing': forced_options.get('is_closing_balance', False),
            }
            
            # Xác định loại
            if info['is_opening']:
                info['type'] = 'opening'
            elif info['is_closing']:
                info['type'] = 'closing'
            else:
                info['type'] = 'movement'
            
            column_groups_info[group_key] = info
        
        return column_groups_info

    def _get_all_relevant_product_ids(self, column_groups_info):
        """Lấy tất cả product_ids có dữ liệu trong bất kỳ period nào"""
        all_product_ids = set()
        
        for group_key, info in column_groups_info.items():
            if info['type'] == 'opening':
                # Products có balance trước date_to
                if info['date_to']:
                    product_ids = self._get_products_with_balance_before(info['date_to'])
                    all_product_ids.update(product_ids)
            elif info['type'] == 'movement':
                # Products có movements trong khoảng date
                if info['date_from'] and info['date_to']:
                    product_ids = self._get_products_with_movements(info['date_from'], info['date_to'])
                    all_product_ids.update(product_ids)
            elif info['type'] == 'closing':
                # Products có balance đến date_to
                if info['date_to']:
                    product_ids = self._get_products_with_balance_before(info['date_to'])
                    all_product_ids.update(product_ids)
        
        return list(all_product_ids)

    def _get_products_info(self, product_ids):
        """Lấy thông tin cơ bản của products"""
        if not product_ids:
            return {}
        
        products = self.env['product.product'].with_context(active_test=False).browse(product_ids)
        return {
            p.id: {
                'name': p.name,
                'uom': p.uom_id,
            }
            for p in products
        }

    def _fetch_data_for_all_column_groups(self, column_groups_info, all_product_ids, products_info):
        """
        Lấy dữ liệu cho tất cả column groups.
        Returns: dict với product_id là key, chứa data cho từng column group
        """
        # Khởi tạo data structure
        products_data = {}
        for product_id in all_product_ids:
            products_data[product_id] = {
                'product_id': product_id,
                'name': products_info.get(product_id, {}).get('name', 'Unknown'),
                'uom': products_info.get(product_id, {}).get('uom'),
                'column_data': {},  # key = column_group_key
            }
        
        # Lấy data cho từng column group
        for group_key, info in column_groups_info.items():
            if info['type'] == 'opening':
                # Lấy balance tại date_to
                balances = self._get_balances_at_date(info['date_to'], all_product_ids)
                for product_id in all_product_ids:
                    balance = balances.get(product_id, {'qty': 0.0, 'value': 0.0})
                    products_data[product_id]['column_data'][group_key] = {
                        'type': 'opening',
                        'qty': balance['qty'],
                        'value': balance['value'],
                    }
                    
            elif info['type'] == 'movement':
                # Lấy movements trong khoảng date
                movements = self._get_period_movements(info['date_from'], info['date_to'])
                for product_id in all_product_ids:
                    movement = movements.get(product_id, {
                        'increase_qty': 0.0, 'increase_value': 0.0,
                        'decrease_qty': 0.0, 'decrease_value': 0.0,
                    })
                    products_data[product_id]['column_data'][group_key] = {
                        'type': 'movement',
                        **movement,
                    }
                    
            elif info['type'] == 'closing':
                # Lấy balance tại date_to
                balances = self._get_balances_at_date(info['date_to'], all_product_ids)
                for product_id in all_product_ids:
                    balance = balances.get(product_id, {'qty': 0.0, 'value': 0.0})
                    products_data[product_id]['column_data'][group_key] = {
                        'type': 'closing',
                        'qty': balance['qty'],
                        'value': balance['value'],
                    }
        
        # Lọc bỏ products không có dữ liệu
        filtered_data = {}
        for product_id, data in products_data.items():
            has_data = False
            for group_key, col_data in data['column_data'].items():
                if col_data['type'] in ['opening', 'closing']:
                    if col_data.get('qty', 0) != 0 or col_data.get('value', 0) != 0:
                        has_data = True
                        break
                elif col_data['type'] == 'movement':
                    if any([
                        col_data.get('increase_qty', 0),
                        col_data.get('decrease_qty', 0),
                        col_data.get('increase_value', 0),
                        col_data.get('decrease_value', 0),
                    ]):
                        has_data = True
                        break
            
            if has_data:
                filtered_data[product_id] = data
        
        return filtered_data

    def _get_products_with_movements(self, date_from, date_to):
        """Lấy danh sách product_ids có movements trong khoảng thời gian"""
        query = """
            SELECT DISTINCT svl.product_id
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE sm.date >= %s AND sm.date <= %s
        """
        date_to_end = f"{date_to} 23:59:59"
        self.env.cr.execute(query, (date_from, date_to_end))
        return [row[0] for row in self.env.cr.fetchall()]

    def _get_products_with_balance_before(self, date_to):
        """Lấy danh sách product_ids có balance đến ngày cho trước"""
        query = """
            SELECT DISTINCT svl.product_id
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE sm.date <= %s
        """
        date_to_end = f"{date_to} 23:59:59"
        self.env.cr.execute(query, (date_to_end,))
        return [row[0] for row in self.env.cr.fetchall()]

    def _get_balances_at_date(self, date_to, product_ids):
        """Lấy số dư tại một ngày cụ thể cho các products"""
        if not product_ids or not date_to:
            return {}
        
        query = """
            SELECT 
                svl.product_id,
                SUM(svl.quantity) AS qty,
                SUM(svl.value) AS value
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE svl.product_id = ANY(%s)
              AND sm.date <= %s
            GROUP BY svl.product_id
        """
        date_to_end = f"{date_to} 23:59:59"
        self.env.cr.execute(query, (product_ids, date_to_end))
        
        return {
            row['product_id']: {
                'qty': row['qty'] or 0.0,
                'value': row['value'] or 0.0,
            }
            for row in self.env.cr.dictfetchall()
        }

    def _get_period_movements(self, date_from, date_to):
        """Fetch period movements with optimized query"""
        if not date_from or not date_to:
            return {}
            
        query = """
            SELECT
                svl.product_id,
                SUM(CASE WHEN svl.quantity < 0 THEN -svl.quantity ELSE 0 END) AS decrease_qty,
                SUM(CASE WHEN svl.quantity >= 0 THEN svl.quantity ELSE 0 END) AS increase_qty,
                SUM(CASE WHEN svl.value < 0 THEN -svl.value ELSE 0 END) AS decrease_value,
                SUM(CASE WHEN svl.value >= 0 THEN svl.value ELSE 0 END) AS increase_value
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE sm.date >= %s AND sm.date <= %s
            GROUP BY svl.product_id
        """
        
        date_to_end = f"{date_to} 23:59:59"
        self.env.cr.execute(query, (date_from, date_to_end))
        
        return {
            row['product_id']: {
                'increase_qty': row['increase_qty'] or 0.0,
                'increase_value': row['increase_value'] or 0.0,
                'decrease_qty': row['decrease_qty'] or 0.0,
                'decrease_value': row['decrease_value'] or 0.0,
            }
            for row in self.env.cr.dictfetchall()
        }

    def _generate_lines_from_data(self, report, options, products_data, column_groups_info):
        """Generate formatted report lines"""
        lines = []
        currency = self.env.company.currency_id
        totals = defaultdict(float)
        
        # Sort products by name
        sorted_products = sorted(products_data.values(), key=lambda x: x['name'])
        
        for product_data in sorted_products:
            line = self._format_product_line(report, options, product_data, currency, column_groups_info)
            lines.append((0, line))
            
            # Accumulate totals
            self._accumulate_line_totals(totals, product_data, options)
        
        # Add total line
        total_line = self._format_totals_line(report, options, totals, currency)
        lines.append((0, total_line))
        
        return lines

    def _format_product_line(self, report, options, product_data, currency, column_groups_info):
        """Format a single product line"""
        product_id = product_data['product_id']
        uom = product_data.get('uom')
        uom_name = uom.name if uom else ''

        line_id = f"~account.report~{report.id}|~product.product~{product_id}"

        line = {
            'name': product_data['name'],
            'id': line_id,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
            'columns': [],
            'caret_options': 'stock_valuation' if product_id else None,
        }
        
        # Build columns based on options['columns']
        for col in options.get('columns', []):
            expr_label = col.get('expression_label', '')
            column_group_key = col.get('column_group_key', '')
            
            # UOM column
            if expr_label == 'uom':
                line['columns'].append({
                    'name': uom_name,
                    'no_format': uom_name,
                    'is_zero': False,
                    'expression_label': 'uom',
                    'class': 'text-center',
                })
                continue
            
            # Get value from product data based on column_group_key
            col_data = product_data.get('column_data', {}).get(column_group_key, {})
            value = self._get_value_from_col_data(col_data, expr_label)
            
            # Format value
            is_qty = 'qty' in expr_label.lower()
            figure_type = 'float' if is_qty else 'monetary'
            
            if is_qty:
                formatted_value = self.env['account.report']._format_value(
                    options, value, figure_type=figure_type,
                    blank_if_zero=False, 
                    digits=2
                )
            else:
                formatted_value = self.env['account.report']._format_value(
                    options, value, figure_type=figure_type, blank_if_zero=False
                )

            line['columns'].append({
                'name': formatted_value,
                'no_format': value,
                'is_zero': currency.is_zero(value) if not is_qty else value == 0,
                'expression_label': expr_label,
                'class': 'numeric text-end',
            })
        
        return line

    def _get_value_from_col_data(self, col_data, expr_label):
        """Extract value from column data based on expression label"""
        col_type = col_data.get('type', '')
        
        if col_type == 'opening':
            if expr_label == 'opening_qty':
                return col_data.get('qty', 0.0)
            elif expr_label == 'opening_value':
                return col_data.get('value', 0.0)
        elif col_type == 'closing':
            if expr_label == 'closing_qty':
                return col_data.get('qty', 0.0)
            elif expr_label == 'closing_value':
                return col_data.get('value', 0.0)
        elif col_type == 'movement':
            if expr_label == 'increase_qty':
                return col_data.get('increase_qty', 0.0)
            elif expr_label == 'increase_value':
                return col_data.get('increase_value', 0.0)
            elif expr_label == 'decrease_qty':
                return col_data.get('decrease_qty', 0.0)
            elif expr_label == 'decrease_value':
                return col_data.get('decrease_value', 0.0)
        
        return 0.0

    def _accumulate_line_totals(self, totals, product_data, options):
        """Accumulate totals for a product line"""
        for col in options.get('columns', []):
            expr_label = col.get('expression_label', '')
            column_group_key = col.get('column_group_key', '')
            
            if expr_label in ['uom']:
                continue
            
            # Only accumulate value columns (not qty)
            if 'value' not in expr_label.lower():
                continue
            
            col_data = product_data.get('column_data', {}).get(column_group_key, {})
            value = self._get_value_from_col_data(col_data, expr_label)
            
            # Use column_group_key + expr_label as unique key for totals
            total_key = f"{column_group_key}_{expr_label}"
            totals[total_key] += value

    def _format_totals_line(self, report, options, totals, currency):
        """Format the totals line"""
        line = {
            'name': 'Total',
            'id': f"~account.report~{report.id}|total~~",
            'level': 0,
            'unfoldable': False,
            'unfolded': False,
            'columns': [],
            'caret_options': None,
        }
        
        for col in options.get('columns', []):
            expr_label = col.get('expression_label', '')
            column_group_key = col.get('column_group_key', '')
            
            # Only show totals for value columns
            if 'value' in expr_label.lower():
                total_key = f"{column_group_key}_{expr_label}"
                value = totals.get(total_key, 0.0)
                formatted_value = self.env['account.report']._format_value(
                    options, value, figure_type='monetary', blank_if_zero=False
                )
                line['columns'].append({
                    'name': formatted_value,
                    'no_format': value,
                    'is_zero': currency.is_zero(value),
                    'expression_label': expr_label,
                    'class': 'numeric text-end',
                })
            else:
                line['columns'].append({
                    'name': '',
                    'no_format': '',
                    'is_zero': True,
                    'expression_label': expr_label,
                    'class': 'numeric text-end',
                })

        return line

    def _caret_options_initializer(self):
        """Initialize caret options for stock valuation report"""
        return {
            'stock_valuation': [
                {'name': _("Stock Valuation Layers"), 'action': 'open_stock_valuation_layers'},
                {'name': _("Stock Moves"), 'action': 'open_stock_moves'},
            ],
        }

    def _parse_product_id(self, line_id):
        """Safely parse product ID from line_id"""
        try:
            product_id_str = line_id.rsplit("~", 1)[-1]
            return int(product_id_str)
        except (ValueError, IndexError):
            return None

    def _get_date_domain(self, date_from, date_to, date_field='stock_move_id.date'):
        """Build date domain safely"""
        domain = []
        if not date_from or not date_to:
            return domain
        
        try:
            date_from_obj = fields.Date.from_string(date_from)
            date_to_obj = fields.Date.from_string(date_to)
            
            if date_field == 'stock_move_id.date':
                domain.append((date_field, '>=', datetime.combine(date_from_obj, datetime.min.time())))
                domain.append((date_field, '<=', datetime.combine(date_to_obj, datetime.max.time())))
            else:
                domain.append((date_field, '>=', date_from_obj))
                domain.append((date_field, '<=', date_to_obj))
        except (ValueError, TypeError):
            pass
        
        return domain

    def open_stock_valuation_layers(self, options, params):
        """Open stock valuation layers filtered by product and date range - opens in new browser tab"""
        product_id = self._parse_product_id(params.get('line_id', ''))

        # Build domain first
        domain = []
        if product_id:
            domain.append(('product_id', '=', product_id))

        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        domain.extend(self._get_date_domain(date_from, date_to, 'stock_move_id.date'))

        # Convert domain to JSON-serializable format
        def serialize_domain(domain):
            serialized = []
            for item in domain:
                if isinstance(item, (list, tuple)):
                    field, op, value = item
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    serialized.append([field, op, value])
                else:
                    serialized.append(item)
            return serialized

        domain_serialized = serialize_domain(domain)
        
        # Create a temporary action with the domain
        action = self.env['ir.actions.act_window'].sudo().create({
            'name': _('Stock Valuation Layers'),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form,pivot,graph',
            'domain': str(domain_serialized),
            'target': 'current',
        })
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/web#action={action.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def open_stock_moves(self, options, params):
        """Open stock moves filtered by product and date range - opens in new browser tab"""
        product_id = self._parse_product_id(params.get('line_id', ''))

        # Build domain
        domain = [('state', '=', 'done')]
        if product_id:
            domain.append(('product_id', '=', product_id))

        date_from = options.get('date', {}).get('date_from')
        date_to = options.get('date', {}).get('date_to')
        domain.extend(self._get_date_domain(date_from, date_to, 'date'))

        # Convert domain to JSON-serializable format
        def serialize_domain(domain):
            serialized = []
            for item in domain:
                if isinstance(item, (list, tuple)):
                    field, op, value = item
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    serialized.append([field, op, value])
                else:
                    serialized.append(item)
            return serialized

        domain_serialized = serialize_domain(domain)
        
        # Create a temporary action with the domain
        action = self.env['ir.actions.act_window'].sudo().create({
            'name': _('Stock Moves'),
            'res_model': 'stock.move',
            'view_mode': 'list,form,pivot,graph,kanban',
            'domain': str(domain_serialized),
            'target': 'current',
            'context': {'search_default_done': 1},
        })
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/web#action={action.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_audit_cell(self, options, params):
        """Override to prevent journal entry audit - not applicable for stock report"""
        return False

    def _get_custom_display_config(self):
        """Override to add custom CSS class and custom PDF export template"""
        return {
            'css_custom_class': 'o_stock_valuation_report',
            'pdf_export': {
                'pdf_export_main_table_header': 'fg_stock_reports_l10n_vn.stock_pdf_export_main_table_header',
            },
        }

