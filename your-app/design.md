# 私のアプリ設計

## 1. 題材（一文で）
見たいと思っているアニメを鑑賞済み・未鑑賞かを記録するアプリ

## 2. テーブル設計
テーブル名: animes
カラム: id / title（アニメ名）/ watched（鑑賞済 0 or 1）

## 3. 変換表
todos → animes, done → watched, todo.db → animes.db, /todos → /animes
