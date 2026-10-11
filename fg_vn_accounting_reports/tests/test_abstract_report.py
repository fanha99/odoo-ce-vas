from datetime import datetime, timezone

from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged

from .common import FakeReportMixin


@tagged('post_install', '-at_install')
class TestAbstractReport(FakeReportMixin, TransactionCase):

    # ---------------------------------------------------------------- options

    @freeze_time('2026-03-17 03:00:00')
    def test_default_options(self):
        options = self.Report._get_default_options()
        self.assertEqual(options['date'], {
            'date_from': '2026-03-01',
            'date_to': '2026-03-17',
            'mode': 'range',
        })
        self.assertEqual(options['company_id'], self.report_user.company_id.id)
        self.assertFalse(options['show_zero_balance'])

    def test_default_options_keep_the_given_ones(self):
        given = {'date': {'date_from': '2025-01-01', 'date_to': '2025-12-31'}, 'show_zero_balance': True}
        options = self.Report._get_default_options(given)
        self.assertEqual(options['date']['date_from'], '2025-01-01')
        self.assertTrue(options['show_zero_balance'])
        self.assertNotIn('company_id', given, "the given dict must not be modified")

    # --------------------------------------------------------------- timezone

    def test_utc_range_in_vietnam_time(self):
        self.report_user.tz = 'Asia/Ho_Chi_Minh'
        date_from, date_to = self.Report._convert_date_to_utc_range('2024-01-01', '2024-01-31')
        self.assertEqual(date_from, datetime(2023, 12, 31, 17, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(date_to, datetime(2024, 1, 31, 16, 59, 59, 999999, tzinfo=timezone.utc))

    def test_utc_range_defaults_to_vietnam_time(self):
        self.report_user.tz = False
        date_from, _date_to = self.Report._convert_date_to_utc_range('2024-01-01', '2024-01-31')
        self.assertEqual(date_from, datetime(2023, 12, 31, 17, 0, 0, tzinfo=timezone.utc))

    def test_utc_range_in_a_timezone_with_dst(self):
        self.report_user.tz = 'Europe/Brussels'
        date_from, date_to = self.Report._convert_date_to_utc_range('2024-03-01', '2024-07-31')
        # winter time is UTC+1, summer time is UTC+2
        self.assertEqual(date_from, datetime(2024, 2, 29, 23, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(date_to, datetime(2024, 7, 31, 21, 59, 59, 999999, tzinfo=timezone.utc))

    def test_utc_datetime_range_from_options(self):
        self.report_user.tz = 'Asia/Ho_Chi_Minh'
        result = self.Report._get_utc_datetime_range({
            'date': {'date_from': '2024-01-01', 'date_to': '2024-01-31'},
        })
        self.assertEqual(result['date_from'], datetime(2023, 12, 31, 17, 0, 0, tzinfo=timezone.utc))

    # --------------------------------------------------------------- language

    def test_report_language_defaults_to_vietnamese(self):
        self.assertEqual(self.report_user.lang, 'en_US')
        data = self.Report.get_report_data({})
        self.assertEqual(data['options']['lang'], 'vi_VN')
        self.assertIn({'code': 'vi_VN', 'name': self.env['res.lang']._get_data(code='vi_VN').name}, data['languages'])

    def test_report_language_follows_the_option(self):
        data = self.Report.get_report_data({'lang': 'en_US'})
        self.assertEqual(data['options']['lang'], 'en_US')

    def test_report_language_ignores_a_language_not_installed(self):
        data = self.Report.get_report_data({'lang': 'xx_XX'})
        self.assertEqual(data['options']['lang'], 'vi_VN')

    def test_report_language_without_vietnamese(self):
        self.env['res.lang']._get_data(code='vi_VN')  # installed by the setup
        self.env['res.lang'].search([('code', '=', 'vi_VN')]).active = False
        data = self.Report.get_report_data({})
        self.assertEqual(data['options']['lang'], 'en_US')

    def test_figures_are_computed_in_the_report_language(self):
        seen = []
        self.patch(
            self.registry['vn.abstract.report'], '_get_lines',
            lambda report, options: seen.append(report.env.lang) or [],
        )
        self.Report.get_report_data({})
        self.Report.get_report_data({'lang': 'en_US'})
        self.assertEqual(seen, ['vi_VN', 'en_US'])

    # ------------------------------------------------------------ report data

    def test_report_data_structure(self):
        options = {'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'}
        data = self.Report.get_report_data(options)
        self.assertEqual(data['header'], {
            'title': "Report",
            'template_code': 'S00 TEST',
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
        })
        self.assertEqual([column['name'] for column in data['columns']], ['date', 'name', 'debit', 'credit'])
        self.assertEqual(data['lines'], self.groups)
        self.assertEqual(data['company']['name'], self.report_user.company_id.name)

    # -------------------------------------------------------------- drill down

    def test_drill_down_action_is_completed(self):
        action = self.Report.action_drill_down({}, {'id': 7})
        self.assertEqual(action['views'], [(False, 'list'), (False, 'form')])
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['domain'], [('id', '=', 7)])

    def test_drill_down_without_action(self):
        self.patch(
            self.registry['vn.abstract.report'], '_get_drill_down_action',
            lambda report, options, params: False,
        )
        self.assertFalse(self.Report.action_drill_down({}, {}))

    # ---------------------------------------------------------------- helpers

    def test_format_helpers(self):
        self.assertEqual(self.Report._format_date('2026-01-31 10:00:00'), '2026-01-31')
        self.assertEqual(self.Report._format_date(datetime(2026, 1, 31)), '2026/01/31')
        self.assertEqual(self.Report._format_date(False), '')
        self.assertEqual(self.Report._format_number('12.345'), 12.35)
        self.assertEqual(self.Report._format_number(None), '')
