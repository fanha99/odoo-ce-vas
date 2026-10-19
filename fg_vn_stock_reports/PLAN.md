# Kế hoạch chuyển `fg_vn_stock_reports` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_stock_reports` (19.0.1.0.0, commit cuối đụng tới module: `64fbf84` ngày 2026-10-11, thêm `_get_report_access_groups()` cho hai báo cáo; không có thay đổi chưa commit).
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả hai báo cáo làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **chờ duyệt, chưa viết code.** Sáu điểm cần quyết định nằm ở mục 8; readme đang viết theo phương án đề xuất của từng điểm.

Nền tảng (`fg_vn_accounting_reports` 20.0.1.1.0) đã có trên 20.0 và đã có cơ chế tải dần. Các quy ước chung (OWL 3, `ir.access`, chuỗi tiếng Anh, tuỳ chọn ngôn ngữ, cách viết test) theo `fg_vn_accounting_reports/doc/DEVELOPER.md` và làm như `fg_vn_report_s03b` (báo cáo có nhóm, tải dần theo nhóm, Excel mỗi nhóm một sheet, PDF mỗi nhóm một trang mới). Kế hoạch này chỉ ghi phần riêng của hai báo cáo kho. Dự kiến không phải sửa nền tảng.

## 1. Phân tích code nguồn

### 1.1. Thành phần

| Thành phần | File | Dòng | Sang 20.0 |
|---|---|---|---|
| `vn.report.s06`: chọn mặt hàng theo tài khoản kho, tồn đầu kỳ và phát sinh của từng mặt hàng, số tồn luỹ kế, drill-down, dòng Excel | `models/s06_report.py` | 387 | viết lại phần truy vấn, giữ cấu trúc dữ liệu |
| `S06PDF`: cột theo hướng giấy, mỗi mặt hàng một trang, cộng chuyển trang | `models/s06_pdf.py` | 193 | giữ, bỏ phần vẽ tiêu đề trang |
| `vn.report.thtk`: nhập xuất tồn toàn công ty, có lọc vị trí, nhóm theo vị trí; tiêu đề Excel hai tầng | `models/thtk_report.py` | 603 | viết lại phần truy vấn theo vị trí, giữ phần còn lại |
| `ThtkPDF` | `models/thtk_pdf.py` | 135 | giữ |
| Hai wizard và form | `wizard/*.py`, `wizard/*.xml` | 63 + 61, 64 + 56 | giữ, bỏ `location_ids` của S06 |
| Client action, menu ở Kho và ở Kế toán | `views/menu_views.xml` | 62 | giữ |
| `S06Report`, `THTKReport` (OWL) | `static/src/js/*.js` | 204 + 238 | sửa theo OWL 3, sửa các action hỏng |
| Hai template gọi `DataTable` | `static/src/xml/*.xml` | 11 + 11 | bỏ (nền tảng tự hiển thị bảng) |
| Phân quyền hai wizard cho kế toán và thủ kho | `security/ir.model.access.csv` | 4 dòng | đổi sang `ir.access.csv` |

Module không có test, không có `i18n/`, không có readme.

### 1.2. Lỗi và điểm yếu có sẵn

Chung cho hai báo cáo:

| # | Vị trí | Vấn đề |
|---|---|---|
| C1 | mọi câu SQL | Số lượng lấy `sm.quantity`, là số theo **đơn vị của phiếu**. Mặt hàng mua theo thùng, tồn theo cái thì số lượng sai. |
| C2 | `s06_report.js:33`, `thtk_report.js:30` | Bộ lọc Mặt hàng trên màn hình dùng domain `type = 'product'`. Giá trị này không còn từ Odoo 18; danh sách chọn luôn trống. |
| C3 | 6 chỗ ở Python, JS, PDF | Nơi cần mã mặt hàng lại lấy `product_id`, tức số id của bản ghi: tiêu đề nhóm, tên sheet, nhãn PDF của S06; cột "Mã SP" của bảng tổng hợp trên màn hình, Excel và PDF. `default_code` có trong dữ liệu nhưng chỉ dùng để sắp xếp. Lặp lại nhất quán nên có thể là cố ý (mục 8, điểm 1). |
| C4 | Toàn module | Giá trị là tổng `value` của các phiếu. Lần đổi giá vốn (`product.value` không gắn phiếu) không được tính, nên tồn cuối kỳ có thể lệch với định giá của Odoo. Với mặt hàng tính **giá chuẩn**, giá trị nhập trên phiếu lấy theo giá mua còn Odoo định giá tồn theo giá chuẩn, nên hai số vốn đã khác nhau. |
| C5 | Toàn module | Chuỗi tiếng Việt viết thẳng, một phần ở JS. `_get_pdf_template()` và hai file template là code chết. Biểu tượng FontAwesome. |

S06:

| # | Vị trí | Vấn đề |
|---|---|---|
| S1 | `s06_report.py:209-262` | Nạp **mọi** mặt hàng có theo dõi tồn kho của công ty, rồi với mỗi mặt hàng chạy hai câu SQL và đọc tài khoản của nhóm qua ORM. 5.000 mặt hàng là 10.000 câu SQL, kể cả cho mặt hàng không có phiếu nào. |
| S2 | `s06_report.py:104` | `DATE_TRUNC('day', sm.date)` cắt ngày theo UTC. Phiếu hoàn tất trước 7 giờ sáng giờ Việt Nam hiện vào ngày hôm trước; kỳ lọc thì theo múi giờ người dùng. |
| S3 | `s06_report.py:129` | Thứ tự trong ngày theo `picking_type_id` rồi `reference`. Số tồn luỹ kế phụ thuộc thứ tự này; không có quy tắc nhập trước xuất sau, nên tồn giữa ngày có thể âm giả. Hai phiếu cùng khoá sắp xếp thì thứ tự không xác định. |
| S4 | `s06_report.py:151-160` | Diễn giải: phiếu nhập ghi "Nhập hàng theo HĐ " và phiếu xuất ghi "Xuất hàng theo HĐ " không kèm số nào; chỉ phiếu nhập có bút toán mới kèm tham chiếu. |
| S5 | `s06_wizard.py:26,60`, `s06_report.js:42` | `location_ids` có trên wizard và màn hình, được gửi đi, nhưng báo cáo không đọc. |
| S6 | `s06_report.py:207` so với `thtk_report.py:65` | Bộ lọc nhóm sản phẩm của S06 dùng `in` (không lấy nhóm con), của bảng tổng hợp dùng `child_of`. |
| S7 | `s06_report.js:122-133` | "Xem chi tiết định giá kho" mở `stock.valuation.layer`, model đã bị xoá từ 19.0. |
| S8 | `s06_report.py:281-292` | Action dự phòng của drill-down dòng liệt kê mọi phiếu của kỳ, không lọc mặt hàng, không lọc công ty; lọc trường `datetime` bằng chuỗi ngày nên bỏ qua múi giờ. |
| S9 | `s06_report.py:219-229` | Tài khoản kho đọc `gbqk_valuation_account_id` bằng `getattr` (trường của `fg_gia_binh_quan_ky`, module chưa có trên 20.0), rồi tới `property_stock_valuation_account_id`. Nhóm không khai cả hai thì mặt hàng bị bỏ khỏi sổ mà không báo. Tập tài khoản mặc định viết cứng bốn tiền tố 152, 153, 155, 156. |
| S10 | `s06_wizard.py:35`, `s06_report.js` | Bộ lọc Tài khoản có trên wizard (domain `15%`) nhưng không có trên màn hình. |
| S11 | `s06_pdf.py:60-87` | Vẽ lại toàn bộ tiêu đề trang để thêm dòng tên mặt hàng. Nền tảng 20.0 đã in nhãn nhóm ở đầu trang qua `_format_group_label()`. |

Bảng tổng hợp:

| # | Vị trí | Vấn đề |
|---|---|---|
| T1 | `thtk_report.py:104-119, 336-351` | Khi xem theo kho, mọi cột giá trị bằng số lượng nhân **đơn giá bình quân của toàn bộ lịch sử** (tổng giá trị ròng chia tổng số lượng ròng của mọi phiếu, không giới hạn ngày). Số của một kỳ đã qua đổi mỗi khi có phiếu mới; mặt hàng đang hết hàng có đơn giá 0 nên mọi giá trị bằng 0. Không khớp với bảng toàn công ty, nơi giá trị là tổng `value` của phiếu. |
| T2 | `thtk_report.py:131-165, 297-331` | Theo kho đọc `location_id` / `location_dest_id` của **phiếu**. Hàng nằm ở vị trí con (kệ, ô) được ghi trên **dòng phiếu**; phiếu chỉ mang vị trí cha. Tồn theo vị trí con vì vậy sai hoặc thiếu. |
| T3 | `thtk_report.py:300-304` | Lọc theo nhiều vị trí: phiếu chuyển giữa hai vị trí cùng được chọn được tính là nhập ở tồn đầu kỳ (nhánh `WHEN` đầu thắng), và là cả nhập lẫn xuất trong kỳ. |
| T4 | `thtk_report.py:122-193` | Nhóm theo kho: hai câu SQL cho mỗi vị trí, rồi vòng lặp vị trí × mặt hàng. |
| T5 | `thtk_report.py` theo kho | Không loại hàng ký gửi (dòng phiếu có chủ khác công ty), trong khi bảng toàn công ty loại chúng qua `is_in` / `is_out`. |
| T6 | `thtk_report.js:99-132` | Hai action dùng `view_mode: 'tree,form'`; kiểu view `tree` đổi thành `list` từ 18. Domain ngày dùng chuỗi ngày trên trường `datetime`. Nhãn "Xem chi tiết định giá kho" mở danh sách phiếu kho. |
| T7 | `thtk_report.py:395-457` | Đoạn kiểm tra "có phát sinh" viết ba lần. |
| T8 | `thtk_report.py:19-33` | `_get_columns()` thiếu `'sortable': True`, bản 17 có trên mọi cột trừ ĐVT; bấm tiêu đề cột không sắp xếp được. Sót khi chuyển sang 19, đã vá ở 19.0 ngày 2026-10-17. |

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng tới module

| # | Khác biệt | Chỗ bị ảnh hưởng | Mức |
|---|---|---|---|
| E1 | **`stock.move.value` của phiếu xuất là số âm** (19.0: dương) | Mọi câu SQL có `CASE WHEN sm.is_in THEN sm.value ELSE -sm.value END`: giá trị xuất sẽ được **cộng** vào tồn. Cột giá trị xuất và đơn giá của dòng xuất ra số âm. | chặn, sai số liệu mà không báo lỗi |
| E2 | `stock.move` có `quantity_product_uom` (lưu) | Sửa được C1 mà không phải tự quy đổi đơn vị | dùng |
| E3 | `ir.model.access` → `ir.access` | `security/ir.model.access.csv` | chặn |
| E4 | OWL 3; nền tảng tự hiển thị bảng; FontAwesome bị bỏ | hai file JS, hai file template | chặn |
| E5 | Nền tảng bỏ `_get_pdf_template()`; renderer PDF nhận `env`; tiêu đề trang là danh sách dòng | hai model báo cáo, hai renderer | cần sửa |
| E6 | `property_stock_valuation_account_id` chuyển sang module `account`; `_get_product_accounts()` lấy tài khoản của nhóm rồi tới `company.account_stock_valuation_id` | Cách xác định tài khoản kho (S9) | dùng |
| E7 | `stock.location._should_be_valued()` thêm điều kiện vị trí thuộc công ty đang làm việc | `is_in` / `is_out` do lõi tính; báo cáo chỉ đọc | không phải sửa |

Đã kiểm tra và **không đổi**: `stock.move` có `is_in`, `is_out` (lưu), `quantity`, `date`, `reference`, `description_picking_manual`, `account_move_id`, `picking_id`, `state`, `company_id`, `location_id`, `location_dest_id`; `stock.move.line` có `quantity_product_uom` (lưu), `location_id`, `location_dest_id`, `owner_id`; `stock.picking.type.code`; `product.template.is_storable` (chuyển từ `stock` sang `product`, tên giữ nguyên); menu `stock.menu_warehouse_report`; nhóm `stock.group_stock_user`.

Đã ghi vào vault: `D:\odoo_vault\odoo\migration\v19-to-v20\stock.md` (mới), cùng mục lục của thư mục và `odoo/index.md`.

## 3. Quyết định thiết kế (đề xuất)

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Dấu của giá trị (E1) | Giá trị nhập `abs(sm.value)` khi `is_in`, giá trị xuất `abs(sm.value)` khi `is_out`. | Đúng với quy ước của 20.0, và vẫn đúng với dữ liệu chuyển từ 19.0 sang mà giá trị xuất còn dương. |
| 2 | Số lượng (C1) | `sm.quantity_product_uom`; theo kho thì `sml.quantity_product_uom`. | Trường có lưu, do lõi tính. |
| 3 | Code dùng chung | Một mixin `vn.stock.report.mixin` (`AbstractModel`) cho hai báo cáo: tập mặt hàng theo bộ lọc, bảng nhóm sản phẩm → tài khoản kho, các biểu thức SQL cho số lượng và giá trị có chiều, biểu thức ngày theo múi giờ, kiểm tra "có phát sinh". | Hai báo cáo phải cho cùng số; một chỗ để sửa khi lõi đổi lần nữa. |
| 4 | Truy vấn S06 (S1) | Số câu SQL không phụ thuộc số mặt hàng: (a) tồn đầu kỳ `GROUP BY product_id`; (b) tổng phát sinh `GROUP BY product_id`; (c) dòng phiếu của kỳ, có số tồn luỹ kế tính bằng hàm cửa sổ `SUM() OVER (PARTITION BY product_id ORDER BY …)`. Mặt hàng chỉ được đọc qua ORM sau khi biết nó có số liệu (hoặc khi bật "hiện mặt hàng không có phát sinh"). `flush_model()` trước khi chạy. | 19.0 chạy 2 câu cho mỗi mặt hàng. |
| 5 | Sổ S06 dài | Bật tải dần của nền tảng, nhóm là mặt hàng, như S03b: `_count_lines()` đếm phiếu của kỳ; `_get_group_summaries()` dùng (a) và (b); `_get_group_lines()` dùng (c) cho một mặt hàng với `OFFSET` / `LIMIT`. `_get_lines()` trả cả sổ cho Excel, PDF và sổ dưới ngưỡng. | Đơn vị thương mại có vài nghìn mặt hàng và hàng trăm nghìn phiếu một năm. |
| 6 | Ngày và thứ tự (S2, S3) | Ngày của dòng là `sm.date` đổi sang múi giờ người dùng, cùng múi giờ với `_get_utc_datetime_range()`. Thứ tự: ngày, nhập trước xuất, `sm.date`, `sm.id`. | Thứ tự xác định; tồn giữa ngày không âm giả. |
| 7 | Tài khoản kho (S9, E6) | Hàm `_get_valuation_account_by_category(company)` trong mixin: tài khoản của nhóm sản phẩm, không có thì `company.account_stock_valuation_id`. Tính một lần cho mỗi **nhóm sản phẩm**, không phải mỗi mặt hàng. Đây là điểm để bản 20.0 của `fg_gia_binh_quan_ky` ghi đè; không dùng `getattr`. Mặt hàng không có tài khoản kho vẫn hiện khi bộ lọc Tài khoản trống. | Không phụ thuộc ngầm vào module chưa có; không âm thầm bỏ mặt hàng. |
| 8 | Bộ lọc S06 (S5, S6, S10) | Bỏ `location_ids`. Nhóm sản phẩm dùng `child_of`. Bộ lọc Tài khoản có trên cả wizard và màn hình; wizard điền sẵn các tài khoản 152, 153, 155, 156 của công ty, người dùng xoá được. | S06 là sổ toàn công ty; mặc định theo mẫu sổ nhưng không viết cứng trong truy vấn. |
| 9 | Theo kho (T2–T5) | Đọc `stock.move.line` nối `stock.move`: vị trí thật, `quantity_product_uom`, bỏ dòng có chủ khác công ty. Vị trí được chọn tính cả vị trí con. Lọc theo vị trí (không nhóm): bỏ dòng phiếu có cả hai đầu trong tập. Nhóm theo kho: một câu `UNION ALL` (đầu nhận, đầu giao) `GROUP BY vị trí, mặt hàng` cho tồn đầu kỳ và một câu cho phát sinh. | Số câu SQL không phụ thuộc số vị trí. |
| 10 | Giá trị theo kho (T1) | Đơn giá bình quân **của kỳ**, toàn công ty: (giá trị đầu kỳ + giá trị nhập) / (số lượng đầu kỳ + số lượng nhập); không tính được thì lấy giá trị cuối kỳ chia số lượng cuối kỳ, rồi tới 0. Áp cho cả bốn cột. Mục 8, điểm 3. | Một đơn giá cho bốn cột giữ được đầu kỳ + nhập − xuất = cuối kỳ; số của kỳ đã qua không đổi khi có phiếu mới. |
| 11 | Mã mặt hàng (C3) | In `default_code`; trống thì để trống. Mục 8, điểm 1. | Cột tên là "Mã SP". |
| 12 | Diễn giải S06 (S4) | Máy chủ dựng: nhãn loại nghiệp vụ theo chiều và loại phiếu (Nhập mua, Xuất bán, Khách trả hàng, Trả nhà cung cấp, Nhập sản xuất, Xuất sản xuất, Kiểm kê, Khác), rồi chứng từ gốc của phiếu kho (`origin`) và tên đối tác; ghi chú của phiếu (`description_picking_manual`) nối sau nếu có. Mục 8, điểm 4. | Câu của 19.0 dở dang. |
| 13 | Đổi giá vốn (C4) | Đợt này **không** đưa vào số liệu; readme ghi rõ giới hạn. Mục 8, điểm 2. | Cộng thêm dòng điều chỉnh chỉ đúng với một số phương pháp tính giá; cần quyết định nghiệp vụ trước. |
| 14 | Drill-down (S7, S8, T6) | Máy chủ trả action, JS không tự dựng. S06: tiêu đề mặt hàng mở danh sách phiếu kho đã định giá của mặt hàng trong kỳ; dòng mở form phiếu kho đó, thêm mục mở bút toán khi có `account_move_id`. Bảng tổng hợp: dòng mở danh sách phiếu của mặt hàng trong kỳ, khi theo kho thì mở dòng phiếu của vị trí đó. Domain ngày là `datetime` UTC, có lọc công ty. | Một nơi dựng domain, đúng múi giờ. |
| 15 | PDF (S11, E5) | `S06PDF` bỏ `_draw_page_header()`, giữ `_format_group_label()` và `_should_paginate_by_group()`. Nhãn qua `self.env._()`. | Nền tảng đã in nhãn nhóm. |
| 16 | Nhãn và tên file | Mọi nhãn trong bảng do máy chủ trả (số dư đầu kỳ, cộng, tổng cộng, tên kho). `_get_report_code()`: `_("Form No. S06-DNN")`; bảng tổng hợp giữ mã `THTK`. `_get_export_filename_code()`: `'S06-DNN'`, `'THTK'`. | Quy ước chung. |
| 17 | Kỳ mặc định, hướng giấy, phân quyền | Giữ: tháng hiện tại, A4 ngang, nhóm kế toán và nhóm kho. | Như 19.0. |

## 4. Cấu trúc module sau khi chuyển

```
fg_vn_stock_reports/
├── __init__.py
├── __manifest__.py                 depends: stock_account, fg_vn_accounting_reports
├── readme.md
├── PLAN.md
├── models/
│   ├── stock_report_mixin.py       vn.stock.report.mixin
│   ├── s06_report.py               vn.report.s06
│   ├── s06_pdf.py                  S06PDF
│   ├── thtk_report.py              vn.report.thtk
│   └── thtk_pdf.py                 ThtkPDF
├── wizard/
│   ├── s06_wizard.py, s06_wizard_views.xml
│   └── thtk_wizard.py, thtk_wizard_views.xml
├── views/menu_views.xml            hai client action, menu ở Kho và ở Kế toán
├── security/ir.access.csv          2 wizard × 2 nhóm, thao tác cru
├── i18n/                           .pot và vi.po
├── static/
│   ├── description/index.html
│   ├── src/js/s06_report.js, thtk_report.js
│   └── tests/tours/stock_reports_tour.js
└── tests/
    ├── common.py                   mặt hàng, kho, phiếu nhập xuất mẫu
    ├── test_s06.py
    ├── test_s06_lazy.py
    ├── test_thtk.py
    ├── test_thtk_location.py
    ├── test_exports.py
    ├── test_wizard.py
    └── test_ui.py
```

So với 19.0: bỏ `static/src/xml/`, `security/ir.model.access.csv`; thêm `models/stock_report_mixin.py`, `i18n/`, `tests/`, `static/description/`, `static/tests/`.

## 5. Việc cần làm theo file

### `models/stock_report_mixin.py` (mới)

| Hàm | Nội dung |
|---|---|
| `_get_valuation_account_by_category(company)` | `{id nhóm sản phẩm: id tài khoản kho}` (quyết định 7). |
| `_get_product_domain(options)` | Có theo dõi tồn kho, thuộc công ty hoặc dùng chung, bộ lọc mặt hàng, nhóm (`child_of`), tài khoản (đổi thành điều kiện trên nhóm sản phẩm). |
| `_sql_valued_move_where(options)` | Điều kiện chung của phiếu đã định giá: công ty, `state = 'done'`, `is_in OR is_out`, tập mặt hàng. |
| `_sql_qty_in()`, `_sql_qty_out()`, `_sql_value_in()`, `_sql_value_out()` | Các biểu thức `SQL` của quyết định 1 và 2. |
| `_sql_local_date(column)` | Ngày theo múi giờ người dùng. |
| `_has_activity(values)` | Kiểm tra "có tồn hoặc có phát sinh" (T7). |

### `models/s06_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_get_report_name()`, `_get_report_code()`, `_get_columns()` | Nhãn qua `_()`; thêm `_get_export_filename_code()`. |
| `_get_pdf_template()` | Bỏ. |
| `_get_filter_accounts()`, `_compute_opening_balance()`, `_compute_period_moves()`, `_compute_product_balance()` | Bỏ; thay bằng ba truy vấn của quyết định 4: `_query_openings()`, `_query_totals()`, `_query_moves(product_ids, offset, limit)`. |
| `_get_lines()` | Dựng nhóm từ ba truy vấn. Cấu trúc nhóm và dòng giữ như 19.0 (`opening`, `closing`, `total`, `lines`), thêm `product_code` đúng nghĩa và các nhãn do máy chủ trả. |
| `_count_lines()`, `_get_group_summaries()`, `_get_group_lines()` | **Mới** (quyết định 5). |
| `_get_move_description(row)` | **Mới** (quyết định 12). |
| `_get_drill_down_action()` | Quyết định 14. |
| `_format_xlsx_sheet_name()`, `_format_xlsx_group_label()`, `_group_to_xlsx_rows()` | Dùng mã mặt hàng; nhãn lấy từ dữ liệu. |

### `models/thtk_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_compute_inventory_data()` | Giữ hai câu SQL toàn công ty, đổi biểu thức theo quyết định 1 và 2. |
| `_compute_inventory_data_with_location_filter()`, `_compute_inventory_data_by_location()` | Viết lại trên `stock_move_line` (quyết định 9); giá trị theo quyết định 10, đơn giá lấy từ kết quả toàn công ty của cùng kỳ. |
| `_get_columns()` | Nhãn qua `_()`; khai `'sortable': True` cho mọi cột trừ ĐVT (T8). |
| `_get_lines()`, `_get_lines_grouped_by_location()` | Giữ cấu trúc; dùng `_has_activity()`; thêm nhãn cộng do máy chủ trả. |
| `_get_drill_down_action()` | Quyết định 14. |
| `_write_xlsx_column_headers()`, `_groups_to_xlsx_rows()` | Giữ tiêu đề hai tầng; nhãn qua `_()`; cột đầu là mã mặt hàng. |

### `models/s06_pdf.py`, `models/thtk_pdf.py`

Nhãn cột và nhãn dòng qua `self.env._()` hoặc lấy từ dữ liệu. `S06PDF` theo quyết định 15. Giữ: cột theo hướng giấy, cộng chuyển trang bốn cột nhập xuất và mang số tồn của S06; bảng tổng hợp không cộng chuyển trang.

### `wizard/`

Nhãn tiếng Anh. S06: bỏ `location_ids`; `account_ids` có `check_company=True`, mặc định theo quyết định 8. Bảng tổng hợp: bỏ khai báo lại `show_zero_balance` (đã có ở lớp cơ sở). Hai form thêm `report_lang`; nút theo kiểu của S03b.

### `views/menu_views.xml`, `security/ir.access.csv`

Giữ hai client action và sáu menu; tên tiếng Anh. Bốn dòng phân quyền, định dạng `ir.access`.

### `static/src/js/`

| Phần | Việc cần làm |
|---|---|
| Đầu file, `static template` | Bỏ `@odoo-module` và `static template`. |
| `getFilterDefinitions()` | Domain mặt hàng `is_storable = true` (C2). S06: bỏ vị trí, thêm tài khoản. Nhãn qua `_t()`. |
| `groupsToRows()` | Nhãn dòng lấy từ dữ liệu của máy chủ. S06 thêm dòng "Xem thêm" của nền tảng (`getLoadMoreRow`). |
| `getGroupMenuItems()`, `getLineMenuItems()` | Gọi drill-down của máy chủ; bỏ `viewStockValuationLayer`, `viewStockMove`, `viewStockMoveLine` tự dựng action. Biểu tượng Material Symbols. |

### `tests/`

Kế thừa `TestStockValuationCommon` của `stock_account` (có `_make_in_move`, `_make_out_move`, `_make_return`).

| File | Nội dung kiểm tra |
|---|---|
| `test_s06.py` | Tồn đầu kỳ, từng dòng, số tồn luỹ kế, dòng cộng; **giá trị xuất làm giảm tồn** (E1); mua theo đơn vị khác đơn vị tồn (C1); phiếu lúc 2 giờ sáng giờ Việt Nam nằm đúng ngày và đúng kỳ; nhập trước xuất trong ngày; phiếu chuyển nội bộ, phiếu nháp, hàng ký gửi không có; từng bộ lọc; mặt hàng không có tài khoản kho; công ty khác không lẫn vào; ba phương pháp tính giá. |
| `test_s06_lazy.py` | Trên ngưỡng: nhóm có số tổng hợp, chưa có dòng; các đoạn của `get_group_lines` ghép lại bằng `_get_lines()`; số tồn luỹ kế liền mạch qua các đoạn; số câu SQL không tăng theo số mặt hàng. |
| `test_thtk.py` | Số của bảng toàn công ty bằng dòng số dư và dòng cộng của S06 cùng kỳ; dòng tổng cộng; bộ lọc. |
| `test_thtk_location.py` | Hàng ở vị trí con; chuyển giữa hai kho là xuất của kho này, nhập của kho kia; chuyển trong tập vị trí được chọn không tính; tổng số lượng các kho bằng toàn công ty; đơn giá của kỳ không đổi khi thêm phiếu sau kỳ; hàng ký gửi. |
| `test_exports.py` | Excel S06 mỗi mặt hàng một sheet; tiêu đề hai tầng của bảng tổng hợp. PDF hai hướng giấy, S06 mỗi mặt hàng một trang và có cộng chuyển trang, bản tiếng Việt. |
| `test_wizard.py` | Mặc định, tuỳ chọn gửi đi, người dùng kho và kế toán mở được, người khác bị từ chối. |
| `test_ui.py` | Tour: mở từng báo cáo, tìm kiếm, bộ lọc, mở phiếu kho và quay lại. |

## 6. Thay đổi hành vi so với 19.0

Liệt kê cho người dùng ở readme mục 5. Tóm tắt: số lượng theo đơn vị của mặt hàng; ngày theo múi giờ; nhập trước xuất trong ngày; diễn giải mới; mã mặt hàng thay cho id; S06 bỏ bộ lọc kho, lọc nhóm lấy cả nhóm con, có bộ lọc tài khoản trên màn hình, mặt hàng không có tài khoản kho không còn bị ẩn ngầm; S06 tải dần; bảng tổng hợp theo kho tính trên dòng phiếu và dùng đơn giá của kỳ; các mục mở chi tiết hoạt động.

## 7. Các giai đoạn

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Cài `stock_account` vào `test_fg_vas` (**báo người dùng tắt Odoo trước**). Dữ liệu đo: khoảng 3.000 mặt hàng, 200.000 phiếu đã định giá trong một năm, 20 vị trí kho; kịch bản tạo dữ liệu thêm vào `tools/perf/`. Đo ba truy vấn của S06 và hai truy vấn theo kho bằng `EXPLAIN ANALYZE`. | Có bảng số đo trong kế hoạch này; biết có cần index hay không. |
| 1 | Khung module, mixin, `s06_report.py` kể cả tải dần. | `test_s06`, `test_s06_lazy` chạy qua. |
| 2 | `thtk_report.py`, toàn công ty và theo kho. | `test_thtk`, `test_thtk_location` chạy qua. |
| 3 | Hai renderer PDF, dòng Excel, hai wizard. | `test_exports`, `test_wizard` chạy qua. |
| 4 | Hai file JS, tour. | Tour chạy qua trên sổ nhỏ và sổ S06 tải dần; console không có lỗi hay cảnh báo. |
| 5 | Đo lại trên dữ liệu của giai đoạn 0. `i18n/vi.po`, `static/description/index.html`, dòng trong `README.md` của repo, cập nhật readme mục 5 và trạng thái của kế hoạch. | Số đo ghi vào kế hoạch; hai báo cáo in ra tiếng Việt đầy đủ. |

## 8. Điểm cần xác nhận

| # | Câu hỏi | Đề xuất | Nếu chọn khác |
|---|---|---|---|
| 1 | Sáu chỗ của 19.0 in **id bản ghi** ở nơi là mã mặt hàng. Cố ý (mặt hàng không có mã nội bộ) hay lỗi? | In mã nội bộ, trống thì để trống. | Giữ id: không đổi gì ở phần này; hoặc mã nội bộ, trống thì in id. |
| 2 | Lần đổi giá vốn không có phiếu kho: có đưa vào báo cáo không? | Đợt này không; readme ghi là giới hạn. Phù hợp khi giá xuất do `fg_gia_binh_quan_ky` ghi lại lên phiếu. | Thêm dòng "Điều chỉnh giá trị" từ `product.value`: thêm một truy vấn và test cho từng phương pháp tính giá; với giá chuẩn vẫn không khớp hẳn với Odoo (C4). |
| 3 | Giá trị khi xem bảng tổng hợp theo kho. | Đơn giá bình quân của kỳ (quyết định 10). | (a) Chỉ hiện số lượng khi xem theo kho. (b) Giữ đơn giá toàn lịch sử như 19.0. |
| 4 | Diễn giải của dòng S06. | Loại nghiệp vụ + chứng từ gốc + đối tác (quyết định 12). | Cho biết mẫu câu mong muốn. |
| 5 | Sổ S06 theo mẫu Thông tư 133 có cột "Tài khoản đối ứng" và "Ghi chú"; 19.0 không có. | Giữ bộ cột của 19.0. Phiếu kho của Odoo 20 phần lớn không có bút toán riêng nên không suy ra được tài khoản đối ứng một cách tin cậy. | Thêm cột, để trống khi phiếu không có bút toán. |
| 6 | `fg_gia_binh_quan_ky` có được chuyển sang 20.0 không, trước hay sau module này? | Module này không phụ thuộc nó; để sẵn điểm ghi đè (quyết định 7). | Nếu chuyển trước: kiểm tra lại quy ước dấu của `stock.move.value` trong module đó (bản 19.0 ghi số dương cho phiếu xuất; lõi 20.0 chờ số âm). |

Ghi chú không cần quyết định ngay: bảng tổng hợp không mang số mẫu; mẫu gần nhất của Thông tư 133 là S07-DNN (bảng tổng hợp chi tiết vật liệu, dụng cụ, sản phẩm, hàng hoá), chỉ có cột giá trị và lập theo từng tài khoản. Có thể làm thành một tuỳ chọn của bảng này sau.
