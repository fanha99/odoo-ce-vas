{
    'name': 'Vietnam - Hide Transfer Accounts',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Company setting to hide the transfer accounts without balance on accounting books',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - Hide Transfer Accounts
================================

Adds a company setting to hide the transfer accounts that have no balance,
and lets the user choose which accounts are concerned. The accounting books
and printouts read this setting; this module has no report of its own.

Meant for companies applying Circular 133, whose chart of accounts has no
account 113.

See readme.md in the module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
}
