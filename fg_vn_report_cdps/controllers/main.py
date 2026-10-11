from odoo import http
from odoo.addons.fg_vn_accounting_reports.controllers.main import VNReportController


class CDPSReportController(VNReportController):

    @http.route('/vn_report/vn.report.cdps/export/xml', type='http', auth='user')
    def export_cdps_xml(self, options=None, **kw):
        return self._export(
            'vn.report.cdps', options, 'get_xml', 'xml', 'application/xml',
            filename_code='F01-CDTK',
        )
