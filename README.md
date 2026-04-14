# Minecraft Resource Pack Builder

A simple Python tool for building Minecraft resource packs with automatic OptiFine CIT generation.

This builder scans your resource pack source, generates `.properties` files for CIT items, preserves folder structure, and outputs a ready-to-use `.zip` pack.

---

## ✨ Features

* 🔄 **Automatic CIT generation**

  * Creates `.properties` files for every `.png`
  * Supports both texture-based and model-based items

* 🧠 **Smart item detection**

  * Uses filename keywords (e.g. `axe`, `sword`, `food`)
  * Supports exact name overrides

* 📁 **Preserves folder structure**

  * Keeps your original directory layout inside the final pack

* 📦 **Automatic packaging**

  * Outputs a ready-to-use `.zip` resource pack

* 🔊 **Supports all asset types**

  * `textures`, `models`, `blockstates`, `sounds`, etc.

* 🧩 **Bedrock model support**

  * `.model` files are automatically moved to `assets/minecraft/bedrock`

* ⚙️ **Fully configurable**

  * All mappings and settings are defined in a JSON config

---

## 📂 Project Structure

Example input structure:

```
resourcepack/
  pack.mcmeta
  pack.png

  assets/
    minecraft/
      mcpatcher/
        weapons/
          axe.png
        food/
          apple.png

      models/
        guns/
          pistol.model

      textures/
      sounds/
      blockstates/
```

Output structure (inside ZIP):

```
assets/minecraft/
  mcpatcher/cit/...        # generated CIT files
  bedrock/...              # .model files
  textures/
  sounds/
  models/
  blockstates/
```

---

## ⚙️ Configuration (`rp_config.json`)

Example:

```json
{
  "general": {
    "project_name": "MyPack",
    "project_version": "1.0.0",
    "nbt_key": "custom",
    "default_type": "CLAY_BALL"
  },

  "paths": {
    "input_dir": "resourcepack",
    "output_dir": "build/resourcepack"
  },

  "exact_types": {
    "wood": "LOG"
  },

  "keyword_types": {
    "axe": "STONE_AXE",
    "sword": "DIAMOND_SWORD",
    "apple": "COOKED_BEEF"
  }
}
```

---

## 🧠 How It Works

For each `.png` file:

1. If filename matches `exact_types` → use that item
2. Else if filename contains a keyword → use mapped item
3. Else → fallback to `default_type`

Then:

* If `.json` model exists → uses `model=...`
* Otherwise → uses `texture=...`

---

## 🚀 Usage

```bash
python builder.py
```

The built resource pack will be saved to:

```
build/resourcepack/<name>-rp-<version>.zip
```

---

## 📌 Example

```
iron_axe_old.png → STONE_AXE
golden_sword.png → DIAMOND_SWORD
apple_pie.png → COOKED_BEEF
```

Generated `.properties`:

```
type=item
items=STONE_AXE
nbt.custom=iron_axe_old
texture=iron_axe_old
```

---

## 🛠 Requirements

* Python 3.10+
* No external dependencies

---

## 📄 License

MIT (or your choice)

---

## 💡 Notes

* Designed for OptiFine CIT workflow
* Works with deeply nested folder structures
* Easy to extend and customize

---

## 🔥 Future Ideas

* Custom property rules per keyword
* Multiple input sources
* GUI interface
* Live preview / validation
