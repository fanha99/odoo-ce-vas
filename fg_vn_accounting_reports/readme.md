# Nền tảng báo cáo kế toán Việt Nam

Module cho Odoo 20 (Community và Enterprise), phụ thuộc module `account`.
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module này không chứa báo cáo nào. Nó là phần dùng chung của các sổ và báo cáo kế toán theo chế độ kế toán Việt Nam (Thông tư 133, Thông tư 200, Thông tư 99): màn hình xem báo cáo, xuất Excel và in PDF. Mỗi sổ (nhật ký chung, sổ cái, bảng cân đối phát sinh, sổ chi tiết vật tư...) là một module riêng, chỉ lo phần số liệu và mẫu biểu của mình. Nhờ vậy mọi sổ có cùng cách dùng và cùng hình thức khi in.

Tài liệu này mô tả những gì người dùng nhận được ở mọi báo cáo xây trên nền tảng. Phần kỹ thuật nằm trong `PLAN.md`.

## 1. Mở một báo cáo

Các báo cáo nằm trong menu Kế toán › Báo cáo › **VAS Reports**.

Chọn một báo cáo sẽ mở cửa sổ tham số:

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ báo cáo | Tháng hiện tại; từng báo cáo có thể đổi thành quý hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| Hiện dòng không có phát sinh | Có liệt kê các đối tượng không phát sinh trong kỳ hay không | Không |
| Ngôn ngữ báo cáo | Ngôn ngữ hiển thị và in của báo cáo, xem mục 6 | Tiếng Việt |
| Hướng giấy | A4 đứng hoặc A4 ngang, dùng khi in PDF | Đứng |
| Lề đối xứng | In hai mặt để đóng sổ: lề gáy nằm bên trái ở trang lẻ, bên phải ở trang chẵn | Không |
| Lề gáy | Độ rộng phần lề dành cho gáy sổ, tính bằng mm | 6 |

Từng báo cáo có thể thêm tham số riêng, ví dụ tài khoản hay sổ nhật ký. Từ cửa sổ này có thể xem báo cáo trên màn hình, hoặc xuất thẳng ra Excel hay PDF mà không cần xem trước.

## 2. Xem báo cáo trên màn hình

Phía trên bảng số liệu là một thanh công cụ, giống nhau ở mọi báo cáo:

- **Kỳ báo cáo.** Chọn nhanh tháng này, quý này, năm nay, tháng trước, quý trước, năm trước, hoặc tự nhập khoảng ngày.
- **Bộ lọc.** Mỗi báo cáo khai báo các bộ lọc của mình: chọn nhiều giá trị (tài khoản, đối tác, sổ nhật ký), chọn một trong danh sách, hoặc bật/tắt. Số bộ lọc đang dùng hiện ngay trên nút.
- **Tìm kiếm.** Gõ để lọc các dòng đang hiển thị, không cần tải lại số liệu.
- **Mở rộng và thu gọn.** Báo cáo có nhóm (theo tài khoản, theo mặt hàng) hoặc có nhiều cấp (tài khoản cha, con) thu gọn và mở ra được từng nhóm hoặc tất cả cùng lúc.
- **Sắp xếp.** Bấm vào tiêu đề của cột cho phép sắp xếp. Dòng số dư đầu kỳ, dòng cộng và dòng số dư cuối kỳ giữ nguyên vị trí; chỉ các dòng chi tiết bên trong đổi thứ tự.
- **Xem chi tiết.** Từ một dòng có thể mở chứng từ gốc hoặc danh sách phát sinh tạo nên con số đó. Khi quay lại, báo cáo giữ nguyên kỳ, bộ lọc, cách sắp xếp và các nhóm đang mở.

**Sổ dài.** Sổ có rất nhiều dòng (mặc định trên 2.000) không được tải hết một lần: màn hình hiện phần đầu, cho biết đã hiện bao nhiêu trên tổng số, và có nút **Xem thêm**. Các dòng cộng và số dư luôn tính trên cả sổ. Khi sổ đang ở chế độ này, không có nút mở rộng tất cả. Từng sổ mô tả cụ thể cách nó tải dần.

Tải lại trang (F5) không làm mất các lựa chọn đang có. Chúng chỉ được xoá khi đóng tab trình duyệt.

Quy ước hiển thị:

- Số tiền hiển thị không có phần thập phân; số lượng và đơn giá hiển thị hai chữ số thập phân.
- Giá trị bằng 0 để trống.
- Ngày hiển thị theo dạng năm/tháng/ngày.
- Dòng tiêu đề nhóm nền xanh nhạt; dòng số dư đầu kỳ, cộng phát sinh, số dư cuối kỳ nền lục nhạt và chữ đậm. Màu này dùng chung cho màn hình, Excel và PDF.

## 3. Xuất Excel

Nút **Excel** xuất đúng những gì đang lọc trên màn hình.

- Hai dòng đầu là tên báo cáo và kỳ báo cáo, sau đó là dòng tiêu đề cột và số liệu.
- Ô số là số thật (cộng, lọc, lập công thức được), không phải chữ.
- Báo cáo theo nhóm có thể xuất mỗi nhóm thành một sheet: sổ cái mỗi tài khoản một sheet, sổ chi tiết vật tư mỗi mặt hàng một sheet. Tên sheet lấy theo tên nhóm.

## 4. In PDF

Nút **PDF** tạo file in theo khổ A4 với các đặc điểm mà sổ kế toán Việt Nam yêu cầu:

- **Cộng chuyển trang.** Khi sổ dài hơn một trang, cuối mỗi trang có dòng "Cộng chuyển trang" ghi số luỹ kế đến hết trang đó, và đầu trang sau có dòng "Số dư đầu trang" mang số đó sang. Báo cáo chọn những cột nào được cộng dồn; cột số dư thì mang giá trị cuối cùng sang chứ không cộng.
- **Đánh số trang** dạng "Trang 3/12" ở cuối mỗi trang. Báo cáo chia theo nhóm (sổ cái, sổ chi tiết vật tư) đánh số riêng cho từng nhóm: trang thứ ba trong sáu trang của một tài khoản in "Trang 3/6", khớp với dòng "Sổ này bao gồm 6 trang" của tài khoản đó.
- **Tiêu đề lặp lại** trên mọi trang: tên công ty, tên báo cáo, kỳ báo cáo và dòng tiêu đề cột.
- **Mỗi nhóm bắt đầu ở trang mới** với báo cáo cần vậy, ví dụ sổ cái mỗi tài khoản một phần riêng. Tên nhóm được in ở đầu mọi trang của nhóm. Số luỹ kế được tính lại từ đầu cho từng nhóm.
- **Lề đối xứng** khi in hai mặt: số trang nằm ở mép ngoài, và mỗi nhóm luôn bắt đầu ở trang lẻ (thêm một trang trắng nếu cần; trang trắng không có tiêu đề và số trang).
- **Dòng không bị tách rời:** báo cáo có thể yêu cầu một dòng luôn nằm cùng trang với dòng kế tiếp, ví dụ dòng số dư đầu kỳ đi cùng dòng phát sinh đầu tiên.
- **Phần ký tên** ở cuối: Người lập biểu, Kế toán trưởng, Giám đốc, kèm ngày lập. Phần ký tên không bao giờ đứng một mình trên trang: nếu trang cuối không đủ chỗ, các dòng cuối của bảng sang trang mới cùng phần ký tên.
- **Phần ghi sổ** với các sổ cần: "Sổ này bao gồm ... trang, đánh số từ trang số 1 đến ..." và ngày mở sổ.

Sổ quá dài (mặc định trên 30.000 dòng) không in được trong một lần: hệ thống báo số dòng và đề nghị thu hẹp kỳ hoặc bộ lọc, hoặc xuất Excel. Quản trị viên đổi giới hạn này bằng tham số hệ thống `fg_vn_accounting_reports.pdf_line_limit`.

File PDF dùng phông chữ đi kèm module nên tiếng Việt hiển thị đúng trên mọi máy chủ, không phụ thuộc phông cài sẵn.

## 5. Phân quyền

Mặc định chỉ người dùng có đầy đủ tính năng kế toán (nhóm `account.group_account_user`) trở lên mới mở, xem và xuất được báo cáo. Người chỉ có quyền lập hoá đơn hoặc quyền chỉ xem kế toán không xem được.

Từng báo cáo có thể mở cho thêm nhóm khác. Ví dụ các báo cáo kho mở cho cả người dùng phân hệ Kho.

Người dùng chỉ xem được số liệu của những công ty mình được phép truy cập. Quy tắc này áp dụng như nhau cho màn hình báo cáo, xem chi tiết, và mọi đường xuất file.

## 6. Ngôn ngữ báo cáo

Sổ kế toán Việt Nam lập bằng tiếng Việt, nên báo cáo mặc định hiển thị và in bằng tiếng Việt, kể cả khi người dùng để giao diện Odoo bằng ngôn ngữ khác.

Ngôn ngữ báo cáo chọn được ở hai nơi:

- Trong cửa sổ tham số, mỗi lần mở báo cáo.
- Trong menu bộ lọc trên màn hình báo cáo, để đổi khi đang xem.

Lựa chọn này quyết định ngôn ngữ của tên báo cáo, tiêu đề cột, nội dung các dòng (tên tài khoản, dòng cộng), và toàn bộ file Excel, PDF, gồm cả dòng cộng chuyển trang và phần ký tên. Các nút và menu trên thanh công cụ vẫn theo ngôn ngữ giao diện của người dùng.

Lựa chọn không được nhớ: lần mở báo cáo sau lại bắt đầu bằng tiếng Việt.

Danh sách chỉ gồm các ngôn ngữ đã cài trong database. Database chưa cài tiếng Việt thì báo cáo mặc định theo ngôn ngữ của người dùng. Ngôn ngữ gốc của module là tiếng Anh; tiếng Việt là bản dịch đi kèm.

## 7. Số chứng từ trên sổ sách

Mặc định, cột Số chứng từ của các sổ in số của bút toán trong Odoo. Hai thiết lập trên form của từng sổ nhật ký (Kế toán › Cấu hình › Sổ nhật ký, ngay dưới ô Mã ngắn) đổi số được in cho các bút toán của sổ nhật ký đó:

| Thiết lập | Tác dụng | Ví dụ |
|---|---|---|
| **Dùng số tham chiếu làm số chứng từ** | In nội dung ô Tham chiếu của bút toán thay cho số của nó. Bút toán không có tham chiếu vẫn in số của nó. | Bút toán `BNK1/2026/00007` có tham chiếu `GBC-0042` được in là `GBC-0042`. |
| **Cắt số thứ tự cuối khỏi số chứng từ** | Bỏ phần `/số` ở cuối. Chỉ cắt khi phần sau dấu `/` cuối cùng toàn là chữ số. | `BL/2025/12/16` được in là `BL/2025/12`; `BL/2025/DK` giữ nguyên. |

Bật cả hai thì lấy số tham chiếu trước rồi mới cắt.

Thiết lập có tác dụng trên sổ nhật ký chung và sổ cái, kể cả số chứng từ ghép của các bút toán nối qua tài khoản trung chuyển (`GBC-0042 (PT/2026)`). Trên hai sổ này:

- các dòng xếp theo ngày, rồi theo **số được in**; các bút toán được in cùng một số thì xếp theo số của chính chúng;
- ô tìm kiếm của sổ nhật ký chung tìm theo số được in.

Các sổ và báo cáo khác không đổi. Bút toán trong Odoo không bị sửa: thiết lập chỉ quyết định số nào được in.

## 8. Tài khoản ngoài chế độ: mã bắt đầu bằng `0`

**Đọc mục này trước khi dùng các sổ với hệ thống tài khoản của Odoo, nhất là theo Thông tư 200 hoặc Thông tư 99.**

### 8.1. Vấn đề

Để chạy nghiệp vụ ngân hàng, Odoo cần vài tài khoản kỹ thuật mà chế độ kế toán Việt Nam không có: tài khoản tạm cho dòng sao kê chưa đối soát, và tài khoản chờ cho phiếu thu, phiếu chi chưa khớp với sao kê. Khi thiết lập kế toán cho công ty, Odoo **tự tạo** các tài khoản này, đặt mã như tài khoản bình thường và gắn chúng vào cây tài khoản của chế độ. Với hệ thống tài khoản Việt Nam của Odoo 20 (`l10n_vn`, theo Thông tư 200):

| Mã Odoo đặt | Tên | Vai trò | Tài khoản cha | Vấn đề |
|---|---|---|---|---|
| 1121 | Tài khoản tạm thời ngân hàng (Bank Suspense Account) | dòng sao kê chưa đối soát | 1120 Tiền gửi không kỳ hạn | Trùng mã 1121 "Tiền Việt Nam" của chế độ |
| 1131 | Biên lai chưa thanh toán (Outstanding Receipts) | phiếu thu chưa khớp sao kê | 1130 Tiền đang chuyển | Trùng mã 1131 "Tiền Việt Nam" của chế độ |
| 1132 | Khoản chi chưa thanh toán (Outstanding Payments) | phiếu chi chưa khớp sao kê | 1130 Tiền đang chuyển | Trùng mã 1132 "Ngoại tệ" của chế độ |

Các sổ không có cách nào biết 1121 kia là tài khoản tạm của Odoo chứ không phải "Tiền Việt Nam": nó được in lên sổ cái, bảng cân đối số phát sinh như một tài khoản của chế độ, đưa vào file XML phụ lục cân đối tài khoản, và phát sinh của nó được cộng vào tài khoản cha 1120.

### 8.2. Quy tắc của các sổ

Bảng cân đối số phát sinh và sổ cái coi **tài khoản có mã bắt đầu bằng `0`** (và tài khoản loại "Off-Balance Sheet" của Odoo) là tài khoản ngoài chế độ:

- Trên màn hình, Excel, PDF: chỉ trình bày khi còn số dư đầu kỳ hoặc cuối kỳ, dòng nền cam. Khi đã đối soát hết (số dư về 0, kể cả có phát sinh trong kỳ) thì không trình bày.
- Trong file XML phụ lục cân đối tài khoản: **không bao giờ** có, và không cộng vào tài khoản cha hay dòng tổng cộng.

Quy tắc này thay cho cách của bản 17.0 (tài khoản không thuộc nhóm tài khoản nào thì không in, không xuất XML); Odoo 20 đã bỏ nhóm tài khoản.

**Độ dài mã không ảnh hưởng.** Chỉ xét ký tự đầu là `0`: `03`, `09`, `031`, `0123`, `01001` đều là tài khoản ngoài chế độ. Vì vậy quy ước mã ở mục 8.3 (`03`, `031`, `032`, `021`…) đặt mã dài hơn hai ký tự mà vẫn được xử lý như trên. Trong XML, điều kiện "mã từ 3 ký tự trở lên" chỉ xét sau khi đã loại tài khoản đầu `0`, nên mã đầu `0` dài bao nhiêu cũng không vào XML. (Code: `_is_off_balance()` trong `fg_vn_report_cdps/models/cdps_report.py` và `fg_vn_report_s03b/models/s03b_report.py` so `code.startswith('0')`; `get_xml()` lọc bằng hàm này trước. Test `test_xml_leaves_off_balance_accounts_out` kiểm với tài khoản `0091`, `0092`.)

Lưu ý thêm:

- Nếu tài khoản đầu `0` vẫn được gắn tài khoản cha (vd. nằm dưới 112): trong XML nó không được cộng lên cha; nhưng trên màn hình, Excel, PDF của bảng cân đối số phát sinh ở chế độ phân cấp, khi nó còn số dư và được trình bày thì số của nó **được cộng vào dòng tài khoản cha**. Vì vậy nên xoá tài khoản cha của các tài khoản này (mục 8.3).
- Quy tắc áp dụng ở **bảng cân đối số phát sinh** và **sổ cái** (với sổ cái: tài khoản đầu `0` không có số dư vẫn được in nếu người dùng chọn đích danh nó trong bộ lọc tài khoản). **Sổ nhật ký chung không áp dụng**: dòng ghi vào tài khoản đầu `0` vẫn được in; sổ này chỉ ẩn dòng của các tài khoản trong danh sách ẩn của `fg_vn_transfer_account` khi dòng đã đối soát hết. Muốn sổ nhật ký chung không in các dòng đó thì thêm tài khoản vào danh sách ẩn.

### 8.3. Quy ước mã và việc người dùng phải làm

**Quy ước mã.** Tài khoản kỹ thuật lấy mã của tài khoản Odoo tương ứng ở hệ thống tài khoản `l10n_vn`, thay `11` ở đầu bằng `0` (113 → `03`, 1131 → `031`, 1121 → `021`); và **không có tài khoản cha** (đứng ở gốc cây), ở mọi hệ thống tài khoản. Nhờ vậy mọi công ty, dù theo thông tư nào, có cùng mã tài khoản kỹ thuật, dễ đối chiếu với tài liệu của Odoo.

| Vai trò trong Odoo | Mã Odoo (`l10n_vn`) | Mã theo quy ước | Tài khoản cha |
|---|---|---|---|
| Tài khoản trung chuyển (Money in transit) | 113 | **03** (chỉ Thông tư 133, xem bảng dưới) | — |
| Tài khoản chờ thu (Outstanding Receipts) | 1131 | **031** | để trống |
| Tài khoản chờ chi (Outstanding Payments) | 1132 | **032** | để trống |
| Tài khoản tạm ngân hàng (Bank Suspense Account) | 1121 | **021** | để trống (không nằm dưới 112) |

Họ `03x` ứng với 113, họ `02x` ứng với 112, họ `01x` để dành cho 111 (tiền mặt) nếu sau này cần. Odoo tạo thêm tài khoản kỹ thuật khác thì đánh tiếp trong họ tương ứng (`033`, `022`…). Mã dài bao nhiêu cũng được xử lý như nhau (mục 8.2).

**Việc người dùng phải làm.** Ngay sau khi thiết lập kế toán cho công ty, **trước khi nhập phát sinh**, vào Kế toán › Cấu hình › Hệ thống tài khoản và với từng tài khoản kỹ thuật Odoo tự tạo:

1. **Đổi mã** theo bảng trên.
2. **Xoá tài khoản cha**, để tài khoản kỹ thuật không nằm lẫn dưới 112, 113 trên cây tài khoản và không bị cộng vào dòng của tài khoản cha trên bảng cân đối số phát sinh khi còn số dư.

Không đổi loại tài khoản sang "Off-Balance Sheet": Odoo bắt mọi dòng của bút toán có dòng ngoài bảng cũng phải là ngoài bảng, nên các tài khoản này sẽ không dùng được nữa.

Kiểm tra lại sau mỗi lần Odoo có thể tạo thêm tài khoản kỹ thuật (thêm công ty, thiết lập lại hệ thống tài khoản).

| Chế độ kế toán | Hệ thống tài khoản | Cần làm |
|---|---|---|
| Thông tư 200, Thông tư 99 | `l10n_vn` của Odoo | 1121 → `021`, xoá cha. 1131 → `031`, 1132 → `032`, xoá cha (cha 113 là tài khoản của chế độ). **Giữ 113 (1130) "Tiền đang chuyển"**: đây là tài khoản của chế độ, không đổi thành `03`. |
| Thông tư 133 | `l10n_vn_tt133` | Không cần: module tạo sẵn `03`, `031`, `032`, `021`, không có tài khoản cha. |
| Hệ thống tài khoản tự làm | — | Tìm tài khoản trung chuyển, tài khoản tạm (Kế toán › Cấu hình › Thiết lập, mục ngân hàng) và tài khoản chờ (phương thức thanh toán của từng sổ ngân hàng), xử lý theo quy ước. |

Đơn vị tự thêm tài khoản nội bộ không muốn đưa lên sổ theo chế độ cũng đặt mã bắt đầu bằng `0`, ngoài các họ `01x`, `02x`, `03x` (vd. `09x`).

### 8.4. Sau khi đối soát, tài khoản kỹ thuật còn phát sinh không

Đọc từ code Odoo 20 (Community) và Odoo 19 (Enterprise, `account_accountant`); chưa chạy thử trên 20.0.

| Tài khoản | Sau khi đối soát hết | Vì sao |
|---|---|---|
| Tạm ngân hàng (`021`, 1121 của Odoo) | **Không còn phát sinh.** | Dòng sao kê được ghi sổ ngay khi nhập, đối ứng là tài khoản tạm. Khi đối soát, Odoo **sửa chính bút toán của dòng sao kê**: dòng tài khoản tạm được thay bằng tài khoản đối ứng thật. Ghi chú trong lõi (`account/models/res_config_settings.py`, trường Bank Suspense): *"Reconciliation replaces the latter by the definitive account(s)."* Bản Enterprise 19 làm như vậy (`_set_move_line_to_statement_line_move`), `account_reconcile_oca` ở chế độ sửa bút toán cũng vậy. Còn phát sinh chỉ khi dòng sao kê chưa đối soát hoặc mới đối soát một phần. |
| Chờ thu, chờ chi (`031`, `032`; 1131, 1132 của Odoo) | **Mặc định không dùng tới.** Nếu dùng thì **còn phát sinh hai bên, số dư bằng 0.** | Thanh toán chỉ sinh bút toán khi phương thức thanh toán của sổ ngân hàng có khai tài khoản chờ (`payment_account_id`; `account_payment.py`: chỉ tạo bút toán khi `outstanding_account_id` có giá trị). `l10n_vn` không gán tài khoản chờ cho phương thức thanh toán (khác `l10n_in`, `l10n_ma`), nên mặc định phiếu thu/chi ngân hàng không có bút toán và hoá đơn được đối soát thẳng với dòng sao kê. Nếu người dùng khai tài khoản chờ: phiếu thu ghi Nợ `031` / Có 131, dòng sao kê khi đối soát ghi Có `031` và hai dòng được đối soát với nhau. Hai bút toán khác nhau, nên `031` có phát sinh cả Nợ lẫn Có, như tài khoản trung chuyển. |
| Trung chuyển (`03`, 113) | Còn phát sinh hai bên, số dư bằng 0. | Hai bút toán của hai sổ tiền gặp nhau ở tài khoản này. |

Hệ quả cho các sổ:

- Bảng cân đối số phát sinh, sổ cái: cả ba loại đều chỉ trình bày khi còn số dư (quy tắc đầu `0`), nên phát sinh hai bên của `03`, `031`, `032` không lên sổ khi đã khớp hết.
- Sổ nhật ký chung không áp quy tắc đầu `0`: muốn không in các dòng của `03`, `031`, `032` thì thêm chúng vào danh sách ẩn của `fg_vn_transfer_account` (dòng đã đối soát hết thì ẩn, hai bút toán trình bày như một nghiệp vụ).
- Tài khoản tạm `021`: vì Odoo sửa lại bút toán của dòng sao kê khi đối soát, đối soát dòng sao kê của tháng trước vào tháng sau sẽ **làm thay đổi số liệu của tháng trước** (dòng tài khoản tạm biến mất, thay bằng tài khoản thật, ngày bút toán giữ nguyên). Sổ của tháng trước in ra trước và sau khi đối soát sẽ khác nhau.

### 8.5. Các thông tư khác nhau ở đâu

Các sổ (nhật ký chung, sổ cái, bảng cân đối số phát sinh) tính như nhau cho Thông tư 133, 200 và 99. Khác nhau chủ yếu ở việc tài khoản nào được trình bày trên PDF và đưa vào XML:

- Tài khoản kỹ thuật của Odoo: xử lý theo mục 8.3.
- Tài khoản trung chuyển (113): Thông tư 133 không có tài khoản này nên phải ẩn đi qua module `fg_vn_transfer_account`; Thông tư 200, 99 có 113 nên để nguyên.
- Mã tài khoản cấp 1: hệ thống tài khoản `l10n_vn` của Odoo thêm số 0 vào cuối mọi mã 3 chữ số (131 thành 1310, 911 thành 9110). Sổ in đúng mã đang có trên hệ thống tài khoản; thẻ XML và bộ lọc "Cấp tài khoản" của bảng cân đối số phát sinh hiện dựa vào mã nên chưa đúng với các mã này. Người dùng có thể tự đổi mã về 3 chữ số (đổi được cả khi đã có phát sinh, và cập nhật module `l10n_vn` không đổi lại). Việc xử lý trong module chưa làm.
- File XML phụ lục cân đối tài khoản theo mẫu của Thông tư 133. Đơn vị theo Thông tư 200, 99 có nhiều tài khoản không có trong danh mục của mẫu này nên không đưa được vào XML. Hiện bảng cân đối số phát sinh xuất một thẻ cho mọi tài khoản có mã từ 3 ký tự (trừ tài khoản ngoài chế độ); chưa lọc theo danh mục của mẫu.

## 9. Các báo cáo dùng nền tảng này

`fg_vn_report_cdps`, `fg_vn_report_s03a` và `fg_vn_report_s03b` đã có trên 20.0; các module còn lại thuộc bản 19.0 và chuyển sau.

| Module | Báo cáo |
|---|---|
| `fg_vn_report_s03a` | Sổ nhật ký chung |
| `fg_vn_report_s03b` | Sổ cái tài khoản |
| `fg_vn_report_cdps` | Bảng cân đối phát sinh |
| `fg_vn_stock_reports` | Sổ chi tiết vật tư hàng hoá, Bảng tổng hợp tồn kho |
| `fg_vn_asset_adapter` | Theo dõi tài sản, phân bổ công cụ dụng cụ, khấu hao và hao mòn luỹ kế tài sản cố định |

`fg_vn_financial_reports` (báo cáo tài chính B01, B02, lưu chuyển tiền tệ, B09) chỉ dùng chung menu **VAS Reports**, không dùng màn hình và phần in của nền tảng.

## 10. Khác với bản 19.0

- Không còn phụ thuộc module `stock` và `stock_account`. Cài nền tảng không kéo theo phân hệ kho.
- Bỏ bộ máy lập báo cáo tài chính từ mẫu XML. Không còn báo cáo nào dùng nó.
- Bỏ đường in PDF cũ qua wkhtmltopdf. Mọi báo cáo in bằng một đường duy nhất có cộng chuyển trang.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch (mục 6). Bản 19.0 viết thẳng tiếng Việt.
- Giấy phép đổi từ LGPL-3 sang AGPL-3.
- Hai thiết lập số chứng từ của sổ nhật ký (mục 7) nằm trong module này. Ở bản 17.0 chúng từng là module riêng `fg_account_journal_ext`; bản 19.0 chưa có.

## 11. Cài đặt

1. Chép module vào thư mục addons của Odoo.
2. Cập nhật danh sách ứng dụng. Module được cài tự động khi cài một module báo cáo phụ thuộc nó; cài riêng thì chỉ thấy menu **VAS Reports** trống.

Máy chủ cần hai thư viện Python `reportlab` và `xlsxwriter`; cả hai có sẵn trong bộ cài chuẩn của Odoo 20.
