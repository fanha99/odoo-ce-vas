import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class S03aReport extends AbstractVNReport {
    // name in the breadcrumb when the action carries none (page reload)
    static displayName = _t("General Journal");

    // the search bears on the lines: a long journal is searched on the server
    static lazySearch = true;

    getReportModel() {
        return "vn.report.s03a";
    }

    getSearchKeys() {
        return ["move_name", "description", "account_code"];
    }

    getFilterDefinitions() {
        return [
            {
                key: "journal_ids",
                label: _t("Journals"),
                type: "many2many",
                model: "account.journal",
                domain: [],
            },
            {
                key: "move_type",
                label: _t("Entry type"),
                type: "selection",
                default: null,
                options: [
                    { value: "entry", label: _t("Journal entries") },
                    { value: "out_invoice", label: _t("Customer invoices") },
                    { value: "in_invoice", label: _t("Vendor bills") },
                    { value: "out_refund", label: _t("Customer credit notes") },
                    { value: "in_refund", label: _t("Vendor credit notes") },
                ],
            },
            {
                key: "account_ids",
                label: _t("Accounts"),
                type: "many2many",
                model: "account.account",
                domain: [],
            },
            {
                key: "partner_ids",
                label: _t("Partners"),
                type: "many2many",
                model: "res.partner",
                domain: [],
            },
        ];
    }

    async initializeFilters() {
        await super.initializeFilters();
        // the wizard sends "all", the selection of the screen uses no value
        if (this.state.advancedFilters.move_type === "all") {
            this.state.advancedFilters.move_type = null;
            this._updateActiveFilterCount();
        }
    }

    getLineMenuItems(line) {
        return [
            {
                key: "view_move",
                label: _t("View journal entry"),
                icon: "open_in_new",
                action: () => this.handleLineDrillDown(line),
            },
        ];
    }

    // the search applies to the lines, not to the single group of the journal
    get filteredLines() {
        return this.state.reportData?.lines || [];
    }

    groupsToRows(groups) {
        if (!groups.length) {
            return [];
        }
        const group = groups[0];
        const searchText = (this.state.filters.searchText || "").toLowerCase();
        const filterLocally = Boolean(searchText) && !this.isServerSearch;
        const keys = this.getSearchKeys();

        const rows = [];
        let debit = 0;
        let credit = 0;
        for (const line of group.lines || []) {
            if (
                filterLocally &&
                !keys.some((key) => String(line[key] ?? "").toLowerCase().includes(searchText))
            ) {
                continue;
            }
            debit += line.debit || 0;
            credit += line.credit || 0;
            rows.push({
                id: line.id,
                type: "data",
                cells: [
                    line.date_display,
                    line.move_name || "",
                    line.description || "",
                    line.debit ? line.account_code : "",
                    line.credit ? line.account_code : "",
                    line.debit || 0,
                    line.credit || 0,
                ],
                data: line,
            });
        }

        const loadMoreRow = this.getLoadMoreRow(group);
        if (loadMoreRow) {
            rows.push(loadMoreRow);
        }

        // The total is the one of the whole journal, computed by the server.
        // When the lines are filtered in the browser, it is the total of the
        // lines shown.
        const total = filterLocally ? { debit, credit } : group.total || {};
        rows.push({
            id: "grand_total",
            type: "grand_total",
            cells: ["", "", group.total_label || "", "", "", total.debit || 0, total.credit || 0],
        });
        return rows;
    }
}

registry.category("actions").add("vn_report_s03a", S03aReport);
