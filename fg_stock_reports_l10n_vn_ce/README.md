# Vietnam Stock Valuation Reports (OCA Style)

## Mô tả

Module báo cáo Xuất Nhập Tồn cho Odoo 17, được xây dựng theo phong cách OCA Account Financial Reports.

## Tính năng

- **Báo cáo Xuất Nhập Tồn**: Hiển thị số dư đầu kỳ, nhập trong kỳ, xuất trong kỳ, số dư cuối kỳ
- **Xuất PDF**: In báo cáo định dạng PDF
- **Xuất Excel**: Xuất dữ liệu ra file Excel với định dạng chuyên nghiệp
- **Lọc linh hoạt**: 
  - Lọc theo khoảng thời gian
  - Lọc theo sản phẩm
  - Lọc theo danh mục sản phẩm
  - Lọc theo kho
- **Tùy chọn hiển thị**:
  - Ẩn dòng có số dư = 0
  - Nhóm theo danh mục sản phẩm

## Cài đặt

### Yêu cầu

- Odoo 17.0
- Module `stock_account`
- Module `report_xlsx` (từ OCA)

### Cách cài đặt

1. Copy module vào thư mục addons của Odoo
2. Cập nhật danh sách module
3. Cài đặt module "Vietnam Stock Valuation Reports (OCA Style)"

## Sử dụng

1. Truy cập menu: **Kho vận → Báo cáo → Báo cáo Xuất Nhập Tồn**
2. Chọn khoảng thời gian báo cáo
3. Tùy chọn các bộ lọc (sản phẩm, danh mục, kho)
4. Nhấn **In PDF** hoặc **Xuất Excel**

## Cấu trúc dữ liệu

Báo cáo dựa trên bảng `stock.valuation.layer` để tính toán:

- **Số dư đầu kỳ**: Tổng hợp tất cả giao dịch trước ngày bắt đầu
- **Nhập trong kỳ**: Tổng các giao dịch có quantity > 0 trong kỳ
- **Xuất trong kỳ**: Tổng các giao dịch có quantity < 0 trong kỳ
- **Số dư cuối kỳ**: Đầu kỳ + Nhập - Xuất

## Tác giả

- Fanha Giang

## Giấy phép

AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
