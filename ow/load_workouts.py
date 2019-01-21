import os

from fitparse.utils import FitHeaderError

from ow.utilities import create_blob
from ow.models.workout import Workout


def get_files(path, extension):
    """
    Given a path and a file extension, return a list of full-path strings
    pointing to files found with such extension
    """
    files = []
    for f in os.listdir(path):
        if f.endswith(extension):
            files.append(os.path.join(path, f))
    return files


def load_workouts(user, paths, extension='fit'):
    """
    Load workouts from the given path, looking for files with the given
    extension (only fit and gpx files supported so far)
    """
    for path in paths:
        print('Loading from path:', path)
        files = get_files(path, extension)
        for file_path in files:
            if extension == 'fit':
                print(' Loading file:', file_path)
                with open(file_path, 'rb') as f_obj:
                    fit_blob = create_blob(
                        f_obj.read(), file_extension=extension, binary=True)
            elif extension == 'gpx':
                print(' Loading file:', file_path)
                with open(file_path, 'r') as f_obj:
                    fit_blob = create_blob(
                        f_obj.read(), file_extension=extension)
            workout = Workout()
            workout.tracking_file = fit_blob
            workout.tracking_filetype = extension
            try:
                workout.load_from_file()
            except FitHeaderError:
                print('  ERROR LOADING WORKOUT  ')
            else:
                # add the workout only if no errors happened
                user.add_workout(workout)
