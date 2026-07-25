# Ophidian Vault Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить репозиторий `ophidian` в единый Obsidian-волт, где заметки — единственный источник правды, а YAML/JSON генерируется скриптом.

**Architecture:** Содержимое `obsidian-ophidian-vault/` переезжает в корень репозитория и раскладывается по ролям (`Language/`, `Corpus/`, `Lore/`, `Drafts/`, `Meta/`). Рукописные YAML в корне удаляются, их знание переносится в заметки. Два скрипта на голой стандартной библиотеке — `tools/check.py` (валидатор) и `tools/build.py` (генератор `build/*.json`) — держат структуру в порядке; общий ридер frontmatter вынесен в `tools/notes.py`.

**Tech Stack:** Python 3.14, только стандартная библиотека. Тесты — `unittest`. Obsidian с встроенным Bases.

## Global Constraints

- **Только стандартная библиотека Python.** `pyyaml` и `pytest` не установлены и не устанавливаются. Тесты — `unittest`, вывод сборки — `json`.
- **Вся работа выполняется в основном рабочем дереве** `/Users/mitiamorovovsheiner/Github/ophidian`, на ветке `vault-restructure`. Волт лежит там untracked и из воркдерева `.claude/worktrees/` не виден.
- **Все перемещения — через `git mv`**, чтобы не оборвать историю файлов.
- **Инвариант:** `Language/` пишет только человек через Obsidian, `build/` пишет только скрипт. Ни один файл не правится с двух сторон.
- **Версия языка `0.4`** живёт ровно в одном месте — frontmatter `README.md`.
- **Запрещённые символы в именах файлов:** `? * : / \ | " < >`.
- **`ș` — это U+0219** (запятая снизу). `ş` U+015F (седиль) запрещён везде.
- Спека: `docs/superpowers/specs/2026-07-25-ophidian-vault-structure-design.md`.

## File Structure

| Файл | Ответственность |
| --- | --- |
| `tools/notes.py` | Разбор и запись frontmatter заметок. Единственное место, знающее формат. |
| `tools/check.py` | Валидация: схема, ссылки, имена, таблица транслитерации. Ошибки vs предупреждения. |
| `tools/build.py` | Генерация `build/lexicon.json` и `build/phonology.json`. |
| `tools/migrate_frontmatter.py` | Одноразовый: старая схема заметок → новая. Удаляется в Task 9. |
| `tests/test_notes.py` | Тесты ридера/райтера frontmatter. |
| `tests/test_check.py` | Тесты валидатора. |
| `tests/test_build.py` | Тесты генератора. |

---

### Task 1: Подготовка git

Волт не в истории. Ничего нельзя двигать, пока он не зафиксирован.

**Files:**
- Modify: рабочее дерево `/Users/mitiamorovovsheiner/Github/ophidian`

**Interfaces:**
- Consumes: ничего
- Produces: ветка `vault-restructure` с закоммиченным волтом и спекой; далее все задачи работают на ней

- [ ] **Step 1: Убедиться, что находимся в основном дереве и посмотреть состояние**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git status
```

Ожидается: ветка `main`, застейдженные правки `Borrowings.md` и `lexicon.yaml`, untracked `obsidian-ophidian-vault/`.

- [ ] **Step 2: Закоммитить висящие правки**

Это правка `ş` → `ș`, сделанная руками ранее. Коммитится отдельно, до всяких перемещений.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git commit -m "fix: use U+0219 s-comma instead of U+015F s-cedilla"
```

- [ ] **Step 3: Создать ветку**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git checkout -b vault-restructure
```

- [ ] **Step 4: Убрать мусор macOS из индексации волта и закоммитить волт как есть**

`.gitignore` уже содержит `.DS_Store`, поэтому `git add` его не подхватит.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add obsidian-ophidian-vault && git status --short
```

Ожидается: список добавленных файлов волта, **без** `.DS_Store` и **без** `.obsidian/workspace.json` (он пока попадёт — это нормально, исключим в Task 3).

- [ ] **Step 5: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git commit -m "chore: add obsidian vault as-is before restructure"
```

- [ ] **Step 6: Перенести спеку и план из воркдерева**

Спека и план живут на ветке `claude/github-latest-version-e93231`. Забираем каталог `docs/` целиком, без перечисления хешей — их список устаревает при каждой правке плана.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git checkout claude/github-latest-version-e93231 -- docs/ && git commit -m "docs: add vault restructure spec and plan"
```

- [ ] **Step 7: Убедиться, что спека и план на месте**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && ls docs/superpowers/specs docs/superpowers/plans
```

Ожидается: `2026-07-25-ophidian-vault-structure-design.md` и `2026-07-25-ophidian-vault-migration.md`.

---

### Task 2: Раскладка папок

**Files:**
- Move: всё содержимое `obsidian-ophidian-vault/` → корень, по ролям
- Move: `lore.md`, `Sandbox.md`, `Borrowings.md`, `fable translation.md`, скрипты

**Interfaces:**
- Consumes: ветка из Task 1
- Produces: целевая раскладка каталогов; дальнейшие задачи ссылаются на `Language/Lexicon/`, `Language/Phonology/`, `tools/`, `Meta/`

- [ ] **Step 1: Создать целевые каталоги**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && mkdir -p Language Corpus Lore Drafts Meta tools/legacy tests
```

- [ ] **Step 2: Перенести лингвистические разделы в `Language/`**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git mv obsidian-ophidian-vault/Lexicon Language/Lexicon && \
git mv obsidian-ophidian-vault/Roots Language/Roots && \
git mv obsidian-ophidian-vault/Affixes Language/Affixes && \
git mv obsidian-ophidian-vault/Grammar Language/Grammar && \
git mv obsidian-ophidian-vault/Phonology Language/Phonology && \
git mv "obsidian-ophidian-vault/Noun Classes" "Language/Noun Classes" && \
git mv "obsidian-ophidian-vault/Verb Classes" "Language/Verb Classes"
```

- [ ] **Step 3: Перенести настройки Obsidian в корень**

Без этого Obsidian не увидит корень репозитория как волт.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git mv obsidian-ophidian-vault/.obsidian .obsidian
```

- [ ] **Step 4: Перенести шаблоны в `Meta/`**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git mv obsidian-ophidian-vault/Templates Meta/Templates
```

- [ ] **Step 5: Перенести тексты, лор и черновики**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git mv "fable translation.md" Corpus/Fable.md && \
git mv lore.md Lore/Lore.md && \
git mv Sandbox.md Drafts/Sandbox.md && \
git mv Borrowings.md Drafts/Borrowings.md
```

- [ ] **Step 6: Перенести легаси-скрипты**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git mv transliteration.py tools/legacy/transliteration.py && \
git mv transposition/transpose-script.py tools/legacy/transpose-script.py && \
git mv dictionary.html tools/legacy/dictionary.html
```

- [ ] **Step 7: Проверить раскладку**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && ls -A && echo "--- Language ---" && ls Language
```

Ожидается в корне: `.claude .gitignore .obsidian Corpus Drafts Language Lore Meta README.md build docs grammar.yaml input_words.txt lexicon.yaml obsidian-ophidian-vault output_transliterations.txt phonology.yaml tests tools transliterations.txt transposition`
(`build/` ещё нет — появится в Task 8; `obsidian-ophidian-vault/` ещё содержит мусор — чистится в Task 3.)

Ожидается в `Language`: `Affixes Grammar Lexicon "Noun Classes" Phonology Roots "Verb Classes"`

- [ ] **Step 8: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "refactor: lay out repo as a single obsidian vault"
```

---

### Task 3: Чистка мусора, имён файлов и .gitignore

**Files:**
- Delete: пустые `.base`/`.canvas`/заметки, вход-выход легаси-скриптов, `Queries/`
- Rename: 4 файла с запрещёнными символами
- Modify: `.gitignore`, `README.md`

**Interfaces:**
- Consumes: раскладка из Task 2
- Produces: `README.md` с `version: 0.4` во frontmatter — из него `build.py` читает версию

- [ ] **Step 1: Удалить пустые файлы и остатки волта**

`Queries/` содержит dataview-запросы, которые всё равно не работали (обращались к несуществующему `script.latin`); их заменяют Bases в Task 9.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git rm -r --quiet obsidian-ophidian-vault/Queries && \
git rm --quiet obsidian-ophidian-vault/*.base obsidian-ophidian-vault/Untitled.canvas obsidian-ophidian-vault/2026-07-25.md && \
rm -rf obsidian-ophidian-vault
```

- [ ] **Step 2: Удалить вход-выход легаси-скриптов**

Это не данные языка, а следы прогонов.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git rm --quiet input_words.txt transliterations.txt output_transliterations.txt transposition/input.txt transposition/output.txt && \
rmdir transposition
```

- [ ] **Step 3: Убрать запрещённые символы из имён**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git mv "Language/Lexicon/ļicejeśe?.md" "Language/Lexicon/ļicejeśe.md" && \
git mv "Language/Lexicon/ļicexese?.md" "Language/Lexicon/ļicexese.md" && \
git mv "Language/Grammar/Future tense*.md" "Language/Grammar/Future tense.md" && \
git mv "Language/Grammar/Past tense*.md" "Language/Grammar/Past tense.md"
```

- [ ] **Step 4: Обновить .gitignore**

Записать в `/Users/mitiamorovovsheiner/Github/ophidian/.gitignore`:

```
.DS_Store
.obsidian/workspace.json
build/
__pycache__/
```

- [ ] **Step 5: Выкинуть workspace.json из индекса**

Он попал в коммит в Task 1; это состояние открытых панелей, не настройка.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git rm --cached --quiet .obsidian/workspace.json
```

- [ ] **Step 6: Добавить frontmatter с версией в README.md**

Дописать в самое начало `/Users/mitiamorovovsheiner/Github/ophidian/README.md`, перед строкой `# ophidian`:

```markdown
---
version: 0.4
---

```

- [ ] **Step 7: Проверить, что запрещённых символов не осталось**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && find Language Corpus Lore Drafts Meta -name '*[?*:\\|"<>]*'
```

Ожидается: пустой вывод.

- [ ] **Step 8: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "chore: drop empty files, fix illegal filenames, single version source"
```

---

### Task 4: `tools/notes.py` — чтение и запись frontmatter

Единственное место, знающее формат заметки. Нужно и валидатору, и генератору, и одноразовой миграции.

**Files:**
- Create: `tools/notes.py`
- Test: `tests/test_notes.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `parse_note(text: str) -> tuple[dict[str, str | list[str] | None], str]` — возвращает `(frontmatter, body)`. Скаляр → `str`, пустое значение → `None`, список (блочный `- item` или инлайновый `[a, b]`) → `list[str]`. Кавычки снимаются. Если frontmatter нет — `({}, text)`.
  - `format_note(fm: dict, body: str) -> str` — обратная операция. `None` → `key:`, список → `key: [a, b]`, строка → `key: value` с кавычками при необходимости.
  - `read_note(path) -> tuple[dict, str]`, `write_note(path, fm, body) -> None` — обёртки над файлом, UTF-8.
  - `parse_table(text: str) -> list[list[str]]` — строки markdown-таблицы, разделитель `| --- |` отброшен, первая строка — заголовок. Нужен и валидатору (Task 7), и генератору (Task 8); живёт здесь, чтобы формат таблицы был описан в одном месте.

- [ ] **Step 1: Написать падающий тест**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tests/test_notes.py`:

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, format_note


class ParseNote(unittest.TestCase):
    def test_scalar_and_empty_and_link(self):
        text = (
            "---\n"
            "type: lexeme\n"
            "lemma: gaśi\n"
            "noun_class: \"[[Class 7]]\"\n"
            "etym:\n"
            "---\n"
            "\n"
        )
        fm, body = parse_note(text)
        self.assertEqual(fm["type"], "lexeme")
        self.assertEqual(fm["lemma"], "gaśi")
        self.assertEqual(fm["noun_class"], "[[Class 7]]")
        self.assertIsNone(fm["etym"])
        self.assertEqual(body, "\n")

    def test_block_sequence(self):
        text = "---\nscript:\n  - gaśi\n  - гащи\ntags:\n  - lexeme\n---\n"
        fm, _ = parse_note(text)
        self.assertEqual(fm["script"], ["gaśi", "гащи"])
        self.assertEqual(fm["tags"], ["lexeme"])

    def test_inline_sequence(self):
        fm, _ = parse_note("---\ntags: [lexeme]\n---\n")
        self.assertEqual(fm["tags"], ["lexeme"])

    def test_empty_inline_sequence_is_a_list(self):
        fm, _ = parse_note("---\nexamples: []\n---\n")
        self.assertEqual(fm["examples"], [])

    def test_meaning_with_comma_stays_one_string(self):
        fm, _ = parse_note("---\nmeaning: to open, to disembowel\n---\n")
        self.assertEqual(fm["meaning"], "to open, to disembowel")

    def test_no_frontmatter(self):
        fm, body = parse_note("# Just prose\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# Just prose\n")

    def test_body_preserved_after_frontmatter(self):
        fm, body = parse_note("---\ntype: root\n---\nSome prose.\n")
        self.assertEqual(body, "Some prose.\n")


class ParseTable(unittest.TestCase):
    def test_separator_row_is_dropped(self):
        from tools.notes import parse_table

        text = (
            "# Title\n\n"
            "| IPA | latin-1 |\n"
            "| --- | ------- |\n"
            "| θ | t |\n"
            "| ʃ | ș |\n"
        )
        rows = parse_table(text)
        self.assertEqual(rows[0], ["IPA", "latin-1"])
        self.assertEqual(rows[1:], [["θ", "t"], ["ʃ", "ș"]])

    def test_no_table_returns_empty(self):
        from tools.notes import parse_table

        self.assertEqual(parse_table("Just prose.\n"), [])


class FormatNote(unittest.TestCase):
    def test_roundtrip_flat(self):
        fm = {"type": "lexeme", "lemma": "gaśi", "etym": None, "tags": ["lexeme"]}
        text = format_note(fm, "")
        self.assertEqual(
            text,
            "---\ntype: lexeme\nlemma: gaśi\netym:\ntags: [lexeme]\n---\n",
        )

    def test_link_value_is_quoted(self):
        text = format_note({"noun_class": "[[Class 7]]"}, "")
        self.assertEqual(text, '---\nnoun_class: "[[Class 7]]"\n---\n')

    def test_parse_of_formatted_matches_original(self):
        fm = {
            "type": "lexeme",
            "lemma": "gaśi",
            "cyrillic": "гащи",
            "meaning": "to open, to disembowel",
            "noun_class": "[[Class 7]]",
            "etym": None,
            "tags": ["lexeme"],
        }
        again, _ = parse_note(format_note(fm, ""))
        self.assertEqual(again, fm)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_notes -v
```

Ожидается: `ModuleNotFoundError: No module named 'tools.notes'`

- [ ] **Step 3: Написать реализацию**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tools/__init__.py` пустым, и `/Users/mitiamorovovsheiner/Github/ophidian/tools/notes.py`:

```python
"""Чтение и запись frontmatter заметок Obsidian.

Намеренно поддерживает только то подмножество YAML, которое реально
встречается в этом волте: плоские пары ключ-значение, блочные списки
и инлайновые списки. Без зависимостей.
"""

import re
from pathlib import Path

DELIM = "---"
# Значение приходится закавычивать, если оно начинается с символа,
# который YAML прочтёт как структуру, либо содержит ссылку [[...]].
_NEEDS_QUOTES_PREFIX = "[{&*!|>%@`#"
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_inline(value):
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",")]


def parse_note(text):
    """-> (frontmatter, body). Пустое значение — None, список — list[str]."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIM:
        return {}, text

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == DELIM:
            end = index
            break
    if end is None:
        return {}, text

    fm = {}
    key = None
    index = 1
    while index < end:
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if line.startswith((" ", "\t")) and stripped.startswith("- "):
            if key is not None:
                if not isinstance(fm[key], list):
                    fm[key] = []
                fm[key].append(_unquote(stripped[2:].strip()))
            index += 1
            continue

        if ":" not in stripped:
            index += 1
            continue

        key, _, raw = stripped.partition(":")
        key = key.strip()
        raw = raw.strip()
        if not raw:
            fm[key] = None
        elif raw.startswith("[") and raw.endswith("]"):
            fm[key] = _split_inline(raw)
        else:
            fm[key] = _unquote(raw)
        index += 1

    body = "\n".join(lines[end + 1 :])
    return fm, body


def _format_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(value) + "]"
    text = str(value)
    if not text:
        return '""'
    if text[0] in _NEEDS_QUOTES_PREFIX or text != text.strip():
        return '"' + text + '"'
    return text


def format_note(fm, body):
    lines = [DELIM]
    for key, value in fm.items():
        rendered = _format_value(value)
        lines.append(f"{key}: {rendered}" if rendered else f"{key}:")
    lines.append(DELIM)
    return "\n".join(lines) + "\n" + body


def parse_table(text):
    """Строки markdown-таблицы. Первая — заголовок, разделитель отброшен."""
    rows = []
    for line in text.split("\n"):
        match = _TABLE_ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if all(set(cell) <= set("- ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def read_note(path):
    return parse_note(Path(path).read_text(encoding="utf-8"))


def write_note(path, fm, body):
    Path(path).write_text(format_note(fm, body), encoding="utf-8")
```

- [ ] **Step 4: Запустить тесты**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_notes -v
```

Ожидается: `OK`, 12 тестов.

- [ ] **Step 5: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add tools/__init__.py tools/notes.py tests/test_notes.py && git commit -m "feat: add dependency-free frontmatter reader/writer"
```

---

### Task 5: Миграция frontmatter заметок

104 лексемы + аффиксы приводятся к новой схеме. Руками не делается — только скриптом.

**Files:**
- Create: `tools/migrate_frontmatter.py` (удаляется в Task 9)
- Modify: все `Language/Lexicon/*.md`, `Language/Affixes/*.md`

**Interfaces:**
- Consumes: `tools.notes.read_note`, `tools.notes.write_note`
- Produces: заметки в схеме, которую ждут `check.py` и `build.py` (Task 7, 8)

- [ ] **Step 1: Написать скрипт миграции**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tools/migrate_frontmatter.py`:

```python
"""Одноразовый перевод заметок в новую схему.

script: [латиница, кириллица] -> cyrillic: кириллица (латиница уже есть в lemma)
пустые "" и [] -> None
добавляется status
порядок ключей приводится к каноническому
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import read_note, write_note

ROOT = Path(__file__).resolve().parent.parent

LEXEME_ORDER = [
    "type", "lemma", "cyrillic", "pos", "meaning", "verb_type",
    "noun_class", "root", "phon", "etym", "examples", "status", "tags",
]
AFFIX_ORDER = ["type", "cyrillic", "meaning", "etym", "examples", "tags"]


def blank(value):
    """Пустая строка, пустой список и '' — всё это отсутствие значения."""
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    return value.strip() == ""


def normalize(fm, order):
    out = {}
    for key in order:
        value = fm.get(key)
        out[key] = None if blank(value) else value
    return out


def script_to_cyrillic(fm):
    """script: [латиница, кириллица] -> cyrillic. Латиница уже есть в lemma."""
    script = fm.pop("script", None)
    fm["cyrillic"] = script[1] if isinstance(script, list) and len(script) >= 2 else None


def migrate_lexeme(path):
    fm, body = read_note(path)
    script_to_cyrillic(fm)

    # Имя файла — канон: переименования уже сделаны на предыдущем шаге.
    fm["lemma"] = path.stem
    fm["status"] = "ok"

    fm = normalize(fm, LEXEME_ORDER)
    fm["type"] = "lexeme"
    fm["tags"] = ["lexeme"]
    write_note(path, fm, body)


def migrate_affix(path):
    fm, body = read_note(path)
    script_to_cyrillic(fm)
    fm = normalize(fm, AFFIX_ORDER)
    fm["type"] = "affix"
    fm["tags"] = ["affix"]
    write_note(path, fm, body)


def main():
    lexemes = sorted((ROOT / "Language" / "Lexicon").glob("*.md"))
    for path in lexemes:
        migrate_lexeme(path)
    affixes = [
        path
        for path in sorted((ROOT / "Language" / "Affixes").glob("*.md"))
        if path.stem != "template"
    ]
    for path in affixes:
        migrate_affix(path)
    print(f"lexemes: {len(lexemes)}, affixes: {len(affixes)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Прогнать миграцию**

Имена файлов с `?` уже переименованы в Task 3, поэтому `status` у всех выйдет `ok`; двум лексемам он проставляется вручную следующим шагом.

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 tools/migrate_frontmatter.py
```

Ожидается: `lexemes: 104, affixes: 10`

- [ ] **Step 3: Проставить `status: unverified` двум лексемам**

В `Language/Lexicon/ļicejeśe.md` и `Language/Lexicon/ļicexese.md` заменить строку `status: ok` на `status: unverified`.

- [ ] **Step 4: Проверить результат глазами на одной заметке**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && cat Language/Lexicon/gaśi.md
```

Ожидается ровно:

```
---
type: lexeme
lemma: gaśi
cyrillic: гащи
pos: nouns
meaning: place
verb_type:
noun_class: "[[Class 7]]"
root: "[[-gaśi-]]"
phon:
etym:
examples:
status: ok
tags: [lexeme]
---

```

- [ ] **Step 5: Убедиться, что поля `script` нигде не осталось**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && grep -rl '^script:' Language/ | head
```

Ожидается: пустой вывод.

- [ ] **Step 6: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "refactor: migrate note frontmatter to flat schema"
```

---

### Task 6: Перенос знания из YAML в заметки

Прежде чем удалять корневые YAML, надо вынуть из них то, чего нет в заметках: комментарии в `grammar.yaml` и `phonology.yaml`, и выровненную таблицу транслитерации.

**Files:**
- Modify: `Language/Grammar/Verb Types.md`, `Language/Grammar/Past tense.md`, `Language/Phonology/Inventory.md`
- Rewrite: `Language/Phonology/Transliteration.md`

**Interfaces:**
- Consumes: раскладку из Task 2
- Produces: `Transliteration.md` с таблицей из 18 строк и колонками `IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2` — её парсит `build.py` (Task 8) и проверяет `check.py` (Task 7)

- [ ] **Step 1: Дописать в `Language/Grammar/Verb Types.md`**

Комментарии из `grammar.yaml`, которых нет в заметках:

```markdown

## Основа

Тип 1 сохраняет базовую основу во всех формах. Тип 2 в части форм использует
геминированную основу.

Геминированная основа — форма основы, в которой первый согласный и последний
гласный удваиваются, а аффикс `-xx-` отбрасывается.
```

- [ ] **Step 2: Дописать в `Language/Grammar/Past tense.md`**

```markdown

Изначально в языке не было различения по времени. Способы выражать прошедшее и
будущее развились позже.
```

- [ ] **Step 3: Дописать в `Language/Phonology/Inventory.md`**

```markdown

## Заметки

- `u` — редкая гласная, встречается преимущественно в заимствованиях.
- Двойные гласные используются в основном грамматически — например, для
  множественного числа существительных.
- Мягкие согласные сочетаются с передними гласными, твёрдые — с задними.

## Категории

**Согласные**
- soft: θ, sʲ, ɕ, ç, h, 𝼆
- hard: s, ʃ, ʂ, x, χ, ħ, ɬ

**Гласные**
- front: i, e, a, ə
- back: ɨ, ɛ, ɑ, ɯ
```

- [ ] **Step 4: Переписать `Language/Phonology/Transliteration.md` целиком**

Пять несвязанных JSON-списков заменяются одной выровненной таблицей.

```markdown
# Transliteration

Строка — фонема, колонка — вариант записи. Порядок строк совпадает с
[[Inventory]]: 13 согласных, 4 гласных, гортанная смычка.

| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2 |
| --- | ------- | ------- | ------- | ----- | ----- |
| θ | t | th | t | т | ф |
| s | s | s | s | с | с |
| sʲ | c | c | c | сь | сј |
| ʃ | ș | sh | w | ш | ш |
| ʂ | š | rz | r | ж | ж |
| ɕ | ś | ch | z | щ | шј |
| ç | j | j | j | хь | ј |
| x | x | x | x | х | х |
| χ | g | g | g | г | г |
| ħ | q | q | q | к | к |
| h | h | h | h | ь | кј |
| ɬ | l | l | l | л | л |
| 𝼆 | ļ | lh | y | ль | лј |
| i | i | i | i | и | и |
| e | e | e | e | э | е |
| a | a | a | a | а | а |
| u | u | u | u | у | у |
| ʔ | ’ | ’ | ’ | ъ | ’ |

## Варианты

- **latin-1** — стандартная латиница.
- **latin-2** — латиница с диграфами.
- **latin-3** — техническая латиница для веба и прочих технических нужд.
- **cyr-1** — стандартная кириллица.
- **cyr-2** — альтернативная кириллица.

## Правила поверх таблицы

- Геминированные согласные и долгие гласные пишутся удвоением буквы:
  θː → `tt` / `tth`, ʂː → `šš` / `rrz`, iː → `ii`.
- Двойные гласные пишутся через гортанную смычку последним символом:
  aʔa → `a’a`.

## Не формализовано

Есть вариант кириллицы, следующий фонетическим правилам русского языка:
стандартное `сэхишэ` / `сьэхьищэ` против `сэхышэ` / `сехище`.
```

- [ ] **Step 5: Проверить, что в таблице 18 строк данных**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && grep -c '^| ' "Language/Phonology/Transliteration.md"
```

Ожидается: `20` (заголовок + разделитель + 18 строк).

- [ ] **Step 6: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "docs: move yaml-only knowledge into notes, realign transliteration table"
```

---

### Task 7: `tools/check.py` — валидатор

**Files:**
- Create: `tools/check.py`
- Test: `tests/test_check.py`

**Interfaces:**
- Consumes: `tools.notes.parse_note`
- Produces:
  - `check_vault(root: Path) -> tuple[list[str], list[str]]` — возвращает `(errors, warnings)`, каждый элемент — готовая к печати строка.
  - `main() -> int` — печатает и возвращает код выхода: `1` при непустых ошибках, иначе `0`.

- [ ] **Step 1: Написать падающий тест**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tests/test_check.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.check import check_vault

GOOD_LEXEME = """---
type: lexeme
lemma: gaśi
cyrillic: гащи
pos: nouns
meaning: place
verb_type:
noun_class: "[[Class 7]]"
root: "[[-gaśi-]]"
phon:
etym:
examples:
status: ok
tags: [lexeme]
---
"""

GOOD_ROOT = """---
type: root
meaning: movement
tags: [root]
---
"""

GOOD_CLASS = """---
type: noun_class
class: 7
prefix:
semantics: inanimate
tags: [noun_class]
---
"""

TABLE = """# Transliteration

| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2 |
| --- | --- | --- | --- | --- | --- |
"""


def build_vault(directory, lexemes=None, table_rows=18):
    root = Path(directory)
    (root / "Language" / "Lexicon").mkdir(parents=True)
    (root / "Language" / "Roots").mkdir(parents=True)
    (root / "Language" / "Noun Classes").mkdir(parents=True)
    (root / "Language" / "Phonology").mkdir(parents=True)

    for name, text in (lexemes or {"gaśi": GOOD_LEXEME}).items():
        (root / "Language" / "Lexicon" / f"{name}.md").write_text(text, encoding="utf-8")
    (root / "Language" / "Roots" / "-gaśi-.md").write_text(GOOD_ROOT, encoding="utf-8")
    (root / "Language" / "Noun Classes" / "Class 7.md").write_text(GOOD_CLASS, encoding="utf-8")

    table = TABLE + "".join(f"| p{i} | a | b | c | d | e |\n" for i in range(table_rows))
    (root / "Language" / "Phonology" / "Transliteration.md").write_text(table, encoding="utf-8")
    return root


class CheckVault(unittest.TestCase):
    def test_clean_vault_has_no_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = check_vault(build_vault(directory))
            self.assertEqual(errors, [])

    def test_filename_must_match_lemma(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"wrong": GOOD_LEXEME})
            errors, _ = check_vault(root)
            self.assertTrue(any("lemma" in error for error in errors))

    def test_broken_link_is_an_error(self):
        broken = GOOD_LEXEME.replace("[[Class 7]]", "[[Class 99]]")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": broken})
            errors, _ = check_vault(root)
            self.assertTrue(any("Class 99" in error for error in errors))

    def test_cedilla_is_an_error(self):
        cedilla = GOOD_LEXEME.replace("meaning: place", "meaning: şagassa")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": cedilla})
            errors, _ = check_vault(root)
            self.assertTrue(any("U+015F" in error for error in errors))

    def test_empty_string_value_is_an_error(self):
        quoted = GOOD_LEXEME.replace("etym:", 'etym: ""')
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": quoted})
            errors, _ = check_vault(root)
            self.assertTrue(any("etym" in error for error in errors))

    def test_duplicate_lemma_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": GOOD_LEXEME})
            (root / "Language" / "Lexicon" / "gaśi copy.md").write_text(
                GOOD_LEXEME, encoding="utf-8"
            )
            errors, _ = check_vault(root)
            self.assertTrue(any("дубль" in error for error in errors))

    def test_wrong_table_row_count_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, table_rows=17)
            errors, _ = check_vault(root)
            self.assertTrue(any("18" in error for error in errors))

    def test_noun_without_class_is_a_warning_not_error(self):
        classless = GOOD_LEXEME.replace('noun_class: "[[Class 7]]"', "noun_class:")
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory, {"gaśi": classless})
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("noun_class" in warning for warning in warnings))

    def test_unreferenced_root_is_a_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_vault(directory)
            (root / "Language" / "Roots" / "-orphan-.md").write_text(GOOD_ROOT, encoding="utf-8")
            errors, warnings = check_vault(root)
            self.assertEqual(errors, [])
            self.assertTrue(any("-orphan-" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_check -v
```

Ожидается: `ModuleNotFoundError: No module named 'tools.check'`

- [ ] **Step 3: Написать реализацию**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tools/check.py`:

```python
"""Валидатор волта.

Ошибки — структурная поломка, ронять сборку. Предупреждения — неполнота
языка, это нормальное рабочее состояние.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, parse_table

ROOT = Path(__file__).resolve().parent.parent

CEDILLA = "ş"  # ş — запрещён, правильный символ ș U+0219
ILLEGAL_NAME_CHARS = set('?*:/\\|"<>')
LINK = re.compile(r"\[\[([^\]]+)\]\]")
PHONEME_COUNT = 18  # 13 согласных + 4 гласных + гортанная смычка
TABLE_COLUMNS = 6  # IPA + пять вариантов записи

SCHEMA = {
    "lexeme": [
        "type", "lemma", "cyrillic", "pos", "meaning", "verb_type",
        "noun_class", "root", "phon", "etym", "examples", "status", "tags",
    ],
    "root": ["type", "meaning", "tags"],
    "affix": ["type", "cyrillic", "meaning", "etym", "examples", "tags"],
    "noun_class": ["type", "class", "prefix", "semantics", "tags"],
    "verb_class": ["type", "affix", "semantics", "tags"],
}

TYPED_DIRS = {
    "Lexicon": "lexeme",
    "Roots": "root",
    "Affixes": "affix",
    "Noun Classes": "noun_class",
    "Verb Classes": "verb_class",
}


def _typed_notes(root):
    """-> список (path, expected_type, frontmatter)."""
    found = []
    for folder, expected in TYPED_DIRS.items():
        directory = root / "Language" / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.stem == "template":
                continue
            fm, _ = parse_note(path.read_text(encoding="utf-8"))
            found.append((path, expected, fm))
    return found


def _note_names(root):
    return {path.stem for path in (root / "Language").rglob("*.md")}


def _check_transliteration(root, errors):
    path = root / "Language" / "Phonology" / "Transliteration.md"
    if not path.is_file():
        errors.append("Transliteration.md отсутствует")
        return
    rows = parse_table(path.read_text(encoding="utf-8"))
    if not rows:
        errors.append("Transliteration.md: таблица не найдена")
        return
    data = rows[1:]
    if len(data) != PHONEME_COUNT:
        errors.append(
            f"Transliteration.md: строк данных {len(data)}, ожидается {PHONEME_COUNT} "
            "(13 согласных + 4 гласных + гортанная смычка)"
        )
    for cells in data:
        if len(cells) != TABLE_COLUMNS:
            errors.append(
                f"Transliteration.md: в строке {cells[0]!r} колонок {len(cells)}, "
                f"ожидается {TABLE_COLUMNS}"
            )
        elif any(not cell for cell in cells):
            errors.append(f"Transliteration.md: пустая клетка в строке {cells[0]!r}")


def check_vault(root):
    root = Path(root)
    errors = []
    warnings = []

    names = _note_names(root)
    notes = _typed_notes(root)
    seen_lemmas = {}
    referenced_roots = set()

    for path, expected, fm in notes:
        where = path.relative_to(root)

        illegal = ILLEGAL_NAME_CHARS & set(path.name)
        if illegal:
            errors.append(f"{where}: запрещённые символы в имени: {''.join(sorted(illegal))}")

        allowed = SCHEMA[expected]
        for key in fm:
            if key not in allowed:
                errors.append(f"{where}: поле {key!r} не из схемы {expected}")
        for key in allowed:
            if key not in fm:
                errors.append(f"{where}: отсутствует поле {key!r}")

        for key, value in fm.items():
            if value == "" or value == []:
                errors.append(f"{where}: поле {key!r} — пустая строка или пустой список, должно быть пустым")

        text = path.read_text(encoding="utf-8")
        if CEDILLA in text:
            errors.append(f"{where}: символ ş U+015F, ожидается ș U+0219")
        for target in LINK.findall(text):
            if target not in names:
                errors.append(f"{where}: битая ссылка [[{target}]]")

        if expected == "lexeme":
            lemma = fm.get("lemma")
            if lemma != path.stem:
                errors.append(f"{where}: lemma {lemma!r} не совпадает с именем файла {path.stem!r}")
            if lemma in seen_lemmas:
                errors.append(f"{where}: дубль lemma {lemma!r}, уже есть в {seen_lemmas[lemma]}")
            else:
                seen_lemmas[lemma] = where

            if fm.get("root"):
                referenced_roots.update(LINK.findall(str(fm["root"])))
            else:
                warnings.append(f"{where}: нет root")
            if fm.get("pos") == "nouns" and not fm.get("noun_class"):
                warnings.append(f"{where}: pos=nouns, но нет noun_class")
            if fm.get("pos") == "verbs" and not fm.get("verb_type"):
                warnings.append(f"{where}: pos=verbs, но нет verb_type")
            if fm.get("status") == "unverified":
                warnings.append(f"{where}: status=unverified")

    for path, expected, _ in notes:
        if expected == "root" and path.stem not in referenced_roots:
            warnings.append(f"{path.relative_to(root)}: на корень не ссылается ни одна лексема")

    _check_transliteration(root, errors)
    return errors, warnings


def main():
    errors, warnings = check_vault(ROOT)
    for warning in warnings:
        print(f"warn:  {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"\n{len(errors)} ошибок, {len(warnings)} предупреждений")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Запустить тесты**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_check -v
```

Ожидается: `OK`, 9 тестов.

- [ ] **Step 5: Прогнать валидатор на настоящем волте**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 tools/check.py
```

Ожидается: `0 ошибок` и какое-то число предупреждений. **Если ошибки есть — чинить заметки, а не подкручивать валидатор**: он описывает схему из спеки. Единственное исключение — если ошибка указывает на реальный промах в самой схеме, тогда сначала правится спека.

- [ ] **Step 6: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "feat: add vault validator with errors/warnings split"
```

---

### Task 8: `tools/build.py` — генератор

**Files:**
- Create: `tools/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `tools.notes.parse_note`
- Produces:
  - `build_lexicon(root: Path) -> dict` — `{"version": str, "lexemes": list[dict]}`
  - `build_phonology(root: Path) -> dict` — `{"version": str, "transliteration": list[dict]}`
  - `read_version(root: Path) -> str` — версия из frontmatter `README.md`
  - `main() -> int` — пишет `build/lexicon.json`, `build/phonology.json`

- [ ] **Step 1: Написать падающий тест**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tests/test_build.py`:

```python
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build import build_lexicon, build_phonology, read_version

LEXEME = """---
type: lexeme
lemma: gaśi
cyrillic: гащи
pos: nouns
meaning: place
verb_type:
noun_class: "[[Class 7]]"
root: "[[-gaśi-]]"
phon:
etym:
examples:
status: ok
tags: [lexeme]
---
"""

README = """---
version: 0.4
---

# ophidian
"""

TABLE = """# Transliteration

| IPA | latin-1 | latin-2 | latin-3 | cyr-1 | cyr-2 |
| --- | --- | --- | --- | --- | --- |
| θ | t | th | t | т | ф |
| ʃ | ș | sh | w | ш | ш |
"""


def build_vault(directory):
    root = Path(directory)
    (root / "Language" / "Lexicon").mkdir(parents=True)
    (root / "Language" / "Phonology").mkdir(parents=True)
    (root / "Language" / "Lexicon" / "gaśi.md").write_text(LEXEME, encoding="utf-8")
    (root / "Language" / "Phonology" / "Transliteration.md").write_text(TABLE, encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    return root


class BuildLexicon(unittest.TestCase):
    def test_version_read_from_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_version(build_vault(directory)), "0.4")

    def test_lexeme_is_flat_and_links_are_unwrapped(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_lexicon(build_vault(directory))
            self.assertEqual(data["version"], "0.4")
            self.assertEqual(len(data["lexemes"]), 1)
            entry = data["lexemes"][0]
            self.assertEqual(entry["lemma"], "gaśi")
            self.assertEqual(entry["cyrillic"], "гащи")
            self.assertEqual(entry["noun_class"], "Class 7")
            self.assertEqual(entry["root"], "-gaśi-")
            self.assertIsNone(entry["etym"])

    def test_type_and_tags_are_not_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            entry = build_lexicon(build_vault(directory))["lexemes"][0]
            self.assertNotIn("type", entry)
            self.assertNotIn("tags", entry)


class BuildPhonology(unittest.TestCase):
    def test_table_rows_keep_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            data = build_phonology(build_vault(directory))
            rows = data["transliteration"]
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[1],
                {"ipa": "ʃ", "latin-1": "ș", "latin-2": "sh", "latin-3": "w",
                 "cyr-1": "ш", "cyr-2": "ш"},
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Запустить тест и убедиться, что он падает**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_build -v
```

Ожидается: `ModuleNotFoundError: No module named 'tools.build'`

- [ ] **Step 3: Написать реализацию**

Создать `/Users/mitiamorovovsheiner/Github/ophidian/tools/build.py`:

```python
"""Сборка машинных представлений языка из заметок.

Заметки — источник правды. Всё, что здесь пишется, — производное,
руками не правится.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.notes import parse_note, parse_table

ROOT = Path(__file__).resolve().parent.parent

LINK = re.compile(r"^\[\[([^\]]+)\]\]$")

EXPORTED = ["lemma", "cyrillic", "pos", "meaning", "verb_type", "noun_class", "root", "status"]


def _unwrap(value):
    """[[Class 7]] -> Class 7. Остальное как есть."""
    if isinstance(value, str):
        match = LINK.match(value.strip())
        if match:
            return match.group(1)
    return value


def read_version(root):
    fm, _ = parse_note((Path(root) / "README.md").read_text(encoding="utf-8"))
    return fm.get("version")


def build_lexicon(root):
    root = Path(root)
    lexemes = []
    for path in sorted((root / "Language" / "Lexicon").glob("*.md")):
        fm, _ = parse_note(path.read_text(encoding="utf-8"))
        lexemes.append({key: _unwrap(fm.get(key)) for key in EXPORTED})
    return {"version": read_version(root), "lexemes": lexemes}


def build_phonology(root):
    root = Path(root)
    path = root / "Language" / "Phonology" / "Transliteration.md"
    rows = parse_table(path.read_text(encoding="utf-8"))
    header = [cell.lower() for cell in rows[0]]
    header[0] = "ipa"
    transliteration = [dict(zip(header, cells)) for cells in rows[1:]]
    return {"version": read_version(root), "transliteration": transliteration}


def main():
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    lexicon = build_lexicon(ROOT)
    phonology = build_phonology(ROOT)
    (out / "lexicon.json").write_text(
        json.dumps(lexicon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "phonology.json").write_text(
        json.dumps(phonology, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"build/lexicon.json: {len(lexicon['lexemes'])} лексем\n"
        f"build/phonology.json: {len(phonology['transliteration'])} фонем"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Запустить тесты**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 -m unittest tests.test_build -v
```

Ожидается: `OK`, 4 теста.

- [ ] **Step 5: Прогнать сборку на настоящем волте**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && python3 tools/check.py && python3 tools/build.py
```

Ожидается: `build/lexicon.json: 104 лексем` и `build/phonology.json: 18 фонем`

- [ ] **Step 6: Убедиться, что `build/` не попадает в git**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git status --short build/
```

Ожидается: пустой вывод.

- [ ] **Step 7: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add tools/build.py tests/test_build.py && git commit -m "feat: generate build/*.json from notes"
```

---

### Task 9: Шаблоны, Bases, удаление старых YAML

**Files:**
- Create: `Meta/Templates/Root.md`, `Meta/Templates/Affix.md`, `Meta/Templates/Verb Class.md`, `Meta/Bases/Lexicon.base`, `Meta/Bases/Roots.base`
- Modify: `Meta/Templates/Lexeme.md`, `Meta/Templates/Noun Class.md`, `README.md`
- Delete: `lexicon.yaml`, `grammar.yaml`, `phonology.yaml`, `Language/*/raw_*.yaml`, `tools/migrate_frontmatter.py`, `Language/Affixes/template.md`

**Interfaces:**
- Consumes: рабочие `check.py` и `build.py` из Task 7, 8
- Produces: конечное состояние репозитория

- [ ] **Step 1: Удалить рукописные и дублирующие YAML**

Всё их содержание уже перенесено: лексика — в заметки (Task 5), комментарии грамматики и фонологии — в заметки (Task 6), транслитерация — в таблицу (Task 6).

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git rm --quiet lexicon.yaml grammar.yaml phonology.yaml && \
git rm --quiet Language/Lexicon/raw_lexicon.yaml Language/Grammar/raw_grammar.yaml Language/Phonology/raw_phonology.yaml
```

- [ ] **Step 2: Удалить одноразовый скрипт миграции и старый шаблон аффикса**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
git rm --quiet tools/migrate_frontmatter.py Language/Affixes/template.md
```

- [ ] **Step 3: Переписать `Meta/Templates/Lexeme.md`**

```markdown
---
type: lexeme
lemma: {{title}}
cyrillic:
pos:
meaning:
verb_type:
noun_class:
root:
phon:
etym:
examples:
status: ok
tags: [lexeme]
---
```

- [ ] **Step 4: Переписать `Meta/Templates/Noun Class.md`**

```markdown
---
type: noun_class
class:
prefix:
semantics:
tags: [noun_class]
---
```

- [ ] **Step 5: Создать `Meta/Templates/Root.md`**

```markdown
---
type: root
meaning:
tags: [root]
---
```

- [ ] **Step 6: Создать `Meta/Templates/Affix.md`**

```markdown
---
type: affix
cyrillic:
meaning:
etym:
examples:
tags: [affix]
---
```

- [ ] **Step 7: Создать `Meta/Templates/Verb Class.md`**

```markdown
---
type: verb_class
affix:
semantics:
tags: [verb_class]
---
```

- [ ] **Step 8: Создать `Meta/Bases/Lexicon.base`**

Заменяет неработавшие dataview-запросы. Колонки и фильтры дальше настраиваются мышкой прямо в Obsidian.

```yaml
filters:
  and:
    - file.hasTag("lexeme")
views:
  - type: table
    name: Все лексемы
    order:
      - lemma
      - cyrillic
      - pos
      - meaning
      - noun_class
    sort:
      - property: lemma
        direction: ASC
  - type: table
    name: Глаголы
    filters:
      and:
        - pos == "verbs"
    order:
      - lemma
      - meaning
      - verb_type
    sort:
      - property: lemma
        direction: ASC
  - type: table
    name: Существительные
    filters:
      and:
        - pos == "nouns"
    order:
      - lemma
      - meaning
      - noun_class
    sort:
      - property: lemma
        direction: ASC
  - type: table
    name: Требует проверки
    filters:
      and:
        - status == "unverified"
    order:
      - lemma
      - meaning
```

- [ ] **Step 9: Создать `Meta/Bases/Roots.base`**

```yaml
filters:
  and:
    - file.hasTag("root")
views:
  - type: table
    name: Корни
    order:
      - file.name
      - meaning
    sort:
      - property: file.name
        direction: ASC
```

- [ ] **Step 10: Переписать `README.md`**

```markdown
---
version: 0.4
---

# Ophidian

Ophidian is a constructed language created for communication between humans and snakes
in magical universes.

Этот репозиторий одновременно является волтом Obsidian: открой его корень как волт.

## Structure

| Папка | Что внутри |
| --- | --- |
| `Language/` | Источник правды по языку: лексика, корни, аффиксы, грамматика, фонология, классы |
| `Corpus/` | Тексты на языке |
| `Lore/` | Лор |
| `Drafts/` | Черновики и WIP — не источник правды |
| `Meta/` | Шаблоны заметок и таблицы Bases |
| `tools/` | Валидатор и генератор |
| `build/` | Генерируется скриптом, руками не трогать, в git не хранится |

Правило: `Language/` правится только через Obsidian, `build/` пишет только скрипт.

## Checks

```bash
python3 tools/check.py && python3 tools/build.py
```

`check.py` разделяет ошибки и предупреждения: падает только на структурной поломке,
неполнота языка печатается сводкой. Тесты — `python3 -m unittest discover tests`.

## Lore of the Language

Ophidian serves as a bridge for communication between humans and snakes. It was
magically created by humans, as snakes themselves don't need it, relying primarily on
non-verbal communication.

On one hand, Ophidian reflects the unique perception of the world by snakes and includes
a significant layer of native snake vocabulary (for example, the word to hiss was
borrowed from the snake language into human languages). On the other hand, many words in
Ophidian are borrowed from human languages, especially when it comes to concepts
unfamiliar or uninteresting to snakes.

If you'd like access to extended materials for learning Ophidian or wish to contribute
your ideas, much of the content is available on my Patreon page:
https://www.patreon.com/c/Azoysheyn
```

- [ ] **Step 11: Настроить исключения Obsidian**

Записать в `/Users/mitiamorovovsheiner/Github/ophidian/.obsidian/app.json`:

```json
{
  "userIgnoreFilters": [
    "docs/",
    "tools/",
    "tests/",
    "build/"
  ]
}
```

- [ ] **Step 12: Полная проверка**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && \
python3 -m unittest discover tests -v && \
python3 tools/check.py && \
python3 tools/build.py
```

Ожидается: все тесты `OK`, `0 ошибок`, `104 лексем`, `18 фонем`.

- [ ] **Step 13: Убедиться, что рукописных YAML не осталось**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && find . -name '*.yaml' -not -path './.git/*'
```

Ожидается: пустой вывод. Файлы `Meta/Bases/*.base` под маску не попадают — у них своё расширение, и это не рукописные данные, а конфигурация таблиц Obsidian.

- [ ] **Step 14: Закоммитить**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && git add -A && git commit -m "feat: templates, bases, readme; drop hand-written yaml"
```

- [ ] **Step 15: Показать итоговое дерево**

```bash
cd /Users/mitiamorovovsheiner/Github/ophidian && ls -A && git log --oneline main..HEAD
```

---

## Ручная проверка после миграции

Автотесты не покрывают Obsidian. Проверить руками:

- [ ] Открыть корень репозитория как волт в Obsidian — заметки на месте, граф связей строится.
- [ ] Открыть `Meta/Bases/Lexicon.base` — таблица показывает 104 лексемы, переключение между видами работает.
- [ ] Открыть `Language/Lexicon/gaśi.md` — ссылки на `[[Class 7]]` и `[[-gaśi-]]` кликаются.
- [ ] Открыть `Language/Roots/-gaśi-.md` — в backlinks видно ссылающиеся лексемы.
- [ ] `docs/`, `tools/`, `tests/`, `build/` не появляются в поиске и быстром переключателе.
