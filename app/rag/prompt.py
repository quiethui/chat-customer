"""Prompt 拼接工具。"""


def build_customer_prompt(
    question: str,
    contexts: list[str],
    history: list[dict[str, str]] | None = None,
    tool_results: list[str] | None = None,
) -> str:
    """构建客服问答 Prompt。

    Args:
        question: 用户本轮问题。
        contexts: 从知识库检索到的文本片段。
        history: 当前用户当前会话的最近聊天上下文。
        tool_results: Tool Calling 返回的业务查询结果，例如订单查询结果。

    Returns:
        拼接后的中文客服 Prompt，供 OpenAI 兼容模型生成最终回答。
    """
    context_text = "\n\n".join(f"[{index + 1}] {item}" for index, item in enumerate(contexts))
    tool_text = "\n\n".join(f"[{index + 1}] {item}" for index, item in enumerate(tool_results or []))
    history_text = "\n".join(
        f"{_role_name(item.get('role', ''))}：{item.get('content', '')}" for item in (history or []) if item.get("content")
    )
    return f"""你是商城在线客服，面向真实用户提供自然、专业、简洁的帮助。你的回答必须像真人客服，不要像知识库问答机器人。

回答原则：
1. 优先根据【内部业务查询结果】回答，其次参考【内部服务资料】；两者只用于你理解问题，禁止向用户提及这些内部信息来源。
2. 禁止在回答中出现或变相表达这些内部系统词：知识库、检索、向量库、上下文、资料片段、根据资料、根据查询结果、未找到依据。
3. 如果内部业务查询结果包含订单信息，只能回答当前查询结果中的订单，不要编造其他订单、物流、退款或售后进度。
4. 如果没有足够信息回答，不要说“知识库中未找到”或“没有依据”，请用客服口吻说明“目前我这边暂时没有查到明确说明”，并给出一个最相关的下一步建议。
5. 默认不要在结尾追加“如果您愿意，我也可以继续帮您看”这类泛化追问；只有确实缺少必要信息或需要用户继续操作时，才用一句话引导用户补充订单号、商品名称、下单时间等关键信息。
6. 回答要直接解决用户问题，避免展开无关内容；能用一两句话说清楚时，不要输出长段落。

历史对话：
{history_text or '暂无历史对话'}

内部业务查询结果（仅供你判断，不得向用户透露来源）：
{tool_text or '暂无业务查询结果'}

内部服务资料（仅供你判断，不得向用户透露来源）：
{context_text or '暂无相关服务资料'}

用户问题：
{question}
"""


def _role_name(role: str) -> str:
    """将数据库中的消息角色转换为 Prompt 中更易读的中文称呼。

    Args:
        role: 聊天消息角色。
    """
    if role == "user":
        return "用户"
    if role == "assistant":
        return "客服助手"
    return role or "消息"
