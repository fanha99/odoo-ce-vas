import io

from PyPDF2 import PdfReader

from odoo.addons.fg_vn_accounting_reports.models.pdf_renderer import (
    RT_BROUGHT_FWD, RT_CARRY_FWD, RT_DATA,
)
from odoo.tests import TransactionCase, tagged

from .common import FakeReportMixin, FakeReportPDF, make_groups

OPTIONS = {'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'}


class GroupPaginatedPDF(FakeReportPDF):

    def _should_paginate_by_group(self):
        return True


class BookPDF(FakeReportPDF):

    def _should_add_journal_info_section(self):
        return True


def data_row(amount, **extra):
    return {
        'type': RT_DATA,
        'cells': ['', '', f'{amount:,.0f}', ''],
        'height': 10,
        'monetary': {2: amount},
        **extra,
    }


@tagged('post_install', '-at_install')
class TestPdfRenderer(FakeReportMixin, TransactionCase):

    def _renderer(self, renderer_cls=FakeReportPDF, **options):
        data = self.Report.get_report_data({**OPTIONS, **options})
        return renderer_cls(data, self.Report.with_context(lang=data['options']['lang']).env)

    def _read(self, content):
        self.assertTrue(content.startswith(b'%PDF'))
        return [page.extract_text() for page in PdfReader(io.BytesIO(content)).pages]

    # ------------------------------------------------------------- pagination

    def test_paginate_fits_on_one_page(self):
        renderer = self._renderer()
        pages = renderer._paginate([data_row(100), data_row(200)], avail_h=1000)
        self.assertEqual(len(pages), 1)
        self.assertEqual([row['type'] for row in pages[0]], [RT_DATA, RT_DATA])

    def test_paginate_carries_the_running_total(self):
        renderer = self._renderer()
        carry_h = renderer._make_carry_row({2: 0, 3: 0}, {}, RT_CARRY_FWD)['height']
        rows = [data_row(100), data_row(200), data_row(300), data_row(400)]
        # room for two data rows and the carried forward row
        pages = renderer._paginate(rows, avail_h=20 + carry_h)

        self.assertEqual(len(pages), 3)
        first, second, third = pages
        self.assertEqual([row['type'] for row in first], [RT_DATA, RT_DATA, RT_CARRY_FWD])
        self.assertEqual(first[-1]['cells'][1], "Carried forward")
        self.assertEqual(first[-1]['cells'][2], '300')
        self.assertEqual(second[0]['type'], RT_BROUGHT_FWD)
        self.assertEqual(second[0]['cells'][1], "Brought forward")
        self.assertEqual(second[0]['cells'][2], '300')
        self.assertEqual(second[-1]['cells'][2], '600')
        self.assertEqual(third[0]['cells'][2], '600')
        self.assertEqual(third[-1]['type'], RT_DATA)

    def test_paginate_resets_the_running_total_per_group(self):
        renderer = self._renderer()
        carry_h = renderer._make_carry_row({2: 0, 3: 0}, {}, RT_CARRY_FWD)['height']
        rows = [
            data_row(100, carry_reset=True), data_row(200),
            data_row(1000, carry_reset=True), data_row(2000), data_row(3000),
        ]
        pages = renderer._paginate(rows, avail_h=20 + carry_h)

        # the second group starts on a new page without carried rows
        self.assertEqual([row['type'] for row in pages[0]], [RT_DATA, RT_DATA])
        self.assertEqual(pages[1][0]['cells'][2], '1,000')
        self.assertEqual(pages[1][-1]['type'], RT_CARRY_FWD)
        self.assertEqual(pages[1][-1]['cells'][2], '3,000', "the total restarts from zero")
        self.assertEqual(pages[2][0]['cells'][2], '3,000')

    def test_paginate_keeps_a_row_with_the_next_one(self):
        renderer = self._renderer()
        carry_h = renderer._make_carry_row({2: 0, 3: 0}, {}, RT_CARRY_FWD)['height']
        avail_h = 20 + carry_h

        rows = [data_row(100), data_row(200), data_row(300)]
        pages = renderer._paginate(rows, avail_h)
        self.assertEqual([row['type'] for row in pages[0]], [RT_DATA, RT_DATA, RT_CARRY_FWD])

        # the second row would fit, but not together with the third one
        rows = [data_row(100), data_row(200, keep_with_next=True), data_row(300)]
        pages = renderer._paginate(rows, avail_h)
        self.assertEqual([row['type'] for row in pages[0]], [RT_DATA, RT_CARRY_FWD])
        self.assertEqual(pages[0][-1]['cells'][2], '100')
        self.assertEqual([row['type'] for row in pages[1][:2]], [RT_BROUGHT_FWD, RT_DATA])
        self.assertEqual(pages[1][1]['cells'][2], '200')

    def test_paginate_last_value_columns(self):

        class BalancePDF(FakeReportPDF):
            def _get_carry_last_cols(self):
                return [3]

        renderer = self._renderer(BalancePDF)
        carry_h = renderer._make_carry_row({2: 0, 3: 0}, {3: 0}, RT_CARRY_FWD)['height']
        rows = [
            data_row(100, last_vals={3: 100}), data_row(200, last_vals={3: 300}),
            data_row(300, last_vals={3: 600}),
        ]
        pages = renderer._paginate(rows, avail_h=20 + carry_h)
        self.assertEqual(pages[0][-1]['cells'][2], '300', "summed column")
        self.assertEqual(pages[0][-1]['cells'][3], '300', "last value column")

    def test_fmt_number(self):
        self.assertEqual(FakeReportPDF.fmt_number(1234567.4), '1,234,567')
        self.assertEqual(FakeReportPDF.fmt_number(1234.5, digits=2), '1,234.50')
        self.assertEqual(FakeReportPDF.fmt_number(0), '')
        self.assertEqual(FakeReportPDF.fmt_number(None), '')
        self.assertEqual(FakeReportPDF.fmt_number('abc'), 'abc')

    # ----------------------------------------------------------------- render

    def test_render_single_page(self):
        pages = self._read(self._renderer().render())
        self.assertEqual(len(pages), 1)
        text = pages[0]
        self.assertIn("Report", text)
        self.assertIn("From 2026-01-01 to 2026-01-31", text)
        self.assertIn("Entry 0/0", text)
        self.assertIn("Page 1/1", text)
        self.assertIn("Prepared by", text)
        self.assertIn("Chief Accountant", text)
        self.assertNotIn("Carried forward", text)

    def test_render_many_pages_with_carried_totals(self):
        self.groups = make_groups(group_count=1, line_count=150)
        pages = self._read(self._renderer(orientation='landscape').render())
        self.assertGreater(len(pages), 2)
        total = len(pages)
        for number, text in enumerate(pages, 1):
            self.assertIn(f"Page {number}/{total}", text)
            self.assertIn("Report", text, "the header is repeated on every page")
            self.assertIn("Debit", text, "the column headers are repeated on every page")
        self.assertIn("Carried forward", pages[0])
        self.assertIn("Brought forward", pages[1])
        self.assertNotIn("Brought forward", pages[0])
        self.assertNotIn("Carried forward", pages[-1])

    def test_render_portrait_and_landscape(self):
        for orientation, (width, height) in (('portrait', (595, 842)), ('landscape', (842, 595))):
            content = self._renderer(orientation=orientation).render()
            box = PdfReader(io.BytesIO(content)).pages[0].mediabox
            self.assertEqual((round(float(box[2])), round(float(box[3]))), (width, height))

    def test_render_each_group_on_a_new_page(self):
        self.groups = make_groups(group_count=3, line_count=2)
        pages = self._read(self._renderer(GroupPaginatedPDF).render())
        self.assertEqual(len(pages), 3)
        for index, text in enumerate(pages):
            self.assertIn(f"Account 11{index}", text)
            self.assertIn("Prepared by", text, "each group is signed")

    def test_render_mirror_margins_start_groups_on_odd_pages(self):
        self.groups = make_groups(group_count=3, line_count=2)
        renderer = self._renderer(GroupPaginatedPDF, mirror_margin=True, gutter_mm=10)
        pages = self._read(renderer.render())
        # one page per group, and a blank page after each group but the last
        self.assertEqual(len(pages), 5)
        self.assertIn("Account 110", pages[0])
        self.assertNotIn("Entry", pages[1])
        self.assertIn("Account 111", pages[2])
        self.assertNotIn("Entry", pages[3])
        self.assertIn("Account 112", pages[4])

    def test_render_book_information(self):
        text = self._read(self._renderer(BookPDF).render())[0]
        self.assertIn("This book has 1 pages, numbered from page 1 to page 1", text)
        self.assertIn("Book opening date: 2026-01-01", text)

    def test_render_vietnamese_text(self):
        self.groups[0]['lines'][0]['name'] = "Thu tiền khách hàng Nguyễn Văn Ước"
        text = self._read(self._renderer().render())[0]
        self.assertIn("Nguyễn Văn Ước", text.replace('\n', ''))

    def test_render_in_vietnamese(self):
        """ The printed labels follow the language of the report. """
        self.env['ir.module.module']._load_module_terms(['fg_vn_accounting_reports'], ['vi_VN'])
        self.groups = make_groups(group_count=1, line_count=150)
        pages = self._read(self._renderer(BookPDF, lang='vi_VN').render())
        self.assertIn("Từ ngày 2026-01-01 đến ngày 2026-01-31", pages[0])
        self.assertIn("Cộng chuyển trang", pages[0])
        self.assertIn("Số dư đầu trang", pages[1])
        self.assertIn(f"Trang 1/{len(pages)}", pages[0])
        last = pages[-1]
        self.assertIn(f"Sổ này bao gồm {len(pages)} trang, đánh số từ trang số 1 đến {len(pages)}", last)
        self.assertIn("Ngày mở sổ: 2026-01-01", last)
        for label in ("Người lập biểu", "Kế toán trưởng", "Giám đốc", "(Ký, họ tên, đóng dấu)"):
            self.assertIn(label, last)

    def test_get_pdf_rl(self):
        pages = self._read(self.Report.get_pdf_rl(dict(OPTIONS)))
        self.assertIn("Entry 1/2", pages[0])

    def test_get_pdf_rl_without_renderer(self):
        self.renderer_cls = None
        with self.assertRaises(NotImplementedError):
            self.Report.get_pdf_rl(dict(OPTIONS))
