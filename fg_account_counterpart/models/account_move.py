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

    @api.depends('line_ids.countered_status')
    def _compute_countered_status(self):
        """ 'fully' when every counterable item is fully countered, 'none' when
        none of them has a counterpart, 'partially' otherwise.

        TODO(phase 2): the skeleton only resets the field.
        """
        for move in self:
            move.countered_status = 'none'

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
        """ Create the missing `account.move.line.ctp` records of the posted
        entries in `self`, in a single batch `create`.

        :param bool regenerate: drop the existing counterparts first; otherwise
            entries that are already fully countered are skipped.
        :return: the created counterparts

        Runs in sudo: counterparts are technical records created on behalf of
        whoever posts the entry.

        TODO(phase 3)
        """
        return self.env['account.move.line.ctp']

    def _ctp_remove(self):
        """ Delete all the counterparts of the entries in `self`.

        TODO(phase 3)
        """

    def _ctp_prepare_vals_list(self):
        """ Return the `create` values of the counterparts of one entry.

        Orders the counterable items by id, splits them into debit and credit
        items, then delegates the matching to `_ctp_allocate`.

        TODO(storno): entries with negative debit/credit items are on hold.
        The matching rule for them is not decided yet; until it is, such an
        entry gets no counterpart and stays 'none'.

        TODO(phase 3)
        """
        self.ensure_one()
        return []

    @api.model
    def _ctp_allocate(self, dr_items, cr_items):
        """ Match debit items with credit items in three passes.

        :param list dr_items: the debit items by ascending id, as dicts with
            the keys `id`, `partner_id`, `amount`, `amount_currency`, and the
            running `residual` and `residual_currency`
        :param list cr_items: the credit items, same structure
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

        TODO(phase 3)
        """
        return []

    @api.model
    def _ctp_find_exact_match(self, dr_item, cr_items):
        """ Pass 1: return the credit item to match one to one with `dr_item`,
        or None.

        It is the first credit item with a residual that has the same amount
        and the same partner (or both without partner).  Exception: when the
        first remaining credit item has an id adjacent (+/-1) to the debit item
        and the same amount, it is returned whatever its partner.

        TODO(phase 3)
        """
        return None

    @api.model
    def _ctp_distribute(self, dr_item, cr_items):
        """ Passes 2 and 3: distribute the residual of `dr_item` pro rata over
        `cr_items`, update the residuals and return the counterpart values.

        amount = min(debit residual, total credit residual)
                 * credit residual of the item / total credit residual

        Amounts are rounded with the currency; the rounding difference goes to
        the last credit item.  The amount in foreign currency is computed
        alongside, the same way.

        TODO(phase 3)
        """
        return []

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
