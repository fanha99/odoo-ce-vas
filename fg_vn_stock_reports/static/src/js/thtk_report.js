import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class THTKReport extends AbstractVNReport {
    // name in the breadcrumb when the action carries none (page reload)
    static displayName = _t("Stock Summary");

    getDefaultSort() {
        return { column: "code", order: "asc" };
    }

    getReportModel() {
        return "vn.report.thtk";
    }

    getSearchKeys() {
        return ["code", "name"];
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
                key: "group_by_location",
                label: _t("Group by location"),
                type: "boolean",
                default: false,
                checkLabel: _t("Group by location"),
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

    getLineMenuItems(line) {
        const drill = (kind) => () => this.handleLineDrillDown({ ...line, drill: kind });
        return [
            {
                key: "view_valuation",
                label: _t("View stock valuation"),
                icon: "view_list",
                action: drill("valuation"),
            },
            {
                key: "view_moves",
                label: _t("View stock moves"),
                icon: "swap_horiz",
                action: drill("move"),
            },
            {
                key: "view_move_lines",
                label: _t("View stock move lines"),
                icon: "menu",
                action: drill("move_lines"),
            },
        ];
    }

    // ==================== ROWS ====================

    _lineCells(line) {
        return [
            line.product_id || line.code || "",
            line.name || "",
            line.uom || "",
            line.opening_qty || 0,
            line.opening_value || 0,
            line.in_qty || 0,
            line.in_value || 0,
            line.out_qty || 0,
            line.out_value || 0,
            line.closing_qty || 0,
            line.closing_value || 0,
        ];
    }

    _totalCells(group) {
        const totals = group.totals || {};
        return [
            "", group.total_label, "",
            totals.opening_qty || 0,
            totals.opening_value || 0,
            totals.in_qty || 0,
            totals.in_value || 0,
            totals.out_qty || 0,
            totals.out_value || 0,
            totals.closing_qty || 0,
            totals.closing_value || 0,
        ];
    }

    _filterLines(lines) {
        const query = (this.state.filters.searchText || "").toLowerCase();
        if (!query) {
            return lines;
        }
        return lines.filter(
            (line) =>
                (line.product_id && String(line.product_id).toLowerCase().includes(query)) ||
                (line.code && String(line.code).toLowerCase().includes(query)) ||
                (line.name && String(line.name).toLowerCase().includes(query))
        );
    }

    // the search bears on the product lines, not on the single group
    get filteredLines() {
        return this.state.reportData?.lines || [];
    }

    groupsToRows(groups) {
        if (!groups.length) {
            return [];
        }
        const data = groups[0];
        const rows = [];

        if (data.group_by_location) {
            for (const location of data.groups || []) {
                const lines = this._filterLines(location.lines || []);
                if (!lines.length && this.state.filters.searchText) {
                    continue;
                }
                const id = `loc_${location.id}`;
                rows.push({
                    id,
                    type: "group_hdr",
                    span_all: true,
                    expandable: true,
                    label: location.location_name,
                    cells: [],
                    data: location,
                });
                for (const line of lines) {
                    rows.push({
                        id: `line_${location.id}_${line.product_id}`,
                        parentId: id,
                        type: "data",
                        cells: this._lineCells(line),
                        data: line,
                    });
                }
                rows.push({
                    id: `${id}_total`,
                    parentId: id,
                    type: "group_total",
                    cells: this._totalCells(location),
                });
            }
        } else {
            for (const line of this._filterLines(data.lines || [])) {
                rows.push({
                    id: `line_${line.product_id}`,
                    type: "data",
                    cells: this._lineCells(line),
                    data: line,
                });
            }
        }

        rows.push({
            id: "grand_total",
            type: "grand_total",
            cells: this._totalCells(data),
        });
        return rows;
    }
}

registry.category("actions").add("vn_report_thtk", THTKReport);
