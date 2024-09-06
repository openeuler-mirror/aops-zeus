import os
import shutil
import stat
import zipfile
from zeus.operation_service.app.core.framework.common.constant import FileSize
from vulcanus.log.log import LOGGER

U_RWX = stat.S_IRWXU
U_RW = stat.S_IRUSR | stat.S_IWUSR
U_RX = stat.S_IRUSR | stat.S_IXUSR
U_WX = stat.S_IWUSR | stat.S_IXUSR
U_READ = stat.S_IRUSR
U_WRITE = stat.S_IWUSR
U_EXEC = stat.S_IXUSR
G_RWX = stat.S_IRWXG
G_RW = stat.S_IRGRP | stat.S_IWGRP
G_RX = stat.S_IRGRP | stat.S_IXGRP
G_WX = stat.S_IWGRP | stat.S_IXGRP
G_READ = stat.S_IRGRP  # read by group
G_WRITE = stat.S_IWGRP  # write by group
G_EXEC = stat.S_IXGRP  # execute by group
O_RWX = stat.S_IRWXO  # mask for others (not in group) permissions
O_RW = stat.S_IROTH | stat.S_IWOTH
O_RX = stat.S_IROTH | stat.S_IXOTH
O_WX = stat.S_IWOTH | stat.S_IXOTH
O_READ = stat.S_IROTH  # read by others
O_WRITE = stat.S_IWOTH  # write by others
O_EXEC = stat.S_IXOTH  # execute by others


class FileUtil:

    @staticmethod
    def file_remove(file_path):
        if os.path.isfile(file_path):
            LOGGER.warning(f"remove file {file_path}")
            os.remove(file_path)

    @staticmethod
    def dir_remove(dir_path):
        if os.path.exists(dir_path):
            LOGGER.warning(f"remove dir {dir_path}")
            shutil.rmtree(dir_path)

    @staticmethod
    def rename(src, dst):
        if os.path.exists(dst):
            dst_name = os.path.basename(dst)
            raise Exception(dst_name + " existed")
        os.rename(src, dst)

    @staticmethod
    def seek_file(file_path: str, index: int, size: int = FileSize.READ_SIZE):
        """通过游标获取文件内容
            params:
                file_path: 读取的文件路径
                index: 指定的游标位置
                size: 读取的内容大小，默认为10240字节
            return:
                文件内容
        """
        with open(file_path, 'r', encoding='utf-8') as file_obj:
            file_obj.seek(index)
            return file_obj.read(size)

    @staticmethod
    def unzip(zip_path, unzip_path):
        """解压压缩包到指定路径
        params:
            zip_path: 压缩包路径
            unzip_path: 解压路径
        """
        LOGGER.warning(f"begin to unzip {os.path.basename(zip_path)}")
        with zipfile.ZipFile(zip_path, 'r') as f:
            f.extractall(unzip_path)
        LOGGER.info(f"{os.path.basename(zip_path)} unzip success")

    @staticmethod
    def zip_dir(dir_path, zip_path):
        """压缩目录
        params：
            dir_path: 待压缩的文件目录
            zip_path: 压缩文件保存路径（路径+xx.zip）
        """
        zip_file = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)
        for path, dirname, filenames in os.walk(dir_path):
            file_path = path.replace(dir_path, '')
            for filename in filenames:
                zip_file.write(os.path.join(path, filename), os.path.join(file_path, filename))
        zip_file.close()
