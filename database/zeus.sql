CREATE DATABASE IF NOT EXISTS aops DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_bin;
use aops;

CREATE TABLE IF NOT EXISTS `user` (
  `username` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `email` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  PRIMARY KEY (`username`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `auth`  (
  `auth_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `auth_account` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `nick_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `auth_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `username` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  PRIMARY KEY (`auth_id`) USING BTREE,
  INDEX `username`(`username`) USING BTREE,
  CONSTRAINT `auth_ibfk_1` FOREIGN KEY (`username`) REFERENCES `user` (`username`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `host_group`  (
  `host_group_id` int(11) NOT NULL AUTO_INCREMENT,
  `host_group_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `description` varchar(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `username` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  PRIMARY KEY (`host_group_id`) USING BTREE,
  INDEX `username`(`username`) USING BTREE,
  CONSTRAINT `host_group_ibfk_1` FOREIGN KEY (`username`) REFERENCES `user` (`username`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Dynamic;

CREATE TABLE IF NOT EXISTS `host`  (
  `host_id` int(11) NOT NULL AUTO_INCREMENT,
  `host_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `host_ip` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `management` tinyint(1) NOT NULL,
  `host_group_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `repo_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `last_scan` int(11) NULL DEFAULT NULL,
  `scene` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `os_version` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `ssh_user` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `ssh_port` int(11) NULL DEFAULT NULL,
  `pkey` varchar(4096) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `status` int(11) NULL DEFAULT NULL,
  `user` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL DEFAULT NULL,
  `host_group_id` int(11) NULL DEFAULT NULL,
  PRIMARY KEY (`host_id`) USING BTREE,
  INDEX `user`(`user`) USING BTREE,
  INDEX `host_group_id`(`host_group_id`) USING BTREE,
  CONSTRAINT `host_ibfk_1` FOREIGN KEY (`user`) REFERENCES `user` (`username`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `host_ibfk_2` FOREIGN KEY (`host_group_id`) REFERENCES `host_group` (`host_group_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Dynamic;

INSERT INTO `user` (`username`, `password`) VALUE('admin', 'pbkdf2:sha256:150000$h1oaTY7K$5b1ff300a896f6f373928294fd8bac8ed6d2a1d6a7c5ea2d2ccd2075e6177896') ON DUPLICATE KEY UPDATE username= 'admin',password='pbkdf2:sha256:150000$h1oaTY7K$5b1ff300a896f6f373928294fd8bac8ed6d2a1d6a7c5ea2d2ccd2075e6177896';