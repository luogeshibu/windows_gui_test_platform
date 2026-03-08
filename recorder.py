import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import keyboard
from pynput import mouse


BASE_DIR = Path(__file__).resolve().parent
CASE_DIR = BASE_DIR / "cases"
CASE_DIR.mkdir(exist_ok=True)


class AdvancedRecorder:
    """
    全量录制器（Windows 稳定修正版）
    支持：
    1. 鼠标移动
    2. 左/右/中键点击
    3. 左键双击
    4. 左键拖拽
    5. 滚轮
    6. 文本输入
    7. 单键 press_key
    8. 快捷键 hotkey（如 ctrl+s / win+d）
    9. sleep 间隔
    10. ESC 停止录制
    """

    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.running = True

        self.last_action_time: float = time.time()
        self.min_sleep_threshold: float = 0.12

        self.text_buffer: str = ""

        # 鼠标移动节流
        self.last_move_record_time: float = 0.0
        self.move_record_interval: float = 0.25

        # 键盘状态
        self.pressed_modifiers: Set[str] = set()
        self.pressed_keys: Set[str] = set()

        self.last_hotkey_time: float = 0.0
        self.hotkey_debounce: float = 0.20

        self.last_key_time: float = 0.0
        self.key_debounce: float = 0.03

        # 单独修饰键状态
        self.pending_single_modifier: Optional[str] = None
        self.modifier_used_in_combo: bool = False

        # 双击检测
        self.last_left_click_time: float = 0.0
        self.last_left_click_pos: Optional[Tuple[int, int]] = None
        self.double_click_threshold: float = 0.35
        self.double_click_distance: int = 8

        # 拖拽检测
        self.mouse_down_button: Optional[str] = None
        self.mouse_down_pos: Optional[Tuple[int, int]] = None
        self.mouse_current_pos: Optional[Tuple[int, int]] = None
        self.drag_threshold: int = 12

        self.special_key_map = {
            "enter": "enter",
            "tab": "tab",
            "backspace": "backspace",
            "delete": "delete",
            "space": "space",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "home": "home",
            "end": "end",
            "page up": "pageup",
            "page down": "pagedown",
            "insert": "insert",
            "esc": "esc",
        }

    # =========================================================
    # 通用辅助
    # =========================================================
    def _now(self) -> float:
        return time.time()

    def record_sleep(self):
        now = self._now()
        delta = now - self.last_action_time
        if delta >= self.min_sleep_threshold:
            self.steps.append({
                "action": "sleep",
                "seconds": round(delta, 2)
            })
        self.last_action_time = now

    def flush_text(self):
        if self.text_buffer:
            self.steps.append({
                "action": "type_text",
                "text": self.text_buffer
            })
            print(f"[TEXT] {self.text_buffer!r}")
            self.text_buffer = ""

    def append_step(self, step: Dict[str, Any], print_text: Optional[str] = None):
        self.flush_text()
        self.record_sleep()
        self.steps.append(step)
        if print_text:
            print(print_text)

    def normalize_key_name(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None

        name = name.lower().strip()

        if name in {"windows", "left windows", "right windows"}:
            return "win"

        if name in {"ctrl", "control", "left ctrl", "right ctrl"}:
            return "ctrl"

        if name in {"shift", "left shift", "right shift"}:
            return "shift"

        if name in {"alt", "left alt", "right alt", "alt gr"}:
            return "alt"

        if name in self.special_key_map:
            return self.special_key_map[name]

        return name

    def current_modifiers(self) -> List[str]:
        order = ["ctrl", "alt", "shift", "win"]
        return [k for k in order if k in self.pressed_modifiers]

    def is_near(self, p1: Optional[Tuple[int, int]], p2: Optional[Tuple[int, int]], max_distance=8) -> bool:
        if p1 is None or p2 is None:
            return False
        return abs(p1[0] - p2[0]) <= max_distance and abs(p1[1] - p2[1]) <= max_distance

    # =========================================================
    # 鼠标事件
    # =========================================================
    def on_move(self, x, y):
        if not self.running:
            return

        current_pos = (int(x), int(y))

        # 如果按着鼠标左键，更新当前位置，用于拖拽判断
        if self.mouse_down_button is not None:
            self.mouse_current_pos = current_pos

        now = self._now()
        if now - self.last_move_record_time < self.move_record_interval:
            return

        self.flush_text()
        self.record_sleep()

        self.steps.append({
            "action": "mouse_move",
            "x": int(x),
            "y": int(y)
        })
        self.last_move_record_time = now
        print(f"[MOVE] ({x}, {y})")

    def on_click(self, x, y, button, pressed):
        if not self.running:
            return

        button_name = str(button).split(".")[-1]
        current_pos = (int(x), int(y))
        now = self._now()

        # =========================
        # 鼠标按下
        # =========================
        if pressed:
            self.flush_text()
            self.record_sleep()

            self.mouse_down_button = button_name
            self.mouse_down_pos = current_pos
            self.mouse_current_pos = current_pos

            print(f"[MOUSE_DOWN] {button_name} ({x}, {y})")
            return

        # =========================
        # 鼠标松开
        # =========================
        if self.mouse_down_button == button_name and self.mouse_down_pos is not None:
            start_x, start_y = self.mouse_down_pos
            end_x, end_y = self.mouse_current_pos if self.mouse_current_pos else current_pos

            dx = abs(end_x - start_x)
            dy = abs(end_y - start_y)

            # 先判断是不是拖拽
            if button_name == "left" and (dx >= self.drag_threshold or dy >= self.drag_threshold):
                self.flush_text()
                self.record_sleep()

                self.steps.append({
                    "action": "drag_point",
                    "start_x": start_x,
                    "start_y": start_y,
                    "end_x": end_x,
                    "end_y": end_y,
                    "button": "left",
                    "duration": 0.5
                })
                print(f"[DRAG] left ({start_x}, {start_y}) -> ({end_x}, {end_y})")

                self.mouse_down_button = None
                self.mouse_down_pos = None
                self.mouse_current_pos = None
                self.last_left_click_time = 0.0
                self.last_left_click_pos = None
                return

        # =========================
        # 非拖拽：点击 / 双击
        # =========================
        self.flush_text()
        self.record_sleep()

        if button_name == "left":
            is_double = (
                self.last_left_click_time > 0
                and (now - self.last_left_click_time) <= self.double_click_threshold
                and self.is_near(self.last_left_click_pos, current_pos, self.double_click_distance)
            )

            if is_double:
                self.steps.append({
                    "action": "double_click_point",
                    "x": int(x),
                    "y": int(y)
                })
                print(f"[DOUBLE_CLICK] left ({x}, {y})")
                self.last_left_click_time = 0.0
                self.last_left_click_pos = None

                self.mouse_down_button = None
                self.mouse_down_pos = None
                self.mouse_current_pos = None
                return

            self.steps.append({
                "action": "click_point",
                "x": int(x),
                "y": int(y)
            })
            print(f"[CLICK] left ({x}, {y})")
            self.last_left_click_time = now
            self.last_left_click_pos = current_pos

        elif button_name == "right":
            self.steps.append({
                "action": "right_click_point",
                "x": int(x),
                "y": int(y)
            })
            print(f"[CLICK] right ({x}, {y})")

        elif button_name == "middle":
            self.steps.append({
                "action": "middle_click_point",
                "x": int(x),
                "y": int(y)
            })
            print(f"[CLICK] middle ({x}, {y})")

        self.mouse_down_button = None
        self.mouse_down_pos = None
        self.mouse_current_pos = None

    def on_scroll(self, x, y, dx, dy):
        if not self.running:
            return

        self.flush_text()
        self.record_sleep()

        amount = int(dy * 120)
        self.steps.append({
            "action": "scroll",
            "amount": amount,
            "x": int(x),
            "y": int(y)
        })
        print(f"[SCROLL] amount={amount} at ({x}, {y})")

    # =========================================================
    # 键盘事件（稳定版）
    # =========================================================
    def on_keyboard_event(self, event):
        if not self.running:
            return

        key_name = self.normalize_key_name(event.name)
        if not key_name:
            return

        if event.event_type == "down" and key_name == "esc":
            self.stop()
            return

        if event.event_type == "down":
            if key_name in {"ctrl", "shift", "alt", "win"}:
                if key_name not in self.pressed_modifiers:
                    self.pressed_modifiers.add(key_name)
                    self.pending_single_modifier = key_name
                    self.modifier_used_in_combo = False
                return

            current_mods = self.current_modifiers()
            if current_mods:
                now = self._now()
                if now - self.last_hotkey_time >= self.hotkey_debounce:
                    combo = current_mods + [key_name]
                    combo = list(dict.fromkeys(combo))

                    self.append_step(
                        {"action": "hotkey", "keys": combo},
                        print_text=f"[HOTKEY] {combo}"
                    )
                    self.last_hotkey_time = now
                    self.modifier_used_in_combo = True
                return

            if len(key_name) == 1:
                self.text_buffer += key_name
                self.last_key_time = self._now()
                return

            now = self._now()
            if now - self.last_key_time >= self.key_debounce:
                self.append_step(
                    {"action": "press_key", "key": key_name},
                    print_text=f"[KEY] {key_name}"
                )
                self.last_key_time = now
            return

        elif event.event_type == "up":
            if key_name in {"ctrl", "shift", "alt", "win"}:
                if self.pending_single_modifier == key_name and not self.modifier_used_in_combo:
                    now = self._now()
                    if now - self.last_key_time >= self.hotkey_debounce:
                        self.append_step(
                            {"action": "press_key", "key": key_name},
                            print_text=f"[KEY] {key_name}"
                        )
                        self.last_key_time = now

                if key_name in self.pressed_modifiers:
                    self.pressed_modifiers.remove(key_name)

                if self.pending_single_modifier == key_name:
                    self.pending_single_modifier = None
                    self.modifier_used_in_combo = False

    # =========================================================
    # 生命周期
    # =========================================================
    def stop(self):
        if not self.running:
            return

        self.running = False
        self.flush_text()

        case_data = {
            "name": "record_full_case",
            "steps": self.steps
        }

        output_path = CASE_DIR / "record_full_case.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        print("=" * 60)
        print(f"录制结束，已生成用例：{output_path}")
        print(f"总步骤数：{len(self.steps)}")
        print("=" * 60)

        try:
            keyboard.unhook_all()
        except Exception:
            pass

    def start(self):
        print("=" * 60)
        print("全量录制器已启动（Windows 稳定修正版）")
        print("说明：")
        print("1. 自动记录 鼠标移动 / 点击 / 双击 / 拖拽 / 滚轮 / 键盘输入 / 快捷键")
        print("2. 已增强识别 Win+D / Ctrl+S / Shift")
        print("3. 支持左键双击识别")
        print("4. 支持左键拖拽识别")
        print("5. 按 ESC 停止录制并生成 JSON")
        print("6. 建议用管理员权限运行 PowerShell / CMD")
        print("=" * 60)

        mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        mouse_listener.start()

        keyboard.hook(self.on_keyboard_event)

        try:
            while self.running:
                time.sleep(0.1)
        finally:
            mouse_listener.stop()
            try:
                keyboard.unhook_all()
            except Exception:
                pass


if __name__ == "__main__":
    recorder = AdvancedRecorder()
    recorder.start()