# Kế hoạch chuyển `fg_vn_stock_reports` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_stock_reports` 19.0.1.1.0, commit `50105bb` (2026-10-22). Bản đầu của kế hoạch này (`bf536b4`) viết theo 19.0.1.0.0 tại `64fbf84` (2026-10-11). Từ đó 19.0 có thêm:

- **định giá theo kho** (`models/location_valuation.py`, kho 157 theo phương án B của `fg_gia_binh_quan_ky`): S06 và bảng tổng hợp chọn kho thì giá trị tính theo từng phiếu đi qua ranh giới các kho đã chọn (mục 1.3);
- `'sortable': True` cho các cột của bảng tổng hợp (T8);
- bỏ đường in QWeb (`_get_pdf_template()`, hai template).

Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả hai báo cáo làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme. **Hiện readme lệch với 19.0.1.1.0 ở hai chỗ** (mục 0.2); phải sửa readme sau khi chốt mục 8.

## 0. Trạng thái (2026-10-22)

### 0.1. Bản đang có: 20.0.1.0.0, port giữ logic 19.0

Commit `3f43577`. Làm trước bản viết lại để chạy được kho 157 trên 20.0 (skill `cutoff-test-v20`, dữ liệu `vsg` 06/2026: THTK / S06 cuối kỳ khớp sổ cái, kho HQ nhập = xuất = 48.450.000).

Đã sửa, chỉ ở mức bắt buộc của 20.0:

| Việc | Ở đâu |
|---|---|
| Giá trị phiếu xuất âm (E1): đọc `ABS(sm.value)`, chiều theo `is_in` / `is_out` | mọi câu SQL; `location_valuation.py` |
| Số lượng theo ĐVT của mặt hàng (C1, E2): `sm.quantity_product_uom` | mọi câu SQL; `_SQL_QTY`, `_SQL_UOM_JOIN = ''` |
| `flush_model()` trước SQL | `s06_report.py`, `thtk_report.py`, `location_valuation.py` |
| `pytz` → `zoneinfo` / `datetime.UTC`; `move.uom_id` | `location_valuation.py`, `s06_report.py` |
| `ir.access.csv` (E3) | `security/` |
| OWL 3, bỏ `@odoo-module` / `static template` / hai file template, `list` thay `tree`, domain `is_storable` (C2), biểu tượng Material Symbols (E4) | `static/src/js/` |
| Tiêu đề trang PDF qua `_get_page_header_lines()` (S11, E5) | `s06_pdf.py` |
| Nhãn kho đã chọn trên PDF / Excel: `_build_report_data()` thêm `header['scope_label']`, `_write_xlsx_header()` | `s06_report.py` (nền tảng 20.0 không có `_get_report_scope_label`) |
| Drill-down nhóm của S06 lọc theo khoảng `datetime` UTC | `s06_report.py` |

Giữ nguyên của 19.0: chuỗi tiếng Việt, cấu trúc dữ liệu, cách truy vấn từng mặt hàng, bộ lọc, menu, giấy phép LGPL-3, category `Fanha Addons/…`.

### 0.1b. 20.0.1.1.0: chuẩn hoá theo repo (giai đoạn 1, 2026-10-22)

Làm G1–G10 của mục 9, không đổi số liệu:

- manifest: tên, mô tả tiếng Anh, `Accounting/Accounting`, AGPL-3;
- chuỗi tiếng Anh ở Python, PDF, JS, XML; `i18n/fg_vn_stock_reports.pot`, `i18n/vi.po` dịch lại đúng chữ của 19.0;
- nhãn trong bảng do máy chủ trả: nhóm S06 có `label`, `opening_label`, `closing_label`; bảng tổng hợp có `total_label` ở từng kho và ở tổng;
- `_get_report_code()` qua `_()`, `_get_export_filename_code()`;
- wizard, menu (`views/stock_report_views.xml`), JS theo kiểu S03b; mọi action mở chi tiết dựng ở máy chủ (`params['drill']`), domain ngày là `datetime` UTC;
- docstring, chú thích, `_description` tiếng Anh; `static/description/`.

Kiểm tra trên `vsg_20` (06/2026): so dữ liệu của `get_report_data()` với bản 20.0.1.0.0 ở năm trường hợp (S06 cả công ty, S06 kho HQ, tổng hợp cả công ty, theo kho HQ, nhóm theo kho). Số, ngày, chứng từ, diễn giải, nhãn tiếng Việt **giống hệt**. Khác có chủ đích:

- tên cột S06 viết thường như bảng tổng hợp: "SL nhập", "GT tồn"… (trước: "SL Nhập", "GT Tồn");
- PDF S06: nhãn mặt hàng ở đầu trang và mục lục là "Sản phẩm: id - tên (ĐVT)", như màn hình và Excel (trước: "id - tên  [ĐVT]", tiền tố chỉ ở đầu trang);
- PDF bảng tổng hợp: dòng tổng "TỔNG CỘNG" như màn hình và Excel (trước: "Tổng cộng");
- mở phiếu kho / dòng phiếu từ bảng tổng hợp lọc kỳ theo giờ địa phương (trước: chuỗi ngày trên trường `datetime`, lệch 7 giờ).

Chưa thử trên trình duyệt (menu bộ lọc, các mục mở chi tiết); chưa có test (G11).

### 0.2. Kế hoạch so với 19.0.1.1.0

| Điểm của kế hoạch cũ | 19.0.1.1.0 đã làm | Kế hoạch sửa thành |
|---|---|---|
| Quyết định 8: S06 bỏ `location_ids` (S5) | S06 **dùng** `location_ids`: chọn kho thì sổ là sổ của các kho đó, có dòng chuyển kho nội bộ | Giữ bộ lọc kho của S06 (quyết định 8 mới) |
| Quyết định 9, 10: theo kho đọc `stock.move.line`; giá trị = SL × đơn giá bình quân **của kỳ** (T1) | Giá trị theo từng phiếu qua ranh giới các kho (`vn.stock.location.valuation`); vẫn đọc vị trí trên `stock.move` | Giữ cách định giá của 19.0; câu hỏi dòng phiếu ở mục 8, điểm 7 |
| Mục 8, điểm 3 (giá trị theo kho) | Đã chọn phương án B ở 19.0 (`fg_gia_binh_quan_ky/DE_XUAT_KHO_157_V19.md`) | Đóng |
| Mục 8, điểm 6 (`fg_gia_binh_quan_ky` có lên 20.0 không) | — | Đóng: đã chuyển, ở `D:\openerp\v20\fanha-addons\fg_gia_binh_quan_ky` 20.0.1.0.0, ghi giá trị phiếu xuất âm theo lõi 20.0 |
| Readme mục 3 "Theo kho" (đơn giá bình quân của kỳ), mục 5 "Bộ lọc Kho của sổ S06 bị bỏ" | — | Sửa readme theo quyết định 8, 10 mới |

## 1. Phân tích code nguồn

### 1.1. Thành phần (bản 20.0.1.0.0)

| Thành phần | File | Dòng | Bản viết lại |
|---|---|---|---|
| `vn.report.s06`: chọn mặt hàng theo tài khoản kho, tồn đầu kỳ và phát sinh của từng mặt hàng (toàn công ty hoặc theo kho), số tồn luỹ kế, drill-down, dòng Excel | `models/s06_report.py` | 551 | viết lại phần truy vấn toàn công ty, giữ nhánh theo kho |
| `S06PDF`: cột theo hướng giấy, mỗi mặt hàng một trang, cộng chuyển trang | `models/s06_pdf.py` | 179 | giữ; nhãn qua `self.env._()` |
| `vn.report.thtk`: nhập xuất tồn toàn công ty, có lọc kho, nhóm theo kho; tiêu đề Excel hai tầng | `models/thtk_report.py` | 478 | giữ phần toàn công ty; nhóm theo kho tính một lần cho mọi kho |
| `ThtkPDF` | `models/thtk_pdf.py` | 135 | giữ; nhãn qua `self.env._()` |
| `vn.stock.location.valuation`: nhập xuất tồn theo một tập vị trí, định giá phiếu nội bộ, kho 157 | `models/location_valuation.py` | 410 | giữ thuật toán; chuỗi, docstring tiếng Anh; sửa L1–L4 (mục 1.3) |
| Hai wizard và form | `wizard/*.py`, `wizard/*.xml` | 63 + 65, 61 + 57 | giữ, theo kiểu S03b |
| Client action, menu ở Kho và ở Kế toán | `views/menu_views.xml` | 62 | giữ |
| `S06Report`, `THTKReport` (OWL 3) | `static/src/js/*.js` | 230 + 234 | nhãn qua `_t()`, nhãn bảng từ máy chủ, drill-down ở máy chủ |
| Phân quyền hai wizard cho kế toán và thủ kho | `security/ir.access.csv` | 4 dòng | giữ |
| Hướng dẫn cấu hình kho 157 | `HUONG_DAN_KHO_157.md` | 185 | giữ (tài liệu nghiệp vụ, viết cho 19.0; sửa đường dẫn và số phiên bản khi viết lại) |

Module chưa có test, `i18n/`, `static/description/`.

### 1.2. Lỗi và điểm yếu có sẵn

Cột "20.0.1.0.0" là tình trạng ở bản port. Số dòng ở cột Vị trí là của 19.0 tại `64fbf84`.

Chung cho hai báo cáo:

| # | Vị trí | Vấn đề | 20.0.1.0.0 |
|---|---|---|---|
| C1 | mọi câu SQL | Số lượng lấy `sm.quantity`, là số theo **đơn vị của phiếu**. Mặt hàng mua theo thùng, tồn theo cái thì số lượng sai. | Đã sửa (`quantity_product_uom`) |
| C2 | `s06_report.js:33`, `thtk_report.js:30` | Bộ lọc Mặt hàng trên màn hình dùng domain `type = 'product'`. Giá trị này không còn từ Odoo 18; danh sách chọn luôn trống. | Đã sửa |
| C3 | 6 chỗ ở Python, JS, PDF | Nơi cần mã mặt hàng lại lấy `product_id`, tức số id của bản ghi: tiêu đề nhóm, tên sheet, nhãn PDF của S06; cột "Mã SP" của bảng tổng hợp trên màn hình, Excel và PDF. `default_code` có trong dữ liệu nhưng chỉ dùng để sắp xếp. Lặp lại nhất quán nên có thể là cố ý (mục 8, điểm 1). | Còn, đủ sáu chỗ |
| C4 | Toàn module | Giá trị là tổng `value` của các phiếu. Lần đổi giá vốn (`product.value` không gắn phiếu) không được tính, nên tồn cuối kỳ có thể lệch với định giá của Odoo. Với mặt hàng tính **giá chuẩn**, giá trị nhập trên phiếu lấy theo giá mua còn Odoo định giá tồn theo giá chuẩn, nên hai số vốn đã khác nhau. | Còn (giới hạn đã biết, mục 8, điểm 2). Trên `vsg` 06/2026 không có đổi giá vốn: THTK khớp sổ cái |
| C5 | Toàn module | Chuỗi tiếng Việt viết thẳng, một phần ở JS. `_get_pdf_template()` và hai file template là code chết. Biểu tượng FontAwesome. | Còn chuỗi tiếng Việt; code chết và FontAwesome đã bỏ |

S06:

| # | Vị trí | Vấn đề | 20.0.1.0.0 |
|---|---|---|---|
| S1 | `s06_report.py:209-262` | Nạp **mọi** mặt hàng có theo dõi tồn kho của công ty, rồi với mỗi mặt hàng chạy hai câu SQL và đọc tài khoản của nhóm qua ORM. 5.000 mặt hàng là 10.000 câu SQL, kể cả cho mặt hàng không có phiếu nào. | Còn ở nhánh toàn công ty; nhánh theo kho đọc mọi mặt hàng một lần |
| S2 | `s06_report.py:104` | `DATE_TRUNC('day', sm.date)` cắt ngày theo UTC. Phiếu hoàn tất trước 7 giờ sáng giờ Việt Nam hiện vào ngày hôm trước; kỳ lọc thì theo múi giờ người dùng. | Còn ở nhánh toàn công ty; nhánh theo kho đổi đúng múi giờ |
| S3 | `s06_report.py:129` | Thứ tự trong ngày theo `picking_type_id` rồi `reference`. Số tồn luỹ kế phụ thuộc thứ tự này; không có quy tắc nhập trước xuất sau, nên tồn giữa ngày có thể âm giả. Hai phiếu cùng khoá sắp xếp thì thứ tự không xác định. | Còn ở nhánh toàn công ty; nhánh theo kho theo `sm.date, sm.id` (xác định, chưa nhập trước xuất) |
| S4 | `s06_report.py:151-160` | Diễn giải: phiếu nhập ghi "Nhập hàng theo HĐ " và phiếu xuất ghi "Xuất hàng theo HĐ " không kèm số nào; chỉ phiếu nhập có bút toán mới kèm tham chiếu. | Còn ở nhánh toàn công ty. Nhánh theo kho nối số hoá đơn khi có `stock.picking.invoice_ids` (OCA `stock_picking_invoice_link`), ghi "Vận chuyển nội bộ từ / đến kho …" cho phiếu nội bộ |
| S5 | `s06_wizard.py:26,60`, `s06_report.js:42` | `location_ids` có trên wizard và màn hình, được gửi đi, nhưng báo cáo không đọc. | **Không còn là lỗi**: 19.0.1.1.0 dùng nó (mục 1.3) |
| S6 | `s06_report.py:207` so với `thtk_report.py:65` | Bộ lọc nhóm sản phẩm của S06 dùng `in` (không lấy nhóm con), của bảng tổng hợp dùng `child_of`. | Còn |
| S7 | `s06_report.js:122-133` | "Xem chi tiết định giá kho" mở `stock.valuation.layer`, model đã bị xoá từ 19.0. | Đã sửa ở 19.0.1.1.0: mở danh sách định giá `stock_account.stock_move_view_list_valuation` của phiếu |
| S8 | `s06_report.py:281-292` | Action dự phòng của drill-down dòng liệt kê mọi phiếu của kỳ, không lọc mặt hàng, không lọc công ty; lọc trường `datetime` bằng chuỗi ngày nên bỏ qua múi giờ. | Một phần: dòng mở đúng phiếu; nhóm lọc mặt hàng và `datetime` UTC nhưng chưa lọc công ty, chưa lọc phiếu đã định giá. Ba action "Dịch chuyển kho", "Chi tiết dịch chuyển", "Bút toán" còn dựng ở JS |
| S9 | `s06_report.py:219-229` | Tài khoản kho đọc `gbqk_valuation_account_id` bằng `getattr`, rồi tới `property_stock_valuation_account_id`. Nhóm không khai cả hai thì mặt hàng bị bỏ khỏi sổ mà không báo. Tập tài khoản mặc định viết cứng bốn tiền tố 152, 153, 155, 156. | Còn. `fg_gia_binh_quan_ky` nay có trên 20.0 nên `getattr` lấy được trường |
| S10 | `s06_wizard.py:35`, `s06_report.js` | Bộ lọc Tài khoản có trên wizard (domain `15%`) nhưng không có trên màn hình. | Còn |
| S11 | `s06_pdf.py:60-87` | Vẽ lại toàn bộ tiêu đề trang để thêm dòng tên mặt hàng. | Đã sửa (`_get_page_header_lines()`) |

Bảng tổng hợp:

| # | Vị trí | Vấn đề | 20.0.1.0.0 |
|---|---|---|---|
| T1 | `thtk_report.py:104-119, 336-351` | Khi xem theo kho, mọi cột giá trị bằng số lượng nhân **đơn giá bình quân của toàn bộ lịch sử**. Số của kỳ đã qua đổi mỗi khi có phiếu mới; mặt hàng hết hàng có đơn giá 0. | Đã thay ở 19.0.1.1.0: định giá từng phiếu qua ranh giới kho (mục 1.3) |
| T2 | `thtk_report.py:131-165, 297-331` | Theo kho đọc `location_id` / `location_dest_id` của **phiếu**. Hàng nằm ở vị trí con (kệ, ô) được ghi trên **dòng phiếu**; phiếu chỉ mang vị trí cha. | Còn: `location_valuation` vẫn đọc vị trí của `stock.move`. Lọc theo kho có mở rộng vị trí con nên đúng khi chọn kho cha; nhóm theo kho thì sai ở vị trí con. Mục 8, điểm 7 |
| T3 | `thtk_report.py:300-304` | Lọc theo nhiều vị trí: phiếu chuyển giữa hai vị trí cùng được chọn được tính là nhập ở tồn đầu kỳ và là cả nhập lẫn xuất trong kỳ. | Đã sửa ở 19.0.1.1.0 (điều kiện `(nguồn IN S) <> (đích IN S)`) |
| T4 | `thtk_report.py:122-193` | Nhóm theo kho: hai câu SQL cho mỗi vị trí, rồi vòng lặp vị trí × mặt hàng. | Còn, nặng hơn: mỗi vị trí gọi `_get_location_entries()`, mỗi lần đọc lại toàn bộ lịch sử định giá và dữ liệu GBQK (L1) |
| T5 | `thtk_report.py` theo kho | Không loại hàng ký gửi (dòng phiếu có chủ khác công ty). | Còn (cả S06 theo kho) |
| T6 | `thtk_report.js:99-132` | Hai action dùng `view_mode: 'tree,form'`. Domain ngày dùng chuỗi ngày trên trường `datetime`. Nhãn "Xem chi tiết định giá kho" mở danh sách phiếu kho. | Một phần: đã đổi `list`; domain ngày vẫn là chuỗi, action vẫn dựng ở JS, nhãn "Xem Stock Move" tiếng Anh lẫn tiếng Việt |
| T7 | `thtk_report.py:395-457` | Đoạn kiểm tra "có phát sinh" viết ba lần. | Còn |
| T8 | `thtk_report.py:19-33` | `_get_columns()` thiếu `'sortable': True`. | Đã sửa |

### 1.3. Định giá theo kho (`vn.stock.location.valuation`, từ 19.0.1.1.0)

Dùng khi S06 hoặc bảng tổng hợp có chọn kho, hoặc bảng tổng hợp nhóm theo kho. Để trống kho thì cả hai báo cáo đọc định giá của cả công ty như trước.

- Tập vị trí S: các vị trí được chọn và vị trí con nội bộ (`_expand_locations()`); nhóm theo kho thì mỗi vị trí nội bộ là một S riêng, **không** gộp con.
- Phát sinh: phiếu đã xong có đúng một đầu trong S. Chiều nhập / xuất theo ranh giới S, không theo `is_in` / `is_out` (kho → 157 có cờ GBQK là `is_out` nhưng là nhập của 157).
- Giá trị, theo thứ tự: phiếu có định giá thì `abs(value)`; batch / consumption của GBQK cho phiếu vào / ra kho 157; ghép FIFO các phiếu vào / ra 157 chưa có GBQK; đơn giá bình quân kỳ GBQK chứa ngày phiếu; bình quân định giá tại ngày phiếu; `price_unit`; giá vốn hiện tại.
- Kho 157: vị trí bật cờ `gbqk_exclude_valuation` và `transit_location_ids` của các kỳ GBQK. Không cài `fg_gia_binh_quan_ky` thì không có kho 157 riêng. Đọc GBQK bằng `sudo` và kiểm tra model / trường có mặt, không khai phụ thuộc.

Điểm yếu thấy khi đọc lại trên 20.0:

| # | Vấn đề |
|---|---|
| L1 | `_get_valued_running_avg()` đọc mọi phiếu đã định giá của các mặt hàng từ đầu lịch sử, và dữ liệu GBQK được đọc lại ở mỗi lần gọi `_get_location_entries()`. Bảng tổng hợp nhóm theo kho gọi một lần cho **mỗi vị trí** (T4). |
| L2 | `_get_internal_move_valuer()` tự đọc `self.env.user.tz or 'Asia/Ho_Chi_Minh'` thay cho `_get_user_timezone()` của nền tảng. Cùng kết quả, trừ khi múi giờ khai sai (nền tảng bắt lỗi, ở đây thì lỗi); nên dùng chung một hàm. |
| L3 | Mỗi phát sinh mang khoá `svl_id` luôn `False`, giữ cho khớp JS của 17.0; JS 20.0 không đọc nó. |
| L4 | Docstring, `_description` tiếng Việt. |

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng tới module

| # | Khác biệt | Chỗ bị ảnh hưởng | 20.0.1.0.0 |
|---|---|---|---|
| E1 | **`stock.move.value` của phiếu xuất là số âm** (19.0: dương) | Mọi câu SQL có `CASE WHEN sm.is_in THEN sm.value ELSE -sm.value END`; `location_valuation` | Đã xử lý (`ABS`) |
| E2 | `stock.move` có `quantity_product_uom` (lưu) | C1 | Đã dùng |
| E3 | `ir.model.access` → `ir.access` | `security/` | Đã đổi |
| E4 | OWL 3; nền tảng tự hiển thị bảng; FontAwesome bị bỏ | hai file JS, hai template | Đã đổi |
| E5 | Nền tảng bỏ `_get_pdf_template()`; renderer PDF nhận `env`; tiêu đề trang là danh sách dòng; không còn `_get_report_scope_label()` | hai model, hai renderer | Đã đổi |
| E6 | `property_stock_valuation_account_id` chuyển sang module `account`; `_get_product_accounts()` lấy tài khoản của nhóm rồi tới `company.account_stock_valuation_id` | S9 | Chưa dùng |
| E7 | `stock.location._should_be_valued()` thêm điều kiện vị trí thuộc công ty đang làm việc | `is_in` / `is_out` do lõi tính | Không phải sửa |

Đã kiểm tra và **không đổi**: `stock.move` có `is_in`, `is_out` (lưu), `quantity`, `date`, `reference`, `description_picking_manual`, `account_move_id`, `picking_id`, `state`, `company_id`, `location_id`, `location_dest_id`, `price_unit`, `origin`; `stock.move.line` có `quantity_product_uom` (lưu), `location_id`, `location_dest_id`, `owner_id`; `stock.picking.type.code`; `product.template.is_storable`; menu `stock.menu_warehouse_report`; nhóm `stock.group_stock_user`.

Đã ghi vào vault: `D:\odoo_vault\odoo\migration\v19-to-v20\stock.md`.

## 3. Quyết định thiết kế (đề xuất)

| # | Vấn đề | Đề xuất | Lý do | 20.0.1.0.0 |
|---|---|---|---|---|
| 1 | Dấu của giá trị (E1) | Giá trị nhập `abs(sm.value)` khi `is_in`, giá trị xuất `abs(sm.value)` khi `is_out`. | Đúng với 20.0, vẫn đúng với dữ liệu chuyển từ 19.0 mà giá trị xuất còn dương. | Đã làm |
| 2 | Số lượng (C1) | `sm.quantity_product_uom`; theo dòng phiếu thì `sml.quantity_product_uom`. | Trường có lưu, do lõi tính. | Đã làm (mức phiếu) |
| 3 | Code dùng chung | Phần dùng chung của hai báo cáo vào một mixin `vn.stock.report.mixin` (`AbstractModel`): tập mặt hàng theo bộ lọc, nhóm sản phẩm → tài khoản kho, biểu thức SQL số lượng / giá trị có chiều, ngày theo múi giờ, kiểm tra "có phát sinh". `vn.stock.location.valuation` giữ riêng phần định giá theo kho. | Hai báo cáo phải cho cùng số; một chỗ để sửa khi lõi đổi. | Chưa |
| 4 | Truy vấn S06 toàn công ty (S1) | Số câu SQL không phụ thuộc số mặt hàng: (a) tồn đầu kỳ `GROUP BY product_id`; (b) tổng phát sinh `GROUP BY product_id`; (c) dòng phiếu của kỳ, số tồn luỹ kế bằng `SUM() OVER (PARTITION BY product_id ORDER BY …)`. Mặt hàng chỉ đọc qua ORM khi đã có số liệu (hoặc khi bật "hiện mặt hàng không có phát sinh"). | 19.0 chạy 2 câu cho mỗi mặt hàng. | Chưa |
| 5 | Sổ S06 dài | Tải dần theo mặt hàng như S03b: `_count_lines()`, `_get_group_summaries()` dùng (a) và (b), `_get_group_lines()` dùng (c) với `OFFSET` / `LIMIT`. Chọn kho: không tải dần (số dòng nhỏ, định giá cần cả lịch sử của mặt hàng). | Đơn vị có vài nghìn mặt hàng và hàng trăm nghìn phiếu một năm. | Chưa |
| 6 | Ngày và thứ tự (S2, S3) | Ngày của dòng là `sm.date` đổi sang múi giờ của `_get_user_timezone()`. Thứ tự: ngày, nhập trước xuất, `sm.date`, `sm.id`; như nhau ở hai nhánh. | Thứ tự xác định; tồn giữa ngày không âm giả. | Nhánh theo kho đúng ngày, chưa nhập trước xuất |
| 7 | Tài khoản kho (S9, E6) | Một hàm `_get_valuation_account_by_category(company)` trong mixin: `gbqk_valuation_account_id` nếu trường có mặt (kiểm tra `_fields`, như cách `location_valuation` đọc GBQK), rồi tài khoản định giá của nhóm, rồi `company.account_stock_valuation_id`. Tính một lần cho mỗi **nhóm sản phẩm**. Mặt hàng không có tài khoản vẫn hiện khi bộ lọc Tài khoản trống. | `fg_gia_binh_quan_ky` 20.0 ở repo khác (`fanha-addons`), không phụ thuộc module này; đọc mềm ở một chỗ thay cho `getattr` rải rác. | Còn `getattr` trong vòng lặp |
| 8 | Bộ lọc S06 (S5, S6, S10) | **Giữ** `location_ids` (sổ của các kho được chọn, mục 1.3). Nhóm sản phẩm dùng `child_of`. Bộ lọc Tài khoản có trên cả wizard và màn hình; wizard điền sẵn các tài khoản 152, 153, 155, 156 của công ty, người dùng xoá được. | Kho 157 cần sổ S06 theo kho. | Có `location_ids`; hai điểm còn lại chưa |
| 9 | Theo kho: vị trí và hàng ký gửi (T2, T5) | Mục 8, điểm 7. Đề xuất: số lượng đọc từ `stock.move.line` (vị trí thật, bỏ dòng có chủ khác công ty), giá trị của phiếu chia theo tỷ lệ số lượng của dòng. Nhóm theo kho: một lần `_get_location_entries()` cho mọi vị trí, gộp theo vị trí trong Python (T4, L1). | Số câu SQL không phụ thuộc số vị trí; tồn ở kệ / ô đúng. | Chưa |
| 10 | Giá trị theo kho (T1) | Giữ cách định giá của `vn.stock.location.valuation` (mục 1.3), thay cho đơn giá bình quân của kỳ của bản kế hoạch đầu. | Đã chạy trên dữ liệu thật; khớp TK 157 khi dùng GBQK. | Đã làm (19.0.1.1.0) |
| 11 | Mã mặt hàng (C3) | ~~In `default_code`~~ Giữ id như 19.0 (mục 8, điểm 1, đã chốt). | | Như đã chốt |
| 12 | Diễn giải S06 (S4) | Máy chủ dựng, một hàm cho cả hai nhánh: nhãn loại nghiệp vụ theo chiều và loại phiếu (Nhập mua, Xuất bán, Khách trả hàng, Trả nhà cung cấp, Nhập sản xuất, Xuất sản xuất, Kiểm kê, Chuyển kho từ / đến …, Khác), rồi chứng từ gốc (`origin`) và đối tác; ghi chú của phiếu nối sau nếu có. Mục 8, điểm 4. | Câu của 19.0 dở dang, hai nhánh viết khác nhau. | Chưa |
| 13 | Đổi giá vốn (C4) | Đợt này **không** đưa vào số liệu; readme ghi giới hạn. Mục 8, điểm 2. | | Như đề xuất |
| 14 | Drill-down (S7, S8, T6) | Máy chủ trả mọi action, JS không tự dựng. S06: tiêu đề mở phiếu kho đã định giá của mặt hàng trong kỳ (có lọc công ty; chọn kho thì phiếu qua ranh giới kho); dòng mở danh sách định giá của phiếu, phiếu kho, dòng phiếu, bút toán. Bảng tổng hợp: dòng mở phiếu của mặt hàng trong kỳ, theo kho thì của vị trí đó. Domain ngày là `datetime` UTC. | Một nơi dựng domain, đúng múi giờ. | Một phần (S8, T6) |
| 15 | PDF (S11, E5) | `S06PDF` dùng `_get_page_header_lines()`, giữ `_format_group_label()` và `_should_paginate_by_group()`. Nhãn qua `self.env._()`. | | Đã làm, nhãn còn tiếng Việt |
| 16 | Nhãn và tên file | Mọi nhãn trong bảng do máy chủ trả (số dư đầu kỳ, cộng, tổng cộng, tên kho, nhãn nhóm). `_get_report_code()`: `_("Form No. S06-DNN")`; bảng tổng hợp giữ mã `THTK`. `_get_export_filename_code()`: `'S06-DNN'`, `'THTK'`. | Quy ước chung (nền tảng, NT-4). | Chưa |
| 17 | Kỳ mặc định, hướng giấy, phân quyền | Giữ: tháng hiện tại, A4 ngang, nhóm kế toán và nhóm kho. | Như 19.0. | Như đề xuất |

## 4. Cấu trúc module sau khi viết lại

```
fg_vn_stock_reports/
├── __init__.py
├── __manifest__.py                 depends: stock_account, fg_vn_accounting_reports
├── readme.md
├── PLAN.md
├── HUONG_DAN_KHO_157.md
├── models/
│   ├── stock_report_mixin.py       vn.stock.report.mixin
│   ├── location_valuation.py       vn.stock.location.valuation
│   ├── s06_report.py               vn.report.s06
│   ├── s06_pdf.py                  S06PDF
│   ├── thtk_report.py              vn.report.thtk
│   └── thtk_pdf.py                 ThtkPDF
├── wizard/
│   ├── s06_wizard.py, s06_wizard_views.xml
│   └── thtk_wizard.py, thtk_wizard_views.xml
├── views/stock_report_views.xml    hai client action, menu ở Kho và ở Kế toán
├── security/ir.access.csv          2 wizard × 2 nhóm, thao tác cru
├── i18n/                           fg_vn_stock_reports.pot, vi.po
├── static/
│   ├── description/icon.png, index.html
│   ├── src/js/s06_report.js, thtk_report.js
│   └── tests/tours/stock_reports_tour.js
└── tests/
    ├── common.py                   mặt hàng, kho, phiếu nhập xuất mẫu
    ├── test_s06.py
    ├── test_s06_lazy.py
    ├── test_thtk.py
    ├── test_location.py            định giá theo kho, kho 157 không GBQK
    ├── test_exports.py
    ├── test_wizard.py
    └── test_ui.py
```

So với 20.0.1.0.0: thêm `models/stock_report_mixin.py`, `i18n/`, `tests/`, `static/description/`, `static/tests/`; `views/menu_views.xml` đổi tên theo kiểu `<báo cáo>_views.xml` của các module khác.

## 5. Việc cần làm theo file

### `models/stock_report_mixin.py` (mới)

| Hàm | Nội dung |
|---|---|
| `_get_valuation_account_by_category(company)` | `{id nhóm sản phẩm: id tài khoản kho}` (quyết định 7). |
| `_get_product_domain(options)` | Có theo dõi tồn kho, thuộc công ty hoặc dùng chung, bộ lọc mặt hàng, nhóm (`child_of`), tài khoản (đổi thành điều kiện trên nhóm sản phẩm). |
| `_sql_valued_move_where(options)` | Điều kiện chung của phiếu đã định giá: công ty, `state = 'done'`, `is_in OR is_out`, tập mặt hàng. |
| `_sql_qty_in()`, `_sql_qty_out()`, `_sql_value_in()`, `_sql_value_out()` | Biểu thức `SQL` của quyết định 1 và 2. |
| `_sql_local_date(column)` | Ngày theo múi giờ của báo cáo. |
| `_has_activity(values)` | "Có tồn hoặc có phát sinh" (T7). |
| `_get_move_description(row)` | Diễn giải (quyết định 12), dùng cho cả nhánh theo kho. |

### `models/location_valuation.py`

Giữ thuật toán. Chuỗi, docstring, `_description` tiếng Anh (L4); múi giờ lấy như nền tảng (L2); bỏ `svl_id` (L3); đọc lịch sử định giá và GBQK một lần cho mọi vị trí (L1, quyết định 9). Nếu chốt mục 8, điểm 7: đọc `stock.move.line`.

### `models/s06_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_get_report_name()`, `_get_report_code()`, `_get_columns()` | Nhãn qua `_()`; thêm `_get_export_filename_code()`. |
| `_get_filter_accounts()`, `_compute_opening_balance()`, `_compute_period_moves()`, `_compute_product_balance()` | Bỏ; thay bằng ba truy vấn của quyết định 4: `_query_openings()`, `_query_totals()`, `_query_moves(product_ids, offset, limit)`. |
| `_compute_product_balance_by_location()`, `_get_invoice_refs()` | Giữ cho nhánh theo kho; diễn giải qua `_get_move_description()`. |
| `_get_report_scope_label()`, `_build_report_data()`, `_write_xlsx_header()` | Giữ; nhãn qua `_()`. |
| `_get_lines()` | Dựng nhóm từ ba truy vấn hoặc từ `location_valuation`. Cấu trúc nhóm và dòng giữ (`opening`, `closing`, `total`, `lines`), thêm `label`, `opening_label`, `closing_label` và `product_code` đúng nghĩa. |
| `_count_lines()`, `_get_group_summaries()`, `_get_group_lines()` | **Mới** (quyết định 5). |
| `_get_drill_down_action()`, `_get_line_valuation_action()` | Quyết định 14. |
| `_format_xlsx_sheet_name()`, `_format_xlsx_group_label()`, `_group_to_xlsx_rows()` | Mã mặt hàng; nhãn lấy từ dữ liệu. |

### `models/thtk_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_compute_inventory_data()` | Giữ hai câu SQL toàn công ty; biểu thức từ mixin. |
| `_compute_inventory_data_with_location_filter()`, `_compute_inventory_data_by_location()` | Một lần `location_valuation` cho mọi vị trí (quyết định 9). |
| `_get_columns()` | Nhãn qua `_()`. |
| `_get_lines()`, `_get_lines_grouped_by_location()` | Dùng `_has_activity()`; nhãn cộng, tổng cộng do máy chủ trả. |
| `_get_drill_down_action()` | Quyết định 14. |
| `_write_xlsx_column_headers()`, `_groups_to_xlsx_rows()` | Tiêu đề hai tầng qua `_()`; cột đầu là mã mặt hàng. |

### `models/s06_pdf.py`, `models/thtk_pdf.py`

Nhãn cột qua `self.env._()`, nhãn dòng lấy từ dữ liệu. Giữ: cột theo hướng giấy, cộng chuyển trang bốn cột nhập xuất và mang số tồn của S06; bảng tổng hợp không cộng chuyển trang.

### `wizard/`

Nhãn tiếng Anh, form theo kiểu S03b (nhóm Period / Filters / Layout, nút View, Excel, PDF, Discard). S06: `account_ids` có `check_company=True`, mặc định theo quyết định 8. Bảng tổng hợp: bỏ khai báo lại `show_zero_balance` (đã có ở lớp cơ sở).

### `views/`, `security/ir.access.csv`

Giữ hai client action và sáu menu; tên tiếng Anh. Bốn dòng phân quyền.

### `static/src/js/`

| Phần | Việc cần làm |
|---|---|
| `getFilterDefinitions()` | Nhãn qua `_t()`. S06 thêm bộ lọc tài khoản. |
| `groupsToRows()` | Nhãn dòng lấy từ dữ liệu của máy chủ. S06 thêm dòng "Xem thêm" (`getLoadMoreRow`). |
| `getGroupMenuItems()`, `getLineMenuItems()` | Chỉ gọi drill-down của máy chủ; bỏ `viewStockMove`, `viewStockMoveLine(s)`, `viewAccountMove`. |
| Lớp | `export class`, `static displayName`, như S03b. |

### `tests/`

Kế thừa `TestStockValuationCommon` của `stock_account`.

| File | Nội dung kiểm tra |
|---|---|
| `test_s06.py` | Tồn đầu kỳ, từng dòng, số tồn luỹ kế, dòng cộng; giá trị xuất làm giảm tồn (E1); mua theo đơn vị khác đơn vị tồn (C1); phiếu lúc 2 giờ sáng giờ Việt Nam đúng ngày và đúng kỳ; nhập trước xuất trong ngày; phiếu nội bộ, phiếu nháp, hàng ký gửi không có; từng bộ lọc; mặt hàng không có tài khoản kho; công ty khác không lẫn vào; ba phương pháp tính giá. |
| `test_s06_lazy.py` | Trên ngưỡng: nhóm có số tổng hợp, chưa có dòng; các đoạn của `get_group_lines` ghép lại bằng `_get_lines()`; số tồn luỹ kế liền mạch; số câu SQL không tăng theo số mặt hàng. |
| `test_thtk.py` | Bảng toàn công ty bằng dòng số dư và dòng cộng của S06 cùng kỳ; tổng cộng; bộ lọc. |
| `test_location.py` | Chuyển giữa hai kho là xuất của kho này, nhập của kho kia, cùng giá trị; chuyển trong tập được chọn không tính; tổng các kho bằng toàn công ty; kho 157 không GBQK (ghép FIFO); S06 theo kho bằng dòng của bảng tổng hợp theo kho; vị trí con, hàng ký gửi nếu chốt mục 8, điểm 7. |
| `test_exports.py` | Excel S06 mỗi mặt hàng một sheet; tiêu đề hai tầng của bảng tổng hợp; nhãn kho đã chọn. PDF hai hướng giấy, S06 mỗi mặt hàng một trang và có cộng chuyển trang, bản tiếng Việt. |
| `test_wizard.py` | Mặc định, tuỳ chọn gửi đi, người dùng kho và kế toán mở được, người khác bị từ chối. |
| `test_ui.py` | Tour: mở từng báo cáo, tìm kiếm, bộ lọc, mở phiếu kho và quay lại. |

Kho 157 có GBQK đã kiểm tra bằng skill `cutoff-test-v20` trên dữ liệu thật; test của module không phụ thuộc `fg_gia_binh_quan_ky`.

## 6. Thay đổi hành vi so với 19.0.1.1.0

Liệt kê cho người dùng ở readme mục 5. Tóm tắt: ngày theo múi giờ; nhập trước xuất trong ngày; diễn giải mới; mã mặt hàng thay cho id; S06 lọc nhóm lấy cả nhóm con, có bộ lọc tài khoản trên màn hình, mặt hàng không có tài khoản kho không còn bị ẩn ngầm; S06 tải dần; các mục mở chi tiết lọc đúng công ty và múi giờ; ngôn ngữ gốc tiếng Anh. Nếu chốt mục 8, điểm 7: theo kho tính trên dòng phiếu và bỏ hàng ký gửi.

## 7. Các giai đoạn

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Port giữ logic 19.0. | **Xong** (20.0.1.0.0, `3f43577`); kiểm tra bằng `cutoff-test-v20` trên `vsg` |
| 1 | Chuẩn hoá theo repo (mục 9): manifest, chuỗi tiếng Anh + `i18n/vi.po`, nhãn bảng do máy chủ trả, wizard / menu / JS theo S03b, drill-down ở máy chủ, `static/description/`. Không đổi số liệu. | **Xong** (20.0.1.1.0, mục 0.1b); còn thử trên trình duyệt |
| 2 | Đo: cài vào `test_fg_vas` (**báo người dùng tắt Odoo trước**), khoảng 3.000 mặt hàng, 200.000 phiếu đã định giá một năm, 20 vị trí kho; kịch bản ở `tools/perf/`. `EXPLAIN ANALYZE` ba truy vấn của S06 và `location_valuation`. | Có bảng số đo; biết có cần index không |
| 3 | Mixin, `s06_report.py` toàn công ty kể cả tải dần (quyết định 3–7, 11, 12). | `test_s06`, `test_s06_lazy` chạy qua |
| 4 | `thtk_report.py`, `location_valuation.py` (quyết định 9). | `test_thtk`, `test_location` chạy qua; `cutoff-test-v20` vẫn khớp |
| 5 | Exports, wizard, tour. | `test_exports`, `test_wizard`, `test_ui` chạy qua |
| 6 | Đo lại; readme mục 5, dòng trong `README.md` của repo, trạng thái kế hoạch. | Số đo ghi vào kế hoạch |

## 8. Điểm cần xác nhận

| # | Câu hỏi | Đề xuất | Nếu chọn khác |
|---|---|---|---|
| 1 | ~~Sáu chỗ in **id bản ghi** ở nơi là mã mặt hàng~~ | **Đã chốt** (2026-10-22): giữ id như 19.0. Quyết định 11 bỏ; C3 không phải lỗi. | |
| 2 | Lần đổi giá vốn không có phiếu kho: có đưa vào báo cáo không? | Đợt này không; readme ghi là giới hạn. Phù hợp khi giá xuất do `fg_gia_binh_quan_ky` ghi lại lên phiếu. | Thêm dòng "Điều chỉnh giá trị" từ `product.value`; với giá chuẩn vẫn không khớp hẳn (C4). |
| 3 | ~~Giá trị khi xem theo kho~~ | **Đã chốt** ở 19.0: định giá từng phiếu qua ranh giới kho (mục 1.3). | |
| 4 | Diễn giải của dòng S06. | Loại nghiệp vụ + chứng từ gốc + đối tác, một hàm cho cả hai nhánh (quyết định 12). | Giữ câu của 19.0 ("Nhập hàng theo HĐ …"); hoặc cho biết mẫu câu. |
| 5 | Sổ S06 theo mẫu Thông tư 133 có cột "Tài khoản đối ứng" và "Ghi chú"; 19.0 không có. | Giữ bộ cột của 19.0. | Thêm cột, để trống khi phiếu không có bút toán. |
| 6 | ~~`fg_gia_binh_quan_ky` có lên 20.0 không~~ | **Đã chuyển** trước module này (`v20/fanha-addons`, 20.0.1.0.0). | |
| 7 | Theo kho: đọc vị trí trên **dòng phiếu** (kệ, ô) và bỏ hàng ký gửi (T2, T5)? | Có: số lượng theo dòng phiếu, giá trị phiếu chia theo tỷ lệ số lượng. | Giữ mức phiếu như 19.0: đúng khi chọn kho cha, sai khi nhóm theo kho có vị trí con. |
| 8 | ~~Giấy phép và category~~ | **Đã chốt** (2026-10-22): AGPL-3, `Accounting/Accounting`. | |

Ghi chú: bảng tổng hợp không mang số mẫu; mẫu gần nhất của Thông tư 133 là S07-DNN (chỉ có cột giá trị, lập theo từng tài khoản). Có thể làm thành một tuỳ chọn sau.

## 9. Chênh lệch với quy ước của repo (giai đoạn 1)

Quy ước: `fg_vn_accounting_reports/doc/DEVELOPER.md` mục 1, 4, 5 và cách làm của `fg_vn_report_s03b`.

| # | Hiện tại (20.0.1.0.0) | Quy ước | File mới? |
|---|---|---|---|
| G1 | Manifest: tên "VN Stock Reports - Báo cáo kho Việt Nam", category `Fanha Addons/Inventory/Reporting`, LGPL-3, description tiếng Việt, không có `web.assets_tests` | Tên tiếng Anh dạng "Vietnam - …", `Accounting/Accounting`, AGPL-3 (mục 8, điểm 8), description tiếng Anh dịch ở `vi.po` | không |
| G2 | Chuỗi tiếng Việt viết thẳng ở Python, PDF, JS, XML; một số chỗ qua `_()` nhưng msgid tiếng Việt | Chuỗi tiếng Anh; `_()`, `self.env._()`, `_t()`; dịch ở `i18n/vi.po` | **có**: `i18n/fg_vn_stock_reports.pot`, `i18n/vi.po` |
| G3 | Nhãn trong bảng dựng ở JS ("Số dư đầu kỳ", "Cộng phát sinh / Số dư cuối kỳ", "TỔNG CỘNG", "Cộng <kho>", "Sản phẩm: …") và dựng lại ở Excel, PDF | Máy chủ trả nhãn trong dữ liệu (`label`, `opening_label`, `closing_label`, `total_label`); JS, Excel, PDF chỉ đọc | không |
| G4 | `_get_report_code()` "Mẫu số S06-DNN"; không có `_get_export_filename_code()` | `_("Form No. S06-DNN")`; `'S06-DNN'`, `'THTK'` | không |
| G5 | Wizard: nhóm "KỲ BÁO CÁO / TÙY CHỌN / BỘ LỌC / IN PDF", nút màu xanh / đỏ, `string` ghi đè trên `date_from` | Như S03b: Period / Filters / Layout; nút View (`btn-primary`, hotkey `q`), Excel (`icon="table"`), PDF (`icon="picture_as_pdf"`), Discard | không |
| G6 | `views/menu_views.xml`, chú thích tiếng Việt, tên menu tiếng Việt | Tên tiếng Anh; đặt tên file theo nội dung | đổi tên file |
| G7 | JS: `class` không export, nháy đơn, không `displayName`, action dựng ở JS (S8, T6) | `export class`, `static displayName = _t(…)`, drill-down qua `handleLineDrillDown` / `handleGroupDrillDown` | không |
| G8 | Docstring và chú thích tiếng Việt, kèm ghi chú "v19: …" | Tiếng Anh, chỉ giữ chú thích giải thích lý do | không |
| G9 | `_description` tiếng Việt (`vn.report.thtk`, `vn.stock.location.valuation`) | Tiếng Anh | không |
| G10 | Không có `static/description/` | `icon.png`, `index.html` (tiếng Việt, như các module khác) | **có** |
| G11 | Không có test | `tests/` và tour (mục 5) | **có**; làm ở giai đoạn 3–5 |
| G12 | Readme mô tả bản viết lại, lệch với 19.0.1.1.0 (mục 0.2); `README.md` của repo chưa có dòng của module | Readme đúng với bản đang có; thêm dòng vào bảng của repo khi xong | không |
