class TaskResult:
    def __init__(self, host, task, executor_result):
        self.host = host
        self.task = task
        self.result = executor_result


