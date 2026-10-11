{
    'name': 'Vietnam - General Journal (S03a-DNN)',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'General journal of the Vietnamese accounting system, form S03a-DNN',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - General Journal (S03a-DNN)
====================================

Lists the posted journal items of a period in chronological order, with the
debited account, the credited account and the amount.

* filters by journal, entry type, account and partner
* entries meeting on a hidden transfer account shown as one operation
* long journals loaded by chunks
* on screen, Excel and PDF with totals carried from page to page

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
        'wizard/s03a_wizard_views.xml',
        'views/s03a_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_vn_report_s03a/static/src/js/s03a_report.js',
        ],
        'web.assets_tests': [
            'fg_vn_report_s03a/static/tests/tours/**/*',
        ],
    },
    'installable': True,
}
