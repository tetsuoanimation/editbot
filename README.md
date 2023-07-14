# editbot
Tools for creating playblasts, edits and previews for trailers, films and animation

The easiest way to build an edit is using a config. You can automatically build a config from a folder using the `editbot_build_config_from_folder.py` script:

```
config = editbot_build_config_from_folder.create_config_from_folder(
                                                        "path/to/desc/temp/folder", 
                                                        "edit_desc_name.json", 
                                                        "path/to/folder/with/videoclips"
                                                        )
```

Once you have the config file, you can run the `build_edit_from_json` scripts function:
```
result = build_edit_from_json.build_edit( 
    edit_desc_path="path/to/desc/temp/folder",
    folder = "path/to/folder/with/videoclips",
    edit_desc_name="edit_desc_name.json", 
    edit_output_path="edit/video/output/path", 
    edit_output_name="edit_video_output_name,
    name = 'Folder Edit', # shown on slate
    pass_name = 'Folder Preview', # shown on slate and in shotmask header
    logo_path=os.path.join("path/to/company/logo.png),
    fps=30
    )
```

You can also supply your own desc files, check `minimal_edit.json` for the structure.

This script uses an installation of FFmpeg. Please make sure it is installed to `C:\Program Files\ffmpeg` or replace the ffmpeg_bin and ffprobe_bin variables in the scripts with where your version is installed.
