class WorkFlowException(Exception):
    def __init__(self, workflow_exception):
        super(WorkFlowException, self).__init__(workflow_exception.msg)
        self.error_info = workflow_exception.msg
        self.error_code = workflow_exception.code

    def __str__(self):
        return self.error_info
