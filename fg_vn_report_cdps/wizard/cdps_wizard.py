from odoo import _, fields, models
from odoo.exceptions import UserError


class CDPSReportWizard(models.TransientModel):
    """ Parameters of the trial balance. """
    _name = 'vn.report.cdps.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'Trial Balance Wizard'

    account_ids = fields.Many2many(
        'account.account',
        string="Accounts",
        check_company=True,
        help="Leave empty for all the accounts.",
    )
    comparison_type = fields.Selection([
        ('none', "No comparison"),
        ('previous_period', "Previous period"),
        ('same_period_last_year', "Same period last year"),
        ('custom', "Custom period"),
    ], string="Compare With", default='none', required=True)
    comparison_date_from = fields.Date(string="Compared From")
    comparison_date_to = fields.Date(string="Compared To")
    show_zero_balance = fields.Boolean(string="Show Accounts Without Figures")
    hierarchy = fields.Boolean(
        string="Account Hierarchy",
        help="Arrange the accounts along their parent accounts.",
    )

    def _default_orientation(self):
        return 'landscape'

    def _get_report_action_tag(self):
        return 'vn_report_cdps'

    def _get_report_name(self):
        return _("Trial Balance")

    def _get_report_model(self):
        return 'vn.report.cdps'

    def _check_report_dates(self):
        super()._check_report_dates()
        if self.comparison_type == 'custom':
            if not self.comparison_date_from or not self.comparison_date_to:
                raise UserError(_("Please set the start and end dates of the compared period."))
            if self.comparison_date_from > self.comparison_date_to:
                raise UserError(_("The start date of the compared period must be before its end date."))

    def _get_report_options(self):
        options = super()._get_report_options()
        options.update({
            'account_ids': self.account_ids.ids,
            'comparison_type': self.comparison_type,
            'comparison_date_from': fields.Date.to_string(self.comparison_date_from),
            'comparison_date_to': fields.Date.to_string(self.comparison_date_to),
            'show_zero_balance': self.show_zero_balance,
            'hierarchy': self.hierarchy,
        })
        return options

    def action_export_xml(self):
        """ Download the XML appendix F01-CDTK straight from the wizard. """
        return self._get_export_action('xml')
