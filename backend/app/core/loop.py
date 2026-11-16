"""Windows 兼容的事件循环工厂。

psycopg3 异步驱动不支持 ProactorEventLoop，而 uvicorn 在 Windows 上默认
返回 ProactorEventLoop。通过 uvicorn --loop 指向本模块，强制使用
SelectorEventLoop。

用法：uvicorn app.main:app --loop app.core.loop:selector_loop_factory

注意：uvicorn 的 Config.get_loop_factory() 会调用本函数并直接把返回值当作
事件循环实例使用，因此这里必须返回已创建的 loop 对象。
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable


def selector_loop_factory(use_subprocess: bool = False) -> Callable[[], asyncio.AbstractEventLoop]:
    return asyncio.SelectorEventLoop()