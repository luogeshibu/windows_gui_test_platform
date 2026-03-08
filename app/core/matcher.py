import os
import cv2
import numpy as np
import pyautogui


class TemplateMatcher:
    def __init__(self, template_dir: str, default_threshold: float = 0.82):
        self.template_dir = template_dir
        self.default_threshold = default_threshold

    def _template_path(self, name: str) -> str:
        path = os.path.join(self.template_dir, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"模板不存在: {path}")
        return path

    def _screenshot_gray(self):
        img = pyautogui.screenshot()
        img = np.array(img)
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    def find(self, template_name: str, threshold: float | None = None):
        threshold = threshold if threshold is not None else self.default_threshold
        screen = self._screenshot_gray()
        template = cv2.imread(self._template_path(template_name), cv2.IMREAD_GRAYSCALE)

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return None

        h, w = template.shape
        return {
            "x": int(max_loc[0] + w // 2),
            "y": int(max_loc[1] + h // 2),
            "score": float(max_val),
            "left": int(max_loc[0]),
            "top": int(max_loc[1]),
            "width": int(w),
            "height": int(h),
        }