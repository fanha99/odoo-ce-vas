{
    'name': 'Account Counterparts',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Countered journal items and countered accounts of every journal item',
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
