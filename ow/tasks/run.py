import sys

from ow.tasks.manager import TasksManager
from ow.tasks.mail import queue_processor


def command_line():
    tasks_manager = TasksManager()

    # "register" the tasks
    tasks_manager.add_task('send_emails', queue_processor)

    if len(sys.argv) != 3:
        tasks_manager.usage(sys.argv[0])
        sys.exit(1)

    script_name = sys.argv[0]
    ini_file = sys.argv[1]
    action = sys.argv[2]

    tasks_manager.run(script_name, ini_file, action)


if __name__ == '__main__':
    command_line()  # pragma no cover
