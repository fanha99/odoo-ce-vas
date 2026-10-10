# Kế hoạch viết `fg_account_counterpart` cho Odoo 20.0

Viết mới hoàn toàn, dựa trên code Odoo 20.0, không dùng lại code của các phiên bản trước.

`readme.md` là bản mô tả nghiệp vụ và là nguồn gốc của kế hoạch này: readme nói module phải làm gì, kế hoạch nói làm bằng cách nào. Readme không định nghĩa model, trường hay hàm; tất cả những thứ đó nằm ở đây. Khi hai tài liệu lệch nhau thì sửa kế hoạch theo readme.

Trạng thái: **cả 6 giai đoạn đã xong**, 33 test qua trên Odoo 20.0. Việc còn lại: bút toán âm đang neo (`TODO(storno)`) và các điểm chờ kế toán xác nhận ở mục 6.

## 1. Quyết định thiết kế

| # | Vấn đề | Quyết định | Lý do |
|---|---|---|---|
| 1 | Sinh đối ứng lúc nào | Khi ghi sổ (`account.move._post`). Xoá khi đưa về nháp (`button_draft`). | Bút toán đã ghi sổ không đổi được số tiền, nên đối ứng luôn khớp. Bút toán nháp còn sửa được nên không giữ đối ứng. |
| 2 | Xác định bên Nợ/Có | Theo cột có số liệu (`debit` hay `credit`), không theo dấu của `balance`. | Odoo 20 có bút toán âm (storno): phát sinh Nợ có thể mang số âm nhưng vẫn là bên Nợ. |
| 3 | Thuật toán ghép Nợ ↔ Có | Ghép 3 lượt theo readme mục 2, duyệt dòng Nợ theo `id` tăng dần. Chi tiết hiện thực ở mục 4. | Yêu cầu của kế toán. |
| 4 | Làm tròn | Làm tròn theo tiền tệ; chênh lệch làm tròn dồn vào dòng Có cuối cùng của lần phân bổ. | Yêu cầu của kế toán; tổng đối ứng của mỗi dòng Nợ luôn khớp. |
| 5 | Kiểu `countered_amt` | `Monetary` theo tiền tệ công ty; `countered_amt_currency` theo nguyên tệ. | Hiển thị và làm tròn đúng. |
| 6 | Trường trên phát sinh | Trường tính toán có lưu, phụ thuộc vào bản ghi `account.move.line.ctp`. | Tìm kiếm và nhóm được trên phát sinh. |
| 7 | Phân quyền | File `security/ir.access.csv` (định dạng mới của Odoo 20). Người dùng chỉ đọc; bản ghi đối ứng được tạo bằng `sudo`. | Người có quyền Invoicing ghi sổ được mà không cần quyền ghi trên model kỹ thuật. |
| 8 | Dữ liệu cũ khi cài | `pre_init_hook` tạo sẵn cột với giá trị mặc định; không tự sinh đối ứng. | Tránh để ORM tính lại toàn bộ phát sinh lúc cài. Dữ liệu cũ xử lý bằng trình tạo đối ứng. |
| 9 | Dòng không đối ứng | Section/subsection/note và phát sinh có số tiền bằng 0 không sinh đối ứng và được tính là "đối ứng hoàn toàn". | Không có gì để đối ứng; không làm bút toán kẹt ở trạng thái "một phần". |
| 12 | Bút toán âm (storno) | Tạm neo lại, xử lý sau. Bút toán có dòng Nợ/Có mang số âm chưa sinh đối ứng và ở trạng thái "chưa đối ứng". Đánh dấu `TODO(storno)` trong code. | Kế toán chưa có quy định cho trường hợp này. |
| 10 | Thứ tự dòng | Chỉ dùng `id` (thứ tự tạo dòng), không dùng `sequence`. Kéo thả sắp lại dòng nằm ngoài phạm vi module này. | Thứ tự chỉ ảnh hưởng kết quả khi đối tác lẫn lộn hoặc ở phần làm tròn. |
| 11 | Ngoại tệ | Thêm `countered_amt_currency` trên `account.move.line.ctp`, tính song song với `countered_amt` theo cùng cách. | Yêu cầu của kế toán. |

## 2. Cấu trúc module

```
fg_account_counterpart/
├── __init__.py                       pre_init_hook
├── __manifest__.py
├── models/
│   ├── account_move_line_ctp.py      model mới account.move.line.ctp
│   ├── account_move_line.py          4 trường đối ứng trên phát sinh
│   └── account_move.py               trạng thái + bộ máy sinh đối ứng
├── wizard/
│   ├── account_counterpart_generate.py
│   └── account_counterpart_generate_views.xml
├── security/ir.access.csv
├── i18n/
│   ├── fg_account_counterpart.pot    mẫu dịch, xuất bằng `odoo-bin i18n export`
│   └── vi.po                         bản dịch tiếng Việt
├── static/description/index.html     trang mô tả module trong Odoo
├── views/
│   ├── account_move_line_ctp_views.xml   list, pivot, search, menu
│   ├── account_move_line_views.xml       list, form, search của phát sinh
│   └── account_move_views.xml            form, search của bút toán, action tạo lại
└── tests/
    ├── common.py
    ├── test_counterpart.py           26 test
    └── test_counterpart_generate.py  7 test
```

Menu:
- Kế toán › Review › Control › **Counterparts**: danh sách và pivot Tài khoản Nợ × Tài khoản Có.
- Kế toán › Configuration › Accounting › **Generate Counterparts**: chỉ nhóm quản lý kế toán.

## 3. Danh sách hàm theo model

### `account.move.line.ctp` (model mới)

Trường: `dr_aml_id`, `cr_aml_id`, `countered_amt`, `countered_amt_currency`, `currency_id`, và các trường related có lưu để báo cáo: `move_id`, `date`, `journal_id`, `company_id`, `company_currency_id`, `dr_account_id`, `cr_account_id`.

Ràng buộc SQL (đã viết): hai phát sinh phải khác nhau, số tiền khác 0, mỗi cặp chỉ có một bản ghi.

| Hàm | Việc cần làm | Giai đoạn |
|---|---|---|
| `_check_same_move()` | Hai phát sinh cùng một bút toán, phát sinh thứ nhất bên Nợ, thứ hai bên Có. | 1, xong |
| `_get_counterpart_values(countered_aml)` | Trả về một cặp đối ứng nhìn từ phát sinh còn lại; dùng bởi `_get_counterparts`. | 2, xong |
| `_compute_display_name()` | Tên hiển thị dạng "131 / 5111: 100". | 4, xong |

### `account.move.line` (mở rộng)

Trường: `ctp_dr_ids`, `ctp_cr_ids`, `countered_aml_ids`, `countered_account_ids`, `countered_account_codes`, `countered_amt`, `countered_status` (none / partially / fully).

`countered_account_codes` là chuỗi mã tài khoản đối ứng, ví dụ "511, 33311". Các view hiển thị trường này thay cho `countered_account_ids` để chỉ thấy mã, không kèm tên tài khoản. Trường không lưu trong database (mã tài khoản phụ thuộc công ty), nên tìm kiếm và nhóm vẫn dùng `countered_account_ids`.

| Hàm | Việc cần làm | Giai đoạn |
|---|---|---|
| `_ctp_is_counterable()` | Phát sinh có tham gia đối ứng không. | 1, xong |
| `_ctp_side()` | Trả về `'dr'`, `'cr'` hoặc `False`. | 1, xong |
| `_ctp_amount()` | Số tiền cần đối ứng, có dấu. | 1, xong |
| `_compute_countered()` | Tính 4 trường đối ứng từ các bản ghi ctp. | 2, xong |
| `_get_counterparts()` | Hàm công khai cho module khác (mục 4b). | 2, xong |
| `_compute_countered_account_codes()` | Ghép mã các tài khoản đối ứng thành chuỗi, sắp theo mã. | 2, xong |
| `action_view_counterparts()` | Mở danh sách đối ứng của phát sinh. | 4, xong |

### `account.move` (mở rộng)

Trường: `countered_status`.

| Hàm | Việc cần làm | Giai đoạn |
|---|---|---|
| `_compute_countered_status()` | Tổng hợp trạng thái từ các phát sinh đối ứng được. Bút toán đã ghi sổ mà không có gì để đối ứng là "hoàn toàn". | 2, xong |
| `_post()` | Gọi `_ctp_generate()` cho bút toán vừa ghi sổ. | 3, xong |
| `button_draft()` | Gọi `_ctp_remove()`. | 3, xong |
| `_ctp_generate(regenerate=False)` | Mặc định chỉ xử lý bút toán đã ghi sổ chưa đối ứng hoàn toàn: xoá đối ứng dở dang rồi tạo lại. `regenerate=True` xử lý cả bút toán đã đủ. Tạo trong một lần `create`, bằng `sudo`. | 3, xong |
| `_ctp_remove()` | Xoá toàn bộ đối ứng của bút toán. | 3, xong |
| `_ctp_prepare_vals_list()` | Sắp phát sinh theo `id`, tách Nợ/Có, trả về dữ liệu để tạo ctp. Bút toán có số âm trả về rỗng (`TODO(storno)`). | 3, xong |
| `_ctp_allocate(dr_items, cr_items, currency)` | Điều phối 3 lượt ghép (mục 4). Hàm thuần, không đụng database. | 3, xong |
| `_ctp_find_exact_match(dr_item, cr_items, currency)` | Lượt 1: tìm dòng Có bằng tiền, cùng đối tác, kèm ngoại lệ `id` liền kề. | 3, xong |
| `_ctp_distribute(dr_item, cr_items, currency)` | Lượt 2 và 3: phân bổ theo tỷ lệ trên một nhóm dòng Có, dồn chênh lệch làm tròn vào dòng cuối. | 3, xong |
| `action_ctp_regenerate()` | Tạo lại đối ứng cho các bút toán đã ghi sổ đang chọn (menu Action, chỉ nhóm quản lý kế toán). | 4, xong |
| `action_view_counterparts()` | Mở danh sách đối ứng của bút toán; có nút "Counterparts" trên form bút toán đã ghi sổ. | 4, xong |

### `account.counterpart.generate` (wizard)

Trường: `company_id`, `mode` (missing / all), `journal_ids`, `date_from`, `date_to`, `move_count`.

| Hàm | Việc cần làm | Giai đoạn |
|---|---|---|
| `_get_moves_domain()` | Điều kiện lọc bút toán cần xử lý: công ty, đã ghi sổ, sổ nhật ký, khoảng ngày; chế độ "missing" chỉ lấy bút toán chưa đối ứng hoàn toàn. | 5, xong |
| `_compute_move_count()` | Số bút toán sẽ xử lý, để xem trước. | 5, xong |
| `_generate_batch(moves)` | Sinh đối ứng cho một lô, tính lại các trường đối ứng của cả lô (kể cả dòng bằng 0 của dữ liệu cũ), flush và xoá cache. | 5, xong |
| `action_generate()` | Chia lô 1000 bút toán, chạy, rồi thông báo số bút toán đã xử lý và số bút toán vẫn chưa đối ứng đủ. | 5, xong |

### `__init__.py`

| Hàm | Việc cần làm | Giai đoạn |
|---|---|---|
| `_pre_init_counterpart(env)` | Tạo sẵn cột trạng thái và số tiền với giá trị mặc định. Đã viết. | xong |

## 4. Hiện thực quy tắc ghép của readme

Quy tắc ghép 3 lượt được mô tả trong `readme.md` mục 2 và minh họa bằng các nghiệp vụ ở mục 3; các quy ước còn lại nằm ở mục 4 của readme. Phần này chỉ ghi những chi tiết kỹ thuật mà readme không nêu.

- **Thứ tự tạo dòng** trong readme là `id` tăng dần của `account.move.line`. Không dùng `sequence`.
- **Dòng liền kề** (ngoại lệ lượt 1) là dòng Có có `id` bằng `id` dòng Nợ ± 1, và phải là dòng Có đầu tiên còn dư.
- **Cùng đối tác** so sánh `partner_id` của hai dòng; hai dòng cùng không có đối tác cũng tính là cùng.
- **Công thức chia tỷ lệ:** min(Nợ còn lại, tổng Có còn lại) × (Có còn lại của dòng / tổng Có còn lại). Làm tròn theo tiền tệ công ty; dòng Có cuối cùng của lần chia nhận phần còn lại.
- **Mỗi lượt duyệt hết các dòng Nợ** rồi mới sang lượt sau. Phần dư của dòng Nợ sau lượt 2 chuyển sang lượt 3.
- **Nguyên tệ:** `countered_amt_currency` được chia song song bằng cùng công thức trên số dư nguyên tệ, khi các dòng Có cùng tiền tệ với dòng Nợ. Nếu khác tiền tệ, nguyên tệ của dòng Nợ được chia theo đúng tỷ lệ số tiền hạch toán của nó.
- **Thứ tự kiểm tra ở lượt 1:** ngoại lệ dòng liền kề được xét trước, rồi mới tìm dòng Có bằng tiền cùng đối tác.
- **Một cặp chỉ có một bản ghi:** nếu cùng một cặp Nợ/Có được ghép ở hai lượt thì số tiền được cộng dồn.

Đối chiếu nghiệp vụ trong readme với test:

| Readme | Nghiệp vụ | Lượt | Test |
|---|---|---|---|
| 3.1 | Thu tiền khách hàng | 1 | `test_one_debit_one_credit` |
| 3.2 | Hóa đơn bán hàng | 2 | `test_one_debit_many_credits` |
| 3.3 | Hóa đơn mua hàng | 2 | `test_many_debits_one_credit` |
| 3.4 | Bán hàng kèm giá vốn | 1 rồi 2 | `test_exact_match_same_partner` |
| 3.5 | Trích bảo hiểm | 2 | `test_many_debits_many_credits` |
| 3.6 | Một lần chi trả hai nhà cung cấp | 3 | `test_remainder_any_partner` |
| 3.7 | Hai dòng liền nhau bằng tiền | 1 (ngoại lệ) | `test_exact_match_adjacent_ignores_partner` |
| 4 | Làm tròn, ngoại tệ, dòng bằng 0, bút toán âm | | `test_rounding`, `test_foreign_currency`, `test_zero_and_note_lines_ignored`, `test_storno` |

## 4b. Giao diện cho module khác

Các module in sổ (sổ cái, sổ chi tiết tài khoản, sổ quỹ, lưu chuyển tiền tệ) lấy dữ liệu đối ứng theo hai cách:

- **Trường có lưu trên phát sinh:** `countered_account_ids`, `countered_aml_ids`, `countered_amt`, `countered_status`. Dùng được trong điều kiện lọc và nhóm.
- **Trường hiển thị:** `countered_account_codes`, chuỗi mã tài khoản đối ứng để in thẳng lên sổ.
- **Hàm `account.move.line._get_counterparts()`:** gọi trên một tập phát sinh, trả về `{id phát sinh: [cặp đối ứng, ...]}`. Mỗi cặp là một dict gồm `aml` (phát sinh đối ứng), `account` (tài khoản đối ứng), `account_code` (mã của tài khoản đó), `amount` (số tiền hạch toán), `amount_currency` (số tiền nguyên tệ), sắp theo `id` của phát sinh đối ứng. Phát sinh không có đối ứng trả về danh sách rỗng. Module gọi không cần biết phát sinh nằm bên Nợ hay bên Có.

Ví dụ với hóa đơn ở readme mục 3.2: dòng 131 trả về (511, 100.000.000) và (33311, 10.000.000); dòng 511 trả về (131, 100.000.000).

Báo cáo trên dữ liệu lớn nên truy vấn thẳng bảng `account_move_line_ctp` (có sẵn `dr_account_id`, `cr_account_id`, `countered_amt`, `date`, `company_id`) thay vì gọi hàm cho từng phát sinh.

## 5. Các giai đoạn

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| 0 | Khung module, view, phân quyền, test giữ chỗ. | **Đã xong**: cài được trên 20.0. |
| 1 | Hàm phụ trợ trên phát sinh và ràng buộc `_check_same_move`. | **Đã xong.** |
| 2 | Hai hàm compute (phát sinh và bút toán), hàm `_get_counterparts`. | **Đã xong.** |
| 3 | Bộ máy sinh đối ứng và thuật toán ghép 3 lượt. | **Đã xong:** bảy nghiệp vụ ở readme mục 3, làm tròn, ngoại tệ, về nháp, ghi sổ lại đều qua. |
| 4 | Hoàn thiện action và tên hiển thị. | **Đã xong.** |
| 5 | Trình tạo đối ứng. | **Đã xong:** 7 test qua. Chưa thử trên database thật có dữ liệu cũ. |
| 6 | Bản dịch `i18n/vi.po`, trang mô tả `static/description/index.html`. | **Đã xong:** 64 chuỗi đã dịch, kiểm tra trên database có tiếng Việt. Thuật ngữ theo bản dịch của Odoo: "Bút toán" (journal entry), "Hạng mục bút toán" (journal item), "Sổ nhật ký" (journal). |

## 5b. Hiệu năng và giới hạn của trình tạo đối ứng

Đo trên máy phát triển với 1000 bút toán 5 dòng (3 cặp đối ứng mỗi bút toán):

- Trình tạo đối ứng: 7,5 giây cho 1000 bút toán, tức khoảng 130 bút toán mỗi giây.
- Ghi sổ 1000 bút toán: 10,9 giây có sinh đối ứng, so với 3,1 giây khi tắt bộ máy đối ứng (lần đo sau là ghi sổ lại, nên chênh lệch thật nhỏ hơn con số này).

Trình tạo đối ứng chạy toàn bộ trong một transaction của request: hoặc xong hết, hoặc không có gì thay đổi. Với database vài trăm nghìn bút toán trở lên, nên chạy theo từng sổ nhật ký hoặc từng khoảng ngày để mỗi lần không quá lâu.

## 6. Điểm cần xác nhận

1. **Đã chốt:** thuật toán ghép 3 lượt theo yêu cầu của kế toán;
2. **Bút toán âm (storno): đã neo lại**, xem quyết định 12. Các chỗ cần quay lại được đánh dấu `TODO(storno)` trong `models/account_move.py` và `tests/test_counterpart.py`.
3. **Nguyên tệ của `countered_amt_currency`:** hai dòng Nợ và Có của cùng một bút toán có thể khác tiền tệ. Code lấy tiền tệ của dòng Nợ và xử lý như mô tả ở mục 4; cần kế toán xác nhận.
4. **Lượt 2 khi nhóm cùng đối tác không đủ:** code chuyển phần dư của dòng Nợ sang lượt 3 (suy ra từ công thức min); cần kế toán xác nhận. Tương tự, khi cả ngoại lệ liền kề và điều kiện cùng đối tác đều có dòng thỏa, code ưu tiên dòng liền kề.
5. **Đã chốt:** phát sinh có số tiền bằng 0 tính là "đối ứng hoàn toàn" (quyết định 9). Lưu ý cho giai đoạn 5: cột trạng thái của dữ liệu cũ mặc định là "chưa đối ứng", nên trình tạo đối ứng phải cập nhật cả các dòng bằng 0.
6. **Đã xử lý:** `readme.md` từng gây cảnh báo khi nạp module vì Odoo đọc nó như reStructuredText. Manifest giờ có `description` riêng và trang mô tả lấy từ `static/description/index.html`. Khi thêm hoặc sửa chuỗi hiển thị, xuất lại file `.pot` rồi cập nhật `vi.po`.
