import yaml
import os
import time
import datetime
from copy import deepcopy as dc
from numpy import array, arange
from shutil import copyfile
import queue

from sqlalchemy import orm
from sqlalchemy import Column, Integer, String, Boolean, Time, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import desc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.fx.resize import resize

from wand.image import Image
from wand.color import Color


Base = declarative_base()

def create_project_databse(db_engine):
    Base.metadata.create_all(db_engine, Base.metadata.tables.values(),checkfirst=True)

def create_session(project_folder):
    if not os.path.exists(project_folder):
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
    db_file = os.path.join(project_folder, 'vcproject.db3')
    engine = 'sqlite:///'+db_file
    some_engine = create_engine(engine)
    create_project_databse(some_engine)
    Session = sessionmaker(bind=some_engine)
    return Session()

class Command(Base):
    """Command Database Object

    """
    __tablename__ = 'command'
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('sequenceElements.id'))
    parent = relationship("SequenceModule", back_populates="list_commands")
    name = Column(String(50))
    device = Column(String(50))
    name_cmd = Column(String(50))
    cmd_parameter1 = Column(String(10))
    cmd_parameter2 = Column(String(10))
    cmd_parameter3 = Column(String(10))
    delay = Column(Integer)
    session = None
    #can be extendet with expected values to check for errors
    
    @classmethod
    def set_session(cls, session):
        cls.session = session

    def __init__(self, name, device, name_cmd, *args, delay=0):
        self.name = name
        self.name_cmd = name_cmd
        self.device = device
        self.delay = delay
        self.set_parameters(*args)
        self._update_db()

    def get_args(self):
        if not self.cmd_parameter1:
            return ()
        elif self.cmd_parameter3:
            return (int(self.cmd_parameter1), int(self.cmd_parameter2), int(self.cmd_parameter3))
        elif self.cmd_parameter2:
            return (int(self.cmd_parameter1), int(self.cmd_parameter2))
        else:  # self.cmd_parameter1
            return (int(self.cmd_parameter1),)

    def set_parameters(self, *args):
        if len(args) > 0:
            self.cmd_parameter1 = args[0]
        if len(args) > 1:
            self.cmd_parameter2 = args[1]
        if len(args) > 2:
            self.cmd_parameter3 = args[2]

    def _update_db(self):
        #return
        if not Command.session:
            return
        if not self.id:
            Command.session.add(self)
        Command.session.commit()

    def __repr__(self):
        return "{}|{}|{}|{}".format(self.name, self.device, self.name_cmd, self.get_args())


class LogicElement(Base):
    """Base class for Logic Elements.
    
    Args:
        name (str): name of the logic element
        key  (int): unique key of logic element (important for loops)

    Attributes:
        name    (str): name of the logic element
        key     (int): unique key of logic element (important for loops)
        id      (int): primary key of object in database
        etyp (string): polymorphic_identity of element in database

    """
    __tablename__ = 'logicElement'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    #position = Column(Integer)
    key = Column(Integer)
    etype = Column(String(20))

    __mapper_args__ = {
        'polymorphic_on':etype,
        'polymorphic_identity':'LogicElement'
    }

    def __init__(self, name, key):
        self.name = name
        self.key = key

class LoopStart(LogicElement):
    """Saves position for the start of a loop condition"""

    __mapper_args__ = {
        'polymorphic_identity':'LoopStart'
    }

    def __init__(self, name, key):
        super().__init__(name, key)

class LoopEnd(LogicElement):
    """Saves position for the start of a loop condition"""

    cycles = Column(Integer)

    __mapper_args__ = {
        'polymorphic_identity':'LoopEnd'
    }

    def __init__(self, name, key, cycles):
        super().__init__(name, key)
        self.cycles = cycles
        self.init2()

    @orm.reconstructor
    def init2(self):
        self.counter = 0


class JumpToTarget(LogicElement):
    """Saves position for the start of a loop condition"""

    __mapper_args__ = {
        'polymorphic_identity':'JumpToTarget'
    }

    def __init__(self, name):
        super().__init__(name, None)


class LogicElementManager:
    """Manager for all lofic elemets at runtime and in database.

    Args:
        session (sqlalchemy.orm.Session): database session

    Attributes:
        session  (sqlalchemy.orm.Session): database session
        elements     (Lits<MediaElemets>): list of active logic elemets

    """

    def __init__(self, session):
        self.session = session
        self.elements = []
        self._load_elements()        

    def add_element(self, obj, num=1):
        # name=obj.name
        # if num > 1:
        #     name='{}_{}'.format(name, num)

        # res = self.session.query(LogicElement).filter(LogicElement.name==name).first()

        # if res:
        #     self.add_element(obj, num=num+1)
        #     return
        # if num > 1:
        #     obj.name=name
        self.elements.append(obj)
        self.session.add(obj)
        self.session.commit()

    def del_element(self, obj):
        pass

    def get_element_with_name(self, name):
        for e in self.elements:
            if e.name==name:
                return e
        return None

    def _load_elements(self):
        self.elements.extend(self.session.query(MediaElement).all())

    def add_element_loop(self, cycles):
        raw_key = self.session.query(LoopStart.key).order_by(desc(LoopStart.key)).first()
        if not raw_key:
            key = 1
        else:
            key = raw_key[0]
        loop_start = LoopStart("LoopStart_{}".format(key), key)
        self.add_element(loop_start)
        loop_end = LoopEnd("LoopEnd_{}".format(key), key, cycles)
        self.add_element(loop_end)

class MediaElement(Base):
    """Base class for Media Elements.

    Since the media output format is always 1080p with an aspect ratio of 16:9, 
    the film format of the film on the BlueRay is either 16:9 widescreen or 
    21:9 cincescope (the term CinemaScope originally stands for a special 
    process for recording and projecting wide-screen films with an aspect ratio
    of 2.55:1 = 23:9 and is nevertheless used here for the designation of the 
    21:9 image format). If the film format is cinescope, the zoom of the 
    projector is adjusted in such a way that the film content fills the screen 
    and the black bars remain outside of the screen. If images and videos are 
    displayed here now, they have to stay in the cinescope image area. 
    Therefore, there are file paths to both media formats, which can also be 
    identical. 

    The following nomenclatures for the image content format are used: 
        cinescope   '21:9'  '_c'
        widescreen  '16:9'  '_w'

    Args:
        name        (str): name of the media element
        file_path_w (str): file path to widescreen version of the file
        file_path_c (str): file path to cinescope version of the file

    Attributes:
        name        (str): name of the media element
        file_path_w (str): file path to widescreen version of the file
        file_path_c (str): file path to cinescope version of the file
        id          (int): primary key of object in database
        etype    (string): polymorphic_identity of element in database

    """
    __tablename__ = 'mediaElement'
    id = Column(Integer, primary_key=True, )
    name = Column(String(50))
    file_path_w = Column(String(50))
    file_path_c = Column(String(50))
    etype = Column(String(20))
    project_path = None
    content_aspect_ratio = 'widescreen'

    __mapper_args__ = {
        'polymorphic_on':etype,
        'polymorphic_identity':'MediaElement'
    }

    @classmethod
    def set_project_path(cls, path):
        cls.project_path = os.path.expanduser(path)

    @classmethod
    def set_content_aspect_ratio(cls, ratio):
        if ratio in ['w', 'widescreen', '16:9']:
            cls.content_aspect_ratio = 'widescreen'
        else:
            cls.content_aspect_ratio = 'cinescope'      

    @staticmethod
    def create_abs_filepath(abs_source, mid, extension, num=1):
        target_file_core = os.path.splitext(os.path.basename(abs_source))[0]
        if num > 1:
            midnum = "{}_{}".format(mid, num)
        else:
            midnum = mid
        target_file = os.path.join(
            MediaElement.project_path,
            target_file_core + midnum + "." + extension
        )
        if os.path.exists(target_file):
            target_file = StartElement.create_abs_filepath(abs_source, mid, extension, num=num+1)
        return target_file, os.path.relpath(target_file, start=MediaElement.project_path)  

    @property
    def file_path(self):
        if MediaElement.content_aspect_ratio == 'widescreen':
            return os.path.join(MediaElement.project_path, self.file_path_w)
        else:
            return os.path.join(MediaElement.project_path, self.file_path_c)
    
    def __init__(self, name, file_path_w, file_path_c):
        self.name = name
        self.file_path_w = file_path_w
        self.file_path_c = file_path_c

    def initialize(self, name, file_path_w, file_path_c):
        self.name = name
        self.file_path_w = file_path_w
        self.file_path_c = file_path_c

    def __repr__(self):
        return "{}|{}".format(type(self), self.name)


class VideoElement(MediaElement):
    """Class for moving MediaElement.
    
    Args:
        name        (str): name of the media element
        file_path (str): file path to source file, which will be copied and/or
            converted into the media folder defined in the config file

    Attributes:
        duration (float): duration in seconds of video clip

    """

    duration = Column(Integer)

    __mapper_args__ = {
        'polymorphic_identity':'VideoElement'
    }

    def __init__(self, name, file_path):
        
        adst_c, rdst_c = MediaElement.create_abs_filepath(file_path, "_c", "mp4")
        dur, car = self.insert_video(file_path, adst_c, cinescope=True)
        self.duration = dur
        content_aspect_ratio = car
        if content_aspect_ratio == '21:9':
            adst_w = adst_c
            rdst_w = rdst_c
        else:
            adst_w, rdst_w = MediaElement.create_abs_filepath(file_path, "_w", "mp4")
            self.insert_video(file_path, adst_w, content_aspect=content_aspect_ratio, cinescope=False)
        super().__init__(name, rdst_w, rdst_c)


    def insert_video(self, path_scr, path_dst, content_aspect=None, cinescope=True):
        video_clip = VideoFileClip(path_scr)
        if cinescope:            
            content_aspect = VideoElement.get_video_content_aspect_ratio(video_clip)
        if content_aspect == "16:9" and cinescope:
            #else do nothing cinscope identical with widescreen
            cclip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=video_clip.duration)
            video_clip = video_clip.fx(resize, height=810).set_position('center')
            result = CompositeVideoClip([cclip, video_clip])
            result.write_videofile(path_dst,fps=video_clip.fps)
        else:
            copyfile(path_scr, path_dst)
        return video_clip.duration, content_aspect

    @staticmethod
    def get_video_content_aspect_ratio(video_file_clip):
        vfc = video_file_clip
        samples=5
        sample_time_step = video_file_clip.duration/samples
        w = []
        for t in arange(0,video_file_clip.duration,sample_time_step):
            frame=video_file_clip.get_frame(t)
            
            w.append(frame[[int(vfc.h*.125), int(vfc.h*.5), int(vfc.h*.875)], 0:vfc.w].mean(axis=2).mean(axis=1))
        w=array(w)
        wm = w.mean(axis=0)

        if wm[0] < 1 and wm[2] < 1 and wm[1]>=1:
            return '21:9'
        else:
            return '16:9'

class StillElement(MediaElement):
    """Class for non-moving MediaElement.

    Args:
        name        (str): name of the media element
        file_path (str): file path to source file, which will be copied and/or
            converted into the media folder defined in the config file

    
    """

    __mapper_args__ = {
        'polymorphic_identity':'StillElement'
    }         
        
    def __init__(self, name, file_path):
        adst_w, rdst_w = MediaElement.create_abs_filepath(file_path, "_w", "jpg")
        adst_c, rdst_c = MediaElement.create_abs_filepath(file_path, "_c", "jpg")
        StillElement.insert_image(file_path, adst_w , False)
        StillElement.insert_image(file_path, adst_c, True)
        super().__init__(name, rdst_w, rdst_c)
    

    @staticmethod
    def insert_image(path_scr, path_dst, cinescope):
        """Composes images with black background for widescreen and cinescope.

        """
        if cinescope:
            screesize =  (1920, 810)
        else:
            screesize =  (1920, 1080)
        with Image(filename=path_scr, resolution=300) as scr:
            with Image(width=1920, height=1080, background=Color("black")) as dst:   
                scr.scale(int(scr.width/scr.height*screesize[1]), screesize[1])
                offset_width = int((dst.width-scr.width)/2)
                offset_height = int((dst.height-scr.height)/2)
                dst.composite(operator='over', left=offset_width, top=offset_height, image=scr)
                dst.save(filename=path_dst)

class StartElement(MediaElement):
    """Class for start MediaElement cointaining the program picture."""

    def __init__(self):
        super().__init__('viewcontrol', 'media/viewcontrol.png', 'media/viewcontrol.png')

class MediaElementManager:
    """Manager for all media elemets at runtime and in database.

    Args:
        session (sqlalchemy.orm.Session): database session

    Attributes:
        session  (sqlalchemy.orm.Session): database session
        elements     (Lits<MediaElemets>): list of active media elemets

    """

    def __init__(self, session):
        self.session = session
        self.elements = []
        self._load_elements()

    def add_element(self, obj, num=1):
        name=obj.name
        if num > 1:
            name='{}_{}'.format(name, num)

        res = self.session.query(MediaElement).filter(MediaElement.name==name).first()

        if res:
            self.add_element(obj, num=num+1)
            return
        if num > 1:
            obj.name=name
        self.elements.append(obj)
        self.session.add(obj)
        self.session.commit()

    def del_element(self, obj):
        pass

    def get_element_with_name(self, name):
        for e in self.elements:
            if e.name==name:
                return e
        return None

    def _load_elements(self):
        self.elements = self.session.query(MediaElement).all()

class SequenceModule(Base):
    """Object of a Playlist

    One of the two elements is always None (construction for database technical
    reasons). A MediaElement can be used in any number of SequenceElements 
    (many to one). With VideoElements the time corresponds to the video length 
    with StillElements the time corresponds to the display duration and is set 
    by the user. 

    Args:
        sequence_name
        position
        element=None
        time=None
        list_commands

    Attributes:
        id          (int): primary key of object in database
        sequence_name
        position
        time
        logic_element_id
        logic_element
        media_element_id
        media_element

    """
    
    __tablename__ = 'sequenceElements'
    id = Column(Integer, primary_key=True)
    sequence_name = Column(String(20), nullable=True)
    position = Column(Integer)
    time = Column(Float)
    #https://docs.sqlalchemy.org/en/13/orm/join_conditions.html
    logic_element_id = Column(Integer, ForeignKey('logicElement.id'))
    logic_element = relationship("LogicElement", foreign_keys=[logic_element_id])
    media_element_id = Column(Integer, ForeignKey('mediaElement.id'))
    media_element = relationship("MediaElement", foreign_keys=[media_element_id])
    list_commands = relationship("Command", back_populates="parent")


    def __init__(self, sequence_name, position, element=None, time=None, list_commands=[]):
        self.sequence_name = sequence_name
        self.position = position
        if isinstance(element, VideoElement):
            #get length of video
            time = element.duration
            pass
        elif isinstance(element, StillElement) and not time:
            time = 5
        else:
            time = 3.14
        self.time=time
        self._set_element(element)
        if isinstance(list_commands, list):
            self.list_commands = list_commands
        else:
            self.list_commands = [list_commands]

    def __repr__(self):
        if self.media_element:
            element_name = self.media_element.name
        else:
            element_name = self.logic_element.name
        return "{}|{}|{}|".format(self.sequence_name, self.position, element_name)

    def _set_element(self, element):
        """set element depending of class"""
        if not element:
            return
        elif issubclass(type(element), MediaElement):
            self.media_element = element
        elif issubclass(type(element), LogicElement):
            self.logic_element = element

    def add_element(self, obj):
        """add media or logic element to playlist pos"""
        if not self.media_element and not self.sequence_name:
            self._set_element(obj)
        else:
            raise Exception("SequenceModule already conatins an element.")

    def add_command(self, command_obj):
        """add a command to the command list"""
        self.list_commands.append(command_obj)

    def remove_command(self, command):
        """remove a command from the command list"""
        raise NotImplementedError
    
    def del_element(self):
        """delete the media or logic element"""
        raise NotImplementedError

    def replace_element(self, obj):
        """replace the current media element with a new one."""
        raise NotImplementedError

    @staticmethod
    def viewcontroll_placeholder():
        return SequenceModule("None", 0, element=StartElement(), time=5)

class Show():
    """SequenceObjectManager/PlaylistManager

    Manages Sequence Object. Media or LogicElements must be in the Database.

    Args:
        name                                 (str): name of the show
        session (sqlalchemy.orm.Session, optional): database session, defaults
            to None. If None, s default session will be created from config 
            file.
        project_folder             (str, optional): path to a existing project
            or for a new project. only used when session is not defined. 
            Defaults to None. If None, path from config.yaml will be used. 

    Attributes:
        current_pos                (int): 
        sequence_name              (str): name of the show (sequece_name of all
            SequenceElements in sequence)
        sequence (List<SequenceElement>): Playlist list of all SequenceElements  
        session (sqlalchemy.orm.Session): database session

    """
    
    def __init__(self, name, session=None, project_folder=None, content_aspect_ratio='w'):
        self.current_pos = 0
        self.sequence_name = name
        self.sequence = list()
        if not session:
            self.session = create_session(project_folder)
        else:
            self.session = session
            project_folder = os.path.dirname(session.bind.engine.engine.engine.url.database)
        MediaElement.set_project_path(project_folder)
        MediaElement.set_content_aspect_ratio(content_aspect_ratio)
        self._load_show()
        self.happened_event_queue = queue.Queue()

    #@orm.reconstructor
    def _load_show(self):
        self._load_objects_from_db()
        self._find_jumptotarget_elements()

    def _find_jumptotarget_elements(self):
        """find all jumptotarget_elements in playlist and set the property"""
        self.jumptotarget_elements = []
        for e in self.sequence:
            if e.logic_element:
                if isinstance(e.logic_element, JumpToTarget):
                    self.jumptotarget_elements.append(e)

    @property
    def current_element(self):
        """returns current element"""
        return self._get_object_at_pos(self.current_pos)

    def notify(self, name_event):
        """handles events send to show"""
        self.happened_event_queue.put(name_event)

    @property
    def count(self):
        """number of modules in playlist"""
        return len(self.sequence)

    def del_show(self):
        """delete show at database"""
        raise NotImplementedError

    def save_show(self):
        """save show to database"""
        self.session.commit()

    def add_jumptotarget(self, name, pos=None, commands=[]):
        """apends a jump to target sequence module"""
        jttm = JumpToTarget(name)
        self.add_module(jttm, pos)
        self.jumptotarget_elements.append(jttm)

    def add_module(self, element, pos=None, time=None, commands=[]):
        """adds a module to playlist at given pos or at end when pos=None"""
        sm = SequenceModule(self.sequence_name, len(self.sequence), 
            element=element, time=time, list_commands=commands)
        self._append_to_pos(sm, pos)

    def add_module_still(self, name, file_path, *kargs):
        """add a module coonatining a StillElement"""
        e = StillElement(name, file_path)
        MediaElementManager(self.session).add_element(e)
        self.add_module(e, *kargs)

    def _append_to_pos(self, element, pos=None):
        """append element at given position"""
        self.sequence.append(element)
        self.session.add(element)
        self.session.commit()
        if pos:
            self.change_position(element, pos)

    def append_module(self, element):
        """add elemement at end of sequence"""
        self.add_module(element)
    
    def add_empty_module(self, pos=None):
        """add a empty module without any elements"""
        self.add_module(None, pos)

    def append_empty_module(self):
        """add a empty module without any elements at end of sequence"""
        self.add_module(None)

    def change_position(self, element, new_pos, first=True):
        """change position of sequence elements"""
        cur_pos = element.position
        if cur_pos < new_pos:
            next_pos = cur_pos+1
        elif cur_pos > new_pos:
            next_pos = cur_pos-1
        else:
            self.session.commit()
            return

        self._get_object_at_pos(next_pos).position = cur_pos
        element.position = next_pos
        
        self.change_position(element, new_pos)

    def _load_objects_from_db(self):
        """load show from database"""
        self.sequence = self.session.query(SequenceModule).\
            filter(SequenceModule.sequence_name==self.sequence_name).all()

    def _get_object_at_pos(self, position):
        """returns object on given playlist position"""
        for s in self.sequence:
            if s.position == position:
                return s

    def first(self):
        """resets playlist counter and returns first object"""
        self.current_pos = 0
        return self._get_object_at_pos(self.current_pos)

    def handle_global_event(self, evnet_name):
        """preperation for future development
            handle a global event that must be handeled emidetly
            > e.g Blury @chapter 10 --> call event pause
        """
        #gets called by the notify function
        #compares evnet_name to global events
        #if True:
        #   signal.send("") send out new event
        #else:
        #   self.happened_event_queue.put(evnet_name)
        pass

    def next(self):
        """returns next element and handles logic elements"""

        while not self.happened_event_queue.empty():
            event = self.happened_event_queue.get()
            for e in self.jumptotarget_elements:
                if e.logic_element.name in event:
                    self.current_pos = e.position

        if self.current_pos < len(self.sequence)-1:
            self.current_pos = self.current_pos+1
            obj = self.current_element
        else:
            obj = SequenceModule.viewcontroll_placeholder()
        
        if not obj:
            raise Exception("playlist at end")
        if obj.logic_element:
            if isinstance(obj.logic_element, LoopEnd):
                if obj.logic_element.counter < obj.logic_element.cycles:
                    for s in self.sequence:
                        if isinstance(s.logic_element, LoopStart) \
                            and s.logic_element.key == obj.logic_element.key:
                            self.current_pos = s.position                  
                    obj.logic_element.counter = obj.logic_element.counter + 1
            
            return self.next()
        else:
            return obj