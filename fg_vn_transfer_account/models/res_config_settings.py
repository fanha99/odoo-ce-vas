from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fg_hide_transfer_account = fields.Boolean(
        related='company_id.fg_hide_transfer_account',
        readonly=False,
    )
    fg_hidden_transfer_account_ids = fields.Many2many(
        related='company_id.fg_hidden_transfer_account_ids',
        readonly=False,
        check_company=True,
    )

    @api.onchange('fg_hide_transfer_account')
    def _onchange_fg_hide_transfer_account(self):
        if self.fg_hide_transfer_account and not self.fg_hidden_transfer_account_ids:
            self.fg_hidden_transfer_account_ids = self.transfer_account_id
