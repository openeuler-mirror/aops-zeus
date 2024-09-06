
class TaskException(Exception):
    def __init__(self, result_code):
        super().__init__(result_code.msg)
        self.msg = result_code.msg
        self.code = result_code.code

    def __str__(self):
        return self.msg

# def task_exception_handler(message):
#     def decorate(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             try:
#                 func_response = func(*args, **kwargs)
#             except TaskException as task_exception:
#                 return Response(build_response(task_exception, {}))
#             except Exception as e:
#                 LOG.error(f"{message} failed,{e}")
#                 return Response(build_response(TaskOperationResultCode.ERR_UNKNOWN, {}))
#             else:
#                 return func_response

#         return wrapper

#     return decorate