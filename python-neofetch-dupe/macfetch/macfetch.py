#!/usr/bin/env python3
"""
macfetch - A neofetch-style system info tool for macOS.
Displays system information with an ASCII logo.
"""

import json
import os
import re
import sys
import time
import shutil
import subprocess
import platform
from pathlib import Path

# Config and assets (config.json, img.txt, neofetch.txt, etc.) are read from:
#   ~/.config/macfetch/
# Config lookup order: $MACFETCH_CONFIG, ~/.config/macfetch/config.json,
# then .macfetch_config.json in cwd or script dir.
#
#   title       bool   Show "user@host" and underline (default: true)
#   info        list   Info keys to show, in order. Only these are fetched/printed.
#   gap_spaces  int    Spaces between logo and text (default: 4)
#   logo_file   str|   Filename for logo (e.g. img.txt), or null to disable. Looked up in ~/.config/macfetch/ then script dir, cwd.
#            null
#   colors      bool   Force colors on (true) or off (false); null = auto
#
DEFAULT_CONFIG = {
    "title": True,
    "info": [
        "OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "Resolution",
        "DE", "WM", "WM Theme", "Theme", "Terminal", "CPU", "GPU", "Memory",
    ],
    "gap_spaces": 4,
    "logo_file": "neofetch.txt",
}


def _use_color(force: bool = False) -> bool:
    if force:
        return True
    if not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term.lower() in ("dumb", "unknown"):
        return False
    return True


COLOR_TITLE = ""
COLOR_AT = ""
COLOR_UNDERLINE = ""
COLOR_SUBTITLE = ""
COLOR_COLON = ""
COLOR_INFO = ""
COLOR_ASCII = ""
RESET = ""


def _init_colors(force_color: bool = False) -> None:
    global COLOR_TITLE, COLOR_AT, COLOR_UNDERLINE, COLOR_SUBTITLE
    global COLOR_COLON, COLOR_INFO, COLOR_ASCII, RESET
    if _use_color(force_color):
        COLOR_TITLE = "\033[1;32m"
        COLOR_AT = "\033[1;33m"
        COLOR_UNDERLINE = "\033[4;32m"
        COLOR_SUBTITLE = "\033[1;32m"
        COLOR_COLON = "\033[1;33m"
        COLOR_INFO = "\033[0;32m"
        COLOR_ASCII = "\033[0;32m"
        RESET = "\033[0m"
    else:
        COLOR_TITLE = COLOR_AT = COLOR_UNDERLINE = COLOR_SUBTITLE = ""
        COLOR_COLON = COLOR_INFO = COLOR_ASCII = RESET = ""


ASCII_LOGO_FALLBACK = r"""
                    c.',
                 ,xKMMX;
                oWMMMMMMW
               .KMMMMMMMX
               lMMMMMMMX.
               :NMMMMMMo
                OMMMMMk
                .XMMMx
                  cN.
""".strip("\n")


def _load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    search_paths = []
    if os.environ.get("MACFETCH_CONFIG"):
        search_paths.append(Path(os.environ["MACFETCH_CONFIG"]))
    script_dir = Path(__file__).resolve().parent
    search_paths.extend([
        Path.home() / ".config" / "macfetch" / "config.json",
        script_dir / "config.json",
        script_dir / ".macfetch_config.json",
        Path.cwd() / ".macfetch_config.json",
    ])
    for path in search_paths:
        if path.is_file():
            try:
                data = json.loads(path.read_text())
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k in DEFAULT_CONFIG:
                            config[k] = v
            except (json.JSONDecodeError, OSError):
                pass
            break
    return config


def _config_dir() -> Path:
    """Standard config/asset directory."""
    return Path.home() / ".config" / "macfetch"


def _load_logo_from_file(filename: str) -> list[str] | None:
    """Load logo from ~/.config/macfetch/, then script dir, then cwd. Neofetch or raw ASCII."""
    for base in [_config_dir(), Path(__file__).resolve().parent, Path.cwd()]:
        path = base / filename
        if not path.is_file():
            continue
        text = path.read_text()
        lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip()]
        if not lines:
            return None
        labels_in_file = [
            "OS", "Host", "Kernel", "Uptime", "Packages", "Shell", "Resolution",
            "DE", "WM", "WM Theme", "Terminal", "Terminal Font", "CPU", "GPU",
            "Memory", "GPU Driver", "CPU Usage", "Battery",
        ]
        is_neofetch = any(f" {label}: " in line for line in lines[:20] for label in labels_in_file[:5])
        if is_neofetch:
            logo_lines = []
            for i, line in enumerate(lines):
                if i >= len(labels_in_file):
                    break
                label = labels_in_file[i]
                marker = " " + label + ": "
                pos = line.find(marker)
                if pos >= 0:
                    logo_lines.append(line[:pos].rstrip())
                else:
                    logo_lines.append("")
            return logo_lines if logo_lines else None
        return lines
    return None


def run(*args: str, capture: bool = True) -> str:
    try:
        r = subprocess.run(args, capture_output=capture, text=True, timeout=5)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def run_shell(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def get_os_version() -> str:
    vers = run("sw_vers", "-productVersion") or platform.mac_ver()[0]
    build = run("sw_vers", "-buildVersion")
    name = "macOS"
    if vers:
        if vers.startswith("26."): name = "macOS Tahoe"
        elif vers.startswith("15."): name = "macOS Sequoia"
        elif vers.startswith("14."): name = "macOS Sonoma"
        elif vers.startswith("13."): name = "macOS Ventura"
        elif vers.startswith("12."): name = "macOS Monterey"
        elif vers.startswith("11."): name = "macOS Big Sur"
    return f"{name} {vers}" + (f" ({build})" if build else "")


def get_host() -> str:
    model = run("sysctl", "-n", "hw.model")
    if not model:
        return ""
    kext = run_shell("kextstat 2>/dev/null | grep -E 'FakeSMC|VirtualSMC'")
    if kext:
        return f"Hackintosh (SMBIOS: {model})"
    return model


def get_kernel() -> str:
    return run("uname", "-r") or run("uname", "-s")


def get_uptime() -> str:
    try:
        out = run("sysctl", "-n", "kern.boottime")
        if not out:
            return ""
        m = re.search(r"sec\s*=\s*(\d+)", out)
        if not m:
            return ""
        boot = int(m.group(1))
        now = int(time.time())
        s = now - boot
    except (ValueError, TypeError):
        return ""
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d} day{'s' if d != 1 else ''}")
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m or not parts:
        parts.append(f"{m} min{'s' if m != 1 else ''}")
    return ", ".join(parts)


def get_packages() -> str:
    counts = []
    cellar = os.environ.get("HOMEBREW_CELLAR", "/opt/homebrew/Cellar")
    for base in [cellar, "/opt/homebrew/Cellar", "/usr/local/Cellar"]:
        if Path(base).is_dir():
            n = len(list(Path(base).iterdir()))
            if n > 0:
                counts.append(f"{n} (brew)")
                break
    cask = os.environ.get("HOMEBREW_REPOSITORY", "/opt/homebrew") or "/usr/local"
    cask_dir = Path(cask) / "Library" / "Taps" / "homebrew" / "homebrew-cask" / "Casks"
    if not cask_dir.is_dir():
        cask_dir = Path("/usr/local/Homebrew/Library/Taps/homebrew/homebrew-cask/Casks")
    if cask_dir.is_dir():
        n = len(list(cask_dir.glob("*.rb")))
        if n > 0 and not counts:
            counts.append(f"{n} (cask)")
        elif n > 0 and counts and "cask" not in counts[0]:
            counts.append(f"{n} (cask)")
    if shutil.which("port"):
        out = run_shell("port installed 2>/dev/null | wc -l")
        if out and out.strip().isdigit():
            n = int(out.strip()) - 1
            if n > 0:
                counts.append(f"{n} (port)")
    return ", ".join(counts) if counts else ""


def get_shell() -> str:
    shell = os.environ.get("SHELL", "")
    name = Path(shell).name if shell else "unknown"
    if "bash" in name:
        out = run_shell(f'"{shell}" -c \'echo $BASH_VERSION\'')
        return f"{name} {out.split('-')[0]}" if out else name
    if "zsh" in name:
        out = run_shell(f'"{shell}" -c \'echo $ZSH_VERSION\'')
        return f"{name} {out}" if out else name
    return name


def get_resolution() -> str:
    out = run_shell(
        "system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Resolution:'"
    )
    if not out:
        return ""
    resolutions = []
    for line in out.splitlines():
        nums = re.findall(r"\d+", line)
        if len(nums) >= 2:
            resolutions.append(f"{nums[0]}x{nums[1]}")
    return ", ".join(resolutions) if resolutions else ""


def get_wm_theme() -> str:
    prefs = Path.home() / "Library" / "Preferences" / ".GlobalPreferences.plist"
    if not prefs.exists():
        return "Light"
    style = run_shell(f'defaults read "{prefs}" AppleInterfaceStyle 2>/dev/null')
    if not style or "does not exist" in style:
        style = "Light"
    color = run_shell(f'defaults read "{prefs}" AppleAccentColor 2>/dev/null')
    colors = {"-1": "Graphite", "0": "Red", "1": "Orange", "2": "Yellow", "3": "Green", "5": "Purple", "6": "Pink"}
    accent = colors.get(color.strip(), "Blue")
    return f"{accent} ({style})"


def get_cpu() -> str:
    brand = run("sysctl", "-n", "machdep.cpu.brand_string")
    logical = run("sysctl", "-n", "hw.logicalcpu_max")
    if not brand:
        return ""
    cores = f" ({logical})" if logical and logical.isdigit() else ""
    return f"{brand}{cores}"


def get_gpu() -> str:
    out = run_shell(
        "system_profiler SPDisplaysDataType 2>/dev/null | awk -F': ' '/Chipset Model:/ {print $2}'"
    )
    if out:
        return ", ".join(line.strip() for line in out.splitlines() if line.strip())
    return ""


def get_memory() -> str:
    try:
        out = run("sysctl", "-n", "hw.memsize")
        if not out or not out.isdigit():
            return ""
        total_mib = int(out) // 1024 // 1024
    except (ValueError, TypeError):
        return ""
    vm = run_shell(
        "vm_stat | awk '/Pages (active|wired|occupied)/ {sum += $3} END {print sum*4096/1024/1024}'"
    )
    try:
        used_mib = int(float(vm)) if vm else (total_mib * 70 // 100)
    except (ValueError, TypeError):
        used_mib = total_mib * 70 // 100
    total_gib = total_mib / 1024
    used_gib = used_mib / 1024
    return f"{used_gib:.2f}GiB / {total_gib:.2f}GiB"


def get_terminal() -> str:
    term = os.environ.get("TERM_PROGRAM", "")
    if term == "Apple_Terminal":
        return "Apple Terminal"
    if term == "iTerm.app":
        return "iTerm2"
    if os.environ.get("WT_SESSION"):
        return "Windows Terminal"
    if term:
        return term.replace(".app", "")
    return os.environ.get("TERM", "unknown")


def get_user_host_title() -> tuple[str, str]:
    user = os.environ.get("USER", "") or run_shell("id -un")
    host = os.environ.get("HOSTNAME", "") or run("hostname", "-s")
    if not host:
        host = run_shell("hostname")
    return user or "user", host or "mac"


def _info_registry() -> dict:
    return {
        "OS": ("OS", get_os_version),
        "Host": ("Host", get_host),
        "Kernel": ("Kernel", get_kernel),
        "Uptime": ("Uptime", get_uptime),
        "Packages": ("Packages", get_packages),
        "Shell": ("Shell", get_shell),
        "Resolution": ("Resolution", get_resolution),
        "DE": ("DE", lambda: "Aqua"),
        "WM": ("WM", lambda: "Quartz Compositor"),
        "WM Theme": ("WM Theme", get_wm_theme),
        "Theme": ("Theme", get_wm_theme),
        "Terminal": ("Terminal", get_terminal),
        "CPU": ("CPU", get_cpu),
        "GPU": ("GPU", get_gpu),
        "Memory": ("Memory", get_memory),
    }


def info(label: str, value: str, value_start_width: int) -> str:
    if not value:
        return ""
    prefix = label + ": "
    pad_len = max(0, value_start_width - len(prefix))
    return (
        f"{COLOR_SUBTITLE}{prefix}{RESET}"
        f"{' ' * pad_len}"
        f"{COLOR_INFO}{value}{RESET}"
    )


def main() -> None:
    config = _load_config()
    force_color = "--color" in sys.argv or "-c" in sys.argv or config.get("colors") is True
    if config.get("colors") is False:
        force_color = False
    _init_colors(force_color=force_color)

    registry = _info_registry()
    info_keys = config.get("info", DEFAULT_CONFIG["info"])
    # Alignment: max "Label: " width for keys we might show
    value_start_width = max(
        len(registry[k][0]) + 2 for k in info_keys if k in registry
    ) if info_keys else 0

    logo_file = config.get("logo_file", DEFAULT_CONFIG["logo_file"])
    use_logo = logo_file is not None
    gap = " " * config.get("gap_spaces", DEFAULT_CONFIG["gap_spaces"]) if use_logo else ""
    if use_logo:
        loaded = _load_logo_from_file(logo_file)
        logo_lines = list(loaded) if loaded else ASCII_LOGO_FALLBACK.splitlines()
        logo_width = max(len(ln) for ln in logo_lines) if logo_lines else 0
        n_logo_art = len(logo_lines)
        max_lines = 2 + len(info_keys)
        while len(logo_lines) < max_lines:
            logo_lines.append(" " * logo_width)
        logo_lines = [ln.ljust(logo_width) for ln in logo_lines[:max_lines]]
    else:
        logo_lines = []
        n_logo_art = 0

    def print_line(line_index: int, right: str) -> None:
        if use_logo and line_index < len(logo_lines):
            left = f"{COLOR_ASCII}{logo_lines[line_index]}{RESET}" if line_index < n_logo_art else logo_lines[line_index]
            print(left + gap + right, flush=True)
        else:
            print(right, flush=True)

    print(flush=True)
    line_index = 0

    if config.get("title", True):
        title_user, title_host = get_user_host_title()
        title_str = (
            f"{COLOR_TITLE}{title_user}{RESET}"
            f"{COLOR_AT}@{RESET}"
            f"{COLOR_TITLE}{title_host}{RESET}"
        )
        print_line(line_index, title_str)
        line_index += 1
        underline_len = len(title_user) + len(title_host) + 1
        underline = COLOR_UNDERLINE + "-" * underline_len + RESET
        print_line(line_index, underline)
        line_index += 1

    for key in info_keys:
        if key not in registry:
            continue
        label, getter = registry[key]
        value = getter()
        if value:
            print_line(line_index, info(label, value, value_start_width))
            line_index += 1

    print(flush=True)


if __name__ == "__main__":
    main()
