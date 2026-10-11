# Kế hoạch chuyển `fg_vn_report_s03a` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_report_s03a` (19.0.1.0.0, commit cuối đụng tới module: `cb4132e` ngày 2026-06-29; commit phân quyền `64fbf84` không sửa module này).
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả sổ làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **đã xong cả bảy giai đoạn (2026-10-11).** 50 test chạy qua trên Odoo 20.0, gồm hai tour trình duyệt (sổ nhỏ và sổ tải dần). Số đo ở mục 9.

Khác với kế hoạch, phát sinh khi code:

| Điểm | Kế hoạch | Thực tế | Lý do |
|---|---|---|---|
| Dòng bị ẩn | Lấy từ `hidden_line_ids` của hàm ghép | Loại ngay trong điều kiện SQL của sổ (`account_id` thuộc tập được ẩn và có `full_reconcile_id`) | Đếm, tính tổng và lấy dòng dùng chung một điều kiện; không phải chuyển danh sách id dòng giữa các bước. Hàm ghép vẫn trả `hidden_line_ids` cho module khác. |
| Hàm ghép chỉ được gọi cho bút toán có dòng bị ẩn | Gọi cho mọi bút toán của kỳ | Câu sắp xếp đánh dấu bút toán nào có dòng bị ẩn; chỉ các bút toán đó đi qua hàm ghép, số còn lại dùng khoá mặc định của cùng module | Không phải đọc 52.000 bút toán qua ORM mỗi lần tải. |
| Bút toán chính của cụm | 19.0 chọn trong các bút toán của kỳ đang xem | Chọn trên cả cụm, kể cả bút toán ngoài kỳ | Số chứng từ ghép không đổi theo kỳ đang xem hay sổ đang in. |
| Tìm kiếm ở máy chủ | Bật khi sổ đang tải dần | Thêm: giữ ở máy chủ cho tới khi ô tìm kiếm được xoá, kể cả khi kết quả tìm đã xuống dưới ngưỡng | Kết quả dưới ngưỡng là một tập đã lọc; xoá ô tìm kiếm phải tải lại cả sổ. |
| Tham số hệ thống | `get_param` | `get_int` | Odoo 20 bỏ `ir.config_parameter.get_param/set_param` (đã ghi vault). |

Đã chốt:

| Điểm | Quyết định |
|---|---|
| Bộ lọc Tài khoản, Đối tác | Chỉ hiện các dòng khớp; chấp nhận Nợ khác Có. |
| Dòng ghi chú, tiêu đề mục, dòng bằng 0 | Bỏ khỏi sổ. |
| Quy tắc ghép số chứng từ | Đưa vào `fg_vn_transfer_account`, dùng chung. Thiết kế ở mục 3a. |
| Bộ cột | Giữ như 19.0. |
| Sổ dài | Tải dần theo mục 3b: ngưỡng 2.000 dòng, mỗi lần 500 dòng; khi tải dần thì ẩn nút "Mở rộng tất cả" và tìm kiếm ở máy chủ. |
| In PDF sổ rất dài | Đặt giới hạn số dòng sau khi đo; vượt thì báo người dùng thu hẹp kỳ hoặc bộ lọc. |
| Phiên bản | `fg_vn_transfer_account` và `fg_vn_accounting_reports` lên 20.0.1.1.0 trong đợt này. |

Nền tảng (`fg_vn_accounting_reports`) và `fg_vn_transfer_account` đã có trên 20.0. Các quy ước chung (OWL 3, `ir.access`, chuỗi tiếng Anh, tuỳ chọn ngôn ngữ, cách viết test) theo `fg_vn_accounting_reports/doc/DEVELOPER.md` và làm như `fg_vn_report_cdps`; kế hoạch này chỉ ghi phần riêng của S03a.

## 1. Phân tích code nguồn

### 1.1. Thành phần

| Thành phần | File | Dòng | Sang 20.0 |
|---|---|---|---|
| `vn.report.s03a`: truy vấn dòng bút toán, ghép cặp qua tài khoản trung chuyển, tên chứng từ ghép, thứ tự, dòng Excel, drill-down | `models/s03a_report.py` | 371 | giữ thuật toán, sửa truy vấn |
| `S03aPDF`: cột theo hướng giấy, cộng chuyển trang hai cột tiền, phần "Sổ này bao gồm … trang" | `models/s03a_pdf.py` | 118 | giữ |
| `vn.report.s03a.wizard`: kỳ mặc định theo quý, bốn bộ lọc | `wizard/s03a_wizard.py` | 70 | giữ |
| Form wizard, action | `wizard/s03a_wizard_views.xml` | 61 | giữ |
| Client action, menu | `views/s03a_report_views.xml` | 17 | giữ |
| `S03aReport` (OWL): bộ lọc sổ nhật ký, dựng dòng | `static/src/js/s03a_report.js` | 105 | sửa theo OWL 3 |
| Template gọi `DataTable` | `static/src/xml/s03a_report.xml` | 11 | bỏ (nền tảng tự hiển thị bảng) |
| Phân quyền wizard | `security/ir.model.access.csv` | 1 dòng | đổi sang `ir.access.csv` |
| Ghi chú quy tắc tài khoản trung gian | `note.md` | 67 | gộp vào readme mục 3 và kế hoạch này |

### 1.2. Lỗi và điểm yếu có sẵn

| # | Vị trí | Vấn đề |
|---|---|---|
| A1 | `s03a_report.py:76-99` | **Không bộ lọc nào có tác dụng.** Wizard gửi `journal_ids`, `account_ids`, `partner_ids`, `move_type`; màn hình có bộ lọc `journal_ids`. Câu SQL chỉ lọc theo công ty, ngày và trạng thái. |
| A2 | `s03a_report.js:19` và `abstract_report.js` | Ô tìm kiếm lọc theo `name`, `code` của **nhóm**. Sổ chỉ có một nhóm với tên rỗng và mã `all`, nên gõ gì cũng làm sổ trống (trừ khi gõ đúng "all"). |
| A3 | `s03a_report.py:75,100` | `try: … except Exception: return []` bọc câu SQL: lỗi truy vấn bị nuốt và sổ hiện trống. Sau một lỗi SQL, transaction đã hỏng nên các lệnh sau cũng hỏng. |
| A4 | `s03a_report.py:76-99` | Lấy mọi dòng bút toán, gồm dòng ghi chú, tiêu đề mục của hoá đơn (`display_type` là `line_section`, `line_subsection`, `line_note`) và dòng có Nợ = Có = 0. Chúng thành dòng sổ không có tài khoản ở cột nào và không có số tiền. |
| A5 | `s03a_report.py:68-72,113,137,226` | Tài khoản trung gian được nhận ra bằng cách **so mã** tài khoản, và chỉ một tài khoản. Bản 20.0 của `fg_vn_transfer_account` cho chọn danh sách tài khoản. |
| A6 | `s03a_report.py:230-296` | Vòng dựng nhóm viết cho nhiều nhóm nhưng `group_key` luôn là `'all'`. Tiêu đề nhóm, cộng nhóm ở Python, JS và PDF không bao giờ chạy. Dữ liệu dòng và nhóm mang các khoá thừa chép từ báo cáo kho (`qty_in`, `value_in`, `unit_price`, `opening`, `closing`…). |
| A7 | `s03a_report.py:314-325` | Action dự phòng của drill-down không lọc theo công ty. |
| A8 | `s03a_report.py:33`, `s03a_report.xml` | `_get_pdf_template()` và file template là code chết sau khi nền tảng bỏ đường QWeb và tự hiển thị bảng. |
| A9 | Toàn module | Chuỗi tiếng Việt viết thẳng; nhãn "Cộng" dựng ở JS. Không có test. |
| A10 | `s03a_report.py`, `fg_vn_report_s03b/models/s03b_report.py` | Quy tắc ghép tên chứng từ và thứ tự (bút toán chính, ngân hàng trước tiền mặt) được viết hai lần: bằng Python ở S03a, bằng SQL cộng Python ở S03b. `vn_payment_print` có bản thứ ba. |

Giới hạn của 19.0 được xử lý ở đợt này: sổ nạp mọi dòng của kỳ vào bộ nhớ và màn hình hiển thị hết, không phân trang. Phương án ở mục 3b.

## 2. Khác biệt 19.0 → 20.0 ảnh hưởng riêng tới S03a

| # | Khác biệt | Chỗ bị ảnh hưởng | Mức |
|---|---|---|---|
| E1 | `ir.model.access` → `ir.access` | `security/ir.model.access.csv` | chặn |
| E2 | OWL 3; nền tảng tự hiển thị bảng | `s03a_report.js`, `s03a_report.xml` | chặn |
| E3 | Nền tảng bỏ `_get_pdf_template()`; renderer PDF nhận `env` | `s03a_report.py`, `s03a_pdf.py` | cần sửa |
| E4 | `fg_vn_transfer_account` 20.0: danh sách tài khoản được ẩn, lấy qua `company._fg_get_hidden_transfer_accounts()` | Phần ghép cặp | cần sửa |

Đã kiểm tra và **không đổi** trên lõi 20.0: `account.move` có `name`, `date`, `invoice_date`, `ref`, `state`, `move_type`, `journal_id`, `company_id`; `account.move.line` có `name`, `debit`, `credit`, `account_id`, `partner_id`, `full_reconcile_id`, `display_type`; `account.journal.type`; mã tài khoản đọc qua `code_store->>'<id công ty gốc>'`.

Không có khác biệt lõi mới nào phải ghi vào vault.

## 3. Quyết định thiết kế (đã chốt)

| # | Vấn đề | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Bộ lọc (A1) | Cho bốn bộ lọc có tác dụng. `journal_ids` và `move_type` lọc bút toán. `account_ids` và `partner_ids` lọc **dòng**: chỉ dòng ghi vào tài khoản được chọn, hoặc của đối tác được chọn, mới hiện. Dòng Cộng là tổng các dòng đang hiện, nên Nợ có thể khác Có. Cả bốn có trên wizard và trên menu bộ lọc của màn hình. | Đã chốt. |
| 2 | Tìm kiếm (A2) | Tìm theo dòng: số chứng từ, diễn giải, mã tài khoản. Làm ở `groupsToRows` như CDPS; ghi đè `filteredLines`. | Sổ chỉ có một nhóm. |
| 3 | Dòng không phải phát sinh (A4) | Bỏ dòng có `display_type` là `line_section`, `line_subsection`, `line_note`, và dòng có Nợ = Có = 0. | Đã chốt. |
| 4 | Tài khoản được ẩn (A5, E4) | Nhận diện theo **id** tài khoản, với tập id từ `company._fg_get_hidden_transfer_accounts()`. Quy tắc ẩn, ghép tên, thứ tự của readme mục 3 áp dụng cho mọi tài khoản trong tập. | Theo thiết kế 20.0 của `fg_vn_transfer_account`. |
| 5 | Quy tắc ghép dùng chung (A10) | Đưa vào `fg_vn_transfer_account` (20.0.1.1.0). Thiết kế ở mục 3a. | Đã chốt. |
| 6 | Cấu trúc dữ liệu (A6) | Giữ khung `[nhóm]` của nền tảng với đúng một nhóm: `{'id', 'lines', 'total': {'debit', 'credit'}, 'total_label'}`. Dòng: `id`, `move_id`, `date`, `date_display`, `move_name`, `description`, `account_code`, `debit`, `credit`. Bỏ các khoá thừa và các nhánh tiêu đề nhóm, cộng nhóm ở cả ba nơi. | Code chết. |
| 7 | Truy vấn (A3) | Câu `SQL` có tham số, không `try/except`; `flush_model()` trước khi chạy. Lọc trên các cột có sẵn của `account_move_line` (`date`, `parent_state`, `company_id`, `journal_id`, `move_name`) để dùng index `(date, move_name, id)` và chỉ nối `account_move` khi cần `invoice_date`, `ref`, `move_type`. | Lỗi phải hiện ra; truy vấn nhẹ hơn. |
| 11 | Sổ dài | Tải dần, theo mục 3b. Thứ tự dòng phụ thuộc quy tắc ghép nên máy chủ sắp xếp ở mức **bút toán** trước rồi mới lấy dòng: (1) một câu `GROUP BY move_id` lấy ngày, số, loại sổ nhật ký và số dòng hiển thị của từng bút toán trong kỳ; (2) lấy liên kết ghép cho các bút toán có dòng bị ẩn; (3) sắp xếp bút toán ở Python; (4) chọn các bút toán phủ đoạn dòng cần tải, không cắt ngang một bút toán; (5) lấy dòng của riêng các bút toán đó. Tổng cộng tính bằng một câu `SUM`. | Mỗi lần tải chỉ dựng 500 dòng; bước (1) chỉ trả một hàng cho mỗi bút toán. |
| 8 | Nhãn | "Cộng" do máy chủ trả về (`total_label`). Tên sổ, nhãn cột qua `_()`. `_get_report_code()` trả `_("Form No. S03a-DNN")` (dịch: "Mẫu số S03a-DNN"); `_get_export_filename_code()` trả `'S03a-DNN'`. | Quy ước chung. Tên file hiện là `Mẫu_số_S03a-DNN_…`; nay là `S03a-DNN_…`. |
| 9 | Drill-down (A7) | Mở bút toán theo `move_id`. Bỏ action dự phòng liệt kê bút toán của kỳ. | Màn hình chỉ gọi drill-down từ dòng, luôn có `move_id`. |
| 10 | Kỳ mặc định, hướng giấy | Giữ: quý hiện tại, A4 đứng. | Như 19.0. |

## 3a. Quy tắc ghép dùng chung trong `fg_vn_transfer_account`

Mục tiêu: một nơi duy nhất trả lời hai câu hỏi mà S03a, S03b và sau này `vn_payment_print` đều hỏi, với cùng một tập tài khoản được ẩn của công ty.

| Câu hỏi | Hàm | Ai dùng |
|---|---|---|
| Các bút toán này nối với những bút toán nào qua dòng bị ẩn, mang số chứng từ gì, xếp ở đâu? | `account.move._fg_get_transfer_links()` | S03a, S03b |
| Dòng này đối ứng với tài khoản được ẩn; tài khoản thật ở đầu bên kia là gì? | Không thuộc module này: cần dữ liệu của `fg_account_counterpart`, nên nằm ở S03b (`fg_vn_report_s03b/PLAN.md`). | S03b |

### `account.move._fg_get_transfer_links()`

Gọi trên một recordset bút toán của cùng một công ty. Trả về `{move_id: link}` cho **mọi** bút toán của recordset; bút toán không nối với ai nhận giá trị mặc định, nên bên gọi không phải rẽ nhánh.

| Khoá của `link` | Kiểu | Ý nghĩa |
|---|---|---|
| `display_name` | chuỗi | Số chứng từ để in: tên bút toán, hoặc `chính (các bút toán còn lại, xếp theo tên)`. |
| `sort_key` | tuple | Khoá sắp xếp của bút toán trên sổ. |
| `linked_move_ids` | list id | Các bút toán nối với nó, kể cả bút toán nằm ngoài recordset. Rỗng nếu không nối với ai. |
| `hidden_line_ids` | list id | Các dòng của bút toán bị ẩn khỏi sổ: ghi vào tài khoản được ẩn và đã đối soát hết. |

Quy tắc, lấy nguyên từ `note.md` của hai sổ 19.0:

1. **Dòng bị ẩn:** `account_id` thuộc `company._fg_get_hidden_transfer_accounts()` và có `full_reconcile_id`.
2. **Hai bút toán nối với nhau** khi mỗi bên có một dòng bị ẩn trên cùng tài khoản, cùng `full_reconcile_id`, ngược chiều Nợ/Có. Điều kiện ngược chiều tránh nối nhầm các phiếu cùng gộp vào một lần nộp.
3. **Cụm:** các bút toán nối với nhau trực tiếp hoặc qua bút toán khác.
4. **Khoá sắp xếp:** `(ngày, tên nhỏ nhất trong các bút toán cùng ngày của cụm, ngân hàng=0 / tiền mặt=1 / khác=2, mã tài khoản nhỏ nhất không thuộc tập được ẩn, tên)`.
5. **Bút toán chính của cụm:** bút toán có khoá sắp xếp nhỏ nhất. Mọi bút toán của cụm mang cùng `display_name`.
6. **Thiết lập tắt, hoặc danh sách rỗng:** mọi bút toán nhận `display_name` là tên của nó, `linked_move_ids` và `hidden_line_ids` rỗng, `sort_key` là `(ngày, tên, 2, '', tên)`.

Thực hiện: hai câu SQL (các cặp nối; thông tin của mọi bút toán liên quan), phần gom cụm và đặt tên ở Python. Số câu SQL không phụ thuộc số bút toán. Recordset lớn được chia lô theo `id` ở bên trong hàm.

Dễ bảo trì:

- Mỗi quy tắc 1–5 là một hàm riêng có tên (`_fg_transfer_pairs`, `_fg_transfer_clusters`, `_fg_transfer_sort_key`…), để đổi một quy tắc không phải đọc cả khối.
- Test nằm trong `fg_vn_transfer_account`, mỗi quy tắc một test, cộng các tình huống của `note.md`: một phiếu một lần nộp; nhiều phiếu một lần nộp; hai ngân hàng; khác ngày; bút toán kia ngoài tập; dòng chưa đối soát; thiết lập tắt; hai tài khoản được ẩn.
- Readme của module thêm mục mô tả quy tắc bằng lời; hai sổ chỉ dẫn chiếu tới đó.

## 3b. Sổ dài: tải dần

### Vì sao sổ chậm trên dữ liệu lớn

Cách làm của 19.0, và của kế hoạch này trước khi có mục này, là: máy chủ đọc mọi dòng của kỳ, gửi hết về trình duyệt, trình duyệt dựng một dòng bảng cho mỗi dòng sổ. Chi phí của từng bước tăng theo số dòng:

| Bước | Tăng theo | Ghi chú |
|---|---|---|
| Truy vấn SQL | số dòng của kỳ | Có index theo ngày; ít khi là chỗ nghẽn. |
| Dựng dữ liệu ở Python, đổi sang JSON | số dòng | Mỗi dòng một dict khoảng mười khoá. |
| Truyền về trình duyệt | số dòng | Ước 200–300 byte mỗi dòng trước khi nén. |
| Dựng bảng trên trình duyệt | số dòng × 8 ô | **Chỗ nghẽn chính.** Trình duyệt phải tạo và bố trí mọi ô, kể cả ô chưa cuộn tới. |

Một quý có 100.000 dòng nghĩa là khoảng 25 MB dữ liệu và 800.000 ô bảng. Các con số trên là ước lượng từ cấu trúc code, chưa đo; giai đoạn 0 có bước đo.

### Phương án (đã chốt)

Thêm cơ chế **tải dần** vào nền tảng (`fg_vn_accounting_reports` 20.0.1.1.0), báo cáo nào cần thì bật:

1. Khi mở sổ, máy chủ đếm số dòng của kỳ bằng một câu `COUNT`.
2. **Dưới ngưỡng** (mặc định 2.000 dòng): làm như cũ, gửi hết. Sổ nhỏ không thay đổi gì.
3. **Trên ngưỡng:** máy chủ chỉ gửi phần tổng hợp (tính bằng SQL) và 500 dòng đầu. Cuối bảng có dòng "Đã hiện 500 / 12.340 dòng · Xem thêm"; bấm thì tải 500 dòng tiếp theo.
4. Ô tìm kiếm, khi sổ đang tải dần, tìm ở máy chủ trên cả kỳ chứ không chỉ trên các dòng đã tải.
5. Excel và PDF luôn xuất cả sổ, không phụ thuộc phần đã tải trên màn hình.

Ngưỡng và cỡ mỗi lần tải là tham số hệ thống (`fg_vn_accounting_reports.lazy_line_threshold`, `fg_vn_accounting_reports.lazy_chunk_size`).

| Phương án | Nội dung | Vì sao không chọn |
|---|---|---|
| Tải dần (đã chọn) | Như trên | |
| Chỉ dựng các dòng đang nhìn thấy (cuộn ảo) | Vẫn tải hết dữ liệu, trình duyệt chỉ dựng phần trong khung nhìn | Bỏ được bước dựng bảng nhưng giữ nguyên ba bước còn lại; phải viết lại bảng chung với chiều cao dòng cố định, trong khi dòng sổ có diễn giải dài ngắn khác nhau. |
| Phân trang có số trang | Trang 1, 2, 3… | Cùng chi phí với tải dần; tải dần giữ được thói quen cuộn một bảng liền. Đổi sang kiểu này sau cũng dễ vì máy chủ đã hỗ trợ `offset`. |
| Giới hạn độ dài kỳ | Không cho xem quá một tháng | Không giải quyết được đơn vị có nhiều phát sinh trong một tháng. |

### Việc ở nền tảng

| Phần | Nội dung |
|---|---|
| `vn.abstract.report` | Báo cáo bật tải dần bằng cách khai ba hook: `_count_lines(options)`, `_get_group_summaries(options)` (nhóm với số tổng hợp, chưa có dòng), `_get_group_lines(options, group_id, offset, limit)`. Hàm công khai mới `get_group_lines(options, group_id, offset)` kiểm tra quyền, chuyển ngôn ngữ, trả `{lines, offset, line_count}`. `_get_lines()` của báo cáo vẫn trả cả sổ và là đường của Excel, PDF và của sổ dưới ngưỡng. |
| `get_report_data()` | Trả thêm `lazy: true/false`. Khi tải dần, mỗi nhóm có `line_count` và `lines` chỉ gồm phần đầu (hoặc rỗng nếu nhóm chưa mở). |
| Component cơ sở | Giữ các dòng đã tải của từng nhóm trong `state`; hàm `loadMoreLines(group)`; kiểu dòng mới `load_more` trong bảng chung; khi `lazy`, ô tìm kiếm gửi `options.search` lên máy chủ sau khi người dùng ngừng gõ; nút "Mở rộng tất cả" bị ẩn. |
| Test | Báo cáo giả trong test của nền tảng bật tải dần: dưới ngưỡng trả hết; trên ngưỡng trả phần đầu; `get_group_lines` trả đúng đoạn; kiểm tra quyền. |
| Tài liệu | Thêm mục "Tải dần" vào `doc/DEVELOPER.md`. |

### Xuất file với sổ rất dài

Excel và PDF dựng cả sổ trong bộ nhớ của máy chủ trong một request. PDF chậm hơn nhiều vì ReportLab phải đo và ngắt trang từng dòng. Đã chốt: đo ở giai đoạn 0, rồi đặt một giới hạn số dòng cho PDF (tham số hệ thống `fg_vn_accounting_reports.pdf_line_limit`); vượt giới hạn thì báo người dùng thu hẹp kỳ hoặc bộ lọc thay vì để request chạy tới khi hết thời gian. Kiểm tra giới hạn nằm ở `get_pdf_rl()` của nền tảng, dùng `_count_lines()` của báo cáo; báo cáo không khai `_count_lines()` thì không bị giới hạn. Con số giới hạn chỉ chốt sau khi đo.

## 4. Cấu trúc module sau khi chuyển

```
fg_vn_report_s03a/
├── __init__.py
├── __manifest__.py                 depends: fg_vn_accounting_reports, fg_vn_transfer_account
├── readme.md
├── PLAN.md
├── models/
│   ├── s03a_report.py              vn.report.s03a
│   └── s03a_pdf.py                 S03aPDF
├── wizard/
│   ├── s03a_wizard.py              vn.report.s03a.wizard
│   └── s03a_wizard_views.xml
├── views/s03a_report_views.xml     client action, menu
├── security/ir.access.csv
├── i18n/                           .pot và vi.po
├── static/
│   ├── description/index.html
│   ├── src/js/s03a_report.js
│   └── tests/tours/s03a_report_tour.js
└── tests/
    ├── common.py                   bút toán mẫu, gồm cặp nộp tiền qua tài khoản trung chuyển
    ├── test_lines.py
    ├── test_transfer.py
    ├── test_exports.py
    ├── test_wizard.py
    └── test_ui.py
```

So với 19.0: bỏ `static/src/xml/`, `note.md`, `security/ir.model.access.csv`; thêm `i18n/`, `tests/`, `static/description/`, `static/tests/`.

## 5. Việc cần làm theo file

### `models/s03a_report.py`

| Hàm | Việc cần làm |
|---|---|
| `_get_report_name()`, `_get_report_code()`, `_get_columns()` | Nhãn qua `_()`; thêm `_get_export_filename_code()` (quyết định 8). |
| `_get_pdf_template()` | Bỏ. |
| `_get_pdf_rl_renderer()` | Giữ; import đầu file. |
| `_format_date_display()` | Giữ. |
| `_get_line_where(options)` | **Mới**: điều kiện SQL dùng chung cho đếm, tổng và lấy dòng: công ty, kỳ, đã ghi sổ, bốn bộ lọc (quyết định 1), bỏ dòng không phải phát sinh (quyết định 3), và ô tìm kiếm khi sổ đang tải dần. |
| `_query_lines(options, move_ids=None)` | **Mới**: lấy dòng theo `_get_line_where`, giới hạn theo `move_ids` khi tải dần; lấy thêm `aml.account_id`. |
| `_get_lines(options)` | Viết gọn lại: gọi `_query_lines`; lấy tập tài khoản được ẩn; lấy tên ghép và khoá sắp xếp (quyết định 5); bỏ dòng bị ẩn; trả một nhóm (quyết định 6). |
| Phần ghép cặp, tên ghép, khoá sắp xếp (bước 2–6 trong `_get_lines` cũ) | Chuyển sang `fg_vn_transfer_account` (mục 3a). |
| `_count_lines()`, `_get_group_summaries()`, `_get_group_lines()` | **Mới**: ba hook tải dần (quyết định 11). |
| `_get_drill_down_action()` | Quyết định 9. |
| `_groups_to_xlsx_rows()` | Bỏ nhánh nhóm; nhãn cộng lấy từ `total_label`. |

### `fg_vn_transfer_account`

Thêm `models/account_move.py` với `_fg_get_transfer_links()` theo mục 3a:

1. Lấy các dòng của tập bút toán ghi vào tài khoản được ẩn và có `full_reconcile_id`.
2. Tìm các bút toán khác có dòng cùng `full_reconcile_id` trên cùng tài khoản (kể cả bút toán ngoài tập, để lấy tên).
3. Gom thành các cụm bút toán nối với nhau.
4. Với mỗi cụm: bút toán chính là bút toán có khoá sắp xếp nhỏ nhất; tên ghép `chính (còn lại, xếp theo tên)`.
5. Khoá sắp xếp: `(ngày, tên nhỏ nhất trong các bút toán cùng ngày của cụm, ngân hàng=0 / tiền mặt=1 / khác=2, mã tài khoản nhỏ nhất không thuộc tập được ẩn, tên)`.

Test đi kèm trong module đó; phiên bản 20.0.1.1.0; cập nhật readme mục 3 và `README.md` của repo.

### `models/s03a_pdf.py`

`self.env._()` cho nhãn cột và "Cộng" (hoặc lấy `total_label` từ dữ liệu). Bỏ nhánh tiêu đề nhóm và cộng nhóm. Giữ: cột theo hướng giấy, cộng chuyển trang cột 5 và 6, nhãn cộng chuyển trang ở cột Diễn giải, phần "Sổ này bao gồm … trang".

### `wizard/s03a_wizard.py`, `wizard/s03a_wizard_views.xml`

Giữ các trường; nhãn và lựa chọn tiếng Anh; `check_company=True` cho `journal_ids`, `account_ids`. Form thêm `report_lang`; nút theo kiểu của CDPS.

### `security/ir.access.csv`

Một dòng cho `vn.report.s03a.wizard`, nhóm `account.group_account_user`, thao tác `cru`.

### `static/src/js/s03a_report.js`

| Phần | Việc cần làm |
|---|---|
| Đầu file, `static template` | Bỏ `@odoo-module` và `static template`. |
| `getFilterDefinitions()` | Bốn bộ lọc: `journal_ids`, `account_ids`, `partner_ids` (nhiều-nhiều), `move_type` (lựa chọn). Nhãn qua `_t()`. |
| `getSearchKeys()` | `['move_name', 'description', 'account_code']`. |
| `filteredLines` | Trả nguyên nhóm (tìm kiếm làm ở `groupsToRows`). |
| `groupsToRows()` | Một vòng qua các dòng của nhóm duy nhất; khi sổ không tải dần thì lọc theo ô tìm kiếm ở trình duyệt; thêm dòng "Xem thêm" của nền tảng khi còn dòng chưa tải; thêm dòng cộng với `total_label` và số tổng do máy chủ trả về. |
| `getLineMenuItems()` | Giữ; nhãn qua `_t()`. |

### `tests/`

| File | Nội dung kiểm tra |
|---|---|
| `test_lazy.py` | Trên ngưỡng: lần đầu trả 500 dòng và tổng của cả kỳ; `get_group_lines` trả đoạn tiếp theo, không lặp, không sót, không cắt ngang bút toán; thứ tự khớp với sổ tải hết; tìm kiếm ở máy chủ; số câu SQL của một lần tải không tăng theo số dòng của kỳ. |
| `test_lines.py` | Thứ tự theo ngày rồi số chứng từ; tài khoản nằm đúng cột Nợ hoặc Có; diễn giải lấy nhãn dòng rồi tới tham chiếu; ngày hoá đơn trong ngoặc; bút toán nháp, dòng ghi chú và dòng bằng 0 không có; tổng cộng; từng bộ lọc trong bốn bộ lọc, và bộ lọc tài khoản, đối tác chỉ giữ dòng khớp; công ty khác không lẫn vào. |
| `test_transfer.py` | Thiết lập tắt: hai bút toán hiện đủ bốn dòng. Thiết lập bật: hai dòng trung chuyển bị ẩn, tên ghép, ngân hàng đứng trước; dòng chưa đối soát vẫn hiện; nhiều phiếu gộp một lần nộp; hai bút toán khác ngày; bút toán kia ngoài kỳ; hai tài khoản được ẩn. |
| `test_exports.py` | Excel: tiêu đề, cột, dòng cộng. PDF: hai hướng giấy, cộng chuyển trang khi nhiều trang, phần "Sổ này bao gồm … trang", bản tiếng Việt. |
| `test_wizard.py` | Mặc định theo quý, tuỳ chọn gửi đi, người không có quyền bị từ chối. |
| `test_ui.py` | Tour: mở sổ, tìm kiếm, bộ lọc sổ nhật ký, mở bút toán và quay lại. |

## 6. Thay đổi hành vi so với 19.0

1. Bốn bộ lọc có tác dụng; lọc theo tài khoản hoặc đối tác thì sổ chỉ còn các dòng khớp và Nợ có thể khác Có (quyết định 1).
2. Ô tìm kiếm lọc theo dòng (quyết định 2).
3. Dòng ghi chú, tiêu đề mục và dòng bằng 0 không còn trên sổ (quyết định 3).
4. Ẩn theo danh sách tài khoản do đơn vị chọn (quyết định 4).
5. Tên file xuất bắt đầu bằng `S03a-DNN` (quyết định 8).
6. Sổ trên 2.000 dòng hiện 500 dòng đầu và tải thêm khi người dùng yêu cầu (quyết định 11).

## 7. Các giai đoạn

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Dữ liệu đo: một công ty thử với khoảng 50.000 bút toán (150.000 dòng) trong một quý, có các cặp nộp tiền qua tài khoản trung chuyển. Đo các truy vấn dự kiến của S03a và S03b bằng `EXPLAIN ANALYZE`. | Có bảng số đo trong kế hoạch này; ngưỡng và cỡ mỗi lần tải được xác nhận hoặc điều chỉnh. |
| 1 | `fg_vn_transfer_account` 20.0.1.1.0: `_fg_get_transfer_links()` (mục 3a). | Test của module chạy qua. |
| 2 | Nền tảng 20.0.1.1.0: tải dần (mục 3b). | Test mới và toàn bộ test cũ của nền tảng, của CDPS chạy qua. |
| 3 | Khung module; `s03a_report.py`: điều kiện lọc, sắp xếp bút toán, ẩn và ghép, tải dần. | `test_lines`, `test_transfer`, `test_lazy` chạy qua. |
| 4 | `s03a_pdf.py`, dòng Excel, wizard. | `test_exports`, `test_wizard` chạy qua. |
| 5 | `s03a_report.js`, tour. | Tour chạy qua trên sổ nhỏ và trên sổ tải dần; console không có lỗi hay cảnh báo. |
| 6 | Đo lại trên dữ liệu của giai đoạn 0: mở sổ, tải thêm, tìm kiếm, Excel, PDF. `i18n/vi.po`, `static/description/index.html`, dòng trong `README.md` của repo. | Số đo ghi vào kế hoạch; sổ in ra tiếng Việt đầy đủ. |

## 8. Điểm cần xác nhận

Không còn. Hai con số sẽ được xác nhận lại bằng số đo ở giai đoạn 0, trước khi viết code của sổ: ngưỡng tải dần (đang là 2.000 dòng, mỗi lần 500) và giới hạn số dòng khi in PDF.

## 9. Số đo

Đo ngày 2026-10-11 trên máy phát triển (Windows 11, PostgreSQL 16), một công ty có 61.000 bút toán và 184.000 dòng bút toán, trong đó quý đo có 52.000 bút toán, 154.000 dòng, gồm 1.000 cặp nộp tiền qua tài khoản trung chuyển đã đối soát. Số trong bảng là lần nhanh nhất trong ba lần chạy, tính ở máy chủ (chưa gồm thời gian trình duyệt dựng bảng).

| Thao tác trên sổ nhật ký chung | Không ẩn | Có ẩn tài khoản trung chuyển |
|---|---|---|
| Đếm dòng của quý | 0,07 giây | 0,07 giây |
| Tính dòng Cộng | 0,08 giây | 0,09 giây |
| Sắp xếp 52.000 bút toán | 0,24 giây | 0,38 giây |
| **Mở sổ (500 dòng đầu)** | **0,47 giây**, 0,11 MB | **0,61 giây**, 0,11 MB |
| Xem thêm, từ dòng 500 | 0,25 giây | 0,39 giây |
| Xem thêm, từ dòng 100.000 | 0,26 giây | 0,39 giây |
| Tìm kiếm trên cả quý | 0,93 giây | 0,93 giây |
| Tải cả sổ một lần, như 19.0 | 1,6 giây, 32,8 MB | 1,8 giây, 32,4 MB |

| Xuất file | Thời gian | Kích thước |
|---|---|---|
| Excel cả quý, 152.000 dòng | 10 giây | 4,9 MB |
| PDF một tuần, 11.700 dòng | 14 giây | 1,5 MB |
| PDF một tháng, 50.200 dòng | 59 giây | 6,3 MB |

Kết luận:

- **Ngưỡng 2.000 dòng và mỗi lần 500 dòng được giữ.** Mở sổ và mỗi lần "Xem thêm" đều dưới một giây, và không chậm đi khi đi sâu vào sổ. Lượng dữ liệu gửi về giảm từ 33 MB xuống 0,11 MB.
- Chi phí cố định của mỗi lần tải là bước sắp xếp bút toán (0,24 đến 0,38 giây cho 52.000 bút toán), vì máy chủ không giữ trạng thái giữa hai lần gọi. Nếu về sau cần nhanh hơn với kỳ lớn hơn nhiều, đây là chỗ để lưu tạm.
- **PDF tốn khoảng 1,2 mili giây mỗi dòng.** Giới hạn mặc định `fg_vn_accounting_reports.pdf_line_limit` đặt là **30.000 dòng**, tương ứng khoảng 35 giây; đặt 0 để bỏ giới hạn.
- Tải cả sổ một lần ở máy chủ chỉ mất 1,6 giây: phần chậm của 19.0 không nằm ở truy vấn mà ở 33 MB dữ liệu và hơn một triệu ô bảng trình duyệt phải dựng. Thời gian dựng bảng trên trình duyệt chưa được đo.
