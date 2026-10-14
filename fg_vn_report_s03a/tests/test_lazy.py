from unittest.mock import patch

from odoo.tests import tagged

from .common import JANUARY, S03aCommon


@tagged('post_install', '-at_install')
class TestS03aLazy(S03aCommon):
    """ A long journal is loaded by chunks, in the same order and with the
    same totals as the journal loaded at once. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 12 entries of 3 items, 2 a day, and a deposit pair in the middle
        for index in range(12):
            cls._post('2026-01-%02d' % (index // 2 + 1), [
                ('131', 110 + index, 0, {'name': f"Sale {index}"}),
                ('511', 0, 100 + index, {'name': f"Sale {index}"}),
                ('33311', 0, 10, {'name': f"VAT {index}"}),
            ])
        cls.cash_move, cls.bank_move = cls._deposit('2026-01-03', 500)
        cls._hide_transfer_account()
        cls.line_count = 12 * 3 + 2

    def _set_param(self, name, value):
        self.env['ir.config_parameter'].sudo().set_int(f'fg_vn_accounting_reports.{name}', value)

    def _all_at_once(self, **options):
        self._set_param('lazy_line_threshold', 100000)
        data = self.Report.get_report_data({**JANUARY, **options})
        self.assertFalse(data['lazy'])
        return data['lines'][0]

    def _lazy(self, chunk_size=7, **options):
        self._set_param('lazy_line_threshold', 10)
        self._set_param('lazy_chunk_size', chunk_size)
        data = self.Report.get_report_data({**JANUARY, **options})
        self.assertTrue(data['lazy'])
        return data['lines'][0]

    def _load_everything(self, group, **options):
        lines = list(group['lines'])
        chunks = [len(lines)]
        while len(lines) < group['line_count']:
            result = self.Report.get_group_lines({**JANUARY, **options}, group['id'], len(lines))
            self.assertTrue(result['lines'], "the server stopped before the end")
            self.assertEqual(result['offset'], len(lines) + len(result['lines']))
            lines += result['lines']
            chunks.append(len(result['lines']))
        return lines, chunks

    def test_first_load(self):
        group = self._lazy()
        self.assertEqual(group['line_count'], self.line_count)
        # 7 lines asked: 3 entries of 3 items, an entry is never cut
        self.assertEqual(len(group['lines']), 9)
        # the total is the one of the whole journal
        full = self._all_at_once()
        self.assertEqual(group['total'], full['total'])
        self.assertEqual(group['total_label'], "Total")

    def test_chunks_rebuild_the_whole_journal(self):
        full = self._all_at_once()
        group = self._lazy()
        lines, chunks = self._load_everything(group)
        self.assertEqual(lines, full['lines'])
        self.assertGreater(len(chunks), 3)
        self.assertEqual(len({line['id'] for line in lines}), self.line_count)

    def test_entries_are_never_cut(self):
        group = self._lazy(chunk_size=4)
        lines, _chunks = self._load_everything(group)
        result = self.Report.get_group_lines(dict(JANUARY), group['id'], 0)
        last_move = result['lines'][-1]['move_id']
        self.assertEqual(
            len([line for line in result['lines'] if line['move_id'] == last_move]),
            len([line for line in lines if line['move_id'] == last_move]),
        )

    def test_linked_entries_keep_their_place_and_number(self):
        group = self._lazy(chunk_size=3)
        lines, _chunks = self._load_everything(group)
        name = f"{self.bank_move.name} ({self.cash_move.name})"
        deposit = [line for line in lines if line['move_name'] == name]
        self.assertEqual(
            [(line['account_code'], line['debit'], line['credit']) for line in deposit],
            [(self.bank.code, 500, 0), (self.cash.code, 0, 500)],
        )
        positions = [lines.index(line) for line in deposit]
        self.assertEqual(positions[1], positions[0] + 1)

    def test_chunks_follow_the_number_printed(self):
        """ Journals printing the reference, or the number without its
        trailing sequence: the chunks are in the order of the number printed. """
        self.bank_move.ref = "GBC-0042"
        self.bank_journal.fg_use_ref_as_doc_no = True
        self.misc_journal.fg_truncate_seq_as_doc_no = True
        self.cash_journal.fg_truncate_seq_as_doc_no = True
        full = self._all_at_once()
        names = {line['move_name'] for line in full['lines']}
        self.assertIn(f"GBC-0042 ({self.cash_move.name.rsplit('/', 1)[0]})", names)
        self.assertEqual(len(names), 2, "the 12 sales are printed with the same number")
        lines, _chunks = self._load_everything(self._lazy(chunk_size=4))
        self.assertEqual(lines, full['lines'])

    def test_nothing_after_the_end(self):
        self._lazy()
        result = self.Report.get_group_lines(dict(JANUARY), 'journal', self.line_count)
        self.assertEqual(result, {'lines': [], 'offset': self.line_count})

    def test_filters_apply_to_the_chunks(self):
        options = {'account_ids': self.accounts['131'].ids}
        self._set_param('lazy_line_threshold', 5)
        self._set_param('lazy_chunk_size', 5)
        data = self.Report.get_report_data({**JANUARY, **options})
        self.assertTrue(data['lazy'])
        group = data['lines'][0]
        self.assertEqual(group['line_count'], 12)
        lines, _chunks = self._load_everything(group, **options)
        self.assertEqual({line['account_code'] for line in lines}, {'131'})
        self.assertEqual(len(lines), 12)

    def test_search_applies_to_the_whole_journal(self):
        group = self._lazy(chunk_size=3, search='VAT')
        self.assertEqual(group['line_count'], 12)
        self.assertEqual(group['total'], {'debit': 0, 'credit': 120})
        lines, _chunks = self._load_everything(group, search='VAT')
        self.assertEqual({line['account_code'] for line in lines}, {'33311'})

    def test_search_narrowing_under_the_threshold_sends_everything(self):
        self._set_param('lazy_line_threshold', 10)
        data = self.Report.get_report_data({**JANUARY, 'search': 'Sale 11'})
        self.assertFalse(data['lazy'])
        self.assertEqual(len(data['lines'][0]['lines']), 2)

    def test_query_count_of_a_chunk_does_not_depend_on_the_journal_length(self):
        self._lazy(chunk_size=6)

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
                self.Report.get_group_lines(dict(JANUARY), 'journal', 0)
            return len([query for query in queries if 'account_move_line' in query])

        before = count_queries()
        for index in range(10):
            self._post('2026-01-20', [('131', 5 + index, 0), ('511', 0, 5 + index)])
        self.assertEqual(count_queries(), before)
