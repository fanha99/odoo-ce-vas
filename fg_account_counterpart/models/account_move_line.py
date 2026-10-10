from odoo import api, fields, models

COUNTERED_STATUS = [
    ('none', "Not Countered"),
    ('partially', "Partially Countered"),
    ('fully', "Fully Countered"),
]
NON_ACCOUNTABLE_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ctp_dr_ids = fields.One2many(
        comodel_name='account.move.line.ctp', inverse_name='dr_aml_id',
        string="Counterparts (as debit item)", readonly=True,
    )
    ctp_cr_ids = fields.One2many(
        comodel_name='account.move.line.ctp', inverse_name='cr_aml_id',
        string="Counterparts (as credit item)", readonly=True,
    )
    countered_aml_ids = fields.Many2many(
        comodel_name='account.move.line',
        relation='account_move_line_countered_rel', column1='aml_id', column2='countered_aml_id',
        string="Countered Journal Items",
        compute='_compute_countered', store=True,
        help="The journal items that are counterparts of this journal item.",
    )
    countered_account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='account_move_line_countered_account_rel', column1='aml_id', column2='account_id',
        string="Countered Accounts",
        compute='_compute_countered', store=True,
        help="The accounts that are counterparts of the account of this journal item.",
    )
    countered_amt = fields.Monetary(
        string="Countered Amount",
        currency_field='company_currency_id',
        compute='_compute_countered', store=True,
        help="The amount of this journal item that has been matched with counterparts.",
    )
    countered_status = fields.Selection(
        selection=COUNTERED_STATUS,
        string="Countered Status",
        compute='_compute_countered', store=True, index=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends(
        'debit', 'credit', 'display_type',
        'ctp_dr_ids.countered_amt', 'ctp_dr_ids.cr_aml_id.account_id',
        'ctp_cr_ids.countered_amt', 'ctp_cr_ids.dr_aml_id.account_id',
    )
    def _compute_countered(self):
        """ Derive the four counterpart fields from the `account.move.line.ctp`
        records of the item:

        - countered_aml_ids: the items on the other end of its counterparts;
        - countered_account_ids: the accounts of those items;
        - countered_amt: the sum of the countered amounts;
        - countered_status: 'fully' when countered_amt equals the amount to
          counter, 'none' when there is no counterpart, 'partially' otherwise.
          An item with nothing to counter (zero amount, section, note) is
          'fully' countered.

        TODO(phase 2): the skeleton only resets the fields.
        """
        for line in self:
            line.countered_aml_ids = False
            line.countered_account_ids = False
            line.countered_amt = 0.0
            line.countered_status = 'none' if line._ctp_is_counterable() else 'fully'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _ctp_is_counterable(self):
        """ Return whether the item takes part in counterparts: it is an
        accounting item (not a section/subsection/note) with a non-zero amount.

        TODO(phase 1)
        """
        self.ensure_one()
        return self.display_type not in NON_ACCOUNTABLE_DISPLAY_TYPES and bool(self.debit or self.credit)

    def _ctp_side(self):
        """ Return 'dr', 'cr' or False (not counterable).

        The side comes from the column that is filled in, not from the sign of
        the balance: a storno item keeps its side with a negative amount.

        TODO(phase 1)
        """
        self.ensure_one()
        if not self._ctp_is_counterable():
            return False
        return 'dr' if self.debit else 'cr'

    def _ctp_amount(self):
        """ Return the signed amount to counter on the item's own side (its
        debit or its credit, negative for a storno item).

        TODO(phase 1)
        """
        self.ensure_one()
        return self.debit or self.credit

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def _get_counterparts(self):
        """ Return the counterparts of the items, seen from each item.

        Entry point for other modules (ledgers, cash flow statement, ...): they
        get the countered account and amount without caring whether the item
        is on the debit or on the credit side.

        :return: {item id: [counterpart, ...]}, every item of `self` being a
            key, with an empty list when it has no counterpart.  A counterpart
            is a dict:

            - `aml`: the countered journal item (account.move.line)
            - `account`: its account (account.account)
            - `amount`: the countered amount, in company currency
            - `amount_currency`: the countered amount in foreign currency

            Counterparts are ordered by the id of the countered item.

        E.g. for the receivable item of an invoice Dr 131 110 / Cr 511 100,
        Cr 33311 10: [{account: 511, amount: 100}, {account: 33311, amount: 10}].
        """
        result = {line.id: [] for line in self}
        for line in self:
            for ctp in line.ctp_dr_ids:
                result[line.id].append(ctp._get_counterpart_values(ctp.cr_aml_id))
            for ctp in line.ctp_cr_ids:
                result[line.id].append(ctp._get_counterpart_values(ctp.dr_aml_id))
            result[line.id].sort(key=lambda values: values['aml'].id)
        return result

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_view_counterparts(self):
        """ Open the `account.move.line.ctp` records of the selected items.

        TODO(phase 4)
        """
        action = self.env['ir.actions.act_window']._for_xml_id(
            'fg_account_counterpart.account_move_line_ctp_action')
        action['domain'] = ['|', ('dr_aml_id', 'in', self.ids), ('cr_aml_id', 'in', self.ids)]
        return action
