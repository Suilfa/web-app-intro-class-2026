/**
 * サイゼリヤガチャ JavaScript
 *
 * 【全体の流れ】
 *  1. ページが開かれる → loadCollection() で図鑑を取得して表示
 *  2. 「ガチャを引く！」ボタン → drawGacha() がサーバーにPOST
 *  3. 結果を演出つきで表示し、図鑑を取り直して最新にする
 */

// ============================================================
// ガチャ
// ============================================================

/**
 * ガチャを1回引く
 */
async function drawGacha() {
  const button = document.getElementById("gacha-button");
  const resultDiv = document.getElementById("gacha-result");

  // 連打できないようにボタンを無効化して、演出の文言に変える
  button.disabled = true;
  button.textContent = "ガチャ回転中…🎰";
  resultDiv.style.display = "none";

  try {
    // サーバーに「ガチャを引く」リクエストを送る
    const response = await fetch("/gacha", { method: "POST" });

    if (!response.ok) {
      const error = await response.json();
      showError(error.detail || "ガチャに失敗しました");
      return;
    }

    const item = await response.json();

    // ちょっとタメてから結果を表示する（ドキドキ演出）
    await sleep(800);
    renderResult(item);

    // 図鑑を取り直して、いまの結果を反映する
    await loadCollection();
  } catch (error) {
    showError("通信エラーが発生しました");
  } finally {
    // 成功でも失敗でも、最後に必ずボタンを元に戻す
    button.disabled = false;
    button.textContent = "ガチャを引く！";
  }
}

/**
 * ガチャ結果を表示する（XSS対策: createElement + textContent）
 */
function renderResult(item) {
  const resultDiv = document.getElementById("gacha-result");
  resultDiv.innerHTML = ""; // 前回の結果を消す

  // レアリティに応じた見た目のクラスをつける（rarity-ssr など）
  resultDiv.className = "gacha-result rarity-" + item.rarity.toLowerCase();

  // レアリティ表示（例: ★★★★ SSR）
  const rarityDiv = document.createElement("div");
  rarityDiv.className = "result-rarity";
  const stars = { N: "★", R: "★★", SR: "★★★", SSR: "★★★★" };
  rarityDiv.textContent = stars[item.rarity] + " " + item.rarity;

  // メニューの絵文字（大きく表示）
  const emojiDiv = document.createElement("div");
  emojiDiv.className = "result-emoji";
  emojiDiv.textContent = item.emoji;

  // メニュー名
  const nameDiv = document.createElement("div");
  nameDiv.className = "result-name";
  nameDiv.textContent = item.name;

  // 値段
  const priceDiv = document.createElement("div");
  priceDiv.className = "result-price";
  priceDiv.textContent = item.price + "円";

  resultDiv.appendChild(rarityDiv);
  resultDiv.appendChild(emojiDiv);
  resultDiv.appendChild(nameDiv);
  resultDiv.appendChild(priceDiv);

  // 初ゲットなら NEW! バッジをつける
  if (item.is_new) {
    const newBadge = document.createElement("div");
    newBadge.className = "result-new";
    newBadge.textContent = "NEW!";
    resultDiv.appendChild(newBadge);
  }

  resultDiv.style.display = "block";
}

// ============================================================
// コレクション（図鑑）
// ============================================================

/**
 * 図鑑を取得して表示する
 */
async function loadCollection() {
  try {
    const response = await fetch("/collection");

    if (!response.ok) {
      const error = await response.json();
      showError(error.detail || "図鑑の取得に失敗しました");
      return;
    }

    const items = await response.json();
    renderCollection(items);
  } catch (error) {
    showError("通信エラーが発生しました");
  }
}

/**
 * 図鑑を描画する。未ゲットのメニューは「？？？」で隠す
 */
function renderCollection(items) {
  const list = document.getElementById("collection-list");
  list.innerHTML = "";

  items.forEach((item) => {
    const owned = item.count > 0; // 1回でも引いていればゲット済み

    const li = document.createElement("li");
    li.className =
      "collection-item rarity-" +
      item.rarity.toLowerCase() +
      (owned ? "" : " locked");

    // 絵文字（未ゲットは❓）
    const emojiDiv = document.createElement("div");
    emojiDiv.className = "item-emoji";
    emojiDiv.textContent = owned ? item.emoji : "❓";

    // 名前（未ゲットは？？？）
    const nameDiv = document.createElement("div");
    nameDiv.className = "item-name";
    nameDiv.textContent = owned ? item.name : "？？？";

    // レアリティと所持数
    const metaDiv = document.createElement("div");
    metaDiv.className = "item-meta";
    metaDiv.textContent = owned
      ? item.rarity + " × " + item.count
      : item.rarity;

    li.appendChild(emojiDiv);
    li.appendChild(nameDiv);
    li.appendChild(metaDiv);
    list.appendChild(li);
  });

  // コンプリート状況（例: 5 / 20）を見出しの横に表示する
  const ownedCount = items.filter((item) => item.count > 0).length;
  const progress = document.getElementById("collection-progress");
  progress.textContent = ownedCount + " / " + items.length;
}

// ============================================================
// 便利関数
// ============================================================

// 指定したミリ秒だけ待つ（演出用）
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// エラーメッセージを画面に表示する（5秒後に自動で消える）
function showError(message) {
  const errorDiv = document.getElementById("error-message");
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
  setTimeout(() => {
    errorDiv.style.display = "none";
  }, 5000);
}

// ============================================================
// イベントリスナー
// ============================================================

document.getElementById("gacha-button").addEventListener("click", drawGacha);

// ページ読み込み時に図鑑を表示する（ここがスタート地点）
loadCollection();
