#!/usr/bin/env python3
"""
TermiChat - AI Terminal Assistant
Features: Config, Chat Sessions, Syntax Highlighting, Themes, History Search, Markdown Render
Powered by Ollama
"""

import ollama
import requests
import sys
import re
import os
import json
import shutil
import subprocess
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

# Enable Windows VT mode for ANSI colors
def enable_windows_vt_mode():
    """Enable Virtual Terminal mode on Windows for ANSI color support"""
    try:
        if sys.platform == 'win32':
            kernel32 = ctypes.windll.kernel32
            # Get current console mode
            STD_OUTPUT_HANDLE = -11
            hConsole = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(hConsole, ctypes.byref(mode))
            # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
            mode.value |= 0x0004
            kernel32.SetConsoleMode(hConsole, mode)
            # Same for error output
            STD_ERROR_HANDLE = -12
            hConsole = kernel32.GetStdHandle(STD_ERROR_HANDLE)
            kernel32.GetConsoleMode(hConsole, ctypes.byref(mode))
            mode.value |= 0x0004
            kernel32.SetConsoleMode(hConsole, mode)
            return True
    except:
        pass
    return False

# Try to enable VT mode at startup
VT_ENABLED = enable_windows_vt_mode()

# 256-color to basic ANSI mapping for fallback
COLOR_256_TO_BASIC = {
    # Grays
    245: 90,  # dim gray
    145: 90,  # bright black
    # Monokai colors
    141: 35,  # purple/magenta
    117: 94,  # light blue
    81: 96,   # cyan
    118: 92,  # light green
    228: 93,  # yellow
    203: 91,  # red/pink
    # Nord colors
    175: 35,  # light purple
    75: 94,   # blue
    73: 96,   # cyan
    72: 92,   # green
    180: 33,  # yellow
    168: 91,  # red
}

# Try imports
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import Terminal256Formatter
    PYGMENTS = True
except ImportError:
    PYGMENTS = False

try:
    import pyperclip
    CLIPBOARD = True
except ImportError:
    CLIPBOARD = False

# ============================================================
# Themes
# ============================================================

def convert_256_color(code: str) -> str:
    """Convert 256-color ANSI code to basic ANSI if VT not enabled"""
    if VT_ENABLED:
        return code

    # Extract color number from \033[38;5;Xm format
    match = re.match(r'\033\[38;5;(\d+)m', code)
    if match:
        color_num = int(match.group(1))
        basic = COLOR_256_TO_BASIC.get(color_num, 37)  # Default to white
        return f'\033[{basic}m'
    return code


class Theme:
    """Color themes for TermiChat"""

    themes_raw = {
        "dark": {
            "header": '\033[95m',   # Magenta
            "blue": '\033[94m',     # Blue
            "cyan": '\033[96m',     # Cyan
            "green": '\033[92m',    # Green
            "yellow": '\033[93m',   # Yellow
            "red": '\033[91m',      # Red
            "bold": '\033[1m',
            "dim": '\033[2m',
            "reset": '\033[0m',
            "bg": '\033[40m',       # Black bg
        },
        "light": {
            "header": '\033[35m',   # Purple
            "blue": '\033[34m',     # Dark Blue
            "cyan": '\033[36m',     # Dark Cyan
            "green": '\033[32m',    # Dark Green
            "yellow": '\033[33m',   # Brown/Yellow
            "red": '\033[31m',      # Dark Red
            "bold": '\033[1m',
            "dim": '\033[90m',      # Bright black (gray)
            "reset": '\033[0m',
            "bg": '\033[47m',       # White bg
        },
        "monokai": {
            "header": '\033[38;5;141m',  # Purple
            "blue": '\033[38;5;117m',    # Light blue
            "cyan": '\033[38;5;81m',     # Cyan
            "green": '\033[38;5;118m',   # Light green
            "yellow": '\033[38;5;228m',   # Yellow
            "red": '\033[38;5;203m',     # Red/Pink
            "bold": '\033[1m',
            "dim": '\033[38;5;245m',     # Gray
            "reset": '\033[0m',
            "bg": '',
        },
        "nord": {
            "header": '\033[38;5;175m',  # Light purple
            "blue": '\033[38;5;75m',     # Blue
            "cyan": '\033[38;5;73m',     # Cyan
            "green": '\033[38;5;72m',    # Green
            "yellow": '\033[38;5;180m',  # Yellow
            "red": '\033[38;5;168m',    # Red
            "bold": '\033[1m',
            "dim": '\033[38;5;145m',     # Bright black
            "reset": '\033[0m',
            "bg": '',
        }
    }

    # Convert all 256-color codes based on VT support
    themes = {name: {k: convert_256_color(v) for k, v in colors.items()} for name, colors in themes_raw.items()}

    def __init__(self, name: str = "dark"):
        self.name = name
        self.colors = self.themes.get(name, self.themes["dark"])

    def __getitem__(self, key):
        return self.colors.get(key, self.themes["dark"].get(key, ''))

    @classmethod
    def list_themes(cls):
        return list(cls.themes.keys())

# ============================================================
# Markdown Renderer
# ============================================================

class MarkdownRenderer:
    """Simple markdown renderer for terminal"""

    def __init__(self, theme: Theme):
        self.theme = theme

    def render(self, text: str) -> str:
        """Convert markdown to ANSI colored text"""
        lines = text.split('\n')
        result = []
        in_code_block = False
        code_lang = ""

        for line in lines:
            # Code blocks
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    lang = line.strip()[3:].strip()
                    code_lang = lang if lang else "text"
                    result.append(f"{self.theme['dim']}{'─' * 50}{self.theme['reset']}")
                    continue
                else:
                    in_code_block = False
                    result.append(f"{self.theme['dim']}{'─' * 50}{self.theme['reset']}")
                    continue

            if in_code_block:
                # Render code line (simplified - no syntax highlighting here, done separately)
                result.append(f"  {self.theme['dim']}{line}{self.theme['reset']}")
                continue

            # Headers
            if line.startswith('# '):
                result.append(f"\n{self.theme['bold']}{self.theme['header']}{line[2:]}{self.theme['reset']}")
                continue
            elif line.startswith('## '):
                result.append(f"\n{self.theme['bold']}{self.theme['blue']}{line[3:]}{self.theme['reset']}")
                continue
            elif line.startswith('### '):
                result.append(f"\n{self.theme['cyan']}{line[4:]}{self.theme['reset']}")
                continue

            # Bold and italic
            line = re.sub(r'\*\*(.+?)\*\*', f'{self.theme["bold"]}\\1{self.theme["reset"]}', line)
            line = re.sub(r'\*(.+?)\*', f'{self.theme["dim"]}\\1{self.theme["reset"]}', line)
            line = re.sub(r'`(.+?)`', f'{self.theme["yellow"]}\\1{self.theme["reset"]}', line)

            # Lists
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                line = re.sub(r'^(\s*)([-*])\s+', f'\\1{self.theme["cyan"]}•{self.theme["reset"]} ', line)

            # Numbered lists
            line = re.sub(r'^(\s*)(\d+)\.\s+', f'\\1{self.theme["cyan"]}\\2.{self.theme["reset"]} ', line)

            # Links (show URL)
            line = re.sub(r'\[(.+?)\]\((.+?)\)', f'{self.theme["blue"]}\\1{self.theme["reset"]}', line)

            # Horizontal rule
            if line.strip() in ['---', '***', '___']:
                result.append(f"{self.theme['dim']}{'─' * 50}{self.theme['reset']}")
                continue

            result.append(line)

        return '\n'.join(result)

# ============================================================
# History Search (Ctrl+R style)
# ============================================================

class HistorySearch:
    """Command history with search (Ctrl+R style)"""

    def __init__(self):
        self.history: List[str] = []
        self.position = 0
        self.search_mode = False
        self.search_query = ""
        self.original_prompt = ""

    def add(self, command: str):
        """Add command to history"""
        if command and command.strip():
            # Don't add duplicates
            if not self.history or self.history[-1] != command:
                self.history.append(command)
        self.position = len(self.history)

    def search(self, query: str) -> Optional[str]:
        """Search history for query"""
        if not query:
            return None

        query = query.lower()
        # Search backwards from current position
        for i in range(len(self.history) - 1, -1, -1):
            if query in self.history[i].lower():
                return self.history[i]
        return None

    def get_previous(self) -> Optional[str]:
        """Get previous command"""
        if self.history and self.position > 0:
            self.position -= 1
            return self.history[self.position]
        return None

    def get_next(self) -> Optional[str]:
        """Get next command"""
        if self.position < len(self.history):
            self.position += 1
            if self.position < len(self.history):
                return self.history[self.position]
        return ""

# ============================================================
# Error Handling
# ============================================================

class TermiChatError(Exception):
    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

class OllamaConnectionError(TermiChatError):
    def __init__(self):
        super().__init__(
            message="Tidak bisa connect ke Ollama server",
            suggestion=(
                f"\n{self._s('Solusi')}\n"
                f"  1. Pastikan Ollama sudah diinstall\n"
                f"     https://ollama.com\n\n"
                f"  2. Jalankan Ollama:\n"
                f"     ollama serve\n\n"
                f"  3. Atau tutup & buka terminal baru, lalu jalankan 'cc'\n"
            )
        )

class ModelNotFoundError(TermiChatError):
    def __init__(self, model: str):
        super().__init__(
            message=f"Model '{model}' tidak ditemukan",
            suggestion=(
                f"\n{self._s('Solusi')}\n"
                f"  1. Install model:\n"
                f"     ollama pull {model}\n\n"
                f"  2. Atau gunakan model lain:\n"
                f"     /models (untuk lihat model yang tersedia)\n"
                f"     /model llama3\n"
            )
        )

class NetworkError(TermiChatError):
    def __init__(self):
        super().__init__(
            message="Koneksi internet bermasalah",
            suggestion=(
                f"\n{self._s('Solusi')}\n"
                f"  1. Cek koneksi internet kamu\n\n"
                f"  2. Jika pakai proxy, set:\n"
                f"     export HTTP_PROXY=http://proxy:port\n"
            )
        )

class FileError(TermiChatError):
    def __init__(self, operation: str, filename: str):
        super().__init__(
            message=f"Gagal {operation} file: {filename}",
            suggestion=(
                f"\n{self._s('Solusi')}\n"
                f"  1. Cek apakah file/path ada\n"
                f"  2. Cek permission file\n"
            )
        )

class CodeExecutionError(TermiChatError):
    def __init__(self, error_type: str, details: str):
        super().__init__(
            message=f"Error saat menjalankan code: {error_type}",
            suggestion=(
                f"\n{self._s('Detail')}\n"
                f"  {details}\n\n"
                f"{self._s('Solusi')}\n"
                f"  1. Perbaiki error di code\n"
                f"  2. Minta AI untuk fix: 'perbaiki error ini'\n"
            )
        )

    def _s(self, text):
        return f"{self.theme['cyan'] if hasattr(self, 'theme') else ''}{text}:"

def print_error(error: TermiChatError, theme: Theme = None):
    """Print error with formatting"""
    if theme is None:
        theme = Theme("dark")

    print(f"\n{theme['red']}{'='*50}{theme['reset']}")
    print(f"{theme['red']}✗ {error.message}{theme['reset']}")
    if error.suggestion:
        print(error.suggestion)
    print(f"{theme['red']}{'='*50}{theme['reset']}\n")

# ============================================================
# Ollama Utilities
# ============================================================

def check_ollama_connection() -> bool:
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=3)
        return response.status_code == 200
    except:
        return False

def check_model_exists(model: str) -> bool:
    try:
        models = get_available_models()
        if model in models:
            return True
        if f"{model}:latest" in models:
            return True
        for m in models:
            if model in m or m in model:
                return True
        return False
    except:
        return False

def get_available_models() -> List[str]:
    try:
        resp = ollama.list()
        models = []
        for m in resp.get('models', []):
            name = getattr(m, 'model', None) or m.get('model', '')
            if name:
                models.append(name)
        return models
    except:
        return []

def auto_start_ollama() -> bool:
    import platform
    system = platform.system().lower()

    ollama_paths = [
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
        Path("ollama.exe"),
    ]

    for path in ollama_paths:
        if path.exists():
            try:
                subprocess.Popen([str(path), "serve"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               start_new_session=True)
                import time
                for _ in range(10):
                    time.sleep(1)
                    if check_ollama_connection():
                        return True
            except:
                pass
    return False

# ============================================================
# Config Management
# ============================================================

class Config:
    DEFAULT = {
        "model": "llama3",
        "project_path": None,
        "theme": "dark",
        "auto_save": True,
        "save_interval": 60,
        "max_history": 100,
        "show_line_numbers": True,
        "stream_response": True,
        "auto_start_ollama": True,
        "markdown_render": True
    }

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path.home() / ".termichat"

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "config.json"
        self.data = self.load()

    def load(self) -> Dict:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding='utf-8'))
                config = self.DEFAULT.copy()
                config.update(data)
                return config
            except:
                pass
        return self.DEFAULT.copy()

    def save(self):
        try:
            self.config_file.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
            return True
        except:
            return False

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def get(self, key, default=None):
        """Get config value with default fallback"""
        return self.data.get(key, default)

# ============================================================
# Session Management
# ============================================================

class Session:
    def __init__(self, session_dir: Path = None, name: str = None):
        if session_dir is None:
            session_dir = Path.home() / ".termichat" / "sessions"

        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if name is None:
            name = datetime.now().strftime("%Y-%m-%d_%H-%M")

        self.name = name
        self.file = self.session_dir / f"{name}.json"

        if self.file.exists():
            self.load()
        else:
            self.messages = []
            self.metadata = {
                "created": datetime.now().isoformat(),
                "model": "llama3",
                "project_path": None
            }

    def load(self):
        try:
            data = json.loads(self.file.read_text(encoding='utf-8'))
            self.messages = data.get("messages", [])
            self.metadata = data.get("metadata", {})
        except:
            self.messages = []
            self.metadata = {}

    def save(self):
        try:
            data = {
                "messages": self.messages,
                "metadata": self.metadata
            }
            self.file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            return True
        except:
            return False

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def list_sessions(self) -> List[Dict]:
        sessions = []
        for f in sorted(self.session_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                meta = data.get("metadata", {})
                sessions.append({
                    "name": f.stem,
                    "file": f,
                    "created": meta.get("created", ""),
                    "model": meta.get("model", ""),
                    "message_count": len(data.get("messages", []))
                })
            except:
                pass
        return sessions

    @staticmethod
    def delete(name: str, session_dir: Path = None) -> bool:
        if session_dir is None:
            session_dir = Path.home() / ".termichat" / "sessions"
        file_path = session_dir / f"{name}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except:
                pass
        return False

# ============================================================
# Helper Functions
# ============================================================

def highlight_code(code: str, lang: str = "python") -> str:
    if PYGMENTS and VT_ENABLED:
        try:
            lexer = get_lexer_by_name(lang)
            formatter = Terminal256Formatter(style='monokai')
            return highlight(code, lexer, formatter)
        except:
            pass
    elif PYGMENTS:
        try:
            lexer = get_lexer_by_name(lang)
            formatter = Terminal256Formatter(style='monokai')
            result = highlight(code, lexer, formatter)
            # Convert 256-color codes to basic ANSI
            def convert_256(s):
                match = re.match(r'\033\[38;5;(\d+)m', s)
                if match:
                    color = int(match.group(1))
                    basic = COLOR_256_TO_BASIC.get(color, 37)
                    return f'\033[{basic}m'
                return s
            return re.sub(r'\033\[38;5;\d+m', convert_256, result)
        except:
            pass
    return code

def get_project_files(project_path: str = None) -> List[Path]:
    if not project_path:
        return []
    files = []
    path = Path(project_path)
    if not path.exists():
        return []
    extensions = ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'go', 'rs',
                  'rb', 'php', 'html', 'css', 'json', 'yaml', 'yml']
    for ext in extensions:
        try:
            files.extend(path.rglob(f'*.{ext}'))
        except:
            pass
    return sorted(files)

def read_file(filename: str, project_path: str = None) -> Optional[str]:
    base_path = Path(project_path) if project_path else Path.cwd()
    file_path = base_path / filename if project_path else Path(filename)
    if not file_path.exists():
        return None
    try:
        return file_path.read_text(encoding='utf-8')
    except:
        return None

def save_file(filename: str, content: str, project_path: str = None, is_fix: bool = False) -> bool:
    base_path = Path(project_path) if project_path else Path.cwd()
    path = base_path / filename if project_path else Path(filename)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_fix and path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            shutil.copy2(path, backup_path)
        path.write_text(content, encoding='utf-8')
        return True
    except:
        return False

def extract_code_blocks(response: str) -> Tuple[List, List]:
    new_files = []
    fixed_files = []

    for match in re.finditer(r'\[FILE:(\S+)\](.*?)\[/FILE\]', response, re.DOTALL):
        filename = match.group(1)
        code = clean_code(match.group(2))
        if code.strip():
            new_files.append((filename, code))

    for match in re.finditer(r'\[FIX:(\S+)\](.*?)\[/FIX\]', response, re.DOTALL):
        filename = match.group(1)
        code = clean_code(match.group(2))
        if code.strip():
            fixed_files.append((filename, code))

    md_pattern = r'```(\w*)\n?(.*?)```'
    for match in re.finditer(md_pattern, response, re.DOTALL):
        lang = match.group(1) or 'text'
        raw_code = match.group(2)
        start = match.start()
        is_inside = any(m.start() < start < m.end() for m in
                       re.finditer(r'\[(?:FILE|FIX):[^\]]+\]', response))
        if is_inside:
            continue

        code = clean_code(raw_code)
        if not code.strip():
            continue

        before = response[:start].lower()
        is_fix = any(x in before for x in ['fix', 'perbaiki', 'bug', 'error', 'correct'])
        fn_match = re.search(r'(?:file|filename)[:\s]+[`"]?([\w./\\]+)[`"]?', response, re.I)
        filename = fn_match.group(1) if fn_match else f"code.{lang}"

        if is_fix:
            fixed_files.append((filename, code))
        else:
            new_files.append((filename, code))

    return new_files, fixed_files

def clean_code(code: str) -> str:
    code = re.sub(r'\[(?:FILE|FIX):[^\]]+\]', '', code)
    lines = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('[/FILE') or stripped.startswith('[/FIX') or stripped.startswith('```'):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()

def display_code(filename: str, code: str, theme: Theme, is_fix: bool = False):
    ext = Path(filename).suffix.lstrip('.')
    lang_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'java': 'java', 'cpp': 'cpp', 'c': 'c', 'go': 'go',
        'rs': 'rust', 'html': 'html', 'css': 'css', 'json': 'json'
    }
    lang = lang_map.get(ext, 'text')

    prefix = f"{theme['yellow']}[FIX]{theme['reset']}" if is_fix else f"{theme['green']}[NEW]{theme['reset']}"
    print(f"\n{prefix} {theme['bold']}{filename}{theme['reset']}")

    lines = code.split('\n')
    max_num = len(str(len(lines)))
    highlighted = highlight_code(code, lang)

    for i, line in enumerate(highlighted.split('\n'), 1):
        print(f"  {theme['dim']}{i:>{max_num}}{theme['reset']} │ {line.rstrip()}")
    print(f"  {'─' * max_num}┼{'─' * 50}")

    if CLIPBOARD:
        print(f"  {theme['dim']}[c] Copy | [r] Run (Python){theme['reset']}")
    elif ext == 'py':
        print(f"  {theme['dim']}[r] Run{theme['reset']}")

def run_python(code: str, theme: Theme) -> bool:
    temp_file = Path.home() / ".termichat_temp.py"
    try:
        temp_file.write_text(code, encoding='utf-8')
        print(f"\n{theme['cyan']}--- Running... ---{theme['reset']}\n")

        result = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True, text=True, timeout=30
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            raise CodeExecutionError("Runtime Error", result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"{theme['red']}Timeout! Code terlalu lama (>30 detik){theme['reset']}")
        return False
    except CodeExecutionError as e:
        print_error(e, theme)
        return False
    except Exception as e:
        print(f"{theme['red']}Error: {e}{theme['reset']}")
        return False
    finally:
        temp_file.unlink(missing_ok=True)

def copy_to_clipboard(code: str, theme: Theme):
    if CLIPBOARD:
        try:
            pyperclip.copy(code)
            print(f"\n{theme['green']}✓ Copied to clipboard!{theme['reset']}")
        except:
            print(f"{theme['yellow']}Could not copy to clipboard{theme['reset']}")

# ============================================================
# Input Handler with History Search
# ============================================================

def get_input(prompt: str, history: HistorySearch, theme: Theme) -> str:
    """Get input with history navigation and search"""

    try:
        import readline
        # Setup readline
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode vi')

        current = ""
        history_position = len(history.history)

        while True:
            try:
                char = input(prompt + current)
                return current + char
            except KeyboardInterrupt:
                return ""
            except EOFError:
                return ""

    except ImportError:
        # Fallback: simple input without fancy features
        return input(prompt)

# ============================================================
# Main Application
# ============================================================

class TermiChat:
    SYSTEM_PROMPT = """Kamu asisten AI yang helpful dan friendly.
Kamu bisa: ngobrol, buatin code, dan fix code.

Format code BARU: [FILE:nama.py]
```python
code
```
[/FILE]

Format FIX code: [FIX:nama.py]
```python
code
```
[/FIX]

Gunakan markdown untuk response agar lebih rapi.
Jawab natural."""

    def __init__(self):
        self.config = Config()
        self.session = Session()
        self.session.metadata["model"] = self.config["model"]
        self.session.metadata["project_path"] = self.config["project_path"]

        self.model = self.config["model"]
        self.project_path = self.config["project_path"]
        self.theme = Theme(self.config["theme"])
        self.markdown = MarkdownRenderer(self.theme)
        self.history = HistorySearch()
        self.pending_code = None

    def print_banner(self):
        ollama_status = f"{self.theme['green']}✓ Connected{self.theme['reset']}" if check_ollama_connection() else f"{self.theme['red']}✗ Not Running{self.theme['reset']}"

        themes = Theme.list_themes()
        current_theme = self.config["theme"]

        print(f"""
{self.theme['header']}╔═══════════════════════════════════════════════════════╗
║    {self.theme['bold']}TermiChat - AI Terminal Assistant{self.theme['reset']}{self.theme['header']}           ║
║    Theme: {current_theme}                                     ║
╚═══════════════════════════════════════════════════════╝{self.theme['reset']}

{self.theme['cyan']}Ollama:{self.theme['reset']} {ollama_status}
{self.theme['cyan']}Model:{self.theme['reset']} {self.model}
{self.theme['cyan']}Session:{self.theme['reset']} {self.session.name}
{self.theme['cyan']}Project:{self.theme['reset']} {self.project_path or "None"}
{self.theme['cyan']}Theme:{self.theme['reset']} {current_theme}

Commands:
  /project <path>   Set project directory
  /read <file>     Read file
  /files           List project files
  /model <name>    Switch AI model
  /models          List available models
  /restart         Restart Ollama
  /theme <name>    Change theme ({', '.join(themes)})
  /sessions        List saved sessions
  /save [name]     Save current session
  /load [name>     Load session
  /delete <name>   Delete session
  /config          Show config
  /set <key> <val> Set config
  /clear           Clear messages
  /exit            Save & exit

{self.theme['dim']}Tips: ↑↓ for history | Ctrl+R to search | Markdown enabled{self.theme['reset']}
""")

    def get_project_context(self) -> str:
        if not self.project_path:
            return ""
        files = get_project_files(self.project_path)
        if not files:
            return ""
        context = f"\n[PROJECT: {self.project_path}]\n[FILES:]\n"
        context += '\n'.join([f"- {f.relative_to(Path(self.project_path))}" for f in files[:30]])
        return context

    def render_response(self, response: str) -> str:
        """Render response with markdown if enabled"""
        if self.config.get("markdown_render", True):
            return self.markdown.render(response)
        return response

    def chat(self, user_input: str) -> Optional[str]:
        self.session.add_message("user", user_input)
        self.history.add(user_input)

        if not check_ollama_connection():
            if self.config.get("auto_start_ollama", True):
                print(f"\n{self.theme['yellow']}⚠ Ollama not running, trying to start...{self.theme['reset']}")
                if auto_start_ollama():
                    print(f"{self.theme['green']}✓ Ollama started{self.theme['reset']}\n")
                else:
                    print(f"{self.theme['red']}✗ Could not start Ollama automatically{self.theme['reset']}\n")

            if not check_ollama_connection():
                print_error(OllamaConnectionError(), self.theme)
                self.session.messages.pop()
                return None

        if not check_model_exists(self.model):
            available = get_available_models()
            err = ModelNotFoundError(self.model)
            print_error(err, self.theme)
            if available:
                print(f"{self.theme['cyan']}Model yang tersedia:{self.theme['reset']} {', '.join(available)}")
            self.session.messages.pop()
            return None

        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        context = self.get_project_context()
        if context:
            messages.append({"role": "system", "content": context})

        for msg in self.session.messages[-30:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = ollama.chat(model=self.model, messages=messages, stream=True)
            full_response = ""

            print(f"\n{self.theme['green']}●{self.theme['reset']} ", end="", flush=True)

            for chunk in response:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                sys.stdout.flush()
                full_response += content

            print()
            self.session.add_message("assistant", full_response)
            return full_response

        except requests.exceptions.ConnectionError:
            print_error(OllamaConnectionError(), self.theme)
            self.session.messages.pop()
            return None
        except Exception as e:
            print(f"\n{self.theme['red']}✗ Error: {e}{self.theme['reset']}")
            self.session.messages.pop()
            return None

    def process_response(self, response: str):
        try:
            new_files, fixed_files = extract_code_blocks(response)

            for filename, code in new_files:
                try:
                    save_file(filename, code, self.project_path)
                    display_code(filename, code, self.theme)
                    print(f"  {self.theme['green']}✓ Saved: {filename}{self.theme['reset']}")
                    if filename.endswith('.py'):
                        self.pending_code = (filename, code)
                except Exception as e:
                    print(f"{self.theme['red']}✗ Error saving {filename}: {e}{self.theme['reset']}")

            for filename, code in fixed_files:
                try:
                    old_code = read_file(filename, self.project_path)
                    if old_code:
                        print(f"\n{self.theme['yellow']}--- Diff: {filename} ---{self.theme['reset']}")
                        self.show_diff(old_code, code)

                    save_file(filename, code, self.project_path, is_fix=True)
                    display_code(filename, code, self.theme, is_fix=True)
                    print(f"  {self.theme['green']}✓ Fixed: {filename}{self.theme['reset']}")
                    if filename.endswith('.py'):
                        self.pending_code = (filename, code)
                except Exception as e:
                    print(f"{self.theme['red']}✗ Error fixing {filename}: {e}{self.theme['reset']}")

        except Exception as e:
            print(f"\n{self.theme['red']}✗ Error processing response: {e}{self.theme['reset']}")

    def show_diff(self, old: str, new: str):
        old_lines = old.split('\n')
        new_lines = new.split('\n')
        max_lines = max(len(old_lines), len(new_lines))
        print()

        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line == new_line:
                if old_line:
                    print(f"  {self.theme['dim']}  {old_line}{self.theme['reset']}")
            else:
                if old_line is not None:
                    print(f"  {self.theme['red']}- {old_line}{self.theme['reset']}")
                if new_line is not None:
                    print(f"  {self.theme['green']}+ {new_line}{self.theme['reset']}")

    def handle_command(self, cmd: str) -> bool:
        cmd = cmd.strip()

        if cmd in ['/exit', '/quit', '/q']:
            self.session.save()
            print(f"\n{self.theme['header']}Session saved. Sampai jumpa!{self.theme['reset']}\n")
            return True

        if cmd == '/clear':
            self.session.messages.clear()
            print(f"{self.theme['yellow']}Messages cleared{self.theme['reset']}")
            return True

        if cmd == '/help':
            self.print_banner()
            return True

        if cmd == '/restart':
            print(f"{self.theme['yellow']}Restarting Ollama...{self.theme['reset']}")
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            if auto_start_ollama():
                print(f"{self.theme['green']}✓ Ollama restarted{self.theme['reset']}")
            else:
                print(f"{self.theme['red']}✗ Failed to restart Ollama{self.theme['reset']}")
            return True

        if cmd == '/theme':
            themes = Theme.list_themes()
            print(f"\n{self.theme['cyan']}Available themes:{self.theme['reset']}")
            for t in themes:
                marker = f" {self.theme['green']}← current{self.theme['reset']}" if t == self.config["theme"] else ""
                print(f"  {t}{marker}")
            print()
            return True

        if cmd.startswith('/theme '):
            new_theme = cmd[7:].strip()
            if new_theme in Theme.list_themes():
                self.config["theme"] = new_theme
                self.theme = Theme(new_theme)
                self.markdown = MarkdownRenderer(self.theme)
                print(f"{self.theme['green']}✓ Theme changed to: {new_theme}{self.theme['reset']}")
            else:
                print(f"{self.theme['red']}✗ Unknown theme: {new_theme}{self.theme['reset']}")
                print(f"{self.theme['cyan']}Available: {', '.join(Theme.list_themes())}{self.theme['reset']}")
            return True

        if cmd == '/config':
            print(f"\n{self.theme['cyan']}--- Config ---{self.theme['reset']}")
            for k, v in self.config.data.items():
                print(f"  {k}: {v}")
            print()
            return True

        if cmd.startswith('/set '):
            parts = cmd[5:].split(' ', 1)
            if len(parts) == 2:
                key, val = parts
                if val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                elif val.isdigit():
                    val = int(val)
                self.config[key] = val

                if key == 'model':
                    self.model = val
                elif key == 'project_path':
                    self.project_path = val
                elif key == 'theme':
                    self.theme = Theme(val)
                    self.markdown = MarkdownRenderer(self.theme)

                print(f"{self.theme['green']}✓ {key} = {val}{self.theme['reset']}")
            return True

        if cmd.startswith('/project '):
            path = cmd[9:].strip()
            if not Path(path).exists():
                print(f"{self.theme['red']}✗ Path not found: {path}{self.theme['reset']}")
                return True
            self.project_path = path
            self.config["project_path"] = path
            files = get_project_files(path)
            print(f"{self.theme['green']}✓ Project: {path}{self.theme['reset']}")
            print(f"  {len(files)} files found")
            return True

        if cmd == '/project':
            print(f"Project: {self.project_path or 'None'}")
            return True

        if cmd.startswith('/read '):
            filename = cmd[6:].strip()
            content = read_file(filename, self.project_path)
            if content:
                display_code(filename, content, self.theme)
            else:
                print(f"{self.theme['red']}✗ Not found: {filename}{self.theme['reset']}")
            return True

        if cmd.lower() in ['/files', '/ls']:
            if not self.project_path:
                print(f"{self.theme['yellow']}No project set. Use /project <path>{self.theme['reset']}")
            else:
                files = get_project_files(self.project_path)
                print(f"\n{self.theme['cyan']}Files in {self.project_path}:{self.theme['reset']}")
                for f in files:
                    print(f"  {f.relative_to(Path(self.project_path))}")
                print()
            return True

        if cmd.startswith('/model '):
            model = cmd[7:].strip()
            if check_model_exists(model):
                self.model = model
                self.config["model"] = model
                self.session.metadata["model"] = model
                print(f"{self.theme['green']}✓ Model: {model}{self.theme['reset']}")
            else:
                available = get_available_models()
                print_error(ModelNotFoundError(model), self.theme)
                if available:
                    print(f"{self.theme['cyan']}Available:{self.theme['reset']} {', '.join(available)}")
            return True

        if cmd == '/models':
            try:
                models = get_available_models()
                if models:
                    print(f"\n{self.theme['cyan']}Available models:{self.theme['reset']}")
                    for m in models:
                        marker = f" {self.theme['green']}← current{self.theme['reset']}" if m == self.model else ""
                        print(f"  {m}{marker}")
                else:
                    print(f"\n{self.theme['yellow']}No models installed{self.theme['reset']}")
            except:
                print_error(OllamaConnectionError(), self.theme)
            print()
            return True

        if cmd == '/sessions':
            sessions = self.session.list_sessions()
            print(f"\n{self.theme['cyan']}--- Sessions ---{self.theme['reset']}")
            if sessions:
                for s in sessions:
                    current = " (current)" if s['name'] == self.session.name else ""
                    print(f"  {s['name']}{current}")
                    print(f"    {s['created'][:19]} | {s['message_count']} messages | {s['model']}")
            else:
                print("  No sessions")
            print()
            return True

        if cmd.startswith('/save'):
            parts = cmd.split(' ', 1)
            name = parts[1].strip() if len(parts) > 1 else None
            if name:
                self.session = Session(name=name)
                self.session.metadata["model"] = self.model
                self.session.metadata["project_path"] = self.project_path
            if self.session.save():
                print(f"{self.theme['green']}✓ Session saved: {self.session.name}{self.theme['reset']}")
            return True

        if cmd.startswith('/load '):
            name = cmd[6:].strip()
            try:
                self.session = Session(name=name)
                self.model = self.session.metadata.get("model", "llama3")
                self.project_path = self.session.metadata.get("project_path")
                print(f"{self.theme['green']}✓ Loaded: {name}{self.theme['reset']}")
                print(f"  {len(self.session.messages)} messages")
            except Exception as e:
                print(f"{self.theme['red']}✗ Error loading: {e}{self.theme['reset']}")
            return True

        if cmd.startswith('/delete '):
            name = cmd[8:].strip()
            if Session.delete(name):
                print(f"{self.theme['green']}✓ Deleted: {name}{self.theme['reset']}")
            else:
                print(f"{self.theme['red']}✗ Not found: {name}{self.theme['reset']}")
            return True

        return False

    def handle_special_input(self, inp: str) -> bool:
        if inp.lower() == 'c' and self.pending_code:
            copy_to_clipboard(self.pending_code[1], self.theme)
            self.pending_code = None
            return True

        if inp.lower() == 'r' and self.pending_code:
            filename, code = self.pending_code
            if filename.endswith('.py'):
                run_python(code, self.theme)
            self.pending_code = None
            return True

        return False

    def run(self):
        self.print_banner()

        if not check_ollama_connection():
            print(f"\n{self.theme['yellow']}⚠ Ollama is not running{self.theme['reset']}")
            if self.config.get("auto_start_ollama", True):
                print(f"{self.theme['cyan']}Trying to start Ollama...{self.theme['cyan']}")
                if auto_start_ollama():
                    print(f"{self.theme['green']}✓ Ollama started{self.theme['reset']}\n")
                else:
                    print(f"\n{self.theme['red']}✗ Could not auto-start Ollama{self.theme['reset']}\n")
            else:
                print(f"{self.theme['yellow']}Auto-start disabled. Run 'ollama serve' manually.{self.theme['reset']}\n")

        while True:
            try:
                prompt = f"{self.theme['dim']}({self.session.name}){self.theme['reset']} "
                if self.project_path:
                    prompt = f"{self.theme['dim']}({Path(self.project_path).name}){self.theme['reset']} "

                inp = input(f"{prompt}{self.theme['blue']}❯{self.theme['reset']} ").strip()

                if not inp:
                    continue

                # Handle arrow key navigation for history
                if inp == '\x1b[A':  # Up arrow
                    prev = self.history.get_previous()
                    if prev:
                        print(f"\r{' ' * 100}\r{prompt}{self.theme['blue']}❯{self.theme['reset']} {prev}", end='', flush=True)
                    continue
                elif inp == '\x1b[B':  # Down arrow
                    nxt = self.history.get_next()
                    print(f"\r{' ' * 100}\r{prompt}{self.theme['blue']}❯{self.theme['reset']} {nxt or ''}", end='', flush=True)
                    continue

                if self.handle_special_input(inp):
                    continue

                if inp.startswith('/'):
                    if self.handle_command(inp):
                        continue

                if self.config["auto_save"] and len(self.session.messages) % 10 == 0:
                    self.session.save()

                response = self.chat(inp)
                if response:
                    self.process_response(response)

            except KeyboardInterrupt:
                self.session.save()
                print(f"\n\n{self.theme['header']}Session saved. Sampai jumpa!{self.theme['reset']}\n")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"\n{self.theme['red']}✗ Unexpected error: {e}{self.theme['reset']}\n")

# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

    app = TermiChat()

    # Handle command line arguments
    args = sys.argv[1:]
    if args:
        if args[0] == "--project" and len(args) > 1:
            path = args[1]
            if Path(path).exists():
                app.project_path = path
                app.config["project_path"] = path
                print(f"\n{app.theme['green']}Project: {path}{app.theme['reset']}")
            else:
                print(f"\n{app.theme['red']}Path not found: {path}{app.theme['reset']}")

        elif args[0] == "--read" and len(args) > 1:
            filename = args[1]
            content = read_file(filename, app.project_path)
            if content:
                display_code(filename, content, app.theme)
            else:
                print(f"\n{app.theme['red']}File not found: {filename}{app.theme['reset']}")
            print()

        else:
            print(f"\nUsage:")
            print(f"  termichat.py              - Start normally")
            print(f"  termichat.py --project <path>  - Start with project")
            print(f"  termichat.py --read <file>    - Read file")
            print()

    app.run()
