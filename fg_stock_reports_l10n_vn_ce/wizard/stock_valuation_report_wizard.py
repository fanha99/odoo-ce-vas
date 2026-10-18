# -*- coding: utf-8 -*-
# Copyright 2024 Fanha Giang
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockValuationReportWizard(models.TransientModel):
    """Stock Valuation Report Wizard - Báo cáo Xuất Nhập Tồn."""

    _name = "stock.valuation.report.wizard"
    _description = "Stock Valuation Report Wizard"

    date_from = fields.Date(
        string="Từ ngày",
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="Đến ngày",
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Công ty",
        default=lambda self: self.env.company.id,
        required=True,
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Sản phẩm",
        help="Để trống để chọn tất cả sản phẩm có giao dịch",
    )
    product_categ_ids = fields.Many2many(
        comodel_name="product.category",
        string="Danh mục sản phẩm",
        help="Lọc theo danh mục sản phẩm",
    )
    warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        string="Kho",
        help="Lọc theo kho (để trống = tất cả kho)",
    )
    hide_zero_lines = fields.Boolean(
        string="Ẩn dòng có số dư = 0",
        default=True,
        help="Ẩn các sản phẩm có đầu kỳ = nhập = xuất = cuối kỳ = 0",
    )
    group_by_category = fields.Boolean(
        string="Nhóm theo danh mục",
        default=False,
        help="Nhóm sản phẩm theo danh mục",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise ValidationError(
                    _("'Từ ngày' không được lớn hơn 'Đến ngày'.")
                )

    @api.onchange("company_id")
    def _onchange_company_id(self):
        """Clear filters when company changes."""
        self.product_ids = False
        self.warehouse_ids = False
        # Return domain for warehouse_ids
        return {
            "domain": {
                "warehouse_ids": [("company_id", "=", self.company_id.id)]
            }
        }

    @api.onchange("product_categ_ids")
    def _onchange_product_categ_ids(self):
        """Update domain for products based on category selection."""
        if self.product_categ_ids:
            # Get all child categories
            categs = self.product_categ_ids
            all_categs = categs
            for categ in categs:
                all_categs |= self.env["product.category"].search(
                    [("id", "child_of", categ.id)]
                )
            return {
                "domain": {
                    "product_ids": [("categ_id", "in", all_categs.ids)]
                }
            }
        return {"domain": {"product_ids": []}}

    def _prepare_report_data(self):
        """Prepare data for the report."""
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "company_id": self.company_id.id,
            "product_ids": self.product_ids.ids or [],
            "product_categ_ids": self.product_categ_ids.ids or [],
            "warehouse_ids": self.warehouse_ids.ids or [],
            "hide_zero_lines": self.hide_zero_lines,
            "group_by_category": self.group_by_category,
        }

    def _print_report(self, report_type):
        """Print the report."""
        self.ensure_one()
        data = self._prepare_report_data()
        if report_type == "xlsx":
            report_name = "fg_stock_reports_l10n_vn_ce.report_stock_valuation_xlsx"
        else:
            report_name = "fg_stock_reports_l10n_vn_ce.report_stock_valuation"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )

    def button_export_html(self):
        """Export to HTML."""
        self.ensure_one()
        return self._print_report("qweb-html")

    def button_export_pdf(self):
        """Export to PDF."""
        self.ensure_one()
        return self._print_report("qweb-pdf")

    def button_export_xlsx(self):
        """Export to XLSX."""
        self.ensure_one()
        return self._print_report("xlsx")
