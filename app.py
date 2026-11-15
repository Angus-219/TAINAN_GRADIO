import io
import os
import tempfile
import warnings

import gradio as gr
import pandas as pd
import requests
import urllib3

# ------------------------------------------------------------------
# 設定（皆可用 Render 的環境變數覆蓋）
# ------------------------------------------------------------------
URL = os.getenv(
    "DATA_URL",
    "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c",
)
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() == "true"
ENCODINGS = ["utf-8-sig", "utf-8", "big5", "cp950"]  # 編碼備援
TITLE = os.getenv("APP_TITLE", "臺南市開放資料瀏覽器")

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

_cache = {"df": None}


# ------------------------------------------------------------------
# 資料處理
# ------------------------------------------------------------------
def read_csv_safe(content: bytes) -> pd.DataFrame:
    last_err = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=enc)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise ValueError(f"無法解析 CSV（已嘗試 {ENCODINGS}）：{last_err}")


def get_df(force: bool = False) -> pd.DataFrame:
    """下載並讀取資料；force=True 時重新下載。"""
    if force or _cache["df"] is None:
        response = requests.get(URL, verify=VERIFY_SSL, timeout=30)
        response.raise_for_status()
        raw = read_csv_safe(response.content)
        df = raw.dropna().reset_index(drop=True)
        if df.empty:  # 欄位多時 dropna() 可能全刪，退而求其次只刪整列皆空
            df = raw.dropna(how="all").reset_index(drop=True)
        if df.empty:
            raise ValueError("資料來源沒有任何資料")
        _cache["df"] = df
    return _cache["df"]


def _col_updates(df: pd.DataFrame):
    cols = list(df.columns)
    return gr.update(choices=cols, value=cols), gr.update(choices=cols, value=cols[0])


def init():
    try:
        return _col_updates(get_df())
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"資料載入失敗：{e}")


def reload_data():
    try:
        return _col_updates(get_df(force=True))
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"重新下載失敗：{e}")


def query(keyword, cols):
    """關鍵字搜尋 + 欄位篩選。"""
    try:
        df = get_df()
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"資料載入失敗：{e}")

    result = df
    keyword = (keyword or "").strip()
    if keyword:
        mask = (
            df.astype(str)
            .apply(lambda col: col.str.contains(keyword, case=False, regex=False))
            .any(axis=1)
        )
        result = df[mask]

    valid_cols = [c for c in (cols or []) if c in result.columns]
    note = ""
    if valid_cols:
        result = result[valid_cols]
    else:
        note = "　⚠️ 未勾選欄位，已顯示全部欄位"

    info = (
        f"### 📊 查詢結果\n"
        f"**符合筆數：** {len(result):,} ／ {len(df):,}　|　"
        f"**顯示欄位：** {result.shape[1]} ／ {df.shape[1]}{note}"
    )

    # 每次產生獨立暫存檔，避免多人使用時互相覆蓋
    fd, out_path = tempfile.mkstemp(suffix=".csv", prefix="filtered_")
    os.close(fd)
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    return info, result, out_path


def analyze(col, topn):
    """統計某欄位出現次數最多的前 N 項。"""
    df = get_df()
    if not col or col not in df.columns:
        empty = pd.DataFrame({"類別": [], "數量": []})
        return empty, empty
    vc = df[col].astype(str).value_counts().head(int(topn)).reset_index()
    vc.columns = ["類別", "數量"]
    return vc, vc


# ------------------------------------------------------------------
# 介面
# ------------------------------------------------------------------
theme = gr.themes.Soft(primary_hue="indigo", secondary_hue="sky", neutral_hue="slate")

with gr.Blocks(theme=theme, title=TITLE) as demo:
    gr.Markdown(
        f"""
        # 🏙️ {TITLE}
        搜尋、篩選、視覺化並下載臺南市政府開放資料
        """
    )

    with gr.Tabs():
        with gr.TabItem("🔍 資料查詢"):
            with gr.Row():
                keyword = gr.Textbox(
                    label="關鍵字搜尋",
                    placeholder="輸入任意文字，會搜尋所有欄位…",
                    scale=4,
                )
                search_btn = gr.Button("搜尋", variant="primary", scale=1)
                reload_btn = gr.Button("🔄 重新下載資料", scale=1)

            cols_box = gr.CheckboxGroup(label="顯示欄位", choices=[], value=[])
            info_md = gr.Markdown()
            table = gr.Dataframe(
                label="資料表", interactive=False, wrap=True, max_height=500
            )
            file_out = gr.File(label="⬇️ 下載查詢結果 (CSV)")

        with gr.TabItem("📈 統計圖表"):
            with gr.Row():
                ana_col = gr.Dropdown(label="選擇統計欄位", choices=[])
                topn = gr.Slider(5, 50, value=10, step=1, label="顯示前 N 名")
            plot = gr.BarPlot(
                x="類別",
                y="數量",
                sort="-y",
                title="欄位次數分布",
                height=400,
                label="長條圖",
            )
            stat_table = gr.Dataframe(label="統計明細", interactive=False)

    q_inputs = [keyword, cols_box]
    q_outputs = [info_md, table, file_out]
    a_inputs = [ana_col, topn]
    a_outputs = [plot, stat_table]

    # 載入：初始化選單 → 查詢 → 統計
    demo.load(init, outputs=[cols_box, ana_col]).then(
        query, q_inputs, q_outputs
    ).then(analyze, a_inputs, a_outputs)

    search_btn.click(query, q_inputs, q_outputs)
    keyword.submit(query, q_inputs, q_outputs)
    cols_box.input(query, q_inputs, q_outputs)  # 只有使用者操作才觸發

    reload_btn.click(reload_data, outputs=[cols_box, ana_col]).then(
        query, q_inputs, q_outputs
    ).then(analyze, a_inputs, a_outputs)

    ana_col.input(analyze, a_inputs, a_outputs)
    topn.release(analyze, a_inputs, a_outputs)  # 放開滑鼠才觸發


if __name__ == "__main__":
    # Render 會提供 PORT 環境變數，且必須綁定 0.0.0.0
    port = int(os.getenv("PORT", "7860"))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
