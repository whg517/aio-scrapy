import pytest
from aiohttp import ClientSession


@pytest.mark.asyncio
async def test(mocker_server):
    """
    测试 mover_server 是否可用。
    :param mocker_server:
    :return:
    """
    async with ClientSession() as session:
        async with session.get(mocker_server) as response:
            assert response.status == 200
            text = await response.text()
            assert text == 'OK'
