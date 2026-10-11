import json

from odoo import http
from odoo.http import request
from odoo.http.stream import content_disposition


class VNReportController(http.Controller):
    """ Export routes shared by the Vietnamese reports:
    /vn_report/<model_name>/export/<format>
    """

    def _export(self, model_name, options, method, extension, content_type, filename_code=None):
        """ Call `method` of the report `model_name` and return its result as a
        file to download.

        :param str options: JSON-encoded options of the report
        :param str filename_code: start of the file name, for a format that is
            not named after the code of the report
        """
        options = json.loads(options) if options else {}

        try:
            report = request.env[model_name]
        except KeyError:
            raise request.not_found() from None

        # only the report models (inheriting vn.report.access.mixin) having that export
        if not getattr(report, '_is_vn_report', False) or not hasattr(type(report), method):
            raise request.not_found()

        # the export methods check the access themselves
        content = getattr(report, method)(options)

        report_code = filename_code or report._get_export_filename_code(options) or ''
        report_code = report_code.replace(' ', '_')
        date_from = options.get('date', {}).get('date_from', '')
        date_to = options.get('date', {}).get('date_to', '')
        filename = f"{report_code}_{date_from}_{date_to}.{extension}"

        return request.make_response(
            content,
            headers=[
                ('Content-Type', content_type),
                ('Content-Disposition', content_disposition(filename)),
            ],
        )

    @http.route('/vn_report/<string:model_name>/export/xlsx', type='http', auth='user')
    def export_xlsx(self, model_name, options=None, **kw):
        return self._export(
            model_name, options, 'get_xlsx', 'xlsx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @http.route('/vn_report/<string:model_name>/export/pdf_rl', type='http', auth='user')
    def export_pdf_rl(self, model_name, options=None, **kw):
        return self._export(model_name, options, 'get_pdf_rl', 'pdf', 'application/pdf')
