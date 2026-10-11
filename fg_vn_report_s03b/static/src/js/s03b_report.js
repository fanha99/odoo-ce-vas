import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class S03bReport extends AbstractVNReport {
    // name in the breadcrumb when the action carries none (page reload)
    static displayName = _t("General Ledger");

    getReportModel() {
        return "vn.report.s03b";
    }

    // the search bears on the accounts, which are always all loaded
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
                key: "account_type",
                label: _t("Account type"),
                type: "selection",
                default: null,
                options: [
                    { value: "asset", label: _t("Assets") },
                    { value: "liability", label: _t("Liabilities") },
                    { value: "equity", label: _t("Equity") },
                    { value: "income", label: _t("Income") },
                    { value: "expense", label: _t("Expenses") },
                ],
            },
            {
                key: "partner_ids",
                label: _t("Partners"),
                type: "many2many",
                model: "res.partner",
                domain: [],
            },
            {
                key: "journal_ids",
                label: _t("Journals"),
                type: "many2many",
                model: "account.journal",
                domain: [],
            },
            {
                key: "empty_accounts",
                label: _t("Accounts without journal items"),
                type: "selection",
                default: null,
                emptyLabel: _t("Leave out"),
                options: [
                    { value: "with_balance", label: _t("Include those with an opening balance") },
                    { value: "all", label: _t("Include all") },
                ],
            },
            {
                key: "split_counterparts",
                label: _t("Counterpart accounts"),
                type: "boolean",
                default: false,
                checkLabel: _t("One line per counterpart account"),
            },
        ];
    }

    async initializeFilters() {
        await super.initializeFilters();
        // the wizard sends "all" and "hide", the selections of the screen use no value
        const filters = this.state.advancedFilters;
        if (filters.account_type === "all") {
            filters.account_type = null;
        }
        if (filters.empty_accounts === "hide") {
            filters.empty_accounts = null;
        }
        this._updateActiveFilterCount();
    }

    getGroupMenuItems(group) {
        return [
            {
                key: "view_items",
                label: _t("View journal items"),
                icon: "view_list",
                action: () => this.handleGroupDrillDown(group),
            },
        ];
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

    groupsToRows(groups) {
        const rows = [];
        // In a long ledger the accounts come folded: their balances stay
        // visible and only their journal items fold.
        const lazy = this.isLazy;
        for (const account of groups) {
            const id = account.id;
            const summaryParent = lazy ? undefined : id;
            rows.push({
                id,
                type: "group_hdr",
                span_all: true,
                expandable: true,
                label: account.label,
                cells: [],
                data: account,
            });
            rows.push({
                id: `${id}_opening`,
                parentId: summaryParent,
                type: "opening",
                cells: ["", "", account.opening_label, "", account.opening.debit, account.opening.credit],
            });
            for (const line of account.lines || []) {
                rows.push({
                    id: `${id}_${line.id}`,
                    parentId: id,
                    type: "data",
                    cells: [
                        line.date_display,
                        line.move_name || "",
                        line.description || "",
                        line.counterpart_account || "",
                        line.debit || 0,
                        line.credit || 0,
                    ],
                    data: line,
                });
            }
            const loadMoreRow = this.getLoadMoreRow(account, id);
            if (loadMoreRow) {
                rows.push(loadMoreRow);
            }
            rows.push({
                id: `${id}_total`,
                parentId: summaryParent,
                type: "group_total",
                cells: ["", "", account.total_label, "", account.total.debit, account.total.credit],
            });
            rows.push({
                id: `${id}_closing`,
                parentId: summaryParent,
                type: "closing",
                cells: ["", "", account.closing_label, "", account.closing.debit, account.closing.credit],
            });
        }
        return rows;
    }
}

registry.category("actions").add("vn_report_s03b", S03bReport);
