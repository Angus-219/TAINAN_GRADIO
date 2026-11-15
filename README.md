# 🏙️ 臺南市開放資料瀏覽器

以 [Gradio](https://www.gradio.app/) 製作的臺南市政府開放資料瀏覽器，可搜尋、篩選欄位、繪製統計長條圖，並下載查詢結果 CSV。

## 功能

- 🔍 **資料查詢**：關鍵字搜尋所有欄位、自選顯示欄位、下載篩選後 CSV（UTF-8 BOM，Excel 不亂碼）
- 📈 **統計圖表**：任選欄位，顯示出現次數前 N 名長條圖
- 🔄 **重新下載**：一鍵更新最新資料（平常使用記憶體快取）
- 編碼自動備援（utf-8-sig / utf-8 / big5 / cp950）

## 專案結構

```
.
├── app.py             # 主程式
├── requirements.txt   # 套件清單
├── render.yaml        # Render 部署設定（選用）
├── .gitignore
└── README.md
```

## 本機執行

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟瀏覽器前往 http://localhost:7860

## 環境變數（皆為選用）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `DATA_URL` | 臺南市資料集網址 | 換成其他 CSV 資料來源 |
| `VERIFY_SSL` | `false` | 設為 `true` 啟用 SSL 憑證驗證 |
| `APP_TITLE` | 臺南市開放資料瀏覽器 | 頁面標題 |
| `PORT` | `7860` | 監聽埠（Render 會自動提供） |

## 部署到 Render

### 1. 上傳到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<你的帳號>/<repo名稱>.git
git push -u origin main
```

### 2. 在 Render 建立服務

**方式 A：使用 render.yaml（Blueprint）**

1. Render Dashboard → **New** → **Blueprint**
2. 選擇你的 GitHub repo，按 **Apply**

**方式 B：手動建立**

1. Render Dashboard → **New** → **Web Service**
2. 連結 GitHub repo，設定：

| 欄位 | 值 |
|------|----|
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Instance Type | Free（即可） |

3. 在 **Environment** 新增 `PYTHON_VERSION` = `3.11.9`
4. 按 **Create Web Service**，等待建置完成後即可取得網址

### 注意事項

- Render 免費方案閒置約 15 分鐘會休眠，再次訪問需等候約 30–60 秒喚醒。
- 資料快取存在記憶體，服務重啟後會重新下載。
- 臺南市資料網站的 SSL 憑證可能無法通過驗證，所以預設 `VERIFY_SSL=false`；若來源憑證正常，建議設為 `true`。
- 免費方案記憶體有限（512 MB），資料集過大時可能無法載入。

## 資料來源

[臺南市政府資料開放平台](https://data.tainan.gov.tw/)
