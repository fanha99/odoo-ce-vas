# Kế hoạch chuyển `fg_vn_transfer_account` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\fg_vn_transfer_account` (19.0.1.0.0, 76 dòng).
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

Trạng thái: **các quyết định đã chốt; chờ duyệt lần cuối trước khi code.** Chưa viết dòng code nào.

Module này được chuyển trước vì `fg_vn_report_cdps` phụ thuộc nó.

## 1. Phân tích code nguồn

| Thành phần | File | Nội dung |
|---|---|---|
| Trường `fg_hide_transfer_account` (Boolean, mặc định tắt) trên `res.company` | `models/res_company.py` | 16 dòng |
| Trường `related` cùng tên trên `res.config.settings` | `models/res_config_settings.py` | 10 dòng |
| Khối "Vietnam Accounting" trong trang thiết lập kế toán | `views/res_config_settings_views.xml` | 18 dòng |

Module không có logic. Bốn module đọc cờ này: `fg_vn_report_cdps`, `fg_vn_report_s03a`, `fg_vn_report_s03b`, `vn_payment_print`. Mỗi module tự viết đoạn "nếu cờ bật và công ty có `transfer_account_id` thì lấy id tài khoản đó".

Điểm cần sửa:

| # | Vấn đề |
|---|---|
| T1 | Nhãn và `help` của trường, `help` trong view viết tiếng Việt. |
| T2 | Manifest có hai khoá `name_vi_VN`, `summary_vi_VN` mà Odoo không đọc. |
| T3 | Không có bản dịch, không có test. |
| T4 | Bốn module lặp lại cùng một đoạn đọc cờ. |
| T5 | Cờ chỉ áp dụng cho đúng một tài khoản `transfer_account_id`; người dùng không chọn được tài khoản. |

## 2. Khác biệt 19.0 → 20.0

Không có khác biệt nào chặn module này. Đã kiểm tra trên lõi 20.0:

- `res.company.transfer_account_id` vẫn có (`account/models/company.py:116`), miền giá trị là tài khoản `asset_current` cho phép đối soát.
- View `account.res_config_settings_view_form` vẫn có `<app name="account">`; thẻ `<block>` và `<setting>` vẫn dùng.
- Trường `related` trên `res.config.settings` không đổi cách khai báo.
- Module không có model mới nên không cần file phân quyền.

Một thay đổi của lõi có liên quan tới ý nghĩa của thiết lập: ở hệ thống tài khoản `l10n_vn` 20.0, hai tài khoản chờ đối soát của thanh toán là con của tài khoản trung chuyển.

| Mã | Tên | Vai trò trong Odoo | Cha |
|---|---|---|---|
| 113 | Tiền đang chuyển | `transfer_account_id` của công ty | |
| 1131 | Outstanding Receipts | Tài khoản chờ của phiếu thu chưa khớp sao kê | 113 |
| 1132 | Outstanding Payments | Tài khoản chờ của phiếu chi chưa khớp sao kê | 113 |

Cả ba là loại `asset_current`, cho phép đối soát. Đơn vị theo Thông tư 133 không có 113 thì cũng không có 1131, 1132. Đây là lý do của quyết định 3.

## 3. Quyết định thiết kế (đã chốt)

| # | Vấn đề | Quyết định |
|---|---|---|
| 1 | Chuỗi | Tiếng Anh trong code, dịch ở `i18n/vi.po`. |
| 2 | Manifest | Bỏ `name_vi_VN`, `summary_vi_VN`; `category` `Accounting/Accounting`; `version` 20.0.1.0.0; giữ AGPL-3. |
| 3 | Tài khoản được ẩn do người dùng chọn (T5) | Thêm `res.company.fg_hidden_transfer_account_ids`: Many2many tới `account.account`, `check_company=True`. Giữ cờ `fg_hide_transfer_account` làm nút bật/tắt. Trong trang thiết lập, danh sách chỉ hiện khi cờ bật. Khi bật cờ mà danh sách đang rỗng, form điền sẵn `transfer_account_id` của công ty (onchange trên `res.config.settings`); người dùng sửa được trước khi lưu. Module không tự thêm tài khoản con hay tài khoản chờ nào. |
| 4 | Ghi chú theo thông tư | Dòng `help` dưới thiết lập ghi gợi ý: Thông tư 133 thì bật và chọn tài khoản trung chuyển cùng các tài khoản chờ thanh toán đang dùng; Thông tư 200, Thông tư 99 thì tắt. Chỉ là ghi chú, không có logic theo thông tư. |
| 5 | Hàm dùng chung (T4) | `res.company._fg_get_hidden_transfer_accounts()`: trả recordset `account.account`. Cờ tắt thì trả rỗng. Cờ bật thì trả `fg_hidden_transfer_account_ids`. Mọi module báo cáo gọi hàm này, không tự đọc hai trường. |
| 6 | Khối trong trang thiết lập | Giữ khối riêng "Vietnam Accounting". |

Lưu ý cho database đi từ 19.0: ở 19.0 bật cờ là đủ. Ở 20.0, cờ bật mà danh sách rỗng thì không tài khoản nào bị ẩn. Module có script `migrations/20.0.1.0.0/post-migrate.py` điền `transfer_account_id` vào danh sách cho các công ty đang bật cờ mà danh sách rỗng, để database nâng cấp từ 19.0 giữ hành vi cũ. Cài mới thì không công ty nào bật cờ nên không cần xử lý.

## 4. Cấu trúc và việc cần làm

```
fg_vn_transfer_account/
├── __init__.py
├── __manifest__.py
├── readme.md
├── PLAN.md
├── models/
│   ├── __init__.py
│   ├── res_company.py              hai trường + _fg_get_hidden_transfer_accounts()
│   └── res_config_settings.py      hai trường related + onchange
├── views/res_config_settings_views.xml
├── migrations/20.0.1.0.0/post-migrate.py
├── i18n/                           .pot và vi.po
├── static/description/index.html
└── tests/test_transfer_account.py
```

| File | Việc cần làm |
|---|---|
| `__manifest__.py` | Quyết định 2; `description` ngắn tiếng Anh. |
| `models/res_company.py` | Nhãn và `help` tiếng Anh; thêm trường Many2many (quyết định 3) và hàm (quyết định 5). |
| `models/res_config_settings.py` | Hai trường `related`, `readonly=False`; onchange điền sẵn (quyết định 3). |
| `views/res_config_settings_views.xml` | Thêm trường danh sách với `widget="many2many_tags"`, `invisible="not fg_hide_transfer_account"`; `help` tiếng Anh gồm ghi chú theo thông tư (quyết định 4). |
| `tests/test_transfer_account.py` | Hàm trả rỗng khi cờ tắt dù danh sách có tài khoản; trả đúng danh sách khi cờ bật; trả rỗng khi cờ bật mà danh sách rỗng; onchange điền sẵn tài khoản trung chuyển và không ghi đè danh sách đã có; thiết lập độc lập giữa hai công ty; không chọn được tài khoản của công ty khác; form thiết lập mở và lưu được; hàm điền danh sách của script nâng cấp chạy đúng cho công ty đang bật cờ. |
| `i18n/` | Xuất `.pot`, viết `vi.po`. |
| `README.md` của repo | Thêm dòng vào bảng module đã hoàn thành. |

Một giai đoạn duy nhất. Xong khi: cài được trên 20.0 không cảnh báo, test chạy qua, bật/tắt và chọn tài khoản được ở trang thiết lập bằng cả hai ngôn ngữ.

## 5. Việc của các module đọc thiết lập

| Module | Việc cần làm |
|---|---|
| `fg_vn_report_cdps` (đang chuyển) | Gọi `_fg_get_hidden_transfer_accounts()`; xử lý một tập tài khoản thay vì một tài khoản. |
| `fg_vn_report_s03a`, `fg_vn_report_s03b`, `vn_payment_print` (chuyển sau) | Như trên. Việc thay tài khoản đối ứng cho phiếu thu, chi chưa khớp sao kê (1131, 1132) khác với chuyển tiền nội bộ; phân tích khi chuyển từng module. |
