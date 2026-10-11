from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_DATA, RT_GROUP_HDR, RT_GROUP_TOTAL, FanhaReportPDF,
)
from odoo.tests import new_test_user

REPORT_MODEL = 'vn.abstract.report'

COLUMNS = [
    {'name': 'date', 'label': "Date", 'type': 'date', 'width': 80},
    {'name': 'name', 'label': "Label", 'type': 'char', 'width': 250},
    {'name': 'debit', 'label': "Debit", 'type': 'monetary', 'width': 120},
    {'name': 'credit', 'label': "Credit", 'type': 'monetary', 'width': 120},
]


def make_groups(group_count=2, line_count=3):
    """ Figures of the fake report: `group_count` groups of `line_count` lines. """
    return [
        {
            'id': f'group_{g}',
            'code': f'11{g}',
            'name': f"Account 11{g}",
            'lines': [
                {
                    'id': f'line_{g}_{i}',
                    'date': '2026-01-%02d' % (i + 1),
                    'name': f"Entry {g}/{i}",
                    'debit': 1000.0 * (i + 1),
                    'credit': 0.0,
                }
                for i in range(line_count)
            ],
        }
        for g in range(group_count)
    ]


def group_to_rows(group):
    """ Typed rows of one group, in the format shared by Excel and PDF. """
    rows = [{'type': RT_GROUP_HDR, 'cells': [group['name']], 'span_all': True}]
    rows += [
        {'type': RT_DATA, 'cells': [line['date'], line['name'], line['debit'], line['credit']]}
        for line in group['lines']
    ]
    rows.append({
        'type': RT_GROUP_TOTAL,
        'cells': ['', "Total", sum(line['debit'] for line in group['lines']), 0.0],
    })
    return rows


class FakeReportPDF(FanhaReportPDF):
    """ Renderer of the fake report: debit and credit are carried forward. """

    def _get_col_specs(self):
        return [
            {'label': "Date", 'width': 60, 'align': 'L'},
            {'label': "Label", 'width': 250, 'align': 'L'},
            {'label': "Debit", 'width': 90, 'align': 'R'},
            {'label': "Credit", 'width': 90, 'align': 'R'},
        ]

    def _get_carry_cols(self):
        return [2, 3]

    def _get_carry_label_col(self):
        return 1

    def _group_to_rows(self, group):
        rows = []
        for index, row in enumerate(group_to_rows(group)):
            cells = row['cells'] + [''] * (4 - len(row['cells']))
            monetary = {}
            if row['type'] == RT_DATA:
                monetary = {2: cells[2], 3: cells[3]}
            rows.append({
                **row,
                'cells': [cells[0], cells[1], self.fmt_number(cells[2]), self.fmt_number(cells[3])],
                'height': None,
                'monetary': monetary,
                'carry_reset': index == 0,
            })
        return rows

    def _groups_to_rows(self, groups):
        return [row for group in groups for row in self._group_to_rows(group)]


class FakeReportMixin:
    """ Turn `vn.abstract.report` itself into a small report by patching its
    hooks, so that the framework is tested without any real report installed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('vi_VN')
        cls.report_user = new_test_user(
            cls.env, login='fg_report_user', groups='account.group_account_user',
        )
        cls.other_user = new_test_user(
            cls.env, login='fg_other_user', groups='base.group_user',
        )
        cls.Report = cls.env[REPORT_MODEL].with_user(cls.report_user)

    def setUp(self):
        super().setUp()
        self.groups = make_groups()
        self.split_by_group = False
        self.renderer_cls = FakeReportPDF
        Report = self.registry[REPORT_MODEL]
        self.patch(Report, '_get_report_name', lambda report: report.env._("Report"))
        self.patch(Report, '_get_report_code', lambda report: 'S00 TEST')
        self.patch(Report, '_get_columns', lambda report: [dict(column) for column in COLUMNS])
        self.patch(Report, '_get_lines', lambda report, options: self.groups)
        self.patch(Report, '_group_to_xlsx_rows', lambda report, group: group_to_rows(group))
        self.patch(Report, '_should_xlsx_split_by_group', lambda report: self.split_by_group)
        self.patch(Report, '_get_pdf_rl_renderer', lambda report: self.renderer_cls)
        self.patch(Report, '_get_drill_down_action', lambda report, options, params: {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', '=', params.get('id'))],
        })
