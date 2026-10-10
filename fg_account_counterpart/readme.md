# Đối ứng tài khoản

Module cho Odoo 20 (Community và Enterprise), phụ thuộc module `account`.
Tác giả: Fanha Giang. Giấy phép: AGPL-3.

Tài liệu này đi qua các nghiệp vụ kế toán thường gặp, từ đơn giản đến phức tạp, để cho thấy module xác định tài khoản đối ứng như thế nào trong từng trường hợp. Số tài khoản theo hệ thống tài khoản kế toán doanh nghiệp Việt Nam.

## 1. Tài khoản đối ứng và lý do cần nó

Trong một bút toán, tài khoản đối ứng của một dòng là tài khoản ở vế bên kia nhận chính khoản tiền của dòng đó. Kế toán Việt Nam dùng thông tin này ở khắp nơi:

- Sổ cái, sổ chi tiết tài khoản, sổ quỹ tiền mặt, sổ tiền gửi ngân hàng đều có cột "Tài khoản đối ứng".
- Báo cáo lưu chuyển tiền tệ phân loại dòng tiền dựa vào tài khoản đối ứng của 111 và 112: thu từ khách hàng (đối ứng 131, 511), trả người lao động (đối ứng 334), trả lãi vay (đối ứng 635).
- Kiểm tra định khoản: một khoản ghi Có 515 đối ứng với 112 là lãi tiền gửi, còn đối ứng với 331 là lãi chênh lệch tỷ giá khi thanh toán.

Odoo chỉ lưu các dòng Nợ và các dòng Có của bút toán, không lưu dòng nào đi với dòng nào. Module này bổ sung phần còn thiếu đó.

## 2. Module hoạt động thế nào

Khi một bút toán được ghi sổ, module ghép các dòng Nợ với các dòng Có và lưu lại từng cặp cùng số tiền của cặp. Từ đó, mỗi phát sinh hiển thị các phát sinh đối ứng, các tài khoản đối ứng, số tiền đã đối ứng và trạng thái (chưa, một phần, hoàn toàn). Khi bút toán được đưa về nháp, các cặp đối ứng bị xoá và sẽ được tạo lại khi ghi sổ lần sau.

Việc ghép đi qua ba lượt. Trong mỗi lượt, các dòng Nợ được xét lần lượt theo thứ tự tạo dòng:

| Lượt | Điều kiện | Cách ghép |
|---|---|---|
| 1 | Dòng Nợ và dòng Có bằng số tiền, cùng đối tác hoặc cùng không có đối tác | Ghép một-một với dòng Có đầu tiên thỏa điều kiện |
| 2 | Cùng đối tác hoặc cùng không có đối tác | Chia phần còn lại của dòng Nợ cho các dòng Có cùng đối tác, theo tỷ lệ số tiền còn lại |
| 3 | Mọi dòng còn dư | Chia phần còn lại của dòng Nợ cho mọi dòng Có còn dư, theo tỷ lệ số tiền còn lại |

Các nghiệp vụ dưới đây minh họa từng lượt.

## 3. Các nghiệp vụ

### 3.1. Thu tiền khách hàng: một Nợ, một Có

Công ty A chuyển khoản trả 55.000.000 tiền hàng.

| Dòng | Tài khoản | Đối tác | Nợ | Có |
|---|---|---|---|---|
| 1 | 112 Tiền gửi không kỳ hạn | Công ty A | 55.000.000 | |
| 2 | 131 Phải thu của khách hàng | Công ty A | | 55.000.000 |

Hai dòng bằng tiền và cùng đối tác nên được ghép ngay ở lượt 1. Tài khoản đối ứng của 112 là 131, của 131 là 112.

### 3.2. Hóa đơn bán hàng: một Nợ, nhiều Có

Bán hàng cho Công ty A, giá chưa thuế 100.000.000, thuế GTGT 10%.

| Dòng | Tài khoản | Đối tác | Nợ | Có |
|---|---|---|---|---|
| 1 | 131 Phải thu của khách hàng | Công ty A | 110.000.000 | |
| 2 | 511 Doanh thu bán hàng và cung cấp dịch vụ | Công ty A | | 100.000.000 |
| 3 | 33311 Thuế GTGT đầu ra | Công ty A | | 10.000.000 |

Không có cặp bằng tiền. Lượt 2 chia 110.000.000 của dòng 131 cho hai dòng Có:

- 131 ↔ 511: 100.000.000
- 131 ↔ 33311: 10.000.000

Tài khoản đối ứng của 131 là 511 và 33311.

### 3.3. Hóa đơn mua hàng: nhiều Nợ, một Có

Mua hàng hóa của Công ty B, giá chưa thuế 40.000.000, thuế GTGT 10%.

| Dòng | Tài khoản | Đối tác | Nợ | Có |
|---|---|---|---|---|
| 1 | 156 Hàng hóa | Công ty B | 40.000.000 | |
| 2 | 1331 Thuế GTGT được khấu trừ | Công ty B | 4.000.000 | |
| 3 | 331 Phải trả cho người bán | Công ty B | | 44.000.000 |

Lượt 2 lần lượt lấy từng dòng Nợ trừ vào dòng Có duy nhất:

- 156 ↔ 331: 40.000.000
- 1331 ↔ 331: 4.000.000

### 3.4. Bán hàng kèm giá vốn: hai nghiệp vụ trong một bút toán

Hóa đơn ở mục 3.2 được ghi cùng bút toán với giá vốn 70.000.000. Tất cả các dòng cùng khách hàng Công ty A.

| Dòng | Tài khoản | Nợ | Có |
|---|---|---|---|
| 1 | 131 Phải thu của khách hàng | 110.000.000 | |
| 2 | 511 Doanh thu bán hàng và cung cấp dịch vụ | | 100.000.000 |
| 3 | 33311 Thuế GTGT đầu ra | | 10.000.000 |
| 4 | 632 Giá vốn hàng bán | 70.000.000 | |
| 5 | 156 Hàng hóa | | 70.000.000 |

- Lượt 1: dòng 632 và dòng 156 bằng tiền nên được ghép với nhau, 70.000.000.
- Lượt 2: dòng 131 được chia cho hai dòng Có còn lại: 511 nhận 100.000.000, 33311 nhận 10.000.000.

Kết quả đúng với bản chất: giá vốn đối ứng với hàng hóa, công nợ đối ứng với doanh thu và thuế. Nếu chỉ chia theo tỷ lệ thì 632 sẽ bị ghép lẫn với 511.

### 3.5. Trích bảo hiểm phần doanh nghiệp đóng: nhiều Nợ, nhiều Có

Quỹ lương bộ phận quản lý 60.000.000, bộ phận bán hàng 40.000.000. Doanh nghiệp đóng BHXH 17,5%, BHYT 3%, BHTN 1%. Các dòng không có đối tác.

| Dòng | Tài khoản | Nợ | Có |
|---|---|---|---|
| 1 | 6421 Chi phí nhân viên quản lý | 12.900.000 | |
| 2 | 6411 Chi phí nhân viên bán hàng | 8.600.000 | |
| 3 | 3383 Bảo hiểm xã hội | | 17.500.000 |
| 4 | 3384 Bảo hiểm y tế | | 3.000.000 |
| 5 | 3386 Bảo hiểm thất nghiệp | | 1.000.000 |

Không có cặp bằng tiền. Lượt 2 chia từng dòng Nợ cho ba dòng Có theo tỷ lệ:

| | 3383 | 3384 | 3386 | Cộng |
|---|---|---|---|---|
| 6421 | 10.500.000 | 1.800.000 | 600.000 | 12.900.000 |
| 6411 | 7.000.000 | 1.200.000 | 400.000 | 8.600.000 |
| Cộng | 17.500.000 | 3.000.000 | 1.000.000 | 21.500.000 |

Mỗi bộ phận gánh đúng phần bảo hiểm của mình: 10.500.000 chính là 17,5% của 60.000.000.

### 3.6. Một lần chi tiền trả hai nhà cung cấp: đối tác khác nhau

Ủy nhiệm chi 50.000.000 trả cho Công ty B 30.000.000 và Công ty C 20.000.000. Dòng tiền gửi không gắn đối tác.

| Dòng | Tài khoản | Đối tác | Nợ | Có |
|---|---|---|---|---|
| 1 | 331 Phải trả cho người bán | Công ty B | 30.000.000 | |
| 2 | 331 Phải trả cho người bán | Công ty C | 20.000.000 | |
| 3 | 112 Tiền gửi không kỳ hạn | | | 50.000.000 |

Lượt 1 và lượt 2 không ghép được gì vì dòng Có không cùng đối tác với dòng Nợ nào. Lượt 3 bỏ qua đối tác:

- 331 (Công ty B) ↔ 112: 30.000.000
- 331 (Công ty C) ↔ 112: 20.000.000

### 3.7. Hai dòng liền nhau bằng tiền: ngoại lệ của lượt 1

Trả Công ty B 20.000.000 bằng chuyển khoản và chi 3.000.000 tiền mặt cho dịch vụ mua ngoài, ghi chung một bút toán.

| Dòng | Tài khoản | Đối tác | Nợ | Có |
|---|---|---|---|---|
| 1 | 331 Phải trả cho người bán | Công ty B | 20.000.000 | |
| 2 | 112 Tiền gửi không kỳ hạn | | | 20.000.000 |
| 3 | 6427 Chi phí dịch vụ mua ngoài | | 3.000.000 | |
| 4 | 111 Tiền mặt | | | 3.000.000 |

Dòng 1 và dòng 2 khác đối tác, nhưng dòng 2 là dòng Có đầu tiên, nằm liền kề dòng 1 và bằng tiền, nên được ghép luôn ở lượt 1. Dòng 3 và dòng 4 bằng tiền và cùng không có đối tác nên cũng được ghép ở lượt 1.

- 331 ↔ 112: 20.000.000
- 6427 ↔ 111: 3.000.000

## 4. Những điều cần biết khi nhập bút toán

- **Muốn một cặp Nợ/Có được ghép riêng với nhau:** nhập hai dòng bằng số tiền và cùng đối tác, hoặc nhập hai dòng liền nhau. Dòng Nợ có đối tác sẽ không được ghép một-một với dòng Có bằng tiền nhưng khác đối tác và không liền kề; nó sẽ bị chia theo tỷ lệ ở lượt 3.
- **Thứ tự dòng:** module xét các dòng theo thứ tự chúng được tạo ra. Thứ tự chỉ ảnh hưởng đến kết quả khi bút toán có nhiều đối tác lẫn lộn, hoặc ở phần làm tròn.
- **Làm tròn:** khi chia tỷ lệ ra số lẻ, phần chênh lệch được dồn vào dòng Có cuối cùng. Ví dụ chia 1.000.000 theo tỷ lệ 2:1 được 666.667 và 333.333.
- **Ngoại tệ:** số tiền nguyên tệ của từng cặp được tính song song theo cùng cách.
- **Dòng bằng 0:** được coi là đã đối ứng hoàn toàn.
- **Bút toán âm:** bút toán có dòng Nợ hoặc Có mang số âm hiện chưa được xử lý và giữ trạng thái "chưa đối ứng".

## 5. Dữ liệu có từ trước khi cài module

Các bút toán đã ghi sổ trước khi cài module chưa có đối ứng. Kế toán trưởng dùng trình tạo đối ứng để:

- tạo đối ứng cho các bút toán còn thiếu;
- tạo lại đối ứng cho toàn bộ bút toán;
- giới hạn phạm vi theo một hoặc nhiều sổ nhật ký.

## 6. Cài đặt

1. Chép module vào thư mục addons của Odoo.
2. Cập nhật danh sách ứng dụng, tìm "Account Counterparts" và cài đặt.
3. Chạy trình tạo đối ứng nếu đã có dữ liệu kế toán.
