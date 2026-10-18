# FG Stock Valuation Report Vietnam

## Mô tả

Module báo cáo **Xuất Nhập Tồn** (Stock Valuation Report) theo chuẩn Việt Nam cho Odoo 17 Enterprise.

## Tính năng chính

- ✅ Báo cáo xuất nhập tồn theo chuẩn Việt Nam
- ✅ Hỗ trợ so sánh với kỳ trước (Previous Period, Same Period Last Year)
- ✅ Xuất PDF, Excel với định dạng chuẩn
- ✅ Tìm kiếm theo tên sản phẩm
- ✅ Click vào dòng để xem chi tiết Stock Valuation Layers hoặc Stock Moves
- ✅ Sắp xếp theo các cột

## Yêu cầu

| Module | Mô tả |
|--------|-------|
| `account_reports` | Odoo 17 Enterprise |
| `stock_account` | Core Odoo |

## Cài đặt

1. Copy thư mục `fg_stock_reports_l10n_vn` vào thư mục addons
2. Cập nhật danh sách module: **Apps > Update Apps List**
3. Tìm và cài đặt module **"Vietnam Stock Valuation Reports"**

## Truy cập báo cáo

| Đường dẫn | Menu |
|-----------|------|
| Inventory | Inventory → Reporting → Báo cáo Xuất Nhập Tồn |
| Accounting | Accounting → Reporting → Báo cáo Xuất Nhập Tồn |

## Cấu trúc cột báo cáo

### Không có so sánh kỳ

| STT | Nhóm cột | Cột con | Mô tả |
|:---:|----------|---------|-------|
| 1 | ĐVT | - | Đơn vị tính |
| 2 | Đầu kỳ | Số lượng | Số lượng tồn đầu kỳ |
| 3 | | Giá trị | Giá trị tồn đầu kỳ |
| 4 | Trong kỳ | SL Tăng | Số lượng nhập trong kỳ |
| 5 | | GT Tăng | Giá trị nhập trong kỳ |
| 6 | | SL Giảm | Số lượng xuất trong kỳ |
| 7 | | GT Giảm | Giá trị xuất trong kỳ |
| 8 | Cuối kỳ | Số lượng | Số lượng tồn cuối kỳ |
| 9 | | Giá trị | Giá trị tồn cuối kỳ |

**Ví dụ hiển thị:**

```
┌─────────────┬─────┬──────────────┬─────────────────────────────────┬──────────────┐
│             │     │   Đầu kỳ     │          Nov 2025               │   Cuối kỳ    │
│ Sản phẩm    │ ĐVT ├───────┬──────┼────────┬────────┬───────┬───────┼───────┬──────┤
│             │     │ SL    │ GT   │ SL Tăng│ GT Tăng│SL Giảm│GT Giảm│ SL    │ GT   │
├─────────────┼─────┼───────┼──────┼────────┼────────┼───────┼───────┼───────┼──────┤
│ Sản phẩm A  │ kg  │ 23.00 │ 4.8M │ 140.00 │ 29.4M  │ 40.00 │ 8.4M  │123.00 │25.8M │
└─────────────┴─────┴───────┴──────┴────────┴────────┴───────┴───────┴───────┴──────┘
```

### Có so sánh 1 kỳ (VD: Oct 2025 vs Nov 2025)

| STT | Nhóm cột | Cột con | Mô tả |
|:---:|----------|---------|-------|
| 1 | ĐVT | - | Đơn vị tính |
| 2 | Đầu kỳ | Số lượng | Tồn đầu kỳ xa nhất (01/10/2025) |
| 3 | | Giá trị | |
| 4 | Oct 2025 | SL Tăng | Nhập trong tháng 10 |
| 5 | | GT Tăng | |
| 6 | | SL Giảm | Xuất trong tháng 10 |
| 7 | | GT Giảm | |
| 8 | Nov 2025 | SL Tăng | Nhập trong tháng 11 |
| 9 | | GT Tăng | |
| 10 | | SL Giảm | Xuất trong tháng 11 |
| 11 | | GT Giảm | |
| 12 | Cuối kỳ | Số lượng | Tồn cuối kỳ gần nhất (30/11/2025) |
| 13 | | Giá trị | |

**Ví dụ hiển thị:**

```
┌───────────┬─────┬──────────┬───────────────────────────────┬───────────────────────────────┬──────────┐
│           │     │ Đầu kỳ   │      Oct 2025                 │      Nov 2025                 │ Cuối kỳ  │
│ Sản phẩm  │ ĐVT ├────┬─────┼───────┬───────┬───────┬───────┼───────┬───────┬───────┬───────┼────┬─────┤
│           │     │ SL │ GT  │SL Tăng│GT Tăng│SL Giảm│GT Giảm│SL Tăng│GT Tăng│SL Giảm│GT Giảm│ SL │ GT  │
├───────────┼─────┼────┼─────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼────┼─────┤
│ SP A      │ kg  │ 10 │ 2M  │  50   │ 10M   │  20   │ 4M    │ 40    │  8M   │  15   │  3M   │ 65 │ 13M │
└───────────┴─────┴────┴─────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴────┴─────┘
```

### Công thức tính toán

| Cột | Công thức |
|-----|-----------|
| Đầu kỳ | Tổng stock valuation layers trước ngày bắt đầu kỳ đầu tiên |
| SL/GT Tăng | Tổng quantity/value > 0 trong kỳ |
| SL/GT Giảm | Tổng \|quantity/value\| < 0 trong kỳ |
| Cuối kỳ | Tổng stock valuation layers đến ngày kết thúc kỳ cuối cùng |

## Filter và Options

| Filter | Mô tả |
|--------|-------|
| Date Range | Khoảng thời gian báo cáo |
| Comparison | So sánh với kỳ trước |
| Search | Tìm kiếm theo tên sản phẩm |

### Comparison Options

| Option | Mô tả |
|--------|-------|
| No Comparison | Chỉ hiển thị kỳ hiện tại |
| Previous Period | So sánh với kỳ trước (VD: tháng trước) |
| Same Period Last Year | So sánh với cùng kỳ năm trước |
| Custom | Tùy chỉnh số kỳ so sánh |

## Xuất báo cáo

| Format | Button | Mô tả |
|--------|--------|-------|
| PDF | 📄 PDF | Xuất file PDF với định dạng chuẩn |
| Excel | 📊 XLSX | Xuất file Excel |

## Tác giả

**Fanha Giang** fanha99@hotmail.com

## License

LGPL-3
