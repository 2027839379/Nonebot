import asyncio
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Union

import ujson as json
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

from configs.config import Config
from configs.path_config import DATA_PATH, IMAGE_PATH
from models.group_member_info import GroupInfoUser
from models.level_user import LevelUser
from services.log import logger
from utils.http_utils import AsyncHttpx
from utils.image_utils import BuildImage
from utils.manager import group_manager, plugins2settings_manager, plugins_manager
from utils.message_builder import image
from utils.typing import BLOCK_TYPE
from utils.utils import get_matchers

CUSTOM_WELCOME_FILE = Path() / "data" / "custom_welcome_msg" / "custom_welcome_msg.json"
CUSTOM_WELCOME_FILE.parent.mkdir(parents=True, exist_ok=True)

ICON_PATH = IMAGE_PATH / "other"

GROUP_HELP_PATH = DATA_PATH / "group_help"


async def group_current_status(group_id: str) -> str:
    """
    说明:
        获取当前群聊所有通知的开关
    参数:
        :param group_id: 群号
    """
    _data = group_manager.get_task_data()
    image_list = []
    for i, task in enumerate(_data):
        name = _data[task]
        name_image = BuildImage(0, 0, plain_text=f"{i+1}.{name}", font_size=20)
        bk = BuildImage(
            name_image.w + 200, name_image.h + 20, color=(103, 177, 109), font_size=15
        )
        await bk.apaste(name_image, (10, 0), True, "by_height")
        a_icon = BuildImage(40, 40, background=ICON_PATH / "btn_false.png")
        if group_manager.check_group_task_status(group_id, task):
            a_icon = BuildImage(40, 40, background=ICON_PATH / "btn_true.png")
        b_icon = BuildImage(40, 40, background=ICON_PATH / "btn_false.png")
        if group_manager.check_task_super_status(task):
            b_icon = BuildImage(40, 40, background=ICON_PATH / "btn_true.png")
        await bk.atext((name_image.w + 20, 10), "状态")
        await bk.apaste(a_icon, (name_image.w + 50, 0), True)
        await bk.atext((name_image.w + 100, 10), "全局")
        await bk.apaste(b_icon, (name_image.w + 130, 0), True)
        image_list.append(bk)
    w = max([x.w for x in image_list])
    h = sum([x.h + 10 for x in image_list])
    A = BuildImage(w + 20, h + 70, font_size=30, color=(119, 97, 177))
    await A.atext((15, 20), "群被动状态")
    curr_h = 75
    for img in image_list:
        # await img.acircle_corner()
        await A.apaste(img, (0, curr_h), True)
        curr_h += img.h + 10
    return A.pic2bs4()


async def custom_group_welcome(
    msg: str, img_list: List[str], user_id: str, group_id: str
) -> Union[str, Message]:
    """
    说明:
        替换群欢迎消息
    参数:
        :param msg: 欢迎消息文本
        :param img_list: 欢迎消息图片
        :param user_id: 用户id，用于log记录
        :param group_id: 群号
    """
    img_result = ""
    result = ""
    img = img_list[0] if img_list else ""
    msg_image = DATA_PATH / "custom_welcome_msg" / f"{group_id}.jpg"
    if msg_image.exists():
        msg_image.unlink()
    data = {}
    if CUSTOM_WELCOME_FILE.exists():
        data = json.load(CUSTOM_WELCOME_FILE.open("r", encoding="utf8"))
    try:
        if msg:
            data[group_id] = msg
            json.dump(
                data,
                CUSTOM_WELCOME_FILE.open("w", encoding="utf8"),
                indent=4,
                ensure_ascii=False,
            )
            logger.info(f"更换群欢迎消息 {msg}", "更换群欢迎信息", user_id, group_id)
            result += msg
        if img:
            await AsyncHttpx.download_file(img, msg_image)
            img_result = image(msg_image)
            logger.info(f"更换群欢迎消息图片", "更换群欢迎信息", user_id, group_id)
    except Exception as e:
        logger.error(f"替换群消息失败", "更换群欢迎信息", user_id, group_id, e=e)
        return "替换群消息失败..."
    return f"替换群欢迎消息成功：\n{result}" + img_result


task_data = None


def change_global_task_status(cmd: str) -> str:
    """
    说明:
        修改全局被动任务状态
    参数:
        :param cmd: 功能名称
    """
    global task_data
    if not task_data:
        task_data = group_manager.get_task_data()
    status = cmd[:2]
    _cmd = cmd[4:]
    if "全部被动" in cmd:
        for task in task_data:
            if status == "开启":
                group_manager.open_global_task(task)
            else:
                group_manager.close_global_task(task)
        group_manager.save()
        return f"已 {status} 全局全部被动技能！"
    else:
        modules = [x for x in task_data if task_data[x].lower() == _cmd.lower()]
        if not modules:
            return "未查询到该被动任务"
        if status == "开启":
            group_manager.open_global_task(modules[0])
        else:
            group_manager.close_global_task(modules[0])
        group_manager.save()
        return f"已 {status} 全局{_cmd}"


async def change_group_switch(cmd: str, group_id: str, is_super: bool = False) -> str:
    """
    说明:
        修改群功能状态
    参数:
        :param cmd: 功能名称
        :param group_id: 群号
        :param is_super: 是否为超级用户，超级用户用于私聊开关功能状态
    """
    global task_data
    if not task_data:
        task_data = group_manager.get_task_data()
    help_path = GROUP_HELP_PATH / f"{group_id}.png"
    status = cmd[:2]
    cmd = cmd[2:]
    type_ = "plugin"
    modules = plugins2settings_manager.get_plugin_module(cmd, True)
    if cmd == "全部被动":
        for task in task_data:
            if status == "开启":
                if not group_manager.check_group_task_status(group_id, task):
                    group_manager.open_group_task(group_id, task)
            else:
                if group_manager.check_group_task_status(group_id, task):
                    group_manager.close_group_task(group_id, task)
        if help_path.exists():
            help_path.unlink()
        return f"已 {status} 全部被动技能！"
    if cmd == "全部功能":
        for f in plugins2settings_manager.get_data():
            if status == "开启":
                group_manager.unblock_plugin(f, group_id, False)
            else:
                group_manager.block_plugin(f, group_id, False)
        group_manager.save()
        if help_path.exists():
            help_path.unlink()
        return f"已 {status} 全部功能！"
    if cmd.lower() in [task_data[x].lower() for x in task_data.keys()]:
        type_ = "task"
        modules = [x for x in task_data.keys() if task_data[x].lower() == cmd.lower()]
    for module in modules:
        if is_super:
            module = f"{module}:super"
        if status == "开启":
            if type_ == "task":
                if group_manager.check_group_task_status(group_id, module):
                    return f"被动 {task_data[module]} 正处于开启状态！不要重复开启."
                group_manager.open_group_task(group_id, module)
            else:
                if group_manager.get_plugin_status(module, group_id):
                    return f"功能 {cmd} 正处于开启状态！不要重复开启."
                group_manager.unblock_plugin(module, group_id)
        else:
            if type_ == "task":
                if not group_manager.check_group_task_status(group_id, module):
                    return f"被动 {task_data[module]} 正处于关闭状态！不要重复关闭."
                group_manager.close_group_task(group_id, module)
            else:
                if not group_manager.get_plugin_status(module, group_id):
                    return f"功能 {cmd} 正处于关闭状态！不要重复关闭."
                group_manager.block_plugin(module, group_id)
    if help_path.exists():
        help_path.unlink()
    if is_super:
        for file in os.listdir(GROUP_HELP_PATH):
            file = GROUP_HELP_PATH / file
            file.unlink()
    else:
        if help_path.exists():
            help_path.unlink()
    return f"{status} {cmd} 功能！"


def set_plugin_status(cmd: str, block_type: BLOCK_TYPE = "all"):
    """
    说明:
        设置插件功能状态（超级用户使用）
    参数:
        :param cmd: 功能名称
        :param block_type: 限制类型, 'all': 全局, 'private': 私聊, 'group': 群聊
    """
    if block_type not in ["all", "private", "group"]:
        raise TypeError("block_type类型错误, 可选值: ['all', 'private', 'group']")
    status = cmd[:2]
    cmd = cmd[2:]
    module = plugins2settings_manager.get_plugin_module(cmd)
    if status == "开启":
        plugins_manager.unblock_plugin(module)
    else:
        plugins_manager.block_plugin(module, block_type=block_type)
    for file in os.listdir(GROUP_HELP_PATH):
        file = GROUP_HELP_PATH / file
        file.unlink()


async def get_plugin_status():
    """
    说明:
        获取功能状态
    """
    return await asyncio.get_event_loop().run_in_executor(None, _get_plugin_status)


def _get_plugin_status() -> MessageSegment:
    """
    说明:
        合成功能状态图片
    """
    rst = "\t功能\n"
    flag_str = "状态".rjust(4) + "\n"
    for matcher in get_matchers(True):
        if module := matcher.plugin_name:
            flag = plugins_manager.get_plugin_block_type(module)
            flag = flag.upper() + " CLOSE" if flag else "OPEN"
            try:
                plugin_name = plugins_manager.get(module).plugin_name
                if (
                    "[Hidden]" in plugin_name
                    or "[Admin]" in plugin_name
                    or "[Superuser]" in plugin_name
                ):
                    continue
                rst += f"{plugin_name}"
            except KeyError:
                rst += f"{module}"
            if plugins_manager.get(module).error:
                rst += "[ERROR]"
            rst += "\n"
            flag_str += f"{flag}\n"
    height = len(rst.split("\n")) * 24
    a = BuildImage(250, height, font_size=20)
    a.text((10, 10), rst)
    b = BuildImage(200, height, font_size=20)
    b.text((10, 10), flag_str)
    A = BuildImage(500, height)
    A.paste(a)
    A.paste(b, (270, 0))
    return image(b64=A.pic2bs4())


async def update_member_info(
    bot: Bot, group_id: int, remind_superuser: bool = False
) -> bool:
    """
    说明:
        更新群成员信息
    参数:
        :param group_id: 群号
        :param remind_superuser: 失败信息提醒超级用户
    """
    _group_user_list = await bot.get_group_member_list(group_id=group_id)
    _error_member_list = []
    _exist_member_list = []
    # try:
    admin_default_auth = Config.get_config("admin_bot_manage", "ADMIN_DEFAULT_AUTH")
    if admin_default_auth is not None:
        for user_info in _group_user_list:
            nickname = user_info["card"] or user_info["nickname"]
            # 更新权限
            if user_info["role"] in [
                "owner",
                "admin",
            ] and not await LevelUser.is_group_flag(
                user_info["user_id"], str(group_id)
            ):
                await LevelUser.set_level(
                    user_info["user_id"],
                    user_info["group_id"],
                    admin_default_auth,
                )
            if str(user_info["user_id"]) in bot.config.superusers:
                await LevelUser.set_level(
                    user_info["user_id"], user_info["group_id"], 9
                )
            user = await GroupInfoUser.get_or_none(
                user_id=str(user_info["user_id"]), group_id=str(user_info["group_id"])
            )
            if user:
                if user.user_name != nickname:
                    user.user_name = nickname
                    await user.save(update_fields=["user_name"])
                    logger.debug(
                        f"更新群昵称成功",
                        "更新群组成员信息",
                        user_info["user_id"],
                        user_info["group_id"],
                    )
                _exist_member_list.append(str(user_info["user_id"]))
                continue
            join_time = datetime.strptime(
                time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(user_info["join_time"])
                ),
                "%Y-%m-%d %H:%M:%S",
            )
            await GroupInfoUser.update_or_create(
                user_id=str(user_info["user_id"]),
                group_id=str(user_info["group_id"]),
                defaults={
                    "user_name": nickname,
                    "user_join_time": join_time.replace(
                        tzinfo=timezone(timedelta(hours=8))
                    ),
                },
            )
            _exist_member_list.append(str(user_info["user_id"]))
            logger.debug("更新成功", "更新成员信息", user_info["user_id"], user_info["group_id"])
        _del_member_list = list(
            set(_exist_member_list).difference(
                set(await GroupInfoUser.get_group_member_id_list(group_id))
            )
        )
        if _del_member_list:
            for del_user in _del_member_list:
                await GroupInfoUser.filter(
                    user_id=str(del_user), group_id=str(group_id)
                ).delete()
                logger.info(f"删除已退群用户", "更新群组成员信息", del_user, group_id)
        if _error_member_list and remind_superuser:
            result = ""
            for error_user in _error_member_list:
                result += error_user
            await bot.send_private_msg(
                user_id=int(list(bot.config.superusers)[0]), message=result[:-1]
            )
    return True


def set_group_bot_status(group_id: str, status: bool) -> str:
    """
    说明:
        设置群聊bot开关状态
    参数:
        :param group_id: 群号
        :param status: 状态
    """
    if status:
        if group_manager.check_group_bot_status(group_id):
            return "笨蛋，我还没有休息呢！"
        group_manager.turn_on_group_bot_status(group_id)
        return "来了来了，又打扰我休息😴...哼"
    else:
        group_manager.shutdown_group_bot_status(group_id)
        return "那我先休息了哦...拜拜"
