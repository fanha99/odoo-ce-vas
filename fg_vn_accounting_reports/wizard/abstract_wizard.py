import json
import uuid
from calendar import monthrange
from datetime import date
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DEFAULT_REPORT_LANG = 'vi_VN'


class AbstractReportWizard(models.AbstractModel):
    """ Common part of the report wizards. A report wizard is a TransientModel
    with its own `_name` inheriting this one, and adds its own fields.
    """
    _name = 'vn.report.wizard.abstract'
    _description = 'Abstract Report Wizard'

    # ==================== COMMON FIELDS ====================

    # Defaults to the whole current month. A wizard overrides date_from and
    # date_to to default to another period (e.g. the current quarter).
    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: self._default_date_from_month(),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: self._default_date_to_month(),
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    show_zero_balance = fields.Boolean(
        string="Show Lines Without Figures",
        default=False,
    )
    report_lang = fields.Selection(
        selection='_get_report_lang_selection',
        string="Report Language",
        required=True,
        default=lambda self: self._default_report_lang(),
        help="Language the report is displayed, exported and printed in. "
             "It does not depend on the language of your interface.",
    )
    orientation = fields.Selection([
        ('landscape', "Landscape (A4)"),
        ('portrait', "Portrait (A4)"),
    ], string="Orientation", default=lambda self: self._default_orientation(), required=True)
    mirror_margin = fields.Boolean(
        string="Mirror Margins (two-sided printing)",
        default=lambda self: self._default_mirror_margin(),
    )
    gutter_mm = fields.Integer(
        string="Gutter (mm)",
        default=lambda self: self._default_gutter_mm(),
    )

    def _default_orientation(self):
        return 'portrait'

    def _default_mirror_margin(self):
        return False

    def _default_gutter_mm(self):
        return 6

    @api.model
    def _get_report_lang_selection(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _default_report_lang(self):
        """ Vietnamese when installed: the accounting books are Vietnamese
        legal forms. The choice is not remembered from one opening to the next.
        """
        installed = {code for code, _name in self._get_report_lang_selection()}
        if DEFAULT_REPORT_LANG in installed:
            return DEFAULT_REPORT_LANG
        return self.env.lang or self.env.user.lang

    # ==================== DATE RANGE DEFAULTS ====================
    # Helpers to use as `default=` of date_from/date_to in the wizards.

    @api.model
    def _default_date_from_month(self):
        return fields.Date.context_today(self).replace(day=1)

    @api.model
    def _default_date_to_month(self):
        today = fields.Date.context_today(self)
        return today.replace(day=monthrange(today.year, today.month)[1])

    @api.model
    def _default_date_from_quarter(self):
        today = fields.Date.context_today(self)
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        return date(today.year, q_start_month, 1)

    @api.model
    def _default_date_to_quarter(self):
        today = fields.Date.context_today(self)
        q_end_month = ((today.month - 1) // 3) * 3 + 3
        return date(today.year, q_end_month, monthrange(today.year, q_end_month)[1])

    # ==================== HOOKS TO OVERRIDE ====================

    def _get_report_action_tag(self):
        """ Override: tag of the client action of the report. """
        raise NotImplementedError("Subclass must implement _get_report_action_tag()")

    def _get_report_name(self):
        """ Override: displayed name of the report. """
        return _("Report")

    def _get_report_model(self):
        """ Override: name of the report model. """
        raise NotImplementedError("Subclass must implement _get_report_model()")

    def _get_report_options(self):
        """ Build the options of the report from the fields of the wizard.
        Override to add the options of the report. """
        self.ensure_one()
        return {
            'date': {
                'date_from': self.date_from.strftime('%Y-%m-%d'),
                'date_to': self.date_to.strftime('%Y-%m-%d'),
                'mode': 'range',
            },
            'company_id': self.company_id.id,
            'show_zero_balance': self.show_zero_balance,
            'lang': self.report_lang,
            'orientation': self.orientation,
            'mirror_margin': self.mirror_margin,
            'gutter_mm': self.gutter_mm,
        }

    # ==================== ACTIONS ====================

    def _check_report_dates(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The start date must be before the end date."))

    def _get_export_action(self, export_format):
        """ Return the action downloading the report in the given format, one
        of the formats of the export routes (xlsx, pdf_rl, ...). """
        self._check_report_dates()
        options = quote(json.dumps(self._get_report_options()))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/vn_report/{self._get_report_model()}/export/{export_format}?options={options}',
            'target': 'self',
        }

    def action_view_report(self):
        """ Open the report on screen with the chosen options. """
        self._check_report_dates()
        return {
            'type': 'ir.actions.client',
            'tag': self._get_report_action_tag(),
            'name': self._get_report_name(),
            'context': {
                'options': self._get_report_options(),
                # The screen keeps its state (period, filters, unfolded rows)
                # in the browser. The token tells a new opening, whose options
                # win, from the screen being restored after a drill-down.
                'report_token': uuid.uuid4().hex,
            },
        }

    def action_export_xlsx(self):
        """ Export to Excel straight from the wizard. """
        return self._get_export_action('xlsx')

    def action_export_pdf_rl(self):
        """ Export to PDF straight from the wizard. """
        return self._get_export_action('pdf_rl')
