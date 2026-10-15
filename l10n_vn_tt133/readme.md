# Vietnam - Hệ thống tài khoản doanh nghiệp nhỏ và vừa (Thông tư 133/2016/TT-BTC)

Module cung cấp một hệ thống tài khoản (chart template) để chọn khi thiết lập kế toán cho công ty áp dụng chế độ kế toán doanh nghiệp nhỏ và vừa theo Thông tư 133/2016/TT-BTC. Module chỉ chứa dữ liệu thiết lập: danh mục tài khoản, thuế GTGT, sổ nhật ký và các tài khoản mặc định của công ty. Sổ sách, báo cáo nằm ở các module `fg_vn_*`.

## 1. Đối tượng áp dụng

- Doanh nghiệp nhỏ và vừa, doanh nghiệp siêu nhỏ theo Thông tư 133/2016/TT-BTC (thay Quyết định 48/2006/QĐ-BTC từ 01/01/2017).
- Không áp dụng cho doanh nghiệp có trên 50% vốn nhà nước và hợp tác xã.
- Đơn vị theo Thông tư 200/2014/TT-BTC dùng hệ thống tài khoản `vn` của module `l10n_vn` có sẵn trong Odoo.

## 2. Cách dùng

1. Cài module.
2. Vào **Kế toán → Cấu hình → Thiết lập**, mục *Kế toán tài chính*, chọn gói **Vietnam - SME accounting (Circular 133/2016/TT-BTC)** cho công ty. Chỉ chọn được khi công ty chưa có phát sinh.
3. Odoo tạo tài khoản, thuế, sổ nhật ký và gán các tài khoản mặc định ở mục 4.

Hai công ty trong cùng một database có thể dùng hai hệ thống khác nhau (một công ty TT133, một công ty TT200).

## 3. Hệ thống tài khoản

### 3.1. Tài khoản tổng hợp và tài khoản chi tiết

Odoo 20.0 bỏ "nhóm tài khoản"; tài khoản cấp trên là một **tài khoản thật** và các tài khoản chi tiết gắn vào nó (tài khoản cha – tài khoản con). Module dựng cây theo danh mục TT133:

| Tài khoản tổng hợp | Tài khoản chi tiết |
|---|---|
| 111 Tiền mặt | 1111 Tiền Việt Nam, 1112 Ngoại tệ |
| 112 Tiền gửi ngân hàng | 1121 Tiền Việt Nam, 1122 Ngoại tệ, và tài khoản của từng ngân hàng khi tạo sổ ngân hàng mới |
| 133 Thuế GTGT được khấu trừ | 1331, 1332 |
| 211 Tài sản cố định | 2111, 2112, 2113 |
| 333 Thuế và các khoản phải nộp Nhà nước | 3331 (gồm 33311, 33312), 3332 … 3337, 3338 (gồm 33381, 33382), 3339 |
| 642 Chi phí quản lý kinh doanh | 6421, 6422 |
| … | (đủ 24 tài khoản tổng hợp, danh sách ở PLAN.md mục 3) |

Tài khoản không có tài khoản chi tiết (131, 152, 331, 515, 632, 911…) giữ mã ba chữ số như danh mục của Bộ Tài chính, không bị thêm số 0 vào cuối.

Chín "loại tài khoản" (loại 1 Tài sản ngắn hạn … loại 9 Xác định kết quả kinh doanh) không còn là một mục riêng trong danh mục. Báo cáo cần cộng theo loại thì lấy theo chữ số đầu của mã tài khoản.

Số dư của tài khoản tổng hợp trên Bảng cân đối số phát sinh (`fg_vn_report_cdps`) bằng tổng các tài khoản chi tiết của nó.

### 3.2. Hạch toán vào tài khoản tổng hợp

Odoo 20.0 **cho phép** ghi bút toán vào tài khoản đã có tài khoản con; lõi Odoo không có kiểm tra nào ngăn việc này (đã thử: bút toán ghi vào tài khoản cha được ghi sổ bình thường, và gắn tài khoản con vào một tài khoản đã có phát sinh cũng không bị chặn). Chính `l10n_vn` (TT200) của Odoo dùng tài khoản cha 112 làm tài khoản của sổ ngân hàng và tài khoản cha 113 làm tài khoản chuyển tiền nội bộ.

Theo chế độ kế toán, nghiệp vụ phải hạch toán vào tài khoản chi tiết cấp thấp nhất. Module này thiết lập sẵn mọi tài khoản mặc định (sổ tiền, công nợ, thuế, doanh thu, chi phí) là tài khoản chi tiết, nên các nghiệp vụ Odoo tự sinh không rơi vào tài khoản tổng hợp. Bút toán người dùng nhập tay vẫn chọn được tài khoản tổng hợp; module không chặn việc này, để không can thiệp vào lõi Odoo. Người lập bút toán tự chọn tài khoản chi tiết. Nếu tài khoản tổng hợp có phát sinh riêng, Bảng cân đối số phát sinh vẫn tính đúng: số của tài khoản tổng hợp là số riêng của nó cộng các tài khoản con.

### 3.3. Tài khoản kỹ thuật

TT133 không có tài khoản 113 "Tiền đang chuyển". Các tài khoản Odoo cần cho nghiệp vụ ngân hàng được tạo với mã ngoài danh mục, bắt đầu bằng `0`, để không lẫn với tài khoản của Bộ Tài chính. Mã theo quy ước chung của các module `fg_vn_*`: lấy mã tài khoản Odoo dùng ở hệ thống tài khoản `l10n_vn` (TT200), thay `11` ở đầu bằng `0`, không có tài khoản cha. Nhờ vậy công ty TT133 và công ty TT200 đã đổi mã theo quy ước có cùng mã tài khoản kỹ thuật.

| Mã | Tên | Dùng cho | Tài khoản cha | Ở `l10n_vn` |
|---|---|---|---|---|
| 03 | Tiền đang chuyển | chuyển tiền giữa các sổ tiền (nộp tiền mặt vào ngân hàng, rút tiền gửi về quỹ) | — | 113 |
| 031 | Khoản thu chưa đối soát | tiền khách trả đã ghi nhận nhưng chưa khớp với sao kê | — | 1131 |
| 032 | Khoản chi chưa đối soát | tiền trả nhà cung cấp đã ghi nhận nhưng chưa khớp với sao kê | — | 1132 |
| 021 | Tài khoản tạm ngân hàng | dòng sao kê chưa đối soát | — | 1121 (con của 112) |

Các tài khoản này phải hết số dư khi đối soát xong. Tài khoản tạm ngân hàng 021 cố ý không nằm dưới 112 "Tiền gửi ngân hàng", để không lẫn với tiền gửi thật. Nếu Odoo tạo thêm tài khoản kỹ thuật khác, đặt mã và cây theo cùng quy ước (`fg_vn_accounting_reports/readme.md`, mục 8.3).

Bản 19.0 khai `01`–`03` (thực tế Odoo đã đệm thành `010`, `020`, `030` khi thiết lập). Bản này dùng mã như bảng trên.

Sau khi đối soát: `021` không còn phát sinh (Odoo thay dòng tài khoản tạm bằng tài khoản thật); `03` còn phát sinh hai bên, số dư bằng 0; `031`, `032` chỉ có phát sinh nếu khai tài khoản chờ cho phương thức thanh toán của sổ ngân hàng (mặc định không khai). Chi tiết: `fg_vn_accounting_reports/readme.md`, mục 8.4. Nên bật `fg_vn_transfer_account` và chọn `03`, `031`, `032`.

Bảng cân đối số phát sinh và sổ cái coi mọi tài khoản có mã bắt đầu bằng `0` (dài bao nhiêu cũng vậy) là tài khoản ngoài chế độ: chỉ trình bày trên màn hình, Excel, PDF khi còn số dư đầu kỳ hoặc cuối kỳ (dòng nền cam), và không bao giờ đưa vào file XML phụ lục cân đối tài khoản. Sổ nhật ký chung vẫn in các dòng này, trừ khi tài khoản nằm trong danh sách ẩn của `fg_vn_transfer_account`. Quy tắc này thay cho "tài khoản không thuộc nhóm nào" của bản 17.0. Đơn vị tự thêm tài khoản nội bộ không muốn đưa lên sổ theo chế độ thì cũng đặt mã bắt đầu bằng `0`. Chi tiết: `fg_vn_accounting_reports/readme.md`, mục 8.

Các tài khoản này không mang loại "Off-Balance Sheet" của Odoo: Odoo bắt mọi dòng của một bút toán có dòng ngoài bảng cũng phải là ngoài bảng, nên tài khoản chờ của ngân hàng không thể mang loại đó.

## 4. Tài khoản mặc định của công ty

| Mục đích | Tài khoản |
|---|---|
| Phải thu khách hàng | 131 |
| Phải trả người bán | 331 |
| Doanh thu mặc định của sản phẩm | 5111 |
| Chi phí mặc định của sản phẩm | 6421 |
| Sổ tiền mặt / sổ ngân hàng | 1111 / 1121 |
| Lãi / lỗ chênh lệch tỷ giá, chiết khấu thanh toán | 515 / 635 |
| Chênh lệch kiểm quỹ (thừa / thiếu) | 711 / 811 |
| Hàng tồn kho (định giá kho) | 156 |
| Chênh lệch kho khi khoá sổ kho (của 152, 153, 155, 156) | 632 |
| Sản phẩm dở dang | 154 |
| Phải thu của điểm bán hàng (POS) | 131 |

Kế toán Anglo-Saxon (ghi giá vốn khi xuất hoá đơn) **tắt**: giá vốn ghi khi xuất kho, theo chế độ kế toán Việt Nam.

Odoo 20.0 bỏ tài khoản định giá kho mặc định theo nhóm sản phẩm (bản 19.0 đặt 155 cho mọi nhóm). Nhóm sản phẩm không đặt tài khoản riêng sẽ dùng 156 của công ty; nhóm thành phẩm cần đặt 155 bằng tay.

## 5. Thuế

Thuế GTGT theo luật thuế, không phụ thuộc chế độ kế toán, nên công ty TT133 dùng **đúng bộ thuế của `l10n_vn`** (TT200): module không khai thuế riêng mà lấy thuế của `l10n_vn` khi thiết lập công ty, chỉ đổi tài khoản sang tài khoản TT133 cùng mã (1331, 33311). Thuế đã gắn mã chỉ tiêu tờ khai 01/GTGT, nên báo cáo thuế của Odoo lấy được số liệu. Khi Odoo cập nhật bộ thuế của `l10n_vn`, công ty TT133 thiết lập sau đó nhận bộ thuế mới.

| Nhóm | Thuế |
|---|---|
| GTGT đầu vào được khấu trừ | 0%, 5%, 8%, 10%, không chịu thuế; ghi Nợ 1331 |
| GTGT đầu vào không được khấu trừ | 5%, 8%, 10% (KKT); tiền thuế cộng vào giá trị hàng mua |
| GTGT hàng nhập khẩu | 0%, 5%, 8%, 10%, không chịu thuế, có bản không được khấu trừ; kê trên tờ khai ở chỉ tiêu hàng nhập khẩu |
| GTGT đầu ra | 0%, 5%, 8%, 10%, không chịu thuế, không kê khai tính nộp thuế (KKKTT); ghi Có 33311 |

Thuế mặc định: mua hàng 10%, bán hàng 10%. Thuế được làm tròn theo từng dòng.

## 6. Ngôn ngữ

Tên tài khoản, thuế, nhóm thuế có cả tiếng Anh và tiếng Việt. Khi database có cài tiếng Việt, người dùng tiếng Việt thấy tên tiếng Việt.

## 7. Giới hạn

- Module không chứa báo cáo tài chính theo mẫu TT133 (B01a-DNN, B02-DNN…); các báo cáo này thuộc module báo cáo riêng.
- Không chuyển dữ liệu cho công ty đã dùng bản 19.0: module dành cho công ty thiết lập mới trên Odoo 20.
