# Disclaimer

This is a pseudocode for installing the add-ons to Blender.
It is not user-friendly yet, its main goal is to describe the process for ourselves...

# Find Blender directory

First task is to find installed Blender version and its main scripts directory.

See: https://docs.blender.org/manual/en/latest/advanced/blender_directory_layout.html

Assuming latest LTS 2.83, `BLENDER_BASE_DIRECTORY=`...

- Linux: `$HOME/.config/blender/2.83/`
- macOS: `/Users/$USER/Library/Application Support/Blender/2.83/`
- Windows: `%USERPROFILE%\AppData\Roaming\Blender Foundation\Blender\2.83\`

# Create subdirectories (if they do not exist)

```
mkdir $BLENDER_BASE_DIRECTORY/scripts
mkdir $BLENDER_BASE_DIRECTORY/scripts/vendor/skybrush
mkdir $BLENDER_BASE_DIRECTORY/scripts/addons
```

# Install all python dependencies to scripts/modules

```
poetry export -f requirements.txt -o requirements.txt
pip install -v -t $BLENDER_BASE_DIRECTORY/scripts/vendor/skybrush -r requirements.txt
```

or alternatively

```
poetry install
cp .venv/Lib/site-packages/all-modules-that-are-needed $BLENDER_BASE_DIRECTORY/scripts/vendor/skybrush
```

# Copy all .py content of ./modules to scripts/modules

```
cp -r modules/sbstudio $BLENDER_BASE_DIRECTORY/scripts/vendor/skybrush
```

# Copy add-ons to scripts/addons

cp addons/\*.py $BLENDER_BASE_DIRECTORY/scripts/addons

# Activate add-ons

Add-ons have to activated from within Blender at _Preferences_ -> _Add-ons_ -> select "User" filter -> checkbox
