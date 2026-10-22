{
    'name': 'Vietnam - Stock Reports (S06-DNN, Stock Summary)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Detailed stock ledger S06-DNN and stock in/out/balance summary of the Vietnamese accounting system',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - Stock Reports (S06-DNN, Stock Summary)
================================================

* S06-DNN: detailed ledger of materials, tools, products and goods, one
  ledger per product
* Stock summary: opening, in, out and closing quantities and values per
  product, optionally per location

With selected locations, the values are those of the moves crossing the
boundary of these locations. The 157 location (goods sent for sale, flag
"Kho 157 (GBQK)") is valued with the batches of the Periodic Average Cost
module when it is installed. See HUONG_DAN_KHO_157.md and readme.md in the
module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': [
        'stock_account',
        'fg_vn_accounting_reports',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/s06_wizard_views.xml',
        'wizard/thtk_wizard_views.xml',
        'views/stock_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_vn_stock_reports/static/src/js/s06_report.js',
            'fg_vn_stock_reports/static/src/js/thtk_report.js',
        ],
    },
    'installable': True,
}
