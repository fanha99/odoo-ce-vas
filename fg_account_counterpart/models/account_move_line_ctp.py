from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import formatLang


class AccountMoveLineCtp(models.Model):
    _name = 'account.move.line.ctp'
    _description = "Journal Item Counterpart"
    _order = 'date desc, move_id desc, id'
    _rec_name = 'move_id'

    dr_aml_id = fields.Many2one(
        comodel_name='account.move.line',
        string="Debit Journal Item",
        required=True, index=True, ondelete='cascade', readonly=True,
    )
    cr_aml_id = fields.Many2one(
        comodel_name='account.move.line',
        string="Credit Journal Item",
        required=True, index=True, ondelete='cascade', readonly=True,
    )
    countered_amt = fields.Monetary(
        string="Countered Amount",
        currency_field='company_currency_id', readonly=True,
        help="Amount, in company currency, of the debit item that is matched with the credit item.",
    )
    countered_amt_currency = fields.Monetary(
        string="Countered Amount in Currency",
        currency_field='currency_id', readonly=True,
        help="The countered amount expressed in the currency of the debit journal item.",
    )
    currency_id = fields.Many2one(related='dr_aml_id.currency_id', store=True)

    # Denormalized for reporting (pivot / group by account pair) and record rules.
    move_id = fields.Many2one(related='dr_aml_id.move_id', store=True, index=True)
    date = fields.Date(related='dr_aml_id.date', store=True, index=True)
    journal_id = fields.Many2one(related='dr_aml_id.journal_id', store=True)
    company_id = fields.Many2one(related='dr_aml_id.company_id', store=True, index=True)
    company_currency_id = fields.Many2one(related='dr_aml_id.company_currency_id', store=True)
    dr_account_id = fields.Many2one(
        related='dr_aml_id.account_id', string="Debit Account", store=True, index=True,
    )
    cr_account_id = fields.Many2one(
        related='cr_aml_id.account_id', string="Credit Account", store=True, index=True,
    )

    _check_distinct_items = models.Constraint(
        'CHECK(dr_aml_id != cr_aml_id)',
        "A journal item cannot be the counterpart of itself.",
    )
    _check_countered_amt = models.Constraint(
        'CHECK(countered_amt != 0)',
        "The countered amount of a counterpart cannot be zero.",
    )
    _unique_pair = models.Constraint(
        'UNIQUE(dr_aml_id, cr_aml_id)',
        "Two journal items can only be countered once with each other.",
    )

    @api.constrains('dr_aml_id', 'cr_aml_id')
    def _check_same_move(self):
        """ Both items must belong to the same journal entry, the first one on
        the debit side and the second one on the credit side.
        """
        for ctp in self:
            if ctp.dr_aml_id.move_id != ctp.cr_aml_id.move_id:
                raise ValidationError(_("The two journal items of a counterpart must belong to the same journal entry."))
            if ctp.dr_aml_id._ctp_side() != 'dr' or ctp.cr_aml_id._ctp_side() != 'cr':
                raise ValidationError(_("A counterpart must link a debit journal item with a credit journal item."))

    def _get_counterpart_values(self, countered_aml):
        """ Return the counterpart as seen from the other item of the pair:
        the values documented in `account.move.line._get_counterparts`.

        :param countered_aml: `dr_aml_id` or `cr_aml_id` of the counterpart
        """
        self.ensure_one()
        return {
            'aml': countered_aml,
            'account': countered_aml.account_id,
            'account_code': countered_aml.account_id.with_company(countered_aml.company_id).code,
            'amount': self.countered_amt,
            'amount_currency': self.countered_amt_currency,
        }

    @api.depends('dr_account_id', 'cr_account_id', 'countered_amt')
    def _compute_display_name(self):
        """ "<debit account code> / <credit account code>: <amount>". """
        for ctp in self:
            dr_code = ctp.dr_account_id.with_company(ctp.company_id).code
            cr_code = ctp.cr_account_id.with_company(ctp.company_id).code
            amount = formatLang(self.env, ctp.countered_amt, currency_obj=ctp.company_currency_id)
            ctp.display_name = f"{dr_code} / {cr_code}: {amount}"
