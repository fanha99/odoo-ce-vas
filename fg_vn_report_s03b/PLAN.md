# Kế hoạch chuyển `fg_vn_report_s03b` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_report_s03b` (19.0.1.0.0, commit cuối đụng tới module: `cb4132e` ngày 2026-06-29; commit phân quyền `64fbf84` không sửa module này).
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả sổ làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **đã xong cả tám giai đoạn (2026-10-11).** 59 test chạy qua trên Odoo 20.0, gồm hai tour trình duyệt (sổ nhỏ và sổ tải dần). Số đo ở mục 9.

Khác với kế hoạch, phát sinh khi code:

| Điểm | Kế hoạch | Thực tế | Lý do |
|---|---|---|---|
| Số dư luỹ kế ở đầu mỗi đoạn tải dần | Trình duyệt gửi lại số dư của dòng cuối đã tải | Máy chủ tính bằng một câu `SUM` trên các dòng đứng trước | Máy chủ không phụ thuộc trạng thái của trình duyệt. Chi phí đo được: 0,55 giây khi bỏ qua 40.000 dòng, 0,07 giây ở đầu sổ. |
| Số dư luỹ kế khi tách dòng | Ghi ở dòng cuối của mỗi phát sinh | Cộng dồn theo từng dòng sau khi tách | Đơn giản hơn; giá trị ở dòng cuối của phát sinh giống hệt. |
| `_count_lines()` khi tách dòng | Đếm sau khi tách | Đếm số phát sinh (trước khi tách); số dòng của **từng tài khoản** trên màn hình thì đếm đúng sau khi tách | Con số này chỉ để quyết định tải dần và giới hạn PDF; đếm sau khi tách phải nối bảng cặp đối ứng. |
| Dòng có số tiền bằng 0 | Không nêu | Bỏ khỏi sổ, như S03a | Dòng không có số tiền không phải phát sinh. Thêm vào mục 6. |
| Dòng số dư khi tài khoản thu gọn (sổ tải dần) | Không nêu | Số dư đầu kỳ, cộng phát sinh, số dư cuối kỳ vẫn hiện; chỉ các phát sinh thu gọn | Readme mục 2 mô tả sổ dài như vậy. Ở sổ nhỏ, thu gọn vẫn ẩn cả các dòng này như 19.0. |
| Số chứng từ ghép | Hàm ghép cho mọi bút toán của các dòng | Chỉ cho bút toán có dòng bị ẩn (tìm bằng một câu SQL) | Như S03a. |

Đã chốt:

| Điểm | Quyết định |
|---|---|
| Tài khoản không có phát sinh | Tuỳ chọn ba mức: không lập sổ (mặc định), lập nếu có số dư đầu kỳ, lập tất cả. |
| Tên nhóm ở đầu trang PDF | Đưa vào nền tảng, thiết kế để lớp con mở rộng dễ: mục 3a. |
| Phát sinh có nhiều tài khoản đối ứng | Tuỳ chọn tách dòng theo tài khoản đối ứng, chọn khi xem và in sổ. Các cặp cùng tài khoản đối ứng gộp một dòng; phần chưa có đối ứng thành một dòng để trống mã (mục 3d). |
| Số dư luỹ kế từng dòng | Giữ trong dữ liệu, không in. Phân tích chi phí ở mục 3c. |
| Chậm trên dữ liệu lớn | Tải dần theo tài khoản và truy vấn theo lô (mục 3b). Khi tải dần, các tài khoản mở ở trạng thái thu gọn và nút "Mở rộng tất cả" bị ẩn. |
| Số dư đầu kỳ trên dữ liệu nhiều năm | Chưa tối ưu thêm nếu số đo chưa buộc phải làm. |
| In PDF sổ rất dài | Giới hạn số dòng như S03a. |

Ba module phụ thuộc (`fg_vn_accounting_reports`, `fg_account_counterpart`, `fg_vn_transfer_account`) đã có trên 20.0. Các quy ước chung theo `fg_vn_accounting_reports/doc/DEVELOPER.md` và làm như `fg_vn_report_cdps`. Nên chuyển sau `fg_vn_report_s03a` vì hai sổ dùng chung quy tắc ghép số chứng từ (`fg_vn_report_s03a/PLAN.md` quyết định 5).

## 1. Phân tích code nguồn

### 1.1. Thành phần

| Thành phần | File | Dòng | Sang 20.0 |
|---|---|---|---|
| `vn.report.s03b`: chọn tài khoản, số dư đầu kỳ, phát sinh kèm tài khoản đối ứng, thay tài khoản trung gian bằng đối ứng thật, số chứng từ ghép, dòng Excel, drill-down | `models/s03b_report.py` | 588 | viết lại phần truy vấn, giữ quy tắc |
| `S03bPDF`: cột theo hướng giấy, mỗi tài khoản một phần, tên tài khoản ở đầu trang, cộng chuyển trang theo tài khoản | `models/s03b_pdf.py` | 176 | giữ, bớt phần chuyển về nền tảng |
| `vn.report.s03b.wizard`: kỳ mặc định theo quý, năm bộ lọc | `wizard/s03b_wizard.py` | 76 | giữ |
| Form wizard, action | `wizard/s03b_wizard_views.xml` | 63 | giữ |
| Client action, menu | `views/s03b_report_views.xml` | 17 | giữ |
| `S03bReport` (OWL): bốn bộ lọc, dựng dòng theo tài khoản | `static/src/js/s03b_report.js` | 125 | sửa theo OWL 3 |
| Template gọi `DataTable` | `static/src/xml/s03b_report.xml` | 11 | bỏ |
| Phân quyền wizard | `security/ir.model.access.csv` | 1 dòng | đổi sang `ir.access.csv` |
| Ghi chú quy tắc tài khoản trung gian | `note.md` | 109 | gộp vào readme mục 4 và kế hoạch này |

### 1.2. Lỗi và điểm yếu có sẵn

| # | Vị trí | Vấn đề |
|---|---|---|
| B1 | `s03b_report.py:390-398` | **Truy vấn theo từng tài khoản.** Với mỗi tài khoản của công ty: một câu SQL số dư đầu kỳ, một câu phát sinh (có truy vấn con cho từng dòng để lấy mã đối ứng), và tối đa ba câu nữa cho tài khoản trung gian. Hệ thống tài khoản `l10n_vn` có khoảng 300 tài khoản: 600 câu SQL trở lên cho một lần mở sổ, kể cả khi hầu hết tài khoản không có phát sinh. |
| B2 | `s03b_report.py:401` | Tài khoản có số dư đầu kỳ nhưng không có phát sinh trong kỳ bị bỏ khỏi sổ (trừ khi bật hiện tài khoản không có phát sinh). Sổ cái của một kỳ yên ắng thiếu các tài khoản còn số dư. |
| B3 | `s03b_report.py:132-143,411-415` và `_balance_split` | Danh sách loại tài khoản "bản chất Nợ" viết tay ở hai nơi, thiếu `expense_other`. Kết quả hiển thị của `_balance_split` chỉ phụ thuộc dấu của (Nợ − Có), trừ trường hợp bằng 0, nên danh sách này không cần. Số dư luỹ kế từng dòng (`balance`, `balance_value`) được tính nhưng không cột nào hiển thị. |
| B4 | `s03b_report.py:203-221` | Tài khoản trung gian được nhận ra bằng cách **so chuỗi mã** trong danh sách mã đối ứng đã nối bằng dấu phẩy, và chỉ một tài khoản. |
| B5 | `s03b_report.py:77-86,456` | Tài khoản ngoài bảng chỉ nhận theo mã bắt đầu bằng 0. CDPS 20.0 đã nhận thêm loại `off_balance`. |
| B6 | `s03b_report.py:512-526` | Drill-down của tài khoản không lọc theo công ty, và không theo bộ lọc đối tác, sổ nhật ký đang chọn: danh sách mở ra có thể không khớp với sổ. |
| B7 | `s03b_report.js:38-67`, `s03b_wizard.py` | Bộ lọc Loại tài khoản chỉ có ở wizard. Ở JS có ghi chú TODO rằng ô tìm của bộ lọc nhiều-nhiều không hiện kết quả khi gõ. |
| B8 | `s03b_pdf.py:47-77` | `_draw_page_header` chép lại toàn bộ hàm của lớp cơ sở chỉ để vẽ thêm dòng "Tài khoản: …" và bỏ tiêu đề ở trang trắng. |
| B9 | `s03b_report.py:285-370` | Quy tắc số chứng từ ghép viết lại lần thứ hai (S03a có bản riêng). |
| B10 | `s03b_report.py:33`, `s03b_report.xml` | `_get_pdf_template()` và file template là code chết. |
| B11 | Toàn module | Chuỗi tiếng Việt viết thẳng; các nhãn "Tài khoản:", "Số dư đầu kỳ", "Cộng phát sinh", "Số dư cuối kỳ" dựng ở JS. Dữ liệu mang các khoá thừa chép từ báo cáo kho. Không có test. |

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng riêng tới S03b

| # | Khác biệt | Chỗ bị ảnh hưởng | Mức |
|---|---|---|---|
| F1 | `fg_account_counterpart` 20.0 đổi tên bảng quan hệ tài khoản đối ứng: `account_ctp_account_rel` (19.0) → **`account_move_line_countered_account_rel`**, cột vẫn là `aml_id`, `account_id`. Trường tương ứng: `account.move.line.countered_account_ids`. | Truy vấn con lấy mã đối ứng; bước 3 của `_resolve_tk10_counterparts` | **chặn** |
| F2 | Bảng `account_move_line_ctp` giữ `dr_aml_id`, `cr_aml_id`; 20.0 có thêm cột lưu sẵn `dr_account_id`, `cr_account_id`, `countered_amt`, `move_id`, `date`, `company_id`. | Bước 1 của `_resolve_tk10_counterparts` | không chặn; dùng được để viết gọn |
| F3 | `fg_vn_transfer_account` 20.0: danh sách tài khoản được ẩn, qua `company._fg_get_hidden_transfer_accounts()`. | Mọi chỗ dùng `transfer_id`, `transfer_code` | cần sửa |
| F4 | `ir.model.access` → `ir.access`; OWL 3; nền tảng bỏ `_get_pdf_template()`, renderer nhận `env`. | Như các module báo cáo khác | chặn |
| F5 | `account.account` có `parent_id` (thay `account.group`). | Không ảnh hưởng: sổ cái lập cho từng tài khoản với phát sinh của riêng nó. | |

Đã kiểm tra và **không đổi** trên lõi 20.0: các cột của `account.move`, `account.move.line`, `account.journal` mà truy vấn dùng (xem `fg_vn_report_s03a/PLAN.md` mục 2); `account.account.account_type` với các giá trị `asset_*`, `liability_*`, `equity*`, `income*`, `expense*`, `off_balance`.

Không có khác biệt lõi mới nào phải ghi vào vault. F1 và F2 là thay đổi của module nhà, ghi ở đây.

## 3. Quyết định thiết kế (đã chốt)

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Truy vấn (B1) | Đọc theo lô, số câu SQL không phụ thuộc số tài khoản: (a) một câu số dư đầu kỳ `GROUP BY account_id`; (b) một câu lấy mọi phát sinh trong kỳ của các tài khoản được chọn, kèm mảng id tài khoản đối ứng; (c) một lần gọi lấy đối ứng thật cho các dòng có đối ứng là tài khoản được ẩn; (d) một lần gọi lấy số chứng từ ghép. Gom theo tài khoản trong Python. | 600 câu SQL thành khoảng 5. Kết quả không đổi. |
| 2 | Tài khoản được lập sổ (B2) | Tuỳ chọn `empty_accounts` thay cho ô đánh dấu `show_zero_balance`, ba giá trị: `hide` (mặc định, như 19.0: chỉ tài khoản có phát sinh trong kỳ), `with_balance` (thêm tài khoản có số dư đầu kỳ), `all` (mọi tài khoản). Có trên wizard và trên menu bộ lọc. Tuỳ chọn cũ `show_zero_balance=True` được hiểu là `all`. | Đã chốt: mặc định không lập sổ cho tài khoản không có phát sinh. |
| 3 | Bên của số dư (B3) | `bal = Nợ − Có`; dương thì ở cột Nợ, âm thì ở cột Có. Bỏ danh sách loại tài khoản viết tay. Số dư luỹ kế từng dòng (`balance`) vẫn được tính và trả về, theo cùng quy ước dấu `Nợ − Có`; không cột nào in nó (mục 3c). | Cùng kết quả hiển thị với 19.0. |
| 4 | Tài khoản được ẩn (B4, F3) | Làm việc trên **id**: câu (b) trả mảng id tài khoản đối ứng; dòng nào có id thuộc tập được ẩn thì thay id đó bằng các id đối ứng thật (đi qua dòng đã đối soát ngược chiều, như 19.0); sau cùng mới đổi id thành mã và nối chuỗi. Dòng của tài khoản được ẩn chưa đối soát giữ nguyên mã của nó. | Không so chuỗi; đúng với nhiều tài khoản được ẩn. |
| 5 | Số chứng từ ghép (B9) | Gọi hàm dùng chung `account.move._fg_get_transfer_links()` nếu quyết định 5 của S03a được duyệt; nếu không thì giữ `_build_tk10_move_names` (đổi tên, đổi sang tập id). | Một định nghĩa cho hai sổ. |
| 6 | Tài khoản ngoài bảng (B5) | `account_type == 'off_balance'` hoặc mã bắt đầu bằng `0`, như CDPS. Tài khoản ngoài bảng và tài khoản được ẩn chỉ có sổ khi còn số dư đầu kỳ hoặc cuối kỳ; không áp dụng khi người dùng chọn đích danh tài khoản (như 19.0). | Thống nhất với CDPS. |
| 7 | Tên tài khoản ở đầu trang PDF (B8) | Đưa vào nền tảng (20.0.1.1.0), thiết kế ở mục 3a. `S03bPDF` chỉ còn `_format_group_label()`. | Đã chốt. |
| 8 | Cấu trúc dữ liệu (B11) | Nhóm: `id`, `account_id`, `code`, `name` (mã - tên), `label` ("Tài khoản: mã - tên"), `opening`, `closing` (mỗi cái `{debit, credit}`), `total` (`{debit, credit}`), `lines`, và ba nhãn `opening_label`, `total_label`, `closing_label`. Dòng: `id`, `move_id`, `date`, `date_display`, `move_name`, `description`, `counterpart_account`, `debit`, `credit`. Bỏ khoá thừa. | Nhãn do máy chủ trả về để theo ngôn ngữ báo cáo. |
| 9 | Bộ lọc trên màn hình (B7) | Thêm `account_type` (lựa chọn) vào menu bộ lọc. Ô tìm của bộ lọc nhiều-nhiều đã chạy trên nền tảng 20.0 (dùng `name_search`); kiểm lại bằng tour. | Wizard và màn hình cùng bộ lọc. |
| 10 | Loại tài khoản | Ánh xạ sang `account_type` bằng tiền tố thay cho danh sách viết tay: `asset` → `asset_%`, `liability` → `liability_%`, `equity` → `equity%`, `income` → `income%`, `expense` → `expense%`. | Bản 19.0 thiếu `liability_credit_card` và `expense_other`. |
| 11 | Drill-down (B6) | Dòng: mở bút toán. Tiêu đề tài khoản: danh sách phát sinh của tài khoản trong kỳ, thêm lọc công ty, đối tác và sổ nhật ký đang chọn. | Danh sách mở ra khớp với sổ. |
| 12 | Nhãn và tên file | `_get_report_code()` trả `_("Form No. S03b-DNN")`; `_get_export_filename_code()` trả `'S03b-DNN'`. | Như S03a. |
| 13 | Tách dòng theo tài khoản đối ứng | Tuỳ chọn `split_counterparts` (mặc định tắt), có trên wizard và trên menu bộ lọc, áp dụng cho màn hình, Excel và PDF. Tắt: như 19.0, một dòng bút toán là một dòng sổ, cột TK đối ứng liệt kê mọi mã. Bật: mỗi tài khoản đối ứng một dòng với số tiền của riêng cặp đó, lấy từ `account_move_line_ctp.countered_amt`; chi tiết ở mục 3d. | Đã chốt. |
| 14 | Sổ dài | Tải dần theo từng tài khoản, mục 3b. | Người dùng báo bản 19.0 chậm trên database lớn. |

## 3a. Tên nhóm ở đầu trang PDF, trong nền tảng

Hiện trạng: `FanhaReportPDF._render_group_paginated()` đã tính nhãn nhóm cho từng trang (`_page_group_labels`) và đánh dấu trang trắng chèn thêm (`_page_info[trang] == (0, 0)`), nhưng `_draw_page_header()` không dùng tới. `S03bPDF` phải chép cả hàm để vẽ thêm một dòng.

Thiết kế: tiêu đề trang là một **danh sách dòng** do một hàm trả về; hàm vẽ chỉ duyệt danh sách đó.

| Hàm của `FanhaReportPDF` | Nội dung | Lớp con làm gì |
|---|---|---|
| `_get_page_header_lines(page)` | Trả danh sách `{'text', 'bold', 'size', 'align', 'space_after'}`. Mặc định: tên công ty, tên sổ, kỳ, và nhãn nhóm của trang nếu có. | Ghi đè, gọi `super()` rồi thêm, bớt hoặc sửa dòng. |
| `_get_page_group_label(page)` | Nhãn nhóm của trang, rỗng nếu báo cáo không ngắt trang theo nhóm. | Hiếm khi cần. |
| `_format_group_label(group)` | Chuỗi nhãn của một nhóm (đã có sẵn). | Ghi đè để trả "Tài khoản: …", "Sản phẩm: …". |
| `_is_blank_page(page)` | Trang trắng chèn thêm khi in lề đối xứng. | Không cần. |
| `_draw_page_header(c, doc, ml)` | Vẽ các dòng của `_get_page_header_lines`; không vẽ gì trên trang trắng. | Không cần ghi đè nữa. |
| `_company_hdr_height()` | Tính từ số dòng tiêu đề nhiều nhất thay cho hằng số 22 mm. | Không cần. |

Yêu cầu "làm kỹ":

- PDF của báo cáo không ngắt trang theo nhóm (CDPS, S03a) phải giống hệt trước khi sửa: test so số trang và nội dung chữ từng trang trước và sau.
- Test mới: nhãn nhóm có ở mọi trang của nhóm, kể cả trang thứ hai trở đi; trang trắng không có tiêu đề và không có số trang; lớp con thêm một dòng tiêu đề bằng `_get_page_header_lines` mà không đụng hàm vẽ; chiều cao vùng tiêu đề tăng đúng khi thêm dòng, bảng không đè lên tiêu đề.
- `doc/DEVELOPER.md` mục 3 thêm bảng hook trên.

## 3b. Chậm trên dữ liệu lớn: phân tích và phương án

### Bản 19.0 tốn thời gian ở đâu

Đọc từ `s03b_report.py` 19.0. Chưa đo trên database thật; giai đoạn 0 có bước đo để xác nhận thứ tự dưới đây.

| # | Nguyên nhân | Tăng theo | Mức |
|---|---|---|---|
| P1 | **Dựng bảng trên trình duyệt.** Mọi dòng của mọi tài khoản trong kỳ được gửi về và dựng thành dòng bảng, tất cả tài khoản ở trạng thái mở. | tổng số dòng của kỳ | Nhiều khả năng là chỗ nghẽn chính khi kỳ có hàng chục nghìn dòng. |
| P2 | **Số dư đầu kỳ từng tài khoản.** Mỗi tài khoản một câu `SUM` trên toàn bộ lịch sử trước kỳ, nối `account_move` để lọc trạng thái và ngày. | số tài khoản × số dòng lịch sử | Nặng dần theo số năm dữ liệu. |
| P3 | **Một lượt truy vấn cho mỗi tài khoản**, kể cả tài khoản không có phát sinh: 2 đến 5 câu SQL mỗi tài khoản. | số tài khoản | Vài trăm lượt đi về database. |
| P4 | **Truy vấn con cho từng dòng** để nối mã tài khoản đối ứng. | số dòng của kỳ | Vừa. |
| P5 | **Dựng dữ liệu và JSON** với các khoá thừa (mỗi dòng 19 khoá, 8 khoá không dùng). | số dòng của kỳ | Nhỏ. |
| P6 | Thay tài khoản trung gian và ghép số chứng từ, chạy riêng cho từng tài khoản. | số tài khoản có dòng liên quan | Nhỏ. |

### Phương án

| Nguyên nhân | Xử lý |
|---|---|
| P1 | **Tải dần theo tài khoản**, dùng cơ chế chung của nền tảng (mô tả đầy đủ ở `fg_vn_report_s03a/PLAN.md` mục 3b). Dưới ngưỡng 2.000 dòng: như cũ, gửi hết, mọi tài khoản mở. Trên ngưỡng: lần đầu chỉ gửi **dòng tổng hợp của từng tài khoản** (số dư đầu kỳ, cộng phát sinh, số dư cuối kỳ, số dòng), các tài khoản ở trạng thái thu gọn. Mở một tài khoản mới tải 500 dòng đầu của nó; "Xem thêm" tải tiếp. |
| P2 | Một câu SQL cho mọi tài khoản: `SUM … FILTER (WHERE date < đầu kỳ)` cùng `SUM` trong kỳ, `GROUP BY account_id`. Lọc bằng các cột có sẵn trên `account_move_line` (`parent_state`, `date`, `company_id`, `journal_id`, `partner_id`), không nối `account_move`. Index `(account_id, date)` của lõi phục vụ truy vấn này. Câu này cũng cho luôn cộng phát sinh, số dư cuối kỳ và số dòng của từng tài khoản. |
| P3 | Số câu SQL không phụ thuộc số tài khoản (quyết định 1). |
| P4 | Lấy mảng id tài khoản đối ứng bằng một phép nối có gom nhóm, đổi id thành mã ở Python từ một bảng tra nạp một lần. |
| P5 | Bỏ khoá thừa (quyết định 8). |
| P6 | Một lần gọi cho mọi dòng được tải (quyết định 4, 5). |

Hệ quả cho người dùng khi sổ đang tải dần: tài khoản mở ra từng cái một; nút "Mở rộng tất cả" bị ẩn; ô tìm kiếm vẫn lọc theo mã và tên tài khoản như cũ vì danh sách tài khoản luôn có đủ.

Phần còn lại sau khi sửa: câu tổng hợp P2 vẫn phải đọc toàn bộ lịch sử trước kỳ của các tài khoản được chọn, mỗi lần mở sổ. Nếu số đo ở giai đoạn 0 cho thấy nó vượt một giây, phương án tiếp theo là tính số dư đầu kỳ từ đầu năm tài chính cho tài khoản doanh thu, chi phí, hoặc lưu số dư theo tháng; cả hai đổi cách tính nên **không** làm trong đợt này nếu chưa có số đo buộc phải làm.

Excel và PDF: luôn xuất cả sổ. PDF chịu giới hạn số dòng của nền tảng (`fg_vn_report_s03a/PLAN.md` mục 3b); số dòng đếm sau khi tách dòng nếu tuỳ chọn tách dòng đang bật.

## 3c. Số dư luỹ kế từng dòng

**Có dùng để chốt số cuối trang không?** Không. Dòng "Cộng chuyển trang" và "Số dư đầu trang" của sổ cái cộng dồn hai cột Nợ và Có (`_get_carry_cols()` trả `[4, 5]`). Cơ chế mang số dư sang trang (`_get_carry_last_cols()`) có trong nền tảng nhưng S03b trả danh sách rỗng, vì sổ không có cột số dư.

**Chi phí giữ lại:**

| Chỗ | Chi phí |
|---|---|
| Tính | Một phép cộng cho mỗi dòng, trong vòng lặp vốn đã duyệt mọi dòng. Không thêm truy vấn. |
| Truyền về trình duyệt | Thêm một khoá số trên mỗi dòng, khoảng 20 byte trên 250. |
| Khi tải dần | Số dư luỹ kế của dòng đầu mỗi đoạn cần tổng của các dòng trước nó. Tính bằng một `SUM` trên các dòng đứng trước trong cùng tài khoản và kỳ, dùng index `(account_id, date)`; hoặc trình duyệt gửi lại số dư của dòng cuối đã tải. Chọn cách thứ hai: không thêm truy vấn. |

Kết luận: giữ `balance` trên mỗi dòng (bỏ bản sao `balance_value`), không in. Khi cần cột "Số dư" thì thêm cột và bật `_get_carry_last_cols()`; không phải sửa phần tính.

Lưu ý: khi bật tách dòng theo tài khoản đối ứng (mục 3d), số dư luỹ kế được ghi ở dòng cuối cùng của mỗi phát sinh.

## 3d. Tách dòng theo tài khoản đối ứng

Ví dụ: hoá đơn bán hàng ghi Nợ 131 110.000.000; Có 511 100.000.000; Có 33311 10.000.000. Trên sổ cái 131:

| Tuỳ chọn | Dòng trên sổ |
|---|---|
| Tắt (mặc định) | một dòng: TK đối ứng `33311, 511`, Nợ 110.000.000 |
| Bật | hai dòng: TK đối ứng `33311`, Nợ 10.000.000; TK đối ứng `511`, Nợ 100.000.000 |

Quy tắc khi bật:

1. Mỗi phát sinh được tách theo **tài khoản đối ứng**: các cặp trong `account_move_line_ctp` có cùng tài khoản đối ứng được cộng lại thành một dòng. Các dòng của một phát sinh xếp theo mã tài khoản đối ứng.
2. Số tiền của mỗi dòng là `countered_amt` của các cặp đó, đặt ở cột Nợ hay Có theo phía của phát sinh.
3. **Phần chưa có đối ứng** (bút toán ghi sổ trước khi cài `fg_account_counterpart`, bút toán có số âm, hoặc đối ứng một phần): một dòng với TK đối ứng để trống và số tiền còn lại, để tổng các dòng luôn bằng số tiền của phát sinh. Cộng phát sinh và số dư không đổi dù bật hay tắt.
4. **Tài khoản được ẩn:** nếu tài khoản đối ứng của một cặp là tài khoản được ẩn đã đối soát, nó được thay bằng tài khoản thật. Khi đầu bên kia có nhiều tài khoản, dòng đó ghi các mã nối bằng dấu phẩy và không tách tiếp.
5. Ngày, số chứng từ và diễn giải lặp lại trên từng dòng. Drill-down của mọi dòng mở cùng một bút toán.
6. Số dòng của tài khoản (để tải dần và hiển thị "đã hiện … / …") đếm theo dòng sau khi tách.

Thực hiện: câu lấy dòng nối `account_move_line_ctp` hai lần (phát sinh ở phía Nợ, phát sinh ở phía Có), `GROUP BY` phát sinh và tài khoản đối ứng; phần còn lại tính bằng số tiền của phát sinh trừ tổng `countered_amt`. Khi tắt, truy vấn không nối bảng cặp mà đọc `account_move_line_countered_account_rel` như quyết định 1.

## 4. Cấu trúc module sau khi chuyển

```
fg_vn_report_s03b/
├── __init__.py
├── __manifest__.py                 depends: fg_vn_accounting_reports, fg_account_counterpart, fg_vn_transfer_account
├── readme.md
├── PLAN.md
├── models/
│   ├── s03b_report.py              vn.report.s03b
│   └── s03b_pdf.py                 S03bPDF
├── wizard/
│   ├── s03b_wizard.py              vn.report.s03b.wizard
│   └── s03b_wizard_views.xml
├── views/s03b_report_views.xml     client action, menu
├── security/ir.access.csv
├── i18n/                           .pot và vi.po
├── static/
│   ├── description/index.html
│   ├── src/js/s03b_report.js
│   └── tests/tours/s03b_report_tour.js
└── tests/
    ├── common.py                   tài khoản, bút toán mẫu có đối ứng, cặp nộp tiền qua tài khoản trung chuyển
    ├── test_ledger.py
    ├── test_counterparts.py
    ├── test_transfer.py
    ├── test_exports.py
    ├── test_wizard.py
    └── test_ui.py
```

So với 19.0: bỏ `static/src/xml/`, `note.md`, `security/ir.model.access.csv`; thêm `i18n/`, `tests/`, `static/description/`, `static/tests/`.

## 5. Việc cần làm theo file

### `models/s03b_report.py`

| Hàm 19.0 | 20.0 |
|---|---|
| `_get_report_name()`, `_get_report_code()`, `_get_columns()` | Nhãn qua `_()`; thêm `_get_export_filename_code()`. |
| `_get_pdf_template()` | Bỏ. |
| `_format_date_display()` | Giữ. |
| `_get_filter_accounts(options)` | Giữ; loại tài khoản theo quyết định 10; trả về recordset trong ngôn ngữ báo cáo. |
| `_is_off_balance_account()` | Theo quyết định 6; nhận tập id được ẩn. |
| `_balance_split()` | Thay bằng hàm một dòng theo dấu (quyết định 3). |
| `_compute_opening_balance(account_id, …)` | Thay bằng `_get_account_summaries(account_ids, options)`: một câu SQL cho mọi tài khoản, trả số dư đầu kỳ, cộng phát sinh và số dòng (mục 3b, P2). |
| (mới) `_count_lines()`, `_get_group_summaries()`, `_get_group_lines()` | Ba hook tải dần của nền tảng. |
| `_get_account_moves(account_id, …)` | Thay bằng `_query_lines(account_ids, options, offset=None, limit=None)`: một câu SQL cho mọi tài khoản được yêu cầu. Không tách dòng: trả `counterpart_account_ids` là mảng id đọc từ `account_move_line_countered_account_rel`. Tách dòng: theo mục 3d. |
| `_resolve_tk10_counterparts()` | Đổi tên `_get_real_counterparts(aml_ids, hidden_ids)`: giữ ba bước của 19.0 (cặp đối ứng trong bút toán → dòng cùng `full_reconcile_id`, cùng tài khoản, ngược chiều → tài khoản đối ứng của dòng đó), trên tập tài khoản được ẩn, trả id tài khoản. Bước 1 dùng `dr_account_id`/`cr_account_id` có sẵn (F2); bước 3 đọc bảng mới (F1). |
| `_build_tk10_move_names()` | Thay bằng hàm dùng chung (quyết định 5). |
| `_get_lines(options)` | Viết lại theo lô (quyết định 1), áp các quyết định 2, 3, 4, 6, 8. |
| `_get_drill_down_action()` | Quyết định 11. |
| `_should_xlsx_split_by_group()`, `_format_xlsx_sheet_name()`, `_format_xlsx_group_label()`, `_group_to_xlsx_rows()`, `_set_xlsx_column_widths()` | Giữ; nhãn lấy từ dữ liệu nhóm. `_format_xlsx_sheet_name()` bỏ, dùng bản của nền tảng (cùng logic). |

`flush_model()` cho `account.move.line`, `account.move`, `account.account`, `account.move.line.ctp` trước khi chạy SQL.

### `fg_vn_accounting_reports` 20.0.1.1.0

`pdf_renderer.py`: tiêu đề trang theo mục 3a. Cơ chế tải dần theo `fg_vn_report_s03a/PLAN.md` mục 3b (làm một lần, hai sổ cùng dùng).

### `models/s03b_pdf.py`

Nhãn cột qua `self.env._()`; các nhãn dòng lấy từ dữ liệu nhóm. Bỏ `_draw_page_header` (quyết định 7) và `_groups_to_rows` dự phòng; thêm `_format_group_label(group)` trả `group['label']`. Giữ: cột theo hướng giấy; cộng chuyển trang cột 4 và 5, đặt lại theo tài khoản (`carry_reset` ở dòng đầu); `keep_with_next` trên dòng cộng phát sinh; `_should_paginate_by_group()`; phần "Sổ này bao gồm … trang".

### `wizard/`, `security/ir.access.csv`

Giữ các trường; nhãn và lựa chọn tiếng Anh; `check_company=True` cho `account_ids`, `journal_ids`. Form thêm `report_lang`. Một dòng `ir.access` cho wizard, nhóm `account.group_account_user`, thao tác `cru`.

### `static/src/js/s03b_report.js`

| Phần | Việc cần làm |
|---|---|
| Đầu file, `static template` | Bỏ `@odoo-module`, `static template` và ghi chú TODO. |
| `getFilterDefinitions()` | Sáu bộ lọc: `account_ids`, `account_type`, `partner_ids`, `journal_ids`, `empty_accounts` (lựa chọn), `split_counterparts` (bật/tắt). Nhãn qua `_t()`. |
| `getSearchKeys()` | `['code', 'name']`. |
| `groupsToRows()` | Giữ cấu trúc (tiêu đề, số dư đầu kỳ, phát sinh, cộng, số dư cuối kỳ); mọi nhãn lấy từ dữ liệu nhóm; mọi dòng có `id` ổn định; thêm dòng "Xem thêm" của nền tảng sau các phát sinh đã tải. |
| `getLineMenuItems()`, `getGroupMenuItems()` | Mở bút toán; mở phát sinh của tài khoản. Nhãn qua `_t()`. |

### `tests/`

| File | Nội dung kiểm tra |
|---|---|
| `test_ledger.py` | Số dư đầu kỳ, phát sinh, cộng, số dư cuối kỳ và bên của số dư; thứ tự dòng; bút toán nháp không tính; ba giá trị của tuỳ chọn tài khoản không có phát sinh (ẩn, có số dư, tất cả) và giá trị cũ `show_zero_balance`; từng bộ lọc (tài khoản, loại, đối tác kèm số dư đầu kỳ của riêng đối tác, sổ nhật ký); tài khoản ngoài bảng; công ty khác không lẫn vào; số câu SQL không tăng theo số tài khoản. |
| `test_counterparts.py` | Một đối ứng; nhiều đối ứng nối bằng dấu phẩy theo thứ tự mã; bút toán chưa có đối ứng thì cột trống. Tách dòng: hoá đơn ở mục 3d cho hai dòng đúng số tiền; hai cặp cùng tài khoản đối ứng gộp một dòng; phần chưa đối ứng thành dòng trống mã; cộng phát sinh và số dư giống hệt khi tắt; kết hợp với tài khoản được ẩn. |
| `test_lazy.py` | Trên ngưỡng: lần đầu chỉ có dòng tổng hợp của từng tài khoản, đúng số dư và số dòng; mở một tài khoản trả 500 dòng đầu; đoạn tiếp theo không lặp, không sót; số dư luỹ kế liền mạch qua các đoạn; kết quả khớp với sổ tải hết; số câu SQL không tăng theo số tài khoản hay số dòng của kỳ. |
| `test_transfer.py` | Thiết lập tắt: đối ứng là 113. Thiết lập bật: đối ứng thật ở cả hai đầu; nhiều phiếu chi gộp một lần nộp không lấy nhầm tài khoản của phiếu khác; dòng chưa đối soát giữ 113; số chứng từ ghép; tài khoản được ẩn không có sổ khi hết số dư và có sổ khi còn; hai tài khoản được ẩn. |
| `test_exports.py` | Excel: mỗi tài khoản một sheet, tên sheet hợp lệ, dòng nhãn tài khoản, bốn loại dòng. PDF: mỗi tài khoản trang mới, tên tài khoản ở đầu trang, cộng chuyển trang đặt lại theo tài khoản, lề đối xứng bắt đầu ở trang lẻ, bản tiếng Việt. |
| `test_wizard.py` | Mặc định, tuỳ chọn gửi đi, quyền. |
| `test_ui.py` | Tour: mở sổ, thu gọn một tài khoản, bộ lọc tài khoản (gõ để tìm), mở bút toán và quay lại. |

## 6. Thay đổi hành vi so với 19.0

1. Tuỳ chọn tài khoản không có phát sinh có ba mức thay cho hai (quyết định 2). Mặc định như 19.0.
2. Tuỳ chọn mới: tách dòng theo tài khoản đối ứng (quyết định 13). Mặc định tắt, như 19.0.
3. Sổ trên 2.000 dòng mở ở trạng thái thu gọn và tải dòng của từng tài khoản khi người dùng mở nó (quyết định 14).
4. Ẩn theo danh sách tài khoản do đơn vị chọn (quyết định 4).
5. Tài khoản ngoài bảng nhận thêm theo loại `off_balance` (quyết định 6).
6. Bộ lọc Loại tài khoản tính cả `liability_credit_card` và `expense_other` (quyết định 10), và có trên màn hình (quyết định 9).
7. Drill-down của tài khoản theo công ty và các bộ lọc đang chọn (quyết định 11).
8. Tên file xuất bắt đầu bằng `S03b-DNN`.
9. Dòng bút toán có số tiền bằng 0 không còn trên sổ.

## 7. Các giai đoạn

Giai đoạn 0 đến 2 của `fg_vn_report_s03a/PLAN.md` (dữ liệu đo, quy tắc ghép dùng chung, tải dần ở nền tảng) phải xong trước.

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Nền tảng: tiêu đề trang PDF theo mục 3a (cùng bản 20.0.1.1.0 với tải dần). | Test mới chạy qua; PDF của CDPS và S03a không đổi. |
| 1 | Khung module; `s03b_report.py`: câu tổng hợp, lấy dòng theo lô, số dư, bộ lọc, đối ứng, tuỳ chọn tài khoản không có phát sinh. | `test_ledger`, `test_counterparts` (phần không tách dòng) chạy qua. |
| 2 | Tài khoản được ẩn: đối ứng thật, số chứng từ ghép. | `test_transfer` chạy qua. |
| 3 | Tách dòng theo tài khoản đối ứng. | Phần tách dòng của `test_counterparts` chạy qua. |
| 4 | Tải dần theo tài khoản. | `test_lazy` chạy qua. |
| 5 | `s03b_pdf.py`, dòng Excel, wizard. | `test_exports`, `test_wizard` chạy qua. |
| 6 | `s03b_report.js`, tour. | Tour chạy qua trên sổ nhỏ và trên sổ tải dần; console không có lỗi hay cảnh báo. |
| 7 | Đo trên dữ liệu của giai đoạn 0 của S03a: mở sổ, mở một tài khoản, tải thêm, Excel, PDF, có và không tách dòng. `i18n/vi.po`, `static/description/index.html`, dòng trong `README.md` của repo. | Số đo ghi vào kế hoạch; sổ in ra tiếng Việt đầy đủ. |

## 8. Điểm cần xác nhận

Không còn. Số đo ở giai đoạn 7 quyết định có phải tối ưu tiếp việc tính số dư đầu kỳ hay không (cuối mục 3b).

## 9. Số đo

Đo ngày 2026-10-11 trên máy phát triển (Windows 11, PostgreSQL 16), một công ty có 61.000 bút toán và 184.000 dòng bút toán, trong đó quý đo có 52.000 bút toán, 154.000 dòng, gồm 1.000 cặp nộp tiền qua tài khoản trung chuyển đã đối soát. Số trong bảng là lần nhanh nhất trong ba lần chạy, tính ở máy chủ (chưa gồm thời gian trình duyệt dựng bảng).

| Thao tác trên sổ cái | Không ẩn | Có ẩn tài khoản trung chuyển |
|---|---|---|
| Đếm dòng của quý | 0,08 giây | 0,08 giây |
| **Mở sổ (các tài khoản thu gọn, đủ số dư)** | **0,17 giây** | **0,17 giây** |
| Mở tài khoản lớn nhất (50.000 dòng), 500 dòng đầu | 0,07 giây | 0,08 giây |
| Xem thêm, từ dòng 40.000 | 0,55 giây | 0,55 giây |
| Mở sổ, có tách dòng theo tài khoản đối ứng | 1,1 giây | 1,1 giây |
| Mở tài khoản lớn nhất, có tách dòng | 0,59 giây | 0,63 giây |
| Tải cả sổ một lần, như 19.0 | 2,6 giây, 38 MB | 3,0 giây, 37,5 MB |

| Xuất file | Thời gian | Kích thước |
|---|---|---|
| Excel cả quý | 10 giây | 4,6 MB |
| PDF một tuần, 11.900 dòng | 13 giây | 1,6 MB |
| PDF một tháng, 50.800 dòng | 59 giây | 6,8 MB |

Kết luận:

- Mở sổ mất 0,17 giây thay cho 2,6 giây và 38 MB. Số câu SQL của một lần mở sổ là 8 đến 14, không phụ thuộc số tài khoản.
- Câu tổng hợp số dư đầu kỳ nằm trong 0,17 giây đó, với 10.000 bút toán lịch sử trước kỳ. **Chưa cần tối ưu thêm**; dữ liệu đo chưa có lịch sử nhiều năm, nên kết luận này cần được kiểm lại trên database thật.
- Tách dòng làm mở sổ chậm hơn (1,1 giây) vì phải đếm số dòng sau khi tách của từng tài khoản.
- PDF tốn khoảng 1,2 mili giây mỗi dòng, như S03a; cùng giới hạn 30.000 dòng.
