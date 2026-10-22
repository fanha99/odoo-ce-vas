import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class S06Report extends AbstractVNReport {
    // name in the breadcrumb when the action carries none (page reload)
    static displayName = _t("Detailed Stock Ledger (S06-DNN)");

    getReportModel() {
        return "vn.report.s06";
    }

    getSearchKeys() {
        return ["product_code", "product_name"];
    }

    getFilterDefinitions() {
        return [
            {
                key: "product_ids",
                label: _t("Products"),
                type: "many2many",
                model: "product.product",
                domain: [["is_storable", "=", true]],
            },
            {
                key: "category_ids",
                label: _t("Product categories"),
                type: "many2many",
                model: "product.category",
                domain: [],
            },
            {
                key: "location_ids",
                label: _t("Locations"),
                type: "many2many",
                model: "stock.location",
                domain: [["usage", "=", "internal"]],
            },
            {
                key: "show_zero_balance",
                label: _t("Display"),
                type: "boolean",
                default: false,
                checkLabel: _t("Products without stock"),
            },
        ];
    }

    getGroupMenuItems(group) {
        return [
            {
                key: "view_moves",
                label: _t("View stock moves"),
                icon: "view_list",
                action: () => this.handleGroupDrillDown(group),
            },
        ];
    }

    getLineMenuItems(line) {
        const drill = (kind) => () => this.handleLineDrillDown({ ...line, drill: kind });
        const items = [];
        if (line.account_move_id) {
            items.push({
                key: "view_account_move",
                label: _t("View journal entry"),
                icon: "description",
                action: drill("account_move"),
            });
        }
        items.push({
            key: "view_valuation",
            label: _t("View stock valuation"),
            icon: "view_list",
            action: drill("valuation"),
        });
        if (line.move_id) {
            items.push(
                {
                    key: "view_move",
                    label: _t("View stock move"),
                    icon: "swap_horiz",
                    action: drill("move"),
                },
                {
                    key: "view_move_lines",
                    label: _t("View stock move lines"),
                    icon: "menu",
                    action: drill("move_lines"),
                }
            );
        }
        return items;
    }

    groupsToRows(groups) {
        const rows = [];
        for (const product of groups) {
            const id = product.id;
            rows.push({
                id,
                type: "group_hdr",
                span_all: true,
                expandable: true,
                label: product.label,
                cells: [],
                data: product,
            });
            const opening = product.opening || {};
            rows.push({
                id: `${id}_opening`,
                parentId: id,
                type: "opening",
                cells: [
                    "", "", product.opening_label,
                    opening.unit_price || 0,
                    "", "", "", "",
                    opening.quantity || 0,
                    opening.value || 0,
                ],
            });
            for (const line of product.lines || []) {
                rows.push({
                    id: line.id,
                    parentId: id,
                    type: "data",
                    cells: [
                        line.date ? this.formatDate(line.date) : "",
                        line.reference || "",
                        line.description || "",
                        line.unit_price || 0,
                        line.qty_in || 0,
                        line.value_in || 0,
                        line.qty_out || 0,
                        line.value_out || 0,
                        line.balance_qty || 0,
                        line.balance_value || 0,
                    ],
                    data: line,
                });
            }
            const total = product.total || {};
            const closing = product.closing || {};
            rows.push({
                id: `${id}_closing`,
                parentId: id,
                type: "closing",
                cells: [
                    "", "", product.closing_label,
                    closing.unit_price || 0,
                    total.qty_in || 0,
                    total.value_in || 0,
                    total.qty_out || 0,
                    total.value_out || 0,
                    closing.quantity || 0,
                    closing.value || 0,
                ],
            });
        }
        return rows;
    }
}

registry.category("actions").add("vn_report_s06", S06Report);
