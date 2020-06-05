from asyncio import AbstractEventLoop

import pytest
from aiohttp import web


@pytest.fixture()
async def mocker_server(loop: AbstractEventLoop):
    """
    启动 mocker 服务器，并且生成器返回该访问地址
    port=0 操作系统会自动选择可用的端口
    https://stackoverflow.com/questions/2838244/get-open-tcp-port-in-python/2838309#2838309
    :param loop:
    :return:
    """
    # host = 'localhost'
    port = 0

    async def handler(request):
        return web.Response(text="OK")

    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    # site_task = loop.create_task(site.start())
    await site.start()
    host, port = site._server.sockets[0].getsockname()  # 获取socket实际绑定端口
    server_addr = f'http://{host}:{port}'
    yield server_addr  # 返回访问地址
    await runner.cleanup()
