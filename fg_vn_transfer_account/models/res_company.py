from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    fg_hide_transfer_account = fields.Boolean(
        string="Hide Transfer Accounts Without Balance",
        help="Hide the selected transfer accounts on the accounting books and printouts "
             "when they have no balance. The journal entries are not modified.",
    )
    fg_hidden_transfer_account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='fg_hidden_transfer_account_company_rel',
        column1='company_id',
        column2='account_id',
        string="Hidden Transfer Accounts",
        check_company=True,
        help="Accounts hidden when they have no balance.",
    )

    @api.constrains('fg_hidden_transfer_account_ids')
    def _check_fg_hidden_transfer_account_ids(self):
        # res.company has no _check_company_auto
        self._check_company(['fg_hidden_transfer_account_ids'])

    def _fg_get_hidden_transfer_accounts(self):
        """ Return the accounts the accounting books must hide when they have
        no balance. Empty when the setting is off.

        :rtype: account.account recordset
        """
        self.ensure_one()
        if not self.fg_hide_transfer_account:
            return self.env['account.account']
        return self.fg_hidden_transfer_account_ids

    def _fg_fill_hidden_transfer_accounts(self):
        """ Select the inter-banks transfer account on the companies that have
        the setting on but no account selected. Before 20.0 the setting had no
        account list and always applied to that single account.
        """
        for company in self:
            if (
                company.fg_hide_transfer_account
                and not company.fg_hidden_transfer_account_ids
                and company.transfer_account_id
            ):
                company.fg_hidden_transfer_account_ids = company.transfer_account_id
