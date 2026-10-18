/** @odoo-module **/

import {ReportAction} from "@web/webclient/actions/reports/report_action";
import {patch} from "@web/core/utils/patch";
import {useEnrichWithActionLinks} from "./report.esm";

const MODULE_NAME = "fg_stock_reports_l10n_vn_ce";

patch(ReportAction.prototype, {
    setup() {
        super.setup(...arguments);
        // Check if this is our stock valuation report
        if (this.props.report_name && this.props.report_name.startsWith(`${MODULE_NAME}.`)) {
            useEnrichWithActionLinks(this.iframe);
        }
    },
});
