# -*- coding: utf-8 -*-
"""
agent-demo：一个最小可运行的 Agent（智能体）
============================================
目标：不装任何第三方包，让你亲眼看到 Agent 的核心循环到底发生了什么。

运行：
    python agent.py "现在几点了？顺便算一下 37*89 等于几"
    python agent.py "sandbox 目录下有哪些文件？帮我读一下 notes.txt，数数有多少字"

它和你平时用的"聊天机器人"最大的区别：
    聊天机器人 = 一问一答，只会说话
    Agent     = 模型自己决定"我要调哪个工具" → 拿到真实结果 → 再决定下一步

核心循环（整个文件最重要的 20 行在 run_agent 里）：
    ① 把用户问题 + 工具清单发给模型
    ② 模型返回 tool_calls（它想调哪些工具、参数是什么）
    ③ 我们真正执行这些工具，把结果当成"观察"塞回对话
    ④ 回到 ①，直到模型不再要工具、直接给出最终回答
"""

import ast
import datetime
import json
import operator
import pathlib
import re
import sys
import time
import urllib.request

# Windows 控制台编码自适应：控制台是 UTF-8 就输出 UTF-8，是 GBK 就输出 GBK
# （不处理的话中文会变成乱码）
try:
    import ctypes
    _cp = ctypes.windll.kernel32.GetConsoleOutputCP()
    sys.stdout.reconfigure(encoding="utf-8" if _cp == 65001 else "gbk", errors="replace")
except Exception:
    pass

# ---------------- 配置 ----------------
OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"

MAX_STEPS = 8          # 防死循环第一板斧：最多走几步
MAX_SECONDS = 180      # 防死循环第二板斧：总耗时上限
SANDBOX = pathlib.Path(__file__).parent / "sandbox"   # 工具只能访问这个目录

# ---------------- 工具（Agent 的"手脚"）----------------
# 每个工具 = 一个普通 Python 函数 + 一段给模型看的说明书（JSON Schema）
# 模型看不懂代码，它只看说明书，所以 description 写得好不好，直接决定它会不会用


def tool_get_time() -> str:
    """返回当前时间。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 计算器用 ast 解析，绝不使用 eval —— 直接 eval 等于把电脑交给模型
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只支持加减乘除和括号")


def tool_calculator(expression: str) -> str:
    """计算一个数学表达式，比如 (1234*56)+789。"""
    try:
        return str(_eval_node(ast.parse(expression, mode="eval")))
    except Exception as e:
        return f"计算失败：{e}"


def _safe_path(rel: str) -> pathlib.Path:
    """防越狱：不管模型传什么路径，都锁死在 sandbox 里面。"""
    p = (SANDBOX / rel).resolve()
    if not str(p).startswith(str(SANDBOX.resolve())):
        raise ValueError("只能访问 sandbox 目录")
    return p


def tool_list_files() -> str:
    """列出 sandbox 目录下的所有文件。"""
    files = [f.name for f in SANDBOX.iterdir() if f.is_file()]
    return ", ".join(files) if files else "（目录是空的）"


def tool_read_file(path: str) -> str:
    """读取 sandbox 目录下某个文本文件的内容。"""
    p = _safe_path(path)
    if not p.is_file():
        return f"文件不存在：{path}"
    return p.read_text(encoding="utf-8")


# 名称 -> (真实函数, 给模型看的说明书)
TOOLS = {
    "get_time": (
        tool_get_time,
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "获取当前的日期和时间。当用户问'现在几点''今天几号'时必须调用这个工具。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ),
    "calculator": (
        tool_calculator,
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "计算数学表达式并返回精确结果。任何算术都不要自己心算，必须调用它。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "要计算的表达式，例如 (1234*56)+789",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
    ),
    "list_files": (
        tool_list_files,
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "列出 sandbox 目录下所有文件的文件名。",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ),
    "read_file": (
        tool_read_file,
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取 sandbox 目录下某个文本文件的内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件名，例如 notes.txt"}
                    },
                    "required": ["path"],
                },
            },
        },
    ),
}

TOOL_SCHEMAS = [v[1] for v in TOOLS.values()]


# ---------------- 和模型对话 ----------------
def chat(messages) -> dict:
    """调 Ollama 的 /api/chat 接口，返回一条 assistant 消息。"""
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOL_SCHEMAS,   # 关键：把工具清单交给模型
        "stream": False,
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))["message"]


def strip_think(text: str) -> str:
    """qwen3 是推理模型，会先输出一段思考过程，展示时去掉，只留结论。"""
    if not text:
        return ""
    text = re.sub(r"<think[^>]*>.*?</think\s*>", "", text, flags=re.S)
    return re.sub(r"</?think[^>]*>", "", text).strip()


# ---------------- 核心：Agent 循环 ----------------
def run_agent(question: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个助手。需要真实信息（时间、计算、文件）时必须调用工具，"
                "不要凭空猜测。拿到工具结果后用中文简洁作答。"
            ),
        },
        {"role": "user", "content": question},
    ]

    started = time.time()
    seen = set()          # 防死循环第三板斧：重复检测，同一个调用不许连着来两次
    step = 0

    while step < MAX_STEPS:
        step += 1
        if time.time() - started > MAX_SECONDS:
            return "超过时间上限，已停止（这就是防死循环的第二板斧）"

        msg = chat(messages)
        tool_calls = msg.get("tool_calls") or []

        # 没有工具调用 = 模型认为可以回答了，循环结束
        if not tool_calls:
            return strip_think(msg.get("content", "")) or "（模型没有给出回答）"

        # 把模型的这一步（含它的工具调用意图）记进对话历史
        messages.append(
            {
                "role": "assistant",
                "content": strip_think(msg.get("content", "")),
                "tool_calls": tool_calls,
            }
        )

        print(f"\n--- 第 {step} 步 ---")
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}

            signature = f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"
            print(f"[模型决定] 调用 {name}({json.dumps(args, ensure_ascii=False)})")

            # 重复检测：完全相同的调用说明它卡住了，直接给它反馈打断
            if signature in seen:
                observation = "这个工具调用你刚刚已经做过了，结果没变。请基于已有信息直接回答，或换一个方法。"
                print("[检测到重复调用] 已拦截")
            else:
                seen.add(signature)
                fn = TOOLS.get(name)
                if fn is None:
                    observation = f"没有名为 {name} 的工具"
                else:
                    try:
                        observation = str(fn[0](**args))
                    except Exception as e:
                        observation = f"工具执行出错：{e}"

            print(f"[工具返回] {observation}")

            # 把工具结果作为"观察"塞回对话，模型下一步会看到它
            messages.append(
                {"role": "tool", "content": observation, "tool_name": name}
            )

    return f"已达到最大步数 {MAX_STEPS} 仍未得出答案，已停止（防死循环第一板斧）"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "现在几点了？顺便算一下 (1234*56)+789 等于多少"
    print(f"[你问] {q}")
    print(f"[模型] {MODEL}")
    answer = run_agent(q)
    print(f"\n[最终回答] {answer}")
