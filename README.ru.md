# WrapBridge

Мост Blender ⇄ Faceform Wrap. Отправляет базовый меш и скан в Wrap и возвращает результат врапинга — без Проводника и единого ручного пути.

*English documentation: [README.md](README.md)*

![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange) ![License](https://img.shields.io/badge/License-GPL--3.0-blue)

## Что делает

N-панель (**WrapBridge**), три кнопки:

- **Send to Wrap** — выгружает Base + Scan в горячие OBJ и открывает проект в Wrap GUI. Если Wrap уже запущен — просто обновляет файлы (пути в проекте постоянные, достаточно пересчитать ноды LoadGeom). Если шаблон графа менялся — свежий проект переоткрывается автоматически.
- **Export + Compute** — тот же экспорт + headless-прогон `WrapCmd`. Без GUI вообще. Для графов, которые не требуют ручной правки (точки хранятся внутри шаблона).
- **Import Results** — затягивает результаты всех `SaveGeom`-нод обратно в сцену.

В панели — слоты **Base** и **Scan**; модификаторы применяются при экспорте.

## Как это работает

1. WrapBridge хранит шаблон `.wrap` с твоим графом врапинга.
2. При каждом запуске переписывает пути `LoadGeom` на горячие файлы в `%TEMP%\wrapbridge\` (`base.obj`, `scan.obj`).
3. Всё, что пишут `Save*`-ноды, находится автоматически на импорте — никаких захардкоженных имён результата.

Сам граф живёт в Wrap: собери его один раз в GUI (точки, FastWrapping, браш — что нужно), направь `LoadGeom` на горячие файлы и сохрани как `templates/template.wrap`. Точки хранятся внутри шаблона, поэтому последующие прогоны полностью автоматические.

## Установка

**Extension** (Blender 4.2+): скачайте `wrapbridge_v*.zip` со страницы [последнего релиза](https://github.com/abyrvalg379/wrapbridge/releases/latest), затем *Preferences → Get Extensions → ⌄ Install from Disk*.

Легаси-зипы больше не поддерживаются.

**Требования:** Faceform Wrap в `C:\Program Files\Faceform\` (путь — константа `WRAP_CMD` в исходнике, поправь под себя).

## Сборка

```
python build.py    # -> ../out/wrapbridge_v*_extension.zip
```

## Примечания

- Проверено с Faceform Wrap 2025.10.8 (headless `WrapCmd compute` работает на бесплатном триале).
- `.wrap`-проекты — это JSON: связи нод лежат внутри плагов параметров (`connectedNodeId`); шаблоны графа проще собирать в Wrap GUI, а не руками.

## Лицензия

GPL-3.0-or-later. Автор: Maksim Kovalev.
