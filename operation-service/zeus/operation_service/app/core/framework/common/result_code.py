from zeus.operation_service.app.constant import ResultCodeEnum


class PluginResultCode(ResultCodeEnum):
    """
    插件错误码枚举类
    """
    SUCCESS = (1000, '成功')
    ERROR = (1001, '错误')
    FAILED = (1002, '失败')
    PARTIAL_PASSED = (1003, '部分通过')
    PRE_DEPENDENCY_ERROR = (1004, '前置依赖报错')

    UNKNOWN = (1005, '未知异常')


class TaskResultCode(ResultCodeEnum):
    """
    任务状态码
    """
    SUCCESS = (200, '成功')
    RUNNABLE = (201, '就绪')
    RUNNING = (202, '执行中')
    PAUSE = (203, '暂停')
    CANCELED = (204, '已取消')
    PARTIAL_PASSED = (206, '部分成功')
    TIMEOUT = (207, '超时')
    WAITING = (208, '等待')
    NO_DATA_REPORTED = (209, '数据上报失败')
    FAILED = (400, '失败')
    SERVER_RESTART = (401, '服务重启')
    RECOVER = (402, '待加固')
    UNKNOWN = (600, '异常')


class ItemResultCode(ResultCodeEnum):
    """
    任务项状态码
    """
    ITEM_SUCCESS = (0, '成功')
    ITEM_FAILED = (1, '失败')
    ITEM_RECOVER = (5, '待加固')
    ITEM_TIMEOUT = (101, '执行超时')
    ITEM_EXCEPTION = (102, '执行异常')


class WorkFlowResultCode(ResultCodeEnum):
    """
    任务流错误码枚举类
    """
    SUCCESS = (4001001, "task successfully")
    NORMAL = (4001002, "workflow running")

    ERR_WORKFLOW_PARSE = (4002001, "workflow parse error")
    ERR_WORKFLOW_JOB_NAME = (4002002, "job name error, should not be null")
    ERR_WORKFLOW_HOST_NAME = (4002003, "host name error, should not be null")
    ERR_WORKFLOW_STEPS_NULL = (4002004, "steps error, should not be null")
    ERR_WORKFLOW_TIMEOUT = (4002005, "workflow execute timeout")
    ERR_WORKFLOW_EXECUTE = (4002006, "workflow run error")
    ERR_WORKFLOW_CIRCLE = (4002007, "workflow relation circle")

    ERR_UNKNOWN = (4002999, 'Unknown error in Asset')


class RunningTaskResultCode(ResultCodeEnum):

    ERR_NO_DATA_REPORTED = (1010012001, "No data reported")
    ERR_INVALID_TASK_RESULT_DATA = (1010012002, "An inspection item of a specific task contains multiple results.")
