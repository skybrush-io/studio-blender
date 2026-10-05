"""Entry point for an isolated Blender export worker; never run as a UI operator."""

import json
import sys
from pathlib import Path

import bpy


def main():
    config_path = Path(sys.argv[sys.argv.index("--") + 1])
    config = json.loads(config_path.read_text())
    result_path = config_path.parent / "result.json"
    try:
        sys.path.insert(0, config["addon_directory"])
        import addon_utils

        # Create the preferences entry in this isolated process. Merely
        # registering the add-on leaves get_preferences() without an entry.
        if addon_utils.enable(config["addon_module"], default_set=True) is None:
            raise RuntimeError("Unable to enable Dronetara Studio in export worker")
        from sbstudio.model.file_formats import FileFormat
        from sbstudio.plugin.local_api import LocalSkybrushStudioAPI
        from sbstudio.plugin.model.global_settings import get_preferences
        from sbstudio.plugin.operators.utils import export_show_to_file_using_api

        prefs = get_preferences()
        prefs.operation_mode = "OFFLINE"
        prefs.gateway_url = ""
        bpy.ops.wm.open_mainfile(filepath=config["snapshot"], use_scripts=False)
        if bpy.app.autoexec_fail:
            raise RuntimeError(
                "Scene needs disabled Python scripts; use foreground export after reviewing it"
            )
        window = bpy.context.window
        if window is None:
            raise RuntimeError("Blender worker has no scene context")
        window.scene = bpy.data.scenes[config["scene"]]
        window.view_layer = bpy.context.scene.view_layers[config["view_layer"]]
        api = LocalSkybrushStudioAPI()
        export_show_to_file_using_api(
            api,
            bpy.context,
            config["settings"],
            config["artifact"],
            FileFormat(config["format"]),
        )
        report = api.last_validation_report
        warnings = (
            report["failed_checks"] + report.get("diagnostic_warnings", [])
            if report
            else []
        )
        result_path.write_text(
            json.dumps(
                {
                    "success": True,
                    "warnings": warnings,
                    "export_gate": report.get("export_gate") if report else None,
                }
            )
        )
    except Exception as exc:
        result_path.write_text(json.dumps({"success": False, "error": str(exc)}))
        raise


if __name__ == "__main__":
    main()
