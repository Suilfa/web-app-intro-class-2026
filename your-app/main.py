"""
TODOアプリ バックエンド - 完成版
第8回: セキュリティの基礎 & 総仕上げ
"""

import sqlite3  # Python標準のデータベース（SQLite）を使うためのライブラリ
import uvicorn  # FastAPIアプリを動かすためのWebサーバー

from fastapi import FastAPI, HTTPException  # Webアプリ本体とエラー応答用
from fastapi.middleware.cors import CORSMiddleware  # ブラウザからのアクセスを許可する設定
from fastapi.staticfiles import StaticFiles  # HTML/CSS/JSなどのファイルを配信する機能
from pydantic import BaseModel, Field  # 受け取るデータの形をチェックする道具

# --- FastAPIアプリ ---
# このappが、Webアプリ全体の本体になる
app = FastAPI(title="ANIME WATCH App")

# CORS設定: 別のアドレスで動くフロント（ブラウザの画面）からの通信を許可する
# allow_origins=["*"] は「どこからのアクセスでもOK」という意味（学習用の設定）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- データベース設定 ---
# データを保存するファイルの名前。アプリと同じフォルダに todo.db が作られる
DATABASE = "animes.db"


def init_db():
    """データベースとテーブルを初期化する"""
    conn = sqlite3.connect(DATABASE)  # データベースに接続する
    cursor = conn.cursor()  # SQLを実行する係（カーソル）を用意する
    # animes テーブルがまだ無ければ作る（IF NOT EXISTS）
    #   id    : 自動で増える番号（主キー）
    #   title : ANIMEのタイトル名（空はNG）
    #   watched  : 鑑賞したかどうか（0=未鑑賞, 1=鑑賞済）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            watched INTEGER DEFAULT 0
        )
    """)
    conn.commit()  # 変更を確定して保存する
    conn.close()  # 接続を閉じる


# --- Pydanticモデル ---
# APIが受け取るデータの「形」を決めるクラス。
# 形に合わないデータが送られてきたら、FastAPIが自動でエラーを返してくれる。


class AnimeCreate(BaseModel):
    # 新しいANIMESを作るときに受け取るデータ
    # title は1文字以上100文字以下の文字列でなければならない
    title: str = Field(min_length=1, max_length=100)


class AnimeUpdate(BaseModel):
    # ANIME WATCHEDを更新するときに受け取るデータ
    # watched は True / False（鑑賞したかどうか）
    watched: bool


# --- APIエンドポイント ---
# @app.get / @app.post などの飾り（デコレータ）で、
# 「どのURLに、どの種類のリクエストが来たら、この関数を動かすか」を決める。


@app.get("/animes")  # GET /animes にアクセスされたら実行
def get_animes():
    """ANIME一覧を取得する"""
    conn = sqlite3.connect(DATABASE)  # 接続する
    cursor = conn.cursor()

    # animes テーブルの全データを id 順に取り出す
    cursor.execute("SELECT id, title, watched FROM animes ORDER BY id")
    animes = cursor.fetchall()  # 取り出した全行をリストで受け取る

    conn.close()  # 接続を閉じる
    # 1行は (id, title, watched) の順のタプルなので、番号で取り出す。
    # 取り出したデータを、ブラウザに返しやすい辞書のリストに作り変える。
    return [
        {"id": anime[0], "title": anime[1], "watched": bool(anime[2])}
        for anime in animes
    ]


@app.post("/animes", status_code=201)  # POST /animes で新規作成（201=作成成功）
def create_anime(anime: AnimeCreate):
    """新しいANIMESを作成する"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 新しいTODOを1件追加する（watched は 0=未鑑賞で登録）
    # ? を使うことで、危険な文字列が混ざってもSQLが壊れない（SQLインジェクション対策）
    cursor.execute(
        "INSERT INTO animes (title, watched) VALUES (?, 0)",
        (anime.title,),
    )
    conn.commit()  # 追加を確定する
    anime_id = cursor.lastrowid  # たった今追加した行の id を取得する

    conn.close()
    return {"id": anime_id, "title": anime.title, "watched": False}


# PUT /animes/5 のように、URLの {anime_id} の部分が引数 anime_id に入る
@app.put("/animes/{anime_id}")
def update_anime(anime_id: int, anime: AnimeUpdate):
    """TODOの完了状態を更新する"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # まず、その id のANIMEが本当にあるか確認する
    cursor.execute("SELECT title FROM animes WHERE id = ?", (anime_id,))
    existing = cursor.fetchone()  # 1件だけ取り出す。無ければ None が返る
    if existing is None:
        conn.close()  # 見つからないときも接続は閉じてから終わる
        # 404エラー（見つからない）を返して処理を中断する
        raise HTTPException(status_code=404, detail="ANIME not found")

    # watched（完了状態）を更新する。True/False は int() で 1/0 に変換して保存
    cursor.execute(
        "UPDATE todos SET done = ? WHERE id = ?",
        (int(anime.watched), anime_id),
    )
    conn.commit()  # 更新を確定する

    conn.close()
    # existing は (title,) のタプルなので、先頭を取り出す
    return {"id": anime_id, "title": existing[0], "watched": anime.watched}


@app.delete("/animes/{anime_id}")  # DELETE /animes/5 で id=5 のANIMEを削除
def delete_anime(anime_id: int):
    """ANIMEを削除する"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 削除する前に、その id のTODOが存在するか確認する
    cursor.execute("SELECT id FROM animes WHERE id = ?", (anime_id,))
    existing = cursor.fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404, detail="ANIME not found")

    cursor.execute("DELETE FROM animes WHERE id = ?", (anime_id,))  # 削除する
    conn.commit()  # 削除を確定する

    conn.close()
    return {"message": "ANIME deleted", "id": anime_id}


# --- 静的ファイル配信 ---
# static フォルダの中身（index.html など）をそのままブラウザに表示できるようにする
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# --- アプリ起動時にDBを初期化 ---
# プログラムが読み込まれたタイミングで、テーブルが無ければ作っておく
init_db()

# このファイルを直接 `python main.py` で実行したときだけ、サーバーを起動する
if __name__ == "__main__":
    # host="0.0.0.0" で外部からのアクセスも受け付ける。ポート8000で待ち受ける
    uvicorn.run(app, host="0.0.0.0", port=8000)
