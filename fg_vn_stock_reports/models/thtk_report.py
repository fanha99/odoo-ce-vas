from odoo import _, api, models
from odoo.tools import float_is_zero

from .thtk_pdf import ThtkPDF


class THTKReport(models.AbstractModel):
    """ Stock summary (Bảng tổng hợp nhập xuất tồn kho): for each product,
    the opening balance, the receipts, the deliveries and the closing
    balance, in quantity and value.

    Without locations, the figures of the company: its valued moves. With
    locations, or grouped by location, the moves crossing the boundary of the
    locations, valued by `vn.stock.location.valuation`. """
    _name = 'vn.report.thtk'
    _inherit = 'vn.abstract.report'
    _description = 'Stock Summary'

    # ==================== REPORT DEFINITION ====================

    def _get_report_name(self):
        return _("STOCK SUMMARY OF RECEIPTS, DELIVERIES AND BALANCES")

    def _get_report_code(self):
        return 'THTK'

    def _get_export_filename_code(self, options):
        return 'THTK'

    def _get_report_access_groups(self):
        # the wizard is granted to the accountants and to the stock users
        return ['account.group_account_user', 'stock.group_stock_user']

    def _get_product_display_name(self, product):
        """ Name of the product with its variant values in brackets, as
        Odoo displays it. """
        name = product.name
        variant = product.product_template_attribute_value_ids._get_combination_name()
        if variant:
            name = f'{name} ({variant})'
        return name

    def _get_columns(self):
        return [
            {'name': 'code', 'label': _("Code"), 'type': 'char', 'width': 100, 'sortable': True},
            {'name': 'name', 'label': _("Product"), 'type': 'char', 'width': 250, 'sortable': True},
            {'name': 'uom', 'label': _("UoM"), 'type': 'char', 'width': 60},
            {'name': 'opening_qty', 'label': _("Opening Qty"), 'type': 'float', 'width': 90, 'sortable': True},
            {'name': 'opening_value', 'label': _("Opening Value"), 'type': 'monetary', 'width': 120, 'sortable': True},
            {'name': 'in_qty', 'label': _("Qty In"), 'type': 'float', 'width': 90, 'sortable': True},
            {'name': 'in_value', 'label': _("Value In"), 'type': 'monetary', 'width': 120, 'sortable': True},
            {'name': 'out_qty', 'label': _("Qty Out"), 'type': 'float', 'width': 90, 'sortable': True},
            {'name': 'out_value', 'label': _("Value Out"), 'type': 'monetary', 'width': 120, 'sortable': True},
            {'name': 'closing_qty', 'label': _("Closing Qty"), 'type': 'float', 'width': 90, 'sortable': True},
            {'name': 'closing_value', 'label': _("Closing Value"), 'type': 'monetary', 'width': 120, 'sortable': True},
        ]

    def _get_pdf_rl_renderer(self):
        return ThtkPDF

    def _get_custom_options(self, options):
        if 'product_ids' not in options:
            options['product_ids'] = []
        if 'category_ids' not in options:
            options['category_ids'] = []
        if 'location_ids' not in options:
            options['location_ids'] = []
        if 'group_by_location' not in options:
            options['group_by_location'] = False
        return options

    # ==================== DATA ====================

    def _get_product_domain(self, options):
        company_id = options.get('company_id', self.env.company.id)
        domain = [
            ('is_storable', '=', True),
            ('company_id', 'in', [False, company_id]),
        ]
        if options.get('product_ids'):
            domain.append(('id', 'in', options['product_ids']))
        if options.get('category_ids'):
            domain.append(('categ_id', 'child_of', options['category_ids']))
        return domain

    def _get_products(self, options):
        domain = self._get_product_domain(options)
        return self.env['product.product'].with_context(active_test=False).search(domain)

    def _get_location_domain(self, options):
        company_id = options.get('company_id', self.env.company.id)
        domain = [
            ('usage', '=', 'internal'),
            ('company_id', '=', company_id),
        ]
        if options.get('location_ids'):
            domain.append(('id', 'in', options['location_ids']))
        return domain

    def _compute_inventory_data_by_location(self, options):
        """ Figures of each internal location on its own, sublocations apart:
        each move crossing the boundary of the location is valued by
        `vn.stock.location.valuation` (the 157 location from the batches of
        the Periodic Average Cost module). """
        company_id = options.get('company_id', self.env.company.id)
        utc_range = self._get_utc_datetime_range(options)
        date_from_utc = utc_range['date_from']
        date_to_utc = utc_range['date_to']

        products = self._get_products(options)
        if not products:
            return {}

        location_domain = self._get_location_domain(options)
        locations = self.env['stock.location'].search(location_domain)
        if not locations:
            return {}

        Valuation = self.env['vn.stock.location.valuation']
        result = {}
        for location in locations:
            entries_by_product = Valuation._get_location_entries(
                company_id, products.ids, [location.id], date_to_utc)
            location_data = {
                'location_id': location.id,
                'location_name': location.complete_name,
                'products': {},
            }
            for product in products:
                data = Valuation._summarize(
                    entries_by_product.get(product.id, []), date_from_utc)

                if (float_is_zero(data['opening_qty'], 3) and float_is_zero(data['in_qty'], 3)
                        and float_is_zero(data['out_qty'], 3) and float_is_zero(data['closing_qty'], 3)):
                    if not options.get('show_zero_balance'):
                        continue

                location_data['products'][product.id] = dict(data, product=product)

            if location_data['products']:
                result[location.id] = location_data

        return result

    def _compute_inventory_data(self, options):
        """ Figures of the company, from its valued moves: is_in are receipts,
        is_out are deliveries. With locations, those of the locations. """
        company_id = options.get('company_id', self.env.company.id)
        utc_range = self._get_utc_datetime_range(options)
        date_from_utc = utc_range['date_from']
        date_to_utc = utc_range['date_to']

        products = self._get_products(options)
        if not products:
            return {}

        if options.get('location_ids'):
            return self._compute_inventory_data_with_location_filter(options, products)

        # Opening balance: the moves before the period. The value of an
        # outgoing move is negative since 20.0: the direction comes from is_in /
        # is_out, the value is ABS(value). Quantities in the unit of the product.
        self.env['stock.move'].flush_model()
        self.env.cr.execute("""
            SELECT
                sm.product_id,
                COALESCE(SUM(CASE WHEN sm.is_in THEN sm.quantity_product_uom ELSE -sm.quantity_product_uom END), 0) as qty,
                COALESCE(SUM(CASE WHEN sm.is_in THEN ABS(sm.value) ELSE -ABS(sm.value) END), 0) as value
            FROM stock_move sm
            WHERE sm.product_id IN %s
              AND sm.company_id = %s
              AND sm.state = 'done'
              AND (sm.is_in = TRUE OR sm.is_out = TRUE)
              AND sm.date < %s
            GROUP BY sm.product_id
        """, (tuple(products.ids), company_id, date_from_utc))
        opening_data = {row[0]: {'qty': row[1], 'value': row[2]}
                        for row in self.env.cr.fetchall()}

        # moves of the period
        self.env.cr.execute("""
            SELECT
                sm.product_id,
                COALESCE(SUM(CASE WHEN sm.is_in THEN sm.quantity_product_uom ELSE 0 END), 0) as in_qty,
                COALESCE(SUM(CASE WHEN sm.is_in THEN ABS(sm.value) ELSE 0 END), 0) as in_value,
                COALESCE(SUM(CASE WHEN sm.is_out THEN sm.quantity_product_uom ELSE 0 END), 0) as out_qty,
                COALESCE(SUM(CASE WHEN sm.is_out THEN ABS(sm.value) ELSE 0 END), 0) as out_value
            FROM stock_move sm
            WHERE sm.product_id IN %s
              AND sm.company_id = %s
              AND sm.state = 'done'
              AND (sm.is_in = TRUE OR sm.is_out = TRUE)
              AND sm.date >= %s
              AND sm.date <= %s
            GROUP BY sm.product_id
        """, (tuple(products.ids), company_id, date_from_utc, date_to_utc))
        movement_data = {row[0]: {
            'in_qty': row[1], 'in_value': row[2],
            'out_qty': row[3], 'out_value': row[4]
        } for row in self.env.cr.fetchall()}

        result = {}
        for product in products:
            opening = opening_data.get(product.id, {'qty': 0, 'value': 0})
            movement = movement_data.get(product.id, {
                'in_qty': 0, 'in_value': 0, 'out_qty': 0, 'out_value': 0
            })
            closing_qty = opening['qty'] + movement['in_qty'] - movement['out_qty']
            closing_value = opening['value'] + movement['in_value'] - movement['out_value']
            result[product.id] = {
                'product': product,
                'opening_qty': opening['qty'],
                'opening_value': opening['value'],
                'in_qty': movement['in_qty'],
                'in_value': movement['in_value'],
                'out_qty': movement['out_qty'],
                'out_value': movement['out_value'],
                'closing_qty': closing_qty,
                'closing_value': closing_value,
            }
        return result

    def _compute_inventory_data_with_location_filter(self, options, products=None):
        """ Figures of the selected locations and their sublocations: each move
        crossing their boundary is valued by `vn.stock.location.valuation`. """
        company_id = options.get('company_id', self.env.company.id)
        location_ids = options.get('location_ids', [])
        if not location_ids:
            return {}
        if products is None:
            products = self._get_products(options)
        if not products:
            return {}

        utc_range = self._get_utc_datetime_range(options)

        Valuation = self.env['vn.stock.location.valuation']
        locations = Valuation._expand_locations(location_ids)
        entries_by_product = Valuation._get_location_entries(
            company_id, products.ids, locations, utc_range['date_to'])

        result = {}
        for product in products:
            data = Valuation._summarize(
                entries_by_product.get(product.id, []), utc_range['date_from'])
            result[product.id] = dict(data, product=product)
        return result

    @api.model
    def _get_lines(self, options):
        show_zero = options.get('show_zero_balance', False)
        group_by_location = options.get('group_by_location', False)

        if group_by_location:
            return self._get_lines_grouped_by_location(options, show_zero)

        inventory_data = self._compute_inventory_data(options)
        lines = []
        totals = {
            'opening_qty': 0, 'opening_value': 0,
            'in_qty': 0, 'in_value': 0,
            'out_qty': 0, 'out_value': 0,
            'closing_qty': 0, 'closing_value': 0,
        }

        sorted_items = sorted(inventory_data.items(),
                              key=lambda x: x[1]['product'].default_code or '')

        for product_id, data in sorted_items:
            product = data['product']
            if not show_zero:
                has_movement = (
                    not float_is_zero(data['opening_qty'], precision_digits=3) or
                    not float_is_zero(data['in_qty'], precision_digits=3) or
                    not float_is_zero(data['out_qty'], precision_digits=3) or
                    not float_is_zero(data['closing_qty'], precision_digits=3)
                )
                if not has_movement:
                    continue

            line = {
                'id': f'product_{product_id}',
                'product_id': product_id,
                'code': product.default_code or '',
                'name': self._get_product_display_name(product),
                'uom': product.uom_id.name,
                'opening_qty': data['opening_qty'],
                'opening_value': data['opening_value'],
                'in_qty': data['in_qty'],
                'in_value': data['in_value'],
                'out_qty': data['out_qty'],
                'out_value': data['out_value'],
                'closing_qty': data['closing_qty'],
                'closing_value': data['closing_value'],
            }
            lines.append(line)
            for key in totals:
                totals[key] += data[key]

        return [{
            'id': 'thtk_report',
            'lines': lines,
            'totals': totals,
            'total_label': _("GRAND TOTAL"),
            'group_by_location': False,
        }]

    def _get_lines_grouped_by_location(self, options, show_zero):
        location_data = self._compute_inventory_data_by_location(options)
        groups = []
        grand_totals = {
            'opening_qty': 0, 'opening_value': 0,
            'in_qty': 0, 'in_value': 0,
            'out_qty': 0, 'out_value': 0,
            'closing_qty': 0, 'closing_value': 0,
        }

        for location_id, loc_data in location_data.items():
            lines = []
            totals = {k: 0 for k in grand_totals}

            sorted_products = sorted(loc_data['products'].items(),
                                     key=lambda x: x[1]['product'].default_code or '')

            for product_id, data in sorted_products:
                product = data['product']
                if not show_zero:
                    has_movement = (
                        not float_is_zero(data['opening_qty'], precision_digits=3) or
                        not float_is_zero(data['in_qty'], precision_digits=3) or
                        not float_is_zero(data['out_qty'], precision_digits=3) or
                        not float_is_zero(data['closing_qty'], precision_digits=3)
                    )
                    if not has_movement:
                        continue

                line = {
                    'id': f'product_{location_id}_{product_id}',
                    'product_id': product_id,
                    'location_id': location_id,
                    'code': product.default_code or '',
                    'name': self._get_product_display_name(product),
                    'uom': product.uom_id.name,
                    'opening_qty': data['opening_qty'],
                    'opening_value': data['opening_value'],
                    'in_qty': data['in_qty'],
                    'in_value': data['in_value'],
                    'out_qty': data['out_qty'],
                    'out_value': data['out_value'],
                    'closing_qty': data['closing_qty'],
                    'closing_value': data['closing_value'],
                }
                lines.append(line)
                for key in totals:
                    totals[key] += data[key]

            if lines:
                groups.append({
                    'id': f'location_{location_id}',
                    'location_id': location_id,
                    'location_name': loc_data['location_name'],
                    'lines': lines,
                    'totals': totals,
                    'total_label': _("Total %s", loc_data['location_name']),
                })
                for key in grand_totals:
                    grand_totals[key] += totals[key]

        return [{
            'id': 'thtk_report',
            'groups': groups,
            'totals': grand_totals,
            'total_label': _("GRAND TOTAL"),
            'group_by_location': True,
        }]

    # ==================== DRILL DOWN ====================

    def _get_drill_down_action(self, options, params):
        """ Moves of the product in the period, by `params['drill']`:
        'valuation' (default) the valued moves, 'move' the stock moves and
        'move_lines' the stock move lines, of the location of the line when
        grouped by location. """
        product_id = params.get('product_id')
        if not product_id:
            return False
        utc_range = self._get_utc_datetime_range(options)
        domain = [
            ('product_id', '=', product_id),
            ('date', '>=', utc_range['date_from']),
            ('date', '<=', utc_range['date_to']),
            ('state', '=', 'done'),
        ]
        drill = params.get('drill') or 'valuation'
        if drill == 'valuation':
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Valuation"),
                'res_model': 'stock.move',
                'view_mode': 'list,form',
                'domain': domain + ['|', ('is_in', '=', True), ('is_out', '=', True)],
            }
        location_id = params.get('location_id')
        if location_id:
            domain += ['|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id)]
        if drill == 'move':
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Moves - %s", params.get('name', '')),
                'res_model': 'stock.move',
                'view_mode': 'list,form',
                'domain': domain,
                'context': {'search_default_done': 1},
            }
        if drill == 'move_lines':
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Move Lines - %s", params.get('name', '')),
                'res_model': 'stock.move.line',
                'view_mode': 'list,form',
                'domain': domain,
            }
        return False

    # ==================== XLSX EXPORT ====================

    def _write_xlsx_column_headers(self, sheet, columns, formats, row):
        """ Headers on two rows: opening, receipts, deliveries and closing on
        the first one, quantity and value below each. """
        headers_main = [
            (_("Code"), 1), (_("Product"), 1), (_("UoM"), 1),
            (_("Opening"), 2), (_("Receipts"), 2), (_("Deliveries"), 2), (_("Closing"), 2),
        ]
        col = 0
        for header, span in headers_main:
            if span > 1:
                sheet.merge_range(row, col, row, col + span - 1, header, formats['header'])
            else:
                sheet.merge_range(row, col, row + 1, col, header, formats['header'])
            col += span

        sub_headers = [_("Qty"), _("Value")] * 4
        for i, h in enumerate(sub_headers):
            sheet.write(row + 1, 3 + i, h, formats['header'])
        return row + 2

    def _groups_to_xlsx_rows(self, groups):
        if not groups:
            return []
        data = groups[0]
        rows = []

        def _line_cells(line):
            return [
                line.get('product_id', '') or '',
                line.get('name', '')       or '',
                line.get('uom', '')        or '',
                line.get('opening_qty')    or 0,
                line.get('opening_value')  or 0,
                line.get('in_qty')         or 0,
                line.get('in_value')       or 0,
                line.get('out_qty')        or 0,
                line.get('out_value')      or 0,
                line.get('closing_qty')    or 0,
                line.get('closing_value')  or 0,
            ]

        def _total_cells(group):
            totals = group.get('totals', {})
            return [
                '', group['total_label'], '',
                totals.get('opening_qty')   or 0,
                totals.get('opening_value') or 0,
                totals.get('in_qty')        or 0,
                totals.get('in_value')      or 0,
                totals.get('out_qty')       or 0,
                totals.get('out_value')     or 0,
                totals.get('closing_qty')   or 0,
                totals.get('closing_value') or 0,
            ]

        if data.get('group_by_location'):
            for loc in data.get('groups', []):
                rows.append({
                    'type':     'group_hdr',
                    'cells':    [loc.get('location_name', '')],
                    'span_all': True,
                })
                for line in loc.get('lines', []):
                    rows.append({'type': 'data', 'cells': _line_cells(line)})
                rows.append({
                    'type':  'group_total',
                    'cells': _total_cells(loc),
                })
        else:
            for line in data.get('lines', []):
                rows.append({'type': 'data', 'cells': _line_cells(line)})

        rows.append({
            'type':  'grand_total',
            'cells': _total_cells(data),
        })
        return rows

    def _set_xlsx_column_widths(self, sheet, columns):
        widths = [12, 35, 8, 12, 15, 12, 15, 12, 15, 12, 15]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
