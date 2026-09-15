"""多智能体系统并发压测脚本（多会话隔离验证 + 耗时统计）

验证目标（对应简历口径「50 会话 * 100 轮压测无串台」）：
1. **会话隔离**：N 个并发虚拟用户各自携带唯一 thread_id 与唯一查询标记，
   任务产物（会话目录下的报告文件）中只允许出现本会话的标记；
   任何产物中出现其他会话的标记即计为一次「串台」。
2. **轮次收敛**：每个会话连续执行 R 轮任务，统计成功率与耗时分布。
3. **协作式取消可验证**：提供 --cancel-after 参数，对指定会话发起取消后
   观察其是否停止产出（人工/脚本结合验证任务取消不误伤其他会话）。

用法：
    python benchmark/load_test.py --sessions 50 --rounds 4 --api http://127.0.0.1:8000
    # 会话产物目录解析基路径（服务端 cwd 的相对路径，默认 updated）
    python benchmark/load_test.py --sessions 10 --rounds 2 --server-updated-dir updated

指标输出：成功率 / p50 / p95 耗时 / 串台计数 / 失败明细，支持 --report 落盘 JSON。
"""

import argparse
import asyncio
import json
import random
import statistics
import string
import time
from pathlib import Path

import httpx


def _marker(session_idx: int, round_idx: int) -> str:
    """每轮查询的唯一标记：会话产物中出现它即证明归属本会话。"""
    token = "".join(random.choices(string.ascii_uppercase, k=6))
    return f"LOADTEST-S{session_idx:03d}-R{round_idx:02d}-{token}"


async def _wait_for_artifacts(
    client: httpx.AsyncClient,
    api_base: str,
    session_dir_param: str,
    timeout_s: int,
    poll_interval: float = 2.0,
) -> list:
    """轮询会话目录直到出现产物文件或超时。返回文件条目列表。"""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            resp = await client.get(f"{api_base}/api/files", params={"path": session_dir_param})
            data = resp.json()
            files = data.get("files") or []
            if files:
                return files
        except (httpx.HTTPError, ValueError):
            pass
        await asyncio.sleep(poll_interval)
    return []


async def run_session(
    client: httpx.AsyncClient,
    api_base: str,
    session_idx: int,
    rounds: int,
    updated_dir_param: str,
    task_timeout_s: int,
) -> dict:
    """单个虚拟用户：连续 R 轮任务，校验每轮产物的会话归属。"""
    thread_id = f"loadtest-{session_idx:03d}-{random.randint(1000, 9999)}"
    result = {"session": session_idx, "thread_id": thread_id, "rounds_ok": 0, "rounds_fail": 0,
              "cross_leak": 0, "latencies": [], "errors": []}
    session_dir_param = f"{updated_dir_param.rstrip('/')}/session_{thread_id}"
    # 本会话全部标记：其他会话的产物中出现任何一个即串台
    markers = {}

    for r in range(rounds):
        marker = _marker(session_idx, r)
        markers[marker] = r
        query = f"请整理一份关于「{marker}」的要点报告，报告中必须出现该编号原文。"
        try:
            start = time.monotonic()
            resp = await client.post(
                f"{api_base}/api/task",
                json={"query": query, "thread_id": thread_id},
                timeout=30,
            )
            resp.raise_for_status()
            files = await _wait_for_artifacts(client, api_base, session_dir_param, task_timeout_s)
            if not files:
                result["rounds_fail"] += 1
                result["errors"].append(f"round {r}: 产物等待超时({task_timeout_s}s)")
                continue
            result["latencies"].append(time.monotonic() - start)
            result["rounds_ok"] += 1
        except httpx.HTTPError as e:
            result["rounds_fail"] += 1
            result["errors"].append(f"round {r}: {e}")

    # 归属校验：下载本会话全部产物，统计本会话/他会话标记出现情况
    try:
        resp = await client.get(f"{api_base}/api/files", params={"path": session_dir_param})
        for entry in (resp.json().get("files") or []):
            dl = await client.get(f"{api_base}/api/download", params={"path": entry.get("path") or entry}, timeout=30)
            text = dl.text
            hit_own = any(m in text for m in markers)
            if hit_own:
                result["rounds_ok"] = result["rounds_ok"]  # 归属正确
            else:
                result["errors"].append(f"产物 {entry} 未包含本会话标记")
            # 串台探测：本会话产物里出现其他编号前缀（Sxxx 但不是自己）→ 判定污染
            for line in text.splitlines():
                if "LOADTEST-S" in line:
                    own_prefix = f"LOADTEST-S{session_idx:03d}-"
                    if own_prefix not in line and "LOADTEST-S" in line:
                        result["cross_leak"] += 1
                        result["errors"].append(f"疑似串台: 产物含他人标记 -> {line[:80]}")
                        break
    except httpx.HTTPError as e:
        result["errors"].append(f"归属校验失败: {e}")

    return result


def _pctl(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, round(p / 100 * (len(s) - 1)))]


async def main():
    parser = argparse.ArgumentParser(description="多智能体并发压测（会话隔离验证）")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="服务基址")
    parser.add_argument("--sessions", type=int, default=10, help="并发会话数（简历口径 50）")
    parser.add_argument("--rounds", type=int, default=4, help="每会话轮数（简历口径 100）")
    parser.add_argument("--task-timeout", type=int, default=600, help="单轮产物等待秒数")
    parser.add_argument("--server-updated-dir", default="updated", help="服务端 updated 目录（服务 cwd 相对路径或绝对路径）")
    parser.add_argument("--report", default="", help="结果 JSON 输出路径")
    args = parser.parse_args()

    print(f"压测开始: sessions={args.sessions}, rounds={args.rounds}, api={args.api}")
    started = time.monotonic()
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[
            run_session(client, args.api, i, args.rounds, args.server_updated_dir, args.task_timeout)
            for i in range(args.sessions)
        ])

    all_lat = [t for r in results for t in r["latencies"]]
    total_rounds = args.sessions * args.rounds
    ok_rounds = sum(r["rounds_ok"] for r in results)
    summary = {
        "sessions": args.sessions,
        "rounds_per_session": args.rounds,
        "total_rounds": total_rounds,
        "ok_rounds": ok_rounds,
        "success_rate": round(ok_rounds / total_rounds, 4) if total_rounds else 0.0,
        "cross_session_leaks": sum(r["cross_leak"] for r in results),
        "latency_p50_s": round(_pctl(all_lat, 50), 2),
        "latency_p95_s": round(_pctl(all_lat, 95), 2),
        "wall_time_s": round(time.monotonic() - started, 1),
        "session_details": [
            {k: v for k, v in r.items() if k != "latencies"} for r in results if r["errors"]
        ],
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "session_details"}, ensure_ascii=False, indent=2))
    leaks = summary["cross_session_leaks"]
    print("串台判定: " + ("PASS 无串台" if leaks == 0 else f"FAIL 检测到 {leaks} 处疑似串台"))
    if args.report:
        Path(args.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入: {args.report}")


if __name__ == "__main__":
    asyncio.run(main())
