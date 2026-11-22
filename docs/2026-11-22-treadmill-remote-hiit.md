# 2026-11-22 走步機儀表板改版與 HIIT 課表調整紀錄

時區皆為 **Asia/Taipei（UTC+8）**。接續 [2026-11-18 自訂課表實測](2026-11-18-custom-interval-test.md)，這次把走步機遙控與課表設定整合成同一份手機儀表板，並把原本固定的「間歇 10 分」改成依設定頁參數執行的 HIIT。

截圖見 [`docs/images/remote.png`](images/remote.png)（主頁）與 [`docs/images/settings.png`](images/settings.png)（設定頁）。

---

## 摘要

| 項目 | 狀態 |
|---|---|
| 走步機儀表板（`dashboards/treadmill_remote.yaml`，HA 路徑 `/treadmill-remote`） | **已改版**：主頁（`remote`）含速度／坡度 +/-、時間與距離、課表狀態、開始／暫停／停止、HIIT 開關與設定入口；設定子頁（`custom`）用 +/- 調整暖身／快走／緩和／收操與輪數。需要 HACS `button-card`（實測 7.0.1）。 |
| `input_boolean.training_hiit` | 新增。主頁 HIIT 開關只切這個 helper，不會自己啟動課表。刻意不設 `initial:`，重啟後還原上次開／關。 |
| `script.treadmill_remote_start`／`_pause`／`_stop` | 新增。主頁三顆按鈕只呼叫這三支：暫停中按開始會繼續課表；HIIT 開啟且待機則依設定開始課表；HIIT 關閉且待機則手動開始走步機。 |
| `script.training_custom` | 仍依 `input_number.training_custom_*` 快照組成課表，交由 `script.training_run`；課表名稱改為「HIIT」。 |
| `script.training_interval_10` | **不再內建固定 10 分鐘課表**。改成相容包裝：先開啟 HIIT，再呼叫 `script.training_custom`。entity_id 保留，讓既有 Assist／Google 場景「間歇訓練開始」繼續可用。 |
| Assist 句子 | 舊的「間歇訓練開始／暫停／結束」全部保留，另加 HIIT 同義句（含有空格／無空格兩種寫法）。 |
| `automation.training_clear_completed_phase` | 新增。階段顯示「已完成」且狀態為 idle 持續 2 分鐘後，把階段收回「待機」、課表名稱收回「未開始」。不控制走步機。 |
| Training 儀表板（`dashboards/training.yaml`） | **未改**（與 2026-11-17 相同）。其「間歇 10 分」開始鈕仍呼叫 `script.training_interval_10`，因此現在會改跑設定頁的 HIIT，而不是舊的固定 10 分鐘課表。主要操作已改到走步機頁。 |

通用執行器 `script.training_run`、安全守護自動化、遙控加減速度／坡度腳本（`dd05_treadmill_remote.yaml`）這次沒有改行為。

---

## 使用方式（走步機頁）

1. 站上走步機並夾好安全鑰匙。
2. 若要跑課表：先到設定頁用 +/- 調好暖身／快走／緩和／收操與輪數（建議預設 14 輪、總長 `45:00`）。+/- 會立刻寫入輔助元件；「儲存」只是返回主頁，不會另外再存一次。
3. 在主頁打開 **HIIT**，再按 **開始**。關閉 HIIT 時，開始／暫停／停止是手動控制走步機，不會啟動課表。
4. 訓練進行中可暫停、繼續或停止；安全守護（跑帶停止、斷線、執行器異常結束）行為與先前相同。

語音「開始走」仍是手動開始走步機（`script.treadmill_start`），不會開啟 HIIT。「間歇訓練開始」或「開始 HIIT」才會開啟 HIIT 並依目前設定開始課表。
