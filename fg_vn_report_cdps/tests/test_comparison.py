from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import JANUARY, CDPSCommon


@tagged('post_install', '-at_install')
class TestCDPSComparison(CDPSCommon):

    def _dates(self, date_from, date_to, comparison_type, **options):
        return self.Report._get_comparison_dates(
            date.fromisoformat(date_from), date.fromisoformat(date_to), comparison_type, options,
        )

    # ------------------------------------------------------------------ dates

    def test_previous_period_of_a_month(self):
        self.assertEqual(
            self._dates('2026-02-01', '2026-02-28', 'previous_period'),
            (date(2026, 1, 1), date(2026, 1, 31)),
        )
        self.assertEqual(
            self._dates('2026-03-01', '2026-03-31', 'previous_period'),
            (date(2026, 2, 1), date(2026, 2, 28)),
        )

    def test_previous_period_of_a_quarter_and_a_year(self):
        self.assertEqual(
            self._dates('2026-04-01', '2026-06-30', 'previous_period'),
            (date(2026, 1, 1), date(2026, 3, 31)),
        )
        self.assertEqual(
            self._dates('2026-01-01', '2026-12-31', 'previous_period'),
            (date(2025, 1, 1), date(2025, 12, 31)),
        )

    def test_previous_period_of_any_range(self):
        # 10 days, not whole months: the 10 days before
        self.assertEqual(
            self._dates('2026-01-11', '2026-01-20', 'previous_period'),
            (date(2026, 1, 1), date(2026, 1, 10)),
        )
        self.assertEqual(
            self._dates('2026-01-01', '2026-01-15', 'previous_period'),
            (date(2025, 12, 17), date(2025, 12, 31)),
        )

    def test_same_period_last_year(self):
        self.assertEqual(
            self._dates('2026-01-01', '2026-03-31', 'same_period_last_year'),
            (date(2025, 1, 1), date(2025, 3, 31)),
        )
        # leap year: the end of February stays the end of February
        self.assertEqual(
            self._dates('2028-02-01', '2028-02-29', 'same_period_last_year'),
            (date(2027, 2, 1), date(2027, 2, 28)),
        )
        self.assertEqual(
            self._dates('2025-02-01', '2025-02-28', 'same_period_last_year'),
            (date(2024, 2, 1), date(2024, 2, 29)),
        )
        self.assertEqual(
            self._dates('2026-01-05', '2026-01-20', 'same_period_last_year'),
            (date(2025, 1, 5), date(2025, 1, 20)),
        )

    def test_custom_period(self):
        self.assertEqual(
            self._dates(
                '2026-01-01', '2026-01-31', 'custom',
                comparison_date_from='2024-07-01', comparison_date_to='2024-09-30',
            ),
            (date(2024, 7, 1), date(2024, 9, 30)),
        )

    def test_custom_period_must_be_complete_and_ordered(self):
        with self.assertRaises(UserError):
            self._dates('2026-01-01', '2026-01-31', 'custom', comparison_date_from='2024-07-01')
        with self.assertRaises(UserError):
            self._dates(
                '2026-01-01', '2026-01-31', 'custom',
                comparison_date_from='2024-09-30', comparison_date_to='2024-07-01',
            )

    def test_no_comparison(self):
        self.assertEqual(self._dates('2026-01-01', '2026-01-31', 'none'), (None, None))
        self.assertEqual(self._dates('2026-01-01', '2026-01-31', False), (None, None))
        self.assertEqual(self._dates('2026-01-01', '2026-01-31', 'previous_month'), (None, None))

    # ---------------------------------------------------------------- figures

    def test_compared_figures(self):
        report = self._report(comparison_type='previous_period')
        self.assertTrue(report['has_comparison'])
        self.assertEqual(report['comparison_label'], "Previous period (01/12/2025 - 31/12/2025)")
        lines = {line['code']: line for line in report['lines']}

        cash = lines['1111']
        self.assertEqual((cash['prev_closing_debit'], cash['prev_closing_credit']), (1000, 0))
        self.assertEqual(cash['variance'], -300)
        self.assertAlmostEqual(cash['variance_percent'], -30.0)

        # nothing in the compared period
        bank = lines['1112']
        self.assertEqual((bank['prev_closing_debit'], bank['variance'], bank['variance_percent']), (0, 200, 100.0))

        equity = lines['411']
        self.assertEqual(equity['prev_closing_credit'], 1000)
        self.assertEqual(equity['variance'], -50)
        self.assertAlmostEqual(equity['variance_percent'], -5.0)

        self.assertEqual(report['totals']['prev_closing_debit'], 1000)
        self.assertEqual(report['totals']['prev_closing_credit'], 1000)

    def test_compared_figures_in_the_hierarchy(self):
        lines = self._lines(comparison_type='previous_period', hierarchy=True)
        parent = lines['111']
        self.assertEqual(parent['prev_closing_debit'], 1000)
        self.assertEqual(parent['variance'], -50)
        self.assertAlmostEqual(parent['variance_percent'], -5.0)

    def test_custom_comparison(self):
        report = self._report(
            comparison_type='custom',
            comparison_date_from='2025-12-01', comparison_date_to='2025-12-10',
        )
        self.assertEqual(report['comparison_label'], "Compared period (01/12/2025 - 10/12/2025)")
        # the opening entry is dated 2025-12-15
        self.assertEqual(report['totals']['prev_closing_debit'], 0)

    def test_columns(self):
        data = self.Report.get_report_data({**JANUARY, 'comparison_type': 'same_period_last_year'})
        self.assertEqual(len(data['columns']), 12)
        self.assertEqual(
            [column['name'] for column in data['columns'][8:]],
            ['prev_closing_debit', 'prev_closing_credit', 'variance', 'variance_percent'],
        )
        data = self.Report.get_report_data({**JANUARY, 'comparison_type': 'none'})
        self.assertEqual(len(data['columns']), 8)
        self.assertNotIn('variance', data['lines'][0]['lines'][0])
