"""
bilibili_api.channel

频道相关，与视频分区不互通。
"""
from bilibili_api.utils.short import get_real_url
from bilibili_api.utils.network_httpx import request, get_session
from bilibili_api.utils.utils import get_api
from bilibili_api.utils.Credential import Credential
from bilibili_api.errors import ResponseException, ApiException
import re
import json
from enum import Enum
from typing import Optional, List, Union

API = get_api("channel")


async def pick_window_INITIAL_STATE(url: str, credential: Optional[Credential] = None) -> dict:
    credential = credential if credential else Credential()
    session = get_session()

    try:
        resp = await session.get(
            url,
            cookies=credential.get_cookies(),
            headers={"User-Agent": "Mozilla/5.0"}
        )
    except Exception as e:
        raise ResponseException(str(e))
    else:
        content = resp.text

        pattern = re.compile(r"window.__INITIAL_STATE__=(\{.*?\});")
        match = re.search(pattern, content)
        if match is None:
            raise ApiException("未找到相关信息")
        try:
            content = json.loads(match.group(1))
        except json.JSONDecodeError:
            raise ApiException("信息解析错误")
        return content


async def get_channel_categories() -> dict:
    """
    获取所有的频道分类（如游戏、鬼畜等）。

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["categories"]["list"]
    return await request(
        "GET",
        api["url"]
    )


async def get_channel_category_detail(category_id: int, offset: str = "0", credential: Optional[Credential] = None) -> dict:
    """
    获取频道分类的频道列表及其详细信息

    Args:
        category_id (int): 频道分类的 id。
        offset      (str): 偏移值（下面的数据的第一个频道 ID，为该请求结果中的 offset 键对应的值），类似单向链表. Defaults to "0"
    """
    credential = credential if credential else Credential()
    api = API["categories"]["sub_channels"]
    params = {
        "id": category_id,
        "offset": offset
    }
    return await request(
        "GET",
        api["url"],
        params=params,
        credential=credential
    )


class ChannelVideosOrder(Enum):
    """
    频道视频排序方式。

    - NEW: 最新
    - HOT: 最火
    - VIEW: 播放量最高
    """
    NEW = "?sort_type=new"
    HOT = "?sort_type=hot"
    VIEW = "?sort_type=view"


class ChannelVideosFilter(Enum):
    """
    频道视频筛选条件

    - ALL     : 全部
    - YEAR_年份: 指定年份筛选
    """
    ALL = "?filter_type="
    YEAR_2023 = "?filter_type=2023"
    YEAR_2022 = "?filter_type=2022"
    YEAR_2021 = "?filter_type=2021"
    YEAR_2020 = "?filter_type=2020"
    YEAR_2019 = "?filter_type=2019"
    YEAR_2018 = "?filter_type=2018"
    YEAR_2017 = "?filter_type=2017"
    YEAR_2016 = "?filter_type=2016"
    YEAR_2015 = "?filter_type=2015"
    YEAR_2014 = "?filter_type=2014"
    YEAR_2013 = "?filter_type=2013"
    YEAR_2012 = "?filter_type=2012"
    YEAR_2011 = "?filter_type=2011"


class Channel:
    """
    频道类。
    """
    def __init__(self, channel_id: int):
        """
        Args:
            channel_id (int): 频道 id.
        """
        self.__channel_id = channel_id

    def get_channel_id(self) -> int:
        return self.__channel_id

    async def get_info(self) -> dict:
        """
        获取频道详细信息

        Returns:
            dict: HTML 中 window.__INITIAL_STATE__ 中的信息
        """
        return await pick_window_INITIAL_STATE(
            await get_real_url(f"https://www.bilibili.com/v/channel/{self.get_channel_id()}") # type: ignore
        )

    async def get_related_channels(self) -> List[dict]:
        """
        获取相关频道

        Returns:
            dict: HTML 中 window.__INITIAL_STATE__ 中的信息
        """
        return (await self.get_info())["channelDetailBanner"]["data"]["tag_channels"]

    async def get_list(
        self,
        order_or_filter: Union[ChannelVideosOrder, ChannelVideosFilter, None] = None,
        offset: str = "",
        page_size: int = 30
    ) -> dict:
        """
        获取频道的所有视频

        Args:
            order_or_filter (ChannelVideosOrder | ChannelVideosFilter | None): 获取视频的相关选项
            offset          (str)                                            : 偏移值（下面的第一个视频的 ID，为该请求结果中的 offset 键对应的值），类似单向链表. Defaults to ""
            page_size       (int)                                            : 每页的数据大小. Defaults to 30.

        Returns:
            dict: 调用 API 返回的结果
        """
        api = API["channel"]["list_filter"]
        if isinstance(order_or_filter, ChannelVideosOrder):
            api = API["channel"]["list_multiple"]
        if isinstance(order_or_filter, Enum):
            api["url"] += order_or_filter.value
        params = {
            "channel_id": self.get_channel_id(),
            "offset": offset,
            "page_size": page_size
        }
        return await request(
            "GET", api["url"], params=params
        )



async def get_channels_in_category(category_id: int) -> List["Channel"]:
    """
    获取频道分类中的所有频道。

    Args:
        category_id (int): 频道 id

    Returns:
        List[Channel]: 频道分类中的所有频道。
    """
    channel_list = []
    offset = "0"
    while True:
        raw_data = await get_channel_category_detail(category_id=category_id, offset=offset)
        channel_list += raw_data["archive_channels"]
        if not raw_data["has_more"]:
            break
        else:
            offset = raw_data["offset"]
    channel_objects = []
    for channel in channel_list:
        channel_objects.append(
            Channel(channel["id"])
        )
    return channel_objects


async def get_self_subscribe_channels(credential: Credential) -> dict:
    """
    获取自己订阅的频道

    Args:
        credential (Credential): 凭据类

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["self_subscribes"]["list"]
    return await request(
        "GET",
        api["url"],
        credential=credential
    )


async def subscribe_channel(channel: Channel, credential: Credential) -> dict:
    """
    订阅频道

    Args:
        channel    (Channel)   : 要订阅的频道
        credential (Credential): 凭据类

    Returns:
        dict: 调用 API 返回的结果
    """
    api = API["channel"]["subscribe"]
    params = {
        "id": channel.get_channel_id()
    }
    return await request(
        "POST",
        api["url"],
        data=params,
        credential=credential
    )
