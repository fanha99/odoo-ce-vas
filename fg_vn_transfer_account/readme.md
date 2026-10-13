# Ẩn tài khoản trung chuyển

Module cho Odoo 20 (Community và Enterprise), phụ thuộc module `account`.
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module thêm một thiết lập theo công ty: **ẩn các tài khoản trung chuyển khi chúng không có số dư**, và cho người dùng tự chọn những tài khoản nào được ẩn. Bản thân module không có báo cáo hay màn hình nào khác. Các sổ kế toán và phiếu in đọc thiết lập này để quyết định có trình bày các tài khoản đó hay không.

## 1. Vì sao cần

Khi chuyển tiền giữa hai tài khoản tiền (rút tiền gửi về quỹ, chuyển giữa hai ngân hàng), nghiệp vụ trong Odoo thường không được ghi thẳng Nợ tài khoản này, Có tài khoản kia. Mỗi sổ nhật ký tiền ghi một bút toán của mình, và hai bút toán gặp nhau ở một tài khoản trung gian gọi là tài khoản trung chuyển (Inter-Banks Transfer Account), khai báo trong cấu hình kế toán của công ty. Với hệ thống tài khoản Việt Nam của Odoo, đó là tài khoản 113 "Tiền đang chuyển".

Ví dụ rút 50.000.000 đồng tiền gửi ngân hàng về nhập quỹ:

| Số phiếu | Bút toán | Nợ | Có | Số tiền |
|---|---|---|---|---|
| BANK/001 | Ngân hàng chi | 113 | 112 | 50.000.000 |
| CASH/001 | Quỹ thu | 111 | 113 | 50.000.000 |

Sau hai bút toán, tài khoản 113 hết số dư. Với đơn vị áp dụng chế độ kế toán có tài khoản 113, cách ghi này đúng. Nhưng chế độ kế toán theo Thông tư 133 không có tài khoản 113: nghiệp vụ trên phải được trình bày là Nợ 111, Có 112. Nếu để nguyên, sổ sách sẽ có một tài khoản không tồn tại trong chế độ.

Odoo còn dùng các tài khoản chờ tương tự cho phiếu thu, phiếu chi đã ghi sổ nhưng chưa khớp với sao kê ngân hàng. Trong hệ thống tài khoản Việt Nam của Odoo 20, đó là 1131 "Outstanding Receipts" và 1132 "Outstanding Payments", đều là tài khoản con của 113.

## 2. Thiết lập

Vào Kế toán › Cấu hình › Thiết lập, khối **Vietnam Accounting**:

| Thiết lập | Ý nghĩa | Mặc định |
|---|---|---|
| Ẩn tài khoản trung chuyển khi không có số dư | Bật hoặc tắt việc ẩn | Tắt |
| Tài khoản được ẩn | Danh sách tài khoản áp dụng việc ẩn, do người dùng chọn. Chỉ hiện khi bật thiết lập trên. | Khi mới bật: tài khoản trung chuyển của công ty |

Thiết lập đặt riêng cho từng công ty. Nó chỉ thay đổi cách trình bày trên sổ và phiếu in; bút toán trong Odoo không bị sửa.

Gợi ý theo chế độ kế toán, cũng được ghi ngay dưới thiết lập:

| Chế độ kế toán | Nên đặt |
|---|---|
| Thông tư 133 (không có tài khoản 113) | Bật. Chọn tài khoản trung chuyển (113) và các tài khoản chờ thanh toán đang dùng (1131, 1132 hoặc các tài khoản tương ứng của đơn vị). |
| Thông tư 200, Thông tư 99 (có tài khoản 113) | Tắt. |

Một tài khoản trong danh sách còn số dư (tiền đã chi ở một đầu mà chưa ghi nhận ở đầu kia) vẫn được trình bày, để số liệu không bị thiếu.

## 3. Nơi thiết lập có tác dụng

Mỗi module dưới đây mô tả cụ thể cách nó xử lý trong readme của mình.

| Module | Tác dụng khi bật |
|---|---|
| `fg_vn_report_cdps` (Bảng cân đối số phát sinh) | Không liệt kê và không cộng các tài khoản được chọn khi chúng hết số dư. |
| `fg_vn_report_s03a` (Sổ nhật ký chung), `fg_vn_report_s03b` (Sổ cái), `vn_payment_print` (phiếu thu, phiếu chi) | Ẩn tài khoản trung chuyển và ghi tài khoản đối ứng thật thay cho nó. |

Ở thời điểm viết tài liệu này, `vn_payment_print` chưa được chuyển sang Odoo 20.

## 4. Hai bút toán trình bày như một nghiệp vụ

Quy tắc dưới đây dùng chung cho mọi sổ và phiếu in đọc thiết lập này. Nó chỉ có tác dụng khi thiết lập đang bật.

Lấy ví dụ ở mục 1, với tài khoản 113 nằm trong danh sách tài khoản được ẩn và hai dòng 113 đã đối soát với nhau.

Khi thiết lập tắt, sổ trình bày đúng như bút toán trong Odoo:

| Số chứng từ | Tài khoản | Nợ | Có |
|---|---|---|---|
| BANK/001 | 113 | 50.000.000 | |
| BANK/001 | 112 | | 50.000.000 |
| CASH/001 | 111 | 50.000.000 | |
| CASH/001 | 113 | | 50.000.000 |

Khi thiết lập bật, hai dòng 113 bị ẩn và hai bút toán mang chung một số:

| Số chứng từ | Tài khoản | Nợ | Có |
|---|---|---|---|
| BANK/001 (CASH/001) | 112 | | 50.000.000 |
| BANK/001 (CASH/001) | 111 | 50.000.000 | |

Kết quả là nghiệp vụ Nợ 111, Có 112 như Thông tư 133 yêu cầu.

Các quy tắc tạo ra kết quả trên:

| Quy tắc | Nội dung |
|---|---|
| Dòng bị ẩn | Dòng ghi vào một tài khoản thuộc danh sách tài khoản được ẩn và đã được đối soát hết. Dòng chưa đối soát, hoặc mới đối soát một phần, vẫn hiện. |
| Bút toán nối với nhau | Mỗi bên có một dòng bị ẩn trên cùng một tài khoản, thuộc cùng một lần đối soát, một bên ghi Nợ và một bên ghi Có. Các bút toán nối với nhau, trực tiếp hoặc qua bút toán khác, tạo thành một cụm. |
| Số chứng từ | Mọi bút toán của một cụm mang chung một số, dạng `chính (các bút toán còn lại, xếp theo số)`. Số này không phụ thuộc sổ nào đang in hay kỳ nào đang xem. |
| Thứ tự | Các bút toán cùng ngày của một cụm được xếp liền nhau: sổ nhật ký ngân hàng trước, tiền mặt sau, rồi tới các sổ khác; cùng loại thì bút toán có mã tài khoản nhỏ hơn đứng trước. Bút toán khác ngày nằm ở ngày của nó. |
| Bút toán chính | Bút toán đứng đầu cụm theo thứ tự trên. |

Số chứng từ trong một số tình huống:

| Tình huống | Số chứng từ trên sổ |
|---|---|
| Một bút toán ngân hàng và một bút toán quỹ, cùng ngày | `BANK/001 (CASH/001)` cho cả hai |
| Hai phiếu chi quỹ gộp vào một lần nộp ngân hàng, cùng ngày | `BANK/001 (CASH/001, CASH/002)` cho cả ba |
| Bút toán quỹ ghi ngày hôm trước, bút toán ngân hàng ghi ngày hôm sau | `CASH/001 (BANK/001)` cho cả hai; mỗi bút toán nằm ở ngày của nó |
| Dòng 113 chưa đối soát hoặc mới đối soát một phần | Mỗi bút toán giữ số của mình; dòng 113 vẫn hiện |

## 5. Cài đặt

Module được cài tự động khi cài một module báo cáo phụ thuộc nó. Cài riêng thì chỉ có thêm thiết lập ở trang cấu hình.
