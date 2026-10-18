# Odoo CE VAS

Các module Odoo Community phục vụ kế toán theo chuẩn mực kế toán Việt Nam (VAS).

Nhánh `20.0` dành cho Odoo 20.0. Mỗi module nằm trong một thư mục riêng và có `readme.md` mô tả nghiệp vụ của nó.

## Module đã hoàn thành

| Module | Mô tả | Phiên bản | Cập nhật lần cuối |
|---|---|---|---|
| [`fg_account_counterpart`](fg_account_counterpart/readme.md) | Đối ứng tài khoản: xác định các phát sinh đối ứng và tài khoản đối ứng của từng phát sinh khi bút toán được ghi sổ. Là dữ liệu nền cho các sổ kế toán có cột "Tài khoản đối ứng". Chưa xử lý bút toán có số tiền âm. | 20.0.1.0.0 | 2026-10-10 |
| [`fg_vn_transfer_account`](fg_vn_transfer_account/readme.md) | Ẩn tài khoản trung chuyển: thiết lập theo công ty để các sổ kế toán và phiếu in không trình bày tài khoản trung chuyển (113) và các tài khoản chờ do đơn vị chọn khi chúng không có số dư, và quy tắc dùng chung để trình bày phiếu chi cùng giấy báo có của một lần nộp tiền như một nghiệp vụ. Dành cho đơn vị áp dụng Thông tư 133. | 20.0.1.1.0 | 2026-10-11 |
| [`fg_vn_accounting_reports`](fg_vn_accounting_reports/readme.md) | Nền tảng báo cáo kế toán Việt Nam: màn hình báo cáo, xuất Excel và in PDF có cộng chuyển trang, tải dần cho sổ dài, dùng chung cho các sổ kế toán. Không chứa báo cáo nào. | 20.0.1.2.2 | 2026-10-18 |
| [`fg_vn_report_cdps`](fg_vn_report_cdps/readme.md) | Bảng cân đối số phát sinh: số dư và phát sinh của từng tài khoản, tách công nợ 131/331 theo đối tác, phân cấp theo tài khoản cha–con, so sánh kỳ, xuất Excel, PDF và XML F01-CDTK. | 20.0.1.0.0 | 2026-10-11 |
| [`fg_vn_report_s03a`](fg_vn_report_s03a/readme.md) | Sổ nhật ký chung (S03a-DNN): các bút toán đã ghi sổ theo thứ tự thời gian, lọc theo sổ nhật ký, loại chứng từ, tài khoản, đối tác; sổ dài được tải dần; xuất Excel và PDF có cộng chuyển trang. | 20.0.1.0.0 | 2026-10-11 |
| [`fg_vn_report_s03b`](fg_vn_report_s03b/readme.md) | Sổ cái tài khoản (S03b-DNN): số dư, phát sinh và tài khoản đối ứng của từng tài khoản, tuỳ chọn tách dòng theo tài khoản đối ứng; sổ dài được tải dần theo tài khoản; Excel mỗi tài khoản một sheet, PDF mỗi tài khoản một trang mới. | 20.0.1.0.0 | 2026-10-11 |
| [`l10n_vn_tt133`](l10n_vn_tt133/readme.md) | Hệ thống tài khoản doanh nghiệp nhỏ và vừa theo Thông tư 133/2016/TT-BTC: tài khoản tổng hợp là tài khoản cha của tài khoản chi tiết, tài khoản kỹ thuật ngân hàng mã đầu `0` (03, 031, 032, 021), dùng nguyên bộ thuế GTGT của `l10n_vn`. | 20.0.1.0.0 | 2026-10-15 |

Khi thêm hoặc cập nhật một module, sửa dòng tương ứng trong bảng: phiên bản lấy theo `version` trong `__manifest__.py` của module, ngày ghi theo dạng năm-tháng-ngày.

## Cài đặt

1. Thêm thư mục của repo này vào `addons_path` trong file cấu hình Odoo.
2. Khởi động lại Odoo, cập nhật danh sách ứng dụng và cài module cần dùng.

## Giấy phép

AGPL-3, xem file [LICENSE](LICENSE).
