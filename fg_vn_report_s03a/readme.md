# Sổ nhật ký chung (S03a-DNN)

Module cho Odoo 20 (Community và Enterprise).
Phụ thuộc: `fg_vn_accounting_reports` (nền tảng báo cáo) và `fg_vn_transfer_account` (thiết lập ẩn tài khoản trung chuyển).
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module thêm **Sổ nhật ký chung** vào menu Kế toán › Báo cáo › VAS Reports. Sổ liệt kê mọi bút toán đã ghi sổ trong kỳ theo thứ tự thời gian, mỗi dòng bút toán một dòng sổ, với tài khoản ghi Nợ, tài khoản ghi Có và số tiền. Sổ xem được trên màn hình, xuất Excel và in PDF theo mẫu S03a-DNN.

Cách dùng chung của màn hình báo cáo (chọn kỳ, xuất file, ngôn ngữ, phân quyền) mô tả trong readme của `fg_vn_accounting_reports`. Tài liệu này chỉ nói phần riêng của sổ nhật ký chung. Phần kỹ thuật nằm trong `PLAN.md`.

## 1. Tham số khi mở sổ

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ ghi sổ | Quý hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| Sổ nhật ký | Chỉ lấy bút toán của các sổ nhật ký được chọn | Tất cả |
| Loại chứng từ | Tất cả, bút toán khác, hoá đơn bán, hoá đơn mua, hoá đơn bán điều chỉnh giảm, hoá đơn mua điều chỉnh giảm | Tất cả |
| Tài khoản | Chỉ lấy các dòng ghi vào những tài khoản được chọn | Tất cả |
| Đối tác | Chỉ lấy các dòng của những đối tác được chọn | Tất cả |
| Ngôn ngữ báo cáo | Ngôn ngữ hiển thị và in | Tiếng Việt |
| Hướng giấy, lề đối xứng, lề gáy | Dùng khi in PDF | A4 đứng |

Bộ lọc Tài khoản và Đối tác chọn **dòng**: sổ chỉ còn các dòng khớp, nên một bút toán có thể chỉ hiện một phần và dòng Cộng có thể có tổng Nợ khác tổng Có.

## 2. Nội dung sổ

| Cột | Nội dung |
|---|---|
| Ngày | Ngày ghi sổ của bút toán. Với hoá đơn có ngày hoá đơn khác ngày ghi sổ, ngày hoá đơn hiện trong ngoặc: `2026/01/05 (2026/01/03)`. |
| Số chứng từ | Số của bút toán. |
| Diễn giải | Nhãn của dòng bút toán; nếu dòng không có nhãn thì lấy nội dung tham chiếu của bút toán. |
| TK Nợ, TK Có | Tài khoản của dòng, đặt ở cột Nợ nếu dòng ghi Nợ, ở cột Có nếu dòng ghi Có. |
| Số tiền Nợ, Số tiền Có | Số tiền của dòng, theo đồng tiền hạch toán. |

Các bút toán xếp theo ngày ghi sổ, rồi theo số chứng từ. Dòng cuối sổ là **Cộng**: tổng số tiền Nợ và tổng số tiền Có của kỳ.

Chỉ bút toán đã ghi sổ được đưa vào sổ. Các dòng ghi chú và tiêu đề mục của hoá đơn, và các dòng có số tiền bằng 0, không được đưa vào.

Ô tìm kiếm lọc các dòng theo số chứng từ, diễn giải và tài khoản.

**Sổ dài.** Khi kỳ có trên 2.000 dòng, màn hình hiện 500 dòng đầu; cuối bảng cho biết đã hiện bao nhiêu trên tổng số và có nút **Xem thêm** để tải 500 dòng tiếp theo. Dòng Cộng luôn là tổng của cả kỳ, không phải của phần đang hiện. Lúc này ô tìm kiếm tìm trên cả kỳ. Excel và PDF luôn xuất cả sổ.

Từ một dòng có thể mở bút toán gốc.

## 3. Ẩn tài khoản trung chuyển

Phần này chỉ có tác dụng khi công ty bật thiết lập *Ẩn tài khoản trung chuyển khi không có số dư* của module `fg_vn_transfer_account`, dành cho đơn vị áp dụng Thông tư 133.

Khi nộp tiền mặt vào ngân hàng, Odoo có hai bút toán gặp nhau ở tài khoản trung chuyển:

| Bút toán | Diễn giải | Tài khoản | Nợ | Có |
|---|---|---|---|---|
| CASH/001 | Nộp tiền vào tài khoản | 1111 | | 100 |
| CASH/001 | Nộp tiền vào tài khoản | 113 | 100 | |
| BANK/001 | A nộp tiền | 1121 | 100 | |
| BANK/001 | A nộp tiền | 113 | | 100 |

Hai dòng 113 đã được đối soát với nhau. Trên sổ, chúng được ẩn và hai bút toán được trình bày như một nghiệp vụ:

| Số chứng từ | Diễn giải | TK Nợ | TK Có | Nợ | Có |
|---|---|---|---|---|---|
| BANK/001 (CASH/001) | A nộp tiền | 1121 | | 100 | |
| BANK/001 (CASH/001) | Nộp tiền vào tài khoản | | 1111 | | 100 |

Quy tắc:

- **Dòng nào bị ẩn:** dòng ghi vào một tài khoản thuộc danh sách tài khoản được ẩn của công ty **và** đã được đối soát hết. Dòng chưa đối soát vẫn hiện, để kế toán biết còn khoản treo cần xử lý.
- **Số chứng từ:** các bút toán nối với nhau qua các dòng bị ẩn dùng chung một số, dạng `chính (các bút toán còn lại)`. Bút toán chính là bút toán ngân hàng nếu có; nhiều phiếu gộp vào một lần nộp thì thành `BANK/001 (CASH/001, CASH/002)`.
- **Thứ tự:** các bút toán nối với nhau và cùng ngày được xếp liền nhau, bút toán ngân hàng trước, bút toán tiền mặt sau.
- **Khác ngày:** mỗi bút toán nằm ở ngày của nó, nhưng vẫn mang số chứng từ ghép, kể cả khi bút toán kia nằm ngoài kỳ đang xem.

Quy tắc trên áp dụng cho mọi tài khoản trong danh sách được ẩn, nên cũng dùng được cho tài khoản chờ của phiếu thu, phiếu chi (ví dụ 1131, 1132) nếu đơn vị đưa chúng vào danh sách: phiếu thu và dòng sao kê ngân hàng đã khớp với nhau được trình bày thành một nghiệp vụ.

Lưu ý: khi một nghiệp vụ có hai bút toán nằm ở hai kỳ khác nhau, kỳ nào cũng chỉ có một nửa của nó. Dòng Cộng của kỳ đó sẽ có tổng Nợ khác tổng Có đúng bằng số tiền của các dòng bị ẩn.

## 4. Xuất file

- **Excel:** cùng các cột với màn hình, có dòng Cộng.
- **PDF:** mẫu S03a-DNN, A4 đứng hoặc ngang. Sổ quá dài không in được trong một lần: hệ thống báo số dòng và đề nghị thu hẹp kỳ hoặc bộ lọc. Cuối mỗi trang có dòng "Cộng chuyển trang" cho hai cột số tiền, đầu trang sau mang số đó sang. Cuối sổ có dòng "Sổ này bao gồm ... trang", ngày mở sổ và phần ký tên.

Excel và PDF xuất theo kỳ và các bộ lọc đang chọn. Ô tìm kiếm chỉ lọc trên màn hình.

## 5. Khác với bản 19.0

- Sổ dài được tải dần thay vì tải hết một lần.
- Các bộ lọc Sổ nhật ký, Loại chứng từ, Tài khoản, Đối tác có tác dụng. Ở bản 19.0 chúng có trên cửa sổ tham số và trên màn hình nhưng sổ luôn liệt kê mọi bút toán.
- Ô tìm kiếm lọc theo dòng. Ở bản 19.0 gõ bất cứ gì vào ô tìm kiếm cũng làm sổ trống.
- Dòng ghi chú, tiêu đề mục và dòng bằng 0 không còn xuất hiện trên sổ.
- Việc ẩn áp dụng cho danh sách tài khoản do đơn vị chọn, không chỉ một tài khoản trung chuyển.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch. Giấy phép đổi từ LGPL-3 sang AGPL-3.

## 6. Cài đặt

Chép module cùng `fg_vn_accounting_reports` và `fg_vn_transfer_account` vào thư mục addons, cập nhật danh sách ứng dụng và cài **Sổ nhật ký chung**. Người dùng cần có đầy đủ tính năng kế toán (nhóm `account.group_account_user`) để mở sổ.
