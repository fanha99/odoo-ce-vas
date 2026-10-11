# Nền tảng báo cáo kế toán Việt Nam

Module cho Odoo 20 (Community và Enterprise), phụ thuộc module `account`.
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module này không chứa báo cáo nào. Nó là phần dùng chung của các sổ và báo cáo kế toán theo chế độ kế toán Việt Nam (Thông tư 133 và Thông tư 99): màn hình xem báo cáo, xuất Excel và in PDF. Mỗi sổ (nhật ký chung, sổ cái, bảng cân đối phát sinh, sổ chi tiết vật tư...) là một module riêng, chỉ lo phần số liệu và mẫu biểu của mình. Nhờ vậy mọi sổ có cùng cách dùng và cùng hình thức khi in.

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
- **Đánh số trang** dạng "Trang 3/12" ở cuối mỗi trang.
- **Tiêu đề lặp lại** trên mọi trang: tên công ty, tên báo cáo, kỳ báo cáo và dòng tiêu đề cột.
- **Mỗi nhóm bắt đầu ở trang mới** với báo cáo cần vậy, ví dụ sổ cái mỗi tài khoản một phần riêng. Tên nhóm được in ở đầu mọi trang của nhóm. Số luỹ kế được tính lại từ đầu cho từng nhóm.
- **Lề đối xứng** khi in hai mặt: số trang nằm ở mép ngoài, và mỗi nhóm luôn bắt đầu ở trang lẻ (thêm một trang trắng nếu cần; trang trắng không có tiêu đề và số trang).
- **Dòng không bị tách rời:** báo cáo có thể yêu cầu một dòng luôn nằm cùng trang với dòng kế tiếp, ví dụ dòng số dư đầu kỳ đi cùng dòng phát sinh đầu tiên.
- **Phần ký tên** ở cuối: Người lập biểu, Kế toán trưởng, Giám đốc, kèm ngày lập.
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

## 7. Các báo cáo dùng nền tảng này

`fg_vn_report_cdps`, `fg_vn_report_s03a` và `fg_vn_report_s03b` đã có trên 20.0; các module còn lại thuộc bản 19.0 và chuyển sau.

| Module | Báo cáo |
|---|---|
| `fg_vn_report_s03a` | Sổ nhật ký chung |
| `fg_vn_report_s03b` | Sổ cái tài khoản |
| `fg_vn_report_cdps` | Bảng cân đối phát sinh |
| `fg_vn_stock_reports` | Sổ chi tiết vật tư hàng hoá, Bảng tổng hợp tồn kho |
| `fg_vn_asset_adapter` | Theo dõi tài sản, phân bổ công cụ dụng cụ, khấu hao và hao mòn luỹ kế tài sản cố định |

`fg_vn_financial_reports` (báo cáo tài chính B01, B02, lưu chuyển tiền tệ, B09) chỉ dùng chung menu **VAS Reports**, không dùng màn hình và phần in của nền tảng.

## 8. Khác với bản 19.0

- Không còn phụ thuộc module `stock` và `stock_account`. Cài nền tảng không kéo theo phân hệ kho.
- Bỏ bộ máy lập báo cáo tài chính từ mẫu XML. Không còn báo cáo nào dùng nó.
- Bỏ đường in PDF cũ qua wkhtmltopdf. Mọi báo cáo in bằng một đường duy nhất có cộng chuyển trang.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch (mục 6). Bản 19.0 viết thẳng tiếng Việt.
- Giấy phép đổi từ LGPL-3 sang AGPL-3.

## 9. Cài đặt

1. Chép module vào thư mục addons của Odoo.
2. Cập nhật danh sách ứng dụng. Module được cài tự động khi cài một module báo cáo phụ thuộc nó; cài riêng thì chỉ thấy menu **VAS Reports** trống.

Máy chủ cần hai thư viện Python `reportlab` và `xlsxwriter`; cả hai có sẵn trong bộ cài chuẩn của Odoo 20.
