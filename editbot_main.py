import os, json, datetime, subprocess, re, mimetypes, tempfile, shutil
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

@dataclass
class Config:
    ffmpeg_bin: str
    ffprobe_bin: str
    shot_mask_logo_path: str
    clip_frame_handles: int
    enable_shotmask: bool=True
    clip_size: tuple=(1920,1080)
    fps: int=24

@dataclass
class ShotMask:
    mode: str
    scale: tuple=(1920,1080)
    mask_size: int=60
    mask_padding: int=25
    mask_opacity: float=0.5
    logo_path: str=''
    pass_name: str='defaultpass'
    shot_name: str='defaultshot'
    file_name: str='defaultfilename.mp4' 
    in_frame: int=0
    fps: int=60
    timecode: str='00\:00\:00\:00'
    date: str='yyyy-mm-dd'
    fontsize_large: int=25
    fontsize_small: int=16

    # generates the filter string for ffmpeg - has two modes, 'clip' for the clip data and 'sequence' for the sequence data
    def generateFilterString(self, mode: str='') -> str:
        if not mode:
            mode=self.mode
        logofilter="[1:v]scale=h={mask_size}-{logopadding}:force_original_aspect_ratio=1".format(mask_size=self.mask_size, logopadding=self.mask_size/6) if self.logo_path else ""
        logooverlay="overlay=x={mask_padding}:y={logopadding}/2".format(mask_padding=self.mask_padding, logopadding=self.mask_size/6) if self.logo_path else ""
        
        # TODO: split this part into the main converter as it is not related to the shotmask
        sizefilter=(
            "scale=w={width}:h={height}:force_original_aspect_ratio=1[0];"
            "[0]pad=width={width}:height={height}:x=-1:y=-1:color=black[0];"
            "color=pink:{width}x{height}:r={fps}[c];"
            "[c][0]overlay=eof_action=pass"
        ).format(width=self.scale[0], height=self.scale[1], logofilter=logofilter, fps=self.fps)
        
        drawmaskfilter=(
            "drawbox=x=0:y=0:w=-1:h={mask_size}:color=black@{mask_opacity}:t=fill[0];"
            "[0]drawbox=x=0:y=ih-h:w=-1:h={mask_size}:color=black@{mask_opacity}:t=fill"
        ).format(mask_size=self.mask_size, mask_opacity=self.mask_opacity, logooverlay=logooverlay)

        if mode == "clip":
            drawtextfilter=(
                "drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':text='{pass_name}':x=(w-text_w)/2:y=({mask_size}/2)-(text_h/2)[0];"
                "[0]drawtext=fontsize={fontsize_large}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':text='{shot_name}':x=w-text_w-{mask_padding}:y=({mask_size}/2)-(text_h/2)[0];"
                "[0]drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':text='{shot_date}':x={mask_padding}:y=h-(text_h/2)-({mask_size}/3)[0];"
                "[0]drawtext=fontsize={fontsize_large}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':text='%{{frame_num}}':start_number={start_frame}:x=w-text_w-{mask_padding}:y=h-(text_h/2)-({mask_size}/2)[0];"
                "[0]drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':text={shot_file_name}':x={mask_padding}:y=h-(text_h/2)-(({mask_size}/3)*2)"
            ).format(fontsize_small=self.fontsize_small, fontsize_large=self.fontsize_large, mask_size=self.mask_size, mask_padding=self.mask_padding, start_frame=self.in_frame, pass_name=self.pass_name, shot_name=self.shot_name, shot_date=self.date, shot_file_name=os.path.basename(self.file_name))
        elif mode == "sequence":
            drawtextfilter=(
                "drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='/Windows/Fonts/arial.ttf':timecode='00\:00\:00\:00':rate={fps}:x=(w-text_w)/2:y=h-(text_h/2)-({mask_size}/2)"
            ).format(fontsize_small=self.fontsize_small, fontsize_large=self.fontsize_large, fps=self.fps, mask_size=self.mask_size, mask_padding=self.mask_padding)
        else:
             drawtextfiler=""
        
        if mode == "clip":
            return '"{logofilter}[1];{sizefilter}[0];[0][1]{logooverlay}[0];[0]{drawmaskfilter}[0];[0]{drawtextfilter}"'.format(
                logofilter=logofilter,
                logooverlay=logooverlay,
                sizefilter=sizefilter, 
                drawmaskfilter=drawmaskfilter,
                drawtextfilter=drawtextfilter
                )
        elif mode == "sequence":
            return '"{drawtextfilter}"'.format(drawtextfilter=drawtextfilter)
        elif mode == "resizeonly":
            return '"{sizefilter}"'.format(sizefilter=sizefilter)
        else:
            return False

@dataclass
class Clip:
    config: Config
    in_frame: int
    duration: float=0
    frame_handles_in: int=None
    clip_size: tuple=(1920,1080)
    pass_name: str='default clip pass'
    name: str='S000'
    _clip_path: str = field(init=False)
    shotmask: ShotMask = field(init=False)
    fps: int= field(init=False)
    is_converted: bool= field(init=False)
    converted_clip_path: str= field(init=False)
    ready: bool= field(init=False)

    def __post_init__(self):
        self._clip_path: Path=Path()
        self.ready=False
        self.converted_clip_path: Path=Path()
        self.is_converted=False
        self.fps=self.getFrameRate() if os.path.isfile(self.clip_path) else self.config.fps
        self.frame_handles_in=self.config.clip_frame_handles if not self.frame_handles_in else self.frame_handles_in
        self.shotmask = ShotMask(
            mode='clip',
            logo_path=self.config.shot_mask_logo_path,
            scale=self.clip_size,
            fps=self.fps,
            pass_name=self.pass_name, 
            shot_name=self.name,
            file_name=self.clip_path, 
            in_frame=self.frame_handles_in,
            mask_opacity=0.2,
            date=datetime.date.today().isoformat()
        )
        if not self.config.enable_shotmask:
            self.shotmask.mode='resizeonly'
        self.clip_size=self.config.clip_size
        self.check_ready()
    
    # convert to @property
    @property
    def clip_path(self):
        return self._clip_path
    
    @clip_path.setter
    def clip_path(self, footage_path):
        if os.path.isfile(footage_path):
            self._clip_path=footage_path
            self.fps=self.getFrameRate()
            self.shotmask.fps=self.fps
            self.shotmask.file_name=os.path.basename(footage_path)
            #this will set the time to the last clip mod time
            self.shotmask.date=datetime.datetime.fromtimestamp(Path(footage_path).stat().st_mtime).strftime('%Y-%m-%d')
            if self.duration==0:
                self.duration=self.getDuration()
            self.check_ready()
        else:
            print('Cannot set file {}, file does not exist.'.format(footage_path))
    
    def check_ready(self):
        if (self.clip_path.is_file()) and self.fps>0 and self.duration>0.0:
            self.ready=True
        else:
            self.ready=False

    def check_converted(self):
        if (self.converted_clip_path.is_file()):
            self.is_converted=True
        else:
            self.is_converted=False

    def findFootage(self, footage_source_path: str, latest: bool=True, durationFromClip=False):
        if latest:
            print('Searching Latest Clip footage for {} in {}'.format(self.name, footage_source_path))
            searchpath = Path(footage_source_path)
            videofiles_in_folder = [vf for vf in searchpath.iterdir() if vf.is_file() and mimetypes.guess_type(vf)[0].startswith('video/')]
            footageClips=[]
            for file in videofiles_in_folder:
                #print(os.path.basename(str(file)))  
                if re.search("({})".format(self.name), os.path.basename(str(file)), flags=re.IGNORECASE):
                    footageClips.append(file)
            if len(footageClips)==0:
                print('Cannot find footage for {}'.format(self.name))
                self.check_ready()
                return None
            
            latest_clip = max(footageClips, key=lambda x: x.stat().st_mtime)

            self.clip_path = latest_clip
            if durationFromClip:
                self.duration=self.getDuration()
            self.check_ready()
            return latest_clip
        else:
            print('Only latest clip is currently implemented')
            return None

    def convertClip(self, output_path:str, ffmpeg_bin:str='', out_fps: Any=None) ->bool: 
        if not ffmpeg_bin:
            ffmpeg_bin=self.config.ffmpeg_bin
        if not out_fps:
            out_fps=self.config.fps
        if type(out_fps)==str:
            if out_fps.lower()=='nochange':
                out_fps=self.fps
        if not self.ready:
            print('Clip {} not ready, skipping conversion!'.format(self.shot_name))
            return False
        if self.shotmask.logo_path:
            ffmpeg_cmd = (
                "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
                "-ss {in_time} "
                "-i {clip_path} "
                "-i {logo_path} "
                "-filter_complex {filter_string} "
                "-t {duration} "
                "-r {out_fps} "
                "{output_name}"
            ).format(
                fps=self.fps,
                in_time=str((self.frame_handles_in)/self.fps),
                ffmpeg_bin=ffmpeg_bin, 
                clip_path=self.clip_path, 
                logo_path=self.shotmask.logo_path, 
                filter_string=self.shotmask.generateFilterString(), 
                duration=str(datetime.timedelta(seconds=self.duration)),
                out_fps=out_fps, 
                output_name=output_path
                )
        else:
            ffmpeg_cmd = (
                "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
                "-ss {in_time} "
                "-i {clip_path} "
                "-filter_complex {filter_string} "
                "-t {duration} "
                "-r {out_fps} "
                "{output_name}"
            ).format(
                in_time=str(datetime.timedelta(seconds=self.frame_handles_in/self.fps)),
                ffmpeg_bin=ffmpeg_bin, 
                clip_path=self.clip_path, 
                filter_string=self.shotmask.generateFilterString(), 
                duration=str(datetime.timedelta(seconds=self.duration)),
                out_fps=out_fps,
                output_name=output_path)
        
        subprocess.call(ffmpeg_cmd)
        
        self.converted_clip_path=Path(output_path)
        self.check_converted()
        return True
    
    def getFrameRate(self, ffprobe_bin:str=''):
        if not ffprobe_bin:
            ffprobe_bin=self.config.ffprobe_bin
        if not os.path.exists(self.clip_path):
            sys.stderr.write("ERROR: filename %r was not found!" % (self.clip_path,))
            return -1         
        out = subprocess.check_output([ffprobe_bin,self.clip_path,"-v","0","-select_streams","v","-print_format","flat","-show_entries","stream=r_frame_rate"], text=True)
        rate = out.split('=')[1].strip()[1:-1].split('/')
        if len(rate)==1:
            return float(rate[0])
        if len(rate)==2:
            return float(rate[0])/float(rate[1])
        return -1

    def getDuration(self, ffprobe_bin:str=''):
        if not ffprobe_bin:
            ffprobe_bin=self.config.ffprobe_bin
        if not os.path.exists(self.clip_path):
            sys.stderr.write("ERROR: filename %r was not found!" % (self.clip_path,))
            return -1   
        out = subprocess.check_output([ffprobe_bin,self.clip_path,"-v", "error","-select_streams","v","-print_format","flat","-show_entries","stream=duration"],text=True)
        duration = float(out.split('=')[1].strip()[1:-1])
        handle_duration= (self.frame_handles_in*2)/self.fps
        duration -= handle_duration
        return duration

@dataclass
class Edit:
    config: Config
    shot_desc_path: str=''
    source_folder: str=''
    frameoffset: int= 0
    fps: int=None
    edit: list[Clip]= field(init=False)
    temp_folder: str= field(init=False)
    ready: bool= field(init=False)

    def check_ready(self):
        if len(self.edit)>0 and all([clip.ready for clip in self.edit]) and all([clip.is_converted for clip in self.edit]): 
            self.ready=True
        else:
            self.ready=False

    def __post_init__(self):
        if self.shot_desc_path:
            self.edit=self.loadEdit(self.shot_desc_path)
            self.findFootage(self.source_folder, latest=True)
        else:
            self.edit=[]
        if self.fps==None:
            self.fps=self.config.fps
        self.temp_folder=None,
        self.check_ready()

    def addClip(self, clip: Clip, sequential: bool=True):
        if sequential:
            clip_offset = sum([c.duration*c.fps for c in self.edit])
            clip.in_frame = clip_offset
        self.edit.append(clip)
        frame_offset = min([c.in_frame for c in self.edit])
        self.edit.sort(key=lambda d: d.in_frame)
        self.check_ready()

    def loadEdit(self, shot_desc_path: str, resetEdit=True) ->list[Clip]:
        if resetEdit:
            self.edit=[]
        with open(shot_desc_path, 'r') as shot_desc:
            data = json.load(shot_desc)
            data.sort(key=lambda d: d['startFrame'])
            for shot in data:
                self.addClip(
                    sequential=False, 
                    clip=Clip(
                        config=self.config,
                        in_frame=shot['startFrame'],
                        duration=shot['durationSeconds'],
                        name=shot['name']
                        )
                    )
                    
        self.frameoffset=min([clip.in_frame for clip in self.edit])
        return self.edit
    
    def findFootage(self, source_folder: str, latest=True, keepClipLengths=False):
        for clip in self.edit:
            clip.findFootage(source_folder, latest=latest, durationFromClip=keepClipLengths)
        self.check_ready()

    def preconvertClips(self, tempfolder: str='') ->str:
        if any(not c.ready for c in self.edit):
            print('Edit is not ready to batch convert, are all clips ready?')
            return None
        if not tempfolder:
            tempfolder = tempfile.mkdtemp(prefix='py_autoedit_')
        else:
            if not os.path.exists(tempfolder):
                os.makedirs(tempfolder)
        for clip in self.edit:
            clip.convertClip(os.path.join(tempfolder, '{}.mp4'.format(clip.name)))
        self.temp_folder = tempfolder
        return tempfolder
    
    def conformEdit(self, mode='in_frame'):
        '''conforms the clip durations and inframes to be continous. Has two modes: 'in_frame' conforms
        everything to keep the values in in_frames in the clips while 'duration' adjusts the in_frame and out_frame of
        all clips so the durations stay the same. Order will always be determined by in_frame'''

        self.edit.sort(key=lambda d: d.in_frame)
        self.frame_offset = min([c.in_frame for c in self.edit])

        if mode=='in_frame':
            for i, clip in enumerate(self.edit):
                if i<len(self.edit)-1:
                    nextclip=self.edit[i+1]
                    clip_framelen=nextclip.in_frame-clip.in_frame
                    clip.duration=clip_framelen/clip.fps
        elif mode=='duration':
            for i, clip in enumerate(self.edit):
                if i>0:
                    prevclip=self.edit[i-1]
                    clip.in_frame=prevclip.in_frame+prevclip.duration*self.fps
        else:
            print('Unknown conform mode, choose "in_frame" or "duration" to conform the edit')

    def cleanup(self, check_folder_name:bool=True):
        if Path(self.temp_folder).exists(): 
            if (check_folder_name and 'py_autoedit_' in self.temp_folder) or not check_folder_name:
                print('Removing Temp Folder at {}'.format(self.temp_folder))
                shutil.rmtree(self.temp_folder)
        # we could also remove the parent of the clips here
        for clip in self.edit:
            clip.check_converted()
            # clip.check_ready()
        self.check_ready()

    def makeEditConcatFile(self):
        if not self.temp_folder:
            tempfolder = tempfile.mkdtemp(prefix='py_autoedit_')
            self.temp_folder=tempfolder
        with open(os.path.join(self.temp_folder, 'edit.txt'), 'w') as editfile:
            editdata=''
            for clip in self.edit:
                if clip.is_converted:
                    editdata+=("file '{}'\n".format(clip.converted_clip_path))
                else:
                    print("Skipping unconverted clip for {}. Make sure to preconvert all clips before building".format(clip.name))
            editfile.write(editdata)
        return Path(os.path.join(self.temp_folder, 'edit.txt'))

    def fastbuild(self, outputpath:str, ffmpeg_bin:str=''):
        '''run ffmpeg demuxer for this filestack without reencoding. 
        This is very fast but it won't add sequencedata or a shotmask.
        outputpath must be a full filename and needs to be handled by the user'''
        
        editfile=self.makeEditConcatFile()
        if not ffmpeg_bin:
            ffmpeg_bin=self.config.ffmpeg_bin
        ffmpeg_cmd = (
            "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
            "-f concat -safe 0 "
            "-i {input} "
            "-c copy "
            "{output_name}"
        ).format(
            ffmpeg_bin=ffmpeg_bin, 
            input=editfile, 
            output_name=outputpath
            )
        
        subprocess.call(ffmpeg_cmd)
        return Path(outputpath)

    def build(self, outputpath:str, ffmpeg_bin:str=''):
        '''Builds the full edit. This will add a timecode and re-encode everything.
        This is quite slow. For a faster build, use the fastbuild() function'''

        if not ffmpeg_bin:
            ffmpeg_bin=self.config.ffmpeg_bin
        
        sequencemask=ShotMask(
            mode='sequence',
            fps=self.fps,
            date=datetime.date.today().isoformat()
        )

        inputlist=''
        concatfilterlist=''

        for i, clip in enumerate(self.edit):
            if clip.is_converted:
                inputlist+= '-i "{}" '.format(clip.converted_clip_path)
                concatfilterlist+='[{index}:0] '.format(index=i)
            else:
                print('Skipping unconverted clip for {}. Make sure to preconvert all clips before building'.format(clip.name))

        concatfilter='{concatfilterlist}concat=n={clipnum}:v=1:a=0'.format(concatfilterlist=concatfilterlist, clipnum=len([c for c in self.edit if c.is_converted]))
        ffmpeg_cmd = (
            "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
            "{input} "
            "-filter_complex \"{concatfilter}[0];[0]{sequencemaskfilter}\" "
            "{output_name}"
        ).format(
            ffmpeg_bin=ffmpeg_bin, 
            input=inputlist, 
            concatfilter=concatfilter,
            sequencemaskfilter=sequencemask.generateFilterString(),
            output_name=outputpath
            )
        
        subprocess.call(ffmpeg_cmd)
        return Path(outputpath)

if __name__ == "__main__":

    config = Config(
        ffmpeg_bin=r'C:\ffmpeg\bin\ffmpeg', 
        ffprobe_bin=r'C:\ffmpeg\bin\ffprobe', 
        enable_shotmask=True,
        shot_mask_logo_path=r'C:\01_Work\02_PersonalProjects\editbot\res\tetsuo_favicon.png' , 
        clip_frame_handles=1,
        fps=30
    )

    # # test edit from desc
    # edit = Edit(
    #     config=config,
    #     shot_desc_path=r"C:\01_Work\02_PersonalProjects\watchtower\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
    #     source_folder=r"C:\Users\Chris\Desktop\testfootage"
    #     )

    # # not needed, if a path is supplied, the constructor will load it automatically
    # # edit.loadEdit(r"C:\01_Work\02_PersonalProjects\watchtower\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json")

    # print(edit)

    #custom edit
    clip1 = Clip(
        config=config,
        name = 'S010-020',
        # frame_handles_in=5,
        in_frame = 60,
        duration= 1.5,
        pass_name='Layout'
    )

    clip2 = Clip(
        config=config,
        name = 'S030-040',
        #frame_handles_in=5,
        in_frame = 20,
        duration= 5,
        pass_name='First Pass Animation'
    )

    edit_custom = Edit(config=config)
    # sequential = True means the edit won't care about the in_frame and just append the clip to the edit
    # edit_custom.addClip(clip1, sequential=True)
    # edit_custom.addClip(clip2, sequential=True)
    # sequential = False will make sure the cutpoints in in_frame are used
    edit_custom.addClip(clip1, sequential=False)
    edit_custom.addClip(clip2, sequential=False)
    # this uses the definition in the clip object if it has not been overwritten
    edit_custom.findFootage(r'C:\Users\chris\Desktop\testfootage', latest=True)
    # keepClipLengths=True overwrites duration and in_frames to use the full source clip lengths ( minus handles )
    # edit_custom.findFootage(r'C:\Users\chris\Desktop\testfootage', latest=True, keepClipLengths=True)
    # conforms edit to the duration set in the clip objects
    # edit_custom.conformEdit(mode='duration')
    # conforms edit to the cutpoints marked in the in_frame property of the clip objects
    edit_custom.conformEdit(mode='in_frame')
    edit_custom.preconvertClips()

    print(edit_custom.fastbuild(r'C:\Users\chris\Desktop\ffmpegFastBuildTest.mp4'))
    print(edit_custom.build(r'C:\Users\chris\Desktop\ffmpegSlowBuildTest.mp4'))

    edit_custom.cleanup()

    # for clip in edit_custom.edit:
    #     print(clip)