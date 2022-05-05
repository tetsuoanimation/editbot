from editbot_main import *
import copy

if __name__ == '__main__':

    base_config = Config(
        name="Fallguys Season Symphony",
        default_pass_name="Animation",
        ffmpeg_bin=r"C:\Program Files\ffmpeg\bin\ffmpeg", 
        ffprobe_bin=r"C:\Program Files\ffmpeg\bin\ffprobe", 
        enable_shotmask=True,
        shot_mask_logo_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\editbot\res\ttf_logo_white_noTagline.png" , 
        clip_frame_handles=1,
        fps=30
    )

    # build location
    storageLocation = Location(name='root', folder=r"d:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview")
    # storageLocation = Location(name='root', folder=r'C:\Users\chris\Desktop\testfootage')
    storageLocation.addSublocation(Location(name='Assembly', folder='04_Assembly', priority=5, subfolders_only=True))
    storageLocation.addSublocation(Location(name='Animation', folder='02_Animation\\02_Shots', priority=3, subfolders_only=True))

    anim_config = copy.deepcopy(base_config)
    animEdit = Edit(
        config=anim_config,
        shot_desc_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\watchtower_ftrack\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
        source_folder=r"D:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\02_Animation\02_Shots"
        )

    assembly_config = copy.deepcopy(base_config)
    assembly_config.default_pass_name="Assembly"
    assemblyEdit = Edit(        
        config=assembly_config,
        shot_desc_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\watchtower_ftrack\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
        source_folder=r"D:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\04_Assembly"
        )

    latest_config = copy.deepcopy(base_config)
    latest_config.default_pass_name="Latest"
    latestEdit = Edit(
        config=latest_config,
        shot_desc_path=r"D:\AutomatedProjects\TechArt\TFPipeline\Code\watchtower_ftrack\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
        source_folder=storageLocation
        )

    edits = [animEdit, assemblyEdit, latestEdit]

    for edit in edits:
        edit.conformEdit(mode='in_frame')
        edit.addAutoSlate()
        edit.preconvertClips()

        print(edit.build(r'd:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\05_Edit\FG_Symphony_{pipepass}_Edit.mp4'.format(pipepass=edit.config.default_pass_name)))
        #print(edit.fastbuild(r'd:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview\05_Edit\FG_Symphony_Animation_Edit.mp4'))
        edit.cleanup()
