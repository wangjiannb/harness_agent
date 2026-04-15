#!/usr/bin/env python3
"""Harness Agent CLI - 原子化 AI 任务记忆控制器"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime


AI_DIR = ".ai"
TASKS_DIR = os.path.join(AI_DIR, "tasks")
SNAPSHOTS_DIR = os.path.join(AI_DIR, "snapshots")
MEMORY_BANK = os.path.join(AI_DIR, "memory-bank")
BACKLOG_PATH = os.path.join(MEMORY_BANK, "backlog.md")
ARCHIVE_PATH = os.path.join(MEMORY_BANK, "archive.md")
ENV_PATH = os.path.join(MEMORY_BANK, "environment.md")
LESSONS_PATH = os.path.join(MEMORY_BANK, "lessons.md")
TECH_SPEC_PATH = os.path.join(MEMORY_BANK, "tech-spec.md")


def _now(fmt="%Y-%m-%d"):
    return datetime.now().strftime(fmt)


def _ensure_dirs():
    for d in [
        TASKS_DIR,
        os.path.join(TASKS_DIR, "archive"),
        SNAPSHOTS_DIR,
        os.path.join(SNAPSHOTS_DIR, "archive"),
        MEMORY_BANK,
    ]:
        os.makedirs(d, exist_ok=True)


def _read(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _append(path, content):
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def _parse_frontmatter(text):
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1].strip()
            body = parts[2].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def _build_frontmatter(meta):
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _parse_backlog_max_seq():
    text = _read(BACKLOG_PATH)
    nums = re.findall(r"-(\d+):", text)
    return max(int(n) for n in nums) if nums else 0


def cmd_init(args):
    _ensure_dirs()
    today = _now()

    if not os.path.exists(ENV_PATH):
        _write(
            ENV_PATH,
            f"""---
updated: {today}
---

# 项目环境

## 基本信息
- 项目名称: {args.project_name or "~"}
- 工作目录: {os.getcwd()}
- 主要语言: ~
- 包管理器: ~

## 常用命令
- 启动: ~
- 测试: ~
- 构建: ~

## 注意事项
- ~
""",
        )

    if not os.path.exists(BACKLOG_PATH):
        _write(BACKLOG_PATH, f"# 任务 backlog\nupdated: {today}\n\n")

    if not os.path.exists(ARCHIVE_PATH):
        _write(ARCHIVE_PATH, f"# 任务归档\nupdated: {today}\n\n")

    if not os.path.exists(LESSONS_PATH):
        _write(LESSONS_PATH, f"# 经验教训\nupdated: {today}\n\n")

    if not os.path.exists(TECH_SPEC_PATH):
        _write(TECH_SPEC_PATH, f"# 技术决策\nupdated: {today}\n\n")

    print("Initialized .ai/ memory bank")


def cmd_task_create(args):
    _ensure_dirs()
    seq = _parse_backlog_max_seq() + 1
    tid = f"{args.prefix}-{seq:03d}"
    task_path = os.path.join(TASKS_DIR, f"{tid}.md")
    snap_path = os.path.join(SNAPSHOTS_DIR, f"{tid}.md")

    if os.path.exists(task_path):
        print(f"Error: task {tid} already exists", file=sys.stderr)
        sys.exit(1)

    today = _now()
    now = _now("%Y-%m-%d %H:%M")

    _write(
        task_path,
        f"""---
task_id: {tid}
task_name: {args.name}
created_at: {today}
status: in-progress
progress: 0%
---

## 目标
{args.name}

## 当前阶段
新建

## 待办
- [ ] 

## 决策记录

## 阻塞/依赖
~
""",
    )

    _write(
        snap_path,
        f"""---
task_id: {tid}
updated_at: {now}
---

focus:
  file: ~
  line: ~
  function: ~
  snippet: ~

context: []

next_action: ~
blocker: ~
""",
    )

    _append(BACKLOG_PATH, f"- {tid}: {args.name} 0% [新建]\n")
    print(tid)


def cmd_task_resume(args):
    task_path = os.path.join(TASKS_DIR, f"{args.id}.md")
    snap_path = os.path.join(SNAPSHOTS_DIR, f"{args.id}.md")

    if not os.path.exists(task_path):
        print(f"Error: task {args.id} not found", file=sys.stderr)
        sys.exit(1)

    tmeta, tbody = _parse_frontmatter(_read(task_path))
    smeta, sbody = _parse_frontmatter(_read(snap_path))

    # extract stage from body
    stage = "~"
    m = re.search(r"## 当前阶段\n(.+?)(?:\n\n|$)", tbody)
    if m:
        stage = m.group(1).strip()

    # parse snapshot yaml-ish fields
    focus_file = _yaml_extract(sbody, "focus", "file")
    focus_line = _yaml_extract(sbody, "focus", "line")
    focus_func = _yaml_extract(sbody, "focus", "function")
    next_action = _yaml_extract(sbody, "next_action")
    blocker = _yaml_extract(sbody, "blocker")
    ctx_count = len(re.findall(r"^  - file:", sbody, re.M))

    out = f"""task_id: {args.id}
task_name: {tmeta.get('task_name', '~')}
status: {tmeta.get('status', '~')}
stage: {stage}
progress: {tmeta.get('progress', '~')}
focus_file: {focus_file}
focus_line: {focus_line}
focus_function: {focus_func}
next_action: {next_action}
blocker: {blocker}
context_count: {ctx_count}
"""
    print(out.strip())


def _yaml_extract(body, *keys):
    text = body
    for key in keys:
        if key == "focus":
            return _extract_focus_field(body, keys[1]) if len(keys) > 1 else "~"
        pattern = rf"^{re.escape(key)}:\s*(.*?)$"
        m = re.search(pattern, text, re.M)
        if not m:
            return "~"
        text = m.group(1).strip()
    return text


def _extract_focus_field(body, field):
    m = re.search(r"^focus:\n((?:[ \t]+.*\n)+)", body, re.M)
    if not m:
        return "~"
    block = m.group(1)
    fm = re.search(rf"^[ \t]+{re.escape(field)}:\s*(.*?)$", block, re.M)
    return fm.group(1).strip() if fm else "~"


def _extract_context_block(body):
    m = re.search(r"^context:\n((?:[ \t]+.*\n)*)", body, re.M)
    if not m:
        return "  []"
    block = m.group(1).rstrip()
    return block if block else "  []"


def cmd_task_archive(args):
    today = _now()
    task_src = os.path.join(TASKS_DIR, f"{args.id}.md")
    snap_src = os.path.join(SNAPSHOTS_DIR, f"{args.id}.md")
    task_dst = os.path.join(TASKS_DIR, "archive", f"{args.id}.md.{today}")
    snap_dst = os.path.join(SNAPSHOTS_DIR, "archive", f"{args.id}.md.{today}")

    if os.path.exists(task_src):
        shutil.move(task_src, task_dst)
    if os.path.exists(snap_src):
        shutil.move(snap_src, snap_dst)

    # remove from backlog
    lines = _read(BACKLOG_PATH).splitlines(keepends=True)
    with open(BACKLOG_PATH, "w", encoding="utf-8") as f:
        for line in lines:
            if not line.startswith(f"- {args.id}:"):
                f.write(line)

    # append to archive
    _append(ARCHIVE_PATH, f"- {args.id}: 已完成归档 [{today}]\n")
    print(f"Archived {args.id}")


def cmd_checkpoint(args):
    task_path = os.path.join(TASKS_DIR, f"{args.id}.md")
    snap_path = os.path.join(SNAPSHOTS_DIR, f"{args.id}.md")

    if not os.path.exists(task_path):
        print(f"Error: task {args.id} not found", file=sys.stderr)
        sys.exit(1)

    now = _now("%Y-%m-%d %H:%M")

    # update task
    tmeta, tbody = _parse_frontmatter(_read(task_path))
    if args.progress is not None:
        tmeta["progress"] = f"{args.progress}%"
    tmeta["updated_at"] = _now()
    if args.stage is not None:
        tbody = _update_section(tbody, "当前阶段", args.stage)
    if args.todo is not None:
        tbody = _update_section(tbody, "待办", args.todo)
    _write(task_path, _build_frontmatter(tmeta) + "\n\n" + tbody.strip() + "\n")

    # read existing snapshot values
    smeta, sbody = _parse_frontmatter(_read(snap_path))
    smeta["updated_at"] = now

    file_val = args.file if args.file is not None else _yaml_extract(sbody, "focus", "file")
    line_val = args.line if args.line is not None else _yaml_extract(sbody, "focus", "line")
    func_val = args.function if args.function is not None else _yaml_extract(sbody, "focus", "function")
    snip_val = args.snippet if args.snippet is not None else _yaml_extract(sbody, "focus", "snippet")
    next_val = args.next_action if args.next_action is not None else _yaml_extract(sbody, "next_action")
    block_val = args.blocker if args.blocker is not None else _yaml_extract(sbody, "blocker")
    ctx_val = _format_context(args.context) if args.context is not None else _extract_context_block(sbody)

    snap_body = f"""focus:
  file: {file_val}
  line: {line_val}
  function: {func_val}
  snippet: {snip_val}

context:
{ctx_val}

next_action: {next_val}
blocker: {block_val}
"""
    if args.note:
        snap_body += f"\nnote: {args.note}\n"

    _write(snap_path, _build_frontmatter(smeta) + "\n\n" + snap_body)
    print(f"Checkpoint saved for {args.id}")


def _update_section(body, section_name, new_value):
    if new_value is None:
        return body
    pattern = rf"(## {re.escape(section_name)}\n)(.*?)(\n## |\Z)"
    replacement = f"## {section_name}\n{new_value}\n\n\\g<3>"
    result, count = re.subn(pattern, replacement, body, count=1, flags=re.S)
    if count == 0:
        # append if section missing
        result = body.rstrip() + f"\n\n## {section_name}\n{new_value}\n"
    return result


def _format_context(ctx_str):
    if not ctx_str:
        return "  []"
    lines = []
    for item in ctx_str.split(";"):
        parts = item.strip().split("|")
        if len(parts) >= 2:
            file = parts[0].strip()
            lines_range = parts[1].strip() if len(parts) > 1 else "~"
            relation = parts[2].strip() if len(parts) > 2 else "~"
            note = parts[3].strip() if len(parts) > 3 else "~"
            lines.append(f"  - file: {file}")
            lines.append(f"    lines: {lines_range}")
            lines.append(f"    relation: {relation}")
            lines.append(f"    note: {note}")
    if not lines:
        return "  []"
    return "\n".join(lines)


def cmd_lesson(args):
    today = _now()
    _append(LESSONS_PATH, f"- [{today}] {args.content}\n")
    print("Lesson recorded")


def cmd_tech(args):
    today = _now()
    _append(TECH_SPEC_PATH, f"\n## {args.title}\n\n- 日期: {today}\n- 内容: {args.content}\n")
    print("Tech spec recorded")


def cmd_env(args):
    if args.key is None:
        print(_read(ENV_PATH))
        return

    text = _read(ENV_PATH)
    meta, body = _parse_frontmatter(text)
    meta["updated"] = _now()

    # try to update existing key in body
    pattern = rf"^(\s*- {re.escape(args.key)}:\s*).*$"
    new_body, count = re.subn(pattern, rf"\g<1>{args.value}", body, flags=re.M, count=1)
    if count == 0:
        # append under 基本信息 if present, else append at end
        if "## 基本信息" in new_body:
            new_body = re.sub(
                r"(## 基本信息\n.*?)(\n## |\Z)",
                rf"\g<1>- {args.key}: {args.value}\n\n\g<2>",
                new_body,
                flags=re.S,
                count=1,
            )
        else:
            new_body = new_body.rstrip() + f"\n\n- {args.key}: {args.value}\n"

    _write(ENV_PATH, _build_frontmatter(meta) + "\n\n" + new_body.strip() + "\n")
    print(f"Updated env: {args.key} = {args.value}")


def main():
    parser = argparse.ArgumentParser(prog="harness", description="AI 任务记忆控制器")
    sub = parser.add_subparsers(dest="cmd")

    # init
    p_init = sub.add_parser("init", help="初始化 .ai/ 记忆库")
    p_init.add_argument("--project-name", default="")
    p_init.set_defaults(func=cmd_init)

    # task
    p_task = sub.add_parser("task", help="任务生命周期")
    task_sub = p_task.add_subparsers(dest="task_cmd")

    p_create = task_sub.add_parser("create", help="新建任务")
    p_create.add_argument("name")
    p_create.add_argument("--prefix", default="task")
    p_create.set_defaults(func=cmd_task_create)

    p_resume = task_sub.add_parser("resume", help="恢复任务")
    p_resume.add_argument("id")
    p_resume.set_defaults(func=cmd_task_resume)

    p_archive = task_sub.add_parser("archive", help="归档任务")
    p_archive.add_argument("id")
    p_archive.set_defaults(func=cmd_task_archive)

    # checkpoint
    p_ck = sub.add_parser("checkpoint", help="保存任务检查点")
    p_ck.add_argument("id")
    p_ck.add_argument("--stage", default=None)
    p_ck.add_argument("--progress", type=int, default=None)
    p_ck.add_argument("--todo", default=None)
    p_ck.add_argument("--file", default=None)
    p_ck.add_argument("--line", default=None)
    p_ck.add_argument("--function", default=None)
    p_ck.add_argument("--snippet", default=None)
    p_ck.add_argument("--next-action", default=None)
    p_ck.add_argument("--blocker", default=None)
    p_ck.add_argument("--note", default=None)
    p_ck.add_argument("--context", default=None)
    p_ck.set_defaults(func=cmd_checkpoint)

    # lesson
    p_lesson = sub.add_parser("lesson", help="记录经验教训")
    p_lesson.add_argument("content")
    p_lesson.set_defaults(func=cmd_lesson)

    # tech
    p_tech = sub.add_parser("tech", help="记录技术决策")
    p_tech.add_argument("--title", required=True)
    p_tech.add_argument("--content", required=True)
    p_tech.set_defaults(func=cmd_tech)

    # env
    p_env = sub.add_parser("env", help="查看/更新环境信息")
    p_env.add_argument("--key", default=None)
    p_env.add_argument("--value", default=None)
    p_env.set_defaults(func=cmd_env)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    if args.cmd == "task" and not args.task_cmd:
        p_task.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
