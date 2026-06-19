"""RAG 上下文选择与引用整理的单元测试。"""

from app.rag.selection import build_references, select_prompt_contexts
from app.repositories.vector.base import RetrievalResult


def _result(text: str, score: float = 1.0) -> RetrievalResult:
    return RetrievalResult(text=text, score=score, metadata={})


def test_select_prompt_contexts_dedupes_and_limits() -> None:
    """重复片段应去重，且数量不超过 limit。"""
    results = [
        _result("退货需要在7天内申请。"),
        _result("退货需要在7天内申请。"),  # 重复
        _result("发货后48小时内可查询物流。"),
        _result("会员积分每消费1元累计1分。"),
    ]
    contexts = select_prompt_contexts("退货怎么操作", results, limit=2)
    assert len(contexts) == 2
    # 去重后第一条仍只出现一次。
    assert contexts.count("退货需要在7天内申请。") == 1


def test_select_prompt_contexts_ranks_by_keyword_overlap() -> None:
    """与问题关键词重合度更高的片段应排在前面。"""
    results = [
        _result("会员积分规则说明。"),
        _result("订单退款会原路退回到支付账户。"),
    ]
    contexts = select_prompt_contexts("退款多久到账", results, limit=1)
    assert contexts == ["订单退款会原路退回到支付账户。"]


def test_select_prompt_contexts_zero_limit_returns_empty() -> None:
    assert select_prompt_contexts("任意问题", [_result("内容")], limit=0) == []


def test_build_references_clips_and_limits() -> None:
    """引用应裁剪到 max_chars 以内并受 limit 约束。"""
    long_text = "这是一段很长的服务资料。" * 20
    references = build_references("服务", [long_text], limit=1, max_chars=30)
    assert len(references) == 1
    assert len(references[0]) <= 31  # 末尾可能带省略号


def test_build_references_zero_limit_returns_empty() -> None:
    assert build_references("问题", ["内容"], limit=0, max_chars=100) == []
