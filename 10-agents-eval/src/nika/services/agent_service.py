import json
import logging
from dataclasses import dataclass
from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from nika.config import Config
from nika.services.chitchat import (
    is_chitchat,
    is_order_request,
    is_product_or_nutrition_question,
    is_reference_question,
    is_register_cgm_request,
)
from nika.services.glucose_unit_converter_tool import create_glucose_unit_converter_tool
from nika.services.mcp_tools_loader import load_mcp_tools, mcp_tool_names
from nika.services.rag_search_tool import create_rag_search_tool, sources_to_documents
from nika.services.rag_service import RagService

logger = logging.getLogger(__name__)

EMPTY_ANSWER_FALLBACK = (
    "Извини, не смогла сформулировать ответ. Попробуй переформулировать вопрос."
)

HITL_TOOL_ORDER = "order_care_product"
HITL_TOOL_REGISTER = "register_cgm_sensor"
HITL_TOOLS = (HITL_TOOL_ORDER, HITL_TOOL_REGISTER)

_RAG_SEARCH_TOOL_CHOICE = {
    "type": "function",
    "function": {"name": "rag_search"},
}

_ORDER_CARE_TOOL_CHOICE = {
    "type": "function",
    "function": {"name": HITL_TOOL_ORDER},
}

_REGISTER_CGM_TOOL_CHOICE = {
    "type": "function",
    "function": {"name": HITL_TOOL_REGISTER},
}


@dataclass(frozen=True)
class AgentAnswer:
    answer: str
    documents: list[Document]
    interrupt: object | None = None


async def create_nika_agent(config: Config, rag: RagService) -> "AgentService":
    """Async-фабрика агента (референс agent-mcp.ipynb)."""
    return await initialize_agent(config, rag)


async def initialize_agent(config: Config, rag: RagService) -> "AgentService":
    """Загрузить MCP tools и собрать AgentService. Без MCP — graceful degradation."""
    mcp_tools = await load_mcp_tools(config.mcp_server_url)
    return AgentService(config, rag, mcp_tools=mcp_tools)


class AgentService:
    def __init__(
        self,
        config: Config,
        rag: RagService,
        *,
        mcp_tools: list[BaseTool] | None = None,
    ) -> None:
        self._config = config
        self._checkpointer = MemorySaver()
        self._thread_versions: dict[str, int] = {}
        rag_search = create_rag_search_tool(rag)
        glucose_converter = create_glucose_unit_converter_tool()
        extra = list(mcp_tools or [])
        tools: list[BaseTool] = [rag_search, glucose_converter, *extra]
        self._mcp_tool_names = mcp_tool_names(extra)
        if self._mcp_tool_names:
            logger.info("Agent tools include MCP: %s", self._mcp_tool_names)
        else:
            logger.info("Agent tools: local only (no MCP)")
        llm = self._chat_llm()
        middleware = self._build_middleware()
        tool_names = {tool.name for tool in tools}
        self._has_order_tool = HITL_TOOL_ORDER in tool_names
        self._has_register_tool = HITL_TOOL_REGISTER in tool_names
        self._agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=config.agent_system_prompt,
            checkpointer=self._checkpointer,
            middleware=middleware,
        )
        self._search_agent = create_agent(
            model=llm.bind_tools(tools, tool_choice=_RAG_SEARCH_TOOL_CHOICE),
            tools=tools,
            system_prompt=config.agent_system_prompt,
            checkpointer=self._checkpointer,
            middleware=middleware,
        )  # type: ignore[call-overload]
        self._order_agent = None
        if self._has_order_tool:
            self._order_agent = create_agent(
                model=llm.bind_tools(tools, tool_choice=_ORDER_CARE_TOOL_CHOICE),
                tools=tools,
                system_prompt=config.agent_system_prompt,
                checkpointer=self._checkpointer,
                middleware=middleware,
            )  # type: ignore[call-overload]
        self._register_agent = None
        if self._has_register_tool:
            self._register_agent = create_agent(
                model=llm.bind_tools(tools, tool_choice=_REGISTER_CGM_TOOL_CHOICE),
                tools=tools,
                system_prompt=config.agent_system_prompt,
                checkpointer=self._checkpointer,
                middleware=middleware,
            )  # type: ignore[call-overload]
        self._direct_agent = create_agent(
            model=llm,
            tools=[],
            system_prompt=config.agent_system_prompt,
            checkpointer=self._checkpointer,
            middleware=middleware,  # PII и на chitchat / ответы без tools
        )

    @property
    def mcp_tool_names(self) -> list[str]:
        return list(self._mcp_tool_names)

    def _build_middleware(self) -> list[AgentMiddleware[Any, Any, Any]]:
        run_limit = self._config.agent_run_limit
        return [
            ModelCallLimitMiddleware(
                run_limit=run_limit,
                exit_behavior="end",
            ),
            ToolCallLimitMiddleware(
                run_limit=run_limit,
                exit_behavior="end",
            ),
            # Layer: PII — карты (order_care_product) и email в ответах
            PIIMiddleware(
                "credit_card",
                strategy="mask",
                apply_to_input=False,
                apply_to_output=True,
                apply_to_tool_results=True,
            ),
            PIIMiddleware(
                "email",
                strategy="mask",
                apply_to_input=False,
                apply_to_output=True,
            ),
            # Layer: HITL — order_care_product / register_cgm_sensor
            HumanInTheLoopMiddleware(
                interrupt_on={
                    name: {"allowed_decisions": ["approve", "reject"]}
                    for name in HITL_TOOLS
                }
            ),
        ]

    async def answer(
        self,
        chat_id: str | int,
        question: str,
        *,
        require_search: bool = False,
    ) -> AgentAnswer:
        if is_register_cgm_request(question):
            if not self._has_register_tool:
                return AgentAnswer(
                    answer=(
                        "Сейчас не могу зарегистрировать сенсор: MCP-сервер "
                        "недоступен. Запусти make run-mcp-nika и повтори запрос."
                    ),
                    documents=[],
                )
            mode = "register"
        elif is_order_request(question):
            if not self._has_order_tool:
                return AgentAnswer(
                    answer=(
                        "Сейчас не могу оформить заказ: MCP-сервер недоступен. "
                        "Запусти make run-mcp-nika и повтори запрос."
                    ),
                    documents=[],
                )
            mode = "order"
        elif is_chitchat(question):
            mode = "direct"
        elif is_product_or_nutrition_question(question):
            mode = "tools"
        elif require_search or is_reference_question(question):
            mode = "search"
        else:
            mode = "tools"
        logger.info("Agent mode=%s chat_id=%s", mode, chat_id)
        return await self.run_turn_agent(
            chat_id,
            user_text=question,
            mode=mode,
        )

    async def resume(
        self,
        chat_id: str | int,
        decision: str,
        *,
        message: str | None = None,
    ) -> AgentAnswer:
        if decision == "approve":
            command: Command[Any] = Command(resume={"decisions": [{"type": "approve"}]})
        else:
            command = Command(
                resume={
                    "decisions": [
                        {
                            "type": "reject",
                            "message": message
                            or "Операция отклонена пользователем",
                        }
                    ]
                }
            )
        return await self.run_turn_agent(
            chat_id,
            command=command,
            mode="tools",
        )

    async def run_turn_agent(
        self,
        chat_id: str | int,
        *,
        user_text: str | None = None,
        command: Command[Any] | None = None,
        mode: str = "tools",
    ) -> AgentAnswer:
        """Один ход агента: user text или resume после HITL (референс notebook)."""
        if command is not None:
            inputs: dict[str, Any] | Command[Any] = command
        elif user_text is not None:
            inputs = {"messages": [HumanMessage(content=user_text)]}
        else:
            raise ValueError("run_turn_agent requires user_text or command")

        if mode == "direct":
            agent = self._direct_agent
        elif mode == "search":
            agent = self._search_agent
        elif mode == "order" and self._order_agent is not None:
            agent = self._order_agent
        elif mode == "register" and self._register_agent is not None:
            agent = self._register_agent
        else:
            agent = self._agent

        config: RunnableConfig = {
            "configurable": {"thread_id": self._thread_id(chat_id)},
        }
        return await self._run_agent_stream(agent, inputs, config, chat_id)

    def reset_thread(self, chat_id: str | int) -> None:
        key = str(chat_id)
        self._thread_versions[key] = self._thread_versions.get(key, 0) + 1

    def get_trajectory(self, chat_id: str | int) -> list[BaseMessage]:
        """Сообщения checkpointer для chat_id (после answer / run_turn_agent)."""
        config: RunnableConfig = {
            "configurable": {"thread_id": self._thread_id(chat_id)},
        }
        state = self._agent.get_state(config)
        return cast(list[BaseMessage], list(state.values.get("messages", [])))

    def _thread_id(self, chat_id: str | int) -> str:
        key = str(chat_id)
        version = self._thread_versions.get(key, 0)
        return f"{key}:{version}"

    async def _run_agent_stream(
        self,
        agent: Any,
        inputs: dict[str, Any] | Command[Any],
        config: RunnableConfig,
        chat_id: str | int,
    ) -> AgentAnswer:
        interrupts: list[object] = []
        final_state: dict[str, Any] | None = None

        # Без stream_mode="values": нужен ключ __interrupt__ (как в референсе).
        async for step in agent.astream(inputs, config=config):
            if not isinstance(step, dict):
                continue
            if "__interrupt__" in step:
                interrupt_data = step["__interrupt__"]
                if isinstance(interrupt_data, tuple) and interrupt_data:
                    interrupts.append(interrupt_data[0])
                    logger.info("HITL interrupt detected: %s", interrupt_data[0])
                continue
            for node_name, update in step.items():
                if node_name == "__interrupt__":
                    continue
                if isinstance(update, dict) and "messages" in update:
                    final_state = update
                    messages = update["messages"]
                    if messages:
                        log_agent_step({"messages": [messages[-1]]})

        if interrupts:
            logger.info("Agent stopped with HITL interrupt for chat_id=%s", chat_id)
            return AgentAnswer(answer="", documents=[], interrupt=interrupts[0])

        state = agent.get_state(config)
        messages = cast(list[BaseMessage], state.values.get("messages", []))
        if not messages and final_state is not None:
            messages = cast(list[BaseMessage], final_state.get("messages", []))

        if not messages:
            logger.warning("Agent stream returned no messages for chat_id=%s", chat_id)
            return AgentAnswer(answer=EMPTY_ANSWER_FALLBACK, documents=[])

        answer = self._extract_answer_text(messages)
        documents = extract_sources_from_turn(messages)
        logger.info(
            "Agent answer: chat_id=%s answer_len=%d sources=%d",
            chat_id,
            len(answer),
            len(documents),
        )
        return AgentAnswer(answer=answer, documents=documents, interrupt=None)

    def _extract_answer_text(self, messages: list[BaseMessage]) -> str:
        for message in reversed(messages):
            if not isinstance(message, AIMessage):
                continue
            content = _ai_message_text(message)
            if message.tool_calls:
                continue
            if not content.strip():
                logger.warning("Empty AIMessage without tool_calls in agent turn")
                continue
            return content

        for message in reversed(messages):
            if isinstance(message, AIMessage):
                content = _ai_message_text(message)
                if content.strip():
                    logger.warning("Using AIMessage with tool_calls as fallback answer")
                    return content

        logger.warning("Agent produced no usable AIMessage; using fallback")
        return EMPTY_ANSWER_FALLBACK

    def _chat_llm(self) -> ChatOpenAI:
        # Gemini 2.5 Flash via OpenRouter тратит токены на reasoning —
        # без лимита ответа текст обрывается на полуслове («Привет! Я Ника, т»).
        return ChatOpenAI(
            model=self._config.model_rag,
            api_key=self._config.openai_api_key,
            base_url=self._config.openai_base_url,
            temperature=0,
            max_tokens=4096,
            extra_body={
                "reasoning": {"effort": "low"},
            },
        )


def log_agent_step(state: object) -> None:
    if not isinstance(state, dict):
        logger.debug("Agent step: %r", state)
        return

    messages = state.get("messages")
    if not isinstance(messages, list) or not messages:
        logger.debug("Agent step: empty messages")
        return

    last = messages[-1]
    message_type = type(last).__name__
    if isinstance(last, AIMessage):
        tool_names = [call.get("name", "?") for call in last.tool_calls or []]
        preview = _ai_message_text(last)[:120]
        logger.info(
            "Agent step: %s tool_calls=%s content_preview=%r",
            message_type,
            tool_names or None,
            preview,
        )
        if not last.tool_calls and not preview.strip():
            logger.warning("Agent step: empty AIMessage without tool_calls")
        return

    if isinstance(last, ToolMessage):
        preview = _message_content_to_str(last.content)[:120]
        logger.info(
            "Agent step: ToolMessage name=%s preview=%r",
            last.name,
            preview,
        )
        return

    logger.info("Agent step: %s", message_type)


def extract_sources_from_turn(messages: list[BaseMessage]) -> list[Document]:
    last_human_idx = -1
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            last_human_idx = index

    turn_messages = messages[last_human_idx + 1 :] if last_human_idx >= 0 else messages
    all_sources: list[dict[str, object]] = []

    for message in turn_messages:
        if not isinstance(message, ToolMessage) or message.name != "rag_search":
            continue
        content = _message_content_to_str(message.content)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse rag_search ToolMessage as JSON")
            continue
        sources = payload.get("sources")
        if isinstance(sources, list):
            all_sources.extend(cast(list[dict[str, object]], sources))

    return sources_to_documents(all_sources)


def format_hitl_interrupt(interrupt: object) -> str:
    """Текст запроса на согласование операции (plain text для Telegram)."""
    value = getattr(interrupt, "value", None)
    if not isinstance(value, dict):
        return (
            "Требуется подтверждение операции.\n\n"
            "Подтвердить выполнение?"
        )

    action_requests = value.get("action_requests") or []
    if not action_requests:
        return (
            "Требуется подтверждение операции.\n\n"
            "Подтвердить выполнение?"
        )

    action = action_requests[0]
    tool_name = action.get("name", "?")
    tool_args = action.get("args") or {}

    lines = [
        "Требуется подтверждение операции",
        "",
        f"Инструмент: {tool_name}",
        "Параметры:",
    ]
    if isinstance(tool_args, dict):
        for key, arg_value in tool_args.items():
            lines.append(f"• {key}: {arg_value}")
    lines.append("")
    lines.append("Подтвердить выполнение операции?")
    return "\n".join(lines)


def _ai_message_text(message: AIMessage) -> str:
    """Собрать видимый текст: у Gemini multipart content / content_blocks."""
    blocks = getattr(message, "content_blocks", None)
    if isinstance(blocks, list) and blocks:
        parts: list[str] = []
        for block in blocks:
            block_type = (
                block.get("type")
                if isinstance(block, dict)
                else getattr(block, "type", None)
            )
            if block_type in {"reasoning", "thinking", "thought"}:
                continue
            text = (
                block.get("text")
                if isinstance(block, dict)
                else getattr(block, "text", None)
            )
            if isinstance(text, str) and text:
                parts.append(text)
        joined = "".join(parts).strip()
        if joined:
            return joined
    return _message_content_to_str(message.content)


def _message_content_to_str(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type")
                if block_type in {"reasoning", "thinking", "thought"}:
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)
