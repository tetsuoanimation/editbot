from editbot_main import *
import os, copy

ffmpeg_bin=r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
ffprobe_bin=r"C:\Program Files\ffmpeg\bin\ffprobe.exe"

def build_edit(
    name, 
    folder,
    pass_name, 
    edit_desc_path, 
    edit_desc_name, 
    edit_output_path, 
    edit_output_name,
    logo_path,
    fps,
    subfolders = False
    ):

    base_config = Config(
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        name=name,
        default_pass_name=pass_name,
        enable_shotmask=True,
        shot_mask_logo_path=logo_path,
        clip_frame_handles=0,
        fps=fps
    )

    # build location
    storageLocation = Location(name='root', folder=folder)
    storageLocation.addSublocation(Location(name=pass_name, folder=folder, priority=7, subfolders_only=subfolders))

    anim_config = copy.deepcopy(base_config)
    anim_config.force_pass = True,
    # anim_config.default_pass_name = 'Style_Test'
    animEdit = Edit(
        config=anim_config,
        shot_desc_path=str(os.path.join(edit_desc_path, edit_desc_name)),
        source_folder=storageLocation,
        # frameoffset = 30*5, # 5 seconds slate
        )
    
    edits = [animEdit]

    for edit in edits:
        edit.conformEdit(mode='duration')
        edit.addAutoSlate(duration=5)
        edit.preconvertClips()

        print("Building edit:")
        [print(f"    {editclip.name}") for editclip in edit.edit]

        result_path = edit.build(os.path.join(edit_output_path, edit_output_name))
        print(f"Edit saved to: {result_path}")
        edit.cleanup()

if __name__ == "__main__":

    edit_desc_path = r"C:"
    edit_desc_name = r"editbot_testconfig.json"
    folder = r"C:\Users\chris\Desktop\testfootage\02_Animation"

    edit_output_path=r"C:", 
    edit_output_name="editbot_testconfig_edit.mp4",

    build_edit_from_json.build_edit( 
        edit_desc_path=edit_desc_path, 
        edit_desc_name=edit_desc_name, 
        edit_output_path=edit_output_path, 
        edit_output_name=edit_output_name,
        name = 'Folder Edit',
        pass_name = 'Folder Preview',
        folder = foldername,
        logo_path=os.path.join(os.path.dirname(__file__),"res","tetsuoanimation_logo_v004_cu.png"),
        fps=30
        )