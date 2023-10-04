from editbot_main import *
import os, copy, argparse

ffmpeg_bin=r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
ffprobe_bin=r"C:\Program Files\ffmpeg\bin\ffprobe.exe"

def build_edit(
    name, 
    folder,
    pass_name,
    video_filename,
    edit_output_path, 
    edit_output_name,
    logo_path,
    fps,
    studio_name = None,
    director_name =None,
    subfolders = False,
    ):

    base_config = Config(
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        studio_name = studio_name,
        director_name =director_name,
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
        source_folder=storageLocation,
        # frameoffset = 30*5, # 5 seconds slate
        )

    #custom edit
    footage_clip = Clip(
        config=anim_config,
        name = os.path.splitext(os.path.basename(video_filename))[0],
        # frame_handles_in=5,
        in_frame = 0,
        duration= 0,
        # pass_name='Layout'
    )
    footage_clip.findFootage(storageLocation)
    footage_clip.getFrameRate()
    footage_clip.getDuration()

    animEdit.addClip(footage_clip)
    
    edits = [animEdit]

    for edit in edits:
        edit.conformEdit(mode='in_frame')
        edit.preconvertClips()

        print("Building edit:")
        [print(f"    {editclip.name}") for editclip in edit.edit]

        result_path = edit.build(os.path.join(edit_output_path, edit_output_name))
        print(f"Edit saved to: {result_path}")
        edit.cleanup()

def list_video_files_in_folder(foldername, ext=".mp4"):
    video_files = []
    folder_list = os.listdir(foldername)
    for vf in [os.path.join(foldername, filename) for filename in folder_list]:
        if os.path.isfile(vf) and vf.endswith(ext):
            video_files.append(vf)
    
    return video_files

if __name__ == "__main__":

    # folder = r"E:\01_Work\00_Sandbox\convert_with_mask"
    # edit_output_path=r"E:\01_Work\00_Sandbox\convert_with_mask\converted"
    # out_fps = 30
    # studio_name = 'Tetsuo Animation Studio'
    # director_name = 'Chris Unterberg'
    # name = 'Animation'
    # pass_name = 'Animation'

    parser = argparse.ArgumentParser(
                    prog='Automatic Shotmask Renderer',
                    description='Renders a shotmask with shot name and framecounter and some other information onto all videofiles in a folder')
    parser.add_argument("--inputfolder", "-i", type=str, required=True)
    parser.add_argument("--outputfolder", "-o", type=str, required=True)
    parser.add_argument("--pass_name", "-p", type=str, default="")
    parser.add_argument("--frames_per_second", "-fps", type=int, default=24)
    parser.add_argument("--studio_name", "-n:s", type=str, default="")
    parser.add_argument("--director_name", "-n:d", default="")
    parser.add_argument("--name", "-n", type=str, default="")

    args = parser.parse_args()
    folder = args.inputfolder
    edit_output_path= args.outputfolder
    out_fps = args.frames_per_second
    studio_name = args.studio_name
    director_name = args.director_name
    name = args.name
    pass_name = args.pass_name

    if not os.path.exists(edit_output_path):
        print(f"Outputfolder did not exist, creating {os.path.abspath(edit_output_path)}")
        os.mkdir(os.path.abspath(edit_output_path))

    for videofile in list_video_files_in_folder(folder):
        edit_output_name=f"{os.path.splitext(os.path.basename(videofile))[0]}_shotmask.mp4"
        print(videofile)
        print(edit_output_name)
        print(edit_output_path)
        build_edit( 
            video_filename = videofile,
            edit_output_path=edit_output_path, 
            edit_output_name=edit_output_name,
            studio_name=studio_name,
            director_name=director_name,
            name = name,
            pass_name = pass_name,
            folder = folder,
            logo_path=os.path.join(os.path.dirname(__file__),"res","ta_logo_new.png"),
            fps=out_fps
            )