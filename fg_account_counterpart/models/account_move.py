from odoo import api, fields, models

from .account_move_line import COUNTERED_STATUS


class AccountMove(models.Model):
    _inherit = 'account.move'

    countered_status = fields.Selection(
        selection=COUNTERED_STATUS,
        string="Countered Status",
        compute='_compute_countered_status', store=True, index=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('state', 'line_ids.countered_status', 'line_ids.debit', 'line_ids.credit', 'line_ids.display_type')
    def _compute_countered_status(self):
        """ 'fully' when every counterable item is fully countered, 'none' when
        none of them has a counterpart, 'partially' otherwise.

        A posted entry with nothing to counter is 'fully' countered.
        """
        for move in self:
            lines = move.line_ids.filtered(lambda line: line._ctp_is_counterable())
            statuses = set(lines.mapped('countered_status'))
            if not lines:
                move.countered_status = 'fully' if move.state == 'posted' else 'none'
            elif statuses == {'fully'}:
                move.countered_status = 'fully'
            elif statuses == {'none'}:
                move.countered_status = 'none'
            else:
                move.countered_status = 'partially'

    # -------------------------------------------------------------------------
    # LIFECYCLE HOOKS
    # -------------------------------------------------------------------------

    def _post(self, soft=True):
        """ Generate the counterparts of the entries that have just been posted. """
        posted = super()._post(soft=soft)
        posted._ctp_generate()
        return posted

    def button_draft(self):
        """ The items of a draft entry can change: drop their counterparts. """
        res = super().button_draft()
        self._ctp_remove()
        return res

    # -------------------------------------------------------------------------
    # COUNTERPART ENGINE
    # -------------------------------------------------------------------------

    def _ctp_generate(self, regenerate=False):
        """ Create the `account.move.line.ctp` records of the posted entries in
        `self`, in a single batch `create`.

        :param bool regenerate: also process the entries that are already
            fully countered.  Otherwise only the entries that are not fully
            countered are processed; their counterparts, if any, are replaced.
        :return: the created counterparts

        Runs in sudo: counterparts are technical records created on behalf of
        whoever posts the entry.
        """
        moves = self.filtered(lambda move: move.state == 'posted')
        if not regenerate:
            moves = moves.filtered(lambda move: move.countered_status != 'fully')
        moves._ctp_remove()
        vals_list = []
        for move in moves:
            vals_list += move._ctp_prepare_vals_list()
        return self.env['account.move.line.ctp'].sudo().create(vals_list)

    def _ctp_remove(self):
        """ Delete all the counterparts of the entries in `self`. """
        if self.ids:
            self.env['account.move.line.ctp'].sudo().search([('move_id', 'in', self.ids)]).unlink()

    def _ctp_prepare_vals_list(self):
        """ Return the `create` values of the counterparts of one entry.

        Orders the counterable items by id, splits them into debit and credit
        items, then delegates the matching to `_ctp_allocate`.

        TODO(storno): entries with negative debit/credit items are on hold.
        The matching rule for them is not decided yet; until it is, such an
        entry gets no counterpart and stays 'none'.
        """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line._ctp_is_counterable()).sorted('id')
        if any(line._ctp_amount() < 0 for line in lines):
            return []
        dr_items = []
        cr_items = []
        for line in lines:
            amount = line._ctp_amount()
            amount_currency = abs(line.amount_currency)
            item = {
                'id': line.id,
                'partner_id': line.partner_id.id,
                'currency': line.currency_id,
                'amount': amount,
                'amount_currency': amount_currency,
                'residual': amount,
                'residual_currency': amount_currency,
            }
            if line._ctp_side() == 'dr':
                dr_items.append(item)
            else:
                cr_items.append(item)
        return self._ctp_allocate(dr_items, cr_items, self.company_currency_id)

    @api.model
    def _ctp_allocate(self, dr_items, cr_items, currency):
        """ Match debit items with credit items in three passes.

        :param list dr_items: the debit items by ascending id, as dicts with
            the keys `id`, `partner_id`, `currency` (of the item), `amount`,
            `amount_currency`, and the running `residual` and
            `residual_currency`.  Residuals are updated in place.
        :param list cr_items: the credit items, same structure
        :param currency: the company currency
        :return: list of dicts `dr_aml_id`, `cr_aml_id`, `countered_amt`,
            `countered_amt_currency`

        Each pass goes through the debit items by ascending id:

        1. same amount and same partner (or both without partner): matched one
           to one with the first credit item that qualifies
           (`_ctp_find_exact_match`);
        2. same partner (or both without partner): the debit residual is
           distributed pro rata over the credit items of that partner;
        3. whatever the partner: the debit residual is distributed pro rata
           over every credit item not fully countered.

        Passes 2 and 3 share `_ctp_distribute`.

        TODO(storno): only positive amounts are supported; negative (storno)
        items are filtered out by the caller until their rule is decided.
        """
        pairs = {}

        def add(vals_list):
            # A pair matched in two passes is stored once, with the total.
            for vals in vals_list:
                key = (vals['dr_aml_id'], vals['cr_aml_id'])
                if key in pairs:
                    pairs[key]['countered_amt'] += vals['countered_amt']
                    pairs[key]['countered_amt_currency'] += vals['countered_amt_currency']
                else:
                    pairs[key] = vals

        def has_residual(item):
            return not currency.is_zero(item['residual'])

        # Pass 1: one to one
        for dr_item in dr_items:
            cr_item = self._ctp_find_exact_match(dr_item, cr_items, currency)
            if cr_item:
                add([{
                    'dr_aml_id': dr_item['id'],
                    'cr_aml_id': cr_item['id'],
                    'countered_amt': dr_item['residual'],
                    'countered_amt_currency': dr_item['residual_currency'],
                }])
                for item in (dr_item, cr_item):
                    item['residual'] = item['residual_currency'] = 0.0

        # Pass 2: pro rata within the partner
        for dr_item in filter(has_residual, dr_items):
            group = [
                cr_item for cr_item in cr_items
                if has_residual(cr_item) and cr_item['partner_id'] == dr_item['partner_id']
            ]
            add(self._ctp_distribute(dr_item, group, currency))

        # Pass 3: pro rata over what is left
        for dr_item in filter(has_residual, dr_items):
            group = [cr_item for cr_item in cr_items if has_residual(cr_item)]
            add(self._ctp_distribute(dr_item, group, currency))

        return list(pairs.values())

    @api.model
    def _ctp_find_exact_match(self, dr_item, cr_items, currency):
        """ Pass 1: return the credit item to match one to one with `dr_item`,
        or None.

        It is the first credit item with a residual that has the same amount
        and the same partner (or both without partner).  Exception, checked
        first: when the first remaining credit item has an id adjacent (+/-1)
        to the debit item and the same amount, it is returned whatever its
        partner.
        """
        def same_amount(cr_item):
            return currency.compare_amounts(cr_item['residual'], dr_item['residual']) == 0

        remaining = [cr_item for cr_item in cr_items if not currency.is_zero(cr_item['residual'])]
        if not remaining or currency.is_zero(dr_item['residual']):
            return None
        first = remaining[0]
        if abs(first['id'] - dr_item['id']) == 1 and same_amount(first):
            return first
        return next((
            cr_item for cr_item in remaining
            if cr_item['partner_id'] == dr_item['partner_id'] and same_amount(cr_item)
        ), None)

    @api.model
    def _ctp_distribute(self, dr_item, cr_items, currency):
        """ Passes 2 and 3: distribute the residual of `dr_item` pro rata over
        `cr_items`, update the residuals and return the counterpart values.

        amount = min(debit residual, total credit residual)
                 * credit residual of the item / total credit residual

        Amounts are rounded with the currency; the rounding difference goes to
        the last credit item.

        The amount in foreign currency is computed alongside with the same
        formula on the residuals in currency.  That only makes sense when the
        credit items share the currency of the debit item; otherwise the
        amount in currency of the debit item is split like its amount in
        company currency.
        """
        total = sum(cr_item['residual'] for cr_item in cr_items)
        if not cr_items or currency.is_zero(total):
            return []
        dr_currency = dr_item['currency'] or currency
        same_currency = all(cr_item['currency'] == dr_item['currency'] for cr_item in cr_items)
        total_currency = sum(cr_item['residual_currency'] for cr_item in cr_items)

        to_allocate = min(dr_item['residual'], total)
        if same_currency:
            to_allocate_currency = min(dr_item['residual_currency'], total_currency)
        else:
            to_allocate_currency = dr_currency.round(
                dr_item['residual_currency'] * to_allocate / dr_item['residual'])

        vals_list = []
        left = to_allocate
        left_currency = to_allocate_currency
        for cr_item in cr_items:
            if cr_item is cr_items[-1]:
                amount = left
                amount_currency = left_currency
            else:
                amount = currency.round(to_allocate * cr_item['residual'] / total)
                if same_currency and total_currency:
                    ratio = cr_item['residual_currency'] / total_currency
                else:
                    ratio = cr_item['residual'] / total
                amount_currency = dr_currency.round(to_allocate_currency * ratio)
            left = currency.round(left - amount)
            left_currency = dr_currency.round(left_currency - amount_currency)
            for item in (dr_item, cr_item):
                item['residual'] = currency.round(item['residual'] - amount)
                item['residual_currency'] = max(
                    dr_currency.round(item['residual_currency'] - amount_currency), 0.0)
            if not currency.is_zero(amount):
                vals_list.append({
                    'dr_aml_id': dr_item['id'],
                    'cr_aml_id': cr_item['id'],
                    'countered_amt': amount,
                    'countered_amt_currency': amount_currency,
                })
        return vals_list

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_ctp_regenerate(self):
        """ Regenerate the counterparts of the selected posted entries.

        TODO(phase 4)
        """
        self.filtered(lambda move: move.state == 'posted')._ctp_generate(regenerate=True)

    def action_view_counterparts(self):
        """ Open the counterparts of the selected entries.

        TODO(phase 4)
        """
        action = self.env['ir.actions.act_window']._for_xml_id(
            'fg_account_counterpart.account_move_line_ctp_action')
        action['domain'] = [('move_id', 'in', self.ids)]
        return action
