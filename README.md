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
| `tests/` | Тесты (unittest) для валидатора и генератора |
| `docs/` | Дополнительная документация |
| `build/` | Генерируется скриптом, руками не трогать, в git не хранится |

Правило: `Language/` правится только через Obsidian, `build/` пишет только скрипт.

## Working in the vault

- **Добавить лексему**: открой `Language/Lexicon/`, создай новую заметку и
  вставь в неё шаблон командой Obsidian "Insert template" (Ctrl/Cmd+P) —
  шаблоны лежат в `Meta/Templates/` и уже привязаны к плагину Templates.
  Заполни поля frontmatter по образцу соседних заметок.
- **Смотреть язык целиком**: таблицы `Meta/Bases/` (плагин Obsidian
  Bases) дают сводный, фильтруемый вид лексикона, корней и классов —
  удобнее, чем листать заметки по одной.
- **Перед коммитом** обязательно прогони обе проверки:

  ```bash
  python3 tools/check.py && python3 tools/build.py
  ```

  `check.py` не должен падать (0 ошибок — предупреждения нормальны),
  `build.py` должен собрать `build/lexicon.json` и `build/phonology.json`
  без ошибок.

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
