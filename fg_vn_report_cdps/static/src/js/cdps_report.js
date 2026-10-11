import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const AMOUNT_FIELDS = [
    "opening_debit",
    "opening_credit",
    "debit",
    "credit",
    "closing_debit",
    "closing_credit",
];

export class CDPSReport extends AbstractVNReport {
    getReportModel() {
        return "vn.report.cdps";
    }

    getSearchKeys() {
        return ["code", "name"];
    }

    getFilterDefinitions() {
        return [
            {
                key: "account_ids",
                label: _t("Accounts"),
                type: "many2many",
                model: "account.account",
                domain: [],
            },
            {
                key: "account_level",
                label: _t("Account level"),
                type: "selection",
                default: null,
                options: [
                    { value: "1", label: _t("Level 1 (3 digits)") },
                    { value: "2", label: _t("Level 2 (4 digits)") },
                    { value: "3", label: _t("Level 3 (5 digits)") },
                    { value: "detail", label: _t("Detailed") },
                ],
            },
            {
                key: "hide_zero",
                label: _t("Accounts without figures"),
                type: "boolean",
                // Mirror of the wizard field show_zero_balance (default False):
                // hide_zero = !show_zero_balance. With another default, a page
                // reload would flip the option.
                default: true,
                checkLabel: _t("Hide"),
            },
            {
                key: "show_hierarchy",
                label: _t("Hierarchy"),
                type: "boolean",
                // mirror of the wizard field hierarchy (default False)
                default: false,
                checkLabel: _t("Show the account hierarchy"),
            },
            {
                key: "comparison_type",
                label: _t("Compare with"),
                type: "selection",
                default: null,
                emptyLabel: _t("No comparison"),
                options: [
                    { value: "previous_period", label: _t("Previous period") },
                    { value: "same_period_last_year", label: _t("Same period last year") },
                    { value: "custom", label: _t("Custom period") },
                ],
            },
            {
                key: "comparison_date_from",
                label: _t("Compared from"),
                type: "date",
                visible: (filters) => filters.comparison_type === "custom",
            },
            {
                key: "comparison_date_to",
                label: _t("Compared to"),
                type: "date",
                visible: (filters) => filters.comparison_type === "custom",
            },
        ];
    }

    async initializeFilters() {
        await super.initializeFilters();
        const options = this.state.options || {};
        const filters = this.state.advancedFilters;
        if (options.hierarchy !== undefined) {
            filters.show_hierarchy = options.hierarchy;
        }
        if (options.show_zero_balance !== undefined) {
            filters.hide_zero = !options.show_zero_balance;
        }
        if (filters.comparison_type === "none") {
            filters.comparison_type = null;
        }
        this._updateActiveFilterCount();
    }

    applyFilters() {
        const filters = this.state.advancedFilters;
        if (
            filters.comparison_type === "custom" &&
            !(filters.comparison_date_from && filters.comparison_date_to)
        ) {
            this.notification.add(
                _t("Please set the start and end dates of the compared period."),
                { type: "warning" }
            );
            return;
        }
        super.applyFilters();
    }

    // By default only the top level is unfolded. When setup() restored the
    // unfolded rows, super has handled it (the flag is read before super,
    // which resets it).
    async loadReportData() {
        const restoring = this._pendingExpandRestore;
        await super.loadReportData();
        if (restoring) {
            return;
        }
        const initial = new Set();
        for (const line of this.reportLines) {
            if (line.level === 0 && line.has_children) {
                initial.add(line.id);
            }
        }
        this.state.expandedNodes = initial;
        this._persistUiState();
    }

    _buildOptions() {
        const options = super._buildOptions();
        // the server knows the options under the names of the wizard fields
        options.hierarchy = options.show_hierarchy ?? false;
        delete options.show_hierarchy;
        options.show_zero_balance = !(options.hide_zero ?? false);
        delete options.hide_zero;
        options.comparison_type = options.comparison_type || "none";
        // account_level stays in the options to be restored with them after
        // a drill-down; the server ignores it, it only hides rows on screen
        return options;
    }

    // ==================== ROWS ====================

    get reportGroup() {
        return this.state.reportData?.lines?.[0] || {};
    }

    get reportLines() {
        return this.reportGroup.lines || [];
    }

    get hasComparison() {
        return this.reportGroup.has_comparison || false;
    }

    _lineCells(line) {
        const cells = [line.code || "", line.name || ""];
        for (const fname of AMOUNT_FIELDS) {
            cells.push(line[fname] || 0);
        }
        if (this.hasComparison) {
            const percent = line.variance_percent;
            cells.push(
                line.prev_closing_debit || 0,
                line.prev_closing_credit || 0,
                line.variance || 0,
                percent != null ? this.formatPercent(percent) : ""
            );
        }
        return cells;
    }

    groupsToRows(groups) {
        if (!groups.length) {
            return [];
        }
        const data = groups[0];
        const lines = data.lines || [];
        const totals = data.totals || {};
        const searchText = (this.state.filters.searchText || "").toLowerCase();
        const maxCodeLength =
            { 1: 3, 2: 4, 3: 5 }[this.state.advancedFilters.account_level] || Infinity;

        const rows = [];
        if (searchText) {
            // a search lists the matching accounts without hierarchy
            const keys = this.getSearchKeys();
            for (const line of lines) {
                if (keys.some((k) => line[k] && String(line[k]).toLowerCase().includes(searchText))) {
                    rows.push({
                        id: line.id,
                        type: "data",
                        isParent: line.is_parent,
                        cells: this._lineCells(line),
                        data: line,
                    });
                }
            }
        } else if (!data.show_hierarchy) {
            // the account level hides the accounts with a longer code
            for (const line of lines) {
                if ((line.code || "").length <= maxCodeLength) {
                    rows.push({
                        id: line.id,
                        type: "data",
                        cells: this._lineCells(line),
                        data: line,
                    });
                }
            }
        } else {
            for (const line of lines) {
                rows.push({
                    id: line.id,
                    parentId: line.parent_id || undefined,
                    type: "data",
                    isParent: line.is_parent,
                    expandable: Boolean(line.has_children),
                    level: line.level || 0,
                    cells: this._lineCells(line),
                    data: line,
                });
            }
        }

        const totalCells = ["", data.total_label || ""];
        for (const fname of AMOUNT_FIELDS) {
            totalCells.push(totals[fname] || 0);
        }
        if (this.hasComparison) {
            totalCells.push(totals.prev_closing_debit || 0, totals.prev_closing_credit || 0, "", "");
        }
        rows.push({ id: "grand_total", type: "grand_total", cells: totalCells });

        return rows;
    }

    // the search applies to the accounts, not to the single group of the report
    get filteredLines() {
        return this.state.reportData?.lines || [];
    }

    // ==================== HIERARCHY ====================

    // Folding an account folds the levels below too.
    toggleNode(rowId) {
        const expanded = new Set(this.state.expandedNodes);
        if (expanded.has(rowId)) {
            this._collectDescendants(rowId, expanded);
            expanded.delete(rowId);
        } else {
            expanded.add(rowId);
        }
        this.state.expandedNodes = expanded;
        this._persistUiState();
    }

    _collectDescendants(id, expanded) {
        for (const line of this.reportLines) {
            if (line.parent_id === id && line.has_children) {
                expanded.delete(line.id);
                this._collectDescendants(line.id, expanded);
            }
        }
    }

    expandAll() {
        this.state.expandedNodes = new Set(
            this.reportLines.filter((line) => line.has_children).map((line) => line.id)
        );
        this._persistUiState();
    }

    collapseAll() {
        this.state.expandedNodes = new Set();
        this._persistUiState();
    }

    // ==================== EXPORT ====================

    get hasXmlExport() {
        return true;
    }

    exportXml() {
        this.notification.add(_t("Exporting to XML..."), { type: "info" });
        window.location.href = this.getExportUrl("xml");
    }

    // ==================== STYLE ====================

    getDataRowClass(row) {
        let cls = super.getDataRowClass(row);
        if (row.type === "data" && row.isParent && !row.level) {
            cls += " o_cdps_root_row";
        }
        if (row.data?.is_off_balance) {
            cls += " o_vn_off_balance_row";
        }
        return cls;
    }
}

registry.category("actions").add("vn_report_cdps", CDPSReport);
