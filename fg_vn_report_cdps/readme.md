# Bảng cân đối số phát sinh

Module cho Odoo 20 (Community và Enterprise).
Phụ thuộc: `fg_vn_accounting_reports` (nền tảng báo cáo) và `fg_vn_transfer_account` (cờ ẩn tài khoản trung chuyển).
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module thêm báo cáo **Bảng cân đối số phát sinh** vào menu Kế toán › Báo cáo › VAS Reports. Với mỗi tài khoản, báo cáo cho biết số dư đầu kỳ, phát sinh trong kỳ và số dư cuối kỳ, tách riêng bên Nợ và bên Có. Báo cáo xem được trên màn hình, xuất Excel, in PDF, và xuất file XML phụ lục cân đối tài khoản để nộp kèm báo cáo tài chính.

Cách dùng chung của màn hình báo cáo (chọn kỳ, tìm kiếm, xuất file, phân quyền, ngôn ngữ) mô tả trong readme của `fg_vn_accounting_reports`. Tài liệu này chỉ nói phần riêng của bảng cân đối số phát sinh. Phần kỹ thuật nằm trong `PLAN.md`.

## 1. Tham số khi mở báo cáo

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ báo cáo | Tháng hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| So sánh với | Không so sánh, kỳ trước, cùng kỳ năm trước, hoặc tự chọn khoảng ngày | Không so sánh |
| Tài khoản | Chỉ lập bảng cho các tài khoản được chọn | Tất cả |
| Hiện tài khoản không có số liệu | Liệt kê cả tài khoản không có số dư và không có phát sinh | Không |
| Hiển thị phân cấp | Xếp tài khoản theo cây cha–con | Không |
| Ngôn ngữ báo cáo | Ngôn ngữ hiển thị và in | Tiếng Việt |
| Hướng giấy, lề đối xứng, lề gáy | Dùng khi in PDF | A4 ngang |

Từ cửa sổ tham số có thể xem báo cáo, hoặc xuất thẳng Excel, PDF, XML.

## 2. Số liệu trên bảng

Mỗi dòng là một tài khoản, với sáu cột số:

| Cột | Cách tính |
|---|---|
| Dư Nợ đầu kỳ, Dư Có đầu kỳ | Luỹ kế mọi phát sinh đã ghi sổ trước ngày đầu kỳ. Chênh lệch nằm bên Nợ nếu Nợ lớn hơn Có, ngược lại nằm bên Có. |
| Phát sinh Nợ, Phát sinh Có | Tổng phát sinh đã ghi sổ trong kỳ. |
| Dư Nợ cuối kỳ, Dư Có cuối kỳ | Số dư đầu kỳ cộng phát sinh trong kỳ, trình bày như số dư đầu kỳ. |

Chỉ bút toán đã ghi sổ được tính. Bút toán nháp và bút toán đã huỷ không được tính.

**Tài khoản công nợ 131 và 331** được tính theo từng đối tác rồi mới cộng lại: các đối tác đang dư Nợ cộng vào cột Dư Nợ, các đối tác đang dư Có cộng vào cột Dư Có. Vì vậy một tài khoản công nợ có thể cùng lúc có số ở cả hai cột, đúng với yêu cầu không bù trừ công nợ giữa các đối tượng.

Dòng cuối là **Tổng cộng** của cả bảng.

## 3. Phân cấp tài khoản

Khi bật **Hiển thị phân cấp**, tài khoản được xếp theo cây cha–con khai báo trên hệ thống tài khoản (trường Tài khoản cha của từng tài khoản).

- Dòng tài khoản cha hiển thị tổng của chính nó và mọi tài khoản con, chữ đậm.
- Bấm vào tài khoản cha để mở hoặc thu gọn các con. Thu gọn một tài khoản cha thì các cấp bên dưới cũng thu gọn theo.
- Khi mới mở báo cáo, chỉ cấp cao nhất được mở.
- Tổng cộng của bảng không bị cộng trùng giữa cha và con.

Bộ lọc **Cấp tài khoản** trên màn hình dùng khi không bật phân cấp: cấp 1 chỉ hiện tài khoản có mã đến 3 chữ số, cấp 2 đến 4 chữ số, cấp 3 đến 5 chữ số. Bộ lọc được giữ khi quay lại từ màn hình chi tiết. Nó chỉ ẩn bớt dòng trên màn hình: số của các tài khoản bị ẩn không được cộng vào dòng nào, dòng Tổng cộng vẫn là tổng của mọi tài khoản, và file Excel, PDF xuất ra vẫn gồm mọi tài khoản.

## 4. So sánh với kỳ khác

Khi chọn một kỳ so sánh, bảng có thêm bốn cột: Dư Nợ cuối kỳ so sánh, Dư Có cuối kỳ so sánh, Chênh lệch số dư cuối kỳ giữa hai kỳ, và tỷ lệ phần trăm thay đổi.

| Lựa chọn | Kỳ so sánh |
|---|---|
| Không so sánh | Không có cột so sánh. |
| Kỳ trước | Kỳ liền trước. Nếu kỳ báo cáo là trọn tháng (từ ngày 1 đến ngày cuối tháng, một hay nhiều tháng) thì kỳ trước là số tháng trọn tương ứng liền trước: tháng 2 so với tháng 1, quý 2 so với quý 1, cả năm so với năm trước. Nếu không thì là khoảng có cùng số ngày, kết thúc vào ngày liền trước kỳ báo cáo. |
| Cùng kỳ năm trước | Cùng khoảng ngày của năm trước. Kỳ kết thúc ngày cuối tháng thì kỳ so sánh cũng kết thúc ngày cuối tháng (29/02/2028 so với 28/02/2027). |
| Tự chọn | Người dùng nhập ngày bắt đầu và ngày kết thúc của kỳ so sánh. |

Kỳ so sánh chọn được trong cửa sổ tham số và đổi được trong menu bộ lọc trên màn hình báo cáo.

## 5. Tài khoản ngoài bảng và tài khoản trung chuyển

**Tài khoản ngoài bảng** là tài khoản có loại "Off-Balance Sheet" trong Odoo, hoặc có mã bắt đầu bằng số 0.

- Chỉ hiện khi còn số dư đầu kỳ hoặc cuối kỳ. Tài khoản chỉ có phát sinh trong kỳ mà hai đầu đều bằng 0 thì không hiện.
- Dòng có nền cam nhạt để phân biệt, trên cả màn hình, Excel và PDF.
- Khi hiện thì được cộng vào Tổng cộng.

**Tài khoản trung chuyển.** Khi công ty bật thiết lập *Ẩn tài khoản trung chuyển khi không có số dư* (module `fg_vn_transfer_account`, dành cho đơn vị áp dụng Thông tư 133), các tài khoản mà đơn vị đã chọn trong thiết lập đó chỉ hiện khi còn số dư đầu kỳ hoặc cuối kỳ. Khi bị ẩn, tài khoản cũng không được cộng vào Tổng cộng; vì lúc đó phát sinh Nợ và Có của nó bằng nhau, Tổng Nợ và Tổng Có của bảng vẫn cân.

Quy tắc chung: Tổng cộng là tổng của mọi tài khoản không bị loại khỏi bảng theo hai quy tắc trên.

## 6. Xem chi tiết

Từ một dòng tài khoản có thể mở danh sách các phát sinh đã ghi sổ của tài khoản đó trong kỳ. Với tài khoản cha, danh sách gồm cả phát sinh của các tài khoản con.

## 7. Xuất file

- **Excel** và **PDF**: cùng nội dung với màn hình, gồm cả các cột so sánh nếu có, trừ bộ lọc Cấp tài khoản và ô tìm kiếm (hai thứ này chỉ ẩn dòng trên màn hình). Tài khoản con thụt vào theo cấp. PDF không có dòng cộng chuyển trang và không có phần ký tên.
- **XML**: file phụ lục cân đối tài khoản `F01-CDTK` (thẻ gốc `PL_CDTK`), gồm ba phần số dư đầu kỳ, số phát sinh trong kỳ, số dư cuối kỳ, mỗi phần chia Nợ và Có. File luôn gồm mọi tài khoản đang dùng có mã từ 3 chữ số trở lên, kể cả tài khoản không có số liệu, và không phụ thuộc các bộ lọc đang chọn. Tài khoản ngoài bảng không được đưa vào file. Số tiền làm tròn đến đồng.

## 8. Khác với bản 19.0

- Cây phân cấp lấy theo quan hệ tài khoản cha–con của Odoo 20. Bản 19.0 lấy theo Nhóm tài khoản, đối tượng mà Odoo 20 đã bỏ. Sau khi nâng cấp cần kiểm tra lại trường Tài khoản cha trên hệ thống tài khoản.
- Kỳ so sánh còn bốn lựa chọn: không so sánh, kỳ trước, cùng kỳ năm trước, tự chọn khoảng ngày. Bản 19.0 có sáu lựa chọn, trong đó hai lựa chọn cho cùng kết quả, và "tháng trước" tính thiếu ngày khi tháng trước dài hơn.
- Tài khoản ngoài bảng được nhận diện thêm theo loại "Off-Balance Sheet" của Odoo, ngoài quy tắc mã bắt đầu bằng 0.
- Tài khoản được ẩn là danh sách do đơn vị chọn, không chỉ một tài khoản trung chuyển.
- Tài khoản trung chuyển đang ẩn chỉ bị loại khỏi Tổng cộng khi nó hết số dư. Bản 19.0 loại cả khi nó còn số dư, làm Tổng Nợ và Tổng Có lệch nhau.
- Xem chi tiết được trên cả dòng tài khoản cha.
- Xuất XML chỉ còn một cách tính, dùng chung cho nút trên màn hình và nút ở cửa sổ tham số. Bản 19.0 có hai cách tính cho ra tổng cộng khác nhau.
- Tên tài khoản hiển thị theo ngôn ngữ báo cáo đang chọn.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch. Giấy phép đổi từ LGPL-3 sang AGPL-3.

## 9. Cài đặt

1. Chép module cùng `fg_vn_accounting_reports` và `fg_vn_transfer_account` vào thư mục addons của Odoo.
2. Cập nhật danh sách ứng dụng và cài **Bảng cân đối số phát sinh**. Hai module phụ thuộc được cài theo.

Người dùng cần có đầy đủ tính năng kế toán (nhóm `account.group_account_user`) để mở báo cáo.
