from unittest.mock import patch

from odoo.tests import tagged

from .common import JANUARY, S03bCommon


@tagged('post_install', '-at_install')
class TestS03bLazy(S03bCommon):
    """ A long ledger comes with the figures of its accounts; the journal
    items of an account are loaded by chunks when it is unfolded. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for index in range(10):
            cls._post('2026-01-%02d' % (index + 13), [
                ('131', 110 + index, 0, {'name': f"Sale {index}", 'partner_id': cls.partner_a.id}),
                ('511', 0, 100 + index, {'name': f"Sale {index}"}),
                ('33311', 0, 10, {'name': f"VAT {index}"}),
            ])

    def _set_param(self, name, value):
        self.env['ir.config_parameter'].sudo().set_int(f'fg_vn_accounting_reports.{name}', value)

    def _all_at_once(self, **options):
        self._set_param('lazy_line_threshold', 100000)
        data = self.Report.get_report_data({**JANUARY, **options})
        self.assertFalse(data['lazy'])
        return {group['code']: group for group in data['lines']}

    def _lazy(self, chunk_size=4, **options):
        self._set_param('lazy_line_threshold', 10)
        self._set_param('lazy_chunk_size', chunk_size)
        data = self.Report.get_report_data({**JANUARY, **options})
        self.assertTrue(data['lazy'])
        return {group['code']: group for group in data['lines']}

    def _load_everything(self, group, **options):
        lines = []
        while len(lines) < group['line_count']:
            result = self.Report.get_group_lines({**JANUARY, **options}, group['id'], len(lines))
            self.assertTrue(result['lines'], "the server stopped before the end")
            lines += result['lines']
        return lines

    def test_first_load_has_the_figures_and_no_line(self):
        full = self._all_at_once()
        lazy = self._lazy()
        self.assertEqual(list(lazy), list(full))
        for code, group in lazy.items():
            self.assertEqual(group['lines'], [])
            for key in ('opening', 'total', 'closing', 'line_count', 'label'):
                self.assertEqual(group[key], full[code][key], f"{key} of {code}")
        self.assertEqual(lazy['131']['line_count'], 12)

    def test_chunks_rebuild_the_ledger_of_an_account(self):
        full = self._all_at_once()
        lazy = self._lazy()
        for code in ('131', '511', '33311'):
            self.assertEqual(self._load_everything(lazy[code]), full[code]['lines'], code)

    def test_chunk_size(self):
        group = self._lazy(chunk_size=5)['131']
        result = self.Report.get_group_lines(dict(JANUARY), group['id'], 0)
        self.assertEqual(len(result['lines']), 5)
        self.assertEqual(result['offset'], 5)
        result = self.Report.get_group_lines(dict(JANUARY), group['id'], 10)
        self.assertEqual(len(result['lines']), 2)
        self.assertEqual(self.Report.get_group_lines(dict(JANUARY), group['id'], 12)['lines'], [])

    def test_running_balance_is_continuous_across_chunks(self):
        group = self._lazy(chunk_size=5)['131']
        lines = self._load_everything(group)
        balance = 200  # opening balance
        for line in lines:
            balance += line['debit'] - line['credit']
            self.assertEqual(line['balance'], balance)

    def test_split_counterparts(self):
        full = self._all_at_once(split_counterparts=True)
        lazy = self._lazy(split_counterparts=True)
        # 11 sales of two counterparts each, and the payment
        self.assertEqual(lazy['131']['line_count'], 23)
        self.assertEqual(
            self._load_everything(lazy['131'], split_counterparts=True), full['131']['lines'])

    def test_chunks_follow_the_number_printed(self):
        """ Journals printing the reference: the chunks are in the order of
        the number printed, and the running balance follows. """
        # two sales a day, whose references are not in the entry order
        for index in range(10):
            self._post('2026-01-%02d' % (index + 13), [
                ('131', 50 + index, 0, {'partner_id': self.partner_a.id}),
                ('511', 0, 50 + index),
            ], ref="HD %02d" % (20 - index))
        self.misc_journal.fg_use_ref_as_doc_no = True
        full = self._all_at_once()['131']['lines']
        by_day = {}
        for line in full:
            by_day.setdefault(line['date'], []).append(line['move_name'])
        for names in by_day.values():
            self.assertEqual(names, sorted(names))
        self.assertIn("HD 20", by_day[min(by_day, key=str)] + sum(by_day.values(), []))

        group = self._lazy(chunk_size=5)['131']
        lines = self._load_everything(group)
        self.assertEqual(lines, full)
        balance = 200  # opening balance
        for line in lines:
            balance += line['debit'] - line['credit']
            self.assertEqual(line['balance'], balance)

    def test_filters_apply_to_the_chunks(self):
        options = {'journal_ids': self.bank_journal.ids}
        self._set_param('lazy_line_threshold', 1)
        group = {g['code']: g for g in self.Report.get_report_data({**JANUARY, **options})['lines']}['131']
        self.assertEqual(group['line_count'], 1)
        lines = self._load_everything(group, **options)
        self.assertEqual([line['move_id'] for line in lines], [self.payment.id])

    def test_unknown_group(self):
        self._lazy()
        self.assertEqual(self.Report.get_group_lines(dict(JANUARY), 'account_0', 0)['lines'], [])
        self.assertEqual(self.Report.get_group_lines(dict(JANUARY), 'nonsense', 0)['lines'], [])
        other = self.setup_other_company()
        group_id = 'account_%s' % other['default_account_revenue'].id
        self.assertEqual(self.Report.get_group_lines(dict(JANUARY), group_id, 0)['lines'], [])

    def test_query_count_of_a_chunk_does_not_depend_on_the_ledger_length(self):
        group = self._lazy(chunk_size=5)['131']

        def count_queries():
            """ Queries reading the journal items: the ones that could grow
            with the data. The ORM reads of users and companies vary with the
            state of its caches. """
            self.env.flush_all()
            self.env.invalidate_all()
            cursor_class = type(self.env.cr)
            execute = cursor_class.execute
            queries = []

            def spy(cursor, query, params=None, log_exceptions=True):
                queries.append(str(getattr(query, 'code', query)))
                return execute(cursor, query, params, log_exceptions)

            with patch.object(cursor_class, 'execute', spy):
                self.Report.get_group_lines(dict(JANUARY), group['id'], 0)
            return len([query for query in queries if 'account_move_line' in query])

        before = count_queries()
        for index in range(10):
            self._post('2026-01-25', [('131', 5 + index, 0), ('511', 0, 5 + index)])
        self.assertEqual(count_queries(), before)
