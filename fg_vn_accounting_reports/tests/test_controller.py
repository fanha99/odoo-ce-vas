import io
import json

from openpyxl import load_workbook

from odoo.tests import HttpCase, tagged

from .common import REPORT_MODEL, FakeReportMixin

OPTIONS = {'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'}


@tagged('post_install', '-at_install')
class TestReportController(FakeReportMixin, HttpCase):

    def _export(self, export_format, model=REPORT_MODEL, options=None):
        return self.url_open(
            f'/vn_report/{model}/export/{export_format}',
            params={'options': json.dumps(options or OPTIONS)},
        )

    def test_export_xlsx(self):
        self.authenticate('fg_report_user', 'fg_report_user')
        response = self._export('xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('S00_TEST_2026-01-01_2026-01-31.xlsx', response.headers['Content-Disposition'])
        sheet = load_workbook(io.BytesIO(response.content))['Sheet1']
        self.assertEqual(sheet['A1'].value, "Report")

    def test_export_pdf(self):
        self.authenticate('fg_report_user', 'fg_report_user')
        response = self._export('pdf_rl')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/pdf')
        self.assertIn('S00_TEST_2026-01-01_2026-01-31.pdf', response.headers['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_export_requires_a_login(self):
        response = self._export('xlsx')
        self.assertNotEqual(
            response.headers.get('Content-Type'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_export_is_refused_to_a_user_not_in_the_group(self):
        self.authenticate('fg_other_user', 'fg_other_user')
        with self.assertLogs('odoo.http', level='WARNING'):
            response = self._export('xlsx')
        self.assertEqual(response.status_code, 403)

    def test_export_is_refused_for_another_company(self):
        other_company = self.env['res.company'].create({'name': "FG other company"})
        self.authenticate('fg_report_user', 'fg_report_user')
        with self.assertLogs('odoo.http', level='WARNING'):
            response = self._export('pdf_rl', options={**OPTIONS, 'company_id': other_company.id})
        self.assertEqual(response.status_code, 403)

    def test_export_of_an_unknown_model(self):
        self.authenticate('fg_report_user', 'fg_report_user')
        self.assertEqual(self._export('xlsx', model='vn.report.unknown').status_code, 404)

    def test_export_of_a_model_that_is_not_a_report(self):
        self.authenticate('fg_report_user', 'fg_report_user')
        # res.partner has no get_xlsx; account.move has none either, and neither is a report
        self.assertEqual(self._export('xlsx', model='res.partner').status_code, 404)
        self.assertEqual(self._export('pdf_rl', model='vn.report.access.mixin').status_code, 404)
