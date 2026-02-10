from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from app.config import MAX_CONTEXT_MESSAGES
from app.logger import get_logger

logger = get_logger("context_window")


def smart_context_window(
    messages: list,
    max_messages: int = MAX_CONTEXT_MESSAGES,
    max_tool_content: int = 1500,
) -> list:
    """
    Reduce conversation history to fit in the LLM context window.

    Args:
        messages: Full message list from state["messages"]
        max_messages: Max number of non-system messages to keep (default from config)
        max_tool_content: Max chars for ToolMessage content before truncation

    Returns:
        List of messages ready to be prepended with a SystemMessage by the caller.
        Never contains SystemMessages (each agent adds its own).
    """

    # ── 1. Strip SystemMessages (agents add their own) ──
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]

    if not filtered:
        return []

    # ── 2. Truncate oversized ToolMessages ──
    filtered = _truncate_tool_messages(filtered, max_tool_content)

    # ── 3. If already small enough, return as-is ──
    if len(filtered) <= max_messages:
        return filtered

    # ── 4. Find the first HumanMessage (original user request) ──
    first_human = None
    first_human_idx = None
    for i, m in enumerate(filtered):
        if isinstance(m, HumanMessage):
            first_human = m
            first_human_idx = i
            break

    # ── 5. Find a safe cut point for the recent window ──
    # We want the last (max_messages - 1) messages if we're prepending first_human,
    # or last max_messages if there's no first_human to prepend.
    reserve = 1 if first_human is not None else 0
    window_size = max_messages - reserve
    cut_start = len(filtered) - window_size

    # Clamp to valid range
    cut_start = max(cut_start, 0)

    # ── 6. Adjust cut point to never orphan a ToolMessage ──
    # Walk backward: if we'd start on a ToolMessage, include its parent AIMessage too.
    while cut_start > 0 and isinstance(filtered[cut_start], ToolMessage):
        cut_start -= 1

    # Also check: if cut_start lands on an AIMessage with tool_calls,
    # but its ToolMessage response is BEFORE cut_start, that's fine (we keep the pair).
    # But if the AIMessage at (cut_start - 1) has tool_calls and the ToolMessage
    # at cut_start is its response, we already handled that above.

    recent = filtered[cut_start:]

    # ── 7. Prepend first HumanMessage if it was cut ──
    if first_human is not None and first_human_idx is not None and first_human_idx < cut_start:
        # Don't duplicate if it's already in the window
        if first_human not in recent:
            recent = [first_human] + recent

    original_count = len([m for m in messages if not isinstance(m, SystemMessage)])
    if len(recent) < original_count:
        logger.debug(
            f"📐 Context window: {original_count} → {len(recent)} messages "
            f"(max={max_messages}, cut_start={cut_start})"
        )

    return recent


def _truncate_tool_messages(messages: list, max_content: int) -> list:
    """
    Truncate ToolMessages that exceed max_content characters.
    Preserves tool_call_id and name so LangChain pairing still works.
    """
    result = []
    for m in messages:
        if isinstance(m, ToolMessage) and isinstance(m.content, str) and len(m.content) > max_content:
            result.append(ToolMessage(
                content=m.content[:max_content] + "\n...[truncated]",
                tool_call_id=m.tool_call_id,
                name=getattr(m, 'name', ''),
            ))
        else:
            result.append(m)
    return result
