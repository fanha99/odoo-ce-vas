import { Component, markRaw, onWillStart, proxy, signal, useListener, useProps } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const { DateTime } = luxon;

/**
 * Base component of the Vietnamese accounting reports. A report extends this
 * class and overrides the hooks it needs; the screen, the toolbar and the
 * table are shared.
 */
export class AbstractVNReport extends Component {
    static template = "fg_vn_accounting_reports.AbstractReport";
    // Template rendering the figures. A report with a table of its own
    // overrides this; the others get the generic table.
    static tableTemplate = "fg_vn_accounting_reports.DataTable";
    static components = { Dropdown, DropdownItem, DateTimeInput };

    props = useProps(standardActionServiceProps);

    filterDropdownRef = signal.ref();
    dateDropdownRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // The state is kept in sessionStorage, one key per report model, so
        // that it survives a drill-down round trip and a page reload; closing
        // the browser tab clears it.
        let model = null;
        try {
            model = this.getReportModel();
        } catch {
            // abstract base
        }
        this._storageKey = model ? `vn_report_state_${model}` : null;
        let stored = this._loadPersistedState();

        // The wizard stamps each opening of the report with a token. Options
        // coming with a token not seen yet are a new opening and win over the
        // stored state; otherwise the stored state is the newer one (coming
        // back from a drill-down, page reload).
        const context = this.props.action.context || {};
        this._reportToken = context.report_token || stored.token || null;
        if (context.options && context.report_token !== stored.token) {
            stored = {};
            this._clearPersistedState();
        }
        const options = stored.options || context.options || {};
        const uiState = stored.uiState || {};
        const defaultSort = this.getDefaultSort();

        // With a snapshot of the unfolded nodes, the first load keeps it
        // instead of unfolding everything.
        this._pendingExpandRestore = Array.isArray(uiState.expandedNodeIds);
        const initialExpand = this._pendingExpandRestore ? uiState.expandedNodeIds : [];

        let dateFrom, dateTo, selectedFilter;
        if (options.date?.date_from && options.date?.date_to) {
            dateFrom = DateTime.fromISO(options.date.date_from);
            dateTo = DateTime.fromISO(options.date.date_to);
            selectedFilter = options.date?.filter || "custom";
        } else {
            const now = DateTime.now();
            dateFrom = now.startOf("month");
            dateTo = now.endOf("month");
            selectedFilter = "this_month";
        }

        this.state = proxy({
            isLoading: true,
            options: options,
            // Period (Luxon DateTime, kept out of the reactivity)
            dateFrom: markRaw(dateFrom),
            dateTo: markRaw(dateTo),
            // Dates being typed in the custom period, not applied yet
            tempDateFrom: markRaw(dateFrom),
            tempDateTo: markRaw(dateTo),
            selectedFilter: selectedFilter,
            showFilterDropdown: false,
            showDateDropdown: false,
            reportData: null,
            // Language of the report; null until the server tells its default
            reportLang: options.lang || null,
            expandedGroups: new Set(initialExpand),
            expandedNodes: new Set(initialExpand), // multi-level hierarchy
            sortColumn: uiState.sortColumn !== undefined ? uiState.sortColumn : defaultSort.column,
            sortOrder: uiState.sortOrder || defaultSort.order,
            filters: {
                searchText: "",
            },
            advancedFilters: {},
            filterSearchText: {},
            filterSearchResults: {},
            activeFilterCount: 0,
        });

        useListener(document, "click", this._onClickOutside.bind(this), { capture: true });

        onWillStart(async () => {
            await this.initializeFilters();
            await this.loadReportData();
        });
    }

    _onClickOutside(ev) {
        const target = ev.target;
        if (this.state.showFilterDropdown) {
            const filterDropdown = this.filterDropdownRef();
            if (filterDropdown && !filterDropdown.contains(target)) {
                this.state.showFilterDropdown = false;
            }
        }
        if (this.state.showDateDropdown) {
            const dateDropdown = this.dateDropdownRef();
            // the date picker popover is rendered outside of the dropdown
            if (
                dateDropdown &&
                !dateDropdown.contains(target) &&
                !target.closest?.(".o_datetime_picker, .o_popover")
            ) {
                this.state.showDateDropdown = false;
            }
        }
    }

    // ==================== HOOKS TO OVERRIDE ====================

    getReportModel() {
        throw new Error("Subclass must implement getReportModel()");
    }

    getSearchKeys() {
        return ["name", "code"];
    }

    /**
     * Filters of the report, shown in the filter menu.
     *
     * Each definition: { key, label, type, ... } with type one of
     * - "many2many" / "many2one": { model, domain }
     * - "selection": { options: [{ value, label }], default, emptyLabel }
     * - "boolean": { checkLabel, default }
     * - "date": { default }, the value is an ISO date string or null
     * A definition may have `visible(filters)`, a function of the current
     * filter values telling whether the filter is shown.
     */
    getFilterDefinitions() {
        return [];
    }

    /**
     * Sort order when the report is first opened. Override this rather than
     * setting state.sortColumn in setup(), which would overwrite the order the
     * user chose before a drill-down.
     */
    getDefaultSort() {
        return { column: null, order: "asc" };
    }

    // ==================== STATE PERSISTENCE ====================

    _loadPersistedState() {
        if (!this._storageKey) {
            return {};
        }
        try {
            const raw = sessionStorage.getItem(this._storageKey);
            return raw ? JSON.parse(raw) : {};
        } catch {
            return {};
        }
    }

    _clearPersistedState() {
        if (!this._storageKey) {
            return;
        }
        try {
            sessionStorage.removeItem(this._storageKey);
        } catch {
            // private mode
        }
    }

    _writePersistedState(patch) {
        if (!this._storageKey) {
            return;
        }
        try {
            const stored = this._loadPersistedState();
            Object.assign(stored, patch, { token: this._reportToken });
            sessionStorage.setItem(this._storageKey, JSON.stringify(stored));
        } catch {
            // quota or private mode: a reload falls back on the defaults
        }
    }

    _persistOptions(options) {
        this._writePersistedState({ options });
    }

    _persistUiState() {
        this._writePersistedState({
            uiState: {
                sortColumn: this.state.sortColumn,
                sortOrder: this.state.sortOrder,
                expandedNodeIds: Array.from(this.state.expandedNodes),
            },
        });
    }

    // ==================== PERIOD ====================

    get dateFilters() {
        return [
            [
                { id: "this_month", label: _t("This month") },
                { id: "this_quarter", label: _t("This quarter") },
                { id: "this_year", label: _t("This year") },
            ],
            [
                { id: "last_month", label: _t("Last month") },
                { id: "last_quarter", label: _t("Last quarter") },
                { id: "last_year", label: _t("Last year") },
            ],
        ];
    }

    // Values of the DateTimeInput components (Luxon DateTime)
    get dateFromValue() {
        return this.state.tempDateFrom;
    }

    get dateToValue() {
        return this.state.tempDateTo;
    }

    get localeDateFrom() {
        return this.state.dateFrom?.toFormat?.("yyyy/MM/dd") || "";
    }

    get localeDateTo() {
        return this.state.dateTo?.toFormat?.("yyyy/MM/dd") || "";
    }

    get dateRangeLabel() {
        const selectedFilter = this.state.selectedFilter;
        if (selectedFilter === "custom" || !selectedFilter) {
            return _t("From: %(date_from)s to: %(date_to)s", {
                date_from: this.localeDateFrom,
                date_to: this.localeDateTo,
            });
        }
        const filter = this.dateFilters.flat().find((f) => f.id === selectedFilter);
        return filter ? filter.label : this._formatDateRange();
    }

    _formatDateRange() {
        const formatDate = (d) => {
            if (!d) {
                return "????/??/??";
            }
            return d.toFormat ? d.toFormat("yyyy/MM/dd") : String(d);
        };
        return `${formatDate(this.state.dateFrom)} - ${formatDate(this.state.dateTo)}`;
    }

    onDateFilterSelected(filterId) {
        const { dateFrom, dateTo } = this._calculateDateRange(filterId);
        this.state.dateFrom = markRaw(dateFrom);
        this.state.dateTo = markRaw(dateTo);
        this.state.tempDateFrom = markRaw(dateFrom);
        this.state.tempDateTo = markRaw(dateTo);
        this.state.selectedFilter = filterId;
        this.state.showDateDropdown = false;
        this.loadReportData();
    }

    onDateFromChange(newDate) {
        if (newDate) {
            this.state.tempDateFrom = markRaw(newDate);
            this.state.selectedFilter = "custom";
        }
    }

    onDateToChange(newDate) {
        if (newDate) {
            this.state.tempDateTo = markRaw(newDate);
            this.state.selectedFilter = "custom";
        }
    }

    applyCustomDate() {
        this.state.dateFrom = this.state.tempDateFrom;
        this.state.dateTo = this.state.tempDateTo;
        this.state.selectedFilter = "custom";
        this.state.showDateDropdown = false;
        this.loadReportData();
    }

    _calculateDateRange(filterId) {
        const now = DateTime.now();
        const units = { month: "months", quarter: "quarters", year: "years" };
        const [when, unit] = (filterId || "").split("_");
        if (!(unit in units) || !["this", "last"].includes(when)) {
            return { dateFrom: this.state.dateFrom, dateTo: this.state.dateTo };
        }
        const reference = when === "last" ? now.minus({ [units[unit]]: 1 }) : now;
        return { dateFrom: reference.startOf(unit), dateTo: reference.endOf(unit) };
    }

    // ==================== FILTERS ====================

    get filterDefinitions() {
        return this.getFilterDefinitions();
    }

    get hasFilters() {
        return this.filterDefinitions.length > 0;
    }

    isFilterVisible(filterDef) {
        return filterDef.visible ? Boolean(filterDef.visible(this.state.advancedFilters)) : true;
    }

    getFilterPlaceholder(filterDef) {
        return _t("Search %s...", filterDef.label);
    }

    async initializeFilters() {
        const definitions = this.getFilterDefinitions();
        const initialOptions = this.state.options;

        for (const def of definitions) {
            const initial = initialOptions[def.key];
            if (def.type === "many2many" || def.type === "many2one") {
                const initialIds = initial || [];
                if (initialIds.length > 0 && def.model) {
                    const records = await this.orm.read(def.model, initialIds, ["display_name"]);
                    this.state.advancedFilters[def.key] = records.map((r) => ({
                        id: r.id,
                        display_name: r.display_name,
                    }));
                } else {
                    this.state.advancedFilters[def.key] = [];
                }
                this.state.filterSearchText[def.key] = "";
                this.state.filterSearchResults[def.key] = [];
            } else if (def.type === "boolean") {
                this.state.advancedFilters[def.key] =
                    initial !== undefined ? initial : def.default || false;
            } else {
                // selection, date
                this.state.advancedFilters[def.key] =
                    initial !== undefined ? initial : def.default || null;
            }
        }
        this._updateActiveFilterCount();
    }

    toggleFilterDropdown(ev) {
        ev.stopPropagation();
        this.state.showFilterDropdown = !this.state.showFilterDropdown;
    }

    toggleDateDropdown(ev) {
        ev.stopPropagation();
        this.state.showDateDropdown = !this.state.showDateDropdown;
    }

    async onFilterSearchInput(filterKey, ev) {
        const searchText = ev.target.value;
        this.state.filterSearchText[filterKey] = searchText;

        if (searchText.length < 1) {
            this.state.filterSearchResults[filterKey] = [];
            return;
        }

        const def = this.filterDefinitions.find((d) => d.key === filterKey);
        if (!def) {
            return;
        }

        try {
            const results = await this.orm.call(def.model, "name_search", [], {
                name: searchText,
                domain: def.domain || [],
                limit: 10,
            });
            this.state.filterSearchResults[filterKey] = results.map(([id, display_name]) => ({
                id,
                display_name,
            }));
        } catch (error) {
            console.error("Filter search error:", error);
            this.state.filterSearchResults[filterKey] = [];
        }
    }

    selectFilterValue(filterKey, record) {
        const values = this.state.advancedFilters[filterKey] || [];
        if (!values.find((v) => v.id === record.id)) {
            this.state.advancedFilters[filterKey] = [
                ...values,
                { id: record.id, display_name: record.display_name || record.name },
            ];
        }
        this.state.filterSearchText[filterKey] = "";
        this.state.filterSearchResults[filterKey] = [];
        this._updateActiveFilterCount();
    }

    removeFilterValue(filterKey, valueId) {
        const values = this.state.advancedFilters[filterKey];
        if (Array.isArray(values)) {
            this.state.advancedFilters[filterKey] = values.filter((v) => v.id !== valueId);
            this._updateActiveFilterCount();
        }
    }

    onSelectionChanged(filterKey, ev) {
        const value = ev.target.value;
        this.state.advancedFilters[filterKey] = value === "" ? null : value;
        this._updateActiveFilterCount();
    }

    onBooleanChanged(filterKey, ev) {
        this.state.advancedFilters[filterKey] = ev.target.checked;
        this._updateActiveFilterCount();
    }

    onDateFilterChanged(filterKey, ev) {
        this.state.advancedFilters[filterKey] = ev.target.value || null;
        this._updateActiveFilterCount();
    }

    onReportLangChanged(ev) {
        this.state.reportLang = ev.target.value || null;
    }

    clearFilter(filterKey) {
        const def = this.filterDefinitions.find((d) => d.key === filterKey);
        if (def) {
            if (def.type === "many2many" || def.type === "many2one") {
                this.state.advancedFilters[filterKey] = [];
            } else if (def.type === "boolean") {
                this.state.advancedFilters[filterKey] = false;
            } else {
                this.state.advancedFilters[filterKey] = null;
            }
            this._updateActiveFilterCount();
        }
    }

    clearAllFilters() {
        for (const def of this.filterDefinitions) {
            this.clearFilter(def.key);
        }
        this.loadReportData();
    }

    _updateActiveFilterCount() {
        let count = 0;
        for (const def of this.filterDefinitions) {
            if (!this.isFilterVisible(def)) {
                continue;
            }
            const value = this.state.advancedFilters[def.key];
            if (Array.isArray(value)) {
                if (value.length > 0) {
                    count++;
                }
            } else if (value !== null && value !== undefined && value !== "" && value !== false) {
                count++;
            }
        }
        this.state.activeFilterCount = count;
    }

    applyFilters() {
        this.state.showFilterDropdown = false;
        this.loadReportData();
    }

    // ==================== DATA LOADING ====================

    _buildOptions() {
        const options = { ...this.state.options };

        options.date = {
            date_from: this.state.dateFrom?.toISODate?.() || this.state.dateFrom,
            date_to: this.state.dateTo?.toISODate?.() || this.state.dateTo,
            filter: this.state.selectedFilter,
            mode: "range",
        };

        if (this.state.reportLang) {
            options.lang = this.state.reportLang;
        } else {
            delete options.lang;
        }

        for (const def of this.filterDefinitions) {
            const value = this.state.advancedFilters[def.key];
            if (def.type === "many2many" || def.type === "many2one") {
                options[def.key] = Array.isArray(value) ? value.map((v) => v.id) : [];
            } else {
                options[def.key] = value;
            }
        }

        return options;
    }

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const options = this._buildOptions();
            this.state.options = options;
            this._persistOptions(options);

            const data = await this.orm.call(this.getReportModel(), "get_report_data", [options]);

            this.state.reportData = data;
            if (data.options?.lang) {
                this.state.reportLang = data.options.lang;
            }

            if (this._pendingExpandRestore) {
                // setup() restored the unfolded nodes: keep them on the first
                // load; the next loads unfold everything again
                this._pendingExpandRestore = false;
            } else {
                const expanded = new Set();
                for (const group of data.lines || []) {
                    expanded.add(group.id);
                }
                for (const row of this.tableRows) {
                    if (row.expandable && row.id != null) {
                        expanded.add(row.id);
                    }
                }
                this.state.expandedNodes = expanded;
                this.state.expandedGroups = new Set(expanded);
            }
            this._persistUiState();
        } catch (error) {
            // access and validation errors carry a message for the user:
            // let the error service show it
            this.state.isLoading = false;
            throw error;
        }
        this.state.isLoading = false;
    }

    // ==================== SEARCH ====================

    onSearchChange(ev) {
        this.state.filters.searchText = ev.target.value.toLowerCase();
    }

    get filteredLines() {
        if (!this.state.reportData?.lines) {
            return [];
        }
        const searchText = this.state.filters.searchText;
        if (!searchText) {
            return this.state.reportData.lines;
        }
        const searchKeys = this.getSearchKeys();
        return this.state.reportData.lines.filter((group) =>
            searchKeys.some((key) => {
                const value = group[key];
                return (
                    value !== null &&
                    value !== undefined &&
                    String(value).toLowerCase().includes(searchText)
                );
            })
        );
    }

    // ==================== EXPAND / COLLAPSE ====================
    // expandedGroups is a legacy alias of expandedNodes, kept in sync

    toggleGroup(groupId) {
        this.toggleNode(groupId);
        this.state.expandedGroups = new Set(this.state.expandedNodes);
    }

    isExpanded(groupId) {
        return this.state.expandedNodes.has(groupId);
    }

    expandAll() {
        const expanded = new Set(this.state.expandedNodes);
        for (const row of this.tableRows) {
            if (row.expandable && row.id != null) {
                expanded.add(row.id);
            }
        }
        for (const group of this.state.reportData?.lines || []) {
            expanded.add(group.id);
        }
        this.state.expandedNodes = expanded;
        this.state.expandedGroups = new Set(expanded);
        this._persistUiState();
    }

    collapseAll() {
        this.state.expandedNodes = new Set();
        this.state.expandedGroups = new Set();
        this._persistUiState();
    }

    // ==================== ACTION MENU ====================

    /**
     * Menu items of a group header. Override to customize.
     * @param {Object} group
     * @returns {Array} [{ key, label, icon, action }]
     */
    getGroupMenuItems(group) {
        return [
            {
                key: "drill_down",
                label: _t("View details"),
                icon: "fa-external-link",
                action: () => this.handleGroupDrillDown(group),
            },
        ];
    }

    /**
     * Menu items of a detail line. Override to customize.
     * @param {Object} line
     * @returns {Array} [{ key, label, icon, action }]
     */
    getLineMenuItems(line) {
        return [
            {
                key: "drill_down",
                label: _t("View details"),
                icon: "fa-external-link",
                action: () => this.handleLineDrillDown(line),
            },
        ];
    }

    // ==================== DRILL DOWN ====================

    async _drillDown(record, type) {
        const params = { ...record, line_id: record.id, type };
        const action = await this.orm.call(this.getReportModel(), "action_drill_down", [
            this.state.options,
            params,
        ]);
        if (action) {
            this._persistUiState();
            this.action.doAction(action);
        }
    }

    handleGroupDrillDown(group) {
        return this._drillDown(group, "group");
    }

    handleLineDrillDown(line) {
        return this._drillDown(line, "line");
    }

    // ==================== EXPORT ====================

    /** URL downloading the report in one of the formats of the export routes */
    getExportUrl(exportFormat) {
        const options = encodeURIComponent(JSON.stringify(this._buildOptions()));
        return `/vn_report/${this.getReportModel()}/export/${exportFormat}?options=${options}`;
    }

    exportXlsx() {
        this.notification.add(_t("Exporting to Excel..."), { type: "info" });
        window.location.href = this.getExportUrl("xlsx");
    }

    exportPdf() {
        this.notification.add(_t("Exporting to PDF..."), { type: "info" });
        window.location.href = this.getExportUrl("pdf_rl");
    }

    /** Override -> true to show the XML button */
    get hasXmlExport() {
        return false;
    }

    exportXml() {}

    // ==================== FORMATTERS ====================

    formatNumber(value, decimals = 2) {
        if (value === null || value === undefined || value === "") {
            return "";
        }
        return formatFloat(value, { digits: [0, decimals] });
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        // 'YYYY-MM-DD' is split as is: new Date() reads it as UTC, which is
        // one day off in the timezones behind UTC
        const m = typeof value === "string" && value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (m) {
            return `${m[1]}/${m[2]}/${m[3]}`;
        }
        const date = new Date(value);
        if (isNaN(date)) {
            return value;
        }
        const day = String(date.getDate()).padStart(2, "0");
        const month = String(date.getMonth() + 1).padStart(2, "0");
        return `${date.getFullYear()}/${month}/${day}`;
    }

    formatInteger(value) {
        if (value === undefined || value === null || value === 0) {
            return "";
        }
        return formatFloat(value, { digits: [0, 0] });
    }

    formatPercent(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
    }

    // ==================== GENERIC DATA TABLE ====================
    // Pipeline: filteredLines (groups) -> groupsToRows() (typed rows) -> sort
    // -> visibleRows (folding) -> the DataTable template renders the cells.

    /**
     * Override: turn the groups (state.reportData.lines) into typed rows.
     * Each row: { type, cells, id?, parentId?, expandable?, level?, data? }
     */
    groupsToRows(groups) {
        return [];
    }

    get tableRows() {
        const rows = this.groupsToRows(this.filteredLines || []);
        // Every row needs a stable id for t-key. The index in this full list
        // is stable across folding (only visibleRows is filtered), unlike the
        // index in the rendered list, which makes the keyed diff fail.
        rows.forEach((row, i) => {
            if (row.id == null) {
                row.id = `__row_${i}__`;
            }
        });
        return rows;
    }

    get sortedRows() {
        const rows = this.tableRows;
        const col = this.state.sortColumn;
        if (!col) {
            return rows;
        }
        const cols = this.state.reportData?.columns || [];
        const idx = cols.findIndex((c) => c.name === col);
        if (idx < 0) {
            return rows;
        }

        // Only the runs of consecutive 'data' rows are sorted: the group
        // headers, totals, opening and closing rows keep their place.
        const dir = this.state.sortOrder === "asc" ? 1 : -1;
        const result = [];
        let buffer = [];
        const flush = () => {
            buffer.sort((a, b) => {
                const va = a.cells[idx];
                const vb = b.cells[idx];
                if (va == null) {
                    return 1;
                }
                if (vb == null) {
                    return -1;
                }
                if (typeof va === "number" && typeof vb === "number") {
                    return (va - vb) * dir;
                }
                return String(va).localeCompare(String(vb)) * dir;
            });
            result.push(...buffer);
            buffer = [];
        };
        for (const row of rows) {
            if (row.type === "data") {
                buffer.push(row);
            } else {
                flush();
                result.push(row);
            }
        }
        flush();
        return result;
    }

    get visibleRows() {
        const rows = this.sortedRows;
        const byId = new Map();
        for (const row of rows) {
            if (row.id != null) {
                byId.set(row.id, row);
            }
        }
        const isAncestorVisible = (row) => {
            let parentId = row.parentId;
            while (parentId != null) {
                const parent = byId.get(parentId);
                if (!parent) {
                    return true; // unknown parent: shown
                }
                if (parent.expandable && !this.isNodeExpanded(parentId)) {
                    return false;
                }
                parentId = parent.parentId;
            }
            return true;
        };
        return rows.filter(isAncestorVisible);
    }

    // ==================== HIERARCHY ====================

    toggleNode(rowId) {
        const expanded = new Set(this.state.expandedNodes);
        if (expanded.has(rowId)) {
            expanded.delete(rowId);
        } else {
            expanded.add(rowId);
        }
        this.state.expandedNodes = expanded;
        this._persistUiState();
    }

    isNodeExpanded(rowId) {
        return this.state.expandedNodes.has(rowId);
    }

    // ==================== SORT ====================

    toggleSort(colName) {
        if (this.state.sortColumn === colName) {
            this.state.sortOrder = this.state.sortOrder === "asc" ? "desc" : "asc";
        } else {
            this.state.sortColumn = colName;
            this.state.sortOrder = "asc";
        }
        this._persistUiState();
    }

    onColumnHeaderClick(col) {
        if (col.sortable) {
            this.toggleSort(col.name);
        }
    }

    // ==================== ROW / CELL FORMATTING ====================

    formatCell(value, colType, rowType) {
        if (value === null || value === undefined || value === "") {
            return "";
        }
        if (colType === "monetary" || colType === "number" || colType === "integer") {
            return value === 0 ? "" : this.formatNumber(value, 0);
        }
        if (colType === "float") {
            return value === 0 ? "" : this.formatNumber(value, 2);
        }
        if (colType === "date") {
            return this.formatDate(value);
        }
        return value;
    }

    /** Class of the <tr>, by row type */
    getDataRowClass(row) {
        const cls = [];
        switch (row.type) {
            case "group_hdr":
                cls.push("o_vn_group_row");
                break;
            case "opening":
                cls.push("o_vn_opening_row");
                break;
            case "closing":
                cls.push("o_vn_closing_row");
                break;
            case "group_total":
            case "grand_total":
                cls.push("o_vn_total_row", "fw-bold");
                break;
            default:
                cls.push("o_vn_detail_row");
        }
        if (row.isParent) {
            cls.push("fw-bold");
        }
        if (row.expandable) {
            cls.push("o_vn_clickable");
        }
        return cls.join(" ");
    }

    /** Class of a data <td> */
    getCellClass(row, col) {
        if (["monetary", "number", "integer", "float"].includes(col.type)) {
            return "text-end";
        }
        if (col.align === "C" || col.align === "center") {
            return "text-center";
        }
        return "";
    }

    /** Class of a column header <th> */
    getColHeaderClass(col) {
        return col.sortable ? "text-center o_vn_sortable" : "text-center";
    }

    getColHeaderStyle(col) {
        const parts = [];
        if (col.width) {
            parts.push(`width: ${col.width}px`);
        }
        if (col.sortable) {
            parts.push("cursor: pointer");
        }
        return parts.join("; ");
    }

    /** Class of the <td> of a row spanning all the columns */
    getSpanCellClass(row) {
        return row.type === "group_hdr" ? "o_vn_group_header" : "text-center fw-bold";
    }

    /** Label of a row spanning all the columns (e.g. the name of the group) */
    getSpanLabel(row) {
        if (row.label) {
            return row.label;
        }
        return row.cells.find((c) => c !== "" && c != null) || "";
    }

    /** Indentation of a hierarchy level, applied to the first cell */
    getRowIndentStyle(row) {
        return row.level ? `padding-left: ${8 + row.level * 20}px;` : "";
    }

    onRowClick(row) {
        if (row.expandable) {
            this.toggleNode(row.id);
        }
    }

    /** Menu items of a row, by row type */
    getRowMenuItems(row) {
        if (!row.data) {
            return [];
        }
        switch (row.type) {
            case "group_hdr":
                return this.getGroupMenuItems(row.data);
            case "data":
                return this.getLineMenuItems(row.data);
            default:
                return [];
        }
    }
}

export default AbstractVNReport;
