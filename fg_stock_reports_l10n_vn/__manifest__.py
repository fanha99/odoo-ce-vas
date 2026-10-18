{
    'name': 'Vietnam Stock Valuation Reports',
    'version': '17.0.1.0.5',
    'category': 'Fanha Addons/Stock/Reporting',
    'summary': 'Vietnam Stock Valuation Reports - Stock Valuation Layer Report',
    'description': '''
        This module adds Vietnamese localized stock valuation reports to Odoo.
        Features:
        - Stock Valuation Layer Report with opening and closing inventory
        - Customizable stock report based on stock movements
        - Access restricted to Stock Manager group
        - Custom PDF styling with alternating row colors
    ''',
    'author': 'Fanha Giang',
    'depends': ['stock_account', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/pdf_export_templates.xml',
        'data/stock_valuation_layer_report.xml',
        'data/menuitems.xml',
    ],
    'assets': {
        'account_reports.assets_pdf_export': [
            'fg_stock_reports_l10n_vn/static/src/scss/stock_valuation_report_pdf.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
