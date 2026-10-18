# Sổ cái tài khoản (S03b-DNN)

Module cho Odoo 20 (Community và Enterprise).
Phụ thuộc: `fg_vn_accounting_reports` (nền tảng báo cáo), `fg_account_counterpart` (đối ứng tài khoản) và `fg_vn_transfer_account` (thiết lập ẩn tài khoản trung chuyển).
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module thêm **Sổ cái tài khoản** vào menu Kế toán › Báo cáo › VAS Reports. Với mỗi tài khoản, sổ cho biết số dư đầu kỳ, từng phát sinh trong kỳ kèm tài khoản đối ứng, tổng phát sinh và số dư cuối kỳ. Sổ xem được trên màn hình, xuất Excel (mỗi tài khoản một sheet) và in PDF theo mẫu S03b-DNN (mỗi tài khoản bắt đầu ở trang mới).

Cách dùng chung của màn hình báo cáo (chọn kỳ, xuất file, ngôn ngữ, phân quyền) mô tả trong readme của `fg_vn_accounting_reports`. Tài liệu này chỉ nói phần riêng của sổ cái. Phần kỹ thuật nằm trong `PLAN.md`.

## 1. Tham số khi mở sổ

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ ghi sổ | Quý hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| Tài khoản | Chỉ lập sổ cho các tài khoản được chọn | Tất cả |
| Loại tài khoản | Tất cả, tài sản, nợ phải trả, vốn chủ sở hữu, doanh thu, chi phí | Tất cả |
| Đối tác | Chỉ tính các phát sinh của những đối tác được chọn | Tất cả |
| Sổ nhật ký | Chỉ tính các phát sinh thuộc những sổ nhật ký được chọn | Tất cả |
| Tài khoản không có phát sinh | Không lập sổ; lập sổ nếu có số dư đầu kỳ; hoặc lập sổ cho mọi tài khoản | Không lập sổ |
| Tách dòng theo tài khoản đối ứng | Mỗi tài khoản đối ứng của một phát sinh thành một dòng riêng, xem mục 3 | Không |
| Ngôn ngữ báo cáo | Ngôn ngữ hiển thị và in | Tiếng Việt |
| Hướng giấy, lề đối xứng, lề gáy | Dùng khi in PDF | A4 đứng |

Bộ lọc Đối tác và Sổ nhật ký áp dụng cho cả số dư đầu kỳ: chọn một khách hàng thì sổ của 131 là sổ chi tiết công nợ của riêng khách hàng đó, với số dư đầu kỳ của riêng họ.

## 2. Nội dung sổ của một tài khoản

Mỗi tài khoản là một phần riêng, bắt đầu bằng dòng tiêu đề "Tài khoản: mã - tên", gồm:

| Dòng | Nội dung |
|---|---|
| Số dư đầu kỳ | Luỹ kế mọi phát sinh đã ghi sổ trước ngày đầu kỳ. Nằm ở cột Nợ nếu Nợ lớn hơn Có, ngược lại ở cột Có. |
| Các phát sinh | Mỗi dòng bút toán ghi vào tài khoản trong kỳ là một dòng, xếp như trên sổ nhật ký chung: theo ngày ghi sổ, rồi theo số chứng từ được in, rồi theo số của bút toán. |
| Cộng phát sinh | Tổng Nợ và tổng Có của các phát sinh trong kỳ. |
| Số dư cuối kỳ | Số dư đầu kỳ cộng phát sinh trong kỳ, trình bày như số dư đầu kỳ. |

Các cột của một dòng phát sinh:

| Cột | Nội dung |
|---|---|
| Ngày | Ngày ghi sổ. Với hoá đơn có ngày hoá đơn khác ngày ghi sổ, ngày hoá đơn hiện trong ngoặc. |
| Số chứng từ | Số của bút toán, hoặc số tham chiếu của nó, tuỳ thiết lập của sổ nhật ký (xem `fg_vn_accounting_reports/readme.md`, mục 7). |
| Diễn giải | Nhãn của dòng bút toán; nếu không có thì lấy nội dung tham chiếu của bút toán. |
| TK đối ứng | Mã các tài khoản đối ứng của dòng, cách nhau bằng dấu phẩy. |
| Nợ, Có | Số tiền của dòng, theo đồng tiền hạch toán. |

Chỉ bút toán đã ghi sổ được tính. Dòng bút toán có số tiền bằng 0 không được đưa vào sổ.

Mặc định, chỉ tài khoản có phát sinh trong kỳ được lập sổ. Tham số *Tài khoản không có phát sinh* cho phép lập thêm sổ cho các tài khoản còn số dư đầu kỳ, hoặc cho mọi tài khoản.

**Sổ dài.** Khi kỳ có trên 2.000 dòng, sổ mở ra với các tài khoản ở trạng thái thu gọn: mỗi tài khoản hiện số dư đầu kỳ, cộng phát sinh và số dư cuối kỳ. Mở một tài khoản thì 500 dòng phát sinh đầu của nó được tải; nút **Xem thêm** tải tiếp. Ở chế độ này không có nút mở rộng tất cả. Excel và PDF luôn xuất cả sổ.

Trên màn hình, bấm vào dòng tiêu đề của một tài khoản để thu gọn hoặc mở sổ của nó. Ô tìm kiếm lọc theo mã và tên tài khoản. Từ một dòng phát sinh có thể mở bút toán gốc; từ dòng tiêu đề có thể mở danh sách phát sinh của tài khoản trong kỳ.

## 3. Tài khoản đối ứng

Cột TK đối ứng lấy từ module `fg_account_counterpart`, module xác định dòng Nợ nào đi với dòng Có nào khi bút toán được ghi sổ. Ví dụ trên sổ cái 131, dòng của một hoá đơn bán hàng có TK đối ứng là `33311, 511`.

**Tách dòng theo tài khoản đối ứng.** Khi bật tuỳ chọn này, dòng 131 của hoá đơn trên được in thành hai dòng: một dòng đối ứng 33311 với số tiền thuế, một dòng đối ứng 511 với số tiền hàng. Tổng các dòng luôn bằng số tiền của phát sinh; phần nào chưa xác định được đối ứng nằm ở một dòng để trống cột TK đối ứng. Cộng phát sinh và số dư của tài khoản không đổi dù bật hay tắt. Tuỳ chọn áp dụng cho màn hình, Excel và PDF.

Hai trường hợp cột này để trống:

- Bút toán ghi sổ trước khi cài `fg_account_counterpart` và chưa được tạo đối ứng. Kế toán trưởng dùng trình tạo đối ứng của module đó để bổ sung.
- Bút toán có dòng mang số tiền âm; `fg_account_counterpart` chưa xử lý loại bút toán này.

## 4. Ẩn tài khoản trung chuyển

Phần này chỉ có tác dụng khi công ty bật thiết lập *Ẩn tài khoản trung chuyển khi không có số dư* của module `fg_vn_transfer_account`, dành cho đơn vị áp dụng Thông tư 133.

Khi nộp tiền mặt vào ngân hàng, Odoo có hai bút toán gặp nhau ở tài khoản trung chuyển: phiếu chi CASH/001 ghi Nợ 113, Có 1111; giấy báo có BANK/001 ghi Nợ 1121, Có 113. Hai dòng 113 đã đối soát với nhau. Sổ cái xử lý ba việc:

- **Tài khoản đối ứng thật.** Trên sổ cái 1111, dòng của CASH/001 có TK đối ứng là 1121 thay cho 113. Trên sổ cái 1121, dòng của BANK/001 có TK đối ứng là 1111. Sổ đi qua dòng 113 đã đối soát để tìm tài khoản ở đầu bên kia.
- **Số chứng từ ghép.** Cả hai dòng mang số `BANK/001 (CASH/001)`, giống trên sổ nhật ký chung: bút toán ngân hàng đứng trước, các bút toán còn lại trong ngoặc.
- **Không lập sổ cho tài khoản được ẩn** khi nó không có số dư đầu kỳ và cuối kỳ.

Nếu dòng 113 chưa được đối soát (tiền đã chi ở một đầu, chưa ghi nhận ở đầu kia), TK đối ứng vẫn là 113 và tài khoản 113 vẫn có sổ, để kế toán thấy khoản đang treo.

Quy tắc áp dụng cho mọi tài khoản trong danh sách tài khoản được ẩn của công ty.

## 5. Tài khoản ngoài bảng

Tài khoản ngoài bảng (loại "Off-Balance Sheet" của Odoo, hoặc mã bắt đầu bằng số 0) chỉ được lập sổ khi còn số dư đầu kỳ hoặc cuối kỳ. Quy tắc này và quy tắc ở mục 4 không áp dụng khi người dùng chọn đích danh tài khoản ở bộ lọc Tài khoản: tài khoản được chọn luôn có sổ.

## 6. Xuất file

- **Excel:** mỗi tài khoản một sheet, tên sheet là mã và tên tài khoản. Đầu sheet có tên sổ, kỳ và dòng "Tài khoản: …".
- **PDF:** mẫu S03b-DNN, A4 đứng hoặc ngang. Sổ quá dài không in được trong một lần: hệ thống báo số dòng và đề nghị thu hẹp kỳ hoặc chọn bớt tài khoản. Mỗi tài khoản bắt đầu ở trang mới, tên tài khoản in ở đầu mỗi trang của nó. Cuối mỗi trang có dòng "Cộng chuyển trang" cho hai cột Nợ và Có, tính riêng cho từng tài khoản. Dòng "Cộng phát sinh" luôn nằm cùng trang với dòng "Số dư cuối kỳ". Cuối sổ của mỗi tài khoản có dòng "Sổ này bao gồm ... trang", ngày mở sổ và phần ký tên; nếu trang cuối không đủ chỗ cho phần ký tên, hai dòng "Cộng phát sinh" và "Số dư cuối kỳ" sang trang mới cùng nó. Số trang ở cuối trang đánh riêng cho từng tài khoản ("Trang 2/3" là trang thứ hai trong ba trang của tài khoản). Khi in lề đối xứng, mỗi tài khoản bắt đầu ở trang lẻ.

## 7. Khác với bản 19.0

- Tuỳ chọn tài khoản không có phát sinh có thêm mức "lập sổ nếu có số dư đầu kỳ". Mặc định vẫn như 19.0.
- Tuỳ chọn mới: tách dòng theo tài khoản đối ứng.
- Sổ dài được tải dần theo từng tài khoản thay vì tải hết một lần.
- Việc ẩn áp dụng cho danh sách tài khoản do đơn vị chọn, không chỉ một tài khoản trung chuyển.
- Tài khoản ngoài bảng được nhận diện thêm theo loại "Off-Balance Sheet" của Odoo.
- Bộ lọc Loại tài khoản có cả trên màn hình, không chỉ ở cửa sổ tham số.
- Sổ nhanh hơn trên hệ thống nhiều tài khoản: số liệu của mọi tài khoản được đọc một lượt thay vì từng tài khoản một.
- Dòng bút toán có số tiền bằng 0 không còn trên sổ.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch. Giấy phép đổi từ LGPL-3 sang AGPL-3.

## 8. Cài đặt

Chép module cùng ba module phụ thuộc vào thư mục addons, cập nhật danh sách ứng dụng và cài **Sổ cái tài khoản**. Người dùng cần có đầy đủ tính năng kế toán (nhóm `account.group_account_user`) để mở sổ.
