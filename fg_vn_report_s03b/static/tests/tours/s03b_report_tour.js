import { registry } from "@web/core/registry";

const TABLE = ".o_vn_report_table";
const RECEIVABLE = `${TABLE} tr.o_vn_group_row:has(td:contains(FGT131))`;

const openReport = [
    {
        content: "Open the ledger from the wizard",
        trigger: ".modal button[name=action_view_report]",
        run: "click",
    },
    {
        content: "The ledger is displayed, one group per account",
        trigger: `${RECEIVABLE} td:contains(FGT Receivable)`,
    },
];

/**
 * Small ledger: everything is loaded and unfolded. The test data are 3
 * entries "FGT Sale n": Dr FGT131 110 / Cr FGT511 100, Cr FGT3331 10.
 */
registry.category("web_tour.tours").add("fg_vn_report_s03b_tour", {
    steps: () => [
        ...openReport,
        {
            content: "The accounts are unfolded: opening, items, total and closing rows",
            trigger: `${TABLE}:has(tr.o_vn_opening_row):has(tr.o_vn_closing_row) tr.o_vn_detail_row:eq(8)`,
        },
        {
            content: "An item of the receivable account lists its two counterpart accounts",
            trigger: `${TABLE} tr.o_vn_detail_row td:contains(FGT3331, FGT511)`,
        },
        {
            content: "Fold the receivable account by clicking its header",
            trigger: `${RECEIVABLE} td:contains(FGT Receivable)`,
            run: "click",
        },
        {
            content: "Its items are hidden",
            trigger: `${TABLE}:not(:has(td:contains(FGT3331, FGT511)))`,
        },
        {
            content: "Unfold it again",
            trigger: `${RECEIVABLE} td:contains(FGT Receivable)`,
            run: "click",
        },
        {
            content: "Its items are back",
            trigger: `${TABLE} td:contains(FGT3331, FGT511)`,
        },
        {
            content: "Search an account",
            trigger: ".o_vn_search_box input",
            run: "edit FGT511",
        },
        {
            content: "Only that account is left",
            trigger: `${TABLE}:has(td:contains(FGT Income)):not(:has(td:contains(FGT Receivable)))`,
        },
        {
            content: "Clear the search",
            trigger: ".o_vn_search_box input",
            run: "clear",
        },
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "Search an account in the filter",
            trigger: ".o_vn_filter_item[data-filter=account_ids] input",
            run: "edit FGT131",
        },
        {
            content: "Pick the account found",
            trigger: ".o_vn_filter_item[data-filter=account_ids] .o_vn_filter_search_item:contains(FGT131)",
            run: "click",
        },
        {
            content: "Ask for one line per counterpart account",
            trigger: ".o_vn_filter_item[data-filter=split_counterparts] input",
            run: "click",
        },
        {
            content: "Apply the filters",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        {
            content: "Only the receivable account, with two lines per entry",
            trigger: `${TABLE}:not(:has(td:contains(FGT Income))) tr.o_vn_detail_row:eq(5)`,
        },
        {
            content: "Each line has a single counterpart account",
            trigger: `${TABLE}:not(:has(td:contains(FGT3331, FGT511))) tr.o_vn_detail_row td:contains(FGT3331)`,
        },
        {
            content: "The total of the account is unchanged",
            trigger: `${TABLE} tr.o_vn_total_row td:contains(330)`,
        },
        {
            content: "Open the entry of a line",
            trigger: `${TABLE} tr.o_vn_detail_row:eq(0) .o_vn_drilldown_btn`,
            run: "click",
        },
        {
            content: "The journal entry is opened",
            trigger: ".o_form_view",
        },
        {
            content: "The breadcrumb names the report",
            trigger: ".o_breadcrumb .breadcrumb-item a:contains(General Ledger)",
        },
        {
            content: "Go back to the ledger",
            trigger: ".o_back_button, .breadcrumb-item a",
            run: "click",
        },
        {
            content: "The ledger kept its filters",
            trigger: `${TABLE}:not(:has(td:contains(FGT Income))) tr.o_vn_detail_row:eq(5)`,
        },
    ],
});

/**
 * Long ledger: 45 lines with a threshold of 10 and chunks of 10. The
 * accounts come folded with their figures; the items of an account are
 * loaded when it is unfolded.
 */
registry.category("web_tour.tours").add("fg_vn_report_s03b_lazy_tour", {
    steps: () => [
        ...openReport,
        {
            content: "No journal item is loaded yet",
            trigger: `${TABLE}:not(:has(tr.o_vn_detail_row))`,
        },
        {
            content: "The balances of the folded accounts are shown",
            trigger: `${TABLE} tr.o_vn_closing_row td:contains(1,650)`,
        },
        {
            content: "Unfolding everything is not offered on a long ledger",
            trigger: ".o_vn_report:not(:has(.o_vn_btn_icon [data-icon=keyboard_double_arrow_down]))",
        },
        {
            content: "Unfold the receivable account",
            trigger: `${RECEIVABLE} td:contains(FGT Receivable)`,
            run: "click",
        },
        {
            content: "Its first chunk of items is loaded",
            trigger: `${TABLE}:has(tr.o_vn_detail_row:eq(9)):not(:has(tr.o_vn_detail_row:eq(10))) .o_vn_load_more_row:contains(10 of 15)`,
        },
        {
            content: "Load the rest",
            trigger: ".o_vn_load_more_btn",
            run: "click",
        },
        {
            content: "All its items are there and nothing more is offered",
            trigger: `${TABLE}:has(tr.o_vn_detail_row:eq(14)):not(:has(.o_vn_load_more_row))`,
        },
        {
            content: "Fold the account",
            trigger: `${RECEIVABLE} td:contains(FGT Receivable)`,
            run: "click",
        },
        {
            content: "The items are hidden, the balances stay",
            trigger: `${TABLE}:not(:has(tr.o_vn_detail_row)) tr.o_vn_closing_row td:contains(1,650)`,
        },
    ],
});
