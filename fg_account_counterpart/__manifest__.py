{
    'name': 'Account Counterparts',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Countered journal items and countered accounts of every journal item',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Account Counterparts
====================

Records, for every posted journal entry, which debit journal items are
countered by which credit journal items, and for what amount. Each journal
item then shows its countered journal items and countered accounts.

See readme.md in the module directory for the matching rules.
""",
    'author': 'Fanha Giang',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.access.csv',
        'views/account_move_line_ctp_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
        'wizard/account_counterpart_generate_views.xml',
    ],
    'pre_init_hook': '_pre_init_counterpart',
    'installable': True,
}
