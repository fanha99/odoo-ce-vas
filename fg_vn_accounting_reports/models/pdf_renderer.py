import io
import os

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, PageBreak, NextPageTemplate, Spacer,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font registration ─────────────────────────────────────────────────────────

_FONT_REGISTERED = False
FONT_NORMAL = 'Helvetica'
FONT_BOLD   = 'Helvetica-Bold'


def _register_fonts():
    global _FONT_REGISTERED, FONT_NORMAL, FONT_BOLD
    if _FONT_REGISTERED:
        return
    _FONT_REGISTERED = True
    # Fonts bundled with this module — works on Windows, Linux, Docker, anywhere
    _fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts')
    path_n = os.path.join(_fonts_dir, 'DejaVuSans.ttf')
    path_b = os.path.join(_fonts_dir, 'DejaVuSans-Bold.ttf')
    try:
        pdfmetrics.registerFont(TTFont('FanhaFont',      path_n))
        pdfmetrics.registerFont(TTFont('FanhaFont-Bold', path_b))
        pdfmetrics.registerFontFamily('FanhaFont', normal='FanhaFont', bold='FanhaFont-Bold')
        FONT_NORMAL = 'FanhaFont'
        FONT_BOLD   = 'FanhaFont-Bold'
    except Exception:
        pass  # Fallback: Helvetica (built-in ReportLab, Latin only)


# ── Numbered canvas (Page X/Y) ───────────────────────────────────────────────

class _NumberedCanvas(rl_canvas.Canvas):
    """
    Two-pass canvas: saves page states on showPage(), then in save() replays
    all pages and draws 'Page X/Y' now that total page count is known.
    The label is translated by the renderer, which has the environment.

    page_info {PDF page: (page in the group, pages of the group)} numbers the
    pages of each group (account, product, ...) instead of the whole document.

    outline {PDF page: group label} is the outline (bookmarks) of the PDF,
    pointing at the first page of each group. It must be built in save():
    before that the pages are not written yet, and every bookmark would
    point at page 1.
    """
    def __init__(self, *args, page_info=None, outline=None, **kwargs):
        rl_canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._page_info = page_info or {}
        self._outline = outline or {}

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for page_num, state in enumerate(self._saved_page_states, 1):
            self.__dict__.update(state)
            info = state.get('_footer_info')
            if info:
                align, xl, xr, y, fn, fs, label = info
                self.setFont(fn, fs)
                page, pages = self._page_info.get(page_num, (page_num, total))
                text = label % {'page': page, 'total': pages}
                if align == 'left':
                    self.drawString(xl, y, text)
                else:
                    self.drawRightString(xr, y, text)
            label = self._outline.get(page_num)
            if label:
                key = f'group_{page_num}'
                self.bookmarkPage(key)
                self.addOutlineEntry(label, key, level=0)
            rl_canvas.Canvas.showPage(self)
        if self._outline:
            self.showOutline()
        rl_canvas.Canvas.save(self)


# ── Row type constants ────────────────────────────────────────────────────────

RT_GROUP_HDR   = 'group_hdr'
RT_DATA        = 'data'
RT_GROUP_TOTAL = 'group_total'
RT_GRAND_TOTAL = 'grand_total'
RT_CARRY_FWD   = 'carry_fwd'
RT_BROUGHT_FWD = 'brought_fwd'
RT_OPENING     = 'opening'
RT_CLOSING     = 'closing'

FONT_SIZE   = 6.5
LINE_HEIGHT = FONT_SIZE * 1.35
ROW_PAD_V   = 3  # points top+bottom per cell


class FanhaReportPDF:
    """
    Base class for ReportLab PDF reports with carry-forward support.

    Subclass must implement:
        _get_col_specs()          → list of col dicts per orientation
        _get_carry_cols()         → list of column indices to accumulate
        _get_carry_label_col()    → column index for carry-forward label
        _groups_to_rows(groups)   → flat list of row dicts
    """

    # Default page (landscape A4); overridden in __init__ based on options
    _DEFAULT_PAGE_W, _DEFAULT_PAGE_H = landscape(A4)

    ML = MR = 12 * mm   # base left/right margin
    MT = MB = 12 * mm   # top/bottom margin

    # Extra reduction to avoid ReportLab table border overflow (~4mm borders + buffer)
    BORDER_OVERHEAD = 2 * mm

    # Colors
    C_COL_HDR = colors.HexColor('#4472C4')
    C_GROUP   = colors.HexColor('#D9E1F2')
    C_TOTAL   = colors.HexColor('#E2EFDA')
    C_CARRY   = colors.HexColor('#E2EFDA')
    C_OPENING = colors.HexColor('#E2EFDA')
    C_CLOSING = colors.HexColor('#E2EFDA')
    C_OFF_BALANCE = colors.HexColor('#FCE4D6')  # off-balance accounts (light orange)
    C_BORDER  = colors.HexColor('#AAAAAA')
    C_WHITE   = colors.white
    C_BLACK   = colors.black

    def __init__(self, report_data, env):
        """
        :param dict report_data: result of ``vn.abstract.report.get_report_data()``
        :param env: environment in the language of the report; ``self.env``
            is what makes the printed labels translatable
        """
        _register_fonts()
        self.env     = env
        self.data    = report_data
        self.company = report_data['company']
        self.hdr     = report_data['header']
        self.groups  = report_data.get('lines', [])

        opts = report_data.get('options', {})
        self.orientation   = opts.get('orientation', 'landscape')
        self.mirror_margin = opts.get('mirror_margin', False)
        self.gutter        = opts.get('gutter_mm', 6) * mm if self.mirror_margin else 0

        if self.orientation == 'portrait':
            self.PAGE_W, self.PAGE_H = A4
        else:
            self.PAGE_W, self.PAGE_H = landscape(A4)

        # Set by _render_group_paginated(); subclasses read them in
        # _draw_page_header/_draw_page_footer to draw the per-group label.
        self._page_group_labels = {}
        self._page_info         = {}

        self._col_specs  = self._get_col_specs()
        self._carry_cols = self._get_carry_cols()

    # ── Abstract interface ────────────────────────────────────────────────

    def _get_col_specs(self):
        """Return list of dicts: {label, width (points), align ('L'/'C'/'R'), type}
        self.orientation is available here."""
        raise NotImplementedError

    def _get_carry_cols(self):
        return []

    def _get_carry_label_col(self):
        return 0

    def _get_carry_last_cols(self):
        """Columns that carry the LAST seen value (not cumulative sum), e.g. running balance."""
        return []

    def _groups_to_rows(self, groups):
        raise NotImplementedError

    def _group_to_rows(self, group):
        """Rows for a single group. Required when
        _should_paginate_by_group() returns True."""
        raise NotImplementedError

    # ── Width helpers ─────────────────────────────────────────────────────

    def _frame_width(self):
        """Width of the content frame. Gutter shifts the frame, does NOT reduce width."""
        return self.PAGE_W - self.ML - self.MR

    def _col_widths(self):
        """Scale column widths proportionally to fit the frame width."""
        specs     = self._col_specs
        total     = sum(s['width'] for s in specs)
        available = self._frame_width()
        if total == 0:
            return [available / len(specs)] * len(specs)
        scale = available / total
        return [s['width'] * scale for s in specs]

    # ── Paragraph helper ─────────────────────────────────────────────────

    def _p(self, text, bold=False, align='L', size=None, color=None):
        fn = FONT_BOLD if bold else FONT_NORMAL
        fs = size or FONT_SIZE
        al = {'L': TA_LEFT, 'C': TA_CENTER, 'R': TA_RIGHT}.get(align, TA_LEFT)
        style = ParagraphStyle(
            'cell',
            fontName=fn, fontSize=fs, leading=fs * 1.35,
            alignment=al, textColor=color or self.C_BLACK,
        )
        return Paragraph(str(text) if text is not None else '', style)

    # ── Row height measurement ────────────────────────────────────────────

    def _measure_row_height(self, cells, bold=False):
        """Measure row height using Paragraph.wrap() — handles text without spaces correctly."""
        col_widths = self._col_widths()
        max_h = LINE_HEIGHT + ROW_PAD_V * 2  # minimum 1-line height
        for i, cell in enumerate(cells):
            if i >= len(col_widths):
                break
            inner_w = col_widths[i] - 6
            if inner_w <= 0:
                continue
            text = str(cell) if cell is not None else ''
            if not text:
                continue
            p = self._p(text, bold=bold)
            _, h = p.wrap(inner_w, 9999)
            max_h = max(max_h, h + ROW_PAD_V * 2)
        return max_h

    @staticmethod
    def fmt_number(val, digits=0):
        if val is None or val == '' or val == 0:
            return ''
        try:
            f = float(val)
            # Use digits parameter to determine decimal places
            if digits > 0:
                return f'{f:,.{digits}f}' if f else ''
            else:
                return f'{f:,.0f}' if f else ''
        except (TypeError, ValueError):
            return str(val)

    # ── Fixed heights ─────────────────────────────────────────────────────

    def _company_hdr_height(self):
        """ Height reserved for the page header: 22 mm, or more when the
        header lines need it. """
        frame_w = self._frame_width()
        height = self.HEADER_TOP_INSET
        # page 0 stands for "the tallest header of the document"
        for line in self._get_page_header_lines(0):
            _w, line_h = self._header_paragraph(line).wrap(frame_w, 100)
            height += line_h + line.get('space_after', 0)
        return max(22 * mm, height + self.HEADER_BOTTOM_GAP)

    def _col_hdr_height(self):
        return 9 * mm

    def _footer_height(self):
        return 7 * mm

    # ── Page header ───────────────────────────────────────────────────────
    #
    # The header of a page is a list of lines. A report changes its header by
    # overriding _get_page_header_lines() (add, remove or change a line) or
    # _format_group_label(); it never has to redraw the header itself.

    HEADER_TOP_INSET = 3    # points between the top margin and the first line
    HEADER_BOTTOM_GAP = 6   # points between the last line and the table

    def _get_page_header_lines(self, page):
        """ Lines of the header of the given page, from top to bottom.

        :param int page: page number, starting at 1. 0 asks for the tallest
            header of the document, to reserve its height.
        :return: list of dicts {'text', 'bold', 'size', 'align' ('L', 'C' or
            'R'), 'space_after' (points)}; only 'text' is required
        """
        lines = [
            {'text': self.company.get('name', ''), 'bold': True, 'size': 9, 'align': 'L', 'space_after': 2},
            {'text': self.hdr.get('title', ''), 'bold': True, 'size': 11, 'align': 'C', 'space_after': 2},
            {
                'text': self.env._(
                    "From %(date_from)s to %(date_to)s",
                    date_from=self.hdr.get('date_from', ''), date_to=self.hdr.get('date_to', ''),
                ),
                'size': 8, 'align': 'C', 'space_after': 4,
            },
        ]
        group_label = self._get_page_group_label(page)
        if group_label:
            lines.append({'text': group_label, 'bold': True, 'size': 9, 'align': 'L'})
        return lines

    def _get_page_group_label(self, page):
        """ Label of the group printed on the given page, '' when the report
        is not paginated by group. For page 0, the longest label. """
        if not self._should_paginate_by_group():
            return ''
        if page == 0:
            labels = [self._format_group_label(group) or '' for group in self.groups]
            return max(labels, key=len, default='')
        return self._page_group_labels.get(page, '')

    def _is_blank_page(self, page):
        """ Filler page inserted so that the next group starts on an odd
        page, when printing with mirror margins. """
        return self._page_info.get(page) == (0, 0)

    def _header_paragraph(self, line):
        return self._p(
            line.get('text', ''), bold=line.get('bold', False),
            size=line.get('size'), align=line.get('align', 'L'),
        )

    # ── Canvas callbacks ──────────────────────────────────────────────────

    def _draw_page_header(self, c, doc, ml):
        """ Draw the lines of _get_page_header_lines(). Paragraph.drawOn()
        renders Vietnamese correctly. Nothing is drawn on a filler page. """
        if self._is_blank_page(doc.page):
            return
        frame_w = self._frame_width()
        y = self.PAGE_H - self.MT - self.HEADER_TOP_INSET
        for line in self._get_page_header_lines(doc.page):
            p = self._header_paragraph(line)
            _w, line_h = p.wrap(frame_w, 100)
            p.drawOn(c, ml, y - line_h)
            y -= line_h + line.get('space_after', 0)

    def _draw_page_footer(self, c, doc, align='right', x_left=None, x_right=None):
        """Store footer info on canvas — _NumberedCanvas will draw 'Page X/Y' in save()."""
        if self._is_blank_page(doc.page):
            # the canvas keeps the footer of the previous page otherwise
            c._footer_info = None
            return
        c._footer_info = (
            align,
            x_left  or self.ML,
            x_right or (self.PAGE_W - self.MR),
            self.MB - 4 * mm,
            FONT_NORMAL,
            7,
            self.env._("Page %(page)s/%(total)s"),
        )

    # ── Document builder ──────────────────────────────────────────────────

    def _build_doc(self, buf, hdr_h, ftr_h):
        """Build BaseDocTemplate with one or two page templates."""
        frame_w = self._frame_width()
        frame_h = self.PAGE_H - self.MT - self.MB - hdr_h - ftr_h
        frame_y = self.MB + ftr_h

        def make_frame(x):
            return Frame(
                x, frame_y, frame_w, frame_h,
                leftPadding=0, rightPadding=0,
                topPadding=0,  bottomPadding=0,
            )

        if self.mirror_margin:
            # Gutter is taken from the opposite margin — frame_width stays constant.
            # Odd pages (recto): left = ML+gutter (binding), right = MR-gutter (outer)
            # Even pages (verso): left = ML-gutter (outer), right = MR+gutter (binding)
            x_odd  = self.ML + self.gutter
            x_even = max(0, self.ML - self.gutter)
            # Outer edge positions for page number
            x_num_odd_right  = self.PAGE_W - max(0, self.MR - self.gutter)
            x_num_even_left  = x_even

            def on_odd(c, doc):
                self._draw_page_header(c, doc, x_odd)
                self._draw_page_footer(c, doc, align='right', x_right=x_num_odd_right)

            def on_even(c, doc):
                self._draw_page_header(c, doc, x_even)
                self._draw_page_footer(c, doc, align='left', x_left=x_num_even_left)

            templates = [
                PageTemplate('odd',  frames=[make_frame(x_odd)],  onPage=on_odd),
                PageTemplate('even', frames=[make_frame(x_even)], onPage=on_even),
            ]
        else:
            ml = self.ML

            def on_page(c, doc):
                self._draw_page_header(c, doc, ml)
                self._draw_page_footer(c, doc, align='right', x_right=self.PAGE_W - self.MR)

            templates = [
                PageTemplate('main', frames=[make_frame(ml)], onPage=on_page),
            ]

        return BaseDocTemplate(
            buf,
            pagesize=(self.PAGE_W, self.PAGE_H),
            pageTemplates=templates,
        )

    # ── Pagination ────────────────────────────────────────────────────────

    def _paginate(self, all_rows, avail_h, tail_h=0):
        """ Split the rows into pages.

        :param float tail_h: height of what is printed after the table on the
            last page (book information, signatures). It must be reserved,
            otherwise ReportLab pushes it to a page the page numbering does
            not know about.
        """
        carry_last_cols = self._get_carry_last_cols()
        if self._carry_cols or carry_last_cols:
            dummy = self._make_carry_row(
                {c: 0 for c in self._carry_cols},
                {c: 0 for c in carry_last_cols},
                RT_CARRY_FWD,
            )
            carry_row_h = dummy['height']
        else:
            carry_row_h = 0

        running      = {col: 0.0 for col in self._carry_cols}
        running_last = {col: 0.0 for col in carry_last_cols}
        pages        = []
        cur_page     = []
        cur_h        = 0.0

        for i, row in enumerate(all_rows):
            h        = row['height']
            is_reset = row.get('carry_reset', False)

            # a row asking to stay with the next one reserves that row's height too
            keep_next_h = 0
            if row.get('keep_with_next') and i + 1 < len(all_rows):
                keep_next_h = all_rows[i + 1]['height']

            # the last page has no carried forward row but the tail: the last
            # row (and the row kept with it) reserves the room for the tail
            last_on_page = i == len(all_rows) - 1 or (
                row.get('keep_with_next') and i + 2 == len(all_rows))
            reserve_h = max(carry_row_h, tail_h) if last_on_page else carry_row_h

            if cur_page and cur_h + h + keep_next_h + reserve_h > avail_h:
                if is_reset or not self._carry_cols:
                    # New section starts here — plain page break, no carry rows
                    pages.append(cur_page)
                    cur_page = []
                    cur_h    = 0.0
                else:
                    cur_page.append(self._make_carry_row(running, running_last, RT_CARRY_FWD))
                    pages.append(cur_page)
                    cur_page = [self._make_carry_row(running, running_last, RT_BROUGHT_FWD)]
                    cur_h    = carry_row_h

            if is_reset:
                running      = {col: 0.0 for col in self._carry_cols}
                running_last = {col: 0.0 for col in carry_last_cols}

            cur_page.append(row)
            cur_h += h

            for col in self._carry_cols:
                running[col] += row['monetary'].get(col, 0) or 0
            for col in carry_last_cols:
                v = row.get('last_vals', {}).get(col)
                if v is not None:
                    running_last[col] = v

        if cur_page:
            pages.append(cur_page)
        return pages

    def _make_carry_row(self, running, running_last, row_type):
        n     = len(self._col_specs)
        cells = [''] * n
        if row_type == RT_CARRY_FWD:
            label = self.env._("Carried forward")
        else:
            label = self.env._("Brought forward")
        cells[self._get_carry_label_col()] = label
        for col in self._carry_cols:
            cells[col] = self.fmt_number(running.get(col, 0))
        for col in self._get_carry_last_cols():
            cells[col] = self.fmt_number(running_last.get(col, 0))
        return {
            'type':     row_type,
            'cells':    cells,
            'height':   self._measure_row_height(cells),
            'monetary': {},
        }

    def _make_journal_info_section(self, num_pages=None):
        """Create info section: number of pages and opening date."""
        pages_str = f'{num_pages}' if num_pages else '?'
        from_date = self.hdr.get('date_from', '')
        
        # Line 1: Number of pages
        line1 = self._p(
            self.env._(
                "This book has %(pages)s pages, numbered from page 1 to page %(pages)s",
                pages=pages_str,
            ),
            size=7, align='L'
        )
        
        # Line 2: Opening date
        line2 = self._p(
            self.env._("Book opening date: %(date)s", date=from_date),
            size=7, align='L'
        )
        
        return [line1, Spacer(1, 1*mm), line2]

    def _make_signature_section(self, date_end=None):
        """Create a 3-column signature section with date in top-right."""
        date_str = date_end or self.hdr.get('date_to', '')
        
        # Signature table with 3 rows:
        # Row 1: empty | empty | date
        # Row 2: Prepared by | Chief Accountant | Director
        # Row 3: (Signature, full name) x2 | (Signature, full name, seal)

        sig_titles = [
            self.env._("Prepared by"),
            self.env._("Chief Accountant"),
            self.env._("Director"),
        ]

        # Row 1: date in column 3
        date_row = [
            self._p('', size=7, align='C'),
            self._p('', size=7, align='C'),
            self._p(self.env._("Date %(date)s", date=date_str), size=7, align='C'),
        ]

        # Row 2: titles
        title_row = [self._p(title, bold=True, size=7, align='C') for title in sig_titles]

        # Row 3: signature labels (last one is modified)
        sig_names = [
            self._p(self.env._("(Signature, full name)"), size=6, align='C'),
            self._p(self.env._("(Signature, full name)"), size=6, align='C'),
            self._p(self.env._("(Signature, full name, seal)"), size=6, align='C'),
        ]

        sig_tbl = Table(
            [date_row, title_row, sig_names],
            colWidths=[self._frame_width() / 3] * 3
        )
        sig_tbl.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, 1), 7),
            ('FONTSIZE', (0, 2), (-1, 2), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        return [sig_tbl]

    def _make_tail_flowables(self, num_pages=None):
        """ What is printed after the table on the last page: book
        information and signatures. """
        flowables = []
        if self._should_add_journal_info_section():
            flowables.append(Spacer(1, 5 * mm))
            flowables.extend(self._make_journal_info_section(num_pages))
            flowables.append(Spacer(1, 2 * mm))
        if self._should_add_signature_section():
            flowables.append(Spacer(1, 5 * mm))
            flowables.extend(self._make_signature_section())
        return flowables

    def _tail_height(self):
        """ Height of _make_tail_flowables(), reserved by _paginate(). """
        frame_w = self._frame_width()
        return sum(f.wrap(frame_w, self.PAGE_H)[1] for f in self._make_tail_flowables())

    # ── Render ────────────────────────────────────────────────────────────
    def _should_paginate_by_group(self):
        """Override to True if need per-group pagination (like S03b)."""
        return False

    def _should_add_journal_info_section(self):
        return False

    def _should_add_signature_section(self):
        return True

    def _format_group_label(self, group):
        """ Hook: label of a group, drawn in the header of each of its pages
        when the report is paginated by group ("Account: ...", "Product: ...").
        Return '' for no label. """
        return group.get('name', '')

    def render(self):
        if self._should_paginate_by_group():
            return self._render_group_paginated()
        else:
            return self._render_single_paginated()

    def _render_single_paginated(self):
        buf        = io.BytesIO()
        hdr_h      = self._company_hdr_height()
        col_hdr_h  = self._col_hdr_height()
        ftr_h      = self._footer_height()
        avail_h    = (self.PAGE_H - self.MT - self.MB
                      - hdr_h - col_hdr_h - ftr_h - self.BORDER_OVERHEAD)

        all_rows = self._groups_to_rows(self.groups)
        for row in all_rows:
            if row.get('height') is None:
                row['height'] = self._measure_row_height(row['cells'])

        pages = self._paginate(all_rows, avail_h, self._tail_height())

        story = []
        for page_idx, page_rows in enumerate(pages):
            if page_idx > 0:
                if self.mirror_margin:
                    # Alternate templates: page 1 = odd, page 2 = even, ...
                    next_tmpl = 'odd' if page_idx % 2 == 0 else 'even'
                    story.append(NextPageTemplate(next_tmpl))
                story.append(PageBreak())

            tbl_data    = []
            row_heights = []
            extra_cmds  = []

            col_hdr = [
                self._p(s['label'], bold=True, align='C', color=self.C_WHITE)
                for s in self._col_specs
            ]
            tbl_data.append(col_hdr)
            row_heights.append(col_hdr_h)

            for row in page_rows:
                ri = len(tbl_data)
                tbl_data.append(self._row_to_paragraphs(row))
                row_heights.append(row['height'])
                if row.get('span_all'):
                    extra_cmds.append(('SPAN', (0, ri), (-1, ri)))
                elif row.get('span_first_two'):
                    extra_cmds.append(('SPAN', (0, ri), (1, ri)))
                self._add_type_style_cmds(extra_cmds, row['type'], ri)

            tbl = Table(
                tbl_data,
                colWidths=self._col_widths(),
                rowHeights=row_heights,
            )
            tbl.setStyle(self._base_table_style(extra_cmds))
            story.append(tbl)

        story.extend(self._make_tail_flowables(len(pages)))

        doc = self._build_doc(buf, hdr_h, ftr_h)
        doc.build(story, canvasmaker=_NumberedCanvas)
        buf.seek(0)
        return buf.read()

    def _render_group_paginated(self):
        buf       = io.BytesIO()
        hdr_h     = self._company_hdr_height()
        col_hdr_h = self._col_hdr_height()
        ftr_h     = self._footer_height()
        avail_h   = (self.PAGE_H - self.MT - self.MB
                     - hdr_h - col_hdr_h - ftr_h - self.BORDER_OVERHEAD)

        # ── Pass 1: measure + paginate per group ──────────────────────────
        self._page_group_labels = {}
        self._page_info         = {}
        group_paginated         = []
        blank_after             = []  # True if a blank page must follow group i
        page_num                = 1
        tail_h                  = self._tail_height()

        for i, group in enumerate(self.groups):
            rows = self._group_to_rows(group)
            for row in rows:
                if row.get('height') is None:
                    row['height'] = self._measure_row_height(row['cells'])
            pages     = self._paginate(rows, avail_h, tail_h)
            num_pages = len(pages)
            group_paginated.append(pages)
            label = self._format_group_label(group)
            for grp_page_idx in range(1, num_pages + 1):
                self._page_group_labels[page_num] = label
                self._page_info[page_num]         = (grp_page_idx, num_pages)
                page_num += 1
            # After last page of this group, page_num is the next page number.
            # If that page would be even and there is a following group, insert
            # a blank page so the next group always starts on an odd page.
            if self.mirror_margin and i < len(self.groups) - 1 and page_num % 2 == 0:
                blank_after.append(True)
                self._page_group_labels[page_num] = ''
                self._page_info[page_num]         = (0, 0)  # sentinel → skip footer
                page_num += 1
            else:
                blank_after.append(False)

        # ── Pass 2: build story ───────────────────────────────────────────
        story        = []
        abs_page_idx = 0

        for i, (group, pages) in enumerate(zip(self.groups, group_paginated)):
             # Blank filler page before this group when previous group required it
             if i > 0 and blank_after[i - 1]:
                 if self.mirror_margin:
                     next_tmpl = 'odd' if abs_page_idx % 2 == 0 else 'even'
                     story.append(NextPageTemplate(next_tmpl))
                 story.append(PageBreak())
                 story.append(Spacer(1, 1 * mm))  # minimal content — renders as blank page
                 abs_page_idx += 1

             for p_idx, p_rows in enumerate(pages):
                 if abs_page_idx > 0:
                     if self.mirror_margin:
                         next_tmpl = 'odd' if abs_page_idx % 2 == 0 else 'even'
                         story.append(NextPageTemplate(next_tmpl))
                     story.append(PageBreak())

                 tbl_data    = []
                 row_heights = []
                 extra_cmds  = []

                 col_hdr = [
                     self._p(s['label'], bold=True, align='C', color=self.C_WHITE)
                     for s in self._col_specs
                 ]
                 tbl_data.append(col_hdr)
                 row_heights.append(col_hdr_h)

                 for row in p_rows:
                     ri = len(tbl_data)
                     tbl_data.append(self._row_to_paragraphs(row))
                     row_heights.append(row['height'])
                     if row.get('span_all'):
                         extra_cmds.append(('SPAN', (0, ri), (-1, ri)))
                     elif row.get('span_first_two'):
                         extra_cmds.append(('SPAN', (0, ri), (1, ri)))
                     self._add_type_style_cmds(extra_cmds, row['type'], ri)

                 tbl = Table(
                     tbl_data,
                     colWidths=self._col_widths(),
                     rowHeights=row_heights,
                 )
                 tbl.setStyle(self._base_table_style(extra_cmds))
                 story.append(tbl)

                 # Add journal info and signature section after the last page of each group
                 if p_idx == len(pages) - 1:
                     story.extend(self._make_tail_flowables(len(pages)))

                 abs_page_idx += 1

        # ── Build doc with per-account canvas ────────────────────────────
        outline = {
            page: self._page_group_labels[page]
            for page, (group_page, _) in self._page_info.items()
            if group_page == 1
        }

        def make_canvas(*args, **kwargs):
            return _NumberedCanvas(*args, page_info=self._page_info,
                                   outline=outline, **kwargs)

        doc = self._build_doc(buf, hdr_h, ftr_h)
        doc.build(story, canvasmaker=make_canvas)
        buf.seek(0)
        return buf.read()

    def _row_to_paragraphs(self, row):
        result = []
        bold = row['type'] in (RT_GROUP_HDR, RT_GROUP_TOTAL, RT_GRAND_TOTAL,
                               RT_CARRY_FWD, RT_BROUGHT_FWD,
                               RT_OPENING, RT_CLOSING)
        for cell, spec in zip(row['cells'], self._col_specs):
            result.append(self._p(cell, bold=bold, align=spec.get('align', 'L')))
        return result

    def _add_type_style_cmds(self, cmds, row_type, ri):
        if row_type == RT_GROUP_HDR:
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_GROUP),
                     ('FONTNAME',   (0, ri), (-1, ri), FONT_BOLD)]
        elif row_type in (RT_GROUP_TOTAL, RT_GRAND_TOTAL):
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_TOTAL),
                     ('FONTNAME',   (0, ri), (-1, ri), FONT_BOLD)]
        elif row_type in (RT_CARRY_FWD, RT_BROUGHT_FWD):
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_CARRY),
                     ('FONTNAME',   (0, ri), (-1, ri), FONT_BOLD)]
        elif row_type == RT_OPENING:
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_OPENING),
                     ('FONTNAME',   (0, ri), (-1, ri), FONT_BOLD)]
        elif row_type == RT_CLOSING:
            cmds += [('BACKGROUND', (0, ri), (-1, ri), self.C_CLOSING),
                     ('FONTNAME',   (0, ri), (-1, ri), FONT_BOLD)]

    def _base_table_style(self, extra_cmds):
        cmds = [
            ('FONTNAME',      (0, 0), (-1, -1), FONT_NORMAL),
            ('FONTSIZE',      (0, 0), (-1, -1), FONT_SIZE),
            ('GRID',          (0, 0), (-1, -1), 0.4, self.C_BORDER),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 3),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
            ('TOPPADDING',    (0, 0), (-1, -1), ROW_PAD_V),
            ('BOTTOMPADDING', (0, 0), (-1, -1), ROW_PAD_V),
            ('BACKGROUND', (0, 0), (-1, 0), self.C_COL_HDR),
            ('FONTNAME',   (0, 0), (-1, 0), FONT_BOLD),
            ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ]
        cmds.extend(extra_cmds)
        return TableStyle(cmds)
