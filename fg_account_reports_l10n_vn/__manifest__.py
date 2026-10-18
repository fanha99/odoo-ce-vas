{
    'name': 'Vietnam Financial Reports TT133 Compliant',
    'version': '1.0',
    'category': 'Fanha Addons/Accounting/Localizations/Reporting',
    'summary': 'Vietnam Financial Reports',
    'description': '''
        This module adds Vietnamese financial reports TT133 compliant reports to Odoo.:
        - Báo Cáo Tình Hình Tài Chính (B01b-DNN-TT133)
        - Báo Cáo Kết Quả Hoạt Động Kinh Doanh (B02-DNN-TT133)
        - Tờ khai quyết toán thuế TNDN (03/TNDN)
        - More reports to be added
    ''',
    'author': 'Fanha Giang',
    'depends': ['account_reports', 'l10n_vn', 'analytic', 'fg_account_counterpart', 'fg_analytic_data'],
    'data': [
        'security/ir.model.access.csv',
        'views/pdf_export_templates.xml',
        'views/vn_b01b_dnn_tt133.xml',
        'views/vn_b02_dnn_tt133.xml',
        'views/vn_031a_tndn.xml',
        #'views/vn_03tndn.xml',
        'views/vn_trial_balance.xml',
        'views/account_report_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fg_account_reports_l10n_vn/static/src/scss/vn_balance_sheet_report.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
