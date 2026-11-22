# BGYM DD05 走步機 × Home Assistant

透過藍牙（FTMS）在 Home Assistant 監看與控制 **BGYM DD05** 走步機，包含手機遙控儀表板、結構化的間歇訓練課表執行器、Assist 中文語音指令，以及選用的 Google 助理／Google Home 控制。

> English: [README.md](README.md)

> ⚠️ **使用前請先讀「[安全須知](#安全須知)」。** 走步機可能造成受傷。本專案不會自行啟動跑帶，使用時你一定要站在機器上，並夾好安全鑰匙。

## 功能

- **即時數據**：速度、坡度、時間、距離、熱量、心率。
- **遙控儀表板**（`dashboards/treadmill_remote.yaml`，需 HACS [button-card](https://github.com/custom-cards/button-card)）：主頁可加減速度（±0.5 km/h）與坡度（±1 %）、看時間與距離、開始／暫停／停止，並用 HIIT 開關決定「開始」是跑課表還是手動控制。設定子頁用 +/- 調整暖身／快走／緩和／收操與輪數。截圖見下方。
- **訓練課表**（`homeassistant/packages/dd05_training.yaml`）：以時間戳計時的通用分段執行器（含差異寫入與讀回重送保護）。HIIT 依設定頁的參數組成課表（建議預設 14 輪、總長 `45:00`）。舊的固定「間歇 10 分」已改成相容包裝：語音或 Google 場景「間歇訓練開始」仍呼叫 `script.training_interval_10`，但會先開啟 HIIT，再依目前設定開始。獨立的 Training 儀表板（`dashboards/training.yaml`）仍保留、內容未改。
- **語音**：Assist 繁體中文句子（開始走／暫停走／停止走／加速度／減速度／加坡度／減坡度，以及間歇訓練或 HIIT 的開始／暫停／結束），同一組腳本也可開放給 Google 助理（在 Google Home 裡是「場景」）。

**主頁**：速度／坡度、時間與距離、課表狀態、開始／暫停／停止，以及 HIIT 開關與設定入口。HIIT 打開時，按開始會依設定頁的參數跑課表；關掉時則是手動控制。

![走步機主頁](docs/images/remote.png)

**設定頁**：用 +/- 調整暖身、快走、緩和、收操與輪數。+/- 會立刻寫入輔助元件；「儲存」只是回到主頁。

![走步機設定頁](docs/images/settings.png)

## 測試環境

| 項目 | 版本／數值 |
|---|---|
| 走步機 | BGYM DD05（藍牙回報為 **FitShow FS-BT-F5**，韌體 `V1.0.5beta`、硬體 `V1.0.0`） |
| 藍牙服務 | Fitness Machine Service（FTMS，UUID `0x1826`） |
| HA 可控範圍 | 速度 1.0–6.0 km/h（每格 0.1）、坡度 0–15 %（每格 1） |
| Home Assistant | 2026.10.4（Docker） |
| 整合 | [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6（pyftms 0.4.10）＋ `patches/` 內的修正 |
| 藍牙 proxy | ESP32-C3（esp32-c3-devkitm-1）、ESPHome 2026.10.1、**ESP-IDF 固定 5.5.5** |
| 自訂卡片 | [button-card](https://github.com/custom-cards/button-card) **7.0.1**（HACS；走步機儀表板必裝） |

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
        ├── packages/dd05_treadmill_remote.yaml → 遙控加減速度／坡度腳本
        ├── packages/dd05_training.yaml         → 輔助元件、HIIT 課表執行器、遙控包裝腳本、安全守護
        ├── 儀表板（走步機遙控／設定、選用的 Training）
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

這一章是給**同樣擁有 BGYM DD05、想套用到自己 Home Assistant（HA）**的人。請依序做；`/config` 指你的 HA 設定資料夾（Docker 是掛載進容器的 `/config`，HA OS 可用 Samba、File editor 或 SSH 類附加元件存取）。

### 0. 前提

- **Home Assistant**：Docker 或 HA OS 都可以。作者的測試環境是 Docker（見上方「[測試環境](#測試環境)」，Home Assistant 2026.10.4）；藍牙是透過 ESPHome proxy，不需要 HA 主機自己有藍牙卡。
- **走步機**：要支援藍牙 FTMS（Fitness Machine Service，`0x1826`）。DD05 已實測可用；其他機型尚未驗證。
- **ESPHome 藍牙 proxy**：例如 ESP32-C3，放在走步機附近（同一個房間）。設定見下一步與 `esphome/bt-proxy-esp32c3.yaml`。
- **hassio-ftms 版本**：repo 內的修正檔是針對 hassio-ftms **0.24.6**（pyftms 0.4.10）。用別的版本請不要直接覆蓋檔案，先比對差異。
- **button-card**：走步機儀表板使用自訂卡片 `custom:button-card`，請先用 HACS 安裝 [button-card](https://github.com/custom-cards/button-card)（實測 7.0.1）。Training 儀表板仍只用內建卡片。
- 同一時間 DD05 只接受一個藍牙連線，使用前請先關掉 FitShow 手機 App。

### 1. 藍牙 proxy（ESP32-C3 + ESPHome）

1. 把 `esphome/secrets.yaml.example` 複製成 `esphome/secrets.yaml` 並填好。
2. 燒錄 `esphome/bt-proxy-esp32c3.yaml`（第一次用 USB，之後可 OTA）。
3. 把 proxy 放在走步機旁邊（同一個房間），HA 會透過 ESPHome 整合自動發現。

**為什麼要固定 ESP-IDF 5.5.5？** ESPHome 2026.10.1 預設用 ESP-IDF 5.5.6。用這版時 proxy 能連上 DD05，但 GATT 服務探索會提早中斷，FTMS 服務 `0x1826` 一直沒回報，整合無法建立。調高 `CONFIG_BT_GATTC_MAX_CACHE_CHAR` 沒有用；改成 `framework: version: 5.5.5` 才解決。ESPHome 會警告「不是建議版本」，屬正常。之後升級 ESPHome 請重新測試，新版 IDF 若已修好就可以拿掉固定版本。

作者自己的 proxy 沒有設 API 加密和 OTA 密碼；這份範例加上了兩者，建議使用。

### 2. hassio-ftms 整合與修正

1. 安裝 [hassio-ftms](https://github.com/dudanov/hassio-ftms) 0.24.6（HACS 自訂儲存庫，或手動複製到 `/config/custom_components/ftms/`）。
2. 套用 Training Status 修正（把 `patches/` 內的 patch 檔放到可存取處，在 `/config` 執行；先加 `--dry-run` 確認能套用，回退用 `-R`，見 `patches/README.md`）：
   ```bash
   cd /config
   patch -p1 < patches/hassio-ftms-0.24.6-lenient-training-status.patch
   ```
3. 把 `homeassistant/custom_components/ftms/` 內三個檔案（`__init__.py`、`sensor.py`、`updater_patch.py`）複製到 `/config/custom_components/ftms/` 對應位置。`updater_patch.py` 是新檔，必須和 `__init__.py` 放在同一層。三個檔案的用途：

   | 檔案 | 作用 |
   |---|---|
   | `__init__.py` | 寬鬆解析 Training Status；控制逾時 `CONTROL_TIMEOUT = 8.0`（pyftms 預設 2 秒對 DD05 太短）；載入 `updater_patch` |
   | `sensor.py` | ENUM 感測器值缺漏時維持 `None`，不再退回 `0` 而拋出 `ValueError` |
   | `updater_patch.py` | 修正 pyftms 0.4.10 在 DD05 交替送兩種 Treadmill Data 封包時丟掉整筆通知（`KeyError: 'step_count'`），否則速度、坡度顯示會落後 |

   詳見 `patches/README.md` 與 `homeassistant/custom_components/ftms/README.md`。
4. 重新啟動 HA，DD05 會以藍牙（FTMS）被發現，加入即可。本專案所有 YAML 都使用 `*.treadmill_*` 實體 ID（裝置名稱為「Treadmill」時的預設值）；如果你的不同，見下方「[7. 實體名稱對照](#7-實體名稱對照)」。

> [!WARNING]
> **透過 HACS 更新 hassio-ftms 會覆蓋這些修改。** 更新後請重新套用 patch 並重新複製三個檔案，再重啟 HA。更新前建議先備份 `/config/custom_components/ftms/`。若沒有重新套用，DD05 可能又出現 Training Status 解析錯誤、速度坡度顯示落後等問題。

**上游現況：** 這些修正是本地 monkey-patch。`docs/upstream-notes.md` 目前仍是**尚未送出的草稿**（issue 標題與內容、送出前檢查清單），並引用 python-pyftms PR #60 下的兩則相關留言；文件中沒有任何已合併的上游修正，所以暫時每次更新都要自己重新套用。

**這個修正做什麼：** DD05 送出的 *Training Status* 通知帶有 FTMS 規格未定義的旗標位元（例如 `0x46`），pyftms 0.4.10 遇到會拋出例外，整合建立就中斷。修正只保留規格定義的兩個旗標位元；若仍無法解析，就記一行警告並略過，不讓整合當掉。詳見 `patches/README.md`。長期應由上游（pyftms／hassio-ftms）修正，見 `docs/upstream-notes.md`。

### 3. 複製檔案總覽

| repo 來源 | 放到你的 HA | 備註 |
|---|---|---|
| `homeassistant/packages/*.yaml`（`dd05_treadmill_remote.yaml`、`dd05_training.yaml`） | `/config/packages/` | 需先在 `configuration.yaml` 啟用 packages（見下一步） |
| `dashboards/*.yaml`（`treadmill_remote.yaml`、`training.yaml`） | 不是複製檔案：新增儀表板後用「原始設定編輯器」貼上；走步機頁需要 button-card，且 URL 路徑須為 `treadmill-remote` | 見步驟 5 |
| `homeassistant/www/training/interval10_v2.svg` | `/config/www/training/interval10_v2.svg` | 給選用的 Training 儀表板「間歇 10 分」頁用的課表圖 |
| `homeassistant/custom_sentences/zh-TW/*.yaml`（`treadmill.yaml`、`training.yaml`） | `/config/custom_sentences/zh-TW/` | Assist 中文句子（選用） |
| `homeassistant/configuration-snippets/intent_script.yaml` | 合併進 `configuration.yaml` | Assist 語音用（選用） |
| `homeassistant/configuration-snippets/google_assistant.yaml` | 合併進 `configuration.yaml` 既有的 `google_assistant:` 區塊 | Google 語音用（選用） |
| `homeassistant/configuration-snippets/homeassistant_packages.yaml` | 合併進 `configuration.yaml` | 啟用 packages，只需一次 |

### 4. Home Assistant packages

1. 先啟用 packages（只需一次），把 `homeassistant/configuration-snippets/homeassistant_packages.yaml` 的內容加進 `configuration.yaml`（已經有 `homeassistant:` 區塊就把 `packages:` 併進去，不要重複寫兩個 `homeassistant:`）：
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. 把 `homeassistant/packages/*.yaml` 複製到 `/config/packages/`。
3. 通知設定：`dd05_training.yaml` 的 `script.training_notify` 內有 `notify.mobile_app_YOUR_PHONE`（repo 內只有這一處），請換成你手機的通知服務，或把整個 `choose:` 通知區塊刪掉。腳本一律會先建立 HA 內的 persistent notification，所以刪掉手機通知後仍看得到訊息。詳見步驟 6。
4. 檢查設定後重新啟動（見步驟 8）。首次使用 HIIT／設定頁前請先寫入預設值，也在步驟 8。

### 5. 儀表板

1. 用 HACS 安裝 [button-card](https://github.com/custom-cards/button-card)（實測 7.0.1），這是走步機儀表板必裝的自訂卡片。
2. 若要一併使用獨立的 Training 儀表板，將 `homeassistant/www/training/interval10_v2.svg` 複製到 `/config/www/training/interval10_v2.svg`（HA 以 `/local/training/interval10_v2.svg` 存取；若 `/config/www/` 為首次建立，需重啟 HA 才會掛載 `/local/`）。
3. 設定 → 儀表板 → 新增儀表板，標題例如「走步機」、圖示 `mdi:walk`。**URL 路徑請設成 `treadmill-remote`**（設定子頁會導向 `/treadmill-remote/custom`，返回主頁為 `/treadmill-remote/remote`；路徑不同就要改 YAML 裡的這兩條）。進入儀表板 → ⋮ → 編輯 → 原始設定編輯器，貼上 `dashboards/treadmill_remote.yaml`。
4. （選用）同樣方式新增「Training」儀表板（圖示 `mdi:run`），貼上 `dashboards/training.yaml`。這份仍只用內建卡片，內容與 2026-11-17 相同。請注意：其中「間歇 10 分」的開始鈕仍呼叫 `script.training_interval_10`，現在會改跑設定頁的 HIIT，而不是舊的固定 10 分鐘課表。日常操作建議直接用走步機頁。

### 6. 語音指令與通知／Google 佔位設定（選用）

不用 Assist 或 Google 語音可略過語音部分；但通知佔位仍建議處理。

- **手機通知佔位：** `homeassistant/packages/dd05_training.yaml` 的 `notify.mobile_app_YOUR_PHONE` 要換成你自己的通知服務（開發者工具 → 動作裡搜尋 `notify.mobile_app_` 可找到），或移除該步驟。只有 `dd05_training.yaml` 用到；`dd05_treadmill_remote.yaml` 與儀表板沒有通知設定。
- **Assist（中文）：** 把 `homeassistant/custom_sentences/zh-TW/*.yaml` 複製到 `/config/custom_sentences/zh-TW/`，把 `configuration-snippets/intent_script.yaml` 合併進 `configuration.yaml`，重新啟動。Assist 語言需設為繁體中文（zh-TW）。
- **Google 助理（手動 YAML 設定）：** 把 `configuration-snippets/google_assistant.yaml` 合併到你既有的 `google_assistant:` 區塊，重新啟動後執行 `google_assistant.request_sync`。腳本在 Google Home 裡會是「場景」。檔內有兩個佔位要換成你自己的：
  - `project_id: YOUR_GOOGLE_PROJECT_ID`：你的 Google Cloud／Actions 專案 ID。
  - `service_account: !include SERVICE_ACCOUNT.json`：你的服務帳戶金鑰檔（放在 `/config`，**不要公開、不要提交到 git**）。

  已經有 Google Assistant 設定的人，只要合併 `entity_config:` 底下的 `script.*` 項目即可，不要覆蓋原有的 `project_id`、`service_account`。

| 說 | 動作 |
|---|---|
| 開始走／走步機開始 | 開始／繼續 |
| 暫停走／走步機暫停 | 暫停 |
| 停止走／走步機停止 | 停止 |
| 加速度／減速度 | 速度 ±0.5 km/h（只在跑帶轉動時） |
| 加坡度／減坡度 | 坡度 ±1 % |
| 開始間歇訓練／開始 HIIT／訓練暫停／繼續訓練／結束訓練 | 開啟 HIIT 並依目前設定開始課表／暫停與繼續／結束 |

### 7. 實體名稱對照

本 repo 的 packages 與儀表板只使用下列走步機實體（已逐檔查核；`configuration-snippets` 內沒有走步機實體，只有 `script.*`）：

| 實體 ID | 用途 | 使用的檔案 |
|---|---|---|
| `sensor.treadmill_speed` | 目前速度（判斷跑帶是否轉動、安全守護、讀回驗證） | `dd05_treadmill_remote.yaml`、`dd05_training.yaml`、兩份儀表板 |
| `sensor.treadmill_inclination` | 目前坡度 | 同上 |
| `number.treadmill_speed` | 寫入目標速度 | `dd05_treadmill_remote.yaml`、`dd05_training.yaml` |
| `number.treadmill_inclination` | 寫入目標坡度 | 同上 |
| `button.treadmill_start_resume` | 開始／繼續 | 同上 |
| `button.treadmill_pause` | 暫停 | 同上 |
| `button.treadmill_stop` | 停止 | 同上 |
| `sensor.treadmill_time_elapsed` | 已進行時間 | 只有 `dashboards/treadmill_remote.yaml` |
| `sensor.treadmill_distance_total` | 總距離 | 只有 `dashboards/treadmill_remote.yaml` |

`sensor.treadmill_status`、`switch.treadmill_connection` 等實體在 packages 與儀表板中**沒有用到**，名稱不同也沒關係。

如果你的實體 ID 不同（例如裝置名稱不是「Treadmill」），有兩種做法：

1. **（最簡單）改 HA 的實體 ID：** 設定 → 裝置與服務 → 實體，逐一點進上表的實體 → 齒輪 → 把「實體 ID」改成上表名稱。HA 會自動更新儀表板、腳本等引用。
2. **全域搜尋取代：** 在 `packages/*.yaml` 與 `dashboards/*.yaml` 裡，把上表的實體 ID 換成你自己的（一定要整串一起換，避免只換到 `sensor.` 而漏掉 `number.`、`button.`）。

### 8. 重新載入與驗證

**1. 檢查設定：** 開發者工具 → YAML → 檢查設定。有錯誤時先修正，不要重啟。

**2. 何時要重啟、何時可重載：**

| 情況 | 做法 |
|---|---|
| 第一次加入 `packages`、`custom_components/ftms`、`google_assistant` 設定 | 必須重新啟動 HA |
| 第一次建立 `/config/www/`（要讓 `/local/` 生效） | 需重新啟動 HA |
| 之後只改 scripts、input_number、template、intent_script、conversation（自訂句子） | 可在開發者工具 → YAML 用各自的「重新載入」，不必重啟 |
| 更新 hassio-ftms 或重新套用修正 | 重新啟動 HA |

**3. 首次部署後寫入自訂課表預設值：** `input_number.training_custom_*` 刻意不設 `initial:`，重載與重啟後會保留你的調整，但第一次是空的。請在開發者工具 → 動作，用 `input_number.set_value` 逐一寫入建議預設值（14 輪，總長 `45:00`）：

| 實體 | 值 |
|---|---|
| `input_number.training_custom_rounds` | 14 |
| `input_number.training_custom_warmup_dur`／`_warmup_speed`／`_warmup_incline` | 90／3.0／0 |
| `input_number.training_custom_fast_dur`／`_fast_speed`／`_fast_incline` | 120／4.5／5 |
| `input_number.training_custom_rest_dur`／`_rest_speed`／`_rest_incline` | 60／3.0／0 |
| `input_number.training_custom_cooldown_dur`／`_cooldown_speed`／`_cooldown_incline` | 90／3.0／0 |

```yaml
action: input_number.set_value
target:
  entity_id: input_number.training_custom_rounds
data:
  value: 14
```

**4. 驗證清單：**

- 上表的走步機實體不是 `unavailable`（`sensor.treadmill_status` 在 DD05 上可能維持 unavailable，屬已知現象，可忽略）。
- 走步機主頁看得到速度／坡度、時間與距離、HIIT 開關和設定入口；設定頁的預估總時長（`sensor.training_custom_total_mmss`）在預設值下顯示 `45:00`。
- **先不要跑課表。** 站上走步機、夾好安全鑰匙，先把 HIIT 關掉，用走步機儀表板以最低速手動控制：按開始後確認跑帶有轉、速度 +／− 與坡度 +／− 有反應、停止能停下來。確認後再打開 HIIT 跑課表。

### 9. 安全提醒與故障處理

- 先在**低速**測試；旁邊最好有人，能隨時按走步機上的停止或拔掉安全鑰匙。更多見下方「[安全須知](#安全須知)」。
- **HA 控制有延遲，逾時不代表沒執行。** pyftms 預設控制逾時只有 2 秒，DD05 回應較慢時，HA 會先報錯，指令卻可能稍後才生效（`docs/2026-11-16-dd05-debug-log.md` 記錄過 HA 回報逾時後約 5 秒跑帶才開始轉）。看到錯誤時請先看走步機實際狀態，不要連按好幾次開始；本 repo 已把控制逾時調成 8 秒。
- **HA 重啟後 DD05 偶發不回應**（藍牙顯示已連線，但控制逾時、沒有狀態回報；原因尚未查清）：
  1. 把 DD05 **斷電重開**（拔電源再插上）。
  2. 在 HA 重新載入 **ESPHome proxy** 裝置（設定 → 裝置與服務 → ESPHome → 該 proxy → 重新載入）。
  3. 重新載入 **FTMS 整合**。
  4. 先用手動開始／暫停確認控制恢復，再使用課表。

## 訓練課表執行器

- **輔助元件**：`input_select.training_state`（`idle/starting/running/paused/resuming/finishing`，`initial: idle`）、時間戳、目前階段、輪數、上次寫入值，以及 `input_boolean.training_hiit`（主頁開關，不設 `initial:`，重啟後還原上次狀態）。
- **`script.training_run`**：通用執行器，接收 `program_name` 和 `segments` 清單（`{name, round, dur, s0, i0, s1?, i1?, ramp_dur?, step?}`），用時間戳計算經過時間（不會漂移），只在跑帶轉動時寫入與目標或讀回有差異的速度／坡度；速度與坡度同時變更時中間間隔 0.5 秒，並於 1.5 秒後核對 `sensor` 讀回、不符僅針對該項補送（最多 4 次）。
- **`script.training_custom`**：讀取 13 個 `input_number.training_custom_*` 快照（輪數 5–30、時間 30–120s、速度 2.0–6.0 km/h、坡度 0–15%）組成 HIIT 課表，交由 `script.training_run` 執行，並以 `sensor.training_custom_total_mmss` 顯示預估總時長（建議預設 14 輪共 `45:00`）。設定頁的 +/- 寫的就是這組輔助元件。
- **`script.training_interval_10`**：相容包裝（entity_id 保留給既有語音／Google 場景）。不再內建固定 10 分鐘課表；改為先開啟 HIIT，再呼叫 `script.training_custom`。暫停中則視為繼續。
- **`script.treadmill_remote_start`／`_pause`／`_stop`**：走步機主頁的開始／暫停／停止只呼叫這三支。暫停中按開始會繼續課表；HIIT 開啟且待機則依設定開始課表；HIIT 關閉且待機則手動開始走步機。
- **`script.training_pause`／`script.training_end`**：暫停與繼續切換；中止並停止。
- **安全守護與收尾自動化**：執行中若速度 < 0.1 km/h 持續 3 秒（按停止、拔安全鑰匙）或感測器 unavailable 持續 10 秒，立即中止課表並通知；另含 `automation.training_run_died_guard` 防止執行器異常中止時跑帶未停。課表正常跑完後，階段顯示「已完成」且狀態為 idle 持續 2 分鐘，會把階段收回「待機」（不控制走步機）。
- 新增課表：寫一支定義腳本組成 `segments` 後呼叫 `script.training_run` 即可，執行器不用改。不要再複製 `training_interval_10`，它已經改成 HIIT 包裝。

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

- [docs/2026-11-22-treadmill-remote-hiit.md](docs/2026-11-22-treadmill-remote-hiit.md)：走步機儀表板改為 button-card 主頁＋設定子頁、新增 HIIT 開關與遙控包裝腳本，並把 `script.training_interval_10` 改成相容包裝（時間為 Asia/Taipei）。
- [docs/2026-11-18-custom-interval-test.md](docs/2026-11-18-custom-interval-test.md)：`script.training_custom` 30 分鐘（32 段、31 次換段）實測紀錄：零錯段、零補送、零跳回舊值，驗證 2026-11-17 換段修正完全有效（時間為 Asia/Taipei）。
- [docs/2026-11-17-dd05-training-update.md](docs/2026-11-17-dd05-training-update.md)：修正段落交接速度覆蓋 bug 並實測驗證、改版「間歇 10 分（第二版）」＋ SVG 課表圖、新增 13 個滑桿「自訂課表」、移除 3 分／35 分課表與更新語音設定（時間為 Asia/Taipei）。
- [docs/2026-11-16-dd05-debug-log.md](docs/2026-11-16-dd05-debug-log.md)：控制逾時、課表執行器、`updater_patch.py` 顯示丟包修正，以及當時記錄的段落交接速度問題（已於 2026-11-17 修正）。

## 免責聲明

本專案為非官方的社群作品，**與 BGYM、FitShow、Home Assistant／Nabu Casa 無任何關聯，也未獲其背書或支援**。所有商標屬各自所有者。使用風險自負，你需自行負責器材的安全操作。遠端控制運動器材可能造成傷害；修改整合後，更新時可能失效。

## 授權

本專案自有檔案的授權見 [LICENSE](LICENSE)。`patches/` 內的修正改的是 hassio-ftms，其授權為 Apache-2.0（`patches/LICENSE-hassio-ftms-Apache-2.0`）。

## 致謝

- [dudanov/hassio-ftms](https://github.com/dudanov/hassio-ftms) 與 pyftms（Sergey Dudanov）。
- [custom-cards/button-card](https://github.com/custom-cards/button-card)。
- ESPHome 藍牙 proxy。
