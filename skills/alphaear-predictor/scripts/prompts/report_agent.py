# src/prompts/report_agent.py
from datetime import datetime
from typing import Optional
from .isq_prompt_generator import generate_isq_prompt_section

def get_report_planner_base_instructions() -> str:
    """生成报告策划员 (Planner) 的基礎系统指令"""
    return """你是一名资深的金融研报主编。你的任务是规划报告的结构，將零散的訊號聚類別成有逻辑的主题。
你拥有 RAG 搜尋工具，可以检索已生成的章节内容以确保逻辑连贯性。
在规划時，应重点关注訊號之间的关联性、产业链的完整性以及使用者特定的关注点。"""

def get_report_writer_base_instructions() -> str:
    """生成报告撰写员 (Writer) 的基礎系统指令"""
    return """你是一名资深金融分析师。你的任务是根据策划员提供的訊號簇撰写深度研报章节。
你应当运用专业的金融知识，將訊號转化為深刻的洞察。
注意：你没有外部搜尋工具，你的分析必须基于提供给你的訊號内容和行情資料。"""

def get_report_editor_base_instructions() -> str:
    """生成报告编辑 (Editor) 的基礎系统指令"""
    return """你是一名严谨的金融研报编辑。你的任务是审核和润色撰写员生成的章节。
你拥有 RAG 搜尋工具，可以检索其他章节的内容，以消除重复、修正逻辑冲突并确保术语一致性。
你应当确保报告符合专业的金融写作规范，且标题层级正确。"""

# 1. 策划阶段 (Structural Planning)
def format_signal_for_report(signal: any, index: int, cite_keys: Optional[list] = None) -> str:
    """格式化单个訊號供研报生成使用"""
    # 这里的逻辑从 ReportAgent._format_signal_input 迁移过来
    from ..schema.models import InvestmentSignal

    if isinstance(signal, dict):
        try:
            sig_obj = InvestmentSignal(**signal)
        except:
            return f"--- 訊號 [{index}] ---\n标题: {signal.get('title')}\n内容: {signal.get('content', '')[:500]}"
    else:
        sig_obj = signal

    chain_str = " -> ".join([f"{n.node_name}({n.impact_type})" for n in sig_obj.transmission_chain])

    text = f"--- 訊號 [{index}] ---\n"
    text += f"标题: {sig_obj.title}\n"
    text += f"逻辑摘要: {sig_obj.summary}\n"
    text += f"传导链条: {chain_str}\n"
    text += f"ISQ 評分: 情绪({sig_obj.sentiment_score}), 确定性({sig_obj.confidence}), 强度({sig_obj.intensity})\n"
    text += f"预期博弈: 時窗({sig_obj.expected_horizon}), 预期差({sig_obj.price_in_status})\n"

    tickers = ", ".join([f"{t.get('name')}({t.get('ticker')})" for t in sig_obj.impact_tickers])
    if tickers:
        text += f"受影響标的: {tickers}\n"

    # Stable bibliography-style citation keys (LaTeX/BibTeX-like)
    if cite_keys:
        joined = " ".join([f"[@{k}]" for k in cite_keys if k])
        if joined:
            text += f"引用: {joined}\n"

    return text

def get_cluster_planner_instructions(signals_text: str, user_query: str = None) -> str:
    """生成訊號聚類別指令 - 將零散訊號组织成逻辑主题"""
    query_context = f"使用者重点关注：{user_query}" if user_query else ""
    return f"""你是一位资深的金融研报主编。你的任务是將以下零散的金融訊號聚類別成 3-5 个核心逻辑主题，以便撰写一份结构清晰的研报。

    {query_context}

    ### 輸入訊號列表
    {signals_text}

    ### 聚類別要求
    1. **主题聚合**: 將相关性强的訊號归為一组（例如：都涉及"AI晶片代工"或"某产业链上下游"）。
    2. **叙事逻辑**: 只需要生成主题名称和套件含的訊號 ID。
    3. **控制数量**: 將所有訊號归類別到 3-5 个主要主题中，不要遗漏。

    ### 輸出格式 (JSON)
    请仅輸出以下 JSON 格式，不要套件含 Markdown 标记：
    {{
        "clusters": [
            {{
                "theme_title": "主题名称（如：AI晶片代工需求爆發引發的產業鏈重構）",
                "signal_ids": [1, 3, 5],
                "rationale": "这些訊號都指向AI伺服器需求爆發帶動晶圓代工產能利用率攀升..."
            }},
            ...
        ]
    }}
    """

def get_report_planner_instructions(toc: str, signal_count: int, user_query: str = None) -> str:
    """生成报告规划指令 - 重点在于逻辑关联与分歧识别"""
    # ... (原有逻辑保持不变，但实际在新的聚類別流程后这个可能作為备用或二次优化)
    query_context = f"使用者重点关注：{user_query}" if user_query else ""
    return f"""你是一位资深的金融研报主编。你的任务是根据现有的草稿章节，规划出一份逻辑严密、穿透力强的终稿结构。

    ### 任务核心：
    1. **识别主线**: 从草稿中识别出贯穿多个章节的"核心逻辑主线"（如：产业链共振、货币政策转向）。
    2. **分歧评估 (Entropy)**: 识别各章节中观点冲突或确定性不一之处，规划如何在正文中呈现这些"分歧点"。
    3. **结构蓝图**:
       - 定义一级标题（逻辑主题）。
       - 归類別章节：哪些訊號应放入同一主题下深度解析？
       - 排序：將 ISQ 强度最高、与{query_context}最相关的訊號置前。

    ### 现有草稿目录 (TOC)
    {toc}

    请輸出你的【终稿修订大纲】（Markdown 格式）。
    """

# 2. 撰写阶段 (Section Writing)
def get_report_writer_instructions(theme_title: str, signal_cluster_text: str, signal_indices: list, price_context: str = "", user_query: str = None) -> str:
    """生成 Writer Agent 指令 - 基于主题聚類別撰写綜合分析"""

    price_info = f"\n### 近期价格参考\n{price_context}\n" if price_context else ""
    query_context = f"\n**使用者意图**: \"{user_query}\"\n请确保分析内容回应了使用者的关注点。\n" if user_query else ""
    isq_block = generate_isq_prompt_section(include_header=False)

    # Keep citation scheme stable across re-ordering / edits.
    # Cite keys are provided in each signal block as: 引用: [@KEY]

    return f"""你是一位资深金融分析师。请针对核心主题 **"{theme_title}"** 撰写一篇深度研报章节。
    {query_context}

    ### 輸入訊號集 (本章节需綜合的訊號)
    {signal_cluster_text}
    {price_info}

    ### ISQ 評分说明
    {isq_block}

    ### 写作要求
    1. **叙事逻辑**: 不要罗列訊號，要將这些訊號编织成一个连贯的故事。先讲宏观/行業背景，再讲具体事件传导，最后落脚到個股/标的影響。
    2. **量化支撑**: 引用 ISQ 評分（确定性、强度、预期差）来佐证你的观点。关键观点必须关联相应的 ISQ 分值。
     3. **引用规范（稳定 CiteKey）**: 关键论断必须标注来源引用，使用 `[@CITE_KEY]` 格式。
         - CiteKey 已在輸入訊號块中以 `引用: [@KEY]` 提供，请直接复制使用。
         - 不要使用 `[[1]]` 这類別不稳定编号。
    4. **关联标的预测**: **必须**在章节末尾明确给出受影響标的的预测分析，套件括：
       - 至少列出 1-2 个相关上市公司代號（如 "AAPL"、"2330"）
       - 给出短期（T+3或T+5）的方向性判断
       - 如果可能，给出预期价格区间或漲跌幅预测

    ### 【重要】标题层级规范

    ❌ **錯誤示例**（绝对不要这样）：
    ```markdown
    # {theme_title}

    ### 宏观背景
    ...
    ```

    ✅ **正确示例**（必须这样）：
    ```markdown
    ## {theme_title}

    ### 宏观背景

    近期全球经济环境...

    ### 具体传导机制分析

    ...

    ### 核心标的分析

    建议关注：台積電（2330）...
    ```

    **关键要求**：
    - 章节主标题使用 `##` (H2)
    - 章节子标题使用 `###` (H3)
    - **绝对禁止**使用 `#` (H1)
    - 第一行必须是 `## {theme_title}` 开头

    ### 核心：图表叙事 (Visual Storytelling)
    **必须**在文中插入至少 1-2 个图表，且图表必须与上下文紧密結合（不要堆砌在末尾）。

    **可选图表類別型 (请根据内容選擇最合适的 1-2 种):**

    **A. AI 预测 + 走势 (Forecast) - 【强烈推荐 / 最新规范】**
    *适用*: 当文中明确提及某上市公司時，**必须**使用此图表展示股价走势与 AI 预测。
    *必填字段*:
    - `ticker`: 股票代號，美股如 "AAPL"、"NVDA"；台股 4 位數字如 "2330"、"2454"，允许带后缀（如 "2330.TW"）
    - `pred_len`: 预测交易日长度（建议 3 或 5）
    *代號示例*:
    ```json-chart
    {{"type": "forecast", "ticker": "2330.TW", "title": "台積電（2330）T+5 预测", "pred_len": 5}}
    ```
    **重要**：禁止手写 `prediction` 陣列（预测由系统自動生成并渲染）。
    *注意*: 如果提及多只股票，应為每只生成独立的 forecast 图表。

        **【推荐写法：多情景 → 最终归因 → 产出唯一预测图】**
        你可以在正文里描述多种情景（如：基准/乐观/悲观），但在插入预测图之前，必须明确给出"本报告最终選擇的最可能情景"及其归因，然后用 `forecast` 图表做最终总结。
        為了让系统把"最终归因"可靠地传递给预测模組，请在 `forecast` JSON 中可选补充以下字段（字段均為可选，越完整越好）：
        - `selected_scenario`: 最可能情景名称（如 "基准" / "乐观" / "悲观"）
        - `selection_reason`: 選擇该情景的归因理由（1-3 句）
        - `scenarios`: 情景列表（陣列），每个元素可套件含 `name`、`description`、`probability`（0-1）
        *示例*:
        ```json-chart
        {{
            "type": "forecast",
            "ticker": "2330.TW",
            "title": "台積電（2330）T+5 预测（基准情景）",
            "pred_len": 5,
            "selected_scenario": "基准",
            "selection_reason": "結合AI伺服器訂單能見度與AI晶片代工市佔，基准情景概率最高；短期扰动主要來自美國出口管制政策不確定性。",
            "scenarios": [
                {{"name": "樂觀", "description": "AI資本開銷持續增加，台積電先進製程滿載", "probability": 0.6}},
                {{"name": "基準", "description": "訂單穩定增長，但地緣政治帶來小幅波動", "probability": 0.3}},
                {{"name": "悲觀", "description": "美國加大出口限制，影響短期訂單", "probability": 0.1}}
            ]
        }}
        ```

    **B. 歷史走势 (Stock) - 仅作為兼容兜底**
    *适用*: 當你無法給出預測時（例如無法確定標的），可僅展示歷史走勢。
    *代號示例*:
    ```json-chart
    {{"type": "stock", "ticker": "2330", "title": "台積電歷史走勢"}}
    ```

    **C. 舆情情绪演变 (Sentiment Trend)**
    *适用*: 当讨论行業政策、突发事件（如"AI監管"、"晶片出口限制"）的民意变化時。
    *注意*: `keywords` 必须是事件核心词。
    *代號*:
    ```json-chart
    {{"type": "sentiment", "keywords": ["AI監管", "晶片出口"], "title": "市場對晶片出口管制的政策情緒演變"}}
    ```

    **D. 逻辑传导链条 (Transmission Chain)**
    *适用*: 复杂的蝴蝶效应分析（支援分支结构）。
    *代號*:
    ```json-chart
    {{
      "type": "transmission",
      "nodes": [
        {{"node_name": "AI需求爆發", "impact_type": "利好", "logic": "雲端服務商資本支出增加"}},
        {{"node_name": "晶圓代工", "impact_type": "利好", "logic": "先進製程產能利用率攀升", "source": "AI需求爆發"}},
        {{"node_name": "設備材料", "impact_type": "利好", "logic": "擴產帶動設備採購需求", "source": "晶圓代工"}},
        {{"node_name": "封測廠", "impact_type": "利好", "logic": "先進封裝需求釋放", "source": "晶圓代工"}}
      ],
      "title": "AI需求爆發的邏輯傳導與分支"
    }}
    ```
    *说明*: 使用 `source` 字段指定父节点名称以创建分支结构。

    **E. 訊號质量评估 (ISQ Radar)**
    *适用*: 对某个关键訊號进行多维度（确定性、预期差等）定性评估時。
    *代號*:
    ```json-chart
    {{"type": "isq", "sentiment": 0.8, "confidence": 0.9, "intensity": 4, "expectation_gap": 0.7, "timeliness": 0.9, "title": "核心訊號质量评估"}}
    ```
    """

# 3. 整合阶段 (Final Assembly) - 原版，保留用于 fallback
def get_report_editor_instructions(draft_sections: str, plan: str, sources_list: str) -> str:
    """生成最终编辑指令 - 根据规划蓝图重组内容"""
    return f"""你是一位专业的研报编辑。请將以下基于主题撰写的草稿章节整合成最终研报。

    ### 原始草稿内容
    {draft_sections}

    ### 原始引用来源
    {sources_list}

    ### 任务与要求
    1. **结构化**: 為每个草稿章节添加合适的 Markdown 标题 (## 级别)。
    2. **连贯性**: 确保章节之间过渡自然。
    3. **完整性**:
       - 必须保留所有 `json-chart` 代號块（图表配置）。
         - 必须保留引用标注 `[@CITE_KEY]`。
       - 生成 `## 核心观点摘要`、`## 参考文献` 和 `## 風險提示`。

    ### 輸出
    只輸出最终的 Markdown 研报内容。
    """


# 4. 单节编辑 (Incremental Section Editing with RAG)
def get_section_editor_instructions(section_index: int, total_sections: int, toc: str) -> str:
    """生成单节编辑 prompt，支援 RAG 工具呼叫"""
    return f"""你是一位研报编辑。你正在编辑报告的第 {section_index}/{total_sections} 节。

    ### 当前目录 (TOC)
    {toc}

    ### 你的任务
    1. 润色当前章节内容，确保逻辑清晰、語言专业。
    2. 保留所有 `[@CITE_KEY](#ref-CITE_KEY)` 或 `[@CITE_KEY]` 格式的引用。
    3. 保留所有 `json-chart` 代號块，不做修改。
    4. 如果需要参考其他章节内容，使用 `search_context` 工具搜尋。
    5. 只輸出编辑后的章节内容，不要輸出其他章节。

    ### 【关键】标题层级规范
    **严格遵守以下规则：**
    - 章节主标题使用 `##` (H2)
    - 章节子标题使用 `###` (H3)
    - **禁止使用** `#` (H1) - 只有报告大标题可以使用 H1
    - 如果原文中有 H1，必须將其降级為 H2
    - 不要輸出与 "参考文献"、"風險提示" 相同的标题

    直接輸出编辑后的 Markdown 内容。
    """


# 5. 摘要生成 (Summary Generation)
def get_summary_generator_instructions(toc: str, section_summaries: str) -> str:
    """生成报告摘要指令 - 套件含市場分歧度分析"""
    return f"""你是一位资深研报主笔。请生成今日报告的核心观点摘要的**正文内容**。

    ### 章节摘要
    {section_summaries}

    ### 任务：
    1. **核心逻辑提炼**: 用 150 字以内总结今日最核心的投资主线。
    2. **分歧识别**: 如果不同訊號对同一板块有冲突观点，请明确指出"市場分歧点"。
    3. **确定性排序**: 标记出今日确定性最高的前两个机会（需列出具体标的代號）。

    ### 【重要】輸出格式规范：

    ❌ **錯誤示例**（不要遗漏二级标题）：
    ```markdown
    ### 核心逻辑提炼
    ...
    ```

    ✅ **正确示例**（应该这样輸出）：
    ```markdown
    ## 核心观点摘要

    ### 核心逻辑提炼

    AI晶片代工需求爆發帶動半導體產業鏈成長...

    ### 市場分歧点

    資本市場波動顯示半導體、新能源等板塊估值邏輯受政策敏感性增強...

    ### 确定性排序

    1. **AI晶片代工**（ISQ确定性0.85，推荐标的：台積電 2330.TW）
    2. **半導體設備材料**（ISQ确定性0.75，推荐标的：NVIDIA 美股代號 NVDA）
    ```

    ### 关键要求：
    - 第一行必须是 `## 核心观点摘要`
    - 主体部分使用 H3 (`###`) 和 H4 (`####`) 级别标题
    - **必须**套件含 `## 核心观点摘要` 这一级标题

    现在请按照正确示例的格式輸出摘要内容。
    """


# 6. 最终组装 (Final Assembly with Sections)
def get_final_assembly_instructions(sources_list: str) -> str:
    """生成最终报告组装的 prompt"""
    return f"""你是一位研报主笔。请完成以下任务：

    ### 任务
    1. 生成 "## 參考文獻" 章節（需要按照順序，順序不對時進行調整）：
    - 原始来源：
    {sources_list}
    - 格式：`<a id="ref-CITE_KEY"></a>[@CITE_KEY] 标题 (来源), [链接地址]`
    2. 生成 "## 風險提示" (标准免责声明)。
    3. 生成 "## 快速扫描" 表格，汇总各主题的核心观点。
    - 表格列：**主题**, **核心观点**, **强度(Intensity)**, **确定性(Confidence)**。
    - 强度和确定性请参考原章节中的 ISQ 評分。

    只輸出上述三个章节的 Markdown 内容。
    """

def get_cluster_task(signals_preview: str) -> str:
    """生成聚類別任务描述"""
    return f"请对以下訊號进行主题聚類別：\n\n{signals_preview}"

def get_writer_task(theme_title: str) -> str:
    """生成撰写任务描述"""
    return f"请依据主题 '{theme_title}' 和 輸入訊號集 開始撰写深度分析章节。"

def get_planner_task() -> str:
    """生成规划任务描述"""
    return "请阅读现有草稿并规划终稿大纲，识别核心逻辑主线和市場分歧点。"

def get_editor_task() -> str:
    """生成编辑任务描述"""
    return "请根据规划大纲和草稿内容，生成最终研报。确保逻辑连贯，保留所有图表和引用。"
