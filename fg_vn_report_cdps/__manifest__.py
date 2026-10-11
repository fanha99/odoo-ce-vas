{
    'name': 'Vietnam - Trial Balance',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Trial balance with account hierarchy, period comparison and XML appendix',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - Trial Balance
=======================

Trial balance of the Vietnamese accounting system: opening balance, movements
of the period and closing balance of every account, debit and credit apart.

* receivable and payable accounts 131 and 331 split by partner
* account hierarchy, comparison with another period
* on screen, Excel, PDF, and the XML appendix F01-CDTK

See readme.md in the module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': [
        'fg_vn_accounting_reports',
        'fg_vn_transfer_account',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/cdps_wizard_views.xml',
        'views/cdps_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_vn_report_cdps/static/src/scss/cdps_report.scss',
            'fg_vn_report_cdps/static/src/js/cdps_report.js',
        ],
        'web.assets_tests': [
            'fg_vn_report_cdps/static/tests/tours/**/*',
        ],
    },
    'installable': True,
}
