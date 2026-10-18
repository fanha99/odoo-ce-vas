# -*- coding: utf-8 -*-
# Copyright 2024 Fanha Giang
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Vietnam Stock Valuation Reports (OCA Style)",
    "version": "17.0.1.0.0",
    "category": "Fanha Addons/Stock/Reporting",
    "summary": "Báo cáo Xuất Nhập Tồn - Stock Valuation Layer Report (OCA Style)",
    "description": """
Vietnam Stock Valuation Reports - OCA Style
============================================

Báo cáo tổng hợp Xuất Nhập Tồn theo phong cách OCA Account Financial Reports.

Features:
- Báo cáo Xuất Nhập Tồn (Stock In/Out/Balance Report)
- Hiển thị số dư đầu kỳ, nhập trong kỳ, xuất trong kỳ, số dư cuối kỳ
- Hỗ trợ xuất PDF và Excel
- Lọc theo ngày, sản phẩm, danh mục sản phẩm, kho
- Dựa trên stock.valuation.layer

Based on OCA account_financial_report trial balance report structure.
    """,
    "author": "Fanha Giang",
    "license": "AGPL-3",
    "depends": [
        "stock_account",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat.xml",
        "wizard/stock_valuation_report_wizard_view.xml",
        "view/menuitems.xml",
        "report/reports.xml",
        "report/templates/layouts.xml",
        "report/templates/stock_valuation_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fg_stock_reports_l10n_vn_ce/static/src/js/*.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
