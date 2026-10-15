# Kế hoạch chuyển `l10n_vn_tt133` sang Odoo 20.0

Nguồn: `D:\openerp\V19\fanha-addons\l10n_vn_tt133` (19.0.1.0.0, commit cuối đụng tới module: `20ce15a` "update website").
Đối chiếu lõi Odoo: 19.0 tại `c50a4e0513e`, 20.0 tại `97d8ce809`.

`readme.md` mô tả module làm gì cho người dùng; kế hoạch này nói làm bằng cách nào. Readme đang viết theo các phương án đề xuất ở mục 7; quyết định khác thì sửa cả hai.

Trạng thái: **đã làm** (2026-10-15). Người dùng duyệt plan ngày 2026-10-15 ("port module này"); Q6 theo phương án đề xuất. Code theo mục 8, chỗ lệch so với kế hoạch ở mục 10. Vấn đề `code_digits = 4` của `l10n_vn` neo lại ở mục 9.

## 1. Phân tích code nguồn

### 1.1. Thành phần

| Thành phần | File | Dòng | Sang 20.0 |
|---|---|---|---|
| Khai báo template `vn_tt133`, dữ liệu công ty, sổ nhật ký, tài khoản biến động kho của 152 | `models/template_vn_tt133.py` | 70 | sửa (mục 2.1) |
| 102 tài khoản, mã 2–5 chữ số | `data/template/account.account-vn_tt133.csv` | 103 | thêm cột `parent_id`, thêm 24 tài khoản tổng hợp |
| 34 nhóm tài khoản (9 loại một chữ số, 25 nhóm 3–4 chữ số) | `data/template/account.group-vn_tt133.csv` | 35 | **xoá**: model `account.group` không còn |
| 15 thuế, chép từ `l10n_vn` 19.0 thêm tiền tố `vn133_` | `data/template/account.tax-vn_tt133.csv` | 61 | **xoá**, dùng thuế của `l10n_vn` (mục 4) |
| 6 nhóm thuế | `data/template/account.tax.group-vn_tt133.csv` | 7 | **xoá**, dùng nhóm thuế của `l10n_vn` |
| Manifest | `__manifest__.py` | 27 | sửa |

Module không có view, không có phân quyền, không có test.

### 1.2. Lỗi và điểm yếu có sẵn

| # | Vị trí | Vấn đề |
|---|---|---|
| A1 | `template_vn_tt133.py:62` và `:66` | Tài khoản tạm ngân hàng (suspense) và tài khoản của sổ ngân hàng **cùng là 1121**. Dòng sao kê chưa đối soát ghi Nợ 1121 / Có 1121, số dư 1121 không phản ánh tiền đã vào tài khoản cho tới khi đối soát xong. |
| A2 | `__manifest__.py:20` | Mô tả ghi "không có TK 113 → dùng 1123 dưới 112", code lại dùng tài khoản kỹ thuật mã `01`. |
| A6 | `template_vn_tt133.py:15` và CSV | `code_digits = '3'` làm Odoo thêm `0` vào cuối mọi mã ngắn hơn 3 ký tự khi nạp template (`chart_template.py` 19.0 dòng 524, 20.0 dòng 529). Mã `01`, `02`, `03` trong CSV thực tế thành `010`, `020`, `030`. **(Suy từ code.)** |
| A3 | thứ tự dòng trong `account.account-vn_tt133.csv` | Khi tạo sổ ngân hàng/tiền mặt mới, Odoo lấy **độ dài mã của tài khoản có id nhỏ nhất** để sinh mã tài khoản mới (`account_journal.py:948`, cả 19.0 và 20.0). Dòng đầu file là `01` (2 chữ số), nên tiền tố `112` bị cắt còn `11` và tài khoản mới nhận mã `12`. **(Suy từ code, chưa chạy thử trên 19.0.)** |
| A4 | `account.tax-vn_tt133.csv:38-41` | Thuế nhập khẩu dùng nhãn `tax_import_base`, `tax_import`; 20.0 không còn hai nhãn này. |
| A5 | `__manifest__.py` | Chuỗi mô tả và tên template viết tiếng Việt trong code; giấy phép LGPL-3. Quy ước repo: chuỗi tiếng Anh + `i18n/vi.po`, AGPL-3. |

## 2. Khác biệt lõi 19.0 → 20.0 ảnh hưởng tới module

Đã ghi vào vault `D:\odoo_vault\odoo\migration\v19-to-v20\account.md` §3 (cập nhật) và §6 (mới).

### 2.1. Chart template

| 19.0 | 20.0 | Xử lý |
|---|---|---|
| Dữ liệu template (`@template('vn_tt133')`) nhận khoá tuỳ ý: `property_account_receivable_id`, `property_account_payable_id`, `property_stock_valuation_account_id`, `display_invoice_amount_total_words` | Chỉ nhận `name`, `country`, `code_digits`, `parent`, `sequence`, `visible` (`TEMPLATE_DATA_KEYS`, `chart_template.py:31`); khoá khác **bị bỏ lặng lẽ** (báo lỗi khi có context `l10n_check_fields_complete`) | Chuyển sang phần `res.company`: `receivable_account_id`, `payable_account_id`, `display_invoice_amount_total_words`. Bỏ `property_stock_valuation_account_id` (không còn nơi nhận, `l10n_vn` 20.0 cũng bỏ). |
| `account_stock_journal_id: 'inventory_valuation'` khai ở từng localization | `account` tự đặt cho mọi template (`chart_template.py:1199`) | Bỏ khỏi module. |
| `account.group-*.csv` | không còn model | Xoá file; cây tài khoản qua cột `parent_id` của `account.account-*.csv` |
| — | Hook `_get_account_parent_xmlid(code_prefix, template_code)` (`chart_template.py:860`): tài khoản Odoo tự sinh theo tiền tố (sổ ngân hàng/tiền mặt mới, tài khoản tạm, chuyển tiền) được gắn vào tài khoản cha do hook trả về | Cài hook: `112` → `vn133_chart112`, `111` → `vn133_chart111`. |
| — | Cột `parent_id` trong CSV được ghi **sau** khi tạo xong mọi tài khoản (trường quan hệ tự trỏ về cùng model bị hoãn, `chart_template.py:640`) | Thứ tự dòng trong CSV không cần cha đứng trước con. |
| `code_digits` thêm số 0 vào cuối mã ngắn | Như cũ, trừ tài khoản `active=False` (`chart_template.py:437`) | Đổi sang `code_digits = '2'`: mã `03` giữ nguyên (sửa A6), mã ba chữ số (131, 331…) giữ nguyên; `'4'` sẽ biến 131 thành 1310 như `l10n_vn`. `code_digits` còn dùng để sinh mã cho tài khoản tiện ích Odoo tự tạo theo tiền tố, nhưng TT133 khai sẵn mọi tài khoản đó nên không bị ảnh hưởng. |

Các trường `res.company` module dùng đều còn ở 20.0 (đã tra `fields.tsv`): `anglo_saxon_accounting`, `account_stock_valuation_id`, `account_production_wip_account_id`, `expense_account_id`, `income_account_id`, `transfer_account_code_prefix`, `account_journal_suspense_account_id`… Riêng `deferred_expense_account_id`, `deferred_revenue_account_id` không có trong bản Community (cả 19.0); loader bỏ qua, giữ lại để dùng khi có bản Enterprise, như `l10n_vn`.

### 2.2. Tài khoản cha – con

`account.account` có `parent_id`, `parent_path`, `parent_ids`, `code_path`, `name_path`; `_order = "code_path, account_type, name_path"`.

**Ghi sổ vào tài khoản cha: được phép.** Đã thử trên `test_fg_vas` (shell, rollback): tạo 9901 và con 99011, bút toán Nợ 9901 100 / Nợ 99011 50 / Có 600000 150 ghi sổ bình thường; `('account_id', 'child_of', 9901)` cộng ra 150 (gồm dòng của chính cha). Gắn tài khoản con vào một tài khoản đã có phát sinh cũng không bị chặn. Không có `_constrains` hay domain nào trên `account.move.line.account_id` xét tới cha–con (domain chỉ loại `off_balance`).

## 3. Cây tài khoản

### 3.1. Tài khoản tổng hợp thêm mới

Mỗi nhóm 3–4 chữ số của 19.0 thành một tài khoản. Nhóm 335 bỏ vì đã có tài khoản 335 và không có con.

| Mã | Tên | `account_type` | Con |
|---|---|---|---|
| 111 | Tiền mặt | `asset_cash` | 1111, 1112 |
| 112 | Tiền gửi ngân hàng | `asset_cash` | 1121, 1122 |
| 128 | Đầu tư nắm giữ đến ngày đáo hạn | `asset_current` | 1281, 1288 |
| 133 | Thuế GTGT được khấu trừ | `asset_current` | 1331, 1332 |
| 136 | Phải thu nội bộ | `asset_current` | 1361, 1368 |
| 138 | Phải thu khác | `asset_current` | 1381, 1386, 1388 |
| 211 | Tài sản cố định | `asset_fixed` | 2111, 2112, 2113 |
| 214 | Hao mòn tài sản cố định | `asset_non_current` | 2141, 2142, 2143, 2147 |
| 228 | Đầu tư góp vốn vào đơn vị khác | `asset_non_current` | 2281, 2288 |
| 229 | Dự phòng tổn thất tài sản | `asset_non_current` | 2291 … 2294 |
| 241 | Xây dựng cơ bản dở dang | `asset_non_current` | 2411, 2412, 2413 |
| 333 | Thuế và các khoản phải nộp Nhà nước | `liability_current` | 3331, 3332 … 3337, 3338, 3339 |
| 3331 | Thuế giá trị gia tăng phải nộp | `liability_current` | 33311, 33312 |
| 3338 | Thuế bảo vệ môi trường và các loại thuế khác | `liability_current` | 33381, 33382 |
| 336 | Phải trả nội bộ | `liability_current` | 3361, 3368 |
| 338 | Phải trả, phải nộp khác | `liability_current` | 3381 … 3388 |
| 341 | Vay và nợ thuê tài chính | `liability_current` | 3411, 3412 |
| 352 | Dự phòng phải trả | `liability_current` | 3521, 3522, 3524 |
| 353 | Quỹ khen thưởng, phúc lợi | `liability_current` | 3531 … 3534 |
| 356 | Quỹ phát triển khoa học và công nghệ | `liability_current` | 3561, 3562 |
| 411 | Vốn đầu tư của chủ sở hữu | `equity` | 4111, 4112, 4118 |
| 421 | Lợi nhuận sau thuế chưa phân phối | `equity` | 4211, 4212 |
| 511 | Doanh thu bán hàng và cung cấp dịch vụ | `income` | 5111, 5112, 5113, 5118 |
| 642 | Chi phí quản lý kinh doanh | `expense` | 6421, 6422 |

- Tài khoản tổng hợp có con là phải thu/phải trả (136, 138, 336, 338) **không** lấy loại `asset_receivable`/`liability_payable`: loại này bắt buộc đối soát và làm tài khoản cha hiện trong ô chọn tài khoản công nợ của đối tác. Dùng `asset_current`/`liability_current`, `reconcile = False`.
- xmlid theo mẫu cũ: `vn133_chart111`, `vn133_chart3331`… Không trùng xmlid nào đang có (`vn133_chart113` là tài khoản kỹ thuật, nay mã `03`).

### 3.4. Tài khoản kỹ thuật (đã chốt 2026-10-14)

Quy ước chung cho mọi chế độ (ghi ở `fg_vn_accounting_reports/readme.md` mục 8.3): tài khoản kỹ thuật Odoo cần thì mang mã của tài khoản Odoo tương ứng, thay `11` ở đầu bằng `0`, **không có tài khoản cha** — `03x` cho họ 113, `02x` cho họ 112. Chốt cuối ngày 2026-10-14 (thay phương án `01`, `011`, `012` có cây trước đó): cùng một cấu trúc với công ty TT200 đã đổi mã, các module khác không phải phân biệt.

| xmlid | Mã | Tên | Vai trò Odoo | Cha | `l10n_vn` tương ứng |
|---|---|---|---|---|---|
| `vn133_chart113` | 03 | Tiền đang chuyển (Money in transit) | `transfer_account_id` | — | 113 |
| `account_journal_payment_debit_account_id` | 031 | Outstanding Receipts | tài khoản chờ thu | — | 1131 |
| `account_journal_payment_credit_account_id` | 032 | Outstanding Payments | tài khoản chờ chi | — | 1132 |
| `vn133_chart021` (mới) | 021 | Bank Suspense Account | `account_journal_suspense_account_id` | — | 1121 |

- `03`: loại `asset_current`, **cho đối soát**. Domain của `res.company.transfer_account_id` đòi đúng hai điều này (`company.py:118`); `fg_vn_transfer_account` chỉ ẩn dòng của tài khoản trung chuyển khi dòng đã đối soát hết, nên tài khoản không cho đối soát thì không bao giờ được ẩn. 19.0 và `l10n_vn` 20.0 để `asset_cash`, không đối soát (domain chỉ chặn trên giao diện).
- `031`, `032`: `asset_current`, đối soát; `021`: `asset_current`, không đối soát (như `l10n_vn`).
- Phát sinh sau khi đối soát (`fg_vn_accounting_reports/readme.md` mục 8.4): `021` không còn; `03` còn hai bên; `031`, `032` chỉ có nếu người dùng khai tài khoản chờ cho phương thức thanh toán. Module **không** gán `031`, `032` vào phương thức thanh toán (giữ như `l10n_vn`).
- `021` không có cha: Odoo đặt 1121 dưới 112 (tài khoản tiền thật); dưới 112 thì khi còn số dư nó bị cộng vào dòng 112 trên bảng cân đối số phát sinh phân cấp.
- Cả bốn đầu `0`, nên CDPS và sổ cái chỉ trình bày khi còn số dư và không bao giờ đưa vào XML (quy tắc đã kiểm ở `fg_vn_accounting_reports/readme.md` mục 8.2). 
- Tên tiếng Anh lấy từ cột `name` của nhóm 19.0 (một số nhóm 19.0 để tên tiếng Việt ở cả hai cột, sẽ dịch lại).

### 3.2. Chín loại tài khoản một chữ số

Bỏ, như `l10n_vn` 20.0. Phương án khác: tạo 9 tài khoản `active=False` làm gốc cây (`l10n_hk` làm vậy; tài khoản lưu trữ không bị thêm số 0, `_search` có context `include_inactive_account_parents`). Không đề xuất: tài khoản mã `1`…`9` hiện trong danh mục khi bật bộ lọc lưu trữ, và các báo cáo `fg_vn_*` không cần.

### 3.3. Thứ tự dòng CSV

Dòng đầu tiên phải là tài khoản 4 chữ số (đặt `1111` lên đầu) để sửa A3: sổ ngân hàng mới nhận mã `1123`, `1124`…, sổ tiền mặt mới nhận `1113`… dưới đúng cha 112/111 (qua hook mục 2.1). Có test khoá lại.

## 4. Thuế

**Không chép file thuế.** Thuế GTGT theo luật, không theo chế độ kế toán; TT133 dùng thẳng bộ thuế của `l10n_vn` (31 thuế, 7 nhóm), đọc từ CSV của `l10n_vn` lúc nạp template:

```python
@template('vn_tt133', 'account.tax.group')
def _get_vn_tt133_account_tax_group(self):
    return self._parse_csv('vn', 'account.tax.group')

@template('vn_tt133', 'account.tax')
def _get_vn_tt133_account_tax(self):
    data = self._parse_csv('vn', 'account.tax')
    self._deref_account_tags('vn', data)
    # đổi xmlid tài khoản trong repartition_line_ids (và cash_basis_transition_account_id nếu có):
    # 'chartXXXX' -> 'vn133_chartXXXX'
    return data
```

Cơ sở (đã đọc code, chưa chạy):

- Xmlid bản ghi tạo từ template là `account.{id công ty}_{xmlid}` (`chart_template.py:1242`), không theo module. Mỗi công ty một template, nên TT133 dùng chung tên `tax_purchase_vat10`, `tax_group_10`… với `l10n_vn` không đụng nhau. Code khác gọi `ref('tax_sale_vat10')` chạy được cho cả công ty TT133.
- `_parse_csv(template_code, model)` (`chart_template.py:1317`) lấy module và tên file theo `template_code`, nên `'vn'` đọc `l10n_vn/data/template/account.tax-vn.csv`. Hàm gốc `@template(model='account.tax')` vẫn chạy cho `vn_tt133`, không tìm thấy file `-vn_tt133.csv` thì trả rỗng; kết quả hai hàm được gộp.
- Nhãn tờ khai tra theo quốc gia của template `'vn'` — cùng quốc gia VN.
- Thuế `l10n_vn` chỉ trỏ hai tài khoản: `chart1331` (14 chỗ), `chart33311` (6 chỗ). TT133 có cả hai, cùng mã.
- `children_tax_ids` của thuế nhóm GTGT nhập khẩu trỏ xmlid thuế, giữ nguyên tên nên không phải đổi.

Rủi ro: bản cập nhật sau của `l10n_vn` trỏ thuế vào tài khoản TT133 không có (vd. 1332 có, 3333 có, nhưng 13311 thì không). Test duyệt mọi tài khoản thuế `l10n_vn` tham chiếu và kiểm `vn133_` tương ứng có trong CSV tài khoản TT133; đổi xmlid gặp tài khoản thiếu thì báo lỗi rõ thay vì để loader báo xmlid không tồn tại.

`res.company`: `account_sale_tax_id: 'tax_sale_vat10'`, `account_purchase_tax_id: 'tax_purchase_vat10'` (bỏ tiền tố `vn133_`).

Khác biệt thuế 19.0 → 20.0 (TT133 nhận theo mà không phải làm gì):

| 19.0 (module) | 20.0 (`l10n_vn`) |
|---|---|
| Nhãn thuế theo tên dòng báo cáo ("Untaxed Purchase of Goods and Services taxed 10%") | Nhãn theo mã chỉ tiêu tờ khai 01/GTGT: `MHND_NET_10`, `MHND_VAT_10`, `MHNK_*`, `BH_*`, `VAT_KKT`, `VAT_NK_KKT`, `BH_KKKTT` |
| GTGT nhập khẩu: 4 thuế `percent` loại mua | Thuế nhóm (`group`) = `subtract_base_amount` (−100%) + thuế thành phần loại `none`; có bản không được khấu trừ |
| — | Thuế mua không được khấu trừ 5/8/10% |
| — | Thuế bán KKKTT, nhóm thuế `tax_group_KKKTT`, `tax_group_base_amount` |
| `tax_import` 5% (thuế nhập khẩu, Có 3333), nhóm `tax_group_import` | Bỏ |

Thuế nhập khẩu 5%: đề xuất **bỏ**, để bộ thuế giống hệt `l10n_vn`. Thuế nhập khẩu tính theo tờ khai hải quan, nhiều mức thuế suất; một mức 5% cố định trên hoá đơn ít khi đúng. Nếu giữ: thêm một thuế `vn133_tax_import` và nhóm `vn133_tax_group_import` trong hàm trên, không nhãn (A4).

## 5. Dữ liệu công ty và sổ nhật ký (`template_vn_tt133.py`)

```python
@template('vn_tt133')
def _get_vn_tt133_template_data(self):
    return {
        'name': _("SME accounting (Circular 133/2016/TT-BTC)"),   # Odoo thêm "🇻🇳 Vietnam - " phía trước
        'code_digits': '2',                 # '03' không bị đệm thành '030' (A6)
    }

@template('vn_tt133', 'res.company')
    # như 19.0, trừ:
    #  + 'display_invoice_amount_total_words': True
    #  + 'receivable_account_id': 'vn133_chart131', 'payable_account_id': 'vn133_chart331'
    #  - 'account_stock_journal_id'
    #  ~ 'account_journal_suspense_account_id': 'vn133_chart021' thay cho 1121 (mục 3.4)

def _get_account_parent_xmlid(self, code_prefix, template_code):
    if template_code == 'vn_tt133':
        return {'111': 'vn133_chart111', '112': 'vn133_chart112'}.get(code_prefix)
    return super()...

def _post_load_data(self, template_code, company, template_data):
    res = super()._post_load_data(template_code, company, template_data)
    if template_code == 'vn_tt133':
        # Odoo vừa gắn 031, 032, 021 vào 112 qua hook (mục 7.2): bỏ cha
        for xmlid in ('account_journal_payment_debit_account_id',
                      'account_journal_payment_credit_account_id', 'vn133_chart021'):
            if account := self.ref(xmlid, raise_if_not_found=False):
                account.parent_id = False
    return res
```

- Bỏ `country_id: 'base.vn'` của 19.0: không nằm trong `TEMPLATE_DATA_KEYS`. Quốc gia lấy từ khoá `country`, thiếu thì lấy phần trước dấu `_` của mã template (`vn_tt133` → `vn`, `account/models/ir_module.py:58-59`).
- Tên template được đọc một lần khi dựng danh sách template (`ir_module.py:56`, `TEMPLATE_REGISTER`); dùng `_()` như `l10n_ar`. Kiểm khi code xem tên có đổi theo ngôn ngữ người dùng không.

Sổ nhật ký: giữ như 19.0 (ngân hàng → 1121, tiền mặt → 1111).

Tài khoản chênh lệch kho: 632 cho 152, 153, 155, 156 (mục 7.3; 19.0 chỉ có 152).

## 6. Manifest, dịch, tài liệu

- `version`: `20.0.1.0.0`; `license`: `AGPL-3`; `depends`: `['l10n_vn']` (cần nhãn thuế và báo cáo 01/GTGT của nó).
- Tên module, `summary`, `description` tiếng Anh; `description` viết tay (không để Odoo dựng từ `readme.md`), như `fg_vn_report_s03a`.
- `i18n/vi.po`: tên template, tên sổ "Cash", mô tả module. Tên tài khoản/thuế dịch qua cột `name@vi_VN` trong CSV như hiện tại.
- `static/description/icon.png` theo icon chung của repo (commit `df5da96`).
- Giữ tên kỹ thuật `l10n_vn_tt133` và mã template `vn_tt133`: đổi tên sẽ làm mất liên kết xmlid nếu sau này chuyển dữ liệu từ 19.0.
- Thêm dòng vào bảng module của `README.md` repo khi xong.

## 7. Quyết định

| # | Câu hỏi | Quyết định | Trạng thái |
|---|---|---|---|
| Q1 | Có chặn ghi sổ vào tài khoản đã có tài khoản con không? | **Không chặn**, không can thiệp lõi. Mọi tài khoản mặc định của template là tài khoản chi tiết. | Đã chốt (2026-10-14) |
| Q2 | Tài khoản tạm ngân hàng (A1) | Tài khoản kỹ thuật mới `021`, theo quy ước `0` + mã Odoo (mục 3.4). | Đã chốt (2026-10-14) |
| Q3 | Cây của tài khoản kỹ thuật | `03`, `031`, `032`, `021` đều không có tài khoản cha. Mục 3.4, 7.2. | Đã chốt (2026-10-14) |
| Q4 | Kịch bản chuyển dữ liệu 19.0 | Không làm. | Đã chốt (2026-10-14) |
| Q5 | Thuế nhập khẩu 5% | Bỏ; bộ thuế giống hệt `l10n_vn`. Thuế này có trong `l10n_vn` 19.0 của Odoo (`tax_import`), bản TT133 chép theo; `l10n_vn` 20.0 đã bỏ. | Đã chốt (2026-10-14) |
| Q6 | Tài khoản chênh lệch kho (`account_stock_variation_id`) | 632 cho 152, 153, 155, 156. Mục 7.3. | Đã chốt (2026-10-15, theo đề xuất) |

### 7.1. Tài khoản nào không vào sổ, PDF, XML

Ở 17.0, tài khoản không thuộc nhóm nào thì không được in và xuất XML; tài khoản kỹ thuật đầu `0` không có nhóm nên bị loại. 20.0 không còn nhóm. Code hiện tại của các báo cáo 20.0 (đã đọc):

| Quy tắc | Nhận diện | Màn hình, Excel, PDF | XML F01-CDTK |
|---|---|---|---|
| "Ngoài bảng" (`_is_off_balance`, `cdps_report.py:25`, `s03b_report.py:18`) | `account_type == 'off_balance'` **hoặc mã bắt đầu bằng `0`** | Chỉ hiện khi còn số dư đầu hoặc cuối kỳ, nền cam | **Không bao giờ có**; không cộng lên cha, không vào `tongCong` |
| Danh sách ẩn của `fg_vn_transfer_account` (người dùng chọn theo công ty) | id tài khoản trong `fg_hidden_transfer_account_ids` | Chỉ hiện khi còn số dư; bị loại trước khi dựng cây nên không cộng lên cha | Vẫn có thẻ riêng và **vẫn cộng phát sinh lên cha** (`cdps_report.py:527-539`); chỉ bị loại khỏi `tongCong` khi hết số dư |
| Mã dưới 3 ký tự | độ dài mã | hiện | không có thẻ, không vào `tongCong` (`cdps_report.py:519, 537`) |

Hệ quả cho TT133: đặt mã đầu `0` (`03`, `031`, `032`, `021`) cho các tài khoản kỹ thuật là đủ, không cần thêm cơ chế mới. Quy tắc "đầu `0`" thay cho "không có nhóm" của 17.0 và áp dụng cho mọi tài khoản đơn vị tự thêm mà không muốn đưa vào sổ theo chế độ.

Không dùng loại `off_balance` cho các tài khoản này: Odoo bắt mọi dòng của bút toán có dòng `off_balance` cũng phải là `off_balance` (`account.move.line._check_off_balance`), nên tài khoản tạm/chờ của ngân hàng không thể mang loại đó.

**Trường hợp `l10n_vn` (TT200) mà người dùng nêu** — 112 "Tiền gửi không kỳ hạn" (thành 1120 vì `code_digits = 4`) có con 1121 "Tài khoản tạm thời ngân hàng": mã không bắt đầu bằng `0`, nên chỉ phân biệt được qua danh sách ẩn của `fg_vn_transfer_account`. Lúc đó màn hình/PDF đúng, nhưng XML vẫn có thẻ `ct1121` và phát sinh của 1121 được cộng vào thẻ `ct1120`. Thêm vào đó mã 1121 của Odoo trùng mã 1121 "Tiền Việt Nam" của chế độ. Đây là việc của `fg_vn_report_cdps` với công ty TT200, không thuộc module này; ghi ở mục 9.

### 7.2. Giữ cây của tài khoản kỹ thuật

- Nếu nằm dưới 112, XML vẫn bỏ chúng (quy tắc đầu `0`), nhưng cây tài khoản trong Odoo hiện chúng là con của "Tiền gửi ngân hàng", lẫn với tài khoản ngân hàng thật, và khi còn số dư chúng bị cộng vào dòng 112 của CDPS phân cấp.
- Odoo tự gắn cha cho tài khoản tạm và hai tài khoản chờ: `_setup_utility_bank_accounts` và `_create_outstanding_accounts` truyền `parent_id = _get_account_parent_id(bank_prefix)`, và `_load_records` (gọi với `update=False`) **ghi đè** cả bản ghi đã có từ CSV (`orm/models.py:4676`). Với hook trả 112 cho tiền tố `112`, `031`, `032`, `021` sẽ bị gắn vào 112.
- Cách xử lý: `_post_load_data` của TT133 gọi `super()` rồi đặt lại cha cho ba tài khoản này (mục 5). Tài khoản của sổ ngân hàng người dùng tạo sau (qua `account.journal._create_default_account`) vẫn vào 112 qua hook.

### 7.3. Tài khoản chênh lệch kho (Q6)

`account.account.account_stock_variation_id` ("Variation Account") dùng khi Odoo lập bút toán khoá sổ kho (`res.company._get_stock_valuation_account_vals`, `company.py:1495`): chênh lệch giữa giá trị kho theo phiếu kho và số dư tài khoản kho được ghi đối ứng vào tài khoản này. Tài khoản kho không khai thì Odoo dùng `res.company.expense_account_id` — với TT133 là **6421 Chi phí bán hàng**, sai bản chất.

Bản 19.0 chỉ khai cho 152; tài khoản kho mặc định của công ty lại là 156, nên chênh lệch của hàng hoá rơi vào 6421. Đề xuất khai 632 cho 152, 153, 155, 156 (các tài khoản có thể làm tài khoản kho của nhóm sản phẩm). Người dùng sửa được trên từng tài khoản.

## 8. Các bước

1. Tạo khung module 20.0: manifest, `__init__`, icon. Xoá `account.group-*.csv`.
2. `account.account-vn_tt133.csv`: thêm cột `parent_id`, 24 tài khoản tổng hợp (mục 3.1), tài khoản kỹ thuật theo mục 3.4 (`01` cũ thành `03`; `02`, `03` cũ thành `031`, `032`; thêm `021`; không tài khoản nào có cha), đưa `1111` lên đầu; dịch lại tên tiếng Anh của các nhóm cũ.
3. Thuế: xoá `account.tax-vn_tt133.csv`, `account.tax.group-vn_tt133.csv`; viết hai hàm đọc thuế `l10n_vn` ở mục 4.
4. `template_vn_tt133.py` theo mục 5.
5. `i18n/vi.po`.
6. Test (`tests/test_chart_vn_tt133.py`, `AccountTestInvoicingCommon` với `setup_chart_template('vn_tt133')`):
   - nạp template với context `l10n_check_fields_complete` không báo lỗi khoá/trường lạ;
   - mã 3 chữ số không bị thêm 0 (131, 911); có đủ 24 tài khoản tổng hợp, `parent_path` đúng (1121 dưới 112, 33311 dưới 3331 dưới 333); không còn `account.group`;
   - tạo sổ ngân hàng mới → tài khoản `1123` có cha 112; sổ tiền mặt mới → `1113` có cha 111;
   - tài khoản tạm ngân hàng khác tài khoản của sổ ngân hàng;
   - công ty: phải thu 131, phải trả 331, `anglo_saxon_accounting` tắt;
   - hoá đơn mua 10%: Nợ 1331, nhãn `MHND_NET_10`/`MHND_VAT_10`; hoá đơn bán 10%: Có 33311; thuế nhóm GTGT nhập khẩu 10% tính đúng;
   - mã tài khoản kỹ thuật đúng `03`, `031`, `032`, `021` (không bị đệm `0`); cả bốn không có cha sau khi nạp template; sổ ngân hàng tạo sau đó có cha 112 (mục 3.4, 7.2);
   - tài khoản chênh lệch kho của 152, 153, 155, 156 là 632.
7. Chạy `tools/run_tests.sh l10n_vn_tt133 '' -i` trên `test_fg_vas` (báo người dùng tắt Odoo trước). Cài thử trên một công ty mới qua giao diện, xem cây tài khoản.
8. Cập nhật `README.md` repo, trạng thái kế hoạch.

## 9. Ghi lại cho module khác

- `fg_vn_report_cdps`, công ty theo `l10n_vn` (TT200): tài khoản trong danh sách ẩn của `fg_vn_transfer_account` (vd. 1121 tạm ngân hàng, 1131, 1132) vẫn có thẻ riêng trong XML F01-CDTK và phát sinh của chúng vẫn cộng vào thẻ của tài khoản cha (mục 7.1). Màn hình/PDF đã loại chúng trước khi dựng cây; XML nên làm giống vậy. Không ảnh hưởng TT133 vì tài khoản kỹ thuật đầu `0`. Với TT200, người dùng đổi mã theo quy ước ở `fg_vn_accounting_reports/readme.md` mục 8.3 thì cũng hết vấn đề này.
- XML F01-CDTK sinh một thẻ `ct<mã>` cho mọi tài khoản mã từ 3 ký tự. Tài khoản Odoo tự tạo cho từng sổ ngân hàng (1123, 1124…) cũng thành thẻ. Chưa kiểm phần mềm nhận tờ khai có chấp nhận thẻ ngoài danh mục hay không.
- **Neo lại (2026-10-14): mã của `l10n_vn` bị đệm 0.** `l10n_vn` đặt `code_digits = 4` (cả 19.0 lẫn 20.0), nên mọi tài khoản 3 chữ số thành 4 chữ số (131 → `1310`, 911 → `9110`; đã chạy thử). Ảnh hưởng: thẻ XML CDPS (`ct1310`), bộ lọc "Cấp tài khoản" của CDPS (cấp 1 trống), mã in trên sổ. Hướng xử lý khi làm: (a) CDPS tính cấp theo cây `parent_path` thay cho độ dài mã; (b) module chuẩn hoá cho TT200/TT99 đổi mã về đúng chế độ. Ghi chú kỹ thuật:
  - `code_digits` không được lưu ở đâu sau khi thiết lập (không có trường trên `res.company`); chỉ dùng lúc nạp template. Sửa nó sau khi đã cài `l10n_vn` không đổi được tài khoản của công ty đã thiết lập.
  - Đổi mã tài khoản đã có phát sinh: được. `account.account.write` chỉ kiểm mã không trùng (`_ensure_code_is_unique`) và đúng ký tự cho phép (`_check_account_code`).
  - Cập nhật module `l10n_vn` không đổi lại mã: khi nạp lại template, tài khoản đã có chỉ được cập nhật `tag_ids` (`chart_template.py:458`), và mã `131` vẫn khớp mẫu `^1310*$` dùng để nhận ra tài khoản cũ (`chart_template.py:438`).
  - Ghi đè `code_digits = 3` cho template `vn` (chỉ có tác dụng với công ty thiết lập sau) vướng A3: tài khoản đầu tiên của `l10n_vn` là `111` (3 chữ số) nên sổ ngân hàng mới sẽ nhận mã `114` (dò từ `112`, bỏ qua `113` đã có).

## 10. Kết quả (2026-10-15)

Đã làm đủ các bước 1–8. Test: `tools/run_tests.sh l10n_vn_tt133` trên `test_fg_vas` — 9 test, 0 hỏng. Thử thêm bằng shell (rollback): công ty mới nạp `vn_tt133` có 127 tài khoản (102 − 3 cũ + 24 tổng hợp + 4 kỹ thuật), 31 thuế; `03`, `031`, `032`, `021` ở gốc cây; sổ ngân hàng mới nhận `1123` dưới 112, tài khoản tạm `021`.

Lệch so với kế hoạch:

| Mục | Kế hoạch | Thực tế | Lý do |
|---|---|---|---|
| 5 | Tên template "Vietnam - SME accounting (…)" | "SME accounting (Circular 133/2016/TT-BTC)" | Odoo tự thêm cờ và tên nước trước tên template (`ir_module.py:13`); giao diện vẫn hiện "🇻🇳 Vietnam - SME accounting (…)" như readme. |
| 8 bước 6 | Nạp template với context `l10n_check_fields_complete` | Kiểm trực tiếp khoá dữ liệu template và khoá `res.company` (`test_template_keys`) | Với context này, trường của module chưa cài gây `KeyError` (`deferred_*` của Enterprise, `account_production_wip_account_id` của `mrp_account`); `l10n_vn` cũng hỏng như vậy. Ghi ở vault `account.md` §6. |
| 8 bước 6 | Sổ ngân hàng mới nhận `1123` | Trong test là `1124` | `AccountTestInvoicingCommon` tạo sẵn sổ thẻ tín dụng, sổ này lấy tiền tố ngân hàng nên chiếm `1123`. Trên công ty thật (shell) là `1123`. |
| 4 | Báo lỗi rõ khi thuế `l10n_vn` trỏ tài khoản TT133 không có | Có, khi nạp template (`ValueError`); thêm test so mã từng tài khoản thuế của `l10n_vn` với mã TT133 cùng xmlid | |

`_post_load_data` chỉ phải gỡ cha cho `031`, `032`: Odoo không ghi lại tài khoản tạm và tài khoản chuyển tiền khi `res.company` đã có (template gán `021`, `03`). Code vẫn duyệt cả bốn cho chắc.

Chưa làm: cài qua giao diện trên một công ty mới và xem tên tiếng Việt (database `test_fg_vas` chưa kích hoạt `vi_VN`).
