# Kế hoạch chuyển `fg_vn_accounting_reports` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_accounting_reports` (19.0.1.0.0, commit `64fbf84` ngày 2026-10-11, "sửa lỗi phân quyền").
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e` (2026-09-11), 20.0 tại `97d8ce809` (2026-10-05).

`readme.md` mô tả module làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **đã xong cả sáu giai đoạn (2026-10-11).** 52 test chạy qua trên Odoo 20.0. Giao diện OWL 3 được kiểm bằng tour trình duyệt của `fg_vn_report_cdps` (Chrome headless), không có lỗi hay cảnh báo trong console.

Khác với kế hoạch, phát sinh khi code:

| Điểm | Kế hoạch | Thực tế | Lý do |
|---|---|---|---|
| Mở rộng dữ liệu báo cáo | Báo cáo con ghi đè `get_report_data()` | Thêm hook `_build_report_data(options)`; báo cáo con ghi đè hook này | `get_report_data()` chuyển sang ngôn ngữ báo cáo ở bên trong; phần ghi đè chạy bên ngoài sẽ dịch nhãn theo ngôn ngữ người dùng. |
| Giữ trạng thái qua drill-down | Ghi vào `props.action.context` và `sessionStorage` | Chỉ `sessionStorage`, kèm `report_token` do wizard cấp cho mỗi lần mở | Không phụ thuộc việc OWL 3 có cho ghi vào props hay không. Token phân biệt "mở mới từ wizard" (dùng tham số mới) với "quay lại từ drill-down, F5" (dùng trạng thái đã lưu). |
| Tìm giá trị cho bộ lọc nhiều-nhiều | `searchRead` theo `name`, `display_name` | `name_search` | Tìm được tài khoản theo mã; không phụ thuộc trường `name` của model. |
| Lỗi khi tải báo cáo | Hiện thông báo chung "Lỗi khi tải dữ liệu" | Để lỗi đi tới dịch vụ lỗi của Odoo | Người dùng thấy đúng nội dung lỗi (không có quyền, thiếu ngày kỳ so sánh). |
| `<select>` của bộ lọc | `t-att-selected` trên `<option>` | Thêm `t-att-value` trên `<select>` | Khi chạy thật, `t-att-selected` không chọn đúng dòng của ô ngôn ngữ. |
| Test wizard cơ sở | Wizard giả trong test của nền tảng | Test qua wizard thật của CDPS (`fg_vn_report_cdps/tests/test_wizard.py`) | `AbstractModel` không tạo được bản ghi; wizard thật kiểm đúng điều cần kiểm. |
| Model báo cáo giả trong test | Khai model riêng | Vá các hook của chính `vn.abstract.report` trong test | Không phải thêm model vào registry lúc chạy test. |
| Controller | `return request.not_found()` | `raise request.not_found()` | Odoo 20 cảnh báo khi route trả về `HTTPException`. |

Chưa làm: xem lại SCSS bằng mắt ở chế độ tối. Ảnh chụp từ tour cho thấy bố cục đúng ở chế độ sáng.

Module được chuyển và kiểm thử song song với `fg_vn_report_cdps` (xem `fg_vn_report_cdps/PLAN.md`).

Các khác biệt lõi 19.0 → 20.0 phát hiện trong lúc phân tích đã ghi vào `D:\odoo_vault\odoo\migration\v19-to-v20\`. Kế hoạch này chỉ nhắc lại phần ảnh hưởng tới module.

## 0. Đã chốt sau lần duyệt 1 (2026-10-11)

| Điểm | Quyết định |
|---|---|
| Bộ máy báo cáo tài chính (`vn.abstract.financial.report`, `vn.financial.report.engine`) | Bỏ. `fg_vn_report_balance_sheet` đã bỏ nên không còn ai dùng. |
| Đường in QWeb/wkhtmltopdf và các template QWeb cơ sở | Bỏ. |
| Ngôn ngữ chuỗi | Mọi chuỗi trong code viết tiếng Anh, dịch sang tiếng Việt qua `i18n/vi.po`. |
| Giấy phép | AGPL-3. |
| Module chuyển song song để kiểm thử | `fg_vn_report_cdps`. |
| Phân quyền | Theo cách bản 19.0 vừa làm ở commit `64fbf84` (mục 1.3). |
| Template bảng của báo cáo con | Dùng template chung của nền tảng. Sau này có thể thêm tuỳ chọn để sửa template, nhằm đồng bộ hình thức các báo cáo. |
| Ngôn ngữ báo cáo | Có tuỳ chọn, mặc định tiếng Việt cho cả hiển thị và in, chọn lại được mỗi lần xem (mục 3.1). |
| Wizard cơ sở | Đổi thành `AbstractModel`, bỏ form view cơ sở và file phân quyền. |
| Vị trí tuỳ chọn ngôn ngữ | Ở cả wizard và menu bộ lọc trên màn hình; không nhớ sang lần sau. |
| Thứ tự chuyển | `fg_vn_transfer_account` trước, rồi nền tảng cùng CDPS. |

## 1. Phân tích code nguồn

### 1.1. Thành phần và mức độ sử dụng

Mức độ sử dụng đếm bằng cách tìm trong sáu module phụ thuộc ở `fanha-addons` 19.0 (`fg_vn_report_s03a`, `fg_vn_report_s03b`, `fg_vn_report_cdps`, `fg_vn_stock_reports`, `fg_vn_asset_adapter`, `fg_vn_financial_reports`).

| Thành phần | File | Ai dùng | Sang 20.0 |
|---|---|---|---|
| `vn.report.access.mixin`: kiểm tra nhóm và công ty trước khi trả số liệu | `models/report_access_mixin.py` (mới ở `64fbf84`) | mọi báo cáo | giữ |
| `vn.abstract.report`: options, `get_report_data`, drill-down, xuất Excel theo dòng có kiểu, gọi renderer PDF | `models/abstract_report.py` | 5 module (7 báo cáo) | giữ |
| `FanhaReportPDF`: dựng PDF bằng ReportLab, phân trang, cộng chuyển trang, lề đối xứng, ký tên | `models/pdf_renderer.py` | 5 module | giữ |
| `AbstractVNReport` (OWL): thanh công cụ, kỳ, bộ lọc, tìm kiếm, thu gọn, sắp xếp, drill-down, giữ trạng thái | `static/src/js/abstract_report.js` | 5 module | viết lại theo OWL 3 |
| Template `AbstractReport`, `DataTable`, `ActionMenu` | `static/src/xml/abstract_report.xml` | 5 module | viết lại theo OWL 3 |
| SCSS của màn hình báo cáo (CSS thuần, 645 dòng) | `static/src/scss/abstract_report.scss` | 5 module | chép |
| `vn.report.wizard.abstract`: tham số chung, mở báo cáo, xuất thẳng | `wizard/abstract_wizard.py` | 5 module | giữ |
| Controller `/vn_report/<model>/export/{xlsx,pdf_rl,pdf}` | `controllers/main.py` | JS và wizard | giữ, bỏ `/pdf` |
| Menu `menu_vn_vas_reports` | `views/menu_views.xml` | cả 6 module | giữ |
| Phông DejaVu Sans (thường, đậm) | `static/fonts/` | renderer PDF | giữ |
| `vn.abstract.financial.report`, `vn.financial.report.engine` | 2 file trong `models/` | không ai | **bỏ** |
| Template QWeb cơ sở | `report/base_report_template.xml` | chỉ template QWeb cũ của CDPS | **bỏ** |
| `get_pdf()`, `_get_pdf_template()`, route `/export/pdf`, `action_export_pdf()` | rải ở 3 file | 2 nút trên form wizard của `fg_vn_asset_adapter` | **bỏ** |
| Form view `view_vn_report_wizard_abstract_form` | `wizard/abstract_wizard_views.xml` | không ai kế thừa | đề xuất bỏ (mục 8) |
| `_format_partner_code()` | `models/abstract_report.py` | không ai | bỏ |

Module khai báo phụ thuộc `stock` và `stock_account` nhưng code không đụng tới model nào của hai module này.

### 1.2. Lỗi và điểm yếu của code nguồn

Bản phân tích lần 1 (trên commit `e29d96f`) liệt kê 12 điểm. Commit `64fbf84` đã sửa 10 điểm; phần chuyển sang 20.0 lấy nguyên các bản sửa đó.

| # | Vấn đề | Tình trạng ở `64fbf84` |
|---|---|---|
| L1 | Không kiểm tra quyền trên `get_report_data` và URL xuất file | Đã sửa: `vn.report.access.mixin` |
| L2 | `options['company_id']` từ trình duyệt không được đối chiếu | Đã sửa: phải thuộc `env.user.company_ids` |
| L3 | Controller nhận model bất kỳ có hàm `get_xlsx` | Đã sửa: cờ `_is_vn_report` |
| L4 | Mỗi lần xuất tính báo cáo hai lần để lấy tên file | Đã sửa: `_get_export_filename_code(options)` |
| L5 | Bộ máy báo cáo tài chính lọc `account.account` theo `company_id` | Còn, nhưng code này bị bỏ |
| L6 | Ngày mặc định của wizard lấy `date.today()` của máy chủ | Đã sửa: `fields.Date.context_today` |
| L7 | Ép `lang=vi_VN` trong context và URL | Đã sửa; `options` trong URL được `quote` |
| L8 | `formatDate` lệch một ngày ở múi giờ âm | Đã sửa: tách chuỗi `YYYY-MM-DD` |
| L9 | Tìm kiếm gọi `toLowerCase()` trên số | Đã sửa |
| L10 | Renderer PDF thiếu `_group_to_rows` ở lớp cơ sở, biến thừa | Đã sửa; `_page_group_labels`, `_page_info` được khởi tạo trong `__init__` |
| L11 | `except:` trần | Đã sửa ở `abstract_report.py` |
| L12 | Không có test | **Còn.** Viết test khi chuyển. |

Điểm mới thấy khi đọc lại:

| # | Vị trí | Vấn đề |
|---|---|---|
| L13 | `report_access_mixin.py`, `abstract_wizard.py`, `abstract_report.py`, JS, template | Chuỗi tiếng Việt viết thẳng trong code, kể cả trong `_()`. Phải đổi sang tiếng Anh (mục 0). |
| L14 | `pdf_renderer.py` | Chuỗi in trên biểu mẫu ("Cộng chuyển trang", "Người lập biểu"…) viết cứng trong lớp Python thuần, không qua cơ chế dịch. |

### 1.3. Phân quyền ở bản 19.0 (commit `64fbf84`)

`vn.report.access.mixin` là `AbstractModel`, được `vn.abstract.report` kế thừa:

- `_is_vn_report = True`: controller chỉ nhận model có cờ này.
- `_get_report_access_groups()`: trả danh sách xml_id nhóm, thuộc một nhóm là đủ. Mặc định `['account.group_account_user']`, khớp với nhóm được cấp quyền trên các wizard báo cáo.
- `_check_report_access(options=None)`: bỏ qua khi `env.su`; báo `AccessError` nếu người dùng không thuộc nhóm nào trong danh sách, hoặc `options['company_id']` không thuộc `env.user.company_ids`; chuẩn hoá `company_id` về số nguyên.
- Gọi ở đầu `get_report_data()` và `action_drill_down()`. `get_xlsx()` và `get_pdf_rl()` đi qua `get_report_data()` nên cũng được kiểm tra. Hàm công khai riêng của báo cáo con phải tự gọi (CDPS: `export_to_xml`).
- Báo cáo kho (`s06`, `thtk`) ghi đè để thêm `stock.group_stock_user`.

Kế hoạch lần 1 đề xuất nhóm mặc định `account.group_account_readonly` và một hàm trả một nhóm; nay bỏ đề xuất đó, làm đúng như 19.0. Hệ quả: người chỉ có quyền "chỉ xem" kế toán (`group_account_readonly`) không xem được báo cáo, giống 19.0.

Đã kiểm tra trên lõi 20.0: `res.users.has_groups(spec)` với danh sách xml_id cách nhau bằng dấu phẩy vẫn có (lõi dùng ở `account_move.py:2600`); `res.users.company_ids`, `env.su`, `odoo.exceptions.AccessError` không đổi; ba nhóm `account.group_account_user`, `account.group_account_readonly`, `stock.group_stock_user` vẫn tồn tại.

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng tới module

Mức "chặn" nghĩa là code 19.0 không chạy được trên 20.0 nếu giữ nguyên.

| # | Khác biệt | Chỗ bị ảnh hưởng | Mức | Vault |
|---|---|---|---|---|
| K1 | OWL 2.8.4 → **OWL 3.0.0-alpha.49**. `useState`, `useRef`, `useExternalListener`, `reactive`, `onRendered` không còn được export. Thay bằng `proxy`, `signal`, `signal.ref()`, `computed`, `useListener`. | `abstract_report.js` import `useState`, `useRef` | chặn | `frontend-owl.md` §1, §3 |
| K2 | Khai báo `static props` ném lỗi ngay khi tạo component. Phải dùng `props = useProps({...})` với kiểu `t.*`. | `static props = ["*"]` | chặn | `frontend-owl.md` §2 |
| K3 | Biểu thức trong template không còn ngầm trỏ vào component. Thành viên của component phải viết `this.x`; biến cục bộ (`t-as`, `t-set`) viết trần. | Mọi biểu thức trong `abstract_report.xml` | chặn | `frontend-owl.md` §4 |
| K4 | `t-ref` nhận biểu thức trỏ tới `signal.ref()` thay vì tên chuỗi; đọc phần tử bằng `ref()` thay vì `ref.el`. | `t-ref="dateDropdown"`, `t-ref="filterDropdown"` | chặn | `frontend-owl.md` §3 |
| K5 | `t-esc` và `t-slot` còn chạy trong OWL 3 nhưng in cảnh báo; tên mới là `t-out` và `t-call-slot`. | 13 chỗ `t-esc`, 1 chỗ `t-slot` | cảnh báo | `frontend-owl.md` §5 |
| K6 | `t-call` nhận tham số qua thuộc tính. Thân `t-call` nay được biên dịch thành khối trễ, nên `t-set` đặt trong thân không còn truyền biến cho template con. | Lời gọi `ActionMenu` truyền `menuItems` bằng `t-set` trong thân | chặn (suy từ code trình biên dịch, phải chạy thử) | `frontend-owl.md` §6 |
| K7 | Props của `Dropdown`, `DropdownItem`, `DateTimeInput` khai bằng `useProps`; tên và ý nghĩa props mà module dùng không đổi. | `ActionMenu`, ô nhập ngày | không chặn | `frontend-owl.md` §7 |
| K8 | `standardActionServiceProps` chuyển sang `@web/webclient/actions/action_plugin`. Client action vẫn nhận `props.action`. | Khai báo props của component | cần sửa | `frontend-owl.md` §8 |
| K9 | `ir.model.access` và `ir.rule` bị xoá, gộp thành model `ir.access`. File là `security/ir.access.csv`. | `security/ir.model.access.csv` | chặn | `security.md` |
| K10 | `odoo/http.py` tách thành gói. `content_disposition` nằm ở `odoo.http.stream`. | `controllers/main.py` | chặn | `orm-python.md` §2 |
| K11 | Lõi bỏ hẳn `pytz`; `env.tz` trả về `zoneinfo.ZoneInfo`. | `abstract_report.py` dùng `pytz.timezone().localize()` và bắt `pytz.UnknownTimeZoneError` | chặn trên máy cài sạch | `orm-python.md` §1 |
| K12 | wkhtmltopdf tách khỏi `base`; `_run_wkhtmltopdf` đổi nghĩa. | `get_pdf()` | chỉ ảnh hưởng code bị bỏ | `reports-qweb.md` §1 |
| K13 | QWeb phía máy chủ bỏ `t-esc` và `t-raw`. | `base_report_template.xml` | chỉ ảnh hưởng code bị bỏ | `reports-qweb.md` §2 |
| K14 | `account.account`: bỏ `_search_code` và `_field_to_sql`, thay bằng `compute_sql`. | `financial_report_engine.py` | chỉ ảnh hưởng code bị bỏ | `account.md` §1 |
| K15 | Yêu cầu tối thiểu: Python 3.12, PostgreSQL 16. `reportlab` 4.1.0 và `XlsxWriter` 3.1.9 không đổi. | `pdf_renderer.py`, xuất Excel | không cần sửa | `orm-python.md` §4 |
| K16 | Model `account.group` bị xoá; tài khoản tự có cây cha–con (`parent_id`, `parent_path`). | Không ảnh hưởng module này; ảnh hưởng `fg_vn_report_cdps` | | `account.md` §3 |

Đã kiểm tra và **không đổi**: `from odoo import models, fields, api, _`; `env._()`; `fields.Date.context_today`; `request.make_response`, `request.not_found`; menu `account.menu_finance_reports`; bundle `web.assets_backend`; `registry.category("actions")`; `useService("orm" | "action" | "notification")`; `formatFloat` ở `@web/views/fields/formatters`; biến toàn cục `luxon`; các cột `debit`, `credit`, `date`, `parent_state`, `company_id` của `account.move.line`.

## 3. Quyết định thiết kế

Cột "Tình trạng": **chốt** là đã được duyệt hoặc lấy nguyên từ 19.0; **đề xuất** là chờ duyệt.

| # | Vấn đề | Quyết định | Tình trạng |
|---|---|---|---|
| 1 | Chuyển hay viết lại | Python: giữ cấu trúc và tên hàm của `64fbf84`, chỉ sửa chỗ cần. JS và template: viết lại theo OWL 3 thuần, không dựa vào lớp tương thích `@web/owl2/utils` (lõi ghi rõ đó là cầu nối tạm thời). | đề xuất |
| 2 | Code không ai dùng | Bỏ bộ máy báo cáo tài chính, `report/base_report_template.xml`, `get_pdf()`, `_get_pdf_template()`, route `/export/pdf`, `action_export_pdf()`, `_format_partner_code()`. | chốt |
| 3 | Phụ thuộc | Chỉ `account`. Bỏ `stock`, `stock_account`. | đề xuất |
| 4 | Wizard cơ sở | Đổi `vn.report.wizard.abstract` từ `TransientModel` thành `AbstractModel`; bỏ form view cơ sở. Module không còn file phân quyền. Wizard con vẫn là `TransientModel` với `_name` riêng và tự có dòng `ir.access`. Giải thích ở mục 8. | chốt |
| 5 | Phân quyền | `vn.report.access.mixin` đúng như mục 1.3, giữ thành file riêng để dễ đối chiếu với 19.0. | chốt |
| 6 | Múi giờ (K11) | Dùng `zoneinfo`. Giữ mặc định `Asia/Ho_Chi_Minh` khi người dùng chưa đặt múi giờ; bắt `ZoneInfoNotFoundError`. | đề xuất |
| 7 | Trạng thái trong component (K1) | `this.state = proxy({...})`, giữ nguyên tên các khoá; hai ref dùng `signal.ref()`; bắt click ngoài bằng `useListener(document, "click", …, { capture: true })`. | đề xuất |
| 8 | Template của báo cáo con | Component cơ sở tự hiển thị `DataTable`. Báo cáo con không cần file XML nữa; báo cáo cần bảng riêng thì đặt `static tableTemplate`. Tuỳ chọn sửa template để lại sau, không thuộc đợt chuyển này. | chốt |
| 9 | Dropdown kỳ và bộ lọc | Giữ dropdown tự viết, chưa chuyển sang `Dropdown` của Odoo (menu của `Dropdown` bị đưa ra ngoài cây DOM nên CSS của báo cáo không áp được). | đề xuất |
| 10 | Giữ trạng thái qua drill-down | Giữ cơ chế hiện có: `props.action.context` và `sessionStorage`. Phải chạy thử xem OWL 3 có cho ghi vào `props.action.context` không; nếu không thì chỉ dùng `sessionStorage`. | đề xuất |
| 11 | Ngôn ngữ chuỗi | Mọi chuỗi viết tiếng Anh: Python qua `_()`, JS qua `_t()`, template và view để Odoo tự trích. Bản dịch ở `i18n/vi.po`. Áp dụng cả cho chuỗi in trên PDF và Excel. | chốt |
| 12 | Dịch trong renderer PDF (L14) | `FanhaReportPDF.__init__(report_data, env)`; lưu `self.env`; các nhãn lấy qua `self.env._("Carried forward")`… `get_pdf_rl()` truyền `self.env`. | đề xuất |
| 13 | Tên file xuất | `_get_export_filename_code(options)` như 19.0. | chốt |
| 14 | Renderer PDF | Giữ nguyên thuật toán phân trang. Thay đổi duy nhất là quyết định 12. | đề xuất |
| 15 | Giấy phép | AGPL-3. | chốt |
| 16 | Tài liệu cho người viết báo cáo | Chuyển `INHERITORS.md` thành `doc/DEVELOPER.md`, viết lại theo API 20.0. | đề xuất |
| 17 | Ngôn ngữ báo cáo | Tuỳ chọn `lang` trong `options`, mặc định `vi_VN`. Chi tiết ở mục 3.1. | chốt |
| 18 | Bộ lọc kiểu ngày | Thêm kiểu bộ lọc `date` vào danh sách kiểu mà `getFilterDefinitions()` nhận (hiện có `many2many`, `many2one`, `selection`, `boolean`), kèm thuộc tính `visible(filters)` để một bộ lọc chỉ hiện khi bộ lọc khác có giá trị nhất định. | chốt; CDPS cần cho kỳ so sánh tự chọn |

### 3.1. Tuỳ chọn ngôn ngữ báo cáo

Bản 19.0 từng ép `lang=vi_VN`, rồi bỏ ở commit `64fbf84`. Bản 20.0 biến nó thành tuỳ chọn.

**Đặt ở hai chỗ, cùng một giá trị `options['lang']`:**

1. **Cửa sổ tham số (wizard):** trường `report_lang` trên wizard cơ sở, kiểu chọn một trong các ngôn ngữ đã cài của database, mặc định tiếng Việt. Mỗi lần mở báo cáo đều thấy và đổi được. Các nút xuất thẳng Excel, PDF từ wizard dùng luôn giá trị này.
2. **Thanh công cụ của màn hình báo cáo:** một mục chọn ngôn ngữ nằm trong menu bộ lọc, để đổi khi đang xem mà không phải mở lại wizard. Đổi xong báo cáo tải lại; Excel và PDF xuất từ màn hình theo ngôn ngữ đang chọn.

Lựa chọn không được nhớ sang lần mở sau: mỗi lần mở wizard, mặc định quay về tiếng Việt.

**Cách hoạt động:** `get_report_data()` (và qua nó là `get_xlsx()`, `get_pdf_rl()`) chạy lại chính mình với `self.with_context(lang=…)` sau khi kiểm tra quyền. Mọi `_()` ở Python, renderer PDF (`self.env._()`), và tên tài khoản, tên đối tác đọc từ database đều theo ngôn ngữ đó.

**Phạm vi:**

| Phần | Theo tuỳ chọn ngôn ngữ báo cáo | Theo ngôn ngữ giao diện của người dùng |
|---|---|---|
| Tên báo cáo, kỳ, tiêu đề cột, nội dung dòng, dòng cộng | ✓ | |
| File Excel, file PDF (gồm cộng chuyển trang, ký tên, số trang) | ✓ | |
| Nút và menu trên thanh công cụ, nhãn bộ lọc, thông báo lỗi | | ✓ |
| Cửa sổ tham số | | ✓ |

Để làm được, mọi chữ nằm **trong bảng** phải do máy chủ trả về trong `get_report_data()`, không dựng ở JS. Bản 19.0 có vài nhãn dựng ở JS (ví dụ "TỔNG CỘNG" của CDPS); khi chuyển phải đưa về máy chủ.

**Giới hạn:** bản dịch tiếng Việt chỉ được nạp khi database đã cài ngôn ngữ `vi_VN`. Danh sách chọn chỉ gồm ngôn ngữ đã cài; nếu chưa cài tiếng Việt thì mặc định là ngôn ngữ của người dùng. Module không tự cài ngôn ngữ.

## 4. Cấu trúc module sau khi chuyển

```
fg_vn_accounting_reports/
├── __init__.py
├── __manifest__.py                 depends: account; version 20.0.1.0.0; AGPL-3
├── readme.md
├── PLAN.md
├── doc/DEVELOPER.md                hướng dẫn viết báo cáo mới
├── controllers/main.py             /vn_report/<model>/export/xlsx, /export/pdf_rl
├── models/
│   ├── report_access_mixin.py      vn.report.access.mixin
│   ├── abstract_report.py          vn.abstract.report
│   └── pdf_renderer.py             FanhaReportPDF
├── wizard/abstract_wizard.py       vn.report.wizard.abstract
├── views/menu_views.xml            menu VAS Reports
├── i18n/                           .pot và vi.po
├── static/
│   ├── description/index.html
│   ├── fonts/                      DejaVuSans, DejaVuSans-Bold
│   └── src/
│       ├── js/abstract_report.js
│       ├── xml/abstract_report.xml
│       └── scss/abstract_report.scss
└── tests/
    ├── common.py                   model báo cáo giả dùng cho test
    ├── test_access.py
    ├── test_abstract_report.py
    ├── test_pdf_renderer.py
    ├── test_xlsx.py
    ├── test_wizard.py
    └── test_controller.py
```

So với 19.0: bỏ `models/abstract_financial_report.py`, `models/financial_report_engine.py`, `report/`, `security/`, `wizard/abstract_wizard_views.xml`, `INHERITORS.md`.

## 5. Việc cần làm theo file

### `__manifest__.py`

`version` 20.0.1.0.0; `license` AGPL-3; `depends` chỉ `account`; `category` `Accounting/Accounting`; thêm `description` ngắn (không có thì Odoo đọc `readme.md` như reStructuredText và báo lỗi bảng Markdown); bỏ các file data đã xoá; giữ ba file trong `web.assets_backend`.

### `models/report_access_mixin.py`

Chép từ `64fbf84`. Ba thông báo lỗi đổi sang tiếng Anh. Không đổi logic.

### `models/abstract_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_get_user_timezone()` | Trả `ZoneInfo`; mặc định `Asia/Ho_Chi_Minh`; bắt `ZoneInfoNotFoundError`. |
| `_convert_date_to_utc_range()` | Thay `tz.localize(dt)` bằng `dt.replace(tzinfo=tz)`; kết quả như cũ. |
| `_get_utc_datetime_range()` | Giữ. |
| `_get_report_name()`, `_get_report_code()`, `_get_export_filename_code()`, `_get_columns()` | Giữ. |
| `_get_default_options()`, `_get_custom_options()` | Giữ. |
| `get_report_data()` | Giữ kiểm tra quyền; thêm chuyển ngôn ngữ theo `options['lang']` (mục 3.1); trả thêm danh sách ngôn ngữ đã cài cho mục chọn trên màn hình. |
| `_get_report_lang(options)` | **Mới**: trả mã ngôn ngữ hợp lệ (đã cài) từ `options`, mặc định `vi_VN`, không có thì ngôn ngữ người dùng. |
| `action_drill_down()`, `_get_drill_down_action()` | Giữ (đã có kiểm tra quyền). |
| Nhóm xuất Excel (`get_xlsx`, `_write_xlsx_*`, `_get_xlsx_formats`, `_pick_xlsx_format`, `_groups_to_xlsx_rows`, `_group_to_xlsx_rows`, `_should_xlsx_split_by_group`, `_format_xlsx_sheet_name`, `_format_xlsx_group_label`, `_set_xlsx_column_widths`, `_unique_sheet_name`) | Giữ logic; chuỗi in ra file đổi sang `_()` tiếng Anh; đưa `import io`, `xlsxwriter` lên đầu file. |
| `get_pdf_rl()` | Truyền `self.env` cho renderer (quyết định 12). |
| `_get_pdf_rl_renderer()`, `_format_date()`, `_format_number()` | Giữ. |
| `get_pdf()`, `_get_pdf_template()`, `_format_partner_code()` | Bỏ. |

### `models/pdf_renderer.py`

Chép từ `64fbf84`. Thêm tham số `env` cho `__init__`; các chuỗi tiếng Việt in trên trang ("Từ ngày … đến ngày …", "Cộng chuyển trang", "Số dư đầu trang", "Sổ này bao gồm … trang…", "Ngày mở sổ", "Ngày …", ba chức danh ký, "(Ký, họ tên)", "(Ký, họ tên, đóng dấu)") đổi thành `self.env._("…")` tiếng Anh. Chuỗi "Trang x/y" được vẽ trong lớp canvas `_NumberedCanvas`, nơi không có `env`: renderer dịch sẵn mẫu chuỗi rồi truyền cho canvas. Không sửa thuật toán phân trang.

### `wizard/abstract_wizard.py`

Chép từ `64fbf84`. Bỏ `action_export_pdf()`. Nhãn trường, lựa chọn và thông báo lỗi đổi sang tiếng Anh; nhãn `show_zero_balance` đổi thành nhãn chung thay cho "Hiện mặt hàng không có phát sinh". Thêm trường `report_lang` (mục 3.1) và đưa vào `_get_report_options()` dưới khoá `lang`. Đổi lớp cha thành `models.AbstractModel` (quyết định 4). Test của nền tảng khai một wizard giả là `TransientModel` kế thừa lớp này để kiểm tra các hàm mở báo cáo và xuất file.

### `controllers/main.py`

Chép từ `64fbf84` (đã gộp về `_export`). Import `content_disposition` từ `odoo.http.stream` (K10). Bỏ route `/export/pdf`. `_export` giữ là hàm dùng lại được để báo cáo con thêm định dạng riêng (CDPS thêm XML); thêm tham số tuỳ chọn `filename_code` để định dạng riêng đặt được tên file khác với mã mẫu.

### `static/src/js/abstract_report.js`

| Phần | 19.0 | 20.0 |
|---|---|---|
| Đầu file | `/** @odoo-module **/` | Bỏ (không còn cần) |
| Import | `Component, useState, onWillStart, useRef, onMounted, onWillUnmount` | `Component, onWillStart, proxy, signal, useListener, useProps` |
| Props | `static props = ["*"]` | `props = useProps(standardActionServiceProps)` |
| State | `useState({...})` | `proxy({...})`, giữ nguyên các khoá |
| Ref | `useRef("filterDropdown")`, `.el` | `filterDropdownRef = signal.ref()`, đọc bằng `this.filterDropdownRef()` |
| Click ngoài | `onMounted` + `onWillUnmount` + `addEventListener` | `useListener(document, "click", …, { capture: true })` |
| Template con | Báo cáo con tự khai template gọi `DataTable` | `static tableTemplate = "fg_vn_accounting_reports.DataTable"` (quyết định 8) |
| Chuỗi | Tiếng Việt viết thẳng (64 dòng có chữ Việt) | `_t("…")` tiếng Anh |
| Kiểu bộ lọc | `many2many`, `many2one`, `selection`, `boolean` | Thêm `date` và thuộc tính `visible` (quyết định 18) |
| Ngôn ngữ báo cáo | Không có | Mục chọn ngôn ngữ trong menu bộ lọc; giá trị nằm trong `state.options.lang`, gửi kèm mọi lần tải và xuất (mục 3.1). |

Các hàm còn lại (kỳ báo cáo, bộ lọc, `_buildOptions`, `loadReportData`, lưu trạng thái, thu gọn, sắp xếp, định dạng ô, drill-down, xuất file) giữ nguyên logic và tên, lấy theo `64fbf84`.

Điểm phải chạy thử: `Set` nằm trong `proxy` có phản ứng khi `add`/`delete` không (code hiện đã gán lại `new Set(...)` sau mỗi thay đổi nên vẫn chạy được kể cả khi không).

### `static/src/xml/abstract_report.xml`

Thêm `this.` cho mọi thành viên component (K3); `t-esc` → `t-out`; `t-ref` trỏ tới signal (K4); vị trí `t-slot="report_table"` thay bằng `<t t-call="{{ this.constructor.tableTemplate }}"/>`; lời gọi `ActionMenu` truyền `menuItems` qua thuộc tính của `t-call` (K6); chuỗi tiếng Việt (32 dòng) đổi sang tiếng Anh. Ba template giữ tên cũ.

### `static/src/scss/abstract_report.scss`

Chép nguyên. Rà lại bằng mắt trên giao diện 20.0 (chế độ tối, thanh điều hướng mới) khi làm giao diện.

### `views/menu_views.xml`

Giữ nguyên.

### `i18n/`

Xuất `fg_vn_accounting_reports.pot` từ Odoo sau khi code xong, rồi viết `vi.po`. Bản dịch tiếng Việt của các chuỗi in trên biểu mẫu lấy đúng nguyên văn chuỗi của 19.0.

## 6. Thay đổi mà các module báo cáo phải theo khi được chuyển

| Thay đổi ở nền tảng | Việc ở module báo cáo |
|---|---|
| Component cơ sở viết bằng OWL 3 | Lớp con bỏ `useState`/`useRef` nếu có dùng riêng; template riêng thêm `this.`; bỏ `static props` nếu có. |
| `DataTable` hiển thị mặc định | Xoá file template 11 dòng và dòng `static template`. |
| Bỏ `_get_pdf_template()` và các template QWeb cơ sở | Xoá các ghi đè `_get_pdf_template()` (5 chỗ) và template QWeb cũ. |
| Bỏ `action_export_pdf()` | `fg_vn_asset_adapter`: đổi 2 nút trên form wizard sang `action_export_pdf_rl`. |
| Renderer PDF nhận `env` | Lớp con có `__init__` riêng (CDPS) nhận và chuyển tiếp `env`; nhãn cột đổi sang `self.env._()`. |
| Chuỗi tiếng Anh | Mọi chuỗi của báo cáo con viết tiếng Anh, kèm `i18n/vi.po`. |
| Tuỳ chọn ngôn ngữ báo cáo | Form wizard con thêm trường `report_lang`. Mọi chữ nằm trong bảng (nhãn dòng cộng, nhãn nhóm) do máy chủ trả về, không dựng ở JS. |
| `ir.model.access.csv` → `ir.access.csv` | Viết lại file phân quyền của từng module. |
| Phân quyền | Hàm công khai riêng của báo cáo con phải gọi `_check_report_access(options)`. Báo cáo kho ghi đè `_get_report_access_groups()`. |
| Bỏ phụ thuộc `stock` | `fg_vn_stock_reports` tự khai phụ thuộc `stock`, `stock_account`. |
| SQL lấy mã tài khoản | Vẫn `code_store->>'<id công ty gốc>'` như ghi chú 19.0. |
| Thiết lập ẩn tài khoản trung chuyển | Gọi `company._fg_get_hidden_transfer_accounts()` của `fg_vn_transfer_account`; xử lý một tập tài khoản. |
| `account.group` bị xoá (K16) | Báo cáo nào dựng cây theo `account.group` (CDPS) phải chuyển sang `account.account.parent_id`. |

## 7. Các giai đoạn

Hai module đi cùng nhau; cột "CDPS" là việc tương ứng trong `fg_vn_report_cdps/PLAN.md`.

| Giai đoạn | `fg_vn_accounting_reports` | CDPS | Xong khi |
|---|---|---|---|
| T | (trước tiên) Chuyển `fg_vn_transfer_account` theo `fg_vn_transfer_account/PLAN.md`. | | Module đó cài được và test chạy qua. |
| 0 | Khung module: manifest, `__init__`, menu, khung test. | Khung module CDPS. | Cài được cả ba trên 20.0, không cảnh báo khi nạp. |
| 1 | Mixin phân quyền, `vn.abstract.report` (options, múi giờ), xuất Excel. | Tính số liệu, cây tài khoản, dòng Excel. | Test quyền, options, múi giờ; test số liệu CDPS trên bút toán mẫu; mở được file Excel. |
| 2 | `pdf_renderer.py`. | `cdps_pdf.py`. | Test phân trang (số trang, cộng chuyển trang, đặt lại theo nhóm, `keep_with_next`, trang trắng khi lề đối xứng); PDF CDPS mở được và có tiếng Việt. |
| 3 | Wizard cơ sở, controller. | Wizard CDPS, xuất XML. | Test HTTP: xuất được các định dạng; người không có quyền, công ty lạ và tên model lạ bị từ chối; tên file đúng. |
| 4 | Giao diện OWL 3: JS, template, SCSS. | JS của CDPS. | Mở CDPS trên trình duyệt không có lỗi hay cảnh báo OWL trong console; chạy đủ kỳ, bộ lọc, tìm kiếm, thu gọn, drill-down và quay lại, F5, xuất file. Sắp xếp cột thử bằng báo cáo giả trong test vì CDPS không dùng. |
| 5 | `i18n/vi.po`, `static/description/index.html`, `doc/DEVELOPER.md`, dòng trong `README.md` của repo. | `i18n/vi.po`, `static/description/index.html`. | Người dùng giao diện tiếng Anh mở báo cáo mặc định thấy bảng, Excel, PDF tiếng Việt; đổi tuỳ chọn sang tiếng Anh thì cả ba đổi theo. |

Sau mỗi giai đoạn: chạy lại toàn bộ test của hai module và ghi vào vault những khác biệt lõi mới gặp.

## 8. Ghi chú về wizard cơ sở (đã chốt)

`vn.report.wizard.abstract` chứa phần chung của mọi cửa sổ tham số và không ai mở trực tiếp nó. Ở 19.0 nó khai là `TransientModel`, nên Odoo tạo một bảng luôn rỗng, đòi một dòng phân quyền, và có một form view không wizard con nào dùng lại. Ở 20.0 nó là `AbstractModel`: không bảng, không phân quyền, không form.

Điều kiện để việc đổi này an toàn, sẽ kiểm tra bằng test ở giai đoạn 3:

- Wizard con khai `models.TransientModel` với `_name` riêng và `_inherit = 'vn.report.wizard.abstract'` nhận đủ trường và hàm của lớp cơ sở.
- Giá trị mặc định của các trường (ngày, công ty, hướng giấy, ngôn ngữ) hoạt động trên wizard con.
- Wizard con tạo được bản ghi, mở được báo cáo và xuất được file với người dùng thuộc nhóm kế toán.

Không còn điểm nào chờ xác nhận ở module này.

## 9. Bản 20.0.1.1.0 (đã duyệt, chưa làm)

Ba việc phát sinh khi chuẩn bị chuyển sổ nhật ký chung và sổ cái; đã được duyệt cùng hai kế hoạch đó ngày 2026-10-11.

| Việc | Mô tả ở | Ai cần |
|---|---|---|
| Tải dần cho sổ dài: ba hook trên `vn.abstract.report`, hàm công khai `get_group_lines()`, dòng "Xem thêm" và tìm kiếm ở máy chủ trên component cơ sở | `fg_vn_report_s03a/PLAN.md` mục 3b | S03a, S03b, sau này sổ chi tiết vật tư |
| Tiêu đề trang PDF là danh sách dòng mở rộng được, có nhãn nhóm | `fg_vn_report_s03b/PLAN.md` mục 3a | S03b, sau này sổ chi tiết vật tư |
| Giới hạn số dòng khi in PDF: `get_pdf_rl()` từ chối và báo người dùng khi `_count_lines()` vượt tham số `fg_vn_accounting_reports.pdf_line_limit` | `fg_vn_report_s03a/PLAN.md` mục 3b | Mọi báo cáo có khai `_count_lines()` |

Báo cáo không bật tải dần, không khai `_count_lines()` và không ngắt trang theo nhóm (CDPS) không thay đổi.

Thứ tự làm chung của đợt này: đo trên dữ liệu lớn → `fg_vn_transfer_account` 20.0.1.1.0 (quy tắc ghép dùng chung) → nền tảng 20.0.1.1.0 (ba việc trên) → `fg_vn_report_s03a` → `fg_vn_report_s03b`.
