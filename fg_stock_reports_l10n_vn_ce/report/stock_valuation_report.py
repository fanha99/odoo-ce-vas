# -*- coding: utf-8 -*-
# Copyright 2024 Fanha Giang
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta, date as date_type
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockValuationReport(models.AbstractModel):
    """Stock Valuation Report - Báo cáo Xuất Nhập Tồn."""

    _name = "report.fg_stock_reports_l10n_vn_ce.report_stock_valuation"
    _description = "Stock Valuation Report"

    # =========================================================================
    # HELPER METHODS - Lấy dữ liệu từ stock.valuation.layer
    # =========================================================================

    def _convert_to_date(self, date_value):
        """Convert string or date to date object."""
        if isinstance(date_value, str):
            return fields.Date.from_string(date_value)
        elif isinstance(date_value, datetime):
            return date_value.date()
        return date_value

    def _get_opening_balance(self, product_ids, date_from, company_id, warehouse_ids=None):
        """
        Lấy số dư đầu kỳ (trước date_from).
        Returns: dict {product_id: {'qty': x, 'value': y}}
        """
        if not product_ids:
            return {}

        # Convert to date if string
        date_from = self._convert_to_date(date_from)
        
        # Ngày trước date_from
        date_before = datetime.combine(date_from, datetime.min.time())
        
        query = """
            SELECT 
                svl.product_id,
                SUM(svl.quantity) AS qty,
                SUM(svl.value) AS value
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE svl.product_id = ANY(%s)
              AND svl.company_id = %s
              AND sm.date < %s
              AND sm.state = 'done'
            GROUP BY svl.product_id
        """
        params = [list(product_ids), company_id, date_before]
        
        self.env.cr.execute(query, params)
        
        result = {}
        for row in self.env.cr.dictfetchall():
            result[row['product_id']] = {
                'qty': row['qty'] or 0.0,
                'value': row['value'] or 0.0,
            }
        return result

    def _get_period_movements(self, product_ids, date_from, date_to, company_id, warehouse_ids=None):
        """
        Lấy biến động trong kỳ (từ date_from đến date_to).
        Returns: dict {product_id: {
            'increase_qty': x, 'increase_value': y,
            'decrease_qty': z, 'decrease_value': w
        }}
        """
        if not product_ids:
            return {}

        # Convert to date if string
        date_from = self._convert_to_date(date_from)
        date_to = self._convert_to_date(date_to)

        date_from_dt = datetime.combine(date_from, datetime.min.time())
        date_to_dt = datetime.combine(date_to, datetime.max.time())
        
        query = """
            SELECT
                svl.product_id,
                SUM(CASE WHEN svl.quantity >= 0 THEN svl.quantity ELSE 0 END) AS increase_qty,
                SUM(CASE WHEN svl.value >= 0 THEN svl.value ELSE 0 END) AS increase_value,
                SUM(CASE WHEN svl.quantity < 0 THEN -svl.quantity ELSE 0 END) AS decrease_qty,
                SUM(CASE WHEN svl.value < 0 THEN -svl.value ELSE 0 END) AS decrease_value
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE svl.product_id = ANY(%s)
              AND svl.company_id = %s
              AND sm.date >= %s AND sm.date <= %s
              AND sm.state = 'done'
            GROUP BY svl.product_id
        """
        params = [list(product_ids), company_id, date_from_dt, date_to_dt]
        
        self.env.cr.execute(query, params)
        
        result = {}
        for row in self.env.cr.dictfetchall():
            result[row['product_id']] = {
                'increase_qty': row['increase_qty'] or 0.0,
                'increase_value': row['increase_value'] or 0.0,
                'decrease_qty': row['decrease_qty'] or 0.0,
                'decrease_value': row['decrease_value'] or 0.0,
            }
        return result

    def _get_all_product_ids_with_data(self, date_from, date_to, company_id, 
                                        product_ids=None, product_categ_ids=None,
                                        warehouse_ids=None):
        """
        Lấy tất cả product_id có dữ liệu trong kỳ hoặc có số dư đầu kỳ.
        """
        # Convert to date if string
        date_to = self._convert_to_date(date_to)
        date_to_dt = datetime.combine(date_to, datetime.max.time())
        
        # Base query
        query = """
            SELECT DISTINCT svl.product_id
            FROM stock_valuation_layer svl
            INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
            INNER JOIN product_product pp ON pp.id = svl.product_id
            INNER JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE svl.company_id = %s
              AND sm.date <= %s
              AND sm.state = 'done'
        """
        params = [company_id, date_to_dt]
        
        # Filter by products
        if product_ids:
            query += " AND svl.product_id = ANY(%s)"
            params.append(list(product_ids))
        
        # Filter by categories
        if product_categ_ids:
            # Get all child categories
            all_categ_ids = list(product_categ_ids)
            for categ_id in product_categ_ids:
                child_categs = self.env['product.category'].search([
                    ('id', 'child_of', categ_id)
                ])
                all_categ_ids.extend(child_categs.ids)
            all_categ_ids = list(set(all_categ_ids))
            query += " AND pt.categ_id = ANY(%s)"
            params.append(all_categ_ids)
        
        self.env.cr.execute(query, params)
        return [row[0] for row in self.env.cr.fetchall()]

    def _get_products_info(self, product_ids):
        """Lấy thông tin sản phẩm."""
        if not product_ids:
            return {}
        
        products = self.env['product.product'].with_context(active_test=False).browse(product_ids)
        return {
            p.id: {
                'id': p.id,
                'default_code': p.default_code or '',
                'name': p.name,
                'uom_name': p.uom_id.name if p.uom_id else '',
                'uom_rounding': p.uom_id.rounding if p.uom_id else 0.01,
                'categ_id': p.categ_id.id,
                'categ_name': p.categ_id.complete_name if p.categ_id else '',
            }
            for p in products
        }

    def _is_zero_line(self, line_data, currency_rounding):
        """Check if a line has all zero values."""
        return (
            float_is_zero(line_data.get('opening_qty', 0), precision_rounding=0.01)
            and float_is_zero(line_data.get('opening_value', 0), precision_rounding=currency_rounding)
            and float_is_zero(line_data.get('increase_qty', 0), precision_rounding=0.01)
            and float_is_zero(line_data.get('increase_value', 0), precision_rounding=currency_rounding)
            and float_is_zero(line_data.get('decrease_qty', 0), precision_rounding=0.01)
            and float_is_zero(line_data.get('decrease_value', 0), precision_rounding=currency_rounding)
            and float_is_zero(line_data.get('closing_qty', 0), precision_rounding=0.01)
            and float_is_zero(line_data.get('closing_value', 0), precision_rounding=currency_rounding)
        )

    # =========================================================================
    # MAIN DATA COMPUTATION
    # =========================================================================

    @api.model
    def _get_report_data(
        self,
        date_from,
        date_to,
        company_id,
        product_ids=None,
        product_categ_ids=None,
        warehouse_ids=None,
        hide_zero_lines=True,
        group_by_category=False,
    ):
        """
        Main method to compute report data.
        Returns: list of product data dicts
        """
        company = self.env['res.company'].browse(company_id)
        currency_rounding = company.currency_id.rounding

        # Get all relevant product IDs
        all_product_ids = self._get_all_product_ids_with_data(
            date_from, date_to, company_id,
            product_ids=product_ids,
            product_categ_ids=product_categ_ids,
            warehouse_ids=warehouse_ids,
        )
        
        if not all_product_ids:
            return [], {}

        # Get product info
        products_info = self._get_products_info(all_product_ids)
        
        # Get opening balances
        opening_data = self._get_opening_balance(
            all_product_ids, date_from, company_id, warehouse_ids
        )
        
        # Get period movements
        movement_data = self._get_period_movements(
            all_product_ids, date_from, date_to, company_id, warehouse_ids
        )

        # Build report lines
        report_lines = []
        totals = {
            'opening_qty': 0.0,
            'opening_value': 0.0,
            'increase_qty': 0.0,
            'increase_value': 0.0,
            'decrease_qty': 0.0,
            'decrease_value': 0.0,
            'closing_qty': 0.0,
            'closing_value': 0.0,
        }

        for product_id in all_product_ids:
            product_info = products_info.get(product_id, {})
            opening = opening_data.get(product_id, {'qty': 0.0, 'value': 0.0})
            movement = movement_data.get(product_id, {
                'increase_qty': 0.0, 'increase_value': 0.0,
                'decrease_qty': 0.0, 'decrease_value': 0.0,
            })

            # Calculate closing balance
            closing_qty = opening['qty'] + movement['increase_qty'] - movement['decrease_qty']
            closing_value = opening['value'] + movement['increase_value'] - movement['decrease_value']

            line_data = {
                'product_id': product_id,
                'default_code': product_info.get('default_code', ''),
                'product_name': product_info.get('name', ''),
                'uom_name': product_info.get('uom_name', ''),
                'categ_id': product_info.get('categ_id', 0),
                'categ_name': product_info.get('categ_name', ''),
                'opening_qty': opening['qty'],
                'opening_value': opening['value'],
                'increase_qty': movement['increase_qty'],
                'increase_value': movement['increase_value'],
                'decrease_qty': movement['decrease_qty'],
                'decrease_value': movement['decrease_value'],
                'closing_qty': closing_qty,
                'closing_value': closing_value,
            }

            # Skip zero lines if requested
            if hide_zero_lines and self._is_zero_line(line_data, currency_rounding):
                continue

            report_lines.append(line_data)

            # Accumulate totals
            totals['opening_qty'] += line_data['opening_qty']
            totals['opening_value'] += line_data['opening_value']
            totals['increase_qty'] += line_data['increase_qty']
            totals['increase_value'] += line_data['increase_value']
            totals['decrease_qty'] += line_data['decrease_qty']
            totals['decrease_value'] += line_data['decrease_value']
            totals['closing_qty'] += line_data['closing_qty']
            totals['closing_value'] += line_data['closing_value']

        # Sort by product code/name
        report_lines.sort(key=lambda x: (x.get('default_code', ''), x.get('product_name', '')))

        # Group by category if requested
        if group_by_category:
            report_lines = self._group_lines_by_category(report_lines)

        return report_lines, totals

    def _group_lines_by_category(self, report_lines):
        """Group report lines by product category."""
        grouped = defaultdict(list)
        for line in report_lines:
            categ_name = line.get('categ_name', _('Không có danh mục'))
            grouped[categ_name].append(line)
        
        result = []
        for categ_name in sorted(grouped.keys()):
            lines = grouped[categ_name]
            # Add category header
            categ_totals = {
                'opening_qty': sum(l['opening_qty'] for l in lines),
                'opening_value': sum(l['opening_value'] for l in lines),
                'increase_qty': sum(l['increase_qty'] for l in lines),
                'increase_value': sum(l['increase_value'] for l in lines),
                'decrease_qty': sum(l['decrease_qty'] for l in lines),
                'decrease_value': sum(l['decrease_value'] for l in lines),
                'closing_qty': sum(l['closing_qty'] for l in lines),
                'closing_value': sum(l['closing_value'] for l in lines),
            }
            result.append({
                'type': 'category',
                'name': categ_name,
                **categ_totals,
            })
            # Add product lines
            for line in lines:
                line['type'] = 'product'
                result.append(line)
        
        return result

    # =========================================================================
    # REPORT VALUES
    # =========================================================================

    @api.model
    def _get_report_values(self, docids, data):
        """Get report values for rendering."""
        wizard_id = data.get('wizard_id')
        wizard = self.env['stock.valuation.report.wizard'].browse(wizard_id)
        company = self.env['res.company'].browse(data.get('company_id'))

        report_lines, totals = self._get_report_data(
            date_from=data.get('date_from'),
            date_to=data.get('date_to'),
            company_id=data.get('company_id'),
            product_ids=data.get('product_ids'),
            product_categ_ids=data.get('product_categ_ids'),
            warehouse_ids=data.get('warehouse_ids'),
            hide_zero_lines=data.get('hide_zero_lines', True),
            group_by_category=data.get('group_by_category', False),
        )

        return {
            'doc_ids': [wizard_id],
            'doc_model': 'stock.valuation.report.wizard',
            'docs': wizard,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
            'company': company,
            'company_name': company.display_name,
            'currency': company.currency_id,
            'currency_name': company.currency_id.name,
            'report_lines': report_lines,
            'totals': totals,
            'hide_zero_lines': data.get('hide_zero_lines', True),
            'group_by_category': data.get('group_by_category', False),
        }
