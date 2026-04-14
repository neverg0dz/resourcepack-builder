import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "rp_config.json"


@dataclass(slots=True)
class Config:
    project_name: str
    project_version: str
    input_dir: Path
    output_dir: Path
    nbt_key: str
    default_type: str
    exact_types: dict[str, str]
    keyword_types: dict[str, str]

    @property
    def output_zip(self) -> Path:
        return self.output_dir / f"{self.project_name}-rp-{self.project_version}.zip"

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            raise FileNotFoundError(f"Файл конфига не найден: {path}")

        with path.open("r", encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)

        general = raw.get("general", {})
        paths = raw.get("paths", {})
        exact_types = raw.get("exact_types", {})
        keyword_types = raw.get("keyword_types", {})

        project_name = str(general.get("project_name", "ResourcePack"))
        project_version = str(general.get("project_version", "1.0.0"))
        nbt_key = str(general.get("nbt_key", "custom"))
        default_type = str(general.get("default_type", "CLAY_BALL")).upper()

        input_dir = ROOT_DIR / str(paths.get("input_dir", "resourcepack"))
        output_dir = ROOT_DIR / str(paths.get("output_dir", "build/resourcepack"))

        normalized_exact = {
            str(name).lower(): str(item_type).upper()
            for name, item_type in exact_types.items()
        }
        normalized_keywords = {
            str(keyword).lower(): str(item_type).upper()
            for keyword, item_type in keyword_types.items()
        }

        return cls(
            project_name=project_name,
            project_version=project_version,
            input_dir=input_dir,
            output_dir=output_dir,
            nbt_key=nbt_key,
            default_type=default_type,
            exact_types=normalized_exact,
            keyword_types=normalized_keywords,
        )


class PackBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config

    def build(self) -> None:
        in_minecraft_dir = self.config.input_dir / "assets" / "minecraft"
        if not in_minecraft_dir.exists():
            raise FileNotFoundError(
                f"Не найдена папка assets/minecraft: {in_minecraft_dir}"
            )

        self.config.output_zip.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
                prefix=f"{self.config.project_name}-rp-bundler-"
        ) as tmp:
            temp_dir = Path(tmp)
            out_minecraft_dir = temp_dir / "assets" / "minecraft"

            self._process_cit(in_minecraft_dir, out_minecraft_dir)
            self._copy_model_files(in_minecraft_dir, out_minecraft_dir)
            self._copy_standard_folders(in_minecraft_dir, out_minecraft_dir)
            self._copy_root_pack_files(temp_dir)
            self._write_zip(temp_dir)

        print(f"\n✅ Resource pack saved to: {self.config.output_zip}")

    def resolve_item_type(self, name: str) -> str:
        normalized_name = name.lower()

        if normalized_name in self.config.exact_types:
            return self.config.exact_types[normalized_name]

        for keyword, item_type in self.config.keyword_types.items():
            if keyword in normalized_name:
                return item_type

        return self.config.default_type

    def make_cit_base(self, name: str) -> dict[str, str]:
        return {
            "type": "item",
            "items": self.resolve_item_type(name),
            f"nbt.{self.config.nbt_key}": name,
        }

    def _process_cit(self, in_minecraft_dir: Path, out_minecraft_dir: Path) -> None:
        src_cit_root = in_minecraft_dir / "mcpatcher"
        dst_cit_root = out_minecraft_dir / "mcpatcher" / "cit"

        if not src_cit_root.exists():
            return

        all_jsons = {
            f.relative_to(src_cit_root).with_suffix(""): f
            for f in self.find_files(src_cit_root, ".json")
        }

        for png in self.find_files(src_cit_root, ".png"):
            rel_path = png.relative_to(src_cit_root)
            rel_without_suffix = rel_path.with_suffix("")
            name = png.stem

            out_png = dst_cit_root / rel_path
            out_png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, out_png)

            model_json = all_jsons.get(rel_without_suffix)

            if model_json is not None:
                out_json = dst_cit_root / model_json.relative_to(src_cit_root)
                out_json.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(model_json, out_json)

                props = {**self.make_cit_base(name), "model": f"{name}.json"}
                print(f'Writing model properties for "{rel_path.as_posix()}"')
            else:
                props = {**self.make_cit_base(name), "texture": name}
                print(f'Writing texture properties for "{rel_path.as_posix()}"')

            out_props = (dst_cit_root / rel_path).with_suffix(".properties")
            self.write_properties(props, out_props)

    def _copy_model_files(self, in_minecraft_dir: Path, out_minecraft_dir: Path) -> None:
        src_models_root = in_minecraft_dir / "models"
        if not src_models_root.exists():
            return

        dst_bedrock_root = out_minecraft_dir / "bedrock"

        for model_file in self.find_files(src_models_root, ".model"):
            rel_path = model_file.relative_to(src_models_root)
            out_model = dst_bedrock_root / rel_path
            out_model.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(model_file, out_model)
            print(f'Copying model "{rel_path.as_posix()}"')

    def _copy_standard_folders(self, in_minecraft_dir: Path, out_minecraft_dir: Path) -> None:
        excluded_dirs = {"mcpatcher", "bedrock"}

        for src in in_minecraft_dir.iterdir():
            if not src.is_dir():
                continue
            if src.name in excluded_dirs:
                continue

            dst = out_minecraft_dir / src.name

            shutil.copytree(
                src,
                dst,
                dirs_exist_ok=True,
                ignore=self.ignore_model_files if src.name == "models" else None,
            )

    def _copy_root_pack_files(self, temp_dir: Path) -> None:
        for extra in ("pack.mcmeta", "pack.png"):
            src = self.config.input_dir / extra
            if src.exists():
                shutil.copy2(src, temp_dir / extra)

    def _write_zip(self, temp_dir: Path) -> None:
        with zipfile.ZipFile(self.config.output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            self.add_folder_to_zip(zf, temp_dir, arcname_base=temp_dir)

    @staticmethod
    def write_properties(props: dict[str, str], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["# Auto-generated\n"]
        for key, value in props.items():
            lines.append(f"{key}={value}\n")
        path.write_text("".join(lines), encoding="utf-8")

    @staticmethod
    def find_files(directory: Path, extension: str) -> list[Path]:
        if not directory.exists():
            return []
        return [f for f in directory.rglob(f"*{extension}") if f.is_file()]

    @staticmethod
    def ignore_model_files(_dir: str, files: list[str]) -> list[str]:
        return [f for f in files if f.endswith(".model")]

    @staticmethod
    def add_folder_to_zip(
            zf: zipfile.ZipFile,
            folder: Path,
            arcname_base: Path | None = None,
    ) -> None:
        base = arcname_base or folder.parent
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(base))


def main() -> None:
    config = Config.load(CONFIG_PATH)
    builder = PackBuilder(config)
    builder.build()


if __name__ == "__main__":
    main()