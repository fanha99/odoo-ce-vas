{
    'name': 'Vietnam - General Ledger (S03b-DNN)',
    'version': '20.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': 'General ledger of the Vietnamese accounting system, form S03b-DNN',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - General Ledger (S03b-DNN)
===================================

For each account: opening balance, journal items of the period with their
counterpart accounts, total of the period and closing balance.

* counterpart accounts from the Account Counterparts module, optionally one
  line per counterpart account
* real counterpart behind a hidden transfer account
* long ledgers loaded account by account
* on screen, Excel (one sheet per account) and PDF (one account per page)

See readme.md in the module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': [
        'fg_vn_accounting_reports',
        'fg_account_counterpart',
        'fg_vn_transfer_account',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/s03b_wizard_views.xml',
        'views/s03b_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_vn_report_s03b/static/src/js/s03b_report.js',
        ],
        'web.assets_tests': [
            'fg_vn_report_s03b/static/tests/tours/**/*',
        ],
    },
    'installable': True,
}
