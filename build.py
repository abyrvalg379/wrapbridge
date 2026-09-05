# Сборка WrapBridge: extension-зип в out/.
# Источник: wrapbridge.py (с bl_info). Для extension bl_info вырезается —
# манифест берётся из blender_manifest.toml.
import os
import re
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "out"))


def read_version():
    src = open(os.path.join(HERE, "wrapbridge.py"), encoding="utf-8").read()
    m = re.search(r'"version": \((\d+), (\d+), (\d+)\)', src)
    return ".".join(m.groups()) if m else "0.0.0"


def strip_bl_info(src):
    return re.sub(r"bl_info = \{.*?\}\n\n", "", src, flags=re.S)


def build_zip(kind, version):
    staging = os.path.join(OUT, "_stage", "wrapbridge")
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(os.path.join(staging, "templates"))

    src = open(os.path.join(HERE, "wrapbridge.py"), encoding="utf-8").read()
    if kind == "extension":
        open(os.path.join(staging, "__init__.py"), "w",
             encoding="utf-8", newline="\n").write(strip_bl_info(src))
        manifest = open(os.path.join(HERE, "blender_manifest.toml"),
                        encoding="utf-8").read()
        manifest = re.sub(r'^version = "[0-9.]+"', 'version = "%s"' % version,
                          manifest, count=1, flags=re.M)
        open(os.path.join(staging, "blender_manifest.toml"), "w",
             encoding="utf-8", newline="\n").write(manifest)
    else:
        open(os.path.join(staging, "__init__.py"), "w",
             encoding="utf-8", newline="\n").write(src)

    # приватный шаблон (реальный граф) идёт только в --private сборку;
    # публичная получает заглушку из template_gen
    if "--private" in sys.argv:
        shutil.copy(os.path.join(HERE, "templates", "template.wrap"),
                    os.path.join(staging, "templates"))
    else:
        import subprocess as sp
        sp.run([sys.executable, os.path.join(HERE, "template_gen.py"),
                os.path.join(tempfile.gettempdir(), "wrapbridge"),
                os.path.join(staging, "templates", "template.wrap")], check=True)
    shutil.copy(os.path.join(HERE, "README.md"), staging)

    name = os.path.join(OUT, "wrapbridge_v%s_%s.zip" % (version, kind))
    if os.path.isfile(name):
        os.remove(name)
    with zipfile.ZipFile(name, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(staging):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, os.path.dirname(staging)))
    shutil.rmtree(os.path.join(OUT, "_stage"))
    return name


if __name__ == "__main__":
    print("OK:", build_zip("extension", read_version()))
