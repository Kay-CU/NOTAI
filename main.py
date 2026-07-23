# -*- coding: utf-8 -*-
"""
赛事分析提示词生成器 - Android 客户端
基于 Kivy 框架，从体彩官方API拉取当日竞猜足球赛事
"""

import json
import urllib.request
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

# ============ 赛事数据拉取 ============

SPORTTERY_API = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry?poolCode=hhad,had&channel=c"


def fetch_matches():
    """从体彩官方API拉取当日竞彩足球赛程"""
    req = urllib.request.Request(SPORTTERY_API, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.sporttery.cn/',
        'Origin': 'https://www.sporttery.cn',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e), "matches": []}

    if not data.get('success'):
        return {"error": "API返回错误", "matches": []}

    matches = []
    for info in data.get('value', {}).get('matchInfoList', []):
        business_date = info.get('businessDate', '')
        for m in info.get('subMatchList', []):
            match_time = m.get('matchTime', '')
            if match_time and business_date:
                full_time = f"{business_date} {match_time}"
            else:
                full_time = match_time or business_date
            matches.append({
                "matchNum": m.get('matchNum', ''),
                "league": m.get('leagueAbbName', ''),
                "home": m.get('homeTeamAllName', '') or m.get('homeTeamAbbName', ''),
                "away": m.get('awayTeamAllName', '') or m.get('awayTeamAbbName', ''),
                "time": full_time,
            })
    return {"matches": matches, "count": len(matches)}


# ============ 提示词模板 ============

PROMPT_TEMPLATE = (
    "你是一名资深足球赛事分析师，请你：\n"
    "1、基于当前赛季主客队积分排名、球队胜率，胜场等因素的权重分（权重占比20%）\n"
    "2、基于保级压力、夺冠意志、欧战或更高一级资格站等战意因素的权重分（权重占比40%）\n"
    "3、基于当前赛季场均进球、失球数等攻防稳定性的权重分（权重占比30%）\n"
    "4、基于天气+场地+主力球员伤情（权重占比10%）\n"
    "分析{matches}最有可能的胜平负结局、以及可能得比分和进球数。"
)


# ============ UI 组件 ============

class MatchItem(BoxLayout):
    """赛事选择列表项"""
    def __init__(self, match_data, index, callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(70)
        self.match_data = match_data
        self.index = index
        self.callback = callback
        self.selected = False

        with self.canvas.before:
            Color(0.11, 0.11, 0.12, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 复选框
        self.cb = CheckBox(size_hint_x=0.15, color=(1, 1, 1, 1))
        self.cb.bind(active=self._on_toggle)
        self.add_widget(self.cb)

        # 赛事信息
        info = BoxLayout(orientation='vertical', size_hint_x=0.7)
        league_label = Label(
            text=f"[color=37F4EE]{match_data.get('league', '')}[/color]",
            markup=True, font_size=dp(11), size_hint_y=0.3,
            halign='left', valign='middle'
        )
        league_label.bind(size=league_label.setter('text_size'))
        teams_label = Label(
            text=f"{match_data['home']} VS {match_data['away']}",
            font_size=dp(14), size_hint_y=0.4,
            halign='left', valign='middle', bold=True
        )
        teams_label.bind(size=teams_label.setter('text_size'))
        time_label = Label(
            text=match_data.get('time', ''),
            font_size=dp(10), size_hint_y=0.3,
            halign='left', valign='middle',
            color=(0.56, 0.56, 0.58, 1)
        )
        time_label.bind(size=time_label.setter('text_size'))
        info.add_widget(league_label)
        info.add_widget(teams_label)
        info.add_widget(time_label)
        self.add_widget(info)

        # 编号
        num_label = Label(
            text=match_data.get('matchNum', ''),
            font_size=dp(11), size_hint_x=0.15,
            color=(0.56, 0.56, 0.58, 1)
        )
        self.add_widget(num_label)

    def _on_toggle(self, instance, value):
        self.selected = value
        with self.canvas.before:
            self.canvas.clear()
            if value:
                Color(0.25, 0.05, 0.1, 1)
            else:
                Color(0.11, 0.11, 0.12, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        if self.callback:
            self.callback(self.index, value)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg'):
            self.bg.pos = self.pos
            self.bg.size = self.size


class MatchInputCard(BoxLayout):
    """已选赛事输入卡片"""
    def __init__(self, match_data, index, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(140)
        self.spacing = dp(8)
        self.padding = dp(12)

        with self.canvas.before:
            Color(0.11, 0.11, 0.12, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 头部：编号 + 联赛
        header = BoxLayout(size_hint_y=0.25)
        num_label = Label(
            text=str(index + 1),
            size_hint_x=0.15, font_size=dp(16), bold=True,
            color=(0.996, 0.173, 0.333, 1)
        )
        league_label = Label(
            text=match_data.get('league', '比赛'),
            size_hint_x=0.85, font_size=dp(14), bold=True,
            halign='left', valign='middle'
        )
        league_label.bind(size=league_label.setter('text_size'))
        header.add_widget(num_label)
        header.add_widget(league_label)
        self.add_widget(header)

        # 输入框区域
        inputs = BoxLayout(size_hint_y=0.75, spacing=dp(8))
        # 主队
        home_box = BoxLayout(orientation='vertical', size_hint_x=0.45, spacing=dp(4))
        home_label = Label(text="主队", font_size=dp(11), size_hint_y=0.25,
                           halign='left', color=(0.996, 0.173, 0.333, 1))
        home_label.bind(size=home_label.setter('text_size'))
        self.home_input = TextInput(
            text=match_data.get('home', ''),
            font_size=dp(14), size_hint_y=0.75,
            background_color=(0.17, 0.17, 0.18, 1),
            foreground_color=(1, 1, 1, 1),
            padding=(dp(8), dp(8))
        )
        home_box.add_widget(home_label)
        home_box.add_widget(self.home_input)
        inputs.add_widget(home_box)

        # VS
        vs_label = Label(text="VS", size_hint_x=0.1, font_size=dp(13), bold=True,
                         color=(0.145, 0.957, 0.933, 1))
        inputs.add_widget(vs_label)

        # 客队
        away_box = BoxLayout(orientation='vertical', size_hint_x=0.45, spacing=dp(4))
        away_label = Label(text="客队", font_size=dp(11), size_hint_y=0.25,
                           halign='left', color=(0.145, 0.957, 0.933, 1))
        away_label.bind(size=away_label.setter('text_size'))
        self.away_input = TextInput(
            text=match_data.get('away', ''),
            font_size=dp(14), size_hint_y=0.75,
            background_color=(0.17, 0.17, 0.18, 1),
            foreground_color=(1, 1, 1, 1),
            padding=(dp(8), dp(8))
        )
        away_box.add_widget(away_label)
        away_box.add_widget(self.away_input)
        inputs.add_widget(away_box)

        self.add_widget(inputs)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg'):
            self.bg.pos = self.pos
            self.bg.size = self.size


class MainApp(App):
    """主应用"""
    use_kivy_settings = False

    def build(self):
        self.title = '赛事分析'
        self.all_matches = []
        self.selected_indices = set()
        self.match_cards = []

        # 主容器
        self.root = BoxLayout(orientation='vertical')

        with self.root.canvas.before:
            Color(0.059, 0.059, 0.059, 1)
            self.root_bg = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._update_root_bg, size=self._update_root_bg)

        # 标题
        header = BoxLayout(size_hint_y=0.12, padding=dp(16))
        title_box = BoxLayout(orientation='vertical')
        title_label = Label(
            text='赛事分析', font_size=dp(24), bold=True,
            size_hint_y=0.6, color=(1, 1, 1, 1)
        )
        subtitle_label = Label(
            text='最多可同时分析5场比赛', font_size=dp(11),
            size_hint_y=0.4, color=(0.56, 0.56, 0.58, 1)
        )
        title_box.add_widget(title_label)
        title_box.add_widget(subtitle_label)
        header.add_widget(title_box)
        self.root.add_widget(header)

        # 按钮栏
        btn_bar = BoxLayout(size_hint_y=0.1, spacing=dp(10), padding=(dp(16), 0))
        self.fetch_btn = Button(
            text='一键拉取', font_size=dp(15), bold=True,
            size_hint_x=0.5,
            background_color=(0.145, 0.957, 0.933, 1),
            color=(0.059, 0.059, 0.059, 1)
        )
        self.fetch_btn.bind(on_release=self.do_fetch)
        self.gen_btn = Button(
            text='生成提示词', font_size=dp(15), bold=True,
            size_hint_x=0.5,
            background_color=(0.996, 0.173, 0.333, 1),
            color=(1, 1, 1, 1)
        )
        self.gen_btn.bind(on_release=self.do_generate)
        btn_bar.add_widget(self.fetch_btn)
        btn_bar.add_widget(self.gen_btn)
        self.root.add_widget(btn_bar)

        # 状态标签
        self.status_label = Label(
            text='', font_size=dp(12), size_hint_y=0.05,
            color=(0.996, 0.173, 0.333, 1)
        )
        self.root.add_widget(self.status_label)

        # 内容滚动区
        self.scroll = ScrollView(size_hint_y=0.73)
        self.content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.content.bind(minimum_height=self.content.setter('height'))
        self.scroll.add_widget(self.content)
        self.root.add_widget(self.scroll)

        # 提示
        hint = Label(
            text='点击「一键拉取」获取今日竞猜赛事',
            font_size=dp(13), color=(0.56, 0.56, 0.58, 1)
        )
        self.content.add_widget(hint)

        return self.root

    def _update_root_bg(self, instance, value):
        self.root_bg.pos = self.root.pos
        self.root_bg.size = self.root.size

    def do_fetch(self, instance):
        """拉取赛事"""
        self.status_label.text = '正在拉取...'
        self.fetch_btn.disabled = True
        Clock.schedule_once(self._do_fetch_async, 0.1)

    def _do_fetch_async(self, dt):
        result = fetch_matches()
        self.fetch_btn.disabled = False

        if result.get('error'):
            self.status_label.text = f'拉取失败: {result["error"]}'
            return

        self.all_matches = result.get('matches', [])
        if not self.all_matches:
            self.status_label.text = '未拉取到赛事数据'
            return

        self.status_label.text = f'共 {len(self.all_matches)} 场赛事，请选择（最多5场）'
        self.selected_indices.clear()
        self._render_match_list()

    def _render_match_list(self):
        """渲染赛事选择列表"""
        self.content.clear_widgets()
        for i, m in enumerate(self.all_matches):
            item = MatchItem(m, i, self._on_match_toggle)
            self.content.add_widget(item)

        # 确认按钮
        confirm_btn = Button(
            text='确认选择', font_size=dp(15), bold=True,
            size_hint_y=None, height=dp(50),
            background_color=(0.996, 0.173, 0.333, 1),
            color=(1, 1, 1, 1)
        )
        confirm_btn.bind(on_release=self._confirm_selection)
        self.content.add_widget(confirm_btn)

    def _on_match_toggle(self, index, selected):
        if selected:
            if len(self.selected_indices) >= 5:
                self.status_label.text = '最多选择5场比赛'
                # 取消勾选
                for child in self.content.children:
                    if isinstance(child, MatchItem) and child.index == index:
                        child.cb.active = False
                        return
            self.selected_indices.add(index)
        else:
            self.selected_indices.discard(index)
        self.status_label.text = f'已选 {len(self.selected_indices)}/5 场'

    def _confirm_selection(self, instance):
        """确认选择，渲染输入卡片"""
        if not self.selected_indices:
            self.status_label.text = '请至少选择1场比赛'
            return

        selected = [self.all_matches[i] for i in sorted(self.selected_indices)]
        self.match_cards = []
        self.content.clear_widgets()
        self.status_label.text = f'已选 {len(selected)} 场比赛，可修改队名后生成提示词'

        for i, m in enumerate(selected):
            card = MatchInputCard(m, i)
            self.match_cards.append(card)
            self.content.add_widget(card)

    def do_generate(self, instance):
        """生成提示词"""
        if not self.match_cards:
            self.status_label.text = '请先拉取并选择赛事'
            return

        match_strs = []
        for card in self.match_cards:
            home = card.home_input.text.strip()
            away = card.away_input.text.strip()
            if home and away:
                match_strs.append(f"{home} vs {away}")

        if not match_strs:
            self.status_label.text = '请至少填写一组主队和客队'
            return

        prompt = PROMPT_TEMPLATE.format(matches='、'.join(match_strs))
        self._show_prompt_popup(prompt)

    def _show_prompt_popup(self, prompt_text):
        """显示提示词弹窗"""
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        # 提示词内容
        scroll = ScrollView()
        prompt_label = Label(
            text=prompt_text,
            font_size=dp(14),
            size_hint_y=None,
            valign='top',
            color=(1, 1, 1, 1)
        )
        prompt_label.bind(
            width=lambda *x: prompt_label.setter('text_size')(prompt_label, (x[1], None)),
            texture_size=prompt_label.setter('size')
        )
        scroll.add_widget(prompt_label)
        content.add_widget(scroll)

        # 复制按钮
        copy_btn = Button(
            text='复制全文', font_size=dp(15), bold=True,
            size_hint_y=None, height=dp(50),
            background_color=(0.996, 0.173, 0.333, 1),
            color=(1, 1, 1, 1)
        )

        popup = Popup(
            title='分析提示词',
            content=content,
            size_hint=(0.9, 0.85),
            background_color=(0.059, 0.059, 0.059, 1),
            title_color=(1, 1, 1, 1),
            separator_color=(0.17, 0.17, 0.18, 1)
        )

        def do_copy(instance):
            try:
                from kivy.clipboard import Clipboard
                Clipboard.copy(prompt_text)
                copy_btn.text = '已复制到剪贴板!'
                Clock.schedule_once(lambda dt: setattr(copy_btn, 'text', '复制全文'), 2)
            except Exception:
                copy_btn.text = '复制失败，请手动选择'
                Clock.schedule_once(lambda dt: setattr(copy_btn, 'text', '复制全文'), 2)

        copy_btn.bind(on_release=do_copy)
        content.add_widget(copy_btn)

        # 关闭按钮
        close_btn = Button(
            text='关闭', font_size=dp(15),
            size_hint_y=None, height=dp(45),
            background_color=(0.17, 0.17, 0.18, 1),
            color=(0.56, 0.56, 0.58, 1)
        )
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)

        popup.open()


if __name__ == '__main__':
    MainApp().run()
