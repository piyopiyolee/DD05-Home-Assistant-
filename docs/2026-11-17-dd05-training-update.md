# 2026-11-17 BGYM DD05 課表更新與換段速度修正紀錄

時區皆為 **Asia/Taipei（UTC+8）**。接續 [2026-11-16 測試與修正紀錄](2026-11-16-dd05-debug-log.md)，今天完成「段落交接速度被覆蓋」根因排查與修正、實測驗證換段正常，並將課表與語音指令全面調整為「間歇 10 分（第二版）」與「自訂課表」。

---

## 摘要

| 項目 | 狀態 |
|---|---|
| 段落交接時速度被上一段覆蓋 | **已修（並於 2026-11-17 實測換段正常）**：差異寫入 ＋ 0.5 秒間隔 ＋ 1.5 秒讀回驗證（最多 4 次） |
| 測試課表 3 分（`script.training_test_3`） | 已移除（`/training/test-3` 一併移除） |
| 間歇訓練 35 分（`script.training_interval35_start`） | 已移除（`/training/interval-35` 一併移除） |
| 間歇 10 分（`script.training_interval_10`，第二版） | 已上線：暖身 45s ＋ 5 輪×(快走 60s 4.5/4＋緩和 45s 3.0/0) ＋ 收操 30s，共 600s ＋ SVG 課表圖 |
| 自訂課表（`script.training_custom`） | 已上線：13 個滑桿設定、總時長感測器 `sensor.training_custom_total_mmss`、`/training/custom` 子頁 |
| Assist 中文語音與 Google Home 場景 | 已切換至啟動 `script.training_interval_10`（`TrainingInterval35Start` → `TrainingIntervalStart`） |

---

## 一、換段速度被覆蓋 Bug 根因與修法

### 1. 證據分析（2026-11-16 實測紀錄）

先排除 HA 與 FTMS 整合層因素：
- `custom_components/ftms/number.py` 與 `pyftms` `MachineController` 設定坡度時僅送出單一 `ControlCode.INCLINE`（`0x03`），不會夾帶舊速度，各指令間亦以 `asyncio.Lock` 依序等待 GATT Indication。
- `FtmsNumberEntity._handle_coordinator_update` 僅將機器主動上報的 `UpdateEvent` 更新到 HA 實體狀態，不會反向寫回走步機。

比對 2026-11-16 紀錄中的三個異常時間點與正常換段：
- **22:54:54 變坡度 ramp 第 1 步（`3.0/0 → 3.2/1`）**：`22:54:54.351` `SPEED 3.2` 收到 ACK、`22:54:54.683` `INCLINE 1.0` 收到 ACK、`22:54:54.769` `sensor.treadmill_speed` 曾短暫更新為 `3.2`；但 `22:54:55.352` 機器回報 `sensor.treadmill_inclination = 1.0` 的同一瞬間，`sensor.treadmill_speed` 與 `number.treadmill_speed` 同時跳回 `3.0`（`ctx=` 為空，屬機器上報）。
- **22:55:44 第 1 輪緩和（`3.5/2 → 2.5/0`）**：`22:55:44.823` `SPEED 2.5` ACK（耗時 647 ms）→ `22:55:45.140` `INCLINE 0.0` ACK → `22:55:45.857` 坡度 `0.0` 生效，但 `sensor.treadmill_speed` 全程停在 `3.5`。因數值未離開發報門檻（`updater_patch.py` 僅在改變時發 `UpdateEvent`），`number.treadmill_speed` 才看似維持 `2.5`。
- **22:56:54 收操（`2.5/0 → 2.0/0`）**：該段坡度根本未變（皆為 `0`），腳本仍於 `22:56:54.287` `SPEED 2.0` ACK 後立刻送出 `INCLINE 0.0`；`22:56:54.646` 機器回報 `2.0`，但約 0.7 秒後的 `22:56:55.260` 機器又回報跳回 `2.5`（連帶覆蓋 `number` 與 `sensor`）。

**根因結論（雙重疊加）：**
1. **觸發端**：原 `script.training_run` 只要 `new_target != prev_target`，無論速度或坡度是否真的改變，都在 `number.treadmill_speed` 完成後 **0 ms** 立即送出 `number.treadmill_inclination`。DD05（FitShow FS-BT-F5）在回覆 `SPEED` GATT Indication 後主控板尚未完成速度鎖定，緊接送入 `INCLINE` 容易引發韌體內部狀態衝突，導致新速度被忽略或約 0.7–1.0 秒後被覆蓋回舊值。
2. **執行器端結構缺口**：原執行器寫入後即把 `input_text.training_last_target` 設成 `new_target`，後續每秒迴圈不再檢查 `sensor.treadmill_speed`／`sensor.treadmill_inclination` 讀回值，因此一旦被韌體忽略或延遲跳回，整段都不會補送。

### 2. 修正方式（於 `packages/dd05_training.yaml` 的 `script.training_run` 與 `script.training_pause` 實作）

不需修改 FTMS Python 整合，直接強化執行器：
1. **差異寫入**：僅寫入與前次目標或目前 `sensor` 讀回不符的項目（容差：速度 `0.05 km/h`、坡度四捨五入整數）；例如收操 `3.0/0 → 2.0/0` 時不會再冗餘寫入 `incline=0`。
2. **寫入間隔 0.5 秒**：當速度與坡度皆須寫入時，先送速度、延遲 **500 ms**、再次確認仍處於 `running`（或 `resuming`）且 `sensor.treadmill_speed > 0` 後再送坡度。
3. **1.5 秒後讀回驗證與有上限重送**：沿用 `input_text.training_last_target` 記錄 `<s/i>|<attempts>|<last_write_ts>`（不新增 helper）。於每秒主迴圈距離上次寫入滿 **1.5 秒** 後比對 `sensor` 實際讀回；若不符則**僅針對不符項目**重送，總嘗試次數上限 **4 次**（初次 1 次＋最多重送 3 次），不以長 `delay` 阻塞主計時。
4. **正常結束順序**：先寫入「已完成」、清空 `last_target` 與發送通知，最後才將 `training_state` 切回 `idle`，避免狀態先回 `idle` 但腳本尚未結束的空窗。

**2026-11-17 實測：** 部署後實跑驗證，各段交接與收操速度／坡度皆依課表正常切換與維持，未再出現跳回前段速度的現象。

---

## 二、間歇 10 分（第二版）與課表圖

考量日常訓練時間，正式新增 **`script.training_interval_10`（間歇 10 分）** 並移除原本的「測試課表 3 分」與「間歇訓練 35 分」。

### 段落設計（`rounds_total: 5`，總長剛好 600 秒）

| 時間區間 | 階段 | 輪數 | 長度（秒） | 目標速度 (km/h) | 目標坡度 (%) |
|---|---|---:|---:|---:|---:|
| 00:00 – 00:45 | 暖身 | 0 / 5 | 45 | 3.0 | 0 |
| 00:45 – 01:45 | 第 1 輪：快走 | 1 / 5 | 60 | 4.5 | 4 |
| 01:45 – 02:30 | 第 1 輪：緩和 | 1 / 5 | 45 | 3.0 | 0 |
| 02:30 – 03:30 | 第 2 輪：快走 | 2 / 5 | 60 | 4.5 | 4 |
| 03:30 – 04:15 | 第 2 輪：緩和 | 2 / 5 | 45 | 3.0 | 0 |
| 04:15 – 05:15 | 第 3 輪：快走 | 3 / 5 | 60 | 4.5 | 4 |
| 05:15 – 06:00 | 第 3 輪：緩和 | 3 / 5 | 45 | 3.0 | 0 |
| 06:00 – 07:00 | 第 4 輪：快走 | 4 / 5 | 60 | 4.5 | 4 |
| 07:00 – 07:45 | 第 4 輪：緩和 | 4 / 5 | 45 | 3.0 | 0 |
| 07:45 – 08:45 | 第 5 輪：快走 | 5 / 5 | 60 | 4.5 | 4 |
| 08:45 – 09:30 | 第 5 輪：緩和 | 5 / 5 | 45 | 3.0 | 0 |
| 09:30 – 10:00 | 收操 | 5 / 5 | 30 | 2.0 | 0 |

### 課表圖與儀表板簡化
- 新增靜態向量圖 `homeassistant/www/training/interval10_v2.svg`（部署至 `/config/www/training/interval10_v2.svg`，HA 以 `/local/training/interval10_v2.svg` 存取）：深色背景、`viewBox="0 0 800 440"`、橫軸 `0:00–10:00` 每分鐘刻度、雙 Y 軸（左速度 `0–5 km/h`、右坡度 `0–5 %`）、兩條階梯線與段落淡色區分。
- `/training/interval-10` 子頁移除長篇說明與文字時間軸表格，改為內建 `picture` 卡片（`/local/training/interval10_v2.svg?v=2`）加上單行簡要說明。

---

## 三、自訂課表（`script.training_custom`）

讓使用者可在 `/training/custom` 子頁直接用滑桿調整四個階段與輪數，按下開始後才讀取快照傳給 `script.training_run`（執行中修改設定不會影響正在進行的訓練；暫停時按開始一樣視同繼續）。

### 1. 新增實體（13 個 `input_number` 滑桿 ＋ 1 個總時長感測器）

所有 `input_number.training_custom_*` 皆採 **`mode: slider`**，且**刻意不設 `initial:`**，確保 `input_number.reload` 或 HA 重啟後會透過 `restore_state` 保留使用者上次調整好的數值（不會被覆蓋回預設值）。

| 實體 `entity_id` | 範圍 (`min`–`max`, `step`) | 單位 | 建議預設值 |
|---|---|---|---:|
| `input_number.training_custom_rounds` | 5–30, step 1 | 輪 | `15` |
| `input_number.training_custom_warmup_dur` | 30–120, step 15 | s | `60` |
| `input_number.training_custom_warmup_speed` | 2.0–6.0, step 0.1 | km/h | `3.0` |
| `input_number.training_custom_warmup_incline` | 0–15, step 1 | % | `0` |
| `input_number.training_custom_fast_dur` | 30–120, step 15 | s | `60` |
| `input_number.training_custom_fast_speed` | 2.0–6.0, step 0.1 | km/h | `4.5` |
| `input_number.training_custom_fast_incline` | 0–15, step 1 | % | `4` |
| `input_number.training_custom_rest_dur` | 30–120, step 15 | s | `45` |
| `input_number.training_custom_rest_speed` | 2.0–6.0, step 0.1 | km/h | `3.0` |
| `input_number.training_custom_rest_incline` | 0–15, step 1 | % | `0` |
| `input_number.training_custom_cooldown_dur` | 30–120, step 15 | s | `60` |
| `input_number.training_custom_cooldown_speed` | 2.0–6.0, step 0.1 | km/h | `2.0` |
| `input_number.training_custom_cooldown_incline` | 0–15, step 1 | % | `0` |

- `sensor.training_custom_total_mmss`：即時計算自訂課表總時長（`mm:ss`）。依建議預設值計算：`60 + 15 × (60 + 45) + 60 = 1695 秒`（`28:15`）。
- **首次部署設定預設值**：因未設 `initial:`，初次部署並載入後，請協調者／使用者透過開發者工具呼叫 `input_number.set_value` 寫入上述建議預設值一次，之後重載與重啟即永久保留。

> **2026-11-18 起預設改為：** `rounds: 14`、暖身 `90s (3.0/0)`、快走 `120s (4.5/5)`、緩和 `60s (3.0/0)`、收操 `90s (3.0/0)`，總長 `90 + 14 × (120 + 60) + 90 = 2700` 秒（`45:00`）。

---

## 四、語音與 Google 助理調整（以及 Reload 說明）

- **Assist 中文句子（`homeassistant/custom_sentences/zh-TW/training.yaml`）**與 **`intent_script`**：將 `TrainingInterval35Start` 改名為 `TrainingIntervalStart`，觸發動作改為 `script.turn_on` `script.training_interval_10`，保留全部原有啟動句型（`[開始]間歇訓練`、`間歇訓練開始`、`開始訓練[課表]`、`訓練開始`）。
- **Google 助理（`homeassistant/configuration-snippets/google_assistant.yaml`）**：`entity_config` 中的 `script.training_interval35_start` 改為 `script.training_interval_10`，保留 `expose: true`、名稱「間歇訓練開始」與既有別名。
- **部署後生效方式**：
  - `intent_script` 與 Assist 自訂句子支援動態重載（`intent_script.reload`、`conversation.reload`）。
  - `google_assistant` 的 `entity_config` 變更建議**重啟 Home Assistant** 後再執行 `google_assistant.request_sync`（同步更新 Google Home 端場景對應的實體）；本次同時有 `/config/packages/` 實體增刪與 `www/` 目錄掛載需求，直接重啟 HA 一次最穩妥。

---

## 五、已知限制與實務提醒

- **HA 重啟後 DD05 偶發不回應控制點**：與 [2026-11-16 紀錄](2026-11-16-dd05-debug-log.md)相同，HA 重啟後若出現藍牙看似已連線、但送出開始／速度指令等滿 8 秒逾時且跑帶無反應的情況，請將 **DD05 斷電重開**，並在 HA 重新載入藍牙 proxy／FTMS 整合後再啟動課表。
- **快速連續操作**：`training_pause`／`training_end` 的 15 秒等待速度歸零視窗為既有設計限制，暫未更動。
