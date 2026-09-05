# WrapBridge — Blender <-> Faceform Wrap bridge (v0.3)
# Пайплайн: экспорт base+scan в OBJ -> подстановка путей в шаблон .wrap ->
# headless WrapCmd compute -> импорт результата в Blender или в Wrap GUI.
#
# Шаблон .wrap: сохраняешь проект в Wrap GUI, в LoadGeom-нодах указываешь
# пути из run-папки (base.obj, scan.obj). WrapBridge перепишет fileNames
# у LoadGeom и возьмёт пути результатов из SaveGeom/SaveImage-нод.
bl_info = {
    "name": "WrapBridge",
    "author": "Maksim Kovalev",
    "version": (0, 5, 3),
    "blender": (4, 2, 0),
    "location": "3D Viewport > N-panel > WrapBridge",
    "description": "Bridge to Faceform Wrap: export base+scan, headless WrapCmd compute, import results",
    "category": "Object",
}

import bpy
from bpy.props import FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

import json
import os
import subprocess
import tempfile

WRAP_CMD = r"C:\Program Files\Faceform\Wrap 2025.10.8\WrapCmd.exe"
WORK_DIR = os.path.join(tempfile.gettempdir(), "wrapbridge")


def _template_path():
    # Шаблон из проекта (templates рядом с аддоном / на уровень выше),
    # иначе fallback в run-папку
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "templates", "template.wrap"),
                 os.path.join(os.path.dirname(here), "templates", "template.wrap"),
                 os.path.join(WORK_DIR, "template.wrap")):
        if os.path.isfile(cand):
            return cand
    return os.path.join(WORK_DIR, "template.wrap")


def _ensure_work_dir():
    os.makedirs(WORK_DIR, exist_ok=True)


def export_object(obj, filepath):
    """Экспорт одного объекта в OBJ (с модификаторами), в исходном масштабе."""
    # выделяем только целевой объект: у wm.obj_export нет покомпонентного выбора
    for o in bpy.data.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        apply_modifiers=True,
        export_normals=True,
        export_uv=True,
        export_materials=False,
    )
    return filepath


def _rewrite_loadgeom_paths(project, work_dir):
    """Все LoadGeom смотрят на base.obj / scan.obj по порядку.
    Формат 69 (2025.x): fileName — строка; старый: fileNames — StringList."""
    names = ["base.obj", "scan.obj"]
    i = 0
    for node in project["nodes"].values():
        if node.get("nodeType") == "LoadGeom":
            path = os.path.join(work_dir, names[min(i, len(names) - 1)])
            params = node["params"]
            if "fileName" in params:
                params["fileName"] = {"value": path}
            else:
                params["fileNames"] = {"dataType": "StringList", "value": [path]}
            i += 1
    return i


def collect_outputs(project):
    """Пути всех результатов из Save* нод (SaveGeom/SaveImage)."""
    outputs = {"geom": [], "image": []}
    for node in project["nodes"].values():
        ntype = node.get("nodeType", "")
        if ntype.startswith("Save"):
            fname = node.get("params", {}).get("fileName", {}).get("value")
            if not fname:
                continue
            if "Geom" in ntype:
                outputs["geom"].append(fname)
            elif "Image" in ntype or "Texture" in ntype:
                outputs["image"].append(fname)
    return outputs


def make_run(template_path, work_dir):
    """Собрать run.wrap из шаблона с путями на свежие OBJ (без вычислений)."""
    _ensure_work_dir()
    with open(template_path, "r", encoding="utf-8") as f:
        project = json.load(f)

    n_loads = _rewrite_loadgeom_paths(project, work_dir)
    project_path = os.path.join(work_dir, "run.wrap")
    with open(project_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2)
    return project_path, n_loads


def compute(template_path, work_dir):
    """Подготовить проект из шаблона и прогнать WrapCmd headless."""
    project_path, n_loads = make_run(template_path, work_dir)

    cmd = [WRAP_CMD, "compute", project_path, "-s", "0", "-e", "0"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    log = (proc.stdout or "") + (proc.stderr or "")
    ok = "COMPLETE" in log and proc.returncode == 0
    return ok, n_loads, log.strip()


def import_results(project_path):
    """Импорт всех SaveGeom-результатов как объектов."""
    with open(project_path, "r", encoding="utf-8") as f:
        project = json.load(f)
    imported = []
    for path in collect_outputs(project)["geom"]:
        if not os.path.isfile(path):
            continue
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        imported.extend(new)
    return imported


class WrapBridge_props(PropertyGroup):
    """Слоты source-геометрии для пайплайна."""

    base_obj: PointerProperty(
        name="Base",
        description="Базовый меш с целевой топологией (пойдёт в base.obj)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "MESH",
    )
    scan_obj: PointerProperty(
        name="Scan",
        description="Скан/источник для врапинга (пойдёт в scan.obj)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "MESH",
    )


def _wrap_gui_running():
    """Запущен ли Wrap GUI (не WrapCmd)?"""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Wrap.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, errors="ignore", timeout=10,
        ).stdout
        return "wrap.exe" in out.lower()
    except Exception:
        return False


def _template_stamp(template_path):
    """Хэш шаблона: менялся ли граф с прошлого раза."""
    import hashlib
    _ensure_work_dir()
    try:
        with open(template_path, "rb") as f:
            digest = hashlib.md5(f.read()).hexdigest()
    except OSError:
        return None
    stamp = os.path.join(WORK_DIR, "template.md5")
    try:
        with open(stamp, "r") as f:
            if f.read().strip() == digest:
                return digest
    except OSError:
        pass
    try:
        with open(stamp, "w") as f:
            f.write(digest)
    except OSError:
        pass
    return None


class WrapBridge_OT_send(Operator):
    """Экспортировать base+scan в открытый Wrap (или открыть его, если закрыт)"""
    bl_idname = "wrapbridge.send_to_wrap"
    bl_label = "Send to Wrap"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.wrapbridge_props
        if not props.scan_obj:
            self.report({"ERROR"}, "Не назначен Scan")
            return {"CANCELLED"}

        _ensure_work_dir()
        template = _template_path()
        if props.base_obj:
            export_object(props.base_obj, os.path.join(WORK_DIR, "base.obj"))
        export_object(props.scan_obj, os.path.join(WORK_DIR, "scan.obj"))

        # собрать свежий run.wrap (без headless-прогона: точки расставляются
        # вручную в GUI)
        make_run(template, WORK_DIR)
        run_path = os.path.join(WORK_DIR, "run.wrap")
        if not os.path.isfile(run_path):
            self.report({"ERROR"}, "run.wrap не создан")
            return {"CANCELLED"}

        template_changed = _template_stamp(template) is None
        if _wrap_gui_running() and not template_changed and os.path.isfile(run_path + ".opened"):
            # Wrap уже открыт, и граф не менялся: пути в run.wrap постоянные,
            # достаточно пересчитать ноды LoadGeom в открытом проекте
            self.report({"INFO"}, "OBJ обновлены — пересчитай ноды в открытом Wrap")
            return {"FINISHED"}

        os.startfile(run_path)  # откроется в Wrap GUI (ассоциация .wrap)
        open(os.path.join(WORK_DIR, "run.wrap.opened"), "w").close()
        if template_changed:
            self.report({"INFO"}, "Шаблон обновлён — открыт свежий run.wrap")
        else:
            self.report({"INFO"}, "Отправлено в Wrap")
        return {"FINISHED"}


class WrapBridge_OT_compute(Operator):
    """Экспортировать base+scan и прогнать Wrap headless"""
    bl_idname = "wrapbridge.compute"
    bl_label = "Export + Compute"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.wrapbridge_props
        if not props.scan_obj:
            self.report({"ERROR"}, "Не назначен Scan")
            return {"CANCELLED"}

        _ensure_work_dir()
        if props.base_obj:
            export_object(props.base_obj, os.path.join(WORK_DIR, "base.obj"))
        export_object(props.scan_obj, os.path.join(WORK_DIR, "scan.obj"))

        ok, n_loads, log = compute(_template_path(), WORK_DIR)
        context.scene["wrapbridge_log"] = log[-2000:]
        if not ok:
            self.report({"ERROR"}, "WrapCmd упал, лог в scene['wrapbridge_log']")
            print("[WrapBridge]", log)
            return {"CANCELLED"}
        self.report({"INFO"}, "Wrap отработал (LoadGeom: %d), результаты в %s" % (n_loads, WORK_DIR))
        return {"FINISHED"}


class WrapBridge_OT_import(Operator):
    """Импортировать результаты SaveGeom в сцену"""
    bl_idname = "wrapbridge.import_results"
    bl_label = "Import Results"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        run_path = os.path.join(WORK_DIR, "run.wrap")
        if not os.path.isfile(run_path):
            self.report({"ERROR"}, "Сначала выполни Compute")
            return {"CANCELLED"}
        objs = import_results(run_path)
        if not objs:
            self.report({"WARNING"}, "SaveGeom-результаты не найдены на диске")
            return {"CANCELLED"}
        for o in objs:
            o.select_set(True)
        context.view_layer.objects.active = objs[0]
        self.report({"INFO"}, "Импортировано объектов: %d" % len(objs))
        return {"FINISHED"}


class WrapBridge_PT_panel(Panel):
    bl_label = "WrapBridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "WrapBridge"

    def draw(self, context):
        props = context.scene.wrapbridge_props
        col = self.layout.column()

        col.prop(props, "base_obj")
        col.prop(props, "scan_obj")
        col.separator()
        col.operator("wrapbridge.send_to_wrap", icon="EXPORT")
        col.operator("wrapbridge.compute", icon="MOD_MESHDEFORM")
        col.operator("wrapbridge.import_results", icon="IMPORT")
        box = col.box()
        box.label(text="Work: " + WORK_DIR, icon="FILE_FOLDER")
        box.label(text="Template: " + os.path.basename(_template_path()))


classes = (WrapBridge_props, WrapBridge_OT_send, WrapBridge_OT_compute, WrapBridge_OT_import, WrapBridge_PT_panel)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.wrapbridge_props = PointerProperty(type=WrapBridge_props)


def unregister():
    del bpy.types.Scene.wrapbridge_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
