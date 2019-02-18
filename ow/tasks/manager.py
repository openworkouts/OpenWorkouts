from pyramid.paster import bootstrap
from pyramid.paster import setup_logging


class TasksManager(object):

    def __init__(self):
        """
        managers is a dict containing all the available tasks. The keys are
        the name used to reference this tasks (the action parameter accepted
        on runtime) while the values are the functions/methods responsible to
        run the task.

        Those functions/methods have to expect one parameter (the environment
        we get from bootstraping pyramid, see the run() method to learn more)
        """
        self.managers = {}

    def usage(self, script_name):
        """
        Prints command line usage.

        The description of the different tasks is gathered from the docstring
        of the methods that will be called to perform the task.
        """
        docs = [t + ': ' + self.managers[t].__doc__ for t in self.managers]
        msg = """
        Usage: %s /path/to/settings.ini [%s]

          settings.ini has to be a PasteDeploy .ini file representing your
          application configuration.

          %s

        """ % (script_name, '|'.join(self.managers), '\n\t  '.join(docs))
        print(msg)

    def add_task(self, name, method):
        self.managers[name] = method

    def remove_task(self, name):
        if name in self.managers:
            del self.managers[name]

    def run(self, script_name, ini_file, action):
        env = bootstrap(ini_file)
        setup_logging(ini_file)
        if action not in self.managers.keys():
            self.usage(script_name)
        else:
            self.managers[action](env)
        env['closer']()
