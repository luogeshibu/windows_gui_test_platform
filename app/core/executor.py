import time
import pyautogui
from app.core.matcher import TemplateMatcher
from app.core.recorder import RunRecorder


class GUIExecutor:
    def __init__(self, template_dir="templates", run_root="runs", threshold=0.82):
        self.matcher = TemplateMatcher(template_dir, threshold)
        self.recorder = RunRecorder(run_root)

    # =========================
    # 通用
    # =========================
    def _release_modifiers(self):
        """
        释放残留修饰键，避免输入和快捷键串键。
        """
        for key in ["shift", "ctrl", "alt", "win"]:
            try:
                pyautogui.keyUp(key)
            except Exception:
                pass

    # =========================
    # 图像匹配类动作
    # =========================
    def wait_image(self, template, timeout=10, threshold=None, interval=0.4):
        end_time = time.time() + timeout
        while time.time() < end_time:
            pos = self.matcher.find(template, threshold)
            if pos:
                return pos
            time.sleep(interval)
        raise TimeoutError(f"等待图片超时: {template}")

    def click_image(self, template, timeout=10, threshold=None, clicks=1):
        pos = self.wait_image(template, timeout, threshold)
        if clicks == 2:
            pyautogui.doubleClick(pos["x"], pos["y"])
        else:
            pyautogui.click(pos["x"], pos["y"])
        return pos

    def double_click_image(self, template, timeout=10, threshold=None):
        return self.click_image(template, timeout, threshold, clicks=2)

    def right_click_image(self, template, timeout=10, threshold=None):
        pos = self.wait_image(template, timeout, threshold)
        pyautogui.rightClick(pos["x"], pos["y"])
        return pos

    def move_to_image(self, template, timeout=10, threshold=None):
        pos = self.wait_image(template, timeout, threshold)
        pyautogui.moveTo(pos["x"], pos["y"], duration=0.2)
        return pos

    def move_relative_from_image(self, template, dx=0, dy=0, timeout=10, threshold=None):
        pos = self.wait_image(template, timeout, threshold)
        x = pos["x"] + dx
        y = pos["y"] + dy
        pyautogui.moveTo(x, y, duration=0.2)
        return {"x": x, "y": y}

    def click_relative_from_image(self, template, dx=0, dy=0, timeout=10, threshold=None):
        pos = self.wait_image(template, timeout, threshold)
        x = pos["x"] + dx
        y = pos["y"] + dy
        pyautogui.click(x, y)
        return {"x": x, "y": y}

    def drag_relative_from_image(self, template, dx=0, dy=0, timeout=10, threshold=None, duration=0.5):
        pos = self.wait_image(template, timeout, threshold)
        start_x = pos["x"]
        start_y = pos["y"]
        end_x = start_x + dx
        end_y = start_y + dy

        pyautogui.moveTo(start_x, start_y, duration=0.2)
        pyautogui.mouseDown(button="left")
        pyautogui.moveTo(end_x, end_y, duration=duration)
        pyautogui.mouseUp(button="left")

        return {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y
        }

    def drag_image_to_image(self, source_template, target_template, timeout=10, threshold=None, duration=0.5):
        src = self.wait_image(source_template, timeout, threshold)
        dst = self.wait_image(target_template, timeout, threshold)

        pyautogui.moveTo(src["x"], src["y"], duration=0.2)
        pyautogui.mouseDown(button="left")
        pyautogui.moveTo(dst["x"], dst["y"], duration=duration)
        pyautogui.mouseUp(button="left")
        return {"source": src, "target": dst}

    # =========================
    # 鼠标基础动作
    # =========================
    def mouse_move(self, x, y, duration=0.1):
        pyautogui.moveTo(x, y, duration=duration)

    def click_point(self, x, y):
        pyautogui.click(x, y)

    def right_click_point(self, x, y):
        pyautogui.rightClick(x, y)

    def middle_click_point(self, x, y):
        pyautogui.middleClick(x, y)

    def mouse_down(self, button="left"):
        pyautogui.mouseDown(button=button)

    def mouse_up(self, button="left"):
        pyautogui.mouseUp(button=button)

    def drag_point(self, start_x, start_y, end_x, end_y, duration=0.5, button="left"):
        pyautogui.moveTo(start_x, start_y, duration=0.1)
        pyautogui.mouseDown(button=button)
        pyautogui.moveTo(end_x, end_y, duration=duration)
        pyautogui.mouseUp(button=button)

    def scroll(self, amount):
        pyautogui.scroll(amount)

    # =========================
    # 键盘动作
    # =========================
    def press_key(self, key):
        self._release_modifiers()
        pyautogui.press(key)

    def key_down(self, key):
        pyautogui.keyDown(key)

    def key_up(self, key):
        pyautogui.keyUp(key)

    def hotkey(self, keys):
        """
        对常见组合键做增强处理，尤其是 win+d。
        """
        self._release_modifiers()
        normalized = [k.lower() for k in keys]

        # Windows 组合键增强处理
        if normalized == ["win", "d"]:
            pyautogui.keyDown("win")
            time.sleep(0.05)
            pyautogui.press("d")
            time.sleep(0.05)
            pyautogui.keyUp("win")
            return

        if normalized == ["win", "e"]:
            pyautogui.keyDown("win")
            time.sleep(0.05)
            pyautogui.press("e")
            time.sleep(0.05)
            pyautogui.keyUp("win")
            return

        # 常见快捷键增强
        if normalized == ["ctrl", "s"]:
            pyautogui.keyDown("ctrl")
            time.sleep(0.03)
            pyautogui.press("s")
            time.sleep(0.03)
            pyautogui.keyUp("ctrl")
            return

        if normalized == ["ctrl", "o"]:
            pyautogui.keyDown("ctrl")
            time.sleep(0.03)
            pyautogui.press("o")
            time.sleep(0.03)
            pyautogui.keyUp("ctrl")
            return

        if normalized == ["alt", "f4"]:
            pyautogui.keyDown("alt")
            time.sleep(0.03)
            pyautogui.press("f4")
            time.sleep(0.03)
            pyautogui.keyUp("alt")
            return

        # 默认通用写法
        pyautogui.hotkey(*normalized)

    def type_text(self, text):
        """
        普通逐字输入。
        建议短英文用它，复杂文本优先 paste_text。
        """
        self._release_modifiers()
        pyautogui.write(text, interval=0.03)

    def paste_text(self, text):
        """
        更稳的输入方式，适合标点、大写、长文本。
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            self._release_modifiers()
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pyautogui.write(text, interval=0.03)

    def sleep(self, seconds):
        time.sleep(seconds)

    # =========================
    # 断言 / 查找类动作
    # =========================
    def assert_image(self, template, timeout=10, threshold=None):
        return self.wait_image(template, timeout, threshold)

    def assert_not_image(self, template, timeout=10, threshold=None):
        end_time = time.time() + timeout
        while time.time() < end_time:
            if self.matcher.find(template, threshold) is None:
                return True
            time.sleep(0.3)
        raise AssertionError(f"模板仍然存在: {template}")

    def scroll_until_find(self, move_anchor_template, target_template, max_scrolls=10, scroll_amount=500):
        pos = self.wait_image(move_anchor_template, timeout=10)
        pyautogui.moveTo(pos["x"] - 30, pos["y"], duration=0.2)

        for _ in range(max_scrolls):
            target = self.matcher.find(target_template)
            if target:
                return target
            pyautogui.scroll(scroll_amount)
            time.sleep(0.3)

        raise TimeoutError(f"滚动后仍未找到模板: {target_template}")