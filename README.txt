# TermiChat - AI Terminal Assistant

Chat dengan AI langsung dari terminal! Powered by Ollama.

## Install (Sekali aja)

1. Jalankan `INSTALL.bat`
2. Pilih model AI yang mau diinstall
3. Pilih apakah mau install context menu
4. Selesai!

## Cara Pakai

**Dari Terminal:**
```
ai          - Buka TermiChat
```

**Dari Windows Explorer:**
```
Klik kanan FOLDER          → "Chat with AI"
Klik kanan AREA KOSONG     → "Chat with AI Here"
```

## Install Model

Saat jalankan `INSTALL.bat`, pilih model:

```
[1] llama3   (~5GB) - Default, bagus untuk semua
[2] mistral  (~4GB) - Cepat, bagus untuk coding
[3] phi3     (~2GB) - Kecil & cepat
[4] codellama (~4GB) - Fokus coding
```

## Context Menu

Setelah install, akan muncul opsi saat klik kanan:

```
Folder (klik kanan)
  ├── Open
  ├── Copy
  └── Chat with AI    ← Langsung chat dengan folder ini sebagai context
```

**Uninstall context menu:**
```
uninstall-context-menu.bat
```

## Commands

```
/project <path>   Set project directory
/read <file>     Baca file dari project
/files           List file di project
/model <nama>    Ganti AI model
/models          List model yang tersedia
/restart         Restart Ollama
/theme <nama>    Ganti theme (dark, light, monokai, nord)

/sessions        List chat sessions tersimpan
/save [nama]    Simpan session sekarang
/load [nama]    Load session
/delete <nama>   Hapus session

/config          Lihat semua setting
/set <key> <val> Set config

/clear           Hapus chat history
/exit            Simpan & keluar
```

## Themes

```
/theme dark      - Tema gelap (default)
/theme light     - Tema terang
/theme monokai   - Tema monokai
/theme nord      - Tema nord
```

Themes otomatis support:
- **Windows Terminal** - Full 256-color
- **cmd.exe** - Basic ANSI colors (fallback otomatis)

## Markdown Render

AI response dirender sebagai markdown dengan warna:

- **# Headers** - diwarnai
- **`inline code`** - kuning
- **bold** dan *italic* - diformat
- **Lists** - bullet points
- **Code blocks** - syntax highlighted (jika Pygments terinstall)
- --- horizontal rules

## Error Handling

TermiChat otomatis mendeteksi dan menangani error:

```
Ollama tidak berjalan    → Auto-start atau muncul saran
Model tidak ditemukan      → Tampilkan model yang tersedia
Koneksi gagal             → Saran troubleshooting
File tidak bisa diakses    → Detail error & solusi
Code error                 → Tunjukkan baris yang bermasalah
```

## Config

Setting tersimpan di `%USERPROFILE%\.termichat\config.json`

```
/config          Show all settings
/set model mistral
/set auto_save false
/set theme light
```

Setting yang bisa diubah:
- `model` - Model AI default
- `project_path` - Folder project default
- `theme` - Tema (dark, light, monokai, nord)
- `auto_save` - Auto save chat
- `markdown_render` - Render markdown
- `auto_start_ollama` - Auto start Ollama

## Chat Sessions

Chat tersimpan otomatis. Bisa simpan dengan nama:

```
/save project_xyz
```

Load session lain:

```
/sessions        Lihat semua session
/load project_xyz
/delete project_xyz
```

## Code Generation

AI bisa generate code dengan format:

**[FILE:nama.py]**
```
code di sini
```
**[/FILE]**

**[FIX:nama.py]** (untuk fix code existing)
```
code yang sudah diperbaiki
```
**[/FIX]**

Setelah AI generate code:
- **c** → Copy code ke clipboard
- **r** → Run code Python langsung (jika .py)

## Navigasi

- `↑` `↓` arrows - Command history
- `/` prefix - Commands (e.g., `/help`, `/model`)

## File Scripts

| File | Fungsi |
|------|--------|
| `INSTALL.bat` | Install lengkap + context menu |
| `ai.bat` | Jalankan TermiChat |
| `install-context-menu.bat` | Install context menu saja |
| `uninstall-context-menu.bat` | Uninstall context menu |
| `termichat.py` | Program utama |

## Uninstall

1. Jalankan `uninstall-context-menu.bat` (jika install context menu)
2. Hapus folder TermiChat-Portable
3. Hapus config: `%USERPROFILE%\.termichat`

## System Requirements

- Windows 10/11
- Python 3.8+
- Ollama
- 15GB+ disk space (untuk models)
- Internet (untuk download models)

## Dependencies

Install otomatis oleh `INSTALL.bat`:
- `ollama` - AI runtime
- `pygments` - Syntax highlighting
- `pyperclip` - Clipboard support
