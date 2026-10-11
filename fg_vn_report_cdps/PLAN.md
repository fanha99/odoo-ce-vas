# Kế hoạch chuyển `fg_vn_report_cdps` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_report_cdps` (19.0.1.0.0, commit `64fbf84` ngày 2026-10-11).
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả báo cáo làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **đã xong cả sáu giai đoạn (2026-10-11).** 72 test chạy qua trên Odoo 20.0, gồm một tour trình duyệt 50 bước (wizard, ngôn ngữ, phân cấp, tìm kiếm, bộ lọc, so sánh, cấp tài khoản, kỳ, drill-down và quay lại, tải lại trang).

Khác với kế hoạch, phát sinh khi code:

| Điểm | Kế hoạch | Thực tế | Lý do |
|---|---|---|---|
| Tổng cộng | Loại tài khoản trung chuyển đang ẩn khi nó hết số dư | Tổng cộng là tổng số riêng của mọi tài khoản không bị loại khỏi báo cáo. Tài khoản bị loại là tài khoản ngoài bảng hoặc tài khoản được ẩn mà hết số dư đầu và cuối kỳ. | Cùng kết quả với kế hoạch cho tài khoản trung chuyển, và là đúng cách 19.0 xử lý tài khoản ngoài bảng. Một tài khoản hết số dư có phát sinh Nợ bằng Có, nên loại nó không làm lệch tổng. |
| `account_level` | JS xoá khỏi `options` trước khi gửi | JS giữ trong `options`; máy chủ không đọc | Tour phát hiện cấp tài khoản bị mất sau khi quay lại từ drill-down, vì trạng thái được khôi phục từ `options` đã lưu. Bản 19.0 có cùng lỗi. |
| Phần trăm chênh lệch khi kỳ so sánh bằng 0 | Như 19.0: luôn `+100%` | `+100%` hoặc `-100%` theo dấu của chênh lệch | 19.0 hiện `+100%` cạnh một chênh lệch âm. |
| Mở rộng `get_report_data()` | Ghi đè `get_report_data()` | Ghi đè `_build_report_data()` của nền tảng | Nhãn cột so sánh phải theo ngôn ngữ báo cáo. |
| Tài khoản đã lưu trữ | Không nêu | Giữ như 19.0: tài khoản đã lưu trữ không có trong báo cáo, kể cả khi còn phát sinh | Xem mục 9. |
| Đọc số liệu | SQL như 19.0 | Thêm `flush_model()` cho `account.move.line` và `account.account` trước khi chạy SQL | Thay đổi chưa ghi xuống database không được SQL thấy; test phát hiện. |

Module này được chuyển song song với `fg_vn_accounting_reports` và là báo cáo dùng để kiểm thử nền tảng trên số liệu thật. Các thay đổi của nền tảng (OWL 3, `ir.access`, phân quyền, chuỗi tiếng Anh) mô tả ở `fg_vn_accounting_reports/PLAN.md`; kế hoạch này chỉ ghi phần riêng của CDPS.

## 1. Phân tích code nguồn

### 1.1. Thành phần

| Thành phần | File | Dòng | Sang 20.0 |
|---|---|---|---|
| `vn.report.cdps`: tính số dư, tách 131/331 theo đối tác, kỳ so sánh, cây phân cấp, dòng Excel, xuất XML, drill-down | `models/cdps_report.py` | 884 | giữ, viết lại phần cây |
| `CDPSPdf`: cột và dòng của bản PDF | `models/cdps_pdf.py` | 122 | giữ |
| `vn.report.cdps.wizard`: tham số, xuất XML từ wizard | `wizard/cdps_wizard.py` | 159 | giữ, bỏ phần XML trùng |
| Form wizard, action | `wizard/cdps_wizard_views.xml` | 59 | giữ |
| Client action, menu | `views/cdps_report_views.xml` | 17 | giữ |
| `CDPSReport` (OWL): bộ lọc, dựng dòng, mở/thu gọn theo cây, xuất XML | `static/src/js/cdps_report.js` | 298 | sửa theo OWL 3 |
| Template gọi `DataTable` | `static/src/xml/cdps_report.xml` | 11 | bỏ |
| SCSS dòng cấp gốc | `static/src/scss/cdps_report.scss` | 20 | chép |
| Phân quyền wizard | `security/ir.model.access.csv` | 1 dòng | đổi sang `ir.access.csv` |
| Template QWeb in PDF cũ | `report/cdps_report_template.xml` | 101 | **bỏ** (đường QWeb đã bỏ ở nền tảng) |
| Ghi chú kỹ thuật | `NOTES.md` | 131 | gộp vào kế hoạch này |

Phụ thuộc: `fg_vn_accounting_reports` và `fg_vn_transfer_account`. Module thứ hai được chuyển trước theo `fg_vn_transfer_account/PLAN.md` (đã chốt).

### 1.2. Lỗi và điểm yếu có sẵn

| # | Vị trí | Vấn đề |
|---|---|---|
| C1 | `cdps_report.py:174-177`, `:579-581` | Tên tài khoản và tên nhóm lấy thẳng cột JSONB bằng SQL rồi chọn **giá trị đầu tiên** của dict. Người dùng tiếng Việt có thể nhận tên tiếng Anh, tuỳ thứ tự khoá. |
| C2 | `cdps_report.js:95` và `cdps_report.py:353` | `_buildOptions` xoá `account_level` trước khi gửi lên máy chủ; việc lọc theo cấp chỉ làm ở trình duyệt. File Excel, PDF xuất ra không theo cấp đang chọn. Nhánh lọc theo cấp ở Python không bao giờ chạy. |
| C3 | `cdps_report.js:164-175` | Ở chế độ không phân cấp, chọn cấp 1 chỉ ẩn các tài khoản mã dài hơn 3 ký tự, không cộng số của chúng lên đâu cả. Tổng các dòng đang hiện không bằng dòng Tổng cộng. |
| C4 | `cdps_wizard.py:66-124` và `cdps_report.py:659-756` | Hai bản xuất XML khác nhau. Bản ở wizard lấy dòng từ `_get_lines` (đã lọc theo tuỳ chọn hiện số 0, gồm cả tài khoản trung chuyển) rồi bù tài khoản thiếu; bản ở báo cáo tính lại từ đầu và loại tài khoản trung chuyển không còn dư. `tongCong` của hai bản có thể khác nhau. Bản ở wizard không cộng số cho nhóm tài khoản. |
| C5 | `cdps_report.py:758-779`, `cdps_wizard.py:113-119` | Mỗi lần xuất XML tạo một `ir.attachment` không gắn bản ghi nào và không bao giờ bị xoá. |
| C6 | `cdps_report.py:824` | `_groups_to_xlsx_rows` lấy tài khoản trung chuyển theo `self.env.company` thay vì công ty của báo cáo. Hàm này còn lọc lại những gì `_get_lines` đã lọc. |
| C7 | `cdps_report.py:79-94` | Kỳ so sánh "tháng trước" trừ một tháng trên cả hai đầu: kỳ 01/02–28/02 cho ra 01/01–28/01, thiếu ba ngày. "Quý trước" bị tương tự. "Năm trước" và "Cùng kỳ năm trước" cho kết quả giống hệt nhau. |
| C8 | `cdps_report.py:195-219` | Nhánh phân biệt tài khoản bản chất Nợ và bản chất Có cho ra cùng một kết quả ở cả hai nhánh (đều là `max(Nợ − Có, 0)` và `max(Có − Nợ, 0)`). Danh sách loại tài khoản đi kèm là code thừa. |
| C9 | `cdps_report.py:49`, `report/` | `_get_pdf_template()` và template QWeb là code chết. |
| C10 | `cdps_report.py:448-450` | Ba khoá `opening`, `closing`, `total` với `quantity`, `qty_in`… là phần thừa chép từ báo cáo kho. |
| C11 | `cdps_report.js:273` | `catch` nuốt mọi lỗi của xuất XML, kể cả lỗi phân quyền, và chỉ báo "Lỗi khi xuất XML". |
| C12 | Toàn module | Chuỗi tiếng Việt viết thẳng. Không có test. |
| C13 | `cdps_report.py:411` | Khi cờ ẩn tài khoản trung chuyển bật, tài khoản này bị loại khỏi Tổng cộng **kể cả khi nó còn số dư và đang được hiển thị**. Lúc đó Tổng Nợ và Tổng Có lệch nhau đúng bằng số dư của nó. Bản xuất XML thì chỉ loại khi hết số dư. |

Điểm giữ nguyên có chủ đích: số dư đầu kỳ là luỹ kế toàn bộ phát sinh trước kỳ, không đặt lại theo năm tài chính cho tài khoản doanh thu, chi phí (đơn vị có bút toán kết chuyển cuối năm); tách Nợ/Có theo đối tác chỉ áp dụng cho tài khoản có mã bắt đầu bằng 131 và 331; tài khoản ngoài bảng nhận diện theo mã bắt đầu bằng 0.

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng riêng tới CDPS

| # | Khác biệt | Chỗ bị ảnh hưởng | Mức | Vault |
|---|---|---|---|---|
| D1 | Model `account.group` bị xoá. `account.account` có `_parent_store` với `parent_id`, `parent_path`, `parent_ids`. Tài khoản cha là tài khoản thật, có thể có phát sinh riêng. `l10n_vn` bỏ `account.group-vn.csv`, thêm cột `parent_id` cho tài khoản (228 trên 301 tài khoản có cha). | `_build_hierarchy_lines()` và phần cộng nhóm của `export_to_xml()` gọi `self.env['account.group']` | **chặn** | `account.md` §3 |
| D2 | `ir.model.access` → `ir.access`. | `security/ir.model.access.csv` | chặn | `security.md` |
| D3 | OWL 3. | `cdps_report.js`, `cdps_report.xml` | chặn | `frontend-owl.md` |
| D4 | Đường in QWeb bị bỏ ở nền tảng; QWeb máy chủ bỏ `t-esc`. | `report/cdps_report_template.xml` | chỉ ảnh hưởng code bị bỏ | `reports-qweb.md` |

Đã kiểm tra và **không đổi**: bảng `account_account_res_company_rel`; `account.account` vẫn có `active`, `name` (dịch được, lưu JSONB), `account_type`, `code_store` (JSONB theo công ty gốc); `res.company.root_id` và `transfer_account_id`; `account.move.line` vẫn có `balance`, `debit`, `credit`, `date`, `parent_state`, `partner_id`, `company_id`; `l10n_vn` vẫn đặt tài khoản trung chuyển là 113.

Hệ thống tài khoản `l10n_vn` 20.0 không có tài khoản nào mã bắt đầu bằng 0. Quy tắc tài khoản ngoài bảng chỉ có tác dụng với đơn vị tự thêm các tài khoản đó.

### 2.1. Tài khoản ngoài bảng và tài khoản chờ trong Odoo 20

Đọc từ `account/models/account_account.py`, `account_move_line.py`, `account_payment.py`, `chart_template.py` và `l10n_vn` của 20.0.

**Tài khoản ngoài bảng của Odoo** là tài khoản có `account_type = 'off_balance'` (nhóm nội bộ `off`). Odoo áp các ràng buộc sau:

| Ràng buộc | Nơi kiểm tra |
|---|---|
| Không được bật đối soát, không được gắn thuế | `account.account._constrains_reconcile` |
| Bút toán có một dòng ngoài bảng thì **mọi dòng** của bút toán phải là tài khoản ngoài bảng | `account.move.line._check_off_balance` |
| Dòng ngoài bảng không được có thuế, không được đối soát | cùng hàm |
| Không chọn được làm tài khoản của sản phẩm, của thuế, của mẫu đối soát | domain trên các trường đó |

Bút toán vẫn phải cân Nợ = Có như mọi bút toán. Vì vậy trong Odoo không ghi đơn được: muốn ghi một tài khoản ngoài bảng phải có một tài khoản ngoài bảng khác làm đối ứng. Hệ quả cho CDPS: cộng tài khoản ngoài bảng vào Tổng cộng không làm lệch Tổng Nợ và Tổng Có. Câu "ghi đơn nên Tổng Nợ khác Tổng Có" trong `NOTES.md` của 19.0 không đúng với cách Odoo hoạt động; chỗ lệch thật là C13.

Hệ thống tài khoản `l10n_vn` 20.0 không có tài khoản nào loại `off_balance` và không có tài khoản nào mã bắt đầu bằng 0. Đơn vị muốn dùng tài khoản ngoài bảng phải tự tạo.

**Tài khoản dùng khi thanh toán hoặc chuyển tiền chưa đối soát** không phải tài khoản ngoài bảng. Chúng là tài khoản trong bảng, loại `asset_current`, cho phép đối soát:

| Tài khoản | Khai báo ở đâu | Dùng khi nào | `l10n_vn` 20.0 |
|---|---|---|---|
| Outstanding Receipts / Outstanding Payments (tài khoản chờ của thanh toán) | `payment_account_id` trên từng phương thức thanh toán của sổ nhật ký; chart template tạo sẵn hai tài khoản | Phiếu thu, phiếu chi đã ghi sổ nhưng chưa khớp với dòng sao kê ngân hàng. Khi khớp sao kê, số ở tài khoản này được đối soát và chuyển sang tài khoản ngân hàng. | 1131, 1132 (con của 113) |
| Tài khoản trung chuyển (`res.company.transfer_account_id`) | Thiết lập kế toán của công ty | Chuyển tiền giữa hai tài khoản tiền. Cũng là tài khoản dự phòng khi thanh toán không tìm thấy tài khoản chờ (`account.payment._get_outstanding_account`). | 113 |
| Tài khoản tạm của sổ nhật ký (`account_journal_suspense_account_id`) | Công ty, từng sổ nhật ký ngân hàng | Dòng sao kê ngân hàng đã nhập nhưng chưa xác định đối ứng. | 1121 (con của 112) |

Phương thức thanh toán không khai `payment_account_id` thì thanh toán không sinh bút toán (`outstanding_account_id` rỗng); đã ghi ở vault `discoveries/v19/payment-architecture.md`.

Tính chất chung của ba loại: là tài sản ngắn hạn, số dư của chúng là tiền thật đang trên đường đi, phải nằm trong bảng cân đối; về 0 khi nghiệp vụ hoàn tất. `NOTES.md` của 19.0 gọi các tài khoản "02, 03" là tài khoản ngoài bảng, nhưng theo cách Odoo phân loại thì chúng là tài khoản chờ loại này, được đặt mã bắt đầu bằng 0 để tách khỏi hệ thống tài khoản của chế độ.

**Ảnh hưởng của từng cách nhận diện tài khoản ngoài bảng trong CDPS:**

| Cách | Database nâng cấp từ 19.0 (có tài khoản chờ mã 0x) | Database mới theo `l10n_vn` 20.0 (tài khoản chờ là 1131, 1132) | Tài khoản loại `off_balance` tự tạo |
|---|---|---|---|
| Chỉ theo mã bắt đầu bằng 0 (như 19.0) | Như cũ: ẩn khi hết số dư, nền cam | Tài khoản chờ hiện như tài khoản thường | Chỉ được nhận nếu mã bắt đầu bằng 0 |
| Chỉ theo loại `off_balance` | **Thay đổi**: tài khoản chờ mã 0x hiện ra như tài khoản thường, mỗi khi có phát sinh | Tài khoản chờ hiện như tài khoản thường | Được nhận |
| Cả hai (đã chốt, quyết định 17) | Như cũ | Tài khoản chờ hiện như tài khoản thường | Được nhận |

Cả ba cách đều không đổi số liệu Tổng cộng (tài khoản ngoài bảng luôn được cộng); chỉ khác ở việc dòng nào bị ẩn khi hết số dư và dòng nào có nền cam.

Ở database mới theo `l10n_vn` 20.0, đơn vị áp dụng Thông tư 133 muốn ẩn 1131, 1132 thì thêm hai tài khoản đó vào danh sách tài khoản được ẩn của `fg_vn_transfer_account`; danh sách do người dùng tự chọn.

## 3. Quyết định thiết kế đề xuất

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Phụ thuộc `fg_vn_transfer_account` | Chuyển module đó sang 20.0 trước, theo kế hoạch riêng của nó (đã chốt). Nó chỉ có 76 dòng: một trường `fg_hide_transfer_account` trên `res.company` và một dòng trong trang cấu hình. | `fg_vn_report_s03a`, `s03b` và `vn_payment_print` cũng cần cờ này. Giấy phép của nó đã là AGPL-3. |
| 2 | Cây phân cấp (D1) | Dựng cây theo `account.account.parent_id`. Câu SQL chính lấy thêm `aa.parent_id`; cây dựng trong Python trên các tài khoản của công ty. Dòng tài khoản cha mang số của chính nó cộng mọi con cháu. Không còn dòng "nhóm" riêng: `is_group`, `is_synthetic`, `group_id` bị bỏ khỏi dữ liệu dòng, cùng quy tắc ẩn nhóm một ký tự. | Odoo 20 không còn nhóm tài khoản. |
| 3 | Tổng cộng | Cộng từ số riêng của từng tài khoản (trước khi cộng dồn lên cha), như 19.0. | Không cộng trùng cha và con. |
| 4 | Tách 131/331 theo đối tác trên cây | Tính theo từng tài khoản như 19.0; tài khoản cha cộng Dư Nợ và Dư Có của các con, không bù trừ. | Giữ nguyên tắc không bù trừ công nợ. |
| 5 | Cấp tài khoản (C2, C3) | Giữ cách của 19.0 (cách A ở mục 8.1): trình duyệt ẩn các dòng có mã dài hơn giới hạn, chỉ ở chế độ không phân cấp; máy chủ không biết tới bộ lọc này. Số của dòng bị ẩn không cộng vào đâu; Excel và PDF không theo cấp. Readme ghi rõ điều này. Nhánh lọc theo cấp không bao giờ chạy ở Python bị xoá. | Đã chốt. Đổi cấp tức thì, không gọi máy chủ; ít code. |
| 6 | Lọc dòng | Mọi quy tắc ẩn/hiện dòng nằm ở `_get_lines()`. `_groups_to_xlsx_rows()`, `CDPSPdf._groups_to_rows()` và JS chỉ chuyển dòng thành ô, không lọc lại (C6). | Một nguồn duy nhất cho ba đầu ra. |
| 7 | Tên tài khoản (C1) | SQL lấy `COALESCE(aa.name->>%(lang)s, aa.name->>'en_US')` với `lang` là ngôn ngữ báo cáo (`self.env.lang` sau khi nền tảng chuyển context theo `options['lang']`). | Đúng ngôn ngữ, không phụ thuộc thứ tự khoá JSON. |
| 8 | Dấu số dư (C8) | Bỏ nhánh theo loại tài khoản; tính một lần `bal = Nợ − Có`. | Kết quả không đổi, bớt 25 dòng. |
| 9 | Kỳ so sánh (C7) | Bốn lựa chọn: `none`, `previous_period`, `same_period_last_year`, `custom`. `previous_period`: nếu kỳ báo cáo là trọn tháng (ngày 1 đến ngày cuối tháng, một hay nhiều tháng) thì lùi đúng số tháng đó và kết thúc ở ngày cuối tháng; nếu không thì lùi cùng số ngày. `same_period_last_year`: lùi một năm, giữ ngày cuối tháng. `custom`: lấy `comparison_date_from`, `comparison_date_to` từ `options`; thiếu hoặc ngược thì báo `UserError`. Wizard có hai trường ngày, chỉ hiện khi chọn `custom`. Trên màn hình: bộ lọc `selection` cho loại kỳ và hai bộ lọc `date` chỉ hiện khi chọn `custom` (cần quyết định 18 của nền tảng). | Đã chốt bốn lựa chọn. |
| 10 | Xuất XML (C4, C5) | Giữ một cách tính duy nhất ở `vn.report.cdps`: hàm `get_xml(options)` trả về bytes. Thêm route `/vn_report/vn.report.cdps/export/xml` trong controller của module, dùng lại `_export()` của nền tảng. Nút trên màn hình và nút ở wizard cùng mở URL này. Bỏ `export_to_xml_download()`, `action_export_xml()` cũ và `_generate_xml_cdtk()`; không tạo `ir.attachment` nữa. | Một cách tính, không để lại file rác, kiểm tra quyền đi cùng đường với Excel và PDF. |
| 11 | Giá trị nhóm trong XML | Thẻ của tài khoản cha mang số của nó cộng con cháu theo cây `parent_id`. Thẻ của tài khoản không có con mang số riêng. `tongCong` cộng số riêng của các tài khoản, theo quy tắc loại trừ của 19.0 (bỏ tài khoản ngoài bảng; bỏ tài khoản trung chuyển đang ẩn và hết số dư). | Thay cho phép cộng theo tiền tố mã của nhóm ở 19.0. |
| 12 | Drill-down | Tài khoản không có con: như 19.0. Tài khoản cha: domain `('account_id', 'child_of', id)`. Thêm `('company_id', '=', công ty của báo cáo)`. | Đã chốt cho xem chi tiết trên dòng cha. |
| 13 | Tên mẫu và tên file | `_get_report_code()` giữ `'Trial Balance'`, nên Excel và PDF vẫn tên `Trial_Balance_<từ ngày>_<đến ngày>`. File XML đặt tên `F01-CDTK_<từ ngày>_<đến ngày>.xml`; để làm được, `_export()` của nền tảng nhận thêm một tham số tên mã tuỳ chọn. | 19.0 đặt tên file XML theo hai kiểu khác nhau ở hai nút (`F01-CDTK_<công ty>_<năm>` và `F01-CDTK_<ngày>`); nay thống nhất một kiểu. |
| 14 | Chuỗi | Tiếng Anh trong code (`_()`, `_t()`, nhãn trường, view), dịch ở `i18n/vi.po`. Tên thẻ trong file XML (`PL_CDTK`, `SoDuDauKy`…) là định dạng file, không dịch. | Theo quyết định chung. |
| 15 | Phân quyền | Wizard: một dòng `ir.access` cho `account.group_account_user`, thao tác `cru`. Báo cáo dùng nhóm mặc định của nền tảng. `get_xml()` gọi `_check_report_access()`. | Như 19.0. |
| 16 | Giấy phép | AGPL-3. | Theo quyết định chung. |
| 17 | Tài khoản ngoài bảng | Nhận diện bằng `account_type == 'off_balance'` **hoặc** mã bắt đầu bằng `0`. Câu SQL đã lấy `account_type` nên không tốn thêm truy vấn. Phân tích ở mục 2.1. | Giữ nguyên kết quả với database nâng cấp từ 19.0, đồng thời nhận đúng tài khoản ngoài bảng khai theo cách của Odoo. Đã chốt. |
| 18 | Tài khoản trung chuyển trong Tổng cộng (C13) | Chỉ loại khỏi Tổng cộng khi dòng bị ẩn (hết số dư đầu và cuối kỳ), giống quy tắc của bản XML. Tập tài khoản được ẩn lấy qua `company._fg_get_hidden_transfer_accounts()` (có thể nhiều tài khoản, do người dùng chọn); quy tắc áp dụng cho từng tài khoản trong tập. Các tài khoản bị ẩn được loại khỏi danh sách dòng trước khi dựng cây, để tổng của tài khoản cha khớp với các dòng con đang hiện. | Tổng Nợ luôn bằng Tổng Có. |

## 4. Cấu trúc module sau khi chuyển

```
fg_vn_report_cdps/
├── __init__.py
├── __manifest__.py                 depends: fg_vn_accounting_reports, fg_vn_transfer_account
├── readme.md
├── PLAN.md
├── controllers/main.py             /vn_report/vn.report.cdps/export/xml
├── models/
│   ├── cdps_report.py              vn.report.cdps
│   └── cdps_pdf.py                 CDPSPdf
├── wizard/
│   ├── cdps_wizard.py              vn.report.cdps.wizard
│   └── cdps_wizard_views.xml
├── views/cdps_report_views.xml     client action, menu
├── security/ir.access.csv
├── i18n/                           .pot và vi.po
├── static/
│   ├── description/index.html
│   └── src/
│       ├── js/cdps_report.js
│       └── scss/cdps_report.scss
└── tests/
    ├── common.py                   công ty, tài khoản có cha–con, bút toán mẫu
    ├── test_balances.py
    ├── test_hierarchy.py
    ├── test_comparison.py
    ├── test_exports.py
    └── test_access.py
```

So với 19.0: bỏ `report/`, `NOTES.md`, `security/ir.model.access.csv`; thêm `controllers/`, `i18n/`, `tests/`, `static/description/`. `static/src/xml/cdps_report.xml` bị bỏ vì nền tảng tự hiển thị bảng (đã chốt).

## 5. Việc cần làm theo file

### `models/cdps_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_is_off_balance()` | Sửa theo dòng dưới. |
| `_get_report_name()`, `_get_report_code()`, `_get_columns()` | Giữ; nhãn đổi sang `_()` tiếng Anh. |
| `_get_pdf_template()` | Bỏ (C9). |
| `_get_pdf_rl_renderer()` | Giữ; đưa import lên đầu file. |
| `_get_transfer_account_id()` | Bỏ, không ai gọi. |
| `_get_hidden_transfer_id()` | Đổi thành `_get_hidden_transfer_ids(company)`: trả tập id từ `company._fg_get_hidden_transfer_accounts()`. `_is_off_balance()` nhận thêm `account_type` và tập id này (quyết định 17, 18). |
| `_get_comparison_dates()` | Sửa theo quyết định 9. |
| `_compute_account_balances()` | Giữ câu SQL; lấy thêm `aa.parent_id`; tên theo ngôn ngữ (quyết định 7); bỏ nhánh theo loại tài khoản (quyết định 8). |
| `_compute_partner_balances()` | Giữ. |
| `_get_lines()` | Giữ khung; chuẩn hoá tên tuỳ chọn một lần (`hierarchy`, `show_zero_balance`, `account_level`); gọi hàm dựng cây mới; bỏ ba khoá thừa (C10); nhãn kết quả đổi sang `_()`. |
| `_get_max_code_length()` | Bỏ: lọc theo cấp chỉ làm ở trình duyệt (quyết định 5), nhánh Python không bao giờ chạy. |
| `_get_comparison_label()` | Giữ; nhãn đổi sang `_()`. |
| `_build_hierarchy_lines()` | **Viết lại** theo quyết định 2–4. Tách thành `_build_account_tree()` (cha–con, cộng dồn) và `_flatten_tree()` (thứ tự theo mã, cấp, ẩn/hiện). Dữ liệu dòng giữ các khoá mà JS và renderer đang đọc: `id`, `account_id`, `code`, `name`, `level`, `parent_id`, `is_parent`, `has_children`, `is_off_balance`, sáu cột số, sáu cột `prev_*`, `variance`, `variance_percent`. |
| `export_to_xml()` | Đổi thành `get_xml(options)` trả bytes; cộng tài khoản cha theo cây (quyết định 11); đưa import lên đầu file. |
| `export_to_xml_download()` | Bỏ (quyết định 10). |
| `_get_drill_down_action()` | Sửa theo quyết định 12; tên action đổi sang tiếng Anh. |
| `get_report_data()` | Giữ; nhãn bốn cột so sánh đổi sang `_()`. |
| `_groups_to_xlsx_rows()` | Bỏ phần lọc lại (quyết định 6); nhãn "TỔNG CỘNG" đổi sang `_()`. |

### `models/cdps_pdf.py`

`__init__(report_data, env)` chuyển tiếp `env` cho lớp cha; nhãn cột và "TỔNG CỘNG" lấy qua `self.env._()`; bỏ điều kiện `is_synthetic` (không còn dòng nhóm). Phần còn lại giữ: không cộng chuyển trang, không có phần ký tên, dòng ngoài bảng nền cam.

### `wizard/cdps_wizard.py`

Giữ các trường và `_get_report_options()`. Nhãn, lựa chọn đổi sang tiếng Anh; `comparison_type` còn bốn lựa chọn và thêm `comparison_date_from`, `comparison_date_to` (quyết định 9). `action_export_xml()` viết lại: kiểm tra ngày rồi trả `ir.actions.act_url` tới route XML, giống `action_export_xlsx()` của wizard cơ sở. Bỏ `_generate_xml_cdtk()` và ba import `base64`, `minidom`, `ET`.

### `wizard/cdps_wizard_views.xml`, `views/cdps_report_views.xml`

Giữ bố cục; chuỗi đổi sang tiếng Anh; thêm trường `report_lang` vào nhóm kỳ báo cáo. Thuộc tính `invisible="not mirror_margin"` giữ nguyên cú pháp.

### `controllers/main.py` (mới)

Kế thừa `VNReportController` của nền tảng, thêm route `/vn_report/vn.report.cdps/export/xml` gọi `self._export('vn.report.cdps', options, 'get_xml', 'xml', 'application/xml', filename_code='F01-CDTK')`.

### `security/ir.access.csv`

```
id,name,model_id,group_id/id,operation,domain
access_vn_report_cdps_wizard,vn.report.cdps.wizard,vn.report.cdps.wizard,account.group_account_user,cru,
```

### `static/src/js/cdps_report.js`

| Phần | Việc cần làm |
|---|---|
| Đầu file, đăng ký action | Bỏ `/** @odoo-module **/`; `registry.category("actions").add("vn_report_cdps", …)` giữ. |
| `static template` | Bỏ. |
| `getFilterDefinitions()` | Giữ bốn bộ lọc, thêm `comparison_type` và hai bộ lọc ngày của kỳ tự chọn; nhãn qua `_t()`. |
| `initializeFilters()`, `loadReportData()` | Giữ. `this.state` là `proxy` của nền tảng, tên khoá không đổi. |
| `_buildOptions()` | Giữ, vẫn xoá `account_level` trước khi gửi (quyết định 5). |
| `groupsToRows()` | Giữ ba nhánh như 19.0 (tìm kiếm, phẳng có lọc theo độ dài mã, phân cấp). Bỏ các điều kiện `is_synthetic` vì không còn dòng nhóm. Điều kiện ẩn dòng mã 2 ký tự không có số liệu xem lại khi chạy thử trên cây tài khoản thật. Nhãn dòng tổng cộng lấy từ dữ liệu máy chủ trả về (`total_label`), không dựng ở JS, để theo ngôn ngữ báo cáo. |
| `toggleNode()`, `_collectDescendants()`, `expandAll()`, `collapseAll()` | Giữ. |
| `getLineMenuItems()` | Cho drill-down trên cả tài khoản cha (quyết định 12). |
| `initializeFilters()` | Thêm: nạp `comparison_type` và hai ngày từ `options` của wizard. |
| `exportXml()` | Mở URL của route XML bằng cùng cách nền tảng mở Excel và PDF; bỏ `try/catch` nuốt lỗi (C11). |
| `getDataRowClass()` | Giữ. |

### `static/src/scss/cdps_report.scss`

Chép nguyên.

### `tests/`

| File | Nội dung kiểm tra |
|---|---|
| `test_balances.py` | Số dư đầu kỳ, phát sinh, cuối kỳ trên bút toán mẫu; bút toán nháp không tính; 131 có một đối tác dư Nợ và một đối tác dư Có cho ra cả hai cột; tài khoản ngoài bảng và tài khoản trung chuyển ẩn/hiện và vào/không vào tổng cộng đúng quy tắc; tuỳ chọn hiện tài khoản số 0. |
| `test_hierarchy.py` | Cha bằng số riêng cộng các con; tổng cộng không cộng trùng; tài khoản không có cha. |
| `test_comparison.py` | Ngày của từng loại kỳ so sánh: trọn tháng, trọn quý, trọn năm, khoảng lẻ, năm nhuận, tự chọn hợp lệ và không hợp lệ; chênh lệch và phần trăm; bốn cột được thêm vào `columns`. |
| `test_exports.py` | Excel mở được và số dòng khớp `_get_lines`; PDF tạo được ở cả hai bộ cột; XML có đủ ba phần, có `tongCong`, không có tài khoản ngoài bảng, số làm tròn; route XML trả đúng tên file. |
| `test_access.py` | Người không thuộc nhóm bị từ chối ở `get_report_data`, `get_xml` và route; công ty ngoài phạm vi bị từ chối. |

## 6. Thay đổi hành vi so với 19.0

Liệt kê riêng vì người dùng sẽ thấy số liệu hoặc màn hình khác đi.

1. **Cây phân cấp** theo tài khoản cha–con thay cho nhóm tài khoản (bắt buộc, do D1). Database nâng cấp từ 19.0 cần kiểm tra trường Tài khoản cha: việc Odoo có tự chuyển nhóm thành tài khoản cha khi nâng cấp hay không chưa được kiểm chứng.
2. **Dòng cha là tài khoản thật**: mở được chi tiết, và có thể có phát sinh riêng.
4. **Kỳ so sánh** còn bốn lựa chọn, có tự chọn khoảng ngày, đổi được trên màn hình (quyết định 9).
5. **XML** chỉ còn cách tính của nút trên màn hình; nút ở wizard cho ra cùng file đó (quyết định 10).
6. **Tổng cộng** gồm cả tài khoản trung chuyển khi nó còn số dư (quyết định 18).

## 7. Các giai đoạn

Đi cùng các giai đoạn của nền tảng (`fg_vn_accounting_reports/PLAN.md` mục 7).

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Khung module CDPS (manifest, `ir.access.csv`, menu, wizard chưa có nút). | Cài được trên 20.0, không cảnh báo khi nạp. |
| 1 | `cdps_report.py`: số dư, đối tác, cây, so sánh, dòng Excel. | `test_balances`, `test_hierarchy`, `test_comparison` chạy qua. |
| 2 | `cdps_pdf.py`. | PDF tạo được ở hai bộ cột, có tiếng Việt. |
| 3 | Wizard, `get_xml`, controller XML. | `test_exports`, `test_access` chạy qua. |
| 4 | `cdps_report.js` trên giao diện OWL 3 của nền tảng. | Chạy trên trình duyệt: bốn bộ lọc, tìm kiếm, mở/thu gọn, drill-down và quay lại, F5, bốn nút xuất file; console không có lỗi hay cảnh báo OWL. |
| 5 | `i18n/vi.po`, `static/description/index.html`, dòng trong `README.md` của repo. | Đủ tiếng Việt với người dùng tiếng Việt. |

## 8. Các điểm đã chốt

| Điểm | Quyết định |
|---|---|
| `fg_vn_transfer_account` | Chuyển trước; tài khoản được ẩn do người dùng chọn. |
| Cấp tài khoản | Cách A: chỉ ẩn dòng, ở trình duyệt, như 19.0. |
| Kỳ so sánh | Không so sánh, kỳ trước, cùng kỳ năm trước, tự chọn ngày; đổi được trên màn hình. |
| Xuất XML | Gộp về một cách tính, tải qua URL. |
| Tài khoản ngoài bảng | Theo loại `off_balance` hoặc mã bắt đầu bằng 0. |
| Xem chi tiết trên dòng tài khoản cha | Có. |

Không còn điểm nào chờ xác nhận.

### 8.1. So sánh hai cách làm bộ lọc Cấp tài khoản (để tham khảo)

Cách A được chọn. Cách B được ghi lại để dùng nếu sau này cần file xuất ra theo cấp.

| Khía cạnh | A. Chỉ ẩn dòng, ở trình duyệt (đã chọn) | B. Cộng dồn lên cha, ở máy chủ |
|---|---|---|
| Kết quả trên màn hình | Tổng các dòng đang hiện nhỏ hơn dòng Tổng cộng khi tài khoản chi tiết có số liệu. | Tổng các dòng đang hiện luôn bằng Tổng cộng. |
| Excel, PDF | Không theo cấp: luôn xuất mọi tài khoản. | Theo cấp đang chọn. |
| Lượng code | JS: khoảng 10 dòng. Python: không. | Python: ước 30–40 dòng. JS ngắn đi. |
| Truy vấn database | 1 câu SQL chính, thêm 1 câu cho 131/331, gấp đôi khi có so sánh. | Y hệt. |
| Khi đổi cấp trên màn hình | Tức thì, không gọi máy chủ. | Tải lại báo cáo. |
| Kiểm thử | Phần lọc ở JS, không có test tự động. | Phần lọc ở Python, có test. |

## 9. Điểm để ngỏ

Giữ nguyên hành vi 19.0, chưa được bàn; ghi lại để quyết định sau.

1. **Tài khoản đã lưu trữ còn số dư hoặc phát sinh không có trong báo cáo.** Câu SQL chỉ lấy tài khoản `active`. Nếu một tài khoản bị lưu trữ khi còn số liệu, Tổng Nợ và Tổng Có của bảng sẽ lệch nhau đúng bằng số của nó.
2. **Tài khoản của công ty con (chi nhánh).** Báo cáo lấy tài khoản gắn trực tiếp với công ty của báo cáo. Hệ thống tài khoản của Odoo thường gắn với công ty gốc; báo cáo lập cho một chi nhánh sẽ không thấy các tài khoản đó.
3. **Tách theo đối tác chỉ cho 131 và 331.** Các tài khoản công nợ khác (138, 338, 141…) được bù trừ trong từng tài khoản.
