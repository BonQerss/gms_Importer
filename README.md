# GMS Model Importer for Blender

Tool designed to import GMS files into Blender.
Based on the MaxScript by Pionome and modified for Blender by Dexxtrip/BonQ

# File Format Support

- **`.gms`** 

Pretty self explanatory

# Texture Conversion

This tool depends on Gimconv which is not shipped with this Github.

**With GimConv.exe:**
- Place GimConv.exe in `gms_importer/tools/gim/gimconv`
- Textures are automatically converted during import

# Supported Games

- Persona 3 Portable (PSP, PC, everything else)
- Persona 4 Golden (PC, PSVita, everything else)
- Other PSP games that use GMO (untested but probably)

# Issues

Armatures are not being imported properly yet. Gotta fix that when I'm not coping through covid tearing up my insides.
Meshes for P4G don't import fully correctly due to the align to the floor function, need to figure out how to read the coordinates better.
Some materials for P4G don't work, they add a white haze over the model.
No animations, need to fix the first three issues before I add animations.

# Credits

- **Original MaxScript**: Pionomes

---

**Note**: This addon requires Blender 4.0 or higher. For older versions, modifications may be needed.