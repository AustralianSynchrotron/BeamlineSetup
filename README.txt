                         / BeamlineSetup /

                 A modular Python application to guide beamline staff through
                 the morning beamline setup procedure on the macromolecular
                 crystallography beamlines at the Australian Synchrotron.


    ~ What are the various modules?

      * beamline_setup.py - creates a WX python GUI with buttons for running the
                   various other modules arranged in a manner to guide a staff
                   member through a logical workflow. Next to the buttons are
                   indicators giving feedback on whether the function has been run.

      * AlignBeam.py - Staff align beam manually on a fluorescing crystal (YAG) at the
                   sample position. Module captures image of the beam on sample, closes
                   shutter and takes an image of the beam on a second crystal at the
                   shutter that is used for beam steering on the beamlines. Images are
                   montaged together and saved with date stamps in a calibration directory.

      * BeamCentre.py - Takes a series of diffraction images from a lanthanum hexaborate
                   powder sample and using Fit2d calculates the direct beam position, the
                   detector distance, pitch and yaw. Straight line fits are made relating
                   distance and the direct beam position in X and Y. These formulae will be
                   used to calculate the direct beam position in the image header records.
                   The user is prompted to correct distance, pitch and yaw.

      * CreateDirs.py - Calibration results will be saved into folders in the home directory
                   of the current user. This script sets up the directory structure and would
                   be run prior to the other scripts.

      * CryoJet.py - Alignment of the cryojet and checking that temperature and flow settings
                   are largely manual but the scripts prompts the staff member with a small
                   GUI for entering the set points and logging the time that the last check was
                   done.

      * FormatReport.py - Formats an HTML report with embedded images describing for the user
                   how and when the beamline was setup and calibrated with up to date values.
                   The report is saved to the users calibration directories and also pushed to
                   an online electronic log book.

      * MakeComment.py - Small module that opens a simple text entry box allowing the staff member
                   doing the setup to log comments about issues they encountered when setting up the
                   beamline. The comments are pushed to the electronic log book with the HTML report
                   but not saved to the users directory.

      * RotationAxis.py - This is a highly automated procedure that rotates the rotation axis through
                   270 degrees taking images every 90 degrees. The images are analysed to determine
                   where the rotation axis is with respect to the cross-hairs on the sample camera and
                   the height of the rotation axis is appropriately corrected.

      * SetUp.py - Some simple functions that are called when the script is run to get the beamline
                   passwords etc.

      * Snapshot.py - Uses epics channel access to harvest most of the process variables defining the
                   current state of the beamlines and archives these.

      * TestCrystal.py - Prompts staff through steps to collect data from a standard protein crystal.
                   The script communicates with the automated data processing running on the beamlines
                   to wait for processing to finish. Harvest relevant statistics and format these for
                   the calibration report.

    ~ What are the dependencies?

      * Control of the beamlines is based on EPICS for low level controls and a mixture of EPICS sequencers,
        third party DHS and in-house Python daemons for higher level functions. A python 'beamline library'
        is called in the script that defines various parameters. A redis database holds variables to allow
        persistence across sessions. Imagemagick is used for image analysis. WX is used to create GUIs and
        dialogs. Maths, curve fitting and graphing is performed using Scipy, Numpy and matplotlib.
