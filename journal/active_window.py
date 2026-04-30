import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveWindow:
    app_name: str
    window_title: str = ""

    @property
    def display_name(self) -> str:
        if self.window_title:
            return f"{self.app_name} - {self.window_title}"
        return self.app_name


def _get_windows_active_window() -> ActiveWindow:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("active window handle was empty")

    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    window_title = buffer.value.strip()

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

    app_name = ""
    process_handle = kernel32.OpenProcess(0x1000 | 0x0400, False, process_id.value)
    if process_handle:
        try:
            image_buffer = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(len(image_buffer))
            if kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                image_buffer,
                ctypes.byref(size),
            ):
                app_name = image_buffer.value.rsplit("\\", maxsplit=1)[-1]
        finally:
            kernel32.CloseHandle(process_handle)

    return ActiveWindow(app_name=app_name or "Unknown app", window_title=window_title)


def _get_macos_active_window() -> ActiveWindow:
    script = """
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set appName to name of frontApp
        set windowTitle to ""
        try
            set windowTitle to name of front window of frontApp
        end try
        return appName & "\n" & windowTitle
    end tell
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    lines = result.stdout.splitlines()
    app_name = lines[0].strip() if lines else ""
    window_title = lines[1].strip() if len(lines) > 1 else ""
    if not app_name:
        raise RuntimeError("frontmost app name was empty")
    return ActiveWindow(app_name=app_name, window_title=window_title)


def _get_linux_active_window() -> ActiveWindow:
    window_title = subprocess.run(
        ["xdotool", "getactivewindow", "getwindowname"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    ).stdout.strip()
    return ActiveWindow(app_name="Active window", window_title=window_title)


def get_active_window() -> ActiveWindow:
    system = platform.system()
    if system == "Windows":
        return _get_windows_active_window()
    if system == "Darwin":
        return _get_macos_active_window()
    if system == "Linux":
        return _get_linux_active_window()
    raise RuntimeError(f"active window tracking is unsupported on {system}")
