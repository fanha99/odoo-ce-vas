import { registry } from "@web/core/registry";

const TABLE = ".o_vn_report_table";
const ROWS = `${TABLE} tr.o_vn_detail_row`;

const openReport = [
    {
        content: "Open the journal from the wizard",
        trigger: ".modal button[name=action_view_report]",
        run: "click",
    },
    {
        content: "The journal is displayed",
        trigger: `${TABLE} tr.o_vn_total_row`,
    },
];

/**
 * Small journal: everything is loaded, the search filters in the browser.
 * The test data are 4 entries "FGT Sale n" of the current quarter.
 */
registry.category("web_tour.tours").add("fg_vn_report_s03a_tour", {
    steps: () => [
        ...openReport,
        {
            content: "The 8 items of the 4 entries are listed",
            trigger: `${ROWS}:eq(7)`,
        },
        {
            content: "Nothing more to load, and everything can be unfolded",
            trigger: `.o_vn_report:not(:has(.o_vn_load_more_row)):has([data-icon=keyboard_double_arrow_down])`,
        },
        {
            content: "An item shows its account on the debit side",
            trigger: `${ROWS}:has(td:contains(FGT Sale 0)) td:contains(FGT131)`,
        },
        {
            content: "Search an entry",
            trigger: ".o_vn_search_box input",
            run: "edit FGT Sale 3",
        },
        {
            content: "Only its two items are left",
            trigger: `${TABLE}:has(td:contains(FGT Sale 3)):not(:has(td:contains(FGT Sale 0)))`,
        },
        {
            content: "The total is the one of the items shown",
            trigger: `${TABLE} tr.o_vn_total_row td:contains(103)`,
        },
        {
            content: "Clear the search",
            trigger: ".o_vn_search_box input",
            run: "clear",
        },
        {
            content: "All the items are back",
            trigger: `${ROWS}:eq(7)`,
        },
        {
            content: "Open the filters",
            trigger: ".o_vn_filter_btn",
            run: "click",
        },
        {
            content: "Search an account in the filter",
            trigger: ".o_vn_filter_item[data-filter=account_ids] input",
            run: "edit FGT511",
        },
        {
            content: "Pick the account found",
            trigger: ".o_vn_filter_item[data-filter=account_ids] .o_vn_filter_search_item:contains(FGT511)",
            run: "click",
        },
        {
            content: "Apply the filters",
            trigger: ".o_vn_filter_actions .o_vn_btn_primary",
            run: "click",
        },
        {
            content: "Only the items on that account are listed",
            trigger: `${TABLE}:has(td:contains(FGT511)):not(:has(td:contains(FGT131)))`,
        },
        {
            content: "Open the entry of an item",
            trigger: `${ROWS}:has(td:contains(FGT Sale 2)) .o_vn_drilldown_btn`,
            run: "click",
        },
        {
            content: "The journal entry is opened",
            trigger: ".o_form_view",
        },
        {
            content: "The breadcrumb names the report",
            trigger: ".o_breadcrumb .breadcrumb-item a:contains(General Journal)",
        },
        {
            content: "Go back to the journal",
            trigger: ".o_back_button, .breadcrumb-item a",
            run: "click",
        },
        {
            content: "The journal kept its account filter",
            trigger: `${TABLE}:has(td:contains(FGT511)):not(:has(td:contains(FGT131)))`,
        },
    ],
});

/**
 * Long journal: 32 lines with a threshold of 10 and chunks of 10. The lines
 * come by chunks and the search is done by the server.
 */
registry.category("web_tour.tours").add("fg_vn_report_s03a_lazy_tour", {
    steps: () => [
        ...openReport,
        {
            content: "The first chunk is there",
            trigger: `${ROWS}:eq(9)`,
        },
        {
            content: "Not the rest, and the journal tells how much is shown",
            trigger: `${TABLE}:not(:has(tr.o_vn_detail_row:eq(10))) .o_vn_load_more_row:contains(10 of 32)`,
        },
        {
            content: "Unfolding everything is not offered on a long journal",
            trigger: ".o_vn_report:not(:has(.o_vn_btn_icon [data-icon=keyboard_double_arrow_down]))",
        },
        {
            content: "The total is the one of the whole journal",
            trigger: `${TABLE} tr.o_vn_total_row td:contains(1,672)`,
        },
        {
            content: "Load more lines",
            trigger: ".o_vn_load_more_btn",
            run: "click",
        },
        {
            content: "The second chunk is added",
            trigger: `${TABLE}:has(tr.o_vn_detail_row:eq(19)) .o_vn_load_more_row:contains(20 of 32)`,
        },
        {
            content: "Search on the server",
            trigger: ".o_vn_search_box input",
            run: "edit FGT Bulk 11",
        },
        {
            content: "The entry is found though it was not loaded, and nothing more is to load",
            trigger: `${TABLE}:has(td:contains(FGT Bulk 11)):not(:has(td:contains(FGT Sale))):not(:has(.o_vn_load_more_row))`,
        },
        {
            content: "The total is the one of the lines found",
            trigger: `${TABLE} tr.o_vn_total_row td:contains(111)`,
        },
        {
            content: "Clear the search",
            trigger: ".o_vn_search_box input",
            run: "clear",
        },
        {
            content: "The journal is back to its first chunk",
            trigger: `${TABLE} .o_vn_load_more_row:contains(10 of 32)`,
        },
    ],
});
