from bisect import bisect_right
from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import models
from odoo.tools import float_is_zero

# Done quantity in the unit of the product: stored on stock_move since 20.0.
# 19.0 converted sm.quantity from the unit of the move and needed a join on
# the units of measure, left empty here.
_SQL_QTY = 'sm.quantity_product_uom'
_SQL_UOM_JOIN = ''


class StockLocationValuation(models.AbstractModel):
    """ Receipts, deliveries and balances (quantity and value) of a set S of
    locations, for the stock summary and the S06 ledger with selected
    locations. Without locations, the reports read the valuation of the
    company.

    Odoo values the stock of the company, not of each location (is_in: in
    the valued stock, is_out: out of it; since 20.0 the value of an outgoing
    move is negative, so the value is always read as abs(value) and the
    direction comes from elsewhere). The value of a set of locations is
    therefore built from the moves crossing the boundary of S: one end in S,
    the other out of S; a move with both ends in S is an internal transfer
    of S and is left out. The direction is the one of the boundary, not
    is_in / is_out: with the flag of the Periodic Average Cost module (GBQK),
    stock -> 157 is is_out but is a receipt of the 157 location.

    - Valued moves (is_in / is_out: purchases, sales, returns, inventory
      adjustments, stock <-> 157 with the flag...): move.value, which already
      holds the landed costs and the price difference of the vendor bill.
    - Moves without valuation:
        stock -> 157: value_in of the GBQK batch created from the move;
        157 -> stock or customer: sum of the values of the GBQK consumptions
        of the move;
        in or out of 157 without GBQK data: FIFO matching of the moves in and
        out of 157 (_get_transit_derived_values);
        others: quantity x GBQK average cost of the period holding the date
        of the move, then x average valuation at the date of the move, then
        x price_unit, then x current cost.
    - A product.value without move (manual revaluation) changes the value of
      no move, so it is not in the figures of a location.

    157 locations: the locations flagged "Kho 157 (GBQK)" and the transit
    locations of the GBQK periods. The Periodic Average Cost module
    (fg_gia_binh_quan_ky) is optional: without it there is no 157 location,
    and internal transfers take the average valuation at their date, the
    price_unit or the current cost.
    """
    _name = 'vn.stock.location.valuation'
    _description = 'Stock In/Out per Location'

    def _expand_locations(self, location_ids):
        """ The selected locations and their internal sublocations. """
        if not location_ids:
            return set()
        locations = self.env['stock.location'].with_context(active_test=False).search([
            ('id', 'child_of', list(location_ids)),
            ('usage', '=', 'internal'),
        ])
        return set(locations.ids)

    def _get_location_entries(self, company_id, product_ids, location_ids, date_to_utc):
        """ The moves crossing the boundary of S until date_to_utc.

        :param location_ids: the set S (sublocations already added if needed)
        :return: {product_id: [entry, ...]} by date and move; an entry is a
            dict: date, move_id, svl_id, reference, picking_id,
            picking_type_code, description, account_move_id, location_id,
            location_dest_id, qty_in, qty_out, value_in, value_out. svl_id is
            always False (no valuation layer since 19.0), kept for the S06
            lines.
        """
        result = {}
        if not product_ids or not location_ids:
            return result
        loc_set = set(location_ids)
        self.env['stock.move'].flush_model()
        params = {
            'company_id': company_id,
            'product_ids': tuple(product_ids),
            'locs': tuple(location_ids),
            'date_to': self._naive(date_to_utc),
        }
        self.env.cr.execute("""
                SELECT sm.id, sm.product_id, sm.date, sm.location_id, sm.location_dest_id,
                       {qty} AS product_qty, sm.price_unit, sm.reference, sm.origin,
                       sm.picking_id, sp.name AS picking_name, spt.code AS picking_type_code,
                       sm.value, (sm.is_in OR sm.is_out) AS valued,
                       sm.account_move_id
                FROM stock_move sm
                {uom_join}
                LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                LEFT JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE sm.state = 'done'
                  AND sm.company_id = %(company_id)s
                  AND sm.product_id IN %(product_ids)s
                  AND sm.date <= %(date_to)s
                  AND ((sm.location_id IN %(locs)s) <> (sm.location_dest_id IN %(locs)s))
                ORDER BY sm.date, sm.id
            """.format(qty=_SQL_QTY, uom_join=_SQL_UOM_JOIN), params)
        moves = self.env.cr.dictfetchall()

        valuer = self._get_internal_move_valuer(company_id, product_ids, moves)
        currency = self.env['res.company'].browse(company_id).currency_id

        for m in moves:
            qty = m['product_qty'] or 0.0
            incoming = m['location_dest_id'] in loc_set
            # |move.value| (negative for outgoing moves since 20.0); the
            # direction is the one of the boundary of S (see the class)
            value = abs(m['value'] or 0.0) if m['valued'] else valuer(m)
            value_in = value if incoming else 0.0
            value_out = value if not incoming else 0.0
            result.setdefault(m['product_id'], []).append({
                'date': m['date'],
                'move_id': m['id'],
                'svl_id': False,
                'reference': m['picking_name'] or m['reference'] or '',
                'picking_id': m['picking_id'],
                'origin': m['origin'] or '',
                'picking_type_code': m['picking_type_code'],
                'description': False,
                'account_move_id': m['account_move_id'],
                'location_id': m['location_id'],
                'location_dest_id': m['location_dest_id'],
                'qty_in': qty if incoming else 0.0,
                'qty_out': qty if not incoming else 0.0,
                'value_in': currency.round(value_in),
                'value_out': currency.round(value_out),
            })
        return result

    @staticmethod
    def _naive(dt):
        """ UTC datetime without timezone, as Odoo stores datetime columns. """
        return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt

    def _get_transit_location_ids(self, company_id):
        """ The 157 locations: flagged "Kho 157 (GBQK)", and the transit
        locations of the GBQK periods (when the module is installed). """
        if 'gia.binh.quan.ky' not in self.env:
            return set()
        periods = self.env['gia.binh.quan.ky'].sudo().search([('company_id', '=', company_id)])
        result = set(periods.mapped('transit_location_ids').ids)
        Location = self.env['stock.location'].sudo().with_context(active_test=False)
        if 'gbqk_exclude_valuation' in Location._fields:
            result |= set(Location.search([
                ('gbqk_exclude_valuation', '=', True),
                ('company_id', '=', company_id),
            ]).ids)
        return result

    def _get_valued_running_avg(self, company_id, product_ids):
        """ Function f(product_id, date) -> average unit value of the valued
        moves of the company (is_in / is_out) until date, None when there is
        none. For the internal transfers without GBQK data. """
        self.env.cr.execute("""
            SELECT sm.product_id, sm.date,
                   CASE WHEN sm.is_in THEN {qty} ELSE -{qty} END,
                   CASE WHEN sm.is_in THEN ABS(sm.value) ELSE -ABS(sm.value) END
            FROM stock_move sm
            {uom_join}
            WHERE sm.state = 'done'
              AND sm.company_id = %s AND sm.product_id IN %s
              AND (sm.is_in OR sm.is_out)
            ORDER BY sm.product_id, sm.date, sm.id
        """.format(qty=_SQL_QTY, uom_join=_SQL_UOM_JOIN), (company_id, tuple(product_ids)))
        series = {}
        for pid, date, qty, value in self.env.cr.fetchall():
            dates, cum = series.setdefault(pid, ([], []))
            q, v = cum[-1] if cum else (0.0, 0.0)
            dates.append(date)
            cum.append((q + (qty or 0.0), v + (value or 0.0)))

        def running_avg(product_id, date):
            data = series.get(product_id)
            if not data:
                return None
            idx = bisect_right(data[0], date) - 1
            # back to the last point with a positive stock (no unit value at 0)
            while idx >= 0 and data[1][idx][0] <= 0:
                idx -= 1
            if idx < 0:
                return None
            q, v = data[1][idx]
            return v / q

        return running_avg

    def _get_transit_derived_values(self, company_id, product_ids, transit_ids, known,
                                    running_avg):
        """ Values of the moves in and out of a 157 location that have none:
        FIFO matching of the moves in and out of 157 by date, for each 157
        location and product.

        A move has a value when it is in `known` (GBQK batch or consumption) or
        is valued by Odoo (is_in / is_out -> |move.value|: stock <-> 157 with
        the flag, sale from 157 without it). The others:

        - into 157 (stock -> 157 without the flag, value 0): matched with the
          valued moves out of 157, at their unit value (goods all gone out of
          157 leave no value); the part not matched (still in 157) at the
          average valuation at the date of the transfer;
        - out of 157 (157 -> stock without the flag; 157 -> customer with the
          flag before GBQK is applied): the value of the lots in, FIFO; a lot
          without value takes, as the move out, the average valuation at the
          date of the move out; a missing lot too.

        :return: {move_id: value} for the moves that had none
        """
        if not transit_ids:
            return {}
        self.env.cr.execute("""
            SELECT sm.id, sm.product_id, sm.date, sm.location_id, sm.location_dest_id,
                   {qty} AS product_qty, sm.value, (sm.is_in OR sm.is_out) AS valued
            FROM stock_move sm
            {uom_join}
            WHERE sm.state = 'done'
              AND sm.company_id = %(company_id)s
              AND sm.product_id IN %(product_ids)s
              AND ((sm.location_id IN %(transit)s) <> (sm.location_dest_id IN %(transit)s))
            ORDER BY sm.date, sm.id
        """.format(qty=_SQL_QTY, uom_join=_SQL_UOM_JOIN), {
            'company_id': company_id, 'product_ids': tuple(product_ids),
            'transit': tuple(transit_ids)})
        # fetch now: precision_get may run a query on the same cursor
        rows = self.env.cr.dictfetchall()
        prec_qty = self.env['decimal.precision'].precision_get('Product Unit')
        derived = {}
        lots = {}         # (product, loc) -> [[move_id, qty left, value left | None, date], ...]
        pending_out = {}  # (product, loc) -> [[unit value, qty left], ...] (out before any lot in)

        def add(move_id, value):
            derived[move_id] = derived.get(move_id, 0.0) + value

        def is_zero(qty):
            return float_is_zero(qty, precision_digits=prec_qty)

        for m in rows:
            qty = m['product_qty'] or 0.0
            if is_zero(qty):
                continue
            value = known.get(m['id'])
            if value is None and m['valued']:
                value = abs(m['value'] or 0.0)

            if m['location_dest_id'] in transit_ids:
                key = (m['product_id'], m['location_dest_id'])
                if value is not None:
                    lots.setdefault(key, []).append([m['id'], qty, value, m['date']])
                    continue
                add(m['id'], 0.0)
                outs = pending_out.get(key, [])
                while outs and not is_zero(qty):
                    take = min(qty, outs[0][1])
                    add(m['id'], take * outs[0][0])
                    outs[0][1] -= take
                    qty -= take
                    if is_zero(outs[0][1]):
                        outs.pop(0)
                if not is_zero(qty):
                    lots.setdefault(key, []).append([m['id'], qty, None, m['date']])
                continue

            key = (m['product_id'], m['location_id'])
            ins = lots.get(key, [])
            if value is not None:
                unit = value / qty
                while ins and not is_zero(qty):
                    lot = ins[0]
                    take = min(qty, lot[1])
                    if lot[2] is None:
                        add(lot[0], take * unit)
                    else:
                        lot[2] -= lot[2] if is_zero(lot[1] - take) else lot[2] * take / lot[1]
                    lot[1] -= take
                    qty -= take
                    if is_zero(lot[1]):
                        ins.pop(0)
                if not is_zero(qty):
                    pending_out.setdefault(key, []).append([unit, qty])
                continue

            avg = running_avg(m['product_id'], m['date']) or 0.0
            out_value = 0.0
            while ins and not is_zero(qty):
                lot = ins[0]
                take = min(qty, lot[1])
                if lot[2] is None:
                    add(lot[0], take * avg)
                    out_value += take * avg
                else:
                    v = lot[2] if is_zero(lot[1] - take) else lot[2] * take / lot[1]
                    lot[2] -= v
                    out_value += v
                lot[1] -= take
                qty -= take
                if is_zero(lot[1]):
                    ins.pop(0)
            if not is_zero(qty):
                out_value += qty * avg
            add(m['id'], out_value)

        for (product_id, _loc), ins in lots.items():
            for move_id, qty, value, date in ins:
                if value is None:
                    add(move_id, qty * (running_avg(product_id, date) or 0.0))
        return derived

    def _get_internal_move_valuer(self, company_id, product_ids, moves):
        """ Function valuing the moves Odoo does not value: f(move_row) ->
        positive value. In this order: GBQK batch or consumption; FIFO
        matching of the 157 locations without GBQK data
        (_get_transit_derived_values); GBQK average cost of the period holding
        the date of the move; average valuation at that date; price_unit;
        current cost. The GBQK data is read as superuser: a stock user may not
        read it.
        """
        internal_ids = [m['id'] for m in moves if not m['valued']]
        known = {}
        avg_periods = {}
        derived = {}
        running_avg = self._get_valued_running_avg(company_id, product_ids) if internal_ids else None
        prec_qty = self.env['decimal.precision'].precision_get('Product Unit')
        # batches linked to their move, with values: GBQK 19.0.1.2.0 and later
        batch_by_move = False
        if 'gia.binh.quan.ky.transit.batch' in self.env:
            Batch = self.env['gia.binh.quan.ky.transit.batch'].sudo()
            Consumption = self.env['gia.binh.quan.ky.transit.consumption'].sudo()
            batch_by_move = ('value_in' in Batch._fields and 'stock_move_id' in Batch._fields
                             and 'value' in Consumption._fields)
        if internal_ids and batch_by_move:
            # GBQK values of every move in or out of 157, the whole history:
            # the FIFO matching needs it
            for b in Batch.search([
                    ('product_id', 'in', list(product_ids)),
                    ('company_id', '=', company_id),
                    ('stock_move_id', '!=', False)]):
                known[b.stock_move_id.id] = b.value_in
            consumed = {}
            for c in Consumption.search([
                    ('batch_id.product_id', 'in', list(product_ids)),
                    ('batch_id.company_id', '=', company_id),
                    ('stock_move_id', '!=', False)]):
                move = c.stock_move_id
                q, v = consumed.get(move, (0.0, 0.0))
                consumed[move] = (q + c.qty, v + c.value)
            for move, (c_qty, c_value) in consumed.items():
                shortfall = move.uom_id._compute_quantity(
                    move.quantity, move.product_id.uom_id, round=False) - c_qty
                if not float_is_zero(shortfall, precision_digits=prec_qty):
                    c_value += shortfall * abs(move.price_unit or 0.0)
                known[move.id] = c_value
        if internal_ids:
            derived = self._get_transit_derived_values(
                company_id, product_ids, self._get_transit_location_ids(company_id),
                known, running_avg)
        if internal_ids and 'gia.binh.quan.ky.line' in self.env:
            lines = self.env['gia.binh.quan.ky.line'].sudo().search([
                ('product_id', 'in', list(product_ids)),
                ('period_id.company_id', '=', company_id),
                ('period_id.state', 'in', ('applied', 'locked')),
            ])
            for line in lines:
                avg_periods.setdefault(line.product_id.id, []).append(
                    (line.period_id.date_start, line.period_id.date_end, line.avg_cost))
            for periods in avg_periods.values():
                periods.sort()

        tz = ZoneInfo(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        products = self.env['product.product'].with_company(company_id).with_context(
            active_test=False).browse(list(product_ids))
        std_price = {p.id: p.standard_price for p in products}

        def period_avg(m):
            periods = avg_periods.get(m['product_id'])
            if not periods:
                return None
            local_date = m['date'].replace(tzinfo=UTC).astimezone(tz).date()
            idx = bisect_right([p[0] for p in periods], local_date) - 1
            if idx >= 0 and periods[idx][0] <= local_date <= periods[idx][1]:
                return periods[idx][2]
            return None

        def valuer(m):
            qty = m['product_qty'] or 0.0
            if m['id'] in known:
                return known[m['id']]
            if m['id'] in derived:
                return derived[m['id']]
            avg = period_avg(m)
            if avg:
                return qty * avg
            avg = running_avg(m['product_id'], m['date'])
            if avg:
                return qty * avg
            if m['price_unit']:
                return qty * abs(m['price_unit'])
            return qty * std_price.get(m['product_id'], 0.0)

        return valuer

    def _summarize(self, entries, date_from_utc):
        """ Opening, receipts, deliveries and closing of a list of entries. """
        date_from_utc = self._naive(date_from_utc)
        res = dict(opening_qty=0.0, opening_value=0.0, in_qty=0.0, in_value=0.0,
                   out_qty=0.0, out_value=0.0)
        for e in entries:
            if e['date'] < date_from_utc:
                res['opening_qty'] += e['qty_in'] - e['qty_out']
                res['opening_value'] += e['value_in'] - e['value_out']
            else:
                res['in_qty'] += e['qty_in']
                res['in_value'] += e['value_in']
                res['out_qty'] += e['qty_out']
                res['out_value'] += e['value_out']
        res['closing_qty'] = res['opening_qty'] + res['in_qty'] - res['out_qty']
        res['closing_value'] = res['opening_value'] + res['in_value'] - res['out_value']
        return res
