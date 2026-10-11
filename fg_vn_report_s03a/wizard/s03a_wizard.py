from odoo import _, fields, models


class S03aReportWizard(models.TransientModel):
    """ Parameters of the general journal. """
    _name = 'vn.report.s03a.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'General Journal Wizard'

    # the journal is usually read by quarter
    date_from = fields.Date(default=lambda self: self._default_date_from_quarter())
    date_to = fields.Date(default=lambda self: self._default_date_to_quarter())

    journal_ids = fields.Many2many(
        'account.journal',
        string="Journals",
        check_company=True,
        help="Leave empty for all the journals.",
    )
    move_type = fields.Selection([
        ('all', "All"),
        ('entry', "Journal entries"),
        ('out_invoice', "Customer invoices"),
        ('in_invoice', "Vendor bills"),
        ('out_refund', "Customer credit notes"),
        ('in_refund', "Vendor credit notes"),
    ], string="Entry Type", default='all', required=True)
    account_ids = fields.Many2many(
        'account.account',
        string="Accounts",
        check_company=True,
        help="Only the journal items on these accounts are listed. Leave empty for all the accounts.",
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Partners",
        help="Only the journal items of these partners are listed. Leave empty for all the partners.",
    )

    def _get_report_action_tag(self):
        return 'vn_report_s03a'

    def _get_report_name(self):
        return _("General Journal")

    def _get_report_model(self):
        return 'vn.report.s03a'

    def _get_report_options(self):
        options = super()._get_report_options()
        options.update({
            'journal_ids': self.journal_ids.ids,
            'move_type': self.move_type,
            'account_ids': self.account_ids.ids,
            'partner_ids': self.partner_ids.ids,
        })
        return options
