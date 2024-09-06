import datetime
import os
from vulcanus.log.log import LOGGER
from zeus.operation_service.app.settings import configuration
from zeus.operation_service.app.core.file_util import FileUtil



# def check_tasks():
#     LOG.warning("begin check_tasks")
#     try:
#         tasks = Task.objects.filter(status__in=[TaskResultCode.WAITING.code, TaskResultCode.RUNNING.code])
#         if len(tasks) > 0:
#             for task in tasks:
#                 LOG.warning(f"{task.name} status: {task.status}, set {task.name} status error code")
#                 task.status = TaskResultCode.SERVER_RESTART.code
#                 task.end_time = int(round(time.time() * 1000))
#                 task.save()
#         else:
#             LOG.warning("no task need to be set")
#     except Exception as e:
#         LOG.error(f"check_tasks error: {e}")


def dir_clean(dir_path):
    LOGGER.warning(f"begin check dir {dir_path}")
    date_now = datetime.datetime.now()
    if not os.path.exists(dir_path):
        return
    for task_result_file in os.listdir(dir_path):
        task_result_file_path = os.path.join(dir_path, task_result_file)
        task_result_file_stat = os.stat(task_result_file_path)

        # 计算文件修改时间
        stat_date = datetime.datetime.fromtimestamp(task_result_file_stat.st_mtime)
        keep_days = configuration.task.task_result_keep_time

        # 任务结果存放超过指定天数，则删除目录
        if (date_now - stat_date).days >= keep_days:
            LOGGER.warning(f"{task_result_file} keep over {keep_days}, deleted")
            if os.path.isdir(task_result_file_path):
                FileUtil.dir_remove(task_result_file_path)
    LOGGER.warning(f"check dir {dir_path} finished")



