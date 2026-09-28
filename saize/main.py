"""
サイゼリヤガチャ バックエンド

技術スタック: FastAPI + SQLite（TODOアプリと同じ構成）
機能:
  - POST /gacha      : ガチャを1回引いて、当たったメニューを返す
  - GET  /collection : いままでにゲットしたメニューの一覧（図鑑）を返す
"""

import random  # ガチャの抽選に使う
import sqlite3  # Python標準のデータベース（SQLite）
import uvicorn  # FastAPIアプリを動かすためのWebサーバー

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="サイゼリヤガチャ")

# CORS設定（学習用: どこからのアクセスでもOK）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- データベース設定 ---
DATABASE = "gacha.db"

# --- メニューのマスターデータ ---
# ガチャの景品になるサイゼリヤのメニュー。
# rarity: N(ノーマル) < R(レア) < SR(スーパーレア) < SSR(激レア)
MENU = [
    # SSR
    {"id": 1, "name": "ミラノ風ドリア", "price": 300, "rarity": "SSR", "emoji": "🧀"},
    {"id": 2, "name": "アロスティチーニ（ラムの串焼き）", "price": 400, "rarity": "SSR", "emoji": "🍢"},
    # SR
    {"id": 3, "name": "エスカルゴのオーブン焼き", "price": 400, "rarity": "SR", "emoji": "🐌"},
    {"id": 4, "name": "辛味チキン", "price": 300, "rarity": "SR", "emoji": "🍗"},
    {"id": 5, "name": "マルゲリータピザ", "price": 400, "rarity": "SR", "emoji": "🍕"},
    {"id": 6, "name": "イタリアンプリン", "price": 300, "rarity": "SR", "emoji": "🍮"},
    # R
    {"id": 7, "name": "ハンバーグステーキ", "price": 500, "rarity": "R", "emoji": "🥩"},
    {"id": 8, "name": "小エビのサラダ", "price": 350, "rarity": "R", "emoji": "🦐"},
    {"id": 9, "name": "ミートソースボロニア風", "price": 400, "rarity": "R", "emoji": "🍝"},
    {"id": 10, "name": "たらこスパゲッティ", "price": 400, "rarity": "R", "emoji": "🍝"},
    {"id": 11, "name": "ティラミス", "price": 300, "rarity": "R", "emoji": "🍰"},
    {"id": 12, "name": "真イカのパプリカソース", "price": 350, "rarity": "R", "emoji": "🦑"},
    # N
    {"id": 13, "name": "ペペロンチーノ", "price": 300, "rarity": "N", "emoji": "🍝"},
    {"id": 14, "name": "プチフォッカ", "price": 150, "rarity": "N", "emoji": "🍞"},
    {"id": 15, "name": "ドリンクバー", "price": 300, "rarity": "N", "emoji": "🥤"},
    {"id": 16, "name": "ほうれん草のソテー", "price": 200, "rarity": "N", "emoji": "🥬"},
    {"id": 17, "name": "コーンクリームスープ", "price": 150, "rarity": "N", "emoji": "🥣"},
    {"id": 18, "name": "半熟卵", "price": 100, "rarity": "N", "emoji": "🥚"},
    {"id": 19, "name": "柔らか青豆の温サラダ", "price": 200, "rarity": "N", "emoji": "🫛"},
    {"id": 20, "name": "ライス", "price": 150, "rarity": "N", "emoji": "🍚"},
]

# レアリティごとの排出率（%）。合計100になるようにする
RARITY_RATES = {"N": 60, "R": 30, "SR": 8, "SSR": 2}


def init_db():
    """データベースとテーブルを初期化する"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # ガチャで引いた履歴を1行ずつ保存するテーブル
    #   item_id : 当たったメニューのid（MENUのidに対応）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def find_item(item_id):
    """idからメニューを探す"""
    for item in MENU:
        if item["id"] == item_id:
            return item
    return None


@app.post("/gacha", status_code=201)
def draw_gacha():
    """ガチャを1回引く"""
    # 1. まずレアリティを排出率にしたがって抽選する
    #    random.choices は weights の重みつきで1つ選んでくれる
    rarities = list(RARITY_RATES.keys())
    weights = list(RARITY_RATES.values())
    rarity = random.choices(rarities, weights=weights)[0]

    # 2. そのレアリティのメニューの中から1つ選ぶ
    candidates = [item for item in MENU if item["rarity"] == rarity]
    item = random.choice(candidates)

    # 3. 引いた結果をデータベースに保存する
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # このメニューを引くのが初めてかどうか（NEW表示に使う）
    cursor.execute(
        "SELECT COUNT(*) FROM collection WHERE item_id = ?",
        (item["id"],),
    )
    is_new = cursor.fetchone()[0] == 0

    cursor.execute(
        "INSERT INTO collection (item_id) VALUES (?)",
        (item["id"],),
    )
    conn.commit()
    conn.close()

    # 当たったメニューの情報に「初ゲットかどうか」を足して返す
    return {**item, "is_new": is_new}


@app.get("/collection")
def get_collection():
    """メニュー図鑑を返す（全メニュー + それぞれ何回ゲットしたか）"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # item_id ごとに何回引いたかを数える
    cursor.execute(
        "SELECT item_id, COUNT(*) FROM collection GROUP BY item_id"
    )
    counts = dict(cursor.fetchall())  # {item_id: 回数} の辞書にする
    conn.close()

    # 全メニューに count（ゲット数）を付けて返す。0なら未ゲット
    return [{**item, "count": counts.get(item["id"], 0)} for item in MENU]


# --- 静的ファイル配信 ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# --- アプリ起動時にDBを初期化 ---
init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
