# Viết một báo cáo trên `fg_vn_accounting_reports`

Tài liệu cho người viết module báo cáo. Ví dụ đầy đủ: `fg_vn_report_cdps` (Bảng cân đối số phát sinh).

Một báo cáo gồm năm phần. Mỗi phần kế thừa một lớp của nền tảng và chỉ khai những gì riêng của nó.

| Phần | Kế thừa | Việc của báo cáo |
|---|---|---|
| Model báo cáo (`AbstractModel`) | `vn.abstract.report` | Tên, mã mẫu, cột, số liệu, dòng Excel, drill-down |
| Renderer PDF (lớp Python thường) | `FanhaReportPDF` | Cột và dòng của bản in |
| Wizard (`TransientModel`) | `vn.report.wizard.abstract` | Tham số riêng, form |
| Component OWL | `AbstractVNReport` | Bộ lọc, chuyển số liệu thành dòng |
| Client action + menu | | Tag của action, menu dưới `menu_vn_vas_reports` |

## 1. Quy tắc chung

- **Chuỗi viết tiếng Anh**, dịch ở `i18n/vi.po`. Python dùng `_()`, renderer PDF dùng `self.env._()`, JS dùng `_t()`.
- **Mọi chữ nằm trong bảng do máy chủ trả về** (nhãn cột, nhãn dòng cộng, tên nhóm), không dựng ở JS. JS chạy theo ngôn ngữ giao diện của người dùng; bảng phải theo ngôn ngữ báo cáo.
- **Số liệu đọc bằng SQL thì phải `flush_model()` trước**, và lọc theo `company_id` trong `options` (đã được nền tảng kiểm tra).
- **Hàm công khai riêng của báo cáo** (gọi được qua RPC hoặc URL) phải gọi `self._check_report_access(options)` trước khi trả số liệu.

## 2. Model báo cáo

```python
class MyReport(models.AbstractModel):
    _name = 'vn.report.my'
    _inherit = 'vn.abstract.report'
    _description = 'My Report'
```

| Hàm | Bắt buộc | Nội dung |
|---|---|---|
| `_get_report_name()` | có | Tên in trên báo cáo |
| `_get_report_code()` | có | Mã mẫu; cũng là đầu tên file xuất |
| `_get_columns()` | có | `[{'name', 'label', 'type', 'width', 'sortable'?}]`; `type`: `char`, `date`, `monetary`, `number`, `integer`, `float` |
| `_get_lines(options)` | có | Danh sách nhóm; cấu trúc do báo cáo tự định, component và renderer của báo cáo đọc nó |
| `_get_custom_options(options)` | không | Thêm giá trị mặc định cho `options` |
| `_build_report_data(options)` | không | Mở rộng kết quả của `get_report_data()` (ví dụ thêm cột theo tuỳ chọn). Chạy trong ngôn ngữ báo cáo, sau khi đã kiểm tra quyền |
| `_get_drill_down_action(options, params)` | không | Action mở chi tiết của một dòng |
| `_get_report_access_groups()` | không | Danh sách xml_id nhóm được xem; mặc định `['account.group_account_user']` |
| `_get_export_filename_code(options)` | không | Đầu tên file khi nó phụ thuộc tuỳ chọn |
| `_get_pdf_rl_renderer()` | để in PDF | Trả lớp renderer |

`get_report_data(options)` là điểm vào duy nhất của màn hình và của hai đường xuất. Nó điền mặc định, kiểm tra quyền (nhóm và công ty), chuyển `self` sang ngôn ngữ báo cáo (`options['lang']`, mặc định `vi_VN`), rồi gọi `_build_report_data()`. Không ghi đè `get_report_data()`.

Hàm hỗ trợ: `_get_utc_datetime_range(options)` đổi kỳ báo cáo sang khoảng `datetime` UTC theo múi giờ người dùng, dùng cho trường `datetime` (phiếu kho).

### Dòng Excel

Excel dùng các dòng có kiểu, cùng định dạng với PDF.

| Hàm | Dùng khi |
|---|---|
| `_groups_to_xlsx_rows(groups)` | Một sheet |
| `_should_xlsx_split_by_group()` trả `True`, `_group_to_xlsx_rows(group)`, `_format_xlsx_sheet_name(group)`, `_format_xlsx_group_label(group)` | Mỗi nhóm một sheet |

Mỗi dòng: `{'type': ..., 'cells': [giá trị thô], 'span_all': bool}`. Kiểu dòng: `data`, `group_hdr`, `group_total`, `grand_total`, `opening`, `closing`, `off_balance`. Ô số để nguyên số, nền tảng tự định dạng theo `type` của cột.

## 3. Renderer PDF

```python
class MyPdf(FanhaReportPDF):
    def _get_col_specs(self):          # [{'label', 'width', 'align': 'L'|'C'|'R'}]
    def _groups_to_rows(self, groups): # dòng: {'type', 'cells': [chuỗi], 'height': None, 'monetary': {cột: số}}
```

`__init__(report_data, env)`: lớp con có `__init__` riêng phải nhận và chuyển tiếp `env`. Nhãn lấy qua `self.env._("…")`.

| Hàm | Mặc định | Tác dụng |
|---|---|---|
| `_get_carry_cols()` | `[]` | Chỉ số các cột được cộng dồn qua trang. Rỗng thì không có dòng cộng chuyển trang |
| `_get_carry_last_cols()` | `[]` | Cột mang giá trị cuối cùng sang trang (số dư luỹ kế); dòng khai `last_vals: {cột: số}` |
| `_get_carry_label_col()` | `0` | Cột ghi nhãn "Cộng chuyển trang" |
| `_should_paginate_by_group()` | `False` | Mỗi nhóm bắt đầu trang mới; cần `_group_to_rows(group)` |
| `_should_add_signature_section()` | `True` | Phần ký tên |
| `_should_add_journal_info_section()` | `False` | "Sổ này bao gồm … trang" và ngày mở sổ |
| `_format_group_label(group)` | tên nhóm | Nhãn nhóm |

Thuộc tính của dòng: `carry_reset: True` đặt lại số cộng dồn (đầu mỗi nhóm); `keep_with_next: True` giữ dòng cùng trang với dòng sau; `span_all`, `span_first_two` gộp ô.

## 4. Wizard

```python
class MyReportWizard(models.TransientModel):
    _name = 'vn.report.my.wizard'
    _inherit = 'vn.report.wizard.abstract'
    _description = 'My Report Wizard'

    def _get_report_action_tag(self): return 'vn_report_my'
    def _get_report_model(self):      return 'vn.report.my'
    def _get_report_name(self):       return _("My Report")
    def _get_report_options(self):    # super() + tham số riêng
```

Lớp cơ sở là `AbstractModel`: wizard con phải là `models.TransientModel`, có dòng riêng trong `security/ir.access.csv` (thao tác `cru`) và form riêng. Form cần có các trường chung: `date_from`, `date_to`, `company_id`, `report_lang`, `orientation`, `mirror_margin`, `gutter_mm`.

Nút trên form gọi `action_view_report`, `action_export_xlsx`, `action_export_pdf_rl`. Định dạng xuất riêng: `self._get_export_action('<định dạng>')` cùng một route trong controller của module (mục 6). Kiểm tra tham số riêng bằng cách mở rộng `_check_report_dates()`. Mặc định khác: ghi đè `_default_orientation()`, hoặc đặt `default=` của `date_from`/`date_to` bằng `_default_date_from_quarter` / `_default_date_to_quarter`.

## 5. Component OWL

```js
import { AbstractVNReport } from "@fg_vn_accounting_reports/js/abstract_report";
import { registry } from "@web/core/registry";

export class MyReport extends AbstractVNReport {
    getReportModel() { return "vn.report.my"; }
    groupsToRows(groups) { ... }
}
registry.category("actions").add("vn_report_my", MyReport);
```

Báo cáo không cần file template: nền tảng hiển thị bảng chung. Báo cáo cần bảng riêng thì đặt `static tableTemplate = "<tên template>"`.

| Hook | Nội dung |
|---|---|
| `getReportModel()` | Tên model báo cáo (bắt buộc) |
| `groupsToRows(groups)` | Chuyển số liệu thành dòng: `{ id, type, cells, parentId?, expandable?, isParent?, level?, span_all?, data? }`. `cells` theo thứ tự cột. `data` là bản ghi gốc, truyền cho menu của dòng |
| `getFilterDefinitions()` | Bộ lọc trong menu Bộ lọc (bảng dưới) |
| `getSearchKeys()` | Khoá dùng cho ô tìm kiếm |
| `getDefaultSort()` | Sắp xếp mặc định `{ column, order }`; cột sắp xếp được khai `sortable: true` ở `_get_columns()` |
| `getLineMenuItems(line)`, `getGroupMenuItems(group)` | Mục menu của dòng; một mục thì hiện thành nút, nhiều mục thành menu |
| `getDataRowClass(row)` | Thêm class CSS cho dòng |
| `hasXmlExport`, `exportXml()` | Nút XML |
| `_buildOptions()` | Đổi tên hoặc bớt tuỳ chọn trước khi gửi máy chủ |

Kiểu bộ lọc:

| `type` | Thuộc tính | Giá trị trong `options` |
|---|---|---|
| `many2many`, `many2one` | `model`, `domain` | danh sách id |
| `selection` | `options: [{ value, label }]`, `default`, `emptyLabel` | giá trị hoặc `null` |
| `boolean` | `checkLabel`, `default` | `true` / `false` |
| `date` | `default` | chuỗi `YYYY-MM-DD` hoặc `null` |

Mọi kiểu nhận thêm `visible(filters)`: hàm trả `false` thì bộ lọc bị ẩn.

Trạng thái (`this.state`) là `proxy` của OWL 3. `expandedNodes` là `Set`: muốn đổi thì gán một `Set` mới. Trạng thái màn hình (kỳ, bộ lọc, ngôn ngữ, sắp xếp, dòng đang mở) tự lưu vào `sessionStorage` theo từng model báo cáo; lần mở mới từ wizard thì bắt đầu lại.

Template viết theo OWL 3: thành viên của component phải viết `this.x`.

## 6. Định dạng xuất riêng

```python
from odoo.addons.fg_vn_accounting_reports.controllers.main import VNReportController

class MyController(VNReportController):
    @http.route('/vn_report/vn.report.my/export/xml', type='http', auth='user')
    def export_my_xml(self, options=None, **kw):
        return self._export('vn.report.my', options, 'get_xml', 'xml', 'application/xml',
                            filename_code='MY-FORM')
```

`get_xml(options)` trả `bytes` và tự gọi `_check_report_access(options)`. Ở JS: `window.location.href = this.getExportUrl("xml")`.

## 7. Test

- Số liệu: kế thừa `AccountTestInvoicingCommon`, tạo tài khoản và bút toán, gọi `get_report_data()`.
- Giao diện: một tour trong `static/tests/tours/` (bundle `web.assets_tests`), chạy bằng `start_tour`. Cần gói Python `websocket-client` và Chrome.
- Bản dịch trong test: `self.env['ir.module.module']._load_module_terms([...], ['vi_VN'])`.
- Test HTTP cần `--db-filter` khớp tên database khi file cấu hình có `dbfilter = ^%d$`.
