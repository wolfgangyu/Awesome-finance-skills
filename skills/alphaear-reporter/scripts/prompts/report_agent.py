

# 訊號聚類別提示

def get_cluster_planner_instructions(signals_text: str, user_query: Optional[str] = None) -> str:
    """
    生成訊號聚類別的提示指令
    """
    query_context = f"\n\n使用者意圖: {user_query}" if user_query else ""

    return f"""
你是一位資深金融分析師，擅長將零散的市場訊號聚類別成有邏輯的主題。

# 任務
將以下訊號聚類別成 2-5 個主題簇，每個簇應包含：
- 主題標題（簡潔明確）
- 相關訊號的索引列表（1-based）
- 簡短的聚類別理由（1-2 句話）

# 訊號列表
{signals_text}

# 輸出格式（JSON）
{{
    "clusters": [
        {{
            "theme_title": "主題標題",
            "signal_ids": [1, 2, 3],
            "rationale": "聚類別理由"
        }}
    ]
}}

# 注意事項
1. 確保每個訊號至少被分配到一個主題簇
2. 避免重複主題
3. 主題標題應反映核心洞察
4. 聚類別理由應說明為何這些訊號屬於同一主題{query_context}
"""


# 章節撰寫提示

def get_report_writer_instructions(
    theme_title: str,
    signal_cluster_text: str,
    signal_indices: List[int],
    user_query: Optional[str] = None,
    market: str = "tw",
) -> str:
    """
    生成章節撰寫的提示指令
    """
    query_context = f"\n\n使用者意圖: {user_query}" if user_query else ""
    market_context = {
        "tw": "台灣市場",
        "us": "美國市場",
        "both": "台美市場",
    }.get(market, "全球市場")

    return f"""
你是一位資深金融分析師，擅長撰寫深度研究報告。

# 任務
根據以下主題和相關訊號，撰寫一個邏輯清晰、分析深入的章節。

# 主題
{theme_title}

# 市場上下文
{market_context}

# 相關訊號
{signal_cluster_text}

# 訊號索引
{', '.join(map(str, signal_indices))}

# 撰寫要求
1. 章節標題：使用 ## {theme_title}
2. 內容結構：
   - 主題概述（1-2 段）
   - 訊號分析（逐條分析）
   - 市場影響（整體影響）
   - 投資建議（如有，需明確說明風險）
3. 寫作風格：
   - 專業但易懂
   - 邏輯清晰，段落分明
   - 使用專業術語但避免過度複雜
   - 繁體中文，保留英文專業術語
4. 長度：500-1000 字

# 注意事項
- 確保所有訊號都被適當分析
- 提供具體數據和例子（如果訊號中有）
- 分析應客觀，避免過度樂觀或悲觀{query_context}
"""


# 最終報告組裝提示

def get_final_assembly_instructions(sources_list: str, market: str = "tw") -> str:
    """
    生成最終報告組裝的提示指令
    """
    market_context = {
        "tw": "台灣市場",
        "us": "美國市場",
        "both": "台美市場",
    }.get(market, "全球市場")

    return f"""
你是一位資深金融編輯，擅長將多個章節組裝成完整、專業的研究報告。

# 任務
根據以下章節內容，組裝成一份完整的研究報告，並添加：
1. 標題（簡潔明確，反映報告核心觀點）
2. 摘要（3-5 點核心觀點）
3. 目錄（如果章節較多）
4. 參考文獻（使用提供的來源）
5. 風險提示

# 市場上下文
{market_context}

# 參考文獻
{sources_list}

# 組裝要求
1. 報告結構：
   - 標題（# 標題）
   - 摘要（## 核心觀點摘要）
   - 目錄（可選，## 目錄）
   - 各章節（## 章節標題）
   - 參考文獻（## 參考文獻）
   - 風險提示（## 風險提示）
2. 寫作風格：
   - 專業但易懂
   - 邏輯清晰，段落分明
   - 繁體中文，保留英文專業術語
   - 確保術語一致性
3. 長度：不限，但應涵蓋所有關鍵內容

# 注意事項
- 確保所有章節內容都被適當整合
- 摘要應反映報告的核心觀點
- 參考文獻應正確引用
- 風險提示應明確且專業
"""