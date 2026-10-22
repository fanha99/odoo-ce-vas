from odoo import _, fields, models


class THTKWizard(models.TransientModel):
    """ Parameters of the stock summary. """
    _name = 'vn.report.thtk.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'Stock Summary Wizard'

    product_ids = fields.Many2many(
        'product.product',
        string="Products",
        domain="[('is_storable', '=', True)]",
        help="Leave empty for all the products.",
    )
    category_ids = fields.Many2many(
        'product.category',
        string="Product Categories",
        help="The selected categories and their subcategories. Leave empty for all the categories.",
    )
    location_ids = fields.Many2many(
        'stock.location',
        string="Locations",
        domain="[('usage', '=', 'internal')]",
        help="Stock of the selected locations and their sublocations. Leave empty for the company.",
    )
    group_by_location = fields.Boolean(
        string="Group by Location",
        help="One table per internal location, sublocations apart.",
    )

    def _get_report_action_tag(self):
        return 'vn_report_thtk'

    def _get_report_name(self):
        return _("Stock Summary")

    def _get_report_model(self):
        return 'vn.report.thtk'

    def _default_orientation(self):
        return 'landscape'

    def _get_report_options(self):
        options = super()._get_report_options()
        options.update({
            'product_ids': self.product_ids.ids,
            'category_ids': self.category_ids.ids,
            'location_ids': self.location_ids.ids,
            'group_by_location': self.group_by_location,
        })
        return options
