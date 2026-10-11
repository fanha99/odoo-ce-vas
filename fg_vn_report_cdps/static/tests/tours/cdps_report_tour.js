import { registry } from "@web/core/registry";

const TABLE = ".o_vn_report_table";

/**
 * Walks through the screen of the trial balance: wizard, hierarchy folding,
 * search, filters, comparison, period, drill-down and back. The test data
 * are entries of the current month on the accounts "FGT ...".
 */
registry.category("web_tour.tours").add("fg_vn_report_cdps_tour", {
    steps: () => [
        // ------------------------------------------------------------ wizard
        {
            content: "Ask for the account hierarchy",
            trigger: ".modal div[name=hierarchy] input",
            run: "click",
        },
        {
            content: "Open the report",
            trigger: ".modal button[name=action_view_report]",
            run: "click",
        },
        // ----------------------------------------------------------- language
        {
            content: "The report opens in Vietnamese, whatever the language of the user",
            trigger: `${TABLE} td:contains(FGT Tiền mặt)`,
        },
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "Switch the report to English",
            trigger: ".o_vn_filter_lang select",
            run: "select en_US",
        },
        {
            content: "Apply",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        // ---------------------------------------------------------- hierarchy
        {
            content: "The report is displayed, with the parent accounts unfolded at the top level",
            trigger: `${TABLE} tr.o_cdps_root_row td:contains(FGT Cash)`,
        },
        {
            content: "The children of the top-level parent are visible",
            trigger: `${TABLE} td:contains(FGT Cash VND)`,
        },
        {
            content: "The title is in English",
            trigger: ".o_vn_report_title_text:contains(TRIAL BALANCE)",
        },
        {
            content: "The grand total is the last row",
            trigger: `${TABLE} tr.o_vn_total_row:last td:contains(TOTAL)`,
        },
        {
            content: "Fold the parent account by clicking its row",
            trigger: `${TABLE} tr.o_cdps_root_row td:contains(FGT Cash)`,
            run: "click",
        },
        {
            content: "Its children are hidden",
            trigger: `${TABLE}:not(:has(td:contains(FGT Cash VND)))`,
        },
        {
            content: "Unfold everything",
            trigger: ".o_vn_btn_icon:has([data-icon=keyboard_double_arrow_down])",
            run: "click",
        },
        {
            content: "The children are back",
            trigger: `${TABLE} td:contains(FGT Cash VND)`,
        },
        {
            content: "Fold everything",
            trigger: ".o_vn_btn_icon:has([data-icon=keyboard_double_arrow_up])",
            run: "click",
        },
        {
            content: "The children are hidden again",
            trigger: `${TABLE}:not(:has(td:contains(FGT Cash VND)))`,
        },
        // ------------------------------------------------------------- search
        {
            content: "Search an account",
            trigger: ".o_vn_search_box input",
            run: "edit FGT Expense",
        },
        {
            content: "Only the matching account is listed, with the total",
            trigger: `${TABLE}:has(td:contains(FGT Expense)):not(:has(td:contains(FGT Cash)))`,
        },
        {
            content: "Clear the search",
            trigger: ".o_vn_search_box input",
            run: "clear",
        },
        {
            content: "All the accounts are back",
            trigger: `${TABLE} td:contains(FGT Cash)`,
        },
        // ------------------------------------------------------------ filters
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "The dates of a custom comparison are hidden",
            trigger: ".o_vn_filter_menu:not(:has([data-filter=comparison_date_from]))",
        },
        {
            content: "Choose a custom comparison",
            trigger: ".o_vn_filter_item[data-filter=comparison_type] select",
            run: "select custom",
        },
        {
            content: "The dates of the custom comparison are shown",
            trigger: ".o_vn_filter_item[data-filter=comparison_date_to] input[type=date]",
        },
        {
            content: "Compare with the previous period instead",
            trigger: ".o_vn_filter_item[data-filter=comparison_type] select",
            run: "select previous_period",
        },
        {
            content: "Leave the hierarchy",
            trigger: ".o_vn_filter_item[data-filter=show_hierarchy] input",
            run: "click",
        },
        {
            content: "Apply the filters",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        {
            content: "The comparison columns are added (action column + 12 columns)",
            trigger: `${TABLE} .o_vn_header_row th:eq(12):contains(%)`,
        },
        {
            content: "Without hierarchy, parents and children are plain rows",
            trigger: `${TABLE}:not(:has(.o_vn_caret)) td:contains(FGT Cash VND)`,
        },
        {
            content: "The number of active filters is shown",
            trigger: ".o_vn_filter_btn .o_vn_badge",
        },
        // ------------------------------------------------------ account level
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "Keep the accounts of level 1 only",
            trigger: ".o_vn_filter_item[data-filter=account_level] select",
            run: "select 1",
        },
        {
            content: "Apply the filters",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        {
            content: "The accounts with a longer code are hidden",
            trigger: `${TABLE}:has(td:contains(FGT Cash)):not(:has(td:contains(FGT Cash VND)))`,
        },
        // ------------------------------------------------------------- period
        {
            content: "Open the period menu",
            trigger: ".o_vn_date_btn",
            run: "click",
        },
        {
            content: "Choose this year",
            trigger: ".o_vn_date_menu .o_vn_date_item:contains(This year)",
            run: "click",
        },
        {
            content: "The period is shown on the button",
            trigger: ".o_vn_date_btn:contains(This year)",
        },
        // --------------------------------------------------------- drill-down
        {
            content: "Open the journal items of an account",
            trigger: `${TABLE} tr:has(td:contains(FGT Expense)) .o_vn_drilldown_btn`,
            run: "click",
        },
        {
            content: "The journal items are listed",
            trigger: ".o_list_view .o_data_row",
        },
        {
            content: "The breadcrumb names the report",
            trigger: ".o_breadcrumb .breadcrumb-item a:contains(Trial Balance)",
        },
        {
            content: "Go back to the report",
            trigger: ".o_back_button, .breadcrumb-item a",
            run: "click",
        },
        {
            content: "The report kept its period",
            trigger: ".o_vn_date_btn:contains(This year)",
        },
        {
            content: "The report kept its comparison and its account level",
            trigger: `${TABLE}:not(:has(td:contains(FGT Cash VND))) .o_vn_header_row th:eq(12)`,
        },
        // ------------------------------------------------------------- reload
        {
            content: "Reload the page",
            trigger: `${TABLE}`,
            run() {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        {
            content: "The report kept its period after the reload",
            trigger: ".o_vn_date_btn:contains(This year)",
        },
        {
            content: "The report kept its language, comparison and account level after the reload",
            trigger: `${TABLE}:has(td:contains(FGT Cash)):not(:has(td:contains(FGT Cash VND))) .o_vn_header_row th:eq(12)`,
        },
        {
            content: "Open the journal items of an account again, after the reload",
            trigger: `${TABLE} tr:has(td:contains(FGT Expense)) .o_vn_drilldown_btn`,
            run: "click",
        },
        {
            content: "The breadcrumb still names the report, though the reloaded action has no name",
            trigger: ".o_list_view:has(.o_data_row) .o_breadcrumb .breadcrumb-item a:contains(Trial Balance)",
        },
        {
            content: "Go back to the report",
            trigger: ".o_back_button, .breadcrumb-item a",
            run: "click",
        },
        {
            content: "The report is back",
            trigger: `${TABLE} td:contains(FGT Cash)`,
        },
        // ----------------------------------------------------------- language
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "Switch the report to Vietnamese",
            trigger: ".o_vn_filter_lang select",
            run: "select vi_VN",
        },
        {
            content: "Apply",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        {
            content: "The account names are in Vietnamese",
            trigger: `${TABLE} td:contains(FGT Tiền mặt)`,
        },
        // ------------------------------------------------------------ exports
        {
            content: "The three exports are offered",
            trigger: ".o_vn_report_actions:has([data-icon=table]):has([data-icon=picture_as_pdf]):has([data-icon=code])",
        },
    ],
});
