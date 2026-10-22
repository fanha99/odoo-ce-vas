# Hướng dẫn cấu hình kho 157 (hàng gửi đi bán) trên V19

> Viết 2026-10-22, cùng bản `fg_gia_binh_quan_ky` 19.0.1.2.0 và `fg_vn_stock_reports` 19.0.1.1.0.
> Thiết kế và lý do: `fg_gia_binh_quan_ky/DE_XUAT_KHO_157_V19.md` (đã chọn phương án B).
> Đã test trên data thật `vsg` tháng 06/2026 (mục 4); luồng nhận về từ 157 chưa có dữ liệu.

Kho 157 là một **location nội bộ** chứa hàng đã xuất khỏi kho chính nhưng chưa bán xong (gửi đại
lý, gửi bán, hàng đang ở hải quan...). Cách cấu hình khác nhau tùy công ty có dùng Giá Bình Quân
Kỳ (GBQK) hay không.

| | Dùng GBQK (mục 2) | Không dùng GBQK (mục 3) |
|---|---|---|
| Cờ **Kho 157 (GBQK)** trên location | **Bật** | Không có / để tắt |
| Hàng ở kho 157 trong định giá core | Không (chỉ TK 156) | Có (gộp vào TK 156) |
| Bút toán TK 157 | GBQK tự sinh (Phase 3) | Kế toán ghi tay cuối kỳ |
| Giá trị hàng ở kho 157 | Batch FIFO của GBQK = số dư TK 157 | Báo cáo tính theo bình quân định giá |
| Khóa sổ định giá kho core | Dùng được | Dùng được (lưu ý thứ tự ở mục 3) |

---

## 1. Phần chung: tạo location kho 157

1. **Tồn kho > Cấu hình > Cài đặt**: bật **Địa điểm lưu trữ** (Storage Locations) nếu chưa bật.
2. **Tồn kho > Cấu hình > Địa điểm** → Mới:
   - Tên: vd `157 - Hàng gửi bán` (mỗi đại lý / nơi gửi có thể là một location riêng).
   - **Địa điểm cha: KHÔNG đặt dưới `WH/Tồn kho`** (`WH/Stock`). Hàng ở location con của
     `WH/Tồn kho` được tính là hàng có sẵn → phiếu giao hàng bình thường có thể lấy (giữ chỗ)
     hàng đang ở 157. Đặt dưới location cha của kho (`WH`) hoặc `Physical Locations`.
   - Loại địa điểm: **Nội bộ** (internal). Công ty: công ty của mình.
3. Loại hoạt động (tùy chọn, cho tiện thao tác):
   - Chuyển hàng đi gửi: loại **Nội bộ**, nguồn mặc định `WH/Tồn kho`, đích mặc định kho 157.
   - Nhận hàng gửi về: loại **Nội bộ**, nguồn kho 157, đích `WH/Tồn kho`.
   - Bán từ kho 157: phiếu giao hàng (từ đơn bán) đổi **Địa điểm nguồn** sang kho 157, hoặc tạo
     loại hoạt động **Giao hàng** có nguồn mặc định kho 157.

Chỉ dùng 3 nghiệp vụ: **kho → 157**, **157 → khách**, **157 → kho**. Hàng hỏng / kiểm kê / trả
NCC ở kho 157: chuyển về kho chính trước rồi xử lý ở đó (GBQK không theo dõi phiếu 157 → nơi
khác, mục 2.5).

---

## 2. Công ty dùng GBQK

### 2.1 Cấu hình

Giữ nguyên cấu hình GBQK ở `fg_gia_binh_quan_ky/NOTES_V19_VALUATION.md` §1 (AVCO, Periodic, TK
156/632, TK 3381/1381/711/811...). Thêm:

| Chỗ | Thiết lập |
|---|---|
| Location kho 157 → **Kho 157 (GBQK)** (ô dưới "Loại địa điểm", chỉ quản lý kho thấy) | **Bật** |
| Location kho 157 → Stock Valuation Account | **Để trống** (form không hiện ô này cho location nội bộ; nếu có giá trị thì không lưu được cờ) |
| Kỳ GBQK → **Kho Trung Gian (TK 157)** | Tự điền các location có cờ của công ty. Phải chọn **đủ** — thiếu thì nút Tính báo lỗi |
| Kỳ GBQK → **TK 157** (khung Cấu Hình Bút Toán) | TK 157 (bắt buộc khi đã chọn kho trung gian) |

Bật cờ thì core **không định giá** hàng ở kho 157:

| Phiếu | Core V19 | GBQK |
|---|---|---|
| kho → 157 | là phiếu **xuất** (`is_out`) | Áp: giá BQ kỳ; tạo batch theo phiếu; BT **Nợ 157 / Có 156** |
| 157 → khách | không định giá | Áp: FIFO theo batch; BT **Nợ 632 / Có 157** |
| 157 → kho | là phiếu **nhập** (`is_in`) | Tính: FIFO batch kỳ trước vào công thức BQ; Áp: ghi giá FIFO; BT **Nợ 156 / Có 157** |

→ Giá trị tồn core (báo cáo định giá, mốc giá cuối kỳ, khóa sổ) chỉ còn hàng ở kho chính = TK 156.
Số dư TK 157 = tổng **GT còn lại** của **Tồn Kho > Hoạt động > Giá Bình Quân Kỳ > Transit Batches
(TK 157)**.

### 2.2 Quy trình cuối kỳ

1. Post đủ hóa đơn mua / hoàn tiền của kỳ.
2. Kỳ GBQK: **Tính → Áp → Sinh BT → Khóa**, **theo đúng thứ tự các kỳ** (batch kỳ trước phải có
   trước khi Tính kỳ sau).
3. (Tùy chọn) Khóa sổ định giá kho core ngày cuối kỳ: chỉ còn chênh lệch làm tròn.
4. Đối chiếu: THTK chọn kho 157 → giá trị cuối kỳ = số dư TK 157; THTK để trống kho = TK 156.

Trên dòng SP của kỳ: *Nhập 157 SL / GT* (phần lấy từ batch kỳ trước, vào công thức BQ), *Nhập 157 SL
theo BQ* (hàng chuyển đi và nhận về trong cùng kỳ, định giá theo BQ kỳ, không vào công thức).

### 2.3 Đổi cờ khi location đã có phiếu

Bật / tắt cờ thì module tính lại hướng nhập / xuất (`is_in` / `is_out`) của các phiếu đã hoàn tất
qua location đó, nhưng **không** tính lại giá trị phiếu. Sau khi đổi: Reset → Tính → Áp lại các kỳ
GBQK từ kỳ có phiếu qua location đó. Tốt nhất bật cờ ngay từ đầu — chuyển dữ liệu từ v17 bằng
`odoo-cutoff-transfer` thì bật **sau khi nạp gói đầu kỳ, trước khi nạp lô** (phiếu bán từ 157 khi
đó được nạp không giá trị, cảnh báo "không định giá trên đích, bỏ giá trị nguồn" là đúng; GBQK ghi
lại khi Áp).

### 2.4 Báo cáo kho (S06, THTK)

- **Chọn kho 157**: nhập = phiếu kho → 157 (giá trị phiếu), xuất = bán / nhận về (giá trị
  consumption của batch). Kỳ chưa Áp thì phiếu chưa có batch được ghép FIFO tạm.
- **Để trống kho**: số liệu định giá cả công ty = **chỉ TK 156** (hàng ở 157 không gồm).
- Chọn tất cả location nội bộ = TK 156 + TK 157.

### 2.5 Giới hạn

- Phiếu 157 → nơi khác (hủy, kiểm kê, trả NCC) GBQK không xử lý: giá trị không ra khỏi TK 157.
- Phiếu 157 → kho là phiếu nhập của core → có thể bị core tính lại giá (sửa dòng chi tiết phiếu đã
  hoàn tất, landed cost chọn phiếu đó...) như phiếu khách trả (`NOTES_V19_VALUATION.md` §4). Có thì
  Tính + Áp lại theo SP.
- Nhóm SP **Real-time** không dùng với GBQK (đã ghi ở NOTES §1).

---

## 3. Công ty không dùng GBQK

Core V19 không có khái niệm TK 157 cho hàng gửi bán: location nội bộ có công ty luôn được định
giá chung vào TK 156; phiếu bán từ kho 157 là phiếu xuất bình thường (giá vốn core). **Không bật cờ
Kho 157 (GBQK)** (cờ chỉ có khi cài GBQK; bật mà không chạy GBQK thì không ai ghi bút toán 157 và
hàng bán từ 157 không có giá vốn).

### 3.1 Cấu hình

- Location kho 157 như mục 1. Không cần thêm gì ở định giá kho core.
- Nhóm SP theo cấu hình core của công ty (AVCO/FIFO, Periodic/Real-time) — không đổi.

### 3.2 Hạch toán TK 157 (ghi tay)

Tự động: core đã hạch toán hàng ở 157 trong TK 156; bán từ 157 có giá vốn như bán từ kho chính
(Real-time: lúc post hóa đơn; Periodic: qua khóa sổ / kế toán tự ghi).

Nếu cần trình bày TK 157 riêng trên sổ / BCTC:

1. Cuối kỳ: THTK **chọn kho 157** → lấy **giá trị tồn cuối kỳ**.
2. Nếu dùng khóa sổ định giá kho core: **chạy khóa sổ trước**.
3. Ghi bút toán **Nợ 157 / Có 156** = giá trị tồn cuối kỳ của kho 157, ngày cuối kỳ, rồi **đảo
   bút toán** ngày đầu kỳ sau (nút Đảo ngược, chọn ngày đảo).
   - Không đảo thì lần khóa sổ core sau thấy TK 156 thấp hơn giá trị tồn core → tự ghi Nợ 156 / Có
     TK biến động, mất bút toán 157.

### 3.3 Báo cáo kho

- **Chọn kho 157**: nhập = phiếu kho → 157 định giá theo **bình quân định giá tại ngày chuyển**;
  xuất bán = giá vốn core của phiếu bán; nhận về = bình quân tại ngày nhận. Vì định giá chung một
  giá cho cả công ty, kho 157 có thể còn chênh lệch nhỏ khi đã hết hàng (giống mọi kho con khác).
- **Để trống kho**: cả công ty, **gồm** hàng ở kho 157 (= TK 156 trên định giá core).

### 3.4 Muốn tự động TK 157 khi không dùng GBQK

Hiện **chưa làm** (cần thêm module / mở rộng — chờ quyết định). Hướng có thể: tách cờ kho 157 ra
module riêng để báo cáo định giá kho 157 theo FIFO, và mở rộng khóa sổ core để ghi Nợ 632 / Có 157
cho phiếu bán từ 157 (core V19 chỉ tự ghi được kho ↔ 157 qua `valuation_account_id`, không ghi
phần bán từ 157).

---

## 4. Trạng thái kiểm tra

Test 2026-10-22 trên data thật: `vsg` (v17, có `fg_sale_kcx`, kho `WH/HQ`) chuyển sang v19 bằng
`odoo-cutoff-transfer` (gói đầu kỳ tại 31/05/2026 + lô chứng từ 01–30/06/2026). Tháng 6 có 2 đơn
KCX: `WH/INT/00001`, `WH/INT/00002` (kho → HQ, 4 dòng, 285 SP) rồi `PXK/2026/0349`, `PXK/2026/0386`
(HQ → khách) cùng ngày.

| DB | Vai trò |
|---|---|
| `vsg_src19` | nguồn v17 (bản sao `vsg`, cài `fg_transfer_to`; gói id 1, lô id 2) |
| `vsg_19_pkg` | đích v19 sau khi nạp gói, trước cấu hình GBQK (FIFO như nguồn) |
| `vsg_19_loaded` | + cấu hình GBQK (AVCO, TK, cờ 157 trên `WH/HQ`) + lô tháng 6, chưa chạy GBQK |
| `vsg_19` | + kỳ GBQK 06/2026 đã Tính / Áp / Sinh BT (đã gỡ 134 bút toán STJ chuyển từ GBQK v17) |
| `vsg_19_nogbqk` | `vsg_19_pkg` + lô tháng 6, cờ tắt, không kỳ GBQK (công ty không dùng GBQK) |

Đích cài thêm `fg_sale_kcx` (đổi tên `WH/Customs` → `HQ` như nguồn) và `fg_sample_receipt` (location
hàng mẫu đặt dưới location view "Virtual Locations" cho trùng tên đầy đủ nguồn; không thì phiếu
WH/HM nạp thành điều chỉnh tồn kho và GBQK coi là nhập khác).

- [x] Cài `fg_gia_binh_quan_ky` 19.0.1.2.0, `fg_vn_stock_reports`, `fg_sale_kcx`, `fg_sample_receipt`
      trên DB mới.
- [x] GBQK kỳ 06/2026 so với kỳ 2026/06 của v17: 124/124 dòng khớp từng ô trừ `Keo FL-5285`
      (+2 SP chỉ có ở đích: `Khung Nhôm`, `Mực in 2010B`). Ba SP này có tồn trên quant (lot "old")
      không có SVL ở nguồn — cảnh báo "3 sản phẩm lệch SL kho với SL định giá" lúc trích gói, lỗi
      dữ liệu nguồn. `Keo FL-5285` làm tồn cuối lệch +611.413; ngoài ra tổng nhập / hàng mẫu /
      tồn đầu khớp. 134 bút toán như v17; TK 157 Nợ = Có = 48.450.000 khớp v17; TK 156 / 632
      chỉ lệch đúng 611.413 trên.
- [x] Kho 157: 4 batch (một batch / phiếu chuyển), giá 170.000 như v17, mỗi batch tiêu thụ hết bởi
      phiếu bán; `value_remaining` = 0 = số dư TK 157 cuối tháng. Phiếu kho → HQ `is_out`, HQ → khách
      không định giá, giá trị phiếu do GBQK ghi.
- [x] Tồn core 30/06 (`stock_value`) 374.909.268 vs sổ cái 156 374.908.883: khóa sổ core chạy thử
      chỉ ghi chênh lệch làm tròn 385đ.
- [x] Báo cáo THTK / S06 06/2026: chọn `WH/HQ` nhập 48.450.000 = xuất, tồn 0; để trống kho = chọn
      `WH/Tồn kho` = chọn mọi location nội bộ, tồn cuối 374.908.883 = sổ cái 156.
- [x] Không dùng GBQK (`vsg_19_nogbqk`, cờ tắt): phiếu bán từ HQ là phiếu xuất core (giá trị nguồn),
      kho → HQ không định giá; THTK / S06 chọn `WH/HQ` nhập 48.450.000 (ghép FIFO theo phiếu bán)
      = xuất, tồn 0. S06 cần TK định giá nhóm SP là 15x (nguồn để `02` → S06 rỗng).
- [ ] Chưa có dữ liệu thật cho: nhận hàng từ 157 về kho (cùng kỳ / khác kỳ), hàng nằm ở 157 qua
      cuối kỳ.
