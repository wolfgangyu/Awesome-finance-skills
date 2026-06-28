# 新聞來源參考

## RSS Feed 來源

| Source ID | 名稱 | 語言 | 說明 |
|:----------|:-----|:-----|:-----|
| `cna_finance` | 中央社財經 | zh-TW | 台灣財經、金融政策、股市新聞 |
| `cna_tech` | 中央社科技 | zh-TW | 台灣科技產業、半導體、AI 新聞 |
| `nhk_economy` | NHK 經濟 | ja | 日本經濟、外匯、日股新聞 |
| `bloomberg` | Bloomberg Markets | en | 美股、全球市場新聞 |
| `investing_reuters` | Reuters (via Investing.com) | en | 路透社財經新聞（透過 Investing.com RSS 轉發） |

## Polymarket

- **Base URL**: `https://gamma-api.polymarket.com`
- **資料**: 預測市場（例如：Fed 會不會降息？）
- **用法**: 使用 `get_active_markets` 取得交易量最高的熱門市場
