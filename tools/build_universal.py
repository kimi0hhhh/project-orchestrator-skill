#!/usr/bin/env python3
"""build_universal.py · 从 ZCode 源契约构建通用版角色契约

用法：python tools/build_universal.py
读取 agents/*.md（ZCode 源契约），做平台解耦变换后写入 universal/agents/*.md。
改契约内容请改源文件后重新构建——universal 侧不手改正文。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "agents"
DST = ROOT / "universal" / "agents"

HEADER = """<!-- 由 tools/build_universal.py 从 ZCode 源契约生成；改内容请改源文件后重新构建 -->
<!-- 平台适配约定：本契约作为子代理的系统提示注入（platform-config.md: role_as_system_prompt）；
     frontmatter 有意不含 tools 白名单——单层编排的堵死方式见 platform-config.md: one_layer；
     文中「派发原语」= 本平台派发子代理的方式；路径前缀按 workspace_layout 落地。 -->

"""


def transform(text: str) -> str:
    # 1. frontmatter：去掉 tools 行（白名单是平台事，归 platform-config）
    text = re.sub(r"^tools: \[.*\]\n", "", text, flags=re.M)
    # 2. 能力地图行指向 capability-map.md（ZCode 特有），通用版改为内联提示
    text = re.sub(
        r"^> \*\*能力地图\*\*.*\n",
        "> **能力边界**：工件契约优先于任何外部模板；本角色不派发子任务、不越权改其他角色工件。\n",
        text,
        flags=re.M,
    )
    # 3. 推荐 skill 行的路径泛化（capability-map.md 通用版暂无，清单保留在行内）
    text = text.replace("见 `capability-map.md` §", "见下「推荐 skill」§")
    # 4. 路径前缀：ZCode 专属 → 通用布局
    text = text.replace(".zcode/", "")
    # 5. 平台工具名 → 原语表述
    text = text.replace("Agent 工具或子进程", "平台的子代理派发原语或子进程")
    text = text.replace("Agent 工具", "派发原语")
    return text


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for src in sorted(SRC.glob("*.md")):
        out = DST / src.name
        out.write_text(HEADER + transform(src.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"built {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
