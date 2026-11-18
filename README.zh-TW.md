# BGYM DD05 走步機 × Home Assistant

透過藍牙（FTMS）在 Home Assistant 監看與控制 **BGYM DD05** 走步機，包含手機遙控儀表板、結構化的間歇訓練課表執行器、Assist 中文語音指令，以及選用的 Google 助理／Google Home 控制。

> English: [README.md](README.md)

> ⚠️ **使用前請先讀「[安全須知](#安全須知)」。** 走步機可能造成受傷。本專案不會自行啟動跑帶，使用時你一定要站在機器上，並夾好安全鑰匙。

## 功能

- **即時數據**：速度、坡度、時間、距離、熱量、心率。
- **遙控儀表板**（`dashboards/treadmill_remote.yaml`）：開始／暫停、速度 ±0.5 km/h、坡度 ±1 %、停止。
- **訓練課表**（`homeassistant/packages/dd05_training.yaml` + `dashboards/training.yaml`）：以時間戳計時的通用分段執行器（含差異寫入與讀回重送保護），內建「間歇 10 分」（含 SVG 課表圖）與「自訂課表」（13 個滑桿設定暖身／快走／緩和／收操與輪數）。新增固定課表只要多寫一支定義腳本。
- **語音**：Assist 繁體中文句子（開始走／暫停走／停止走／加速度／減速度／加坡度／減坡度，以及間歇訓練開始／暫停／結束，預設啟動間歇 10 分），同一組腳本也可開放給 Google 助理（在 Google Home 裡是「場景」）。

## 測試環境

| 項目 | 版本／數值 |
|---|---|
| 走步機 | BGYM DD05（藍牙回報為 **FitShow FS-BT-F5**，韌體 `V1.0.5beta`、硬體 `V1.0.0`） |
| 藍牙服務 | Fitness Machine Service（FTMS，UUID `0x1826`） |
| HA 可控範圍 | 速度 1.0–6.0 km/h（每格 0.1）、坡度 0–15 %（每格 1） |
| Home Assistant | 2026.10.4（Docker） |
| 整合 | [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6（pyftms 0.4.10）＋ `patches/` 內的修正 |
| 藍牙 proxy | ESP32-C3（esp32-c3-devkitm-1）、ESPHome 2026.10.1、**ESP-IDF 固定 5.5.5** |

其他使用 FitShow 模組、支援 FTMS 的走步機很可能也能用，但目前只實測過 DD05。

## 架構

```
BGYM DD05（FitShow FS-BT-F5，FTMS 0x1826）
        │  藍牙 LE（主動連線）
        ▼
ESP32-C3 ESPHome 藍牙 proxy（esphome/bt-proxy-esp32c3.yaml）
        │  Wi-Fi，ESPHome 原生 API
        ▼
Home Assistant ── hassio-ftms（自訂整合，已套修正）
        ├── 實體：sensor.treadmill_*、number.treadmill_*、button.treadmill_*
        ├── packages/dd05_treadmill_remote.yaml → 遙控腳本
        ├── packages/dd05_training.yaml         → 輔助元件、課表執行器、安全守護
        ├── 儀表板（走步機遙控、Training）
        ├── Assist 自訂句子 + intent_script
        └── Google 助理（腳本以場景開放）
```

## 目錄

```
esphome/                       ESP32-C3 藍牙 proxy 設定與 secrets 範例
homeassistant/packages/        HA packages（腳本、輔助元件、自動化）
homeassistant/www/training/    Training 儀表板課表圖（放到 /config/www/training/）
homeassistant/custom_sentences/zh-TW/   Assist 語音句子
homeassistant/configuration-snippets/   intent_script、google_assistant、packages 啟用片段
dashboards/                    儀表板（貼到「原始設定編輯器」）
homeassistant/custom_components/ftms/  已修改的 hassio-ftms 檔案（不是完整整合）
patches/                       hassio-ftms 修正（Apache-2.0，見 patches/README.md）
docs/                          架構、回饋上游說明，以及按日的測試修正紀錄
```

## 安裝步驟

### 1. 藍牙 proxy（ESP32-C3 + ESPHome）

1. 把 `esphome/secrets.yaml.example` 複製成 `esphome/secrets.yaml` 並填好。
2. 燒錄 `esphome/bt-proxy-esp32c3.yaml`（第一次用 USB，之後可 OTA）。
3. 把 proxy 放在走步機旁邊（同一個房間），HA 會透過 ESPHome 整合自動發現。

**為什麼要固定 ESP-IDF 5.5.5？** ESPHome 2026.10.1 預設用 ESP-IDF 5.5.6。用這版時 proxy 能連上 DD05，但 GATT 服務探索會提早中斷，FTMS 服務 `0x1826` 一直沒回報，整合無法建立。調高 `CONFIG_BT_GATTC_MAX_CACHE_CHAR` 沒有用；改成 `framework: version: 5.5.5` 才解決。ESPHome 會警告「不是建議版本」，屬正常。之後升級 ESPHome 請重新測試，新版 IDF 若已修好就可以拿掉固定版本。

作者自己的 proxy 沒有設 API 加密和 OTA 密碼；這份範例加上了兩者，建議使用。

### 2. hassio-ftms 整合與修正

1. 安裝 [hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6（HACS 自訂儲存庫，或手動複製到 `/config/custom_components/ftms/`）。
2. 套用修正：
   ```bash
   cd /config
   patch -p1 < patches/hassio-ftms-0.24.6-lenient-training-status.patch
   ```
3. 把 `homeassistant/custom_components/ftms/` 內三個檔案（`__init__.py`、`sensor.py`、`updater_patch.py`）複製到 `/config/custom_components/ftms/` 對應位置。`updater_patch.py` 是新檔，必須和 `__init__.py` 放在同一層。詳見 `patches/README.md` 與 `homeassistant/custom_components/ftms/README.md`。
4. 重新啟動 HA，DD05 會以藍牙（FTMS）被發現，加入即可。本專案所有 YAML 都使用 `*.treadmill_*` 實體 ID（裝置名稱為「Treadmill」時的預設值）；如果你的不同，請改裝置或實體名稱。

**這個修正做什麼：** DD05 送出的 *Training Status* 通知帶有 FTMS 規格未定義的旗標位元（例如 `0x46`），pyftms 0.4.10 遇到會拋出例外，整合建立就中斷。修正只保留規格定義的兩個旗標位元；若仍無法解析，就記一行警告並略過，不讓整合當掉。詳見 `patches/README.md`。長期應由上游（pyftms／hassio-ftms）修正，見 `docs/upstream-notes.md`。

### 3. Home Assistant packages

1. 先啟用 packages（只需一次），內容見 `homeassistant/configuration-snippets/homeassistant_packages.yaml`。
2. 把 `homeassistant/packages/*.yaml` 複製到 `/config/packages/`。
3. 在 `dd05_training.yaml` 把 `notify.mobile_app_YOUR_PHONE` 換成你手機的通知服務（或刪掉那一步）。
4. 檢查設定後重新啟動。首次使用「自訂課表」前，可於開發者工具呼叫 `input_number.set_value` 為 `input_number.training_custom_*` 寫入建議預設值（`rounds: 14`、暖身 `90s 3.0/0`、快走 `120s 4.5/5`、緩和 `60s 3.0/0`、收操 `90s 3.0/0`，總長 `45:00`）；這些實體刻意不設 `initial:`，重載與重啟後會保留你的調整。

### 4. 儀表板

1. 將 `homeassistant/www/training/interval10_v2.svg` 複製到 `/config/www/training/interval10_v2.svg`（HA 以 `/local/training/interval10_v2.svg` 存取；若 `/config/www/` 為首次建立，需重啟 HA 才會掛載 `/local/`）。
2. 設定 → 儀表板 → 新增儀表板（例如「走步機」圖示 `mdi:walk`、「Training」圖示 `mdi:run`）。進入儀表板 → ⋮ → 編輯 → 原始設定編輯器，分別貼上 `dashboards/treadmill_remote.yaml` 和 `dashboards/training.yaml`。只用內建卡片。

### 5. 語音指令

- **Assist（中文）：** 把 `homeassistant/custom_sentences/zh-TW/*.yaml` 複製到 `/config/custom_sentences/zh-TW/`，把 `configuration-snippets/intent_script.yaml` 合併進 `configuration.yaml`，重新啟動。
- **Google 助理（手動 YAML 設定）：** 把 `configuration-snippets/google_assistant.yaml` 合併到你既有的 `google_assistant:` 區塊，重新啟動後執行 `google_assistant.request_sync`。腳本在 Google Home 裡會是「場景」。

| 說 | 動作 |
|---|---|
| 開始走／走步機開始 | 開始／繼續 |
| 暫停走／走步機暫停 | 暫停 |
| 停止走／走步機停止 | 停止 |
| 加速度／減速度 | 速度 ±0.5 km/h（只在跑帶轉動時） |
| 加坡度／減坡度 | 坡度 ±1 % |
| 開始間歇訓練／訓練暫停／繼續訓練／結束訓練 | 課表開始／暫停與繼續／結束 |

## 訓練課表執行器

- **輔助元件**：`input_select.training_state`（`idle/starting/running/paused/resuming/finishing`，`initial: idle`）、時間戳、目前階段、輪數、上次寫入值。
- **`script.training_run`**：通用執行器，接收 `program_name` 和 `segments` 清單（`{name, round, dur, s0, i0, s1?, i1?, ramp_dur?, step?}`），用時間戳計算經過時間（不會漂移），只在跑帶轉動時寫入與目標或讀回有差異的速度／坡度；速度與坡度同時變更時中間間隔 0.5 秒，並於 1.5 秒後核對 `sensor` 讀回、不符僅針對該項補送（最多 4 次）。
- **`script.training_interval_10`**：「間歇 10 分」：暖身 45 秒 `3.0 km/h / 0%`，5 輪 ×（快走 60 秒 `4.5 km/h / 4%` ＋ 緩和 45 秒 `3.0 km/h / 0%`），收操 30 秒 `2.0 km/h / 0%`。總長 10:00（600 秒），結束送停止；對應 `/training/interval-10` 課表圖頁面。
- **`script.training_custom`**：讀取 13 個 `input_number.training_custom_*` 滑桿快照（輪數 5–30、時間 30–120s、速度 2.0–6.0 km/h、坡度 0–15%）組成課表並交由 `script.training_run` 執行，並以 `sensor.training_custom_total_mmss` 顯示預估總時長（建議預設 14 輪共 `45:00`）。
- **`script.training_pause`／`script.training_end`**：暫停與繼續切換；中止並停止。
- **安全守護自動化**：執行中若速度 < 0.1 km/h 持續 3 秒（按停止、拔安全鑰匙）或感測器 unavailable 持續 10 秒，立即中止課表並通知；另含 `automation.training_run_died_guard` 防止執行器異常中止時跑帶未停。
- 新增課表：複製 `training_interval_10`，改 `program_name` 和 `segments`，在 Training 儀表板加一顆按鈕和子視圖即可，執行器不用改。

## 疑難排解

| 狀況 | 原因／解法 |
|---|---|
| 一直找不到裝置或連線失敗 | FitShow 手機 App（或別支手機）佔住藍牙連線。DD05 同時只接受一個連線，請關掉 App 或手機藍牙。 |
| proxy 連得上但整合建立失敗、找不到 FTMS 服務 | GATT 服務探索被截斷（只看到前面幾個標準服務，例如裝置資訊 `0x180A`）。請照 `esphome/bt-proxy-esp32c3.yaml` 用 ESP-IDF 5.5.5；重燒後清掉 proxy 對走步機的 GATT 快取，或兩者都重新上電。 |
| 建立時出現 Training Status 解析錯誤 | 套用 `patches/` 內的修正。 |
| 記錄出現 `Skipping unparsable FTMS training status …` | 套修正後的正常現象，DD05 會送非標準狀態（例如代碼 83 加文字），無害。 |
| `sensor.treadmill_status` 顯示 unavailable | 已知問題，同樣由非標準狀態造成，不影響速度、坡度和控制，尚未修正。 |
| 按開始後跑帶沒有馬上轉 | FitShow 跑帶開始後會倒數幾秒；執行器最多等 30 秒速度 > 0。 |
| 停止時按速度鈕沒反應 | 刻意設計：只在跑帶轉動時才調速度。 |
| proxy 離走步機太遠常斷線 | 在同一個房間放一台 proxy，隔牆訊號會明顯變差。 |

## 安全須知

- **一定要把安全鑰匙夾在衣服上。** 拔掉時跑帶必須停止，守護自動化也會中止課表。
- **只有你站在走步機上時才使用遙控、語音或課表。** 不要幫別人或對著空機器啟動。
- **課表絕不會自動開始。** 沒有任何排程或自動化會啟動跑帶或課表；訓練相關自動化只會停止或中止。
- 跑帶靜止時絕不寫入速度坡度；數值限制在 1.0–6.0 km/h、0–15 %。
- HA 重新啟動後執行器回到 `idle`。
- 讓小孩和寵物遠離。新課表先用低速測試。

## 開發紀錄

- [docs/2026-11-18-custom-interval-test.md](docs/2026-11-18-custom-interval-test.md)：`script.training_custom` 30 分鐘（32 段、31 次換段）實測紀錄：零錯段、零補送、零跳回舊值，驗證 2026-11-17 換段修正完全有效（時間為 Asia/Taipei）。
- [docs/2026-11-17-dd05-training-update.md](docs/2026-11-17-dd05-training-update.md)：修正段落交接速度覆蓋 bug 並實測驗證、改版「間歇 10 分（第二版）」＋ SVG 課表圖、新增 13 個滑桿「自訂課表」、移除 3 分／35 分課表與更新語音設定（時間為 Asia/Taipei）。
- [docs/2026-11-16-dd05-debug-log.md](docs/2026-11-16-dd05-debug-log.md)：控制逾時、課表執行器、`updater_patch.py` 顯示丟包修正，以及當時記錄的段落交接速度問題（已於 2026-11-17 修正）。

## 免責聲明

本專案為非官方的社群作品，**與 BGYM、FitShow、Home Assistant／Nabu Casa 無任何關聯，也未獲其背書或支援**。所有商標屬各自所有者。使用風險自負，你需自行負責器材的安全操作。遠端控制運動器材可能造成傷害；修改整合後，更新時可能失效。

## 授權

本專案自有檔案的授權見 [LICENSE](LICENSE)。`patches/` 內的修正改的是 hassio-ftms，其授權為 Apache-2.0（`patches/LICENSE-hassio-ftms-Apache-2.0`）。

## 致謝

- [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 與 pyftms（Sergey Dudanov）。
- ESPHome 藍牙 proxy。
