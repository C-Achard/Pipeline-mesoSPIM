"""Schema for experimental information."""
import sys

sys.path.append("")
import datajoint as dj

schema = dj.schema("exp", locals(), create_tables=True)


@schema
class Experimenter(dj.Lookup):
    definition = """  # Information about Experimenter
    experimenter_name      : char(20)   # lab member in lower case
    ---
    full_name              : varchar(255)    # Full name (FirstName LastName)
    email='info@example.com': varchar(128) # email address
    """
    contents = [
        ["mathislab", "general mathislab account"],
        ["mackenzie", "Mackenzie Mathis"],
        ["alexander", "Alexander Mathis"],
        ["adrian", "Adrian Hoffmann"],
        ["tanmay", "Tanmay Nath"],
        ["gary", "Gary Kane"],
        ["sebastien", "Sebastien Hausmann"],
    ]


################################### Experimental Session Information: #####################


@schema
class Anesthesia(dj.Lookup):
    definition = """   #  anesthesia states
    anesthesia_name             : varchar(20) # anesthesia short name
    ---
    anesthesia_details = ''     : varchar(1024) # longer description
    """
    contents = [
        ["awake", "mouse is awake and no immediate hx of anesthesia"],
        [
            "ketamine",
            "mouse is anesthetized to near surgical plane with K/X mixture: 87.5 mg/kg Ketamine + 12.5 mg/kg Xylazine",
        ],
        [
            "isoflurane",
            "mouse is under gas anesthesia, ~4-5 Percent induction, ~1 Percent maintaince",
        ],
    ]


@schema
class Rig(dj.Lookup):
    definition = """
    rig_id        : int             # Experimental setup number
    ---
    details       : varchar(2048)   # Description of the setup
    """
    contents = [
        [1, "behavior training, optogenetics, perturbations"],
        [2, "behavior training - rig 2 (for left handed mice)"],
        [3, "behavior training - rig 3 (for right handed mice)"],
        [4, "behavior training - rig 4 (for right handed mice)"],
        [5, "mesoscope scans, perturbations"],
        [6, "virtual reality with electrophysiology, optogenetics"],
        [7, "cognitive tasks with electrophysiology, optogenetics"],
        [8, "cognitive tasks - rig 8"],
        [9, "split-belt treadmill"],
        [10, "robotic manipulandum"],
    ]


@schema
class OptogeneticsRegion(dj.Lookup):
    definition = """  # Optogenetics applied

    opto_region_name          : char(10)   # region
    -----
    opto_region_details = ''  : varchar(2048)   # brain region
    """
    contents = [
        ["none", "no optogenetics was applied during the session"],
        ["M1", "unilaterally applied over M1 (forelimb)"],
        ["S1", "unilaterally applied over S1 (forelimb)"],
        ["ALM", "unilaterally applied over ALM "],
        [
            "SC",
            "applied over the spinal cord at the region of the forelimb brachical complex",
        ],
        ["CB_all", "applied over a spatial map of CB"],
        ["CB_IV/V", "applied over specific lobule only"],
        ["CB_V1a", "applied over specific lobule only"],
        ["CB_V1b", "applied over specific lobule only"],
        ["CB_VII", "applied over specific lobule only"],
        ["CB_VIII", "applied over specific lobule only"],
        ["CB_Sim", "applied over specific lobule only"],
        ["CB_CrI", "applied over specific lobule only"],
        ["CB_CrII", "applied over specific lobule only"],
        ["CB_PM", "applied over specific lobule only"],
        ["other", "other area; add notes"],
    ]


@schema
class OptogeneticsTiming(dj.Lookup):
    definition = """  # timing of the optogenetics in joystick tasks only

    opto_timing_name          : varchar(20)     # short name for the timing
    -----
    opto_timing_details = ''  : varchar(2048)   # details about timing
    """
    contents = [
        ["none", ""],
        ["withFF_100ms", "with the force field, for 100 ms"],
        ["50ms_delay", "50 ms after forcefield onset, but on for 100 ms"],
        ["100_ms", "100 ms from the start of the pull"],
        ["200_ms", "200 ms from the start of the pull"],
    ]


@schema
class OptogeneticsVariant(dj.Lookup):
    definition = """  # Type of expressed channel
    opto_variant_name          : char(10)       # optogenetic variant short name
    -----
    opto_variant_details = ''  : varchar(2048)  # details about the variant
    """
    contents = [
        ["none", "no optogentics used"],
        ["ChR2", "ChR2 to activate neurons with 473 nM light"],
        [
            "ReaChR",
            "red-shfted variant of ChR2 that is best with 590 nm light",
        ],
        ["590np", "nano-particle (currently under development)"],
    ]


@schema
class Optogenetics(dj.Lookup):
    definition = """  # Optogenetics used in the session

    opto_name     : char(128)   # optogenetic protocoll abbreviation
    -----
    pulse_frequency    : double      # Pulse frequency in Hz
    pulse_length       : double      # Pulse length in ms
    laser_power        : double      # Input power at laser tip in mW
    -> OptogeneticsRegion
    -> OptogeneticsTiming
    -> OptogeneticsVariant
    """
    contents = [
        ["none", -1, -1, -1, "none", "none", "none"],
        ["Mathis2017", 50, 5, 8, "S1", "withFF_100ms", "ChR2"],
    ]


@schema
class ForceField(dj.Lookup):
    # Information about the task.
    definition = """  # Details about the used force field
    force_field_name  : varchar(100)      # short name of the perturbation
    ---
    strength          : double            # Volts applied from Ni-DAQ in V, -1 means variable force field, check experimental file
    details = ''      : varchar(2048)     # detailed description

    """
    contents = [
        ["pulsed_100ms", 2.2, "100 ms pulsed onset perturbation"],
        ["pulsed_50ms", 2.2, "100 ms pulsed onset perturbation"],
        ["pulsed_30ms", 2.2, "100 ms pulsed onset perturbation"],
        ["velocity_1", 2.2, "pre-calculated standard velocity profile"],
        [
            "delayed_onset_velocity_1",
            2.2,
            "same delay as above with a pre-calculated standard velocity profile",
        ],
        ["none", -1, "no force-field applied"],
    ]


@schema
class Task(dj.Lookup):
    # Information about the task.
    definition = """  # Information about the performed task
    task_name          : char(100)
    ---
    task_details = ''  : varchar(2048)
    """

    __joystick_tasks = [
        ["task1", "75 baseline trials, 100 perturbation trials, 75 washout"],
        [
            "task2",
            "75 baseline trials, 100 perturbation+boundary crossing at 2.2=rew trials 75, washout with "
            "boundary crossing at 2.2=rew",
        ],
        [
            "task3",
            "75 baseline trials, 100 perturbation trials 75, washout with boundary crossing at 2.2=rew",
        ],
        [
            "task4",
            "75 baseline trials, 100 box shifted right by 80%,  75 washout",
        ],
        [
            "task5",
            "75 baseline trials, 100 perturbation trials+righward box open, 75 washout",
        ],
        ["10prob_pert", "10 Percent probabilistic force field of 100 ms"],
        ["20prob_pert", "10 Percent robabilistic force field of 100 ms"],
        ["baseline", "standard target box task"],
        ["training_day", "standard target box task"],
        ["training_velocity", "training with velocity threshold for reward"],
        [
            "training_2.3_baseline",
            "training on short distance pull with position-dependent rewards",
        ],
        [
            "training_2.2_baseline",
            "training on full distance pull with position-dependent rewards",
        ],
    ]
    __passive_timing_tasks = [
        ["passive_timing", "water delivered at random intervals"]
    ]
    __active_timing_tasks = [
        [
            "active_timing",
            "differential reinforcement of low response rate task",
        ]
    ]
    __mouse_track_tasks = [["mouse_track", "virtualy reality wheels task"]]
    __split_belt_tasks = [["splitBelt", "split belt treadmill task"]]

    contents = [
        *__joystick_tasks,
        *__passive_timing_tasks,
        *__active_timing_tasks,
        ["wheel_training", "training to run on two-wheel system"],
        *__mouse_track_tasks,
        *__split_belt_tasks,
    ]

    __pipeline_to_tasks = {
        "joystick": __joystick_tasks,
        "passive_timing": __passive_timing_tasks,
        "active_timing": __active_timing_tasks,
        "mouse_track": __mouse_track_tasks,
        "split_belt": __split_belt_tasks,
    }

    @classmethod
    def get_pipeline_task_names(cls, pipeline_name):
        return [task[0] for task in cls.__pipeline_to_tasks[pipeline_name]]


@schema
class Joystick(dj.Lookup):
    definition = """   # Used joystick in the experiment
    joystick_name          : varchar(100)    # unique short name of the joystick
    ---
    joystick_details = ''  : varchar(2048)
    """
    contents = [
        ["classical", "original base is fixed design (metal handle)"],
        ["2D_axis", "2 axis force perturbation"],
        ["none", "no joystick used in this session"],
    ]


@schema
class Session(dj.Manual):
    # Information about the session, rigs etc.
    definition = """ # Experimental session
    -> mice.Mouse
    day       : int       # days after start of the experiment
    attempt   : int       # counter for sessions on same day (usually 1)
    ---
    doe : date          # date of the Session
    session_increment  : int           # counter of consecutive sessions for each mouse (manually)
    -> Rig              # links to the tables defining details of the session
    -> Experimenter
    -> Anesthesia
    -> Optogenetics
    -> Task
    -> ForceField
    -> Joystick
    session_notes = ""              : varchar(4095)       # free-text notes
    session_ts = CURRENT_TIMESTAMP  : timestamp           # automatic
    """

    @classmethod
    def get_sessions_for_pipeline(cls, pipeline_name):
        return cls & [
            "task_name = '{}'".format(task)
            for task in Task.get_pipeline_task_names(pipeline_name)
        ]


@schema
class RawBehavior(dj.Manual):
    definition = """   # Stores the file names of the behavioral data
    -> Session
    ---
    joystick_path   : varchar(256)    #labVIEW binary file
    reward_path     : varchar(256)    #labVIEW binary file
    trial_path      : varchar(256)    #labVIEW binary file
    trial_timing_path = None : varchar(256) #labVIEW binary file for trial timing
    """


@schema
class RawBehaviorPickle(dj.Manual):
    definition = """ # Stores file path for behavioral data
    -> Session
    ---
    raw_behavior_path : varchar(256)     # pickle file (contains python dictionary)
    """


@schema
class RawVideo(dj.Manual):
    definition = """  # Stores the file names of the raw videos of the recording
    -> Session
    camera_id     : int      # Camera number (corresponding to the camera)
    part_id       : int      # number of the video part (starts with 0, continious video seperated into parts to have smaller video files)
    ---
    video_path   : varchar(256)    # .avi videos synced to labVIEW files
    camera1_timing_path = None : varchar(256) #labVIEW binary file for the path of camera 1 timing
    camera2_timing_path = None : varchar(256) #labVIEW binary file for the path of camera 2 timing
    behavior_timestamps_path=None: varchar(256) # Numpy timestamps from behavior task to camera
    camera_timestamps_path=None: varchar(256) # Numpy Camera timestamps
    camera_calibration_path=None: varchar(256) # Path of the camera calibration image
    """


@schema
class RawExperimentInfo(dj.Manual):
    definition = """  # Stores file with experimental parameters
     -> Session
     ---
     experiment_path            : varchar(256)    # TODO: add details about format of files
     original_file_name = None  : varchar(256)    # File name of the experiment info file that was selected in the GUI. Note: the file was renamed when transfered to the server.

     """
