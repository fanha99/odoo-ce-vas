# -*- coding: utf-8 -*-
{
    'name': 'Account Journal Items Report',
    'version': '17.0.1.0.0',
    'category': 'Fanha Addons/Accounting/Reports',
    'summary': 'Chi tiết bút toán theo tài khoản',
    'description': """
Module báo cáo chi tiết Journal Items theo tài khoản
====================================================

Tính năng:

* Báo cáo chi tiết journal items theo từng tài khoản
* Lọc theo khoảng thời gian
* Lọc theo trạng thái (Posted/Draft)
* Lọc theo Journal (Sổ nhật ký)
* Số dư đầu kỳ, cuối kỳ cho từng tài khoản
* Xem trước HTML
* Xuất PDF (giấy dọc A4)
* Xuất Excel (mỗi tài khoản một sheet)
* Tích hợp vào Trial Balance: Mở báo cáo trực tiếp từ caret menu của từng tài khoản
    """,
    'author': 'Fanha Giang',
    'depends': ['account', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_journal_items_report_wizard_views.xml',
        'report/account_journal_items_report_templates.xml',
        'views/menu_views.xml',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
