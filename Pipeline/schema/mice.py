"""Schema for mouse related information."""

import os
import pathlib

import datajoint as dj
import PIL.Image
import schema.utils.datastore as datastore

schema = dj.schema("mice", locals(), create_tables=True)

datastore.add_store(
    key="surgery_images",
    value={
        "protocol": "file",
        "location": os.path.expanduser("~"),
    },
)


@schema
class Strain(dj.Lookup):
    definition = """    # Genetic type of the mouse
    strain          : char(128) # mouse variant short name
    ---
    formal_name     : varchar(2048)
    stock_number    : varchar(255)

    """
    contents = [
        ["WT", "C57B/6J", "na"],
        ["TetO-GCamP6s", "B6:DBA-Tg(tetO-GCaMP6s)2Niell/J", "024742"],
        ["Piezo-cre", "B6(SJL)-Piezo<tm1.1(cre)Apat>/J", "027719"],
        [
            "Thy1-jRGECO1a-8.31",
            "C57BL/6J-Tg(Thy1-jRGECO1a)GP8.31DKim/J",
            "030526",
        ],
        ["-ReaChR", "B6;129S-Gt(ROSA)26Sor<tm2.11Ksvo>/J", "024846"],
        ["CamK2a-tTa", "B6.Cg-Tg(Camk2a-tTa)1Mmay/DboJ", "007004"],
        ["CamK2a-tTa-TetO-GCamP6s", "024742x007004", "inhouse"],
        ["Piezo-ReaChR", "027719x024846", "inhouse"],
        ["L7-cre", "B6.129-Tg(Pcp2-cre)2Mpin/J", "004146"],
        ["L7-ReaChR", "004146x024846", "in house"],
        ["piezo-cre-TetO-GCamP6s", "024742x027719", "in house"],
        [
            "CamK2a-tTa-TetO-GCamP6s-ReaChR",
            "inhouse(024742x007004)x024846",
            "in house",
        ],
        ["Pvalb-cre", "Pvalb-2A-Cre-D (PV-2A-Cre-D)", "012358"],
        ["Pvalb-cre-TetO-GCamP6s", "012358x024742", "in house"],
        ["VGAT-ChR2", "B6.Cg-Tg(Slc32a1-COP4*H134R/EYFP)8Gfng/J", "014548"],
        ["Pvalb-cre-ReaChR", "012358x024846", "in house"],
        ["Pvalb-cre-TetO-GCamP6s", "024742x012358", "in house"],
        [
            "Pvalb-cre-TetO-GCamP6s-ReaChR",
            "inhouse(024742x012358)x024846",
            "in house",
        ],
        ["Pvalb-FlpO", "B6.Cg-Pvalbtm4.1(flpo)Hze/J", "022730"],
        ["Pvalb-FlpO-ReaChR", "022730x024846", "in house"],
        [
            "Pvalb-FlpO-Piezo-cre-ReaChR",
            "inhouse(027719x024846)x022730",
            "in house",
        ],
        ["Pvalb-FlpO-Piezo-cre", "027719x022730", "in house"],
        ["Thy1-GCaMP6s-4.3", "C57BL/6J-Tg(Thy1-GCaMP6s)GP4/3DKim/J", "24275"],
        ["slc17a7-ai148", "023527x030328", "in house"],
        ["ai148", "Ai148(TIT2L-GC6f-ICL-tTA2)-D", "030328"],
        ["Scnn1a-ai148", "009613x030328", "in house"],
        ["Scnn1a-cre", "B6;C3-Tg(Scnn1a-cre)3Aibs/J", "009613"],
        ["Vglut2-cre", "Slc17a6tm2(cre)Lowl", "016963"],
        ["Vglut2-ai148", "016963x030328", "in house"],
        ["VGAT-ReaChR", "028862x024846", "in house"],
    ]


@schema
class Mouse(dj.Manual):
    definition = """ # Basic information about the Mouse
      mouse_name    : varchar(128)             # name of mouse (unique)
      ---
      mouse_id      : int                      # unique mouse id, ATTENTION: take care that this is really unique
      dob           : date                     # day of birth (year-month-day)
      sex           : enum('M', 'F', 'U')      # sex of mouse - Male, Female, or Unknown/Unclassified
      -> Strain                                # link to the genetic type of the mouse
      """

    def get_starting_date(self):
        """Returns the date of the first session if present, else returns none.

        This method searches through all sessions for the given mouse
        and returns the date of the first session that was performed

        Input:
              self        A query that relates to one mouse, else error is thrown
        Output:
              date        The date of the first session as object of datetime.datetime
                          If no session has been performed, returns none
        """
        # Check if self corresponds only to a single mouse
        if len(self) != 1:
            raise Exception(
                "Query resulted in %i mice! Only 1 result allowed..."
                % len(self)
            )

        from . import (
            exp,
        )

        # be imported before it is created

        daysOfExperiments = (exp.Session() & self).fetch("doe")
        startDate = (
            min(daysOfExperiments) if len(daysOfExperiments) > 0 else None
        )

        return startDate

    def get_current_day(self):
        """Returns the day since start of the training for a single mouseID.

        This method calculates the difference in days between the first session
        and the current date and adds one.

        Input:
              self        Query for a single mouse
        Output:
              day         Integer of the current day since the training started
                          None returned if no experiment was done before
        """
        startDate = self.get_starting_date()
        if startDate is None:
            return 1

        import datetime

        dateToday = datetime.date.today()
        return (dateToday - startDate).days + 1

    def get_session_increment(self):
        """Returns the incrementing number for the sessions.

        This method searches through all sessions for the given mouse
        and returns the new incrementing value for the sessions

        Input:
              self                   A query that relates to one mouse, else error is thrown
        Output:
              session_increment      Integer, starts with 0 to number
        """
        # Check if self corresponds only to a single mouse
        if len(self) != 1:
            raise Exception(
                "Query resulted in %i mice! Only 1 result allowed..."
                % len(self)
            )

        from . import exp  # import here, reason see get_starting_date

        sessionNumbers = (exp.Session() & self).fetch("session_increment")
        if len(sessionNumbers) > 0:
            return max(sessionNumbers) + 1
        else:
            return 0


@schema
class SurgeryType(dj.Lookup):
    definition = """  # Genetic type of the mouse
    surgery_type    : varchar(128) # surgery short name
    ---
    """
    contents = [
        ["injection craniotomy"],
        ["7 mm craniotomy"],
        ["5 mm craniotomy"],
        ["3 mm craniotomy"],
        ["custom craniotomy"],
        ["D window craniotomy"],
        ["other shape or size"],
        ["headplate only"],
        ["tetrode implant"],
        ["optical fibers"],
    ]


@schema
class Surgery(dj.Manual):
    definition = """ # Details about the surgery
    -> Mouse
    ---
    -> SurgeryType                     # link to type of surgery
    surgery_details     : varchar(1024)   # descritpion of the aim of the surgery
    surgery_date  : varchar(256) # date of the surgery
    surgery_image  : longblob # path of the surgery image
    """


@schema
class SurgeryImage(dj.Computed):
    """Surgery images retrievable via filepath attributes.

    Different to mice.Surgery, this table will contain the surgery image
    stored using the filetype attribute. This allows to retrieve the image
    on any host machine.

    Please do not reference this table in downstream tables, and keep referencing
    mice.Surgery instead.
    """

    definition = """ # Surgery images
    -> Mouse
    -> SurgeryType
    ---
    surgery_image  : attach@surgery_images # path of the surgery image
    """

    @property
    def key_source(self):
        return Mouse

    def make(self, key):
        """Populate the table with all available surgery images in mice.Surgery."""
        query = Surgery() & key
        for entry in query.fetch(
            "surgery_type", "surgery_image", as_dict=True
        ):
            if entry["surgery_image"] is None:
                # print(f'Did not find a surgery image for {key}. Skipping.')
                continue
            (fname,) = entry["surgery_image"]
            fname = pathlib.Path(fname)
            if not fname.exists():
                # print(f'Found an entry for {key}, but the path is not available locally: {fname}')
                continue
            # print(f'Populate {key} with {fname}')
            self.insert1(
                dict(
                    **key,
                    surgery_type=entry["surgery_type"],
                    surgery_image=str(fname),
                )
            )

    def fetch_image(self, name: str) -> "PIL.Image":
        """Load and return the surgery image as a PIL.Image object.

        name can be the mouse name, or a query dictionary. The
        query should correspond to a unique entry in the table.
        """
        if isinstance(name, str):
            name = dict(mouse_name=name)
        path = (self & name).fetch1("surgery_image")
        with open(path, "rb") as fh:
            image = PIL.Image.open(fh).convert("RGB")
        return image


@schema
class SxDetails(dj.Manual):  # TODO: describe what this is
    definition = """
    -> Mouse
    ---
    comments : varchar(2048)        # comments about the sx prep
    """


@schema
class Sacrificed(dj.Manual):
    definition = """ # table to keep the record for sacrifice.Also, not to show in the dropdown menu!
    -> Mouse
    ---
    date_of_sacrifice   : datetime      # date of sacrifice
    reason              : varchar(2048) # comments about the reason of sacrifice
    """


@schema
class Breed(dj.Manual):
    definition = """ # table to keep the record for breeding. Also, not to show in the dropdown menu!
    -> Mouse
    ---
    """


@schema
class MouseLicensingGeneva(dj.Lookup):
    definition = """ #table to log the animals license
    license   : varchar(128) # licensing name
    ---
    informal_title     : varchar(2048)
    """
    contents = [
        ["GE10", "locomotor learning and VR"],
        ["GE1", "nautral animal behavuor maus haus"],
        ["GE68", "joystick forelimb motor control"],
    ]


@schema
class MouseScoreSheet_BodyCondition(dj.Lookup):
    definition = """ #table to log the scorecard condition of the mice during active experimental times. If the data is not logged, the mouse is in stable condition
    body_condition   : varchar(128) # short body condition name
    ---
    define_score     : varchar(2048)
    """
    contents = [
        ["BodyCondition1", "emaciated"],
        ["BodyCondition2", "under-conditioned"],
        ["BodyCondition3", "well-conditioned"],
        ["BodyCondition4", "over-conditioned"],
        ["BodyCondition5", "5 obese"],
    ]


@schema
class MouseScoreSheet_GeneralAssay(dj.Lookup):
    definition = """ #table to log the scorecard condition of the mice during active experimental times. If the data is not logged, the mouse is in stable condition
    general_assay   : varchar(128) # general assay score name
    ---
    define_score     : varchar(2048)
    """
    contents = [
        ["Assay1", "1 or less euthanize cannot not aroused"],
        ["Assay2", "2 or less euthanize unable to rouse without large stim"],
        ["Assay3", "3 not groomed slow movements"],
        ["Assay4", "4 slightly lethargic"],
        ["Assay5", "5 normal behavior"],
    ]


@schema
class MouseScoreSheet_HousingAssesment(dj.Lookup):
    definition = """ #table to log the scorecard condition of the mice during active experimental times. If the data is not logged, the mouse is in stable condition
    housing_assay   : varchar(128) # general assay score name
    ---
    define_score     : varchar(2048)
    """
    contents = [
        ["Yes", "animal built housing as normal"],
        ["No", "watch animal for signs of stress"],
    ]


@schema
class MouseScoreSheet_WaterRestriction(dj.Manual):
    definition = """ #if water restricted, input the percentage change in weight from baseline
    -> Mouse
    doc : date          # date of check
    ---
    weight_percentage   :   varchar(128)   # percentage change from baseline
    """


@schema
class MouseScoreSheet(dj.Manual):
    definition = """ # Score sheet table with all the lookup information about the mouse health at date of check
    -> Mouse
    doc : date          # date of check
    ---
    -> MouseLicensingGeneva
    -> MouseScoreSheet_BodyCondition
    -> MouseScoreSheet_GeneralAssay
    -> MouseScoreSheet_HousingAssesment
    """
