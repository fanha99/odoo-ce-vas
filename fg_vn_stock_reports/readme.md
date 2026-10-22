# Báo cáo kho Việt Nam (S06-DNN, Tổng hợp nhập xuất tồn)

Module cho Odoo 20 (Community và Enterprise).
Phụ thuộc: `stock_account` (định giá kho của Odoo) và `fg_vn_accounting_reports` (nền tảng báo cáo).
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Module thêm hai báo cáo, có ở cả hai menu Kho › Báo cáo › Báo cáo kho VN và Kế toán › Báo cáo › VAS Reports › Báo cáo kho VN:

| Báo cáo | Nội dung |
|---|---|
| **Sổ chi tiết vật liệu, dụng cụ, sản phẩm, hàng hoá (S06-DNN)** | Mỗi mặt hàng một sổ: tồn đầu kỳ, từng lần nhập và xuất trong kỳ với số lượng, giá trị, và số tồn sau mỗi lần. |
| **Bảng tổng hợp nhập xuất tồn kho** | Mỗi mặt hàng một dòng: tồn đầu kỳ, nhập, xuất, tồn cuối kỳ, theo số lượng và giá trị. Có thể chia theo kho. |

Hai báo cáo xem được trên màn hình, xuất Excel và in PDF.

Cách dùng chung của màn hình báo cáo (chọn kỳ, xuất file, ngôn ngữ, phân quyền) mô tả trong readme của `fg_vn_accounting_reports`. Tài liệu này chỉ nói phần riêng của hai báo cáo kho. Phần kỹ thuật nằm trong `PLAN.md`.

> Trạng thái: tài liệu này mô tả bản 20.0 **sẽ làm**, viết trước khi code để duyệt. Các điểm còn chờ quyết định nằm ở `PLAN.md` mục 8.
>
> Bản đang có (20.0.1.1.0, 2026-10-22) là **port bản 19.0** để dùng trước: giữ nguyên logic và
> số liệu của 19.0 (chọn kho theo `models/location_valuation.py`, kho 157 có / không GBQK:
> `HUONG_DAN_KHO_157.md`), sửa phần bắt buộc của 20.0 (giá trị phiếu xuất âm, số lượng theo ĐVT
> của mặt hàng, `ir.access`, OWL 3, biểu tượng, tiêu đề trang PDF) và theo quy ước của repo
> (chuỗi tiếng Anh dịch qua `i18n/vi.po`, nhãn bảng do máy chủ trả, AGPL-3). Mặt hàng vẫn hiện
> bằng id như 19.0. Đối chiếu với kế hoạch: `PLAN.md` mục 0.

## 1. Số liệu lấy từ đâu

Cả hai báo cáo đọc các **phiếu kho đã hoàn tất** của Odoo. Không báo cáo nào đọc sổ kế toán.

| Số liệu | Nguồn |
|---|---|
| Số lượng nhập, xuất | Số lượng đã thực hiện của phiếu, quy về đơn vị tính của mặt hàng. |
| Giá trị nhập, xuất | Giá trị định giá mà Odoo ghi trên phiếu, theo phương pháp tính giá của nhóm sản phẩm (giá chuẩn, bình quân, nhập trước xuất trước). |
| Ngày | Ngày hoàn tất phiếu, theo múi giờ của người xem. |

Một phiếu là **nhập** khi hàng đi từ ngoài công ty (nhà cung cấp, khách trả hàng, sản xuất, kiểm kê thừa) vào kho của công ty, là **xuất** khi đi theo chiều ngược lại. Phiếu chuyển giữa hai kho của cùng công ty không làm đổi tồn kho của công ty nên không có trên sổ S06 và không có trên bảng tổng hợp toàn công ty; nó chỉ hiện khi bảng tổng hợp được xem theo kho.

Chỉ lấy mặt hàng có theo dõi tồn kho. Hàng của chủ khác gửi tại kho (hàng ký gửi) không được tính.

Ba điều cần biết khi đối chiếu với sổ kế toán:

- Giá trị trên phiếu là giá trị **hiện tại** của phiếu. Odoo có thể tính lại nó sau khi phiếu đã xong, ví dụ khi hoá đơn mua về với giá khác giá đặt hàng, hoặc khi kế toán điều chỉnh giá trị của phiếu. In lại báo cáo của một kỳ đã qua có thể cho số khác lần in trước.
- Lần **đổi giá vốn** của mặt hàng (đổi giá chuẩn, định giá lại) làm đổi giá trị tồn kho của Odoo mà không có phiếu kho nào, nên **không có trên báo cáo**. Sau một lần đổi giá vốn, giá trị tồn trên báo cáo lệch với giá trị tồn kho của Odoo đúng bằng số điều chỉnh. Mặt hàng tính giá chuẩn còn lệch thêm khi giá mua khác giá chuẩn, vì giá trị nhập trên phiếu là giá mua.
- Báo cáo không đối chiếu với số dư các tài khoản 152, 153, 155, 156. Đơn vị ghi sổ hàng tồn kho theo kỳ sẽ thấy hai số này lệch nhau cho tới khi làm bút toán cuối kỳ.

## 2. Sổ chi tiết vật liệu, dụng cụ, sản phẩm, hàng hoá (S06-DNN)

### Tham số

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ báo cáo | Tháng hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| Mặt hàng | Chỉ lấy các mặt hàng được chọn | Tất cả |
| Nhóm sản phẩm | Chỉ lấy mặt hàng thuộc nhóm được chọn và các nhóm con của nó | Tất cả |
| Tài khoản | Chỉ lấy mặt hàng có tài khoản kho thuộc danh sách được chọn; để trống thì lấy mọi mặt hàng | Các tài khoản 152, 153, 155, 156 |
| Hiện mặt hàng không có phát sinh | Hiện cả mặt hàng không có tồn đầu kỳ và không có phiếu nào trong kỳ | Không |
| Ngôn ngữ báo cáo | Ngôn ngữ hiển thị và in | Tiếng Việt |
| Hướng giấy, lề đối xứng, lề gáy | Dùng khi in PDF | A4 ngang |

Tài khoản kho của một mặt hàng là tài khoản định giá kho khai trên nhóm sản phẩm của nó; nhóm không khai thì lấy tài khoản định giá kho mặc định của công ty. Mặt hàng không xác định được tài khoản kho chỉ hiện khi bộ lọc Tài khoản để trống.

### Nội dung

Mỗi mặt hàng là một nhóm, tiêu đề là mã, tên và đơn vị tính. Trong nhóm:

| Cột | Nội dung |
|---|---|
| Ngày tháng | Ngày hoàn tất phiếu |
| Chứng từ | Số phiếu kho; phiếu không thuộc phiếu kho nào (kiểm kê, sản xuất) thì lấy tham chiếu của nó |
| Diễn giải | Loại nghiệp vụ, chứng từ gốc và đối tác của phiếu; ghi chú của phiếu nếu có |
| Đơn giá | Giá trị chia cho số lượng của dòng |
| SL nhập, GT nhập | Số lượng và giá trị nhập |
| SL xuất, GT xuất | Số lượng và giá trị xuất |
| SL tồn, GT tồn | Tồn sau dòng đó |

Dòng đầu của nhóm là **Số dư đầu kỳ**, dòng cuối là **Cộng phát sinh / Số dư cuối kỳ**. Đơn giá ở hai dòng này là giá trị tồn chia cho số lượng tồn.

Trong một ngày, các phiếu nhập đứng trước các phiếu xuất, rồi theo giờ hoàn tất.

Ô tìm kiếm lọc mặt hàng theo mã và tên. Từ tiêu đề của mặt hàng mở được danh sách phiếu kho của mặt hàng trong kỳ; từ một dòng mở được phiếu kho đó, và bút toán của nó nếu phiếu có sinh bút toán.

**Sổ dài.** Khi kỳ có trên 2.000 dòng, màn hình hiện danh sách mặt hàng với số dư và tổng phát sinh; các dòng phiếu của một mặt hàng được tải khi mở mặt hàng đó, mỗi lần 500 dòng. Excel và PDF luôn xuất cả sổ.

### Xuất file

- **Excel:** mỗi mặt hàng một sheet.
- **PDF:** mẫu S06-DNN, mỗi mặt hàng bắt đầu một trang mới, tên mặt hàng in ở đầu mọi trang của nó, số trang đánh riêng cho từng mặt hàng, file PDF có mục lục (bookmark) theo mặt hàng. Cuối mỗi trang có dòng "Cộng chuyển trang" cho bốn cột nhập xuất và mang số tồn sang trang sau.

## 3. Bảng tổng hợp nhập xuất tồn kho

### Tham số

| Tham số | Ý nghĩa | Mặc định |
|---|---|---|
| Từ ngày, đến ngày | Kỳ báo cáo | Tháng hiện tại |
| Công ty | Chỉ hiện khi dùng nhiều công ty | Công ty đang làm việc |
| Mặt hàng, Nhóm sản phẩm | Như sổ S06 | Tất cả |
| Kho/Vị trí | Chỉ tính tồn và phát sinh tại các vị trí được chọn và vị trí con của chúng | Toàn công ty |
| Nhóm theo kho | Chia bảng theo từng vị trí kho, có dòng cộng của mỗi vị trí | Không |
| Hiện mặt hàng không có phát sinh | Hiện cả mặt hàng không có tồn và không có phát sinh | Không |
| Ngôn ngữ báo cáo, hướng giấy, lề | Như sổ S06 | Tiếng Việt, A4 ngang |

### Nội dung

| Cột | Nội dung |
|---|---|
| Mã SP, Tên sản phẩm, ĐVT | Mã nội bộ, tên và đơn vị tính của mặt hàng |
| Đầu kỳ (SL, giá trị) | Tồn trước ngày đầu kỳ |
| Nhập trong kỳ (SL, giá trị) | Tổng nhập trong kỳ |
| Xuất trong kỳ (SL, giá trị) | Tổng xuất trong kỳ |
| Cuối kỳ (SL, giá trị) | Đầu kỳ cộng nhập trừ xuất |

Dòng cuối là **Tổng cộng**. Bảng sắp theo mã mặt hàng; bấm vào tiêu đề cột để sắp theo cột khác.

**Toàn công ty** (không chọn Kho/Vị trí, không nhóm theo kho): số liệu của một mặt hàng trên bảng bằng đúng dòng số dư và dòng cộng của mặt hàng đó trên sổ S06 cùng kỳ.

**Theo kho** (có chọn Kho/Vị trí hoặc bật Nhóm theo kho): số lượng tính theo vị trí thật của hàng, nên có cả các phiếu chuyển kho nội bộ: chuyển đi là xuất của kho này và là nhập của kho kia. Odoo định giá tồn kho cho cả công ty, không định giá riêng từng kho, nên **giá trị theo kho là số tính ra**: số lượng tại kho nhân với đơn giá bình quân của mặt hàng trong kỳ, tức là (giá trị tồn đầu kỳ + giá trị nhập trong kỳ) chia cho (số lượng tồn đầu kỳ + số lượng nhập trong kỳ) của toàn công ty. Vì vậy tổng giá trị của các kho có thể lệch với giá trị toàn công ty vài đồng do làm tròn, và giá trị xuất theo kho không bằng giá vốn Odoo đã ghi cho từng phiếu.

Ô tìm kiếm lọc theo mã và tên mặt hàng. Từ một dòng mở được danh sách phiếu kho của mặt hàng trong kỳ (của riêng vị trí đó khi đang xem theo kho).

### Xuất file

- **Excel:** một sheet, tiêu đề cột hai tầng (Đầu kỳ, Nhập trong kỳ, Xuất trong kỳ, Cuối kỳ; dưới mỗi nhóm là SL và Giá trị).
- **PDF:** A4 ngang hoặc đứng, tiêu đề cột lặp lại ở mỗi trang, không có dòng cộng chuyển trang.

## 4. Phân quyền

Hai báo cáo mở được với người dùng có đầy đủ tính năng kế toán (`account.group_account_user`) hoặc người dùng kho (`stock.group_stock_user`). Mở phiếu kho từ báo cáo cần quyền đọc phiếu kho; mở bút toán cần quyền kế toán.

## 5. Khác với bản 19.0

Sửa lỗi:

- Giá trị xuất được trừ khỏi tồn. Odoo 20 ghi giá trị của phiếu xuất là số âm (bản 19.0 ghi số dương); code của bản 19.0 chạy trên 20.0 sẽ cộng giá trị xuất vào tồn.
- Số lượng quy về đơn vị tính của mặt hàng. Bản 19.0 lấy số lượng theo đơn vị của phiếu, nên mua theo thùng, tồn theo cái thì sai số lượng.
- Ngày của phiếu theo múi giờ người xem. Bản 19.0 cắt ngày theo giờ UTC, nên phiếu hoàn tất trước 7 giờ sáng hiện vào ngày hôm trước.
- Bộ lọc Mặt hàng trên màn hình có danh sách để chọn. Bản 19.0 lọc theo một loại sản phẩm không còn tồn tại nên danh sách luôn trống.
- Các mục "Xem chi tiết định giá kho", "Xem Stock Move", "Xem Stock Move Line" mở được. Bản 19.0 mở một model đã bị Odoo xoá và một kiểu view đã đổi tên.
- Bộ lọc Kho của sổ S06 bị bỏ: bản 19.0 có ô này nhưng sổ không dùng nó. Sổ S06 là sổ của cả công ty.
- Bộ lọc Nhóm sản phẩm của S06 lấy cả nhóm con, giống bảng tổng hợp.
- Bảng tổng hợp theo kho: tính theo vị trí thật trên dòng phiếu, kể cả vị trí con; phiếu chuyển giữa hai vị trí cùng được chọn không còn bị tính là nhập; giá trị dùng đơn giá bình quân của kỳ thay cho đơn giá bình quân của toàn bộ lịch sử.

Thay đổi khác:

- Mã mặt hàng là mã nội bộ. Bản 19.0 in số id của bản ghi ở tiêu đề mặt hàng của S06 và ở cột Mã SP của bảng tổng hợp.
- Mặt hàng mà nhóm sản phẩm không khai tài khoản kho vẫn hiện khi bộ lọc Tài khoản để trống. Bản 19.0 bỏ chúng khỏi sổ S06.
- Diễn giải của dòng S06 ghi loại nghiệp vụ, chứng từ gốc và đối tác. Bản 19.0 ghi "Nhập hàng theo HĐ" và "Xuất hàng theo HĐ" không kèm số nào.
- Trong một ngày, phiếu nhập đứng trước phiếu xuất.
- Sổ S06 dài được tải dần theo mặt hàng.
- Tài khoản kho lấy theo nhóm sản phẩm rồi tới mặc định của công ty. Trường tài khoản riêng của module `fg_gia_binh_quan_ky` chỉ được dùng khi module đó có mặt trên 20.0.
- Ngôn ngữ gốc của module là tiếng Anh, tiếng Việt là bản dịch. Giấy phép đổi từ LGPL-3 sang AGPL-3.

## 6. Cài đặt

Chép module cùng `fg_vn_accounting_reports` vào thư mục addons, cập nhật danh sách ứng dụng và cài **Báo cáo kho Việt Nam**. Module kéo theo `stock_account` (Kho và Kế toán).
