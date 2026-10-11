from odoo import _, fields, models


class S03bReportWizard(models.TransientModel):
    """ Parameters of the general ledger. """
    _name = 'vn.report.s03b.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'General Ledger Wizard'

    # the ledger is usually read by quarter
    date_from = fields.Date(default=lambda self: self._default_date_from_quarter())
    date_to = fields.Date(default=lambda self: self._default_date_to_quarter())

    account_ids = fields.Many2many(
        'account.account',
        string="Accounts",
        check_company=True,
        help="Leave empty for all the accounts.",
    )
    account_type = fields.Selection([
        ('all', "All"),
        ('asset', "Assets"),
        ('liability', "Liabilities"),
        ('equity', "Equity"),
        ('income', "Income"),
        ('expense', "Expenses"),
    ], string="Account Type", default='all', required=True)
    partner_ids = fields.Many2many(
        'res.partner',
        string="Partners",
        help="Only the journal items of these partners are counted, in the opening balance too. "
             "Leave empty for all the partners.",
    )
    journal_ids = fields.Many2many(
        'account.journal',
        string="Journals",
        check_company=True,
        help="Only the journal items of these journals are counted, in the opening balance too. "
             "Leave empty for all the journals.",
    )
    empty_accounts = fields.Selection([
        ('hide', "Leave out"),
        ('with_balance', "Include those with an opening balance"),
        ('all', "Include all"),
    ], string="Accounts Without Journal Items", default='hide', required=True)
    split_counterparts = fields.Boolean(
        string="One Line per Counterpart Account",
        help="Split each journal item into one line per counterpart account, with the amount "
             "matched with that account.",
    )

    def _get_report_action_tag(self):
        return 'vn_report_s03b'

    def _get_report_name(self):
        return _("General Ledger")

    def _get_report_model(self):
        return 'vn.report.s03b'

    def _get_report_options(self):
        options = super()._get_report_options()
        # replaced by empty_accounts
        options.pop('show_zero_balance', None)
        options.update({
            'account_ids': self.account_ids.ids,
            'account_type': self.account_type,
            'partner_ids': self.partner_ids.ids,
            'journal_ids': self.journal_ids.ids,
            'empty_accounts': self.empty_accounts,
            'split_counterparts': self.split_counterparts,
        })
        return options
