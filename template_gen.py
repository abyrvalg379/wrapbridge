# Генератор шаблонного .wrap-проекта для WrapBridge.
# Формат v5 (2025.10.8): ноды требуют ПОЛНЫЙ набор полей, иначе миграция
# формата при загрузке падает. Структура снята с галерейных проектов.
#
# Запуск: python template_gen.py [workdir_base_scan]
# По умолчанию пути ведут в run-папку, которую создаёт аддон (%TEMP%/wrapbridge).
import json
import os
import sys
import tempfile

RUN_DIR = os.path.join(tempfile.gettempdir(), "wrapbridge")


def visual_param():
    return {"dataType": "VisualParam", "value": {
        "colorBack": {"b": 85, "g": 85, "r": 85},
        "colorFront": {"b": 255, "g": 129, "r": 61},
        "colorWire": {"b": 34, "g": 26, "r": 17},
        "isLightingEnabled": True, "isSurfaceEnabled": True,
        "isWireframeEnabled": True, "surfaceFillType": 1}}


def transform():
    return {"dataType": "Transform", "value": {
        "offset": {"x": 0, "y": 0, "z": 0},
        "rotationQuat": {"scalar": 1, "x": 0, "y": 0, "z": 0},
        "scale": 1, "translation": {"x": 0, "y": 0, "z": 0}}}


def load_geom(nid, x, path):
    return {"color": {"a": 0, "b": 0, "g": 0, "r": 0}, "hasColor": False,
            "isAlwaysVisible": True, "nodeId": nid, "nodeType": "LoadGeom",
            "x": x, "y": 0,
            "params": {"fileNames": {"dataType": "StringList", "value": [path]},
                       "texture": {"dataType": "Image"},
                       "transform": transform(), "visualParam": visual_param()}}


def save_geom(nid, x, path, source_nid):
    # v5-параметры SaveGeom: fileName, geom, includeTransform, saveNormals
    # (saveUVs/writeUVs в старом формате нет — excess = ошибка загрузки)
    return {"color": {"a": 0, "b": 0, "g": 0, "r": 0}, "hasColor": False,
            "isAlwaysVisible": True, "nodeId": nid, "nodeType": "SaveGeom",
            "x": x, "y": 0,
            "params": {"fileName": {"dataType": "String", "value": path},
                       "geom": {"dataType": "Geom", "connectedNodeId": source_nid},
                       "includeTransform": {"dataType": "Bool", "value": False},
                       "saveNormals": {"dataType": "Bool", "value": True}}}


def build(run_dir=RUN_DIR):
    """base.obj + scan.obj -> wrapped.obj (скан копится как есть; настоящий
    врапинг-граф сохраняешь из Wrap GUI в этот же шаблон)."""
    return {
        "formatVersion": 5,
        "nodes": {
            "Base": load_geom(0, 0, os.path.join(run_dir, "base.obj")),
            "Scan": load_geom(1, 150, os.path.join(run_dir, "scan.obj")),
            "Save": save_geom(2, 300, os.path.join(run_dir, "wrapped.obj"), 1),
        },
        "timeline": {"current": 0, "max": 25, "min": 0},
    }


if __name__ == "__main__":
    # argv[1] = run_dir, argv[2] = выходной файл (ОБЯЗАТЕЛЬНО вне templates/,
    # там лежит приватный шаблон с реальным графом)
    run_dir = sys.argv[1] if len(sys.argv) > 1 else RUN_DIR
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RUN_DIR, "template.wrap")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(run_dir), f, indent=2)
    print("OK:", out)
