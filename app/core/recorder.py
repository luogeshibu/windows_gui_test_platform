import json
import os
import time
import pyautogui


class RunRecorder:
    def __init__(self, run_root="runs"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(run_root, ts)
        self.screen_dir = os.path.join(self.run_dir, "screens")
        os.makedirs(self.screen_dir, exist_ok=True)
        self.log_file = os.path.join(self.run_dir, "run.log")
        self.result_file = os.path.join(self.run_dir, "result.json")
        self.events = []

    def log(self, msg: str):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def screenshot(self, name: str):
        path = os.path.join(self.screen_dir, f"{time.strftime('%H%M%S')}_{name}.png")
        pyautogui.screenshot(path)
        return path

    def add_event(self, event: dict):
        event["ts"] = time.time()
        self.events.append(event)

    def save_result(self, success: bool, error: str | None = None):
        with open(self.result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "success": success,
                    "error": error,
                    "events": self.events
                },
                f,
                ensure_ascii=False,
                indent=2
            )