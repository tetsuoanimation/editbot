import json, os, subprocess

ffmpeg_bin=r"C:\Program Files\ffmpeg\bin\ffmpeg", 
ffprobe_bin=r"C:\Program Files\ffmpeg\bin\ffprobe"

def list_video_files_in_folder(foldername, ext=".mp4"):
    video_files = []
    folder_list = os.listdir(foldername)
    for vf in [os.path.join(foldername, filename) for filename in folder_list]:
        if os.path.isfile(vf) and vf.endswith(ext):
            video_files.append(vf)
    
    return video_files

def get_video_duration(clip_path):
    out = subprocess.check_output([ffprobe_bin,str(clip_path),"-v","0","-select_streams","v","-print_format","flat","-show_entries","stream=duration"], text=True)
    duration = out.split('=')[1].strip()[1:-1].split('/')
    if len(duration)==1:
        return float(duration[0])
    if len(duration)==2:
        return float(duration[0])/float(duration[1])

def get_video_fps(clip_path):
    out = subprocess.check_output([ffprobe_bin,str(clip_path),"-v","0","-select_streams","v","-print_format","flat","-show_entries","stream=r_frame_rate"], text=True)
    rate = out.split('=')[1].strip()[1:-1].split('/')
    if len(rate)==1:
        return float(rate[0])
    if len(rate)==2:
        return float(rate[0])/float(rate[1])
    return -1

def create_config_from_folder(edit_desc_path, edit_desc_name, foldername):

    videos = list_video_files_in_folder(foldername)
    video_dict = []

    for vf in videos:
        name = os.path.splitext(os.path.basename(vf))[0]
        duration = get_video_duration(vf)
        framerate = get_video_fps(vf)

        clip_dict = {
            "name": name,
            "durationSeconds": duration,
            "fps": framerate,
            "startFrame": 0
        }

        video_dict.append(clip_dict)

    json_str=(json.dumps(video_dict, indent=4))

    # Writing to sample.json
    with open(os.path.join(edit_desc_path, edit_desc_name), "w") as outfile:
        outfile.write(json_str)
    return ({
        "resultpath": os.path.join(edit_desc_path, edit_desc_name),
        "json": json.loads(json_str)
        })

if __name__ == "__main__":

    edit_desc_path = r"C:"
    edit_desc_name = r"editbot_testconfig.json"
    foldername = r"C:\Users\chris\Desktop\testfootage\02_Animation"
    
    result = create_config_from_folder(edit_desc_path, edit_desc_name, foldername)
    print (json.dumps(result, indent=4))
