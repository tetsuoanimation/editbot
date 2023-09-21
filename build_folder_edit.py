import editbot_build_config_from_folder
import build_edit_from_json
import os

edit_desc_path = r"E:\01_Work\03_Kunden\tetsuoanimation\00_mainDepot\FallGuys\20230814_Fallguys_EOY\10_Output\00_Preview\01_Layout"
edit_desc_name = r"SQ02_editconfig.json"
foldername = r"E:\01_Work\03_Kunden\tetsuoanimation\00_mainDepot\FallGuys\20230814_Fallguys_EOY\10_Output\00_Preview\01_Layout"

result = editbot_build_config_from_folder.create_config_from_folder(edit_desc_path, edit_desc_name, foldername)

edit_output_path=r"E:\01_Work\03_Kunden\tetsuoanimation\00_mainDepot\FallGuys\20230814_Fallguys_EOY\10_Output\00_Preview\01_Layout"
edit_output_name="FG_EOY_SQ02_v001.mp4"

build_edit_from_json.build_edit( 
    studio_name = "Tetsuo Animation Studio",
    director_name = "Chris Unterberg",
    edit_desc_path=edit_desc_path, 
    edit_desc_name=edit_desc_name, 
    edit_output_path=edit_output_path, 
    edit_output_name=edit_output_name,
    name = 'Fallguys EOY SQ02',
    pass_name = 'Layout',
    folder = foldername,
    logo_path=os.path.join(os.path.dirname(__file__),"res","ta_logo_new.png"),
    fps=30
    )