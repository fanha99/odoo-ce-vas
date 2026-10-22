from odoo import _, fields, models


class S06ReportWizard(models.TransientModel):
    """ Parameters of the detailed stock ledger S06-DNN. """
    _name = 'vn.report.s06.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'Detailed Stock Ledger Wizard'

    product_ids = fields.Many2many(
        'product.product',
        string="Products",
        domain=[('is_storable', '=', True)],
        help="Leave empty for all the products.",
    )
    category_ids = fields.Many2many(
        'product.category',
        string="Product Categories",
        help="Leave empty for all the categories.",
    )
    location_ids = fields.Many2many(
        'stock.location',
        string="Locations",
        domain=[('usage', '=', 'internal')],
        help="Ledger of the selected locations and their sublocations, with the internal "
             "transfers crossing their boundary. Leave empty for the ledger of the company.",
    )
    account_ids = fields.Many2many(
        'account.account',
        string="Accounts",
        domain="[('code', '=like', '15%')]",
        help="Only the products whose stock valuation account is selected. "
             "Leave empty for the accounts 152, 153, 155 and 156.",
    )

    def _get_report_action_tag(self):
        return 'vn_report_s06'

    def _get_report_name(self):
        return _("Detailed Stock Ledger (S06-DNN)")

    def _get_report_model(self):
        return 'vn.report.s06'

    def _default_orientation(self):
        return 'landscape'

    def _get_report_options(self):
        options = super()._get_report_options()
        options.update({
            'product_ids': self.product_ids.ids,
            'category_ids': self.category_ids.ids,
            'location_ids': self.location_ids.ids,
            'account_ids': self.account_ids.ids,
        })
        return options
