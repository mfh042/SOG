"""并发与并行基础设施。

设计目标（高并发装配现场）：
- 阻塞调用（同步库、外部 IO、批量 CPU 计算）放入后台线程池，避免阻塞事件循环；
- 可并发的异步任务用信号量限流，避免瞬间打爆 DB 连接池；
- 提供 asyncio.gather 批量分片执行工具，用于多工单 / 多物料并行处理。
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Iterable, List, TypeVar

from app.core.config import settings

T = TypeVar("T")

# 全局阻塞任务线程池（数量由 worker_threads 控制）
_thread_pool = ThreadPoolExecutor(
    max_workers=settings.worker_threads,
    thread_name_prefix="delv-sog-worker",
)

# 异步并发限流信号量
_semaphore = asyncio.Semaphore(settings.async_concurrency)


def run_in_threadpool(func: Callable[..., T], *args: Any, **kwargs: Any) -> Awaitable[T]:
    """把同步阻塞函数交给线程池执行，返回可 await 的协程。"""
    return asyncio.get_running_loop().run_in_executor(_thread_pool, func, *args, **kwargs)


async def gather_limited(tasks: List[Awaitable[T]], limit: int | None = None) -> List[T]:
    """带并发上限地执行一组协程。

    每个任务先拿信号量；未拿限时退化为 gather。
    """
    sem = asyncio.Semaphore(limit) if limit else _semaphore

    async def _wrap(task: Awaitable[T]) -> T:
        async with sem:
            return await task

    return await asyncio.gather(*[_wrap(t) for t in tasks], return_exceptions=False)


async def parallel_map(
    func: Callable[[T], Awaitable[Any]],
    items: Iterable[T],
    limit: int | None = None,
) -> List[Any]:
    """对可迭代元素并行映射，并发受限。"""
    return await gather_limited([func(item) for item in items], limit=limit)


def shutdown_threadpool() -> None:
    _thread_pool.shutdown(wait=True)