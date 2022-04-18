from editbot_main import *

if __name__ == '__main__':

    config = Config(
        name="Fallguys Season Symphony",
        default_pass_name="Animation",
        ffmpeg_bin=r"C:\Program Files\ffmpeg\bin\ffmpeg", 
        ffprobe_bin=r"C:\Program Files\ffmpeg\bin\ffprobe", 
        enable_shotmask=True,
        shot_mask_logo_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\editbot\res\ttf_logo_white_noTagline.png" , 
        clip_frame_handles=1,
        fps=30
    )

    edit = Edit(
        config=config,
        shot_desc_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\watchtower_ftrack\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
        source_folder=r"D:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\02_Animation\02_Shots"
        )

    edit.conformEdit(mode='in_frame')
    edit.addAutoSlate()
    edit.preconvertClips()

    print(edit.build(r'd:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\05_Edit\FG_Symphony_Animation_Edit.mp4'))
    #print(edit.fastbuild(r'd:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\05_Edit\FG_Symphony_Animation_Edit.mp4'))
    edit.cleanup()
