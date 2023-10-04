# editbot
Tools for creating playblasts, edits and previews for trailers, films and animation.

This script uses an installation of FFmpeg. Please make sure it is installed to `C:\Program Files\ffmpeg` or replace the ffmpeg_bin and ffprobe_bin variables in the scripts with where your version is installed.

## Overall Usage

### Build config
The easiest way to build an edit is using a editconfig that describes it. 
You can supply your own desc files, check `minimal_edit.json` for the structure.

For easy usage, we include a script that automatically builds the config from a folder: `editbot_build_config_from_folder.py`.

```
config = editbot_build_config_from_folder.create_config_from_folder(
                                                        "path/to/desc/temp/folder", 
                                                        "edit_desc_name.json", 
                                                        "path/to/folder/with/videoclips"
                                                        )
```

### Build edit
Once you have the config file, you can run the `build_edit_from_json` scripts function:
```
result = build_edit_from_json.build_edit( 
                                edit_desc_path="path/to/desc/temp/folder",
                                folder = "path/to/folder/with/videoclips",
                                subfolders = False                          # footage is located in subfolders
                                edit_desc_name="edit_desc_name.json", 
                                edit_output_path="edit/video/output/path", 
                                edit_output_name="edit_video_output_name,
                                name = 'Folder Edit',                       # shown on slate
                                pass_name = 'Folder Preview',               # shown on slate and in shotmask header
                                logo_path=os.path.join("path/to/company/logo.png),
                                fps=30
                                )
```

## Helpers and tools
### Build folder edit
Build config and edit from a folder in one go: `build_folder_edit.py` 

### Add shotmask to clips
Add the basic shotmask to all clips in a folder: `add_shotmask.py`
This script includes a basic commandline interface. Use `-h` to see all options.
To run it run this commandline: `python add_shotmask.py -i . -o ./output -p Animation -fps 30`



