from __future__ import annotations
import os, json, datetime, subprocess, re, mimetypes, tempfile, shutil, glob, sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, overload
from pathlib import Path

@dataclass
class Config:
    ffmpeg_bin: str
    ffprobe_bin: str
    shot_mask_logo_path: str
    clip_frame_handles: int
    name: str='Edit'
    default_pass_name: str='latest pass'
    force_pass: bool=False #this forces the location to use the pass name
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
    missing_frame_color: str='orange'

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
            "color={missing_frame_color}:{width}x{height}:r={fps}[c];"
            "[c][0]overlay=eof_action=pass"
        ).format(width=self.scale[0], height=self.scale[1], logofilter=logofilter, missing_frame_color=self.missing_frame_color, fps=self.fps)
        
        drawmaskfilter=(
            "drawbox=x=0:y=0:w=-1:h={mask_size}:color=black@{mask_opacity}:t=fill[0];"
            "[0]drawbox=x=0:y=ih-h:w=-1:h={mask_size}:color=black@{mask_opacity}:t=fill"
        ).format(mask_size=self.mask_size, mask_opacity=self.mask_opacity, logooverlay=logooverlay)

        if mode == "clip":
            drawtextfilter=(
                "drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{pass_name}':x=(w-text_w)/2:y=({mask_size}/2)-(text_h/2)[0];"
                "[0]drawtext=fontsize={fontsize_large}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{shot_name}':x=w-text_w-{mask_padding}:y=({mask_size}/2)-(text_h/2)[0];"
                "[0]drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{shot_date}':x={mask_padding}:y=h-(text_h/2)-({mask_size}/3)[0];"
                "[0]drawtext=fontsize={fontsize_large}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='%{{frame_num}}':start_number={start_frame}:x=w-text_w-{mask_padding}:y=h-(text_h/2)-({mask_size}/2)[0];"
                "[0]drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text={shot_file_name}':x={mask_padding}:y=h-(text_h/2)-(({mask_size}/3)*2)"
            ).format(fontsize_small=self.fontsize_small, fontsize_large=self.fontsize_large, mask_size=self.mask_size, mask_padding=self.mask_padding, start_frame=self.in_frame, pass_name=self.pass_name, shot_name=self.shot_name, shot_date=self.date, shot_file_name=os.path.basename(self.file_name))
        elif mode == "sequence":
            drawtextfilter=(
                "drawtext=fontsize={fontsize_small}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':timecode='00\:00\:00\:00':rate={fps}:x=(w-text_w)/2:y=h-(text_h/2)-({mask_size}/2)"
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
    pass_name: str=''
    name: str='S000'
    shotmask: ShotMask = field(init=False)
    fps: int= field(init=False)
    is_converted: bool= field(init=False)
    is_missing_media: bool= field(init=False)
    converted_clip_path: str= field(init=False)
    ready: bool= field(init=False)
    _clip_path: str = field(init=False)

    def __post_init__(self):
        _clip_path: str = ''
        _pass_name: str = ''
        if not self.pass_name:
            self.pass_name=self.config.default_pass_name
        self._clip_path: Path=Path()
        self.ready=False
        self.converted_clip_path: Path=Path()
        self.is_missing_media=False
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
    
    def get_pass_name(self) -> str:
        return self.pass_name
    
    def set_pass_name(self, pass_name: str):
        self.shotmask.pass_name = pass_name
        self.pass_name = pass_name

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
    
    @overload
    def findFootage(self, footage_source: str, latest: bool=True, durationFromClip=False):
        pass
    @overload
    def findFootage(self, footage_source: Location, durationFromClip=False, location_filter=''):
        pass

    def findFootage(self, footage_source, latest=True, durationFromClip=False, location_filter=''):
        if type(footage_source)==Location:
            if location_filter=='':
                latest_clip = footage_source.findLatestAllLocations(name=self.name, mime_type='video')
                if latest_clip:
                    self.set_pass_name(latest_clip['sublocation_name'])
                    latest_clip=latest_clip['path']
                    
                else:
                    return None
            else:
                latest_clip=footage_source.findLatestInLocation(name=self.name, mime_type='video', location_name=location_filter)
                if latest_clip:
                    self.set_pass_name(latest_clip['sublocation_name'])
                    latest_clip=latest_clip['path']
                else:
                    return None
            
        elif type(footage_source)==str:
            if latest:
                # print('Searching Latest Clip footage for {} in {}'.format(self.name, footage_source))
                searchpath = Path(footage_source)
                videofiles_in_folder = [vf for vf in searchpath.rglob("*") if vf.is_file() and mimetypes.guess_type(vf)[0].startswith('video/')]
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
            else:
                raise NotImplementedError('Only latest clip mode is implemented. Set latest=True for this function')
        else:
            raise NotImplementedError('Footage Source Type {} not implemented'.format(type(footage_source)))
        
        self.clip_path = latest_clip
        if durationFromClip:
            self.duration=self.getDuration()
        self.check_ready()
        self.is_missing_media=False
        # print("Found {}".format(latest_clip))
        return latest_clip

    def generateMissingMediaFilter(self):
        color='Red'
        grid_ratio=self.clip_size[1]/5
        
        fontsize_title = self.clip_size[1]/15
        fontsize_subtitle = self.clip_size[1]/35
        fontsize_text = self.clip_size[1]/45

        logo_size=grid_ratio/1.5
        logo_padding=grid_ratio/2

        text_leading=grid_ratio/20
        text_offset_y=logo_size+logo_padding*2
        text_offset_x=logo_size+logo_padding*2

        current_offset=text_offset_y

        background="color={color}:{width}x{height}:r={fps}".format(color=color, width=self.clip_size[0], height=self.clip_size[1], fps=self.fps )
        missing_media_text="drawtext=fontsize={fontsize_title}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{text}':x={x_ofs}:y={y_ofs}".format(
            fontsize_title=fontsize_title, text="Missing Media {}".format(self.name), x_ofs=text_offset_x, y_ofs=current_offset)
        
        return '"{background}[0];[0]{missing_media_text}"'.format(
            background=background,
            missing_media_text=missing_media_text
        )

    def convertClip(self, output_path:str, ffmpeg_bin:str='', out_fps: Any=None) ->bool: 
        if not ffmpeg_bin:
            ffmpeg_bin=self.config.ffmpeg_bin
        if not out_fps:
            out_fps=self.config.fps
        if type(out_fps)==str:
            if out_fps.lower()=='nochange':
                out_fps=self.fps
        if not self.ready:
            print('Clip {} not ready, creating missing media clip!'.format(self.name))
            missing_media_out_name=Path(Path(output_path).parent,"missingMedia_{}.mp4".format(self.name))
            ffmpeg_cmd = (
                "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
                "-filter_complex {filter_string} "
                "-t {duration} "
                "-r {out_fps} "
                "{output_name}"
            ).format(
                ffmpeg_bin=ffmpeg_bin, 
                filter_string=self.generateMissingMediaFilter(), 
                duration=str(datetime.timedelta(seconds=self.duration+(self.frame_handles_in/self.fps))),
                out_fps=out_fps, 
                output_name=missing_media_out_name
            )
            subprocess.call(ffmpeg_cmd)

            self.clip_path=Path(missing_media_out_name)
            self.is_missing_media=True

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
        try:         
            out = subprocess.check_output([ffprobe_bin,self.clip_path,"-v","0","-select_streams","v","-print_format","flat","-show_entries","stream=r_frame_rate"], text=True)
            rate = out.split('=')[1].strip()[1:-1].split('/')
            if len(rate)==1:
                return float(rate[0])
            if len(rate)==2:
                return float(rate[0])/float(rate[1])
            return -1
        # when no clip does exist, it can't be checked for its fps and we need to use the base
        except TypeError as e:
            print("Error when getting frame rate, using base fps\n{}".format(e))
            return self.fps

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
class Slate(Clip):
    # config: Config
    in_frame: int=0
    # duration: float=5
    # clip_size: tuple=(1920,1080)
    title: str="Slate"
    notes: List[str]=List
    # pass_name: str=''
    # fps: int=field(init=False)
    # ready: bool=field(init=False)
    # converted_clip_path: str=field(init=False)
    # ready: bool=field(init=False)

    def __post_init__(self):
        self.name='slate_{}'.format("".join( x for x in self.title if (x.isalnum() or x in "_")))
        self._clip_path: Path=None
        self.ready=False
        self.converted_clip_path: Path=Path()
        self.is_converted=False
        self.fps=self.config.fps
        self.frame_handles_in=0
        self.shotmask = None
        self.clip_size=self.config.clip_size
        self.is_missing_media=False
        self.check_ready()

    def check_ready(self):
        if self.fps>0 and self.duration>0.0 and self.title:
            self.ready=True
        else:
            self.ready=False
    
    def convertClip(self, output_path:str, ffmpeg_bin:str='', out_fps: Any=None) ->bool: 
        if not ffmpeg_bin:
            ffmpeg_bin=self.config.ffmpeg_bin
        if not out_fps:
            out_fps=self.config.fps
        if type(out_fps)==str:
            if out_fps.lower()=='nochange':
                out_fps=self.fps
        if not self.ready:
            print('Slate {} not ready, skipping conversion!'.format(self.title))
            return False
        ffmpeg_cmd = (
            "{ffmpeg_bin} -y -hide_banner -stats -loglevel error "
            "-i {logo_path} "
            "-filter_complex {filter_string} "
            "-t {duration} "
            "-r {out_fps} "
            "{output_name}"
        ).format(
            fps=self.fps,
            ffmpeg_bin=ffmpeg_bin, 
            logo_path=self.config.shot_mask_logo_path, 
            filter_string=self.generateFilterString(), 
            duration=str(datetime.timedelta(seconds=self.duration)),
            out_fps=out_fps, 
            output_name=output_path
            )

        subprocess.call(ffmpeg_cmd)
        
        self.converted_clip_path=Path(output_path)
        self.check_converted()
        return True

    def generateFilterString(self):
        color='DarkSlateGray'
        grid_ratio=self.clip_size[1]/5
        
        fontsize_title = self.clip_size[1]/15
        fontsize_subtitle = self.clip_size[1]/35
        fontsize_text = self.clip_size[1]/45

        logo_size=grid_ratio/1.5
        logo_padding=grid_ratio/2

        text_leading=grid_ratio/20
        text_offset_y=logo_size+logo_padding*2
        text_offset_x=logo_size+logo_padding*2

        background="color={color}:{width}x{height}:r={fps}".format(color=color, width=self.clip_size[0], height=self.clip_size[1], fps=self.fps )
        logofilter="[0:v]scale=h={logo_size}:force_original_aspect_ratio=1".format(logo_size=logo_size) if self.config.shot_mask_logo_path else ""
        logooverlay="overlay=x={logo_padding}:y={logo_padding}".format(logo_padding=logo_padding) if self.config.shot_mask_logo_path else ""
        
        current_offset=text_offset_y

        title="drawtext=fontsize={fontsize_title}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{title}':x={x_ofs}:y={y_ofs}".format(
            fontsize_title=fontsize_title, title=self.title, x_ofs=text_offset_x, y_ofs=current_offset)
        current_offset+=fontsize_title
        
        subtitle="drawtext=fontsize={fontsize_subtitle}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{pass_name}':x={x_ofs}:y={y_ofs}".format(
            fontsize_subtitle=fontsize_subtitle, pass_name="Work in progress edit\: "+self.pass_name, x_ofs=text_offset_x, y_ofs=current_offset+text_leading)
        current_offset+=text_leading+fontsize_subtitle
        
        date="drawtext=fontsize={fontsize_text}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{date}':x={x_ofs}:y={y_ofs}".format(
            fontsize_text=fontsize_text, date=datetime.date.today().strftime("%y-%m-%d"), x_ofs=text_offset_x, y_ofs=current_offset+text_leading)
        current_offset+=text_leading+fontsize_text

        current_offset+=text_leading*4
        notes=[]
        for i, note in enumerate(self.notes):
            notes.append(
                "drawtext=fontsize={fontsize_text}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{notes_list}':x={x_ofs}:y={y_ofs}".format(
                    fontsize_text=fontsize_text, 
                    notes_list="- {}".format(note.replace(':', '\\:')), 
                    x_ofs=text_offset_x, 
                    y_ofs=current_offset+(text_leading*i)+(fontsize_text*i)
                    )
            )
        notes=','.join(notes)
        
        countdown_text="drawtext=fontsize={fontsize_title}:fontcolor=white:fontfile='C\\:/Windows/fonts/consola.ttf':text='{title}':x={x_ofs}:y={y_ofs}".format(
            fontsize_title=fontsize_title,
            # title='%{eif\\:(t)\\:d}.%{eif\\:(mod(t, 1)*pow(10,0))\\:d\\:0}',
            title='%{{eif\\:{duration}-(t)\\:d}}'.format(duration=self.duration),
            x_ofs=self.clip_size[0]-(grid_ratio/2),
            y_ofs=self.clip_size[1]-(grid_ratio/2)
        )

        return '"{background}[2];{logofilter}[1];[2][1]{logooverlay}[0];[0]{title}[0];[0]{date}[0];[0]{subtitle}[0];[0]{countdown_text}[0];[0]{notes}"'.format(
            background=background, 
            logofilter=logofilter, 
            logooverlay=logooverlay,
            title=title,
            date=date,
            subtitle=subtitle,
            countdown_text=countdown_text,
            notes=notes
            )

    def findFootage(self, footage_source: str, latest: bool=True, durationFromClip=False):
        print('Slates currently do not support footage')
        self.check_ready()

@dataclass
class Location():
    name: str
    folder: str
    priority: int=0
    parent_path: str=''
    location_type: str='local'
    subfolders_only: Bool=False
    sub_locations: List[Location]=field(init=False)

    def __post_init__(self):
        self.sub_locations=[]

    def __str__(self):
        return self.folder

    @property
    def path(self):
        return os.path.join(self.parent_path, self.folder) if self.parent_path else self.folder

    def addSublocation(self, location: Location):
        #sublocation are automatically sorted by priority
        location.parent_path=self.path
        self.sub_locations.append(location)
        self.sub_locations.sort(key=lambda i: i.priority, reverse=True)

    def getFilesDict(self, glob_filter: str='*', mime_type: str= '') ->Dict:
        # files are always sorted by latest per sublocation
        # sublocation are always sorted by priority
        files = {}
        files[self.name] = {}
        files[self.name]['path'] = self.path
        if not self.subfolders_only:
            file_list = [Path(f) for f in glob.glob(r'{}\{}'.format(self.path,glob_filter)) if os.path.isfile(f)]
            if mime_type:
                file_list = [vf for vf in file_list if mimetypes.guess_type(vf)[0].startswith('{}/'.format(mime_type))]
            files[self.name]['files'] = sorted(file_list, key= lambda x: x.stat().st_mtime)
        else:
            file_list = [Path(f) for f in glob.glob(r'{}\*\{}'.format(self.path,glob_filter)) if os.path.isfile(f)]
            if mime_type:
                file_list = [vf for vf in file_list if mimetypes.guess_type(vf)[0].startswith('{}/'.format(mime_type))]
            files[self.name]['files'] = sorted(file_list, key= lambda x: x.stat().st_mtime)
        if len(self.sub_locations)>0:
            files[self.name]['sublocations']=[]
            for sub_location in self.sub_locations:
                files[self.name]['sublocations'].append(sub_location.getFilesDict(glob_filter=glob_filter, mime_type=mime_type))
        return files
    
    def getFiles(self, glob_filter: str='*', mime_type: str= '', include_sublocations=True) ->List[Path]:
        # files are always sorted by priority first and latest second
        files = []
        if not self.subfolders_only:
            files.extend(sorted([Path(f) for f in glob.glob(r'{}\{}'.format(self.path,glob_filter)) if os.path.isfile(f)], key=lambda x: x.stat().st_mtime))
        else:
            files.extend(sorted([Path(f) for f in glob.glob(r'{}\*\{}'.format(self.path,glob_filter)) if os.path.isfile(f)], key=lambda x: x.stat().st_mtime))
        if len(self.sub_locations)>0 and include_sublocations:
            for sub_location in self.sub_locations:
                files.extend(sub_location.getFiles(glob_filter=glob_filter, mime_type=mime_type))
        if mime_type:
            files = [vf for vf in files if mimetypes.guess_type(vf)[0].startswith('{}/'.format(mime_type))]
        return files

    @overload
    def findLatestInLocation(self, name: str, glob_filter: str='*', mime_type: str= '') ->List:
        pass
    @overload
    def findLatestInLocation(self, name: str, glob_filter: str='*', mime_type: str= '', location_name='') ->Dict:
        pass

    def findLatestInLocation(self, name: str, glob_filter: str='*', mime_type: str= '', location_name=''):
        files = []
        if len(self.sub_locations)>0:
            for sublocation in self.sub_locations:
                files.extend(sublocation.findLatestInLocation(name, glob_filter, mime_type))
        found_files = []
        for file in self.getFiles(glob_filter, mime_type, include_sublocations=False):
            if re.search("({})".format(name), str(file), flags=re.IGNORECASE):
                found_files.extend(file if type(file)==List else [file])
        if found_files: 
            latest_file = max(found_files, key=lambda x: x.stat().st_mtime)
            found_file={
                'name': name,
                'path': latest_file,
                'sublocation_name': self.name,
                'priority': self.priority
            }
            files.append(found_file)
        if location_name:
            latest_clips_in_loc=[ff for ff in files if ff['sublocation_name']==location_name]
            return (latest_clips_in_loc[0] if len(latest_clips_in_loc)>0 else None)
        
        return sorted(files, key= lambda x: x['priority'], reverse=True)
    
    def findLatestAllLocations(self, name: str, glob_filter: str='*', mime_type: str= '') ->Dict:
        latestInLocation = self.findLatestInLocation(name, glob_filter, mime_type)
        return latestInLocation[0] if len(latestInLocation)>0 else None

@dataclass
class Edit:
    config: Config
    name: str=''
    shot_desc_path: str=''
    source_folder: Union(str, Location)=''
    frameoffset: int= 0
    fps: int=None
    edit: list[Clip]= field(init=False)
    temp_folder: str= field(init=False)
    ready: bool= field(init=False)

    def __post_init__(self):
        if not self.name:
            self.name=self.config.name
        if self.shot_desc_path:
            self.edit=self.loadEdit(self.shot_desc_path)
            self.findFootage(self.source_folder, latest=True)
        else:
            self.edit=[]
        if self.fps==None:
            self.fps=self.config.fps
        self.temp_folder=None,
        self.check_ready()

    def check_ready(self):
        if len(self.edit)>0 and all([clip.ready for clip in self.edit]) and all([clip.is_converted for clip in self.edit]): 
            self.ready=True
        else:
            self.ready=False

    def addAutoSlate(self):
        source_folder_format = self.source_folder if len(str(self.source_folder))<35 else Path(*Path(str(self.source_folder)).parts[-5:])
        shot_desc_path_format = self.shot_desc_path if len(self.shot_desc_path)<35 else Path(*Path(self.shot_desc_path).parts[-2:])
        slate=Slate(
            config=self.config,
            title=self.name,
            notes=[
                "size: {} x {}".format(self.config.clip_size[0], self.config.clip_size[1]),
                "fps: {}".format(self.fps),
                "pass: {}".format(self.config.default_pass_name),
                "Source: {}".format(str(shot_desc_path_format).replace('\\', '\\\\\\\\')),
                "Footage Source: {}".format(str(source_folder_format).replace('\\', '\\\\\\\\'))
            ],
            duration=self.frameoffset/self.fps,
            pass_name=self.config.default_pass_name
        )
        self.addClip(slate, sequential=False)

    def addClip(self, clip: Clip, sequential: bool=True):
        if sequential:
            clip_offset = sum([c.duration*c.fps for c in self.edit])
            clip.in_frame = clip_offset
        self.edit.append(clip)
        self.frameoffset = min([c.in_frame for c in self.edit])
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
    
    def findFootage(self, source_folder: Union(str,Location)=None, latest=True, keepClipLengths=False, location_filter=''):
        if source_folder==None:
            source_folder=self.source_folder
        for clip in self.edit:
            if type(source_folder)==Location:
                if location_filter:
                    clip.findFootage(source_folder, durationFromClip=keepClipLengths, location_filter=location_filter)
                elif self.config.force_pass:
                    clip.findFootage(source_folder, durationFromClip=keepClipLengths, location_filter=self.config.default_pass_name)
                else:
                    clip.findFootage(source_folder, durationFromClip=keepClipLengths )
            else:
                clip.findFootage(source_folder, latest=latest, durationFromClip=keepClipLengths)
        self.check_ready()

    def preconvertClips(self, tempfolder: str='') ->str:
        if any(not c.ready for c in self.edit):
            print('Not all clips are ready, output will have missing media clips')
            # return None
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
        '''conforms the clip durations and inframes to be continous. Order will always be determined by in_frame
        Has three modes: 
        'in_frame' conforms everything to the in frame on the edit using the edits fps
        'in_frame_clip' will use the clips fps to cut at that frame in the clip - if the clip is using different framerates than the edit, values don't match.
        'duration' adjusts the in_frame and out_frame of all clips so the durations stay the same.'''

        self.edit.sort(key=lambda d: d.in_frame)
        self.frameoffset = min([c.in_frame for c in self.edit])

        if mode=='in_frame':
            for i, clip in enumerate(self.edit):
                if i<len(self.edit)-1:
                    nextclip=self.edit[i+1]
                    clip_framelen=nextclip.in_frame-clip.in_frame
                    clip.duration=clip_framelen/self.fps
        elif mode=='in_frame_clip':
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
            #"-movflags faststart "
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

    anim_config = Config(
        ffmpeg_bin=r'C:\ffmpeg\bin\ffmpeg', 
        ffprobe_bin=r'C:\ffmpeg\bin\ffprobe',
        name='Test Edit',
        default_pass_name='Animation', 
        force_pass=True, #forces to use clips from #pass# location ( Animation )
        enable_shotmask=True,
        shot_mask_logo_path=r'C:\01_Work\02_PersonalProjects\editbot\res\tetsuo_favicon.png' , 
        clip_frame_handles=1,
        fps=30
    )

    latest_config = Config(
        ffmpeg_bin=r'C:\Program Files\ffmpeg\bin\ffmpeg', 
        ffprobe_bin=r'C:\Program Files\ffmpeg\bin\ffprobe',
        name='Test Edit',
        default_pass_name='Latest Pass', 
        force_pass=False, #uses latest location pass and sets name to it
        enable_shotmask=True,
        shot_mask_logo_path=r'D:\01_Work\01_Software\EditBot\res\tetsuo_favicon.png' , 
        clip_frame_handles=1,
        fps=30
    )

    # set config for this build
    running_config=latest_config

    #build location
    # storageLocation = Location(name='root', folder=r"d:\AutomatedProjects\FallGuys\2106_Fallguys_Symphony\10_Output\00_Preview")
    storageLocation = Location(name='root', folder=r'C:\Users\chris\Desktop\testfootage')
    storageLocation.addSublocation(Location(name='Assembly', folder='04_Assembly', priority=5, subfolders_only=True))
    storageLocation.addSublocation(Location(name='Animation', folder='02_Animation\\02_Shots', priority=3, subfolders_only=True))

    # print(storageLocation)
    # # print(json.dumps(storageLocation.getFilesDict(mime_type='video'), indent=4, default=str))
    # # print(json.dumps(storageLocation.getFiles(mime_type='video'), indent=4, default=str))
    # print(json.dumps(storageLocation.findLatestInLocation(name='S010', mime_type='video', location_name='Animation'), indent=4, default=str))
    # print(json.dumps(storageLocation.findLatestAllLocations(name='S010', mime_type='video'), indent=4, default=str))

    # test edit from desc
    # edit = Edit(
    #     config=config,
    #     shot_desc_path=r"C:\01_Work\02_PersonalProjects\watchtower\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json",
    #     source_folder=r"C:\Users\Chris\Desktop\testfootage"
    #     )

    # not needed, if a path is supplied, the constructor will load it automatically
    # edit.loadEdit(r"C:\01_Work\02_PersonalProjects\watchtower\watchtower\dist\static\projects\5c28af86-7550-11ec-a8d3-aea52421b16b\shots.json")

    #custom edit
    clip1 = Clip(
        config=running_config,
        name = 'S010-020',
        # frame_handles_in=5,
        in_frame = 60,
        duration= 5,
        # pass_name='Layout'
    )

    clip2 = Clip(
        config=running_config,
        name = 'S030-040',
        #frame_handles_in=5,
        in_frame = 20,
        duration= 5,
        pass_name='First Pass Animation'
    )

    missing = Clip(
        config=running_config,
        name = 'S070',
        in_frame = 80,
        duration= 4,
        pass_name='Missing Clip'
    )

    slate1 = Slate(
        config=running_config,
        title='Testedit',
        notes=[
            'an edit for testing',
            'does not include real data',
            'temp audio pass',
            'scenery is not built',
            'if this actually runs, I\'m surprised'
        ],
        duration=5,
        pass_name='Animation'
    )

    edit_custom = Edit(config=running_config)
    # sequential = True means the edit won't care about the in_frame and just append the clip to the edit
    # edit_custom.addClip(clip1, sequential=True)
    # edit_custom.addClip(clip2, sequential=True)
    # sequential = False will make sure the cutpoints in in_frame are used
    # edit_custom.addClip(slate1, sequential=False)
    edit_custom.addClip(missing, sequential=False)
    edit_custom.addClip(clip1, sequential=False)
    edit_custom.addClip(clip2, sequential=False)
    # this uses the definition in the clip object if it has not been overwritten
    # simple mode - set folder
    # edit_custom.findFootage(r'C:\Users\chris\Desktop\testfootage\nofolders', latest=True)
    # storage location mode - needs configures storage location ( would use config defaults )
    edit_custom.findFootage(storageLocation)
    # filter for specific pass on find footage step ( this is an override for the config! )
    # edit_custom.findFootage(storageLocation, location_filter='Assembly')
    # keepClipLengths=True overwrites duration and in_frames to use the full source clip lengths ( minus handles )
    # edit_custom.findFootage(r'C:\Users\chris\Desktop\testfootage', latest=True, keepClipLengths=True)
    # conforms edit to the duration set in the clip objects
    # edit_custom.conformEdit(mode='duration')
    # conforms edit to the cutpoints marked in the in_frame property of the clip objects
    edit_custom.conformEdit(mode='in_frame')
    edit_custom.addAutoSlate()
    edit_custom.preconvertClips()

    print(edit_custom.fastbuild(r'C:\Users\chris\Desktop\ffmpegFastBuildTest.mp4'))
    print(edit_custom.build(r'C:\Users\chris\Desktop\ffmpegSlowBuildTest.mp4'))

    edit_custom.cleanup()

    # for clip in edit_custom.edit:
    #     print(clip)