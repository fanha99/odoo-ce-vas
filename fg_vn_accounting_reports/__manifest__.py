{
    'name': 'Vietnam Accounting Reports - Core',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Shared screen, Excel export and PDF printing of the Vietnamese accounting books',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam Accounting Reports - Core
=================================

Common part of the Vietnamese accounting books: the on-screen report with its
period, filters, search, folding and drill-down, the Excel export, and the PDF
printing with running totals carried from page to page.

This module holds no report. Each book is a separate module built on it.

See readme.md in the module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_vn_accounting_reports/static/src/scss/abstract_report.scss',
            'fg_vn_accounting_reports/static/src/js/abstract_report.js',
            'fg_vn_accounting_reports/static/src/xml/abstract_report.xml',
        ],
    },
    'installable': True,
}
