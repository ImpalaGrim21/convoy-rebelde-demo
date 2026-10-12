"""Verify the pinned release and assemble only its declared public files."""
import hashlib
import json
import pathlib
import re
import shutil
import stat
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_relative(name):
    require(isinstance(name, str) and name and "\\" not in name, "Ruta inválida")
    require(not any(ord(c) < 32 for c in name), "Ruta con caracteres de control")
    route = pathlib.PurePosixPath(name)
    require(not route.is_absolute() and route.as_posix() == name, "Ruta no canónica")
    require(all(part not in (".", "..") and ":" not in part for part in route.parts), "Ruta fuera del sitio")
    return route


def main():
    config = json.loads(pathlib.Path("deployment.json").read_text(encoding="utf-8"))
    manifest_path = pathlib.Path("manifest-web.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(re.fullmatch(r"[0-9a-f]{64}", config["sha256"]) is not None, "SHA del ZIP inválido")
    asset = safe_relative(config["asset"])
    require(len(asset.parts) == 1 and asset.suffix == ".zip", "Asset inválido")
    archive = pathlib.Path("package") / asset.name
    require(sha_file(archive) == config["sha256"], "ZIP distinto de la distribución fijada")
    require(manifest["version"] == config["tag"], "Tag y manifiesto distintos")
    expected = {}
    for metadata in manifest["archivos"]:
        name = metadata["archivo"]
        safe_relative(name)
        require(name not in expected and name not in ("manifest-web.json", ".nojekyll"), "Entrada duplicada o reservada")
        require(type(metadata["bytes"]) is int and metadata["bytes"] >= 0, "Tamaño inválido")
        require(re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"]) is not None, "SHA de archivo inválido")
        expected[name] = metadata
    require("index.html" in expected and bool(expected), "Falta entrada al juego")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        require(len(entries) == len(expected) and {entry.filename for entry in entries} == set(expected), "Contenido no autorizado o duplicado en el ZIP")
        for entry in entries:
            safe_relative(entry.filename)
            require(not entry.is_dir(), "No se admiten entradas de directorio")
            require(not stat.S_ISLNK(entry.external_attr >> 16), "No se admiten enlaces")
            require(entry.file_size == expected[entry.filename]["bytes"], "Tamaño ZIP distinto")
        site = pathlib.Path("_site")
        require(not site.exists(), "Destino ya existente; no sobrescribir")
        site.mkdir()
        root = site.resolve()
        for name, metadata in expected.items():
            target = site.joinpath(*safe_relative(name).parts)
            require(target.resolve().is_relative_to(root), "Destino fuera del sitio")
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            size = 0
            with package.open(name) as source, target.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            require(size == metadata["bytes"] and digest.hexdigest() == metadata["sha256"], "Archivo distinto: " + name)
    shutil.copyfile(manifest_path, site / "manifest-web.json")
    (site / ".nojekyll").touch()
    print(f"Distribución íntegra: {len(expected)} archivos públicos verificados.")


if __name__ == "__main__":
    main()
