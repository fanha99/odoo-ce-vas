import json
from xml.etree import ElementTree as ET

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged

from .common import JANUARY, CDPSCommon


@tagged('post_install', '-at_install')
class TestCDPSAccess(CDPSCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = new_test_user(
            cls.env, login='fg_cdps_accountant', groups='account.group_account_user',
        )
        cls.employee = new_test_user(cls.env, login='fg_cdps_employee', groups='base.group_user')

    def test_accountant_reads_the_report(self):
        Report = self.Report.with_user(self.accountant)
        self.assertTrue(Report.get_report_data(dict(JANUARY))['lines'][0]['lines'])
        self.assertTrue(Report.get_xml(dict(JANUARY)))

    def test_employee_is_refused(self):
        Report = self.Report.with_user(self.employee)
        for method in ('get_report_data', 'get_xlsx', 'get_pdf_rl', 'get_xml'):
            with self.assertRaises(AccessError, msg=method):
                getattr(Report, method)(dict(JANUARY))

    def test_another_company_is_refused(self):
        other_company = self.env['res.company'].create({'name': "FG other company"})
        Report = self.Report.with_user(self.accountant)
        for method in ('get_report_data', 'get_xml'):
            with self.assertRaises(AccessError, msg=method):
                getattr(Report, method)({**JANUARY, 'company_id': other_company.id})

    def test_readonly_accountant_is_refused(self):
        readonly = new_test_user(
            self.env, login='fg_cdps_readonly', groups='account.group_account_readonly',
        )
        with self.assertRaises(AccessError):
            self.Report.with_user(readonly).get_report_data(dict(JANUARY))

    # ------------------------------------------------------------------ route

    def _export_xml(self):
        return self.url_open(
            '/vn_report/vn.report.cdps/export/xml', params={'options': json.dumps(JANUARY)},
        )

    def test_xml_route(self):
        self.authenticate('fg_cdps_accountant', 'fg_cdps_accountant')
        response = self._export_xml()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/xml')
        self.assertIn('F01-CDTK_2026-01-01_2026-01-31.xml', response.headers['Content-Disposition'])
        self.assertEqual(ET.fromstring(response.content).tag, 'PL_CDTK')

    def test_xml_route_is_refused_to_an_employee(self):
        self.authenticate('fg_cdps_employee', 'fg_cdps_employee')
        with self.assertLogs('odoo.http', level='WARNING'):
            response = self._export_xml()
        self.assertEqual(response.status_code, 403)

    def test_generic_routes_serve_the_report(self):
        self.authenticate('fg_cdps_accountant', 'fg_cdps_accountant')
        for export_format, start in (('xlsx', b'PK'), ('pdf_rl', b'%PDF')):
            response = self.url_open(
                f'/vn_report/vn.report.cdps/export/{export_format}',
                params={'options': json.dumps(JANUARY)},
            )
            self.assertEqual(response.status_code, 200, export_format)
            self.assertTrue(response.content.startswith(start), export_format)
            self.assertIn('Trial_Balance_2026-01-01_2026-01-31', response.headers['Content-Disposition'])
