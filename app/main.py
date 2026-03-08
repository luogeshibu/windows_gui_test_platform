from app.core.executor import GUIExecutor
from app.core.case_loader import load_case


def is_plain_text_key(key: str) -> bool:
    if not key:
        return False
    return len(key) == 1 and key.isprintable()


def run_case(case_path: str):
    case_data = load_case(case_path)
    executor = GUIExecutor(template_dir="templates", run_root="runs", threshold=0.82)

    executor.recorder.log(f"开始执行用例: {case_data['name']}")

    try:
        for idx, step in enumerate(case_data["steps"], start=1):
            action = step["action"]
            executor.recorder.log(f"STEP {idx}: {action}")
            executor.recorder.add_event({"step": idx, "action": action, "data": step})

            if action == "click_image":
                executor.click_image(
                    step["template"],
                    timeout=step.get("timeout", 10),
                    clicks=step.get("clicks", 1)
                )

            elif action == "double_click_image":
                executor.double_click_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "right_click_image":
                executor.right_click_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "move_to_image":
                executor.move_to_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "move_relative_from_image":
                executor.move_relative_from_image(
                    step["template"],
                    dx=step.get("dx", 0),
                    dy=step.get("dy", 0),
                    timeout=step.get("timeout", 10)
                )

            elif action == "click_relative_from_image":
                executor.click_relative_from_image(
                    step["template"],
                    dx=step.get("dx", 0),
                    dy=step.get("dy", 0),
                    timeout=step.get("timeout", 10)
                )

            elif action == "drag_relative_from_image":
                executor.drag_relative_from_image(
                    step["template"],
                    dx=step.get("dx", 0),
                    dy=step.get("dy", 0),
                    timeout=step.get("timeout", 10),
                    duration=step.get("duration", 0.5)
                )

            elif action == "drag_image_to_image":
                executor.drag_image_to_image(
                    step["source_template"],
                    step["target_template"],
                    timeout=step.get("timeout", 10),
                    duration=step.get("duration", 0.5)
                )

            elif action == "mouse_move":
                executor.mouse_move(
                    step["x"],
                    step["y"],
                    duration=step.get("duration", 0.1)
                )

            elif action == "click_point":
                executor.click_point(
                    step["x"],
                    step["y"]
                )

            elif action == "double_click_point":
                executor.double_click_point(
                    step["x"],
                    step["y"]
                )

            elif action == "right_click_point":
                executor.right_click_point(
                    step["x"],
                    step["y"]
                )

            elif action == "middle_click_point":
                executor.middle_click_point(
                    step["x"],
                    step["y"]
                )

            elif action == "mouse_down":
                executor.mouse_down(button=step.get("button", "left"))

            elif action == "mouse_up":
                executor.mouse_up(button=step.get("button", "left"))

            elif action == "drag_point":
                executor.drag_point(
                    start_x=step["start_x"],
                    start_y=step["start_y"],
                    end_x=step["end_x"],
                    end_y=step["end_y"],
                    duration=step.get("duration", 0.5),
                    button=step.get("button", "left")
                )

            elif action == "key_down":
                key = step["key"]
                if not is_plain_text_key(key):
                    executor.key_down(key)

            elif action == "key_up":
                key = step["key"]
                if not is_plain_text_key(key):
                    executor.key_up(key)

            elif action == "scroll":
                executor.scroll(step["amount"])

            elif action == "press_key":
                executor.press_key(step["key"])

            elif action == "hotkey":
                executor.hotkey(step["keys"])

            elif action == "type_text":
                executor.type_text(step["text"])

            elif action == "paste_text":
                executor.paste_text(step["text"])

            elif action == "sleep":
                executor.sleep(step.get("seconds", 1))

            elif action == "wait_image":
                executor.wait_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "assert_image":
                executor.assert_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "assert_not_image":
                executor.assert_not_image(
                    step["template"],
                    timeout=step.get("timeout", 10)
                )

            elif action == "scroll_until_find":
                executor.scroll_until_find(
                    move_anchor_template=step["move_anchor_template"],
                    target_template=step["target_template"],
                    max_scrolls=step.get("max_scrolls", 10),
                    scroll_amount=step.get("scroll_amount", 500)
                )

            elif action == "screenshot":
                path = executor.recorder.screenshot(step.get("name", f"step_{idx}"))
                executor.recorder.log(f"截图保存: {path}")

            else:
                raise ValueError(f"未知动作: {action}")

            shot = executor.recorder.screenshot(f"step_{idx}_{action}")
            executor.recorder.add_event({
                "step": idx,
                "status": "success",
                "screenshot": shot
            })

        executor.recorder.log("用例执行成功 ✅")
        executor.recorder.save_result(True)

    except Exception as e:
        executor.recorder.log(f"用例执行失败 ❌: {e}")
        fail_shot = executor.recorder.screenshot("fail")
        executor.recorder.add_event({
            "status": "fail",
            "error": str(e),
            "screenshot": fail_shot
        })
        executor.recorder.save_result(False, str(e))
        raise


if __name__ == "__main__":
    run_case("cases/notepadpp_case.json")