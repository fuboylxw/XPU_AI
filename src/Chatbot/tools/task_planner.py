import json
from typing import Any, Dict, List, Optional
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config.settings import settings

class TaskPlanner:
    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        self.llm = llm or ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_MODEL_BASE_URL,
            temperature=0.2,
        )


    async def plan(self, goal: str, max_steps: int = 5, intent_analysis :Dict[str, Any] = {}) -> Dict[str, Any]:
        sys_text = (
            """
            你是一个专业的任务规划助手，负责 plan-and-execute 架构中的“计划阶段”（Planner）。
            你的职责是：基于用户原始需求（goal）与意图识别结果（intent_analysis），
            将复杂需求拆解为一组可执行、可调度、语义独立的子任务。

            请严格遵循以下要求：

            1. 输出必须是一个 JSON 数组（列表），其中每个元素为一个任务对象。
            2. 你只能输出严格 JSON，禁止出现解释、自然语言、额外文字、注释。
            3. 拆解的任务数量不得超过 {max_steps} 个。
            4. 任务对象必须包含以下字段：
            - order：任务执行顺序（从 1 开始递增）
            - title：任务标题，需基于用户目标与 intent_analysis 进行概括
            - query：每个子任务的具体执行指令或查询内容（必须可独立执行）

            5. 输出格式必须与以下结构完全一致：
            [
            {{
                "order": 1,
                "title": "",
                "query": ""
            }}
            ]

            6. 禁止输出 null、None、空对象、空数组、空字符串。
            7. 若 intent_analysis 中已有明确意图分类或动作，你必须参考并优先使用该信息拆解任务。
            8. 如果某任务无法从 intent_analysis 中明确归类，则基于用户表达生成 query。
            9. 禁止生成重复任务；每个任务必须是具体且可执行的语义动作。

            10. 拆解原则：
                - 基于 intent_analysis 的主意图将需求划分为多个动作型子任务
                - 同一句话中的多个不同动作必须拆成多个任务
                - 信息查询类任务独立成任务
                - 操作类任务（如“发送消息”“写入内容”）必须拆成独立任务

            例如：
                用户需求：今天西安天气如何，几点了
                输出：[
                {{"order": 1, "title": "今天西安天气如何，几点了", "query": "查询西安天气"}},
                {{"order": 2, "title": "今天西安天气如何，几点了", "query": "查询当前时间"}}
                ]
                用户需求：今天有什么重要新闻，微信给XX回复知道了
                输出：[
                {{"order": 1, "title": "今天有什么重要新闻，微信给XX回复知道了", "query": "查询今天的重要新闻"}},
                {{"order": 2, "title": "今天有什么重要新闻，微信给XX回复知道了", "query": "微信给XX回复'知道了'"}}
                ]
            """
        )
        tmpl = ChatPromptTemplate.from_messages([
            ("system", sys_text),
            ("human", "用户需求：{goal}。意图分析：{intent_analysis}。请根据规则生成纯数组计划，数组元素为每个子任务的具体需求文本。")
        ])
        msg = tmpl.format_messages(goal=goal, max_steps=max_steps, intent_analysis=intent_analysis)
        out = await self.llm.ainvoke(msg)
        try:
            # 清理可能的Markdown格式
            content = out.content.strip()
            # 移除可能的```json 和 ```标记
            if content.startswith('```'):
                lines = content.split('\n')
                # 移除第一行（```json 或 ```）
                if lines[0].strip().startswith('```'):
                    lines = lines[1:]
                # 移除最后一行（```）
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()
            data = json.loads(content)
        except Exception as e:
            # 解析失败时打印错误日志并返回空列表
            import logging
            logging.error(f"TaskPlanner JSON解析失败: {e}, 原始内容: {out.content[:200]}")
            data = {"tasks": []}
        tasks: List[Any]
        if isinstance(data, list):
            tasks = data
        else:
            tasks = data.get("tasks") or []
            if not isinstance(tasks, list):
                tasks = []
        # 规范化字段
        normalized: List[Dict[str, Any]] = []
        for i, t in enumerate(tasks[:max_steps]):
            if isinstance(t, dict):
                normalized.append({
                    "order": i + 1,
                    "title": str(t.get("title") or f"任务{i+1}"),
                    "query": str(t.get("query") or goal),
                })
            else:
                normalized.append({
                    "order": i + 1,
                    "title": f"任务{i+1}",
                    "query": str(t) if isinstance(t, str) and t.strip() else goal,
                })
        return {"success": True, "source": "task_planner", "results": normalized}

def build_task_planner_runner():
    async def runner(params: Dict[str, Any]) -> Dict[str, Any]:
        goal = str(params.get("goal") or "")
        max_steps = int(params.get("max_steps") or 5)
        planner = TaskPlanner()
        intent_analysis = params.get("intent_analysis") or {}
        return await planner.plan(goal, max_steps=max_steps, intent_analysis=intent_analysis)
    return runner

TASK_PLANNER_INPUT_SCHEMA = {
    "properties": {
        "goal": {"type": "string"},
        "max_steps": {"type": "integer"},
    },
    "required": ["goal"],
}