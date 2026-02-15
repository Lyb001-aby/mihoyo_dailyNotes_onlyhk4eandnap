"""
米游社功能函数 - 游戏角色信息获取
注意：凭证（gameroles是stoken，便笺是ltoken_v2和cookie_token_v2等等一系列其余cookies
目前看来崩铁对ds验证非常严格，没找到对应salt，一直返回10001（非法请求），希望大佬能改进
"""

import json
import time
import random
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union


# ==================== DS签名生成器 ====================
class DSGenerator:
    """DS签名生成器 - 与米哈游登录管理器保持一致"""
    
    @staticmethod
    def generate_ds_nobodyandquery(param_type=3, body=None, query=""):
        """
        生成DS签名
        salt: dDIQHbKOdaPaLuvQKVzUzqdeCaxjtaPV (v2.90.1)
        """
        salt = "dDIQHbKOdaPaLuvQKVzUzqdeCaxjtaPV"
        
        t = str(int(time.time()))
        r = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        
        sign_str = f"salt={salt}&t={t}&r={r}"
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        
        return f"{t},{r},{sign}"

    @staticmethod
    def generate_ds(param_type=3, body=None, query=""):  #便笺全部使用ds2签名
        salt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"  #这个salt不确定，希望大佬能修改
        
        t = str(int(time.time()))
        r = random.randint(100001,200000)  #api文档特别声明如果随机到100000要加542367，所以直接跳过100000
        
        # 处理body
        b = ""
        if body:
            if isinstance(body, dict):
                b = json.dumps(body, separators=(',', ':'), ensure_ascii=False)
            else:
                b = str(body)
        
        # 处理query - 需要排序
        q = ""
        if query:
            if isinstance(query, dict):
                # 如果是字典，按键排序
                sorted_params = sorted([f"{k}={v}" for k, v in query.items()])
                q = '&'.join(sorted_params)
            elif isinstance(query, str) and query:
                # 如果是字符串，按参数名排序
                params = query.split('&')
                sorted_params = sorted(params)
                q = '&'.join(sorted_params)
        
        # 构建签名字符串: salt + t + r + b + q
        sign_str = f"{salt}{t}{r}{b}{q}"
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        
        return f"{t},{r},{sign}"


# ==================== 游戏角色信息获取 ====================

# 游戏名称映射
GAME_BIZ_MAP = {
    'hk4e_cn': '原神',
    'hkrpg_cn': '崩坏：星穹铁道',
    'nap_cn': '绝区零',
    'bh3_cn': '崩坏3',
    'bh3_global': '崩坏3(国际)',
    'nobu_cn': '未定事件簿',
}

# 游戏ID映射
GAME_ID_MAP = {
    'hk4e_cn': 1,      # 原神
    'hkrpg_cn': 6,     # 崩坏：星穹铁道
    'nap_cn': 8,       # 绝区零
    'bh3_cn': 2,       # 崩坏3
    'nobu_cn': 4,      # 未定事件簿
}


def get_user_game_roles(login_manager) -> Tuple[bool, Union[List[Dict], str]]:
    """
    从MihoyoLoginManager实例获取游戏角色信息
    
    使用manager中已保存的凭证：
    - manager.stoken
    - manager.mid
    - manager.account_id
    - manager.device_id2 / device_fp2 (手机端设备)
    
    参数:
        login_manager: MihoyoLoginManager 实例
    
    返回:
        (success, result)
        success: 是否成功
        result: 成功时返回角色列表，失败时返回错误信息
    """
    
    # 1. 检查登录状态
    if not login_manager:
        return False, "LoginManager实例为空"
    
    if not login_manager.stoken or not login_manager.mid:
        return False, "缺少SToken或MID，请先登录"
    
    # 2. 准备请求参数
    url = "https://api-takumi.miyoushe.com/binding/api/getUserGameRolesByStoken"
    
    # 3. 构建Cookie字符串
    cookie_parts = [
        f"stuid={login_manager.account_id}",
        f"stoken={login_manager.stoken}",
        f"mid={login_manager.mid};"
    ]
    
    cookie_str = ";".join(cookie_parts)
    
    # 4. 获取设备信息 - 优先使用手机端设备
    device_id = None
    device_fp = None
    
    if hasattr(login_manager, 'device_id2') and login_manager.device_id2:
        device_id = login_manager.device_id2
        device_fp = login_manager.device_fp2
    elif hasattr(login_manager, 'device_id1') and login_manager.device_id1:
        device_id = login_manager.device_id1
        device_fp = login_manager.device_fp1
    
    if not device_id or not device_fp:
        return False, "缺少设备信息"
    
    # 5. 生成DS签名
    ds = DSGenerator.generate_ds_nobodyandquery(param_type=3, query="")
    
    # 6. 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 miHoYoBBS/2.90.1 Capture/1.0.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Cookie': cookie_str,
        'x-rpc-device_id': device_id,
        'x-rpc-device_fp': device_fp,
        'x-rpc-app_id': 'bll8iq97cem8',
        'x-rpc-client_type': '5',  #必须是5！（其他端）
        'x-rpc-device_name': 'Mihoyo Capture',
        'x-rpc-device_model': 'Mi 14',
        'x-rpc-app_version': '2.90.1',
        'x-rpc-sdk_version': '2.35.1',
        'x-rpc-verify_key': 'bll8iq97cem8',
        'DS': ds,
        'Referer': 'https://app.mihoyo.com',
        'Accept-Language': 'zh-cn',
    }
    print(headers)
    # 7. 发送请求
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            verify=True
        )
        
        if response.status_code != 200:
            return False, f"HTTP错误: {response.status_code}"
        
        result = response.json()
        print(result)
        if result.get('retcode') == 0:
            roles = result.get('data', {}).get('list', [])
            
            # 处理角色数据，添加游戏名称
            for role in roles:
                game_biz = role.get('game_biz', '')
                role['game_name'] = GAME_BIZ_MAP.get(game_biz, game_biz)
                role['game_id'] = GAME_ID_MAP.get(game_biz, 0)
                
                # 添加服务器名称
                region = role.get('region', '')
                if region in REGION_NAME_MAP:
                    if game_biz=='hkrpg_cn':
                        role['region_display'] = '星穹列车'
                    elif game_biz=='nap_cn':
                        role['region_display'] = '新艾利都'
                    else:
                        role['region_display'] = REGION_NAME_MAP[region]
                else:
                    role['region_display'] = region
            
            return True, roles
        else:
            err_msg = result.get('message', f'API错误: {result.get("retcode")}')
            return False, err_msg
            
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "网络连接错误"
    except Exception as e:
        return False, f"请求异常: {str(e)}"


# 服务器名称映射
REGION_NAME_MAP = {
    'cn_gf01': '天空岛',
    'cn_qd01': '世界树',
    'prod_gf_cn': '星穹列车/新艾利都',
    'prod_qd_cn': '星穹列车(渠道)',
}


def get_user_game_roles_simple(login_manager) -> Tuple[bool, Union[str, List[Dict]]]:
    """
    获取简化版的游戏角色信息（只返回用户名和UID）
    
    参数:
        login_manager: MihoyoLoginManager 实例
    
    返回:
        (success, result)
        success: 是否成功
        result: 成功时返回简化角色列表，失败时返回错误信息
    """
    success, result = get_user_game_roles(login_manager)
    
    if not success:
        return False, result
    
    # 简化角色信息
    simple_roles = []
    for role in result:
        simple_roles.append({
            'game_name': role.get('game_name', role.get('game_biz', '未知')),
            'nickname': role.get('nickname', '未知'),
            'uid': role.get('game_uid', ''),
            'level': role.get('level', 0),
            'region': role.get('region_display', role.get('region', '')),
            'is_chosen': role.get('is_chosen', False)
        })
    
    return True, simple_roles


def format_roles_text(roles: List[Dict]) -> str:
    """
    将角色列表格式化为可读文本
    
    参数:
        roles: 角色列表
    
    返回:
        格式化的文本
    """
    if not roles:
        return "暂无绑定的游戏角色"
    
    lines = []
    lines.append("=" * 50)
    lines.append("🎮 已绑定的游戏角色")
    lines.append("=" * 50)
    
    for role in roles:
        game_name = role.get('game_name', role.get('game_biz', '未知游戏'))
        nickname = role.get('nickname', '未知')
        uid = role.get('uid', role.get('game_uid', '无UID'))
        level = role.get('level', 0)
        region = role.get('region_display', role.get('region', ''))
        chosen = role.get('is_chosen', False)
        
        lines.append(f"\n📱 {game_name}")
        lines.append(f"  昵称: {nickname}")
        lines.append(f"  UID: {uid}")
        lines.append(f"  等级: {level}")
        if region:
            lines.append(f"  服务器: {region}")
        if chosen:
            lines.append(f"  ✅ 默认展示")
    
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)


def get_user_game_roles_by_game(login_manager, game_biz: str = None) -> Tuple[bool, Union[List[Dict], str]]:
    """
    获取指定游戏的角色信息
    
    参数:
        login_manager: MihoyoLoginManager 实例
        game_biz: 游戏标识，如 'hk4e_cn'(原神), 'hkrpg_cn'(星铁), 'nap_cn'(绝区零)
                  None则返回所有游戏
    
    返回:
        (success, result)
    """
    success, roles = get_user_game_roles(login_manager)
    
    if not success:
        return False, roles
    
    if game_biz:
        filtered = [role for role in roles if role.get('game_biz') == game_biz]
        return True, filtered
    else:
        return True, roles

# ==================== 实时便笺功能 - 原神 ====================

def get_genshin_note(login_manager, role_id: str, server: str = 'cn_gf01') -> Tuple[bool, Union[Dict, str]]:
    """
    获取原神实时便笺
    
    参数:
        login_manager: MihoyoLoginManager 实例
        role_id: 游戏角色UID
        server: 服务器 (默认: cn_gf01 天空岛)
    
    返回:
        (success, result) 成功返回字典，失败返回错误信息
    """
    
    # 1. 检查登录状态
    if not login_manager or not login_manager.stoken or not login_manager.mid:
        return False, "缺少SToken或MID，请先登录"
    
    # 2. 检查V2凭证
    if not login_manager.ltoken_v2 or not login_manager.cookie_token_v2:
        return False, "缺少V2凭证(ltoken_v2/cookie_token_v2)，请先刷新Cookie"
    
    # 3. 构建URL和参数
    url = "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote"
    params = {
        'role_id': role_id,
        'server': server
    }
    
    # 4. 构建Cookie字符串 (使用V2凭证)
    cookie_parts = [
        f"ltoken_v2={login_manager.ltoken_v2}",
        f"cookie_token_v2={login_manager.cookie_token_v2}",
        f"ltmid_v2={login_manager.mid}",
        f"ltuid_v2={login_manager.account_id}",
        f"account_id={login_manager.account_id}",
        f"account_id_v2={login_manager.account_id}",
        f"account_mid_v2={login_manager.mid}",
        f"ltuid={login_manager.account_id}",
        f"mid={login_manager.mid}",
    ]
    '''
    if login_manager.stoken:
        cookie_parts.append(f"stoken={login_manager.stoken}")
    '''
    cookie_str = "; ".join(cookie_parts)
    
    # 5. 获取设备信息
    device_id = getattr(login_manager, 'device_id2', None) or getattr(login_manager, 'device_id1', None)
    device_fp = getattr(login_manager, 'device_fp2', None) or getattr(login_manager, 'device_fp1', None)
    
    if not device_id or not device_fp:
        return False, "缺少设备信息"
    
    # 6. 生成DS签名
    ds = DSGenerator.generate_ds(param_type=3, query=f"role_id={role_id}&server={server}")
    
    # 7. 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.84.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-cn',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': 'https://webstatic.mihoyo.com',
        'Referer': 'https://webstatic.mihoyo.com/app/community-game-records/index.html?bbs_presentation_style=fullscreen',
        'Cookie': cookie_str,
        'x-rpc-app_version': '2.84.1',
        'x-rpc-client_type': '5',
        'x-rpc-device_id': device_id,
        'x-rpc-device_fp': device_fp,
        'x-rpc-device_name': 'iPad',
        'x-rpc-platform': '5',
        'x-rpc-sys_version': '14.3',
        'x-rpc-tool_verison': 'v6.3.1-gr-cn',
        'x-rpc-page': 'v6.3.1-gr-cn_#/ys/daily',
        'DS': ds
    }
    
    # 8. 发送请求
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15,
            verify=True
        )
        
        if response.status_code != 200:
            return False, f"HTTP错误: {response.status_code}"
        
        result = response.json()
        print(result)
        
        if result.get('retcode') == 0:
            data = result.get('data', {})
            
            # 添加处理后的字段
            processed_data = process_genshin_note_data(data)
            return True, processed_data
        else:
            err_msg = result.get('message', f'API错误: {result.get("retcode")}')
            return False, err_msg
            
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "网络连接错误"
    except Exception as e:
        return False, f"请求异常: {str(e)}"


def process_genshin_note_data(data: Dict) -> Dict:
    """处理原神实时便笺数据"""
    processed = data.copy()
    
    # 添加可读时间字段
    if 'resin_recovery_time' in data:
        recovery_sec = int(data['resin_recovery_time'])
        processed['resin_recovery_time_readable'] = format_seconds(recovery_sec)
        processed['resin_full_time'] = get_full_time(recovery_sec)
    
    if 'home_coin_recovery_time' in data:
        home_sec = int(data['home_coin_recovery_time'])
        processed['home_coin_recovery_time_readable'] = format_seconds(home_sec)
    
    # 处理派遣信息
    if 'expeditions' in data:
        for exp in data['expeditions']:
            if 'remained_time' in exp:
                exp['remained_time_readable'] = format_seconds(int(exp['remained_time']))
    
    # 处理参量质变仪
    if 'transformer' in data and data['transformer']:
        trans = data['transformer']
        if 'recovery_time' in trans:
            rt = trans['recovery_time']
            if isinstance(rt, dict):
                total_seconds = rt.get('Day', 0) * 86400 + rt.get('Hour', 0) * 3600 + rt.get('Minute', 0) * 60
                processed['transformer']['recovery_time_readable'] = format_seconds(total_seconds)
    
    # 计算树脂百分比
    if 'current_resin' in data and 'max_resin' in data:
        current = int(data['current_resin'])
        max_resin = int(data['max_resin'])
        processed['resin_percent'] = round((current / max_resin) * 100, 1)
    
    return processed


# ==================== 实时便笺功能 - 崩坏：星穹铁道 ====================

def get_starrail_note(login_manager, role_id: str, server: str = 'prod_gf_cn') -> Tuple[bool, Union[Dict, str]]:
    """
    获取星穹铁道实时便笺
    
    参数:
        login_manager: MihoyoLoginManager 实例
        role_id: 游戏角色UID
        server: 服务器 (默认: prod_gf_cn 星穹列车)
    
    返回:
        (success, result) 成功返回字典，失败返回错误信息
    """
    
    # 1. 检查登录状态
    if not login_manager or not login_manager.stoken or not login_manager.mid:
        return False, "缺少SToken或MID，请先登录"
    
    # 2. 检查V2凭证
    if not login_manager.ltoken_v2 or not login_manager.cookie_token_v2:
        return False, "缺少V2凭证(ltoken_v2/cookie_token_v2)，请先刷新Cookie"
    
    # 3. 构建URL和参数
    url = "https://api-takumi-record.mihoyo.com/game_record/app/hkrpg/api/note"
    params = {
        'role_id': role_id,
        'server': server
    }
    
    # 4. 构建Cookie字符串 (使用V2凭证)
    cookie_parts = [
        f"ltoken_v2={login_manager.ltoken_v2}",
        f"cookie_token_v2={login_manager.cookie_token_v2}",
        f"ltmid_v2={login_manager.mid}",
        f"ltuid_v2={login_manager.account_id}",
        f"account_id={login_manager.account_id}",
        f"account_id_v2={login_manager.account_id}",
        f"account_mid_v2={login_manager.mid}",
        f"ltuid={login_manager.account_id}",
        f"mid={login_manager.mid}",
    ]
    
    if login_manager.stoken:
        cookie_parts.append(f"stoken={login_manager.stoken}")
    
    cookie_str = "; ".join(cookie_parts)
    
    # 5. 获取设备信息
    device_id = getattr(login_manager, 'device_id2', None) or getattr(login_manager, 'device_id1', None)
    device_fp = getattr(login_manager, 'device_fp2', None) or getattr(login_manager, 'device_fp1', None)
    
    if not device_id or not device_fp:
        return False, "缺少设备信息"
    
    # 6. 生成DS签名
    ds = DSGenerator.generate_ds(param_type=3, query=f"role_id={role_id}&server={server}")
    
    # 7. 构建请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.84.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-cn',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': 'https://webstatic.mihoyo.com',
        'Referer': 'https://webstatic.mihoyo.com/app/community-game-records/rpg/index.html?bbs_presentation_style=fullscreen',
        'Cookie': cookie_str,
        'x-rpc-app_version': '2.84.1',
        'x-rpc-client_type': '5',
        'x-rpc-device_id': device_id,
        'x-rpc-device_fp': device_fp,
        'x-rpc-device_name': 'iPad',
        'x-rpc-platform': '5',
        'x-rpc-sys_version': '14.3',
        'x-rpc-tool_verison': 'v4.0.0-prod',
        'x-rpc-page': 'v4.0.0-prod_#/rpg',
        'DS': ds
    }
    
    # 8. 发送请求
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15,
            verify=True
        )
        
        if response.status_code != 200:
            return False, f"HTTP错误: {response.status_code}"
        
        result = response.json()
        
        if result.get('retcode') == 0:
            data = result.get('data', {})
            
            # 添加处理后的字段
            processed_data = process_starrail_note_data(data)
            return True, processed_data
        else:
            err_msg = result.get('message', f'API错误: {result.get("retcode")}')
            return False, err_msg
            
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "网络连接错误"
    except Exception as e:
        return False, f"请求异常: {str(e)}"


def process_starrail_note_data(data: Dict) -> Dict:
    """处理星穹铁道实时便笺数据"""
    processed = data.copy()
    
    # 添加可读时间字段
    if 'stamina_recover_time' in data:
        recovery_sec = int(data['stamina_recover_time'])
        processed['stamina_recover_time_readable'] = format_seconds(recovery_sec)
        processed['stamina_full_time'] = get_full_time(recovery_sec)
    
    # 计算开拓力百分比
    if 'current_stamina' in data and 'max_stamina' in data:
        current = int(data['current_stamina'])
        max_stamina = int(data['max_stamina'])
        processed['stamina_percent'] = round((current / max_stamina) * 100, 1)
    
    # 计算后备开拓力百分比
    if 'current_reserve_stamina' in data and 'max_stamina' in data:
        reserve = int(data['current_reserve_stamina'])
        max_stamina = int(data['max_stamina'])
        processed['reserve_stamina_percent'] = round((reserve / max_stamina) * 100, 1)
        processed['reserve_stamina_percent_of_max'] = round((reserve / 2400) * 100, 1) if max_stamina else 0
    
    # 计算模拟宇宙百分比
    if 'current_rogue_score' in data and 'max_rogue_score' in data:
        current = int(data['current_rogue_score'])
        max_score = int(data['max_rogue_score'])
        if max_score > 0:
            processed['rogue_score_percent'] = round((current / max_score) * 100, 1)
    
    # 计算差分宇宙百分比
    if 'rogue_tourn_weekly_cur' in data and 'rogue_tourn_weekly_max' in data:
        current = int(data['rogue_tourn_weekly_cur'])
        max_score = int(data['rogue_tourn_weekly_max'])
        if max_score > 0:
            processed['rogue_tourn_percent'] = round((current / max_score) * 100, 1)
    
    # 计算末日幻影百分比
    if 'grid_fight_weekly_cur' in data and 'grid_fight_weekly_max' in data:
        current = int(data['grid_fight_weekly_cur'])
        max_score = int(data['grid_fight_weekly_max'])
        if max_score > 0:
            processed['grid_fight_percent'] = round((current / max_score) * 100, 1)
    
    return processed


# ==================== 实时便笺功能 - 绝区零 ====================

def get_zzz_note(login_manager, role_id: str, server: str = 'prod_gf_cn') -> Tuple[bool, Union[Dict, str]]:
    """
    获取绝区零实时便笺
    
    参数:
        login_manager: MihoyoLoginManager 实例
        role_id: 游戏角色UID
        server: 服务器 (默认: prod_gf_cn 新艾利都)
    
    返回:
        (success, result) 成功返回字典，失败返回错误信息
    """
    
    # 1. 检查登录状态
    if not login_manager or not login_manager.stoken or not login_manager.mid:
        return False, "缺少SToken或MID，请先登录"
    
    # 2. 检查V2凭证
    if not login_manager.ltoken_v2 or not login_manager.cookie_token_v2:
        return False, "缺少V2凭证(ltoken_v2/cookie_token_v2)，请先刷新Cookie"
    
    # 3. 构建URL和参数
    url = "https://api-takumi-record.mihoyo.com/event/game_record_zzz/api/zzz/note"
    params = {
        'role_id': role_id,
        'server': server
    }
    
    # 4. 构建Cookie字符串 (使用V2凭证)
    cookie_parts = [
        f"ltoken_v2={login_manager.ltoken_v2}",
        f"cookie_token_v2={login_manager.cookie_token_v2}",
        f"ltmid_v2={login_manager.mid}",
        f"ltuid_v2={login_manager.account_id}",
        f"account_id={login_manager.account_id}",
        f"account_id_v2={login_manager.account_id}",
        f"account_mid_v2={login_manager.mid}",
        f"ltuid={login_manager.account_id}",
        f"mid={login_manager.mid}",
        f"_MHYUUID=7c387e9b-a2a3-44c4-0b9f-07dd472dd414",
        f"mi18nLang=zh-cn",
    ]
    
    if login_manager.stoken:
        cookie_parts.append(f"stoken={login_manager.stoken}")
    
    cookie_str = "; ".join(cookie_parts)
    
    # 5. 获取设备信息
    device_id = getattr(login_manager, 'device_id2', None) or getattr(login_manager, 'device_id1', None)
    device_fp = getattr(login_manager, 'device_fp2', None) or getattr(login_manager, 'device_fp1', None)
    
    if not device_id or not device_fp:
        return False, "缺少设备信息"
    
    # 6. 构建geetest扩展信息
    geetest_ext = {
        "viewUid": login_manager.account_id,
        "server": server,
        "gameId": 8,
        "page": "v2.6.2_#/zzz/daily-note",
        "isHost": 1,
        "viewSource": 3,
        "actionSource": 127
    }
    
    # 7. 构建请求头 (绝区零需要特殊headers)
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) miHoYoBBS/2.84.1',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-cn',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Origin': 'https://act.mihoyo.com',
        'Referer': f'https://act.mihoyo.com/app/mihoyo-zzz-game-record/m.html?uid={login_manager.account_id}&mhy_presentation_style=fullscreen&game_id=8&bbs_auth_required=true&bbs_presentation_style=fullscreen&user_id={login_manager.account_id}&mhy_bg_style=dark',
        'Cookie': cookie_str,
        'x-rpc-app_version': '2.84.1',
        'x-rpc-client_type': '5',
        'x-rpc-device_id': device_id,
        'x-rpc-device_fp': device_fp,
        'x-rpc-device_name': 'iPad',
        'x-rpc-platform': '1',
        'x-rpc-sys_version': '14.3',
        'x-rpc-language': 'zh-cn',
        'x-rpc-lang': 'zh-cn',
        'x-rpc-page': 'v2.6.2_#/zzz/daily-note',
        'x-rpc-geetest_ext': json.dumps(geetest_ext, separators=(',', ':'))
    }
    
    # 8. 发送请求
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15,
            verify=True
        )
        
        if response.status_code != 200:
            return False, f"HTTP错误: {response.status_code}"
        
        result = response.json()
        
        if result.get('retcode') == 0:
            data = result.get('data', {})
            
            # 添加处理后的字段
            processed_data = process_zzz_note_data(data)
            return True, processed_data
        else:
            err_msg = result.get('message', f'API错误: {result.get("retcode")}')
            return False, err_msg
            
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        return False, "网络连接错误"
    except Exception as e:
        return False, f"请求异常: {str(e)}"


def process_zzz_note_data(data: Dict) -> Dict:
    """处理绝区零实时便笺数据"""
    processed = data.copy()
    
    # 处理电池能量
    if 'energy' in data:
        energy = data['energy']
        if 'progress' in energy:
            current = energy['progress'].get('current', 0)
            max_energy = energy['progress'].get('max', 240)
            processed['energy_percent'] = round((current / max_energy) * 100, 1)
        
        if 'restore' in energy:
            restore_sec = int(energy['restore'])
            processed['energy_restore_readable'] = format_seconds(restore_sec)
            processed['energy_full_time'] = get_full_time(restore_sec)
    
    # 处理活跃度
    if 'vitality' in data:
        vitality = data['vitality']
        current = vitality.get('current', 0)
        max_vitality = vitality.get('max', 400)
        processed['vitality_percent'] = round((current / max_vitality) * 100, 1)
    
    # 处理录像店状态
    if 'vhs_sale' in data and 'sale_state' in data['vhs_sale']:
        state = data['vhs_sale']['sale_state']
        state_map = {
            'SaleStateDone': '已售完',
            'SaleStateCanSell': '可销售',
            'SaleStateWait': '等待中'
        }
        processed['vhs_sale_state_cn'] = state_map.get(state, state)
    
    # 处理刮刮卡状态
    if 'card_sign' in data:
        card_map = {
            'CardSignNo': '未刮卡',
            'CardSignYes': '已刮卡'
        }
        processed['card_sign_cn'] = card_map.get(data['card_sign'], data['card_sign'])
    
    # 处理悬赏委托
    if 'bounty_commission' in data:
        bounty = data['bounty_commission']
        if 'num' in bounty and 'total' in bounty:
            current = int(bounty['num'])
            total = int(bounty['total'])
            processed['bounty_percent'] = round((current / total) * 100, 1)
        
        if 'refresh_time' in bounty:
            refresh_sec = int(bounty['refresh_time'])
            processed['bounty_refresh_readable'] = format_seconds(refresh_sec)
    
    # 处理深渊
    if 'abyss_refresh' in data:
        abyss_sec = int(data['abyss_refresh'])
        processed['abyss_refresh_readable'] = format_seconds(abyss_sec)
    
    # 处理每周任务
    if 'weekly_task' in data:
        weekly = data['weekly_task']
        if 'cur_point' in weekly and 'max_point' in weekly:
            current = int(weekly['cur_point'])
            max_point = int(weekly['max_point'])
            processed['weekly_task_percent'] = round((current / max_point) * 100, 1)
        
        if 'refresh_time' in weekly:
            refresh_sec = int(weekly['refresh_time'])
            processed['weekly_refresh_readable'] = format_seconds(refresh_sec)
    
    # 处理会员卡状态
    if 'member_card' in data and 'member_card_state' in data['member_card']:
        state = data['member_card']['member_card_state']
        card_map = {
            'MemberCardStateNo': '未领取',
            'MemberCardStateYes': '已领取'
        }
        processed['member_card_state_cn'] = card_map.get(state, state)
    
    # 处理随便观经营
    if 'temple_running' in data:
        temple = data['temple_running']
        
        # 探索派遣状态
        if 'expedition_state' in temple:
            exp_map = {
                'ExpeditionStateEnd': '已结束',
                'ExpeditionStateDoing': '进行中',
                'ExpeditionStateNone': '无'
            }
            processed['expedition_state_cn'] = exp_map.get(temple['expedition_state'], temple['expedition_state'])
        
        # 工作台状态
        if 'bench_state' in temple:
            bench_map = {
                'BenchStateCanProduce': '可生产',
                'BenchStateProducing': '生产中'
            }
            processed['bench_state_cn'] = bench_map.get(temple['bench_state'], temple['bench_state'])
        
        # 货架状态
        if 'shelve_state' in temple:
            shelve_map = {
                'ShelveStateSoldOut': '已售完',
                'ShelveStateCanSale': '可销售'
            }
            processed['shelve_state_cn'] = shelve_map.get(temple['shelve_state'], temple['shelve_state'])
        
        # 货币百分比
        if 'current_currency' in temple and 'weekly_currency_max' in temple:
            try:
                current = int(temple['current_currency'])
                max_currency = int(temple['weekly_currency_max'])
                if max_currency > 0:
                    processed['currency_percent'] = round((current / max_currency) * 100, 1)
            except:
                pass
    
    # 处理咖啡店状态
    if 'cafe_state' in data:
        cafe_map = {
            'CafeStateNo': '未饮用',
            'CafeStateDone': '已饮用'
        }
        processed['cafe_state_cn'] = cafe_map.get(data['cafe_state'], data['cafe_state'])
    
    return processed


# ==================== 通用函数 ====================

def format_seconds(seconds: int) -> str:
    """将秒数格式化为可读时间"""
    if seconds <= 0:
        return "已就绪"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    
    if not parts:
        return "小于1分钟"
    
    return "".join(parts)


def get_full_time(seconds: int) -> str:
    """获取预计满额时间"""
    if seconds <= 0:
        return "当前已满"
    
    from datetime import datetime, timedelta
    full_time = datetime.now() + timedelta(seconds=seconds)
    return full_time.strftime("%H:%M")


# ==================== 格式化输出 ====================

def format_genshin_note(data: Dict) -> str:
    """格式化原神实时便笺为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append("🌍 原神 - 实时便笺")
    lines.append("=" * 50)
    
    # 树脂
    current = data.get('current_resin', 0)
    max_resin = data.get('max_resin', 200)
    percent = data.get('resin_percent', 0)
    recovery = data.get('resin_recovery_time_readable', '未知')
    full_time = data.get('resin_full_time', '')
    
    lines.append(f"\n⚡ 原粹树脂")
    lines.append(f"  当前: {current}/{max_resin} ({percent}%)")
    lines.append(f"  恢复: {recovery}")
    if full_time and recovery != "已就绪":
        lines.append(f"  满额: {full_time}")
    
    # 每日任务
    finished = data.get('finished_task_num', 0)
    total = data.get('total_task_num', 4)
    extra = "✓" if data.get('is_extra_task_reward_received') else "✗"
    
    lines.append(f"\n📋 每日委托")
    lines.append(f"  进度: {finished}/{total}")
    lines.append(f"  额外奖励: {extra}")
    
    # 周本减半
    remain = data.get('remain_resin_discount_num', 0)
    limit = data.get('resin_discount_num_limit', 3)
    lines.append(f"\n⚔️ 周本减半")
    lines.append(f"  剩余: {remain}/{limit}")
    
    # 探索派遣
    current_exp = data.get('current_expedition_num', 0)
    max_exp = data.get('max_expedition_num', 5)
    lines.append(f"\n🗺️ 探索派遣")
    lines.append(f"  进度: {current_exp}/{max_exp}")
    
    if 'expeditions' in data:
        for i, exp in enumerate(data['expeditions'], 1):
            remain = exp.get('remained_time_readable', '未知')
            lines.append(f"  派遣{i}: {remain}")
    
    # 洞天宝钱
    current_coin = data.get('current_home_coin', 0)
    max_coin = data.get('max_home_coin', 2400)
    coin_time = data.get('home_coin_recovery_time_readable', '')
    
    lines.append(f"\n🏠 洞天宝钱")
    lines.append(f"  当前: {current_coin}/{max_coin}")
    if coin_time:
        lines.append(f"  满额: {coin_time}")
    
    # 参量质变仪
    transformer = data.get('transformer', {})
    if transformer and transformer.get('obtained'):
        status = "✓ 可用" if transformer.get('reached') else "✗ 冷却中"
        lines.append(f"\n🔧 参量质变仪")
        lines.append(f"  状态: {status}")
    
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)


def format_starrail_note(data: Dict) -> str:
    """格式化星穹铁道实时便笺为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append("🚂 崩坏：星穹铁道 - 实时便笺")
    lines.append("=" * 50)
    
    # 开拓力
    current = data.get('current_stamina', 0)
    max_stamina = data.get('max_stamina', 300)
    percent = data.get('stamina_percent', 0)
    recovery = data.get('stamina_recover_time_readable', '未知')
    full_time = data.get('stamina_full_time', '')
    
    lines.append(f"\n⚡ 开拓力")
    lines.append(f"  当前: {current}/{max_stamina} ({percent}%)")
    lines.append(f"  恢复: {recovery}")
    if full_time and recovery != "已就绪":
        lines.append(f"  满额: {full_time}")
    
    # 后备开拓力
    reserve = data.get('current_reserve_stamina', 0)
    reserve_percent = data.get('reserve_stamina_percent', 0)
    if reserve > 0:
        lines.append(f"\n📦 后备开拓力")
        lines.append(f"  当前: {reserve}/300 ({reserve_percent}%)")
    
    # 派遣
    accepted = data.get('accepted_epedition_num', 0)
    total = data.get('total_expedition_num', 4)
    lines.append(f"\n🗺️ 派遣")
    lines.append(f"  进度: {accepted}/{total}")
    
    # 模拟宇宙
    rogue_cur = data.get('current_rogue_score', 0)
    rogue_max = data.get('max_rogue_score', 14000)
    rogue_percent = data.get('rogue_score_percent', 0)
    lines.append(f"\n🌌 模拟宇宙")
    lines.append(f"  当前: {rogue_cur}/{rogue_max} ({rogue_percent}%)")
    
    # 历战余响
    cocoon = data.get('weekly_cocoon_cnt', 0)
    cocoon_limit = data.get('weekly_cocoon_limit', 3)
    lines.append(f"\n⚔️ 历战余响")
    lines.append(f"  本周: {cocoon}/{cocoon_limit}")
    
    # 差分宇宙
    if data.get('rogue_tourn_weekly_unlocked'):
        tourn_cur = data.get('rogue_tourn_weekly_cur', 0)
        tourn_max = data.get('rogue_tourn_weekly_max', 2000)
        tourn_percent = data.get('rogue_tourn_percent', 0)
        lines.append(f"\n🌀 差分宇宙")
        lines.append(f"  本周: {tourn_cur}/{tourn_max} ({tourn_percent}%)")
    
    # 末日幻影
    grid_cur = data.get('grid_fight_weekly_cur', 0)
    grid_max = data.get('grid_fight_weekly_max', 18000)
    grid_percent = data.get('grid_fight_percent', 0)
    if grid_max > 0:
        lines.append(f"\n💥 末日幻影")
        lines.append(f"  本周: {grid_cur}/{grid_max} ({grid_percent}%)")
    
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)


def format_zzz_note(data: Dict) -> str:
    """格式化绝区零实时便笺为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append("🎮 绝区零 - 实时便笺")
    lines.append("=" * 50)
    
    # 电池能量
    energy = data.get('energy', {})
    if energy:
        progress = energy.get('progress', {})
        current = progress.get('current', 0)
        max_energy = progress.get('max', 240)
        percent = data.get('energy_percent', 0)
        restore = data.get('energy_restore_readable', '未知')
        full_time = data.get('energy_full_time', '')
        
        lines.append(f"\n🔋 电池能量")
        lines.append(f"  当前: {current}/{max_energy} ({percent}%)")
        lines.append(f"  恢复: {restore}")
        if full_time and restore != "已就绪":
            lines.append(f"  满额: {full_time}")
    
    # 活跃度
    vitality = data.get('vitality', {})
    if vitality:
        current = vitality.get('current', 0)
        max_vitality = vitality.get('max', 400)
        percent = data.get('vitality_percent', 0)
        lines.append(f"\n💪活跃度")
        lines.append(f"  当前: {current}/{max_vitality} ({percent}%)")
    
    # 录像店
    vhs_state = data.get('vhs_sale_state_cn', '')
    if vhs_state:
        lines.append(f"\n📼 录像店")
        lines.append(f"  状态: {vhs_state}")
    
    # 刮刮卡
    card_state = data.get('card_sign_cn', '')
    if card_state:
        lines.append(f"\n🎫 刮刮卡")
        lines.append(f"  状态: {card_state}")
    
    # 悬赏委托
    bounty = data.get('bounty_commission', {})
    if bounty:
        current = bounty.get('num', 0)
        total = bounty.get('total', 8000)
        percent = data.get('bounty_percent', 0)
        refresh = data.get('bounty_refresh_readable', '')
        
        lines.append(f"\n💰 悬赏委托")
        lines.append(f"  当前: {current}/{total} ({percent}%)")
        if refresh:
            lines.append(f"  刷新: {refresh}")
    
    # 式舆防卫战/深渊
    abyss = data.get('abyss_refresh_readable', '')
    if abyss:
        lines.append(f"\n⚔️ 式舆防卫战")
        lines.append(f"  刷新: {abyss}")
    
    # 每周任务
    weekly = data.get('weekly_task', {})
    if weekly:
        current = weekly.get('cur_point', 0)
        max_point = weekly.get('max_point', 2100)
        percent = data.get('weekly_task_percent', 0)
        refresh = data.get('weekly_refresh_readable', '')
        
        lines.append(f"\n📊 每周任务")
        lines.append(f"  当前: {current}/{max_point} ({percent}%)")
        if refresh:
            lines.append(f"  刷新: {refresh}")
    
    # 随便观经营
    temple = data.get('temple_running', {})
    if temple:
        exp_state = data.get('expedition_state_cn', '')
        bench_state = data.get('bench_state_cn', '')
        shelve_state = data.get('shelve_state_cn', '')
        level = temple.get('level', 0)
        currency = temple.get('current_currency', '0')
        currency_percent = data.get('currency_percent', 0)
        
        lines.append(f"\n🏢 随便观经营")
        lines.append(f"  等级: {level}")
        if exp_state:
            lines.append(f"  探索: {exp_state}")
        if bench_state:
            lines.append(f"  工作台: {bench_state}")
        if shelve_state:
            lines.append(f"  货架: {shelve_state}")
        lines.append(f"  货币: {currency} ({currency_percent}%)")
    
    # 咖啡店
    cafe_state = data.get('cafe_state_cn', '')
    if cafe_state:
        lines.append(f"\n☕ 咖啡店")
        lines.append(f"  状态: {cafe_state}")
    
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)


# ==================== 角色卡片读取与批量查询 ====================

def get_roles_from_cache(regedist: str) -> Tuple[bool, List[Dict]]:
    """
    从缓存文件读取已绑定的游戏角色列表
    
    参数:
        regedist: 注册表路径
    
    返回:
        (success, roles_list)
        roles_list: 每个角色包含 game_biz, game_name, role_id, server, nickname, level 等信息
    """
    if not regedist:
        return False, "注册表路径为空"
    
    cache_file = os.path.join(regedist, "internal_files", "miyoushe_cache.json")
    if not os.path.exists(cache_file):
        return False, "缓存文件不存在，请先获取角色信息"
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        game_data = cache_data.get('game_data', {})
        if not game_data:
            return False, "缓存中没有游戏角色数据"
        
        # 转换为统一格式的角色列表
        roles_list = []
        
        # game_data 结构: { "原神": [ {...}, ... ], "崩坏：星穹铁道": [ {...}, ... ], ... }
        for game_name, roles in game_data.items():
            for role in roles:
                # 确定 game_biz
                game_biz = None
                if game_name == "原神":
                    game_biz = "hk4e_cn"
                elif game_name == "崩坏：星穹铁道":
                    game_biz = "hkrpg_cn"
                elif game_name == "绝区零":
                    game_biz = "nap_cn"
                else:
                    continue  # 跳过不支持的 game
                
                # 提取角色信息
                role_info = {
                    'game_biz': game_biz,
                    'game_name': game_name,
                    'role_id': role.get('uid') or role.get('game_uid'),
                    'server': role.get('region') or role.get('server', ''),
                    'nickname': role.get('nickname', ''),
                    'level': role.get('level', 0),
                    'is_chosen': role.get('is_chosen', False)
                }
                
                # 服务器映射（如果需要标准格式）
                if game_biz == 'hk4e_cn' and role_info['server'] == '天空岛':
                    role_info['server'] = 'cn_gf01'
                elif game_biz == 'hk4e_cn' and role_info['server'] == '世界树':
                    role_info['server'] = 'cn_qd01'
                elif game_biz == 'hkrpg_cn' and role_info['server'] == '星穹列车':
                    role_info['server'] = 'prod_gf_cn'
                elif game_biz == 'nap_cn' and role_info['server'] == '新艾利都':
                    role_info['server'] = 'prod_gf_cn'
                
                roles_list.append(role_info)
        
        return True, roles_list
        
    except Exception as e:
        return False, f"读取缓存失败: {str(e)}"


def get_all_games_note(login_manager, regedist: str = None) -> Dict[str, List[Dict]]:
    """
    获取所有已绑定游戏的所有角色实时便笺
    
    参数:
        login_manager: MihoyoLoginManager 实例
        regedist: 注册表路径（用于读取角色缓存）
    
    返回:
        {
            'genshin': [{'role': role_info, 'success': True, 'data': data}, ...],
            'starrail': [...],
            'zzz': [...],
            'errors': [...]  # 全局错误
        }
    """
    result = {
        'genshin': [],
        'starrail': [],
        'zzz': [],
        'errors': []
    }
    
    # 1. 获取角色列表
    if regedist:
        success, roles_or_error = get_roles_from_cache(regedist)
        if not success:
            result['errors'].append(f"获取角色列表失败: {roles_or_error}")
            return result
        roles_list = roles_or_error
    else:
        # 如果没有 regedist，尝试从 login_manager 直接获取
        try:
            from miyoushe_func import get_user_game_roles
            success, roles_or_error = get_user_game_roles(login_manager)
            if not success:
                result['errors'].append(f"获取角色列表失败: {roles_or_error}")
                return result
            
            # 转换为统一格式
            roles_list = []
            for role in roles_or_error:
                game_biz = role.get('game_biz')
                if game_biz not in ['hk4e_cn', 'hkrpg_cn', 'nap_cn']:
                    continue
                
                role_info = {
                    'game_biz': game_biz,
                    'game_name': role.get('game_name', ''),
                    'role_id': role.get('game_uid'),
                    'server': role.get('region', ''),
                    'nickname': role.get('nickname', ''),
                    'level': role.get('level', 0),
                    'is_chosen': role.get('is_chosen', False)
                }
                roles_list.append(role_info)
        except Exception as e:
            result['errors'].append(f"获取角色列表异常: {str(e)}")
            return result
    
    # 2. 按游戏分类查询
    for role in roles_list:
        game_biz = role.get('game_biz')
        role_id = role.get('role_id')
        server = role.get('server')
        
        if not role_id or not server:
            result['errors'].append(f"角色信息不完整: {role}")
            continue
        
        # 根据 game_biz 调用对应函数
        if game_biz == 'hk4e_cn':
            success, data = get_genshin_note(login_manager, role_id, server)
            result['genshin'].append({
                'role': role,
                'success': success,
                'data': data if success else None,
                'error': None if success else data
            })
            
        elif game_biz == 'hkrpg_cn':
            success, data = get_starrail_note(login_manager, role_id, server)
            result['starrail'].append({
                'role': role,
                'success': success,
                'data': data if success else None,
                'error': None if success else data
            })
            
        elif game_biz == 'nap_cn':
            success, data = get_zzz_note(login_manager, role_id, server)
            result['zzz'].append({
                'role': role,
                'success': success,
                'data': data if success else None,
                'error': None if success else data
            })
        
        # 添加短暂延迟，避免请求过快
        time.sleep(0.5)
    
    return result


def get_game_note_by_role(login_manager, game_biz: str, role_id: str, server: str = None) -> Tuple[bool, Union[Dict, str]]:
    """
    根据游戏类型和角色ID获取实时便笺（统一入口）
    
    参数:
        login_manager: MihoyoLoginManager 实例
        game_biz: 游戏标识 ('hk4e_cn', 'hkrpg_cn', 'nap_cn')
        role_id: 游戏角色UID
        server: 服务器 (不传则使用默认)
    
    返回:
        (success, result)
    """
    
    # 服务器默认值
    DEFAULT_SERVERS = {
        'hk4e_cn': 'cn_gf01',
        'hkrpg_cn': 'prod_gf_cn',
        'nap_cn': 'prod_gf_cn'
    }
    
    if server is None:
        server = DEFAULT_SERVERS.get(game_biz)
        if not server:
            return False, f"未知游戏: {game_biz}"
    
    # 分发到具体函数
    if game_biz == 'hk4e_cn':
        return get_genshin_note(login_manager, role_id, server)
    elif game_biz == 'hkrpg_cn':
        return get_starrail_note(login_manager, role_id, server)
    elif game_biz == 'nap_cn':
        return get_zzz_note(login_manager, role_id, server)
    else:
        return False, f"不支持的game_biz: {game_biz}"


# ==================== 批量格式化输出 ====================

def format_all_games_note(results: Dict) -> str:
    """
    格式化所有游戏的实时便笺为可读文本
    
    参数:
        results: get_all_games_note 返回的结果字典
    
    返回:
        格式化的完整文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🎮 米游社 - 全游戏实时便笺")
    lines.append("=" * 60)
    
    has_data = False
    
    # 原神
    if results['genshin']:
        has_data = True
        for item in results['genshin']:
            role = item['role']
            lines.append(f"\n🌍 【原神】{role.get('nickname', '')} (UID: {role.get('role_id')})")
            if item['success']:
                lines.append(format_genshin_note(item['data']).split('\n', 1)[1])  # 去掉第一行标题
            else:
                lines.append(f"  ❌ 获取失败: {item['error']}")
    
    # 星穹铁道
    if results['starrail']:
        has_data = True
        for item in results['starrail']:
            role = item['role']
            lines.append(f"\n🚂 【崩坏：星穹铁道】{role.get('nickname', '')} (UID: {role.get('role_id')})")
            if item['success']:
                lines.append(format_starrail_note(item['data']).split('\n', 1)[1])
            else:
                lines.append(f"  ❌ 获取失败: {item['error']}")
    
    # 绝区零
    if results['zzz']:
        has_data = True
        for item in results['zzz']:
            role = item['role']
            lines.append(f"\n🎮 【绝区零】{role.get('nickname', '')} (UID: {role.get('role_id')})")
            if item['success']:
                lines.append(format_zzz_note(item['data']).split('\n', 1)[1])
            else:
                lines.append(f"  ❌ 获取失败: {item['error']}")
    
    # 错误信息
    if results['errors']:
        lines.append("\n" + "=" * 60)
        lines.append("⚠️ 错误信息")
        lines.append("=" * 60)
        for error in results['errors']:
            lines.append(f"  • {error}")
    
    if not has_data and not results['errors']:
        lines.append("\n暂无游戏角色数据")
    
    lines.append("\n" + "=" * 60)
    return "\n".join(lines)

# ==================== 测试代码 ====================
def test_with_manager():
    """测试函数 - 需要在有MihoyoLoginManager实例的环境下运行"""
    try:
        from miyoushe_new import MihoyoLoginManager
        
        # 这个测试需要你有一个已经登录的manager实例
        # 这里只是示例代码
        print("请在已登录的MihoyoLoginManager实例中调用:")
        print("from miyoushe_func import get_user_game_roles_simple, format_roles_text")
        print("success, roles = get_user_game_roles_simple(manager)")
        print("if success:")
        print("    print(format_roles_text(roles))")
        
    except ImportError:
        print("未找到miyoushe_new模块，请在完整环境中测试")


if __name__ == "__main__":
    print("米游社角色信息获取模块")
    print("此模块需要与miyoushe_new.py配合使用")
    print("\n使用示例:")
    print("""
    from miyoushe_new import MihoyoLoginManager
    from miyoushe_func import get_user_game_roles_simple, format_roles_text
    
    # 假设你已经通过扫码登录获取了manager实例
    manager = MihoyoLoginManager(cookie_str=your_cookie)
    
    # 获取游戏角色
    success, roles = get_user_game_roles_simple(manager)
    if success:
        print(format_roles_text(roles))
    else:
        print(f"获取失败: {roles}")
    """)
