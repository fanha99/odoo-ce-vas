from datetime import UTC

from odoo import _, api, models
from odoo.tools import float_is_zero

from .s06_pdf import S06PDF


class S06Report(models.AbstractModel):
    """ Detailed ledger of materials, tools, products and goods (Sổ chi tiết
    vật liệu, dụng cụ, sản phẩm, hàng hoá, form S06-DNN): for each product,
    the opening balance, the stock moves of the period with the running
    balance, and the closing balance.

    Without locations, the ledger of the company: its valued moves (is_in /
    is_out). With locations, the ledger of these locations: the moves crossing
    their boundary, valued by `vn.stock.location.valuation`. """
    _name = 'vn.report.s06'
    _inherit = 'vn.abstract.report'
    _description = 'Detailed Stock Ledger (S06-DNN)'

    # ==================== REPORT DEFINITION ====================

    def _get_report_name(self):
        return _("DETAILED LEDGER OF MATERIALS, TOOLS, PRODUCTS AND GOODS")

    def _get_report_code(self):
        return _("Form No. S06-DNN")

    def _get_export_filename_code(self, options):
        return 'S06-DNN'

    def _get_report_access_groups(self):
        # the wizard is granted to the accountants and to the stock users
        return ['account.group_account_user', 'stock.group_stock_user']

    def _get_columns(self):
        return [
            {'name': 'date', 'label': _("Date"), 'type': 'date', 'width': 85},
            {'name': 'reference', 'label': _("Voucher"), 'type': 'char', 'width': 105},
            {'name': 'description', 'label': _("Description"), 'type': 'char', 'width': 245},
            {'name': 'unit_price', 'label': _("Unit Price"), 'type': 'monetary', 'width': 85},
            {'name': 'qty_in', 'label': _("Qty In"), 'type': 'float', 'width': 70},
            {'name': 'value_in', 'label': _("Value In"), 'type': 'monetary', 'width': 105},
            {'name': 'qty_out', 'label': _("Qty Out"), 'type': 'float', 'width': 70},
            {'name': 'value_out', 'label': _("Value Out"), 'type': 'monetary', 'width': 105},
            {'name': 'balance_qty', 'label': _("Qty Balance"), 'type': 'float', 'width': 70},
            {'name': 'balance_value', 'label': _("Value Balance"), 'type': 'monetary', 'width': 105},
        ]

    def _get_pdf_rl_renderer(self):
        return S06PDF

    def _get_report_scope_label(self, options):
        """ The selected locations, printed with the period on the PDF and in
        the Excel file; their sublocations are not listed. """
        if not options.get('location_ids'):
            return ''
        locations = self.env['stock.location'].browse(options['location_ids'])
        return _("Locations: %s", ', '.join(locations.mapped('complete_name')))

    def _build_report_data(self, options):
        data = super()._build_report_data(options)
        data['header']['scope_label'] = self._get_report_scope_label(options)
        return data

    def _write_xlsx_header(self, sheet, data, formats, group=None):
        next_row = super()._write_xlsx_header(sheet, data, formats, group)
        hdr = data['header']
        if hdr.get('scope_label'):
            sheet.write(1, 0, _(
                "%(scope)s, from %(date_from)s to %(date_to)s", scope=hdr['scope_label'],
                date_from=hdr.get('date_from', ''), date_to=hdr.get('date_to', ''),
            ), formats['title'])
        return next_row

    def _get_custom_options(self, options):
        if 'product_ids' not in options:
            options['product_ids'] = []
        if 'category_ids' not in options:
            options['category_ids'] = []
        if 'account_ids' not in options:
            options['account_ids'] = []
        return options

    # ==================== DATA ====================

    def _get_filter_accounts(self, options):
        """ The stock accounts of the ledger: 152, 153, 155 and 156. """
        company_id = options.get('company_id', self.env.company.id)
        domain = [
            ('company_ids', 'in', [company_id]),
            '|', '|', '|',
            ('code', '=like', '152%'),
            ('code', '=like', '153%'),
            ('code', '=like', '155%'),
            ('code', '=like', '156%'),
        ]
        return self.env['account.account'].search(domain)

    def _compute_opening_balance(self, product_id, date_from_utc, company_id):
        """ Quantity and value of the company before the period, from its
        valued moves. The value of an outgoing move is negative since 20.0:
        the direction comes from is_in / is_out, the value is ABS(value). The
        quantity is in the unit of the product. """
        self.env['stock.move'].flush_model()
        self.env.cr.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN sm.is_in THEN sm.quantity_product_uom ELSE -sm.quantity_product_uom END), 0) as quantity,
                COALESCE(SUM(CASE WHEN sm.is_in THEN ABS(sm.value) ELSE -ABS(sm.value) END), 0) as value
            FROM stock_move sm
            WHERE sm.product_id = %s
              AND sm.company_id = %s
              AND sm.state = 'done'
              AND (sm.is_in = TRUE OR sm.is_out = TRUE)
              AND sm.date < %s
        """, (product_id, company_id, date_from_utc))

        result = self.env.cr.fetchone()
        quantity = result[0] if result else 0
        value = result[1] if result else 0
        return {
            'quantity': quantity,
            'value': value,
            'unit_price': value / quantity if quantity else 0,
        }

    def _compute_period_moves(self, product_id, date_from_utc, date_to_utc, company_id):
        """ Valued moves of the company in the period: is_in are receipts,
        is_out are deliveries. """
        self.env.cr.execute("""
            SELECT
                sm.id,
                DATE_TRUNC('day', sm.date)::date AS date,
                sm.reference AS reference,
                sp.name AS picking_name,
                spt.code AS picking_type_code,
                CASE WHEN sm.is_in THEN sm.quantity_product_uom ELSE -sm.quantity_product_uom END AS quantity,
                CASE WHEN sm.is_in THEN ABS(sm.value) ELSE -ABS(sm.value) END AS value,
                CASE WHEN sm.quantity_product_uom > 0 THEN ABS(sm.value) / sm.quantity_product_uom ELSE 0 END AS unit_price,
                CASE WHEN sm.is_in THEN sm.quantity_product_uom ELSE 0 END AS qty_in,
                CASE WHEN sm.is_in THEN ABS(sm.value) ELSE 0 END AS value_in,
                CASE WHEN sm.is_out THEN sm.quantity_product_uom ELSE 0 END AS qty_out,
                CASE WHEN sm.is_out THEN ABS(sm.value) ELSE 0 END AS value_out,
                COALESCE(sm.description_picking_manual, '') AS description,
                am.id AS account_move_id,
                am.name AS account_move_name,
                am.ref AS account_move_ref
            FROM stock_move sm
            LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
            LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            LEFT JOIN account_move am ON am.id = sm.account_move_id
            WHERE sm.product_id = %s
              AND sm.company_id = %s
              AND sm.state = 'done'
              AND (sm.is_in = TRUE OR sm.is_out = TRUE)
              AND sm.date >= %s
              AND sm.date <= %s
            ORDER BY date, sp.picking_type_id, sm.reference
        """, (product_id, company_id, date_from_utc, date_to_utc))

        return self.env.cr.dictfetchall()

    def _compute_product_balance(self, product, options):
        company_id = options.get('company_id', self.env.company.id)
        utc_range = self._get_utc_datetime_range(options)
        date_from_utc = utc_range['date_from']
        date_to_utc = utc_range['date_to']

        opening = self._compute_opening_balance(product.id, date_from_utc, company_id)
        moves = self._compute_period_moves(product.id, date_from_utc, date_to_utc, company_id)

        running_qty = opening['quantity']
        running_value = opening['value']

        lines = []
        for move in moves:
            running_qty += move['qty_in'] - move['qty_out']
            running_value += move['value_in'] - move['value_out']

            picking_type = move.get('picking_type_code')
            if picking_type == 'incoming':
                if move.get('account_move_ref'):
                    str_def = _("Purchase costs, invoice %s", move['account_move_ref'])
                else:
                    str_def = _("Goods receipt, invoice %s", '')
            elif picking_type == 'outgoing':
                str_def = _("Goods delivery, invoice %s", '')
            else:
                str_def = move.get('description') or ''

            lines.append({
                'move_id': move['id'],
                'svl_id': False,
                'date': move['date'],
                'reference': move['picking_name'] or move['reference'] or '',
                'description': str_def,
                'account_move_id': move['account_move_id'],
                'account_move_name': move['account_move_name'],
                'unit_price': move['value'] / move['quantity'] if move['quantity'] else 0,
                'qty_in': move['qty_in'],
                'value_in': move['value_in'],
                'qty_out': move['qty_out'],
                'value_out': move['value_out'],
                'balance_qty': running_qty,
                'balance_value': running_value,
            })

        return {
            'opening': opening,
            'lines': lines,
            'closing': {
                'quantity': running_qty,
                'value': running_value,
                'unit_price': running_value / running_qty if running_qty else 0,
            },
            'total': {
                'qty_in': sum(l['qty_in'] for l in lines),
                'value_in': sum(l['value_in'] for l in lines),
                'qty_out': sum(l['qty_out'] for l in lines),
                'value_out': sum(l['value_out'] for l in lines),
            }
        }

    def _get_invoice_refs(self, picking_ids):
        """ References of the invoices of each transfer: {picking_id: 'ref1, ref2'}.
        Needs stock.picking.invoice_ids (OCA stock_picking_invoice_link); empty
        without it. """
        if not picking_ids or 'invoice_ids' not in self.env['stock.picking']._fields:
            return {}
        self.env.cr.execute("""
            SELECT rel.stock_picking_id,
                   string_agg(NULLIF(am.ref, ''), ', ' ORDER BY am.ref)
            FROM account_move_stock_picking_rel rel
            JOIN account_move am ON am.id = rel.account_move_id
            WHERE rel.stock_picking_id IN %s
            GROUP BY rel.stock_picking_id
        """, (tuple(picking_ids),))
        return {row[0]: row[1] or '' for row in self.env.cr.fetchall()}

    def _compute_product_balance_by_location(self, entries, options, location_names, invoice_refs):
        """ Balances and moves of one product in the selected locations, from
        the entries of `vn.stock.location.valuation`: one line per move crossing
        the boundary of the locations, internal transfers included (e.g. to and
        from the 157 location). """
        Valuation = self.env['vn.stock.location.valuation']
        utc_range = self._get_utc_datetime_range(options)
        date_from_utc = Valuation._naive(utc_range['date_from'])
        tz = self._get_user_timezone()

        opening_qty = opening_value = 0.0
        period_entries = []
        for e in entries:
            if e['date'] < date_from_utc:
                opening_qty += e['qty_in'] - e['qty_out']
                opening_value += e['value_in'] - e['value_out']
            else:
                period_entries.append(e)

        running_qty, running_value = opening_qty, opening_value
        lines = []
        for e in period_entries:
            running_qty += e['qty_in'] - e['qty_out']
            running_value += e['value_in'] - e['value_out']
            refs = invoice_refs.get(e['picking_id'], '') if e['picking_id'] else ''
            code = e['picking_type_code']
            if not e['move_id']:
                str_def = e['description'] or _("Value adjustment")
            elif code == 'incoming':
                str_def = _("Goods receipt, invoice %s", refs)
            elif code == 'outgoing':
                str_def = _("Goods delivery, invoice %s", refs)
            elif e['qty_in']:
                str_def = _("Internal transfer from %s", location_names.get(e['location_id'], ''))
            else:
                str_def = _("Internal transfer to %s", location_names.get(e['location_dest_id'], ''))
            qty = e['qty_in'] or e['qty_out']
            value = e['value_in'] or e['value_out']
            lines.append({
                'move_id': e['move_id'],
                'svl_id': e['svl_id'],
                'date': e['date'].replace(tzinfo=UTC).astimezone(tz).date(),
                'reference': e['reference'],
                'description': str_def,
                'account_move_id': e['account_move_id'],
                'account_move_name': False,
                'unit_price': value / qty if qty else 0,
                'qty_in': e['qty_in'],
                'value_in': e['value_in'],
                'qty_out': e['qty_out'],
                'value_out': e['value_out'],
                'balance_qty': running_qty,
                'balance_value': running_value,
            })

        return {
            'opening': {
                'quantity': opening_qty,
                'value': opening_value,
                'unit_price': opening_value / opening_qty if opening_qty else 0,
            },
            'lines': lines,
            'closing': {
                'quantity': running_qty,
                'value': running_value,
                'unit_price': running_value / running_qty if running_qty else 0,
            },
            'total': {
                'qty_in': sum(l['qty_in'] for l in lines),
                'value_in': sum(l['value_in'] for l in lines),
                'qty_out': sum(l['qty_out'] for l in lines),
                'value_out': sum(l['value_out'] for l in lines),
            }
        }

    def _get_product_label(self, product):
        """ Header of the ledger of a product. The product is shown with its
        database id, as in 19.0. """
        return _("Product: %(id)s - %(name)s (%(uom)s)",
                 id=product.id, name=product.name, uom=product.uom_id.name)

    @api.model
    def _get_lines(self, options):
        company_id = options.get('company_id', self.env.company.id)
        show_zero = options.get('show_zero_balance', False)

        product_domain = [
            ('is_storable', '=', True),
            ('company_id', 'in', [False, company_id]),
        ]
        if options.get('product_ids'):
            product_domain.append(('id', 'in', options['product_ids']))
        if options.get('category_ids'):
            product_domain.append(('categ_id', 'in', options['category_ids']))

        products = self.env['product.product'].with_context(active_test=False).search(
            product_domain, order='default_code, name'
        )

        accounts = self._get_filter_accounts(options)
        if options.get('account_ids'):
            accounts = accounts.filtered(lambda a: a.id in options['account_ids'])

        # With locations: each move crossing the boundary of the locations
        # (sublocations included) is valued. Without: the valuation of the company.
        entries_by_product = None
        if options.get('location_ids') and products:
            Valuation = self.env['vn.stock.location.valuation']
            locations = Valuation._expand_locations(options['location_ids'])
            utc_range = self._get_utc_datetime_range(options)
            entries_by_product = Valuation._get_location_entries(
                company_id, products.ids, locations, utc_range['date_to'])
            all_entries = [e for entries in entries_by_product.values() for e in entries]
            invoice_refs = self._get_invoice_refs(
                {e['picking_id'] for e in all_entries if e['picking_id']})
            loc_ids = set()
            for e in all_entries:
                loc_ids.update(filter(None, (e['location_id'], e['location_dest_id'])))
            location_names = {
                loc.id: loc.complete_name
                for loc in self.env['stock.location'].browse(list(loc_ids))
            }

        opening_label = _("Opening balance")
        closing_label = _("Total of the period / Closing balance")
        result = []
        for product in products:
            # The account of the Periodic Average Cost module first (many
            # categories only set this one), then the standard one. Both are
            # company dependent: read them for the company of the report.
            categ = product.categ_id.with_company(company_id)
            product_account = (
                getattr(categ, 'gbqk_valuation_account_id', False)
                or categ.property_stock_valuation_account_id
            )
            if not product_account or product_account not in accounts:
                continue

            if entries_by_product is not None:
                balance_data = self._compute_product_balance_by_location(
                    entries_by_product.get(product.id, []), options,
                    location_names, invoice_refs)
            else:
                balance_data = self._compute_product_balance(product, options)

            if not show_zero:
                if (not balance_data['lines'] and
                        float_is_zero(balance_data['opening']['quantity'], precision_digits=3) and
                        float_is_zero(balance_data['closing']['quantity'], precision_digits=3)):
                    continue

            product_data = {
                'id': f'product_{product.id}',
                'product_id': product.id,
                'product_code': product.default_code or '',
                'product_name': product.name,
                'product_uom': product.uom_id.name,
                'label': self._get_product_label(product),
                'opening_label': opening_label,
                'closing_label': closing_label,
                'account_id': product_account.id,
                'account_code': product_account.code,
                'opening': balance_data['opening'],
                'closing': balance_data['closing'],
                'total': balance_data['total'],
                'lines': [],
            }

            for idx, line in enumerate(balance_data['lines']):
                product_data['lines'].append({
                    'id': f'line_{product.id}_{idx}',
                    'parent_id': f'product_{product.id}',
                    **line,
                })

            result.append(product_data)

        return result

    # ==================== DRILL DOWN ====================

    def _get_drill_down_action(self, options, params):
        """ Group: the stock moves of the product in the period. Line, by
        `params['drill']`: 'valuation' (default), 'move', 'move_lines' or
        'account_move'. """
        if params.get('type') == 'line':
            move_id = params.get('move_id')
            drill = params.get('drill') or 'valuation'
            if drill == 'move' and move_id:
                return self._get_record_action('stock.move', move_id, _("Stock Move"))
            if drill == 'move_lines' and move_id:
                domain = [('move_id', '=', move_id)]
                return {
                    'type': 'ir.actions.act_window',
                    'name': _("Stock Move Lines"),
                    'res_model': 'stock.move.line',
                    'view_mode': 'list,form',
                    'domain': domain,
                }
            if drill == 'account_move' and params.get('account_move_id'):
                return self._get_record_action(
                    'account.move', params['account_move_id'], _("Journal Entry"))
            if drill == 'valuation':
                return self._get_line_valuation_action(move_id)
            return False

        if params.get('type') == 'group':
            product_id = params.get('product_id')
            line_id = str(params.get('line_id', ''))
            if not product_id and line_id.startswith('product_'):
                product_id = int(line_id.removeprefix('product_'))
            if product_id:
                utc_range = self._get_utc_datetime_range(options)
                domain = [
                    ('product_id', '=', product_id),
                    ('date', '>=', utc_range['date_from']),
                    ('date', '<=', utc_range['date_to']),
                    ('state', '=', 'done'),
                ]
                return {
                    'type': 'ir.actions.act_window',
                    'name': _("Stock Moves"),
                    'res_model': 'stock.move',
                    'view_mode': 'list,form',
                    'domain': domain,
                }
        return False

    def _get_record_action(self, model, res_id, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'res_id': res_id,
            'view_mode': 'form',
        }

    def _get_line_valuation_action(self, move_id):
        """ Valuation of one line of the ledger, that is of one stock move:
        the valuation list of stock_account for a valued move, the transfer
        (or the move) for an internal transfer. """
        if not move_id:
            return False
        move = self.env['stock.move'].browse(move_id)
        view = self.env.ref('stock_account.stock_move_view_list_valuation',
                            raise_if_not_found=False)
        if (move.is_in or move.is_out) and view:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Stock Valuation"),
                'res_model': 'stock.move',
                'view_mode': 'list',
                'views': [(view.id, 'list')],
                'domain': [('id', '=', move.id)],
                'context': {
                    'cost_method': move.product_id.cost_method,
                    'tracking': move.product_id.tracking,
                },
            }
        if move.picking_id:
            return self._get_record_action('stock.picking', move.picking_id.id, _("Transfer"))
        return self._get_record_action('stock.move', move.id, _("Stock Move"))

    # ==================== XLSX EXPORT ====================

    def _should_xlsx_split_by_group(self):
        return True

    def _format_xlsx_sheet_name(self, group):
        code = group.get('product_id', '') or group.get('id', '')
        name = group.get('product_name') or group.get('name') or 'Sheet'
        label = f"{code} - {name}" if code else str(name)
        label = label[:31]
        for ch in '/\\*?[]:':
            label = label.replace(ch, '-')
        return label

    def _format_xlsx_group_label(self, group):
        return group['label']

    def _group_to_xlsx_rows(self, group):
        rows = []
        op = group.get('opening', {})
        rows.append({
            'type': 'opening',
            'cells': ['', '', group['opening_label'],
                      op.get('unit_price') or 0,
                      '', '', '', '',
                      op.get('quantity') or 0,
                      op.get('value') or 0],
        })
        for line in group.get('lines', []):
            date_s = str(line['date'])[:10] if line.get('date') else ''
            rows.append({
                'type': 'data',
                'cells': [
                    date_s,
                    line.get('reference') or '',
                    line.get('description') or '',
                    line.get('unit_price') or 0,
                    line.get('qty_in') or 0,
                    line.get('value_in') or 0,
                    line.get('qty_out') or 0,
                    line.get('value_out') or 0,
                    line.get('balance_qty') or 0,
                    line.get('balance_value') or 0,
                ],
            })
        total = group.get('total', {})
        cl = group.get('closing', {})
        rows.append({
            'type': 'closing',
            'cells': ['', '', group['closing_label'],
                      cl.get('unit_price') or 0,
                      total.get('qty_in') or 0,
                      total.get('value_in') or 0,
                      total.get('qty_out') or 0,
                      total.get('value_out') or 0,
                      cl.get('quantity') or 0,
                      cl.get('value') or 0],
        })
        return rows

    def _set_xlsx_column_widths(self, sheet, columns):
        widths = [10.5, 13.5, 35, 11, 8.5, 11.5, 8.5, 11.5, 8.5, 11.5]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)
