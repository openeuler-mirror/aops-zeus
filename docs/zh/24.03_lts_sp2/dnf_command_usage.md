# dnf插件命令使用手册

将dnf-hotpatch-plugin安装部署完成后，可使用dnf命令调用A-ops ceres中的冷/热补丁操作，命令包含热补丁扫描（dnf hot-updateinfo），热补丁状态设置及查询（dnf hotpatch ），热补丁应用（dnf hotupgrade），内核升级前kabi检查（dnf upgrade-en）。本文将介绍上述命令的具体使用方法。

>热补丁包括ACC/SGL（accumulate/single）类型
>
>- ACC：增量补丁。目标高版本热补丁包含低版本热补丁所修复问题。
>- SGL_xxx：单独补丁，xxx为issue id，如果有多个issue id，用多个'_'拼接。目标修复issue id相关问题。

## 热补丁扫描

`dnf hot-updateinfo`命令支持扫描热补丁并指定cve查询相关热补丁，命令使用方式如下：

```shell
dnf hot-updateinfo list cves [--available(default) | --installed] [--cve [cve_id]] 

General DNF options:
  -h, --help, --help-cmd
                        show command help
  --cve CVES, --cves CVES
                        Include packages needed to fix the given CVE, in updates
Hot-updateinfo command-specific options:                     
  --available          
                        cves about newer versions of installed packages
                        (default)
  --installed
                        cves about equal and older versions of installed packages
```

- `list cves`

1、查询主机所有可修复的cve和对应的冷/热补丁。

```shell
[root@localhost ~]# dnf hot-updateinfo list cves
# cve-id   level    cold-patch   hot-patch
Last metadata expiration check: 2:39:04 ago on 2023年12月29日 星期五 07时45分02秒.
CVE-2022-30594  Important/Sec. kernel-4.19.90-2206.1.0.0153.oe1.x86_64                        patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
CVE-2023-1111   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2023-1112   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2023-1111   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-SGL_CVE_2023_1111_CVE_2023_1112-1-1.x86_64
```

2、查询主机所有已修复的cve和对应的冷/热补丁

```shell
[root@localhost ~]# dnf hot-updateinfo list cves --installed
# cve-id   level    cold-patch   hot-patch
Last metadata expiration check: 2:39:04 ago on 2023年12月29日 星期五 07时45分02秒.
CVE-2022-36298  Important/Sec. -      patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_36298-1-1.x86_64
```

2、指定cve查询对应的可修复冷/热补丁。

```shell
[root@localhost ~]# dnf hot-updateinfo list cves --cve CVE-2022-30594
# cve-id   level    cold-patch   hot-patch
Last metadata expiration check: 2:39:04 ago on 2023年12月29日 星期五 07时45分02秒.
CVE-2022-30594 Important/Sec. kernel-4.19.90-2206.1.0.0153.oe1.x86_64       patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
```

3、cve不存在时列表为空。

```shell
[root@localhost ~]# dnf hot-updateinfo list cves --cve CVE-2022-3089
# cve-id   level    cold-patch   hot-patch
Last metadata expiration check: 2:39:04 ago on 2023年12月29日 星期五 07时45分02秒.
```

## 热补丁状态及转换图

- 热补丁状态图

  NOT-APPLIED: 热补丁尚未应用。

  DEACTIVED: 热补丁未被激活。

  ACTIVED: 热补丁已被激活。

  ACCEPTED: 热补丁已被激活，后续重启后会被自动应用激活。

  ![热补丁状态转换图](./figures/syscare热补丁状态图.png)

## 热补丁状态查询和切换

`dnf hotpatch`命令支持查询、切换热补丁的状态，命令使用方式如下：

```shell
dnf hotpatch 

General DNF options:
  -h, --help, --help-cmd
                        show command help
  --cve CVES, --cves CVES
                        Include packages needed to fix the given CVE, in updates

Hotpatch command-specific options:
  --list [{cve, cves}]  show list of hotpatch
  --apply APPLY_NAME apply hotpatch
  --remove REMOVE_NAME remove hotpatch
  --active ACTIVE_NAME active hotpatch
  --deactive DEACTIVE_NAME
                       deactive hotpatch
  --accept ACCEPT_NAME accept hotpatch
```

- 使用`dnf hotpatch`命令查询热补丁状态

  - 使用`dnf hotpatch --list`命令查询当前系统中可使用的热补丁状态并展示。

  ```shell
  [root@localhost ~]# dnf hotpatch --list
  Last metadata expiration check: 0:09:25 ago on 2023年12月29日 星期五 10时26分45秒.
  base-pkg/hotpatch                                               status
  kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
  ```

  - 使用`dnf hotpatch --list cves`查询漏洞（CVE-id）对应热补丁及其状态并展示。

  ```shell
  [root@openEuler ~]# dnf hotpatch --list cves
  Last metadata expiration check: 0:11:05 ago on 2023年12月29日 星期五 10时26分45秒.
  CVE-id         base-pkg/hotpatch                                               status
  CVE-2022-30594 kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
  ```

  - `dnf hotpatch --list cves --cve <CVE-id>`筛选指定CVE对应的热补丁及其状态并展示。

  ```shell
  [root@openEuler ~]# dnf hotpatch --list cves --cve CVE-2022-30594
  Last metadata expiration check: 0:12:25 ago on 2023年12月29日 星期五 10时26分45秒.
  CVE-id         base-pkg/hotpatch                                               status
  CVE-2022-30594 kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
  ```

  - 使用`dnf hotpatch --list cves --cve <CVE-id>`查询无结果时展示为空。

  ```shell
  [root@openEuler ~]# dnf hotpatch --list cves --cve CVE-2023-1
  Last metadata expiration check: 0:13:11 ago on 2023年12月29日 星期五 10时26分45秒.
  ```

- 使用`dnf hotpatch --apply <patch name>`命令应用热补丁，可使用 `dnf hotpatch --list`查询应用后的状态变化，变化逻辑见上文的热补丁状态转换图。

```shell
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:13:55 ago on 2023年12月29日 星期五 10时26分45秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
[root@openEuler ~]# dnf hotpatch --apply kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
Last metadata expiration check: 0:15:37 ago on 2023年12月29日 星期五 10时26分45秒.
Gonna apply this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
apply hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:16:20 ago on 2023年12月29日 星期五 10时26分45秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACTIVED
```

- 使用`dnf hotpatch --deactive <patch name>`停用热补丁，可使用`dnf hotpatch --list`查询停用后的状态变化，变化逻辑见上文的热补丁状态转换图。

```shell
[root@openEuler ~]# dnf hotpatch --deactive kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
Last metadata expiration check: 0:19:00 ago on 2023年12月29日 星期五 10时26分45秒.
Gonna deactive this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
deactive hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:19:12 ago on 2023年12月29日 星期五 10时26分45秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux DEACTIVED
```

- 使用`dnf hotpatch --remove <patch name>`删除热补丁，可使用`dnf hotpatch --list`查询删除后的状态变化，变化逻辑见上文的热补丁状态转换图。

```shell
[root@openEuler ~]# dnf hotpatch --remove kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
Last metadata expiration check: 0:20:12 ago on 2023年12月29日 星期五 10时26分45秒.
Gonna remove this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
remove hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:20:23 ago on 2023年12月29日 星期五 10时26分45秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
```

- 使用`dnf hotpatch --active <patch name>`激活热补丁，可使用`dnf hotpatch --list`查询激活后的状态变化，变化逻辑见上文的热补丁状态转换图。

```shell
[root@openEuler ~]# dnf hotpatch --active kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
Last metadata expiration check: 0:15:37 ago on 2023年12月29日 星期五 10时26分45秒.
Gonna active this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
active hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:16:20 ago on 2023年12月29日 星期五 10时26分45秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACTIVED
```

- 使用`dnf hotpatch --accept <patch name>`接收热补丁，可使用`dnf hotpatch --list`查询接收后的状态变化，变化逻辑见上文的热补丁状态转换图。

```shell
[root@openEuler ~]# dnf hotpatch --accept kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
Last metadata expiration check: 0:14:19 ago on 2023年12月29日 星期五 10时47分38秒.
Gonna accept this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
accept hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:14:34 ago on 2023年12月29日 星期五 10时47分38秒.
base-pkg/hotpatch                                               status
kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACCEPTED
```

## 热补丁应用

`hotupgrade`命令根据cve id和热补丁名称进行热补丁修复，同时也支持全量修复。命令使用方式如下：

```shell
dnf hotupgrade [--cve [cve_id]] [PACKAGE ...] [--takeover] [-f]

General DNF options:
  -h, --help, --help-cmd
                        show command help
  --cve CVES, --cves CVES
                        Include packages needed to fix the given CVE, in updates
 
command-specific options:
  --takeover            
                        kernel cold patch takeover operation
  -f
                        force retain kernel rpm package if kernel kabi check fails
  PACKAGE               
                        Package to upgrade
```

- 使用`dnf hotupgrade PACKAGE`安装目标热补丁。

  - 使用`dnf hotupgrade PACKAGE`安装目标热补丁

  ```shell
  [root@openEuler ~]# dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
  Last metadata expiration check: 0:26:25 ago on 2023年12月29日 星期五 10时47分38秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx(Install process)
  Complete!
  Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
  ```

  - 当目标热补丁已经应用激活，使用`dnf hotupgrade PACKAGE`安装目标热补丁

  ```shell
  [root@openEuler ~]# dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
  Last metadata expiration check: 0:28:35 ago on 2023年12月29日 星期五 10时47分38秒.
  The hotpatch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'vmlinux'
  Package patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 is already installed.
  Dependencies resolved.
  Nothing to do.
  Complete!
  ```

  - 使用`dnf hotupgrade PACKAGE`安装目标热补丁，自动卸载激活失败的热补丁。

  ```shell
  [root@openEuler ~]# dnf hotupgrade patch-redis-6.2.5-1-ACC-1-1.x86_64
  Last metadata expiration check: 0:30:30 ago on 2023年12月29日 星期五 10时47分38秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx(Install process)
  Complete!
  Apply hot patch failed: redis-6.2.5-1/ACC-1-1.
  Error: Operation failed
  
  Caused by:
      0. Transaction "Apply patch 'redis-6.2.5-1/ACC-1-1'" failed
      
      Caused by:
          Cannot match any patch named "redis-6.2.5-1/ACC-1-1"
  
  Gonna remove unsuccessfully activated hotpatch rpm.
  Remove package succeed: patch-redis-6.2.5-1-ACC-1-1.x86_64.
  ```

- 使用`--cve <cve_id>`指定cve_id安装CVE对应的热补丁

  - 使用`dnf hotupgrade --cve CVE-2022-30594`安装CVE对应的热补丁

  ```shell
  [root@openEuler ~]# dnf hotupgrade --cve CVE-2022-30594
  Last metadata expiration check: 0:26:25 ago on 2023年12月29日 星期五 10时47分38秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx(Install process)
  Complete!
  Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
  ```

  - 使用`dnf hotupgrade --cve CVE-2022-2021`安装CVE对应的热补丁，对应的CVE不存在。

  ```shell
  [root@openEuler ~]# dnf hotupgrade --cve CVE-2022-2021
  Last metadata expiration check: 1:37:44 ago on 2023年12月29日 星期五 13时49分39秒.
  The cve doesn't exist or cannot be fixed by hotpatch: CVE-2022-2021
  No hot patches marked for install.
  Dependencies resolved.
  Nothing to do.
  Complete!
  ```

  - 使用`dnf hotupgrade --cve <cve_id>`指定cve_id安装时，该CVE对应的ACC低版本热补丁已安装时，删除低版本热补丁，安装高版本ACC热补丁包。

  ```shell
  [root@openEuler ~]# dnf hotupgrade --cve CVE-2023-1070
  Last metadata expiration check: 0:00:48 ago on 2024年01月02日 星期二 11时21分55秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx (Install messages and process upgrade)
  Complete!
  Apply hot patch succeed: kernel-5.10.0-153.12.0.92.oe2203sp2/ACC-1-3.
  [root@openEuler tmp]# 
  ```

  - 指定cve_id安装时，该CVE对应的最高版本热补丁包已存在

  ```shell
  [root@openEuler ~]# dnf hotupgrade --cve CVE-2023-1070
  Last metadata expiration check: 1:37:44 ago on 2023年12月29日 星期五 13时49分39秒.
  The cve doesn't exist or cannot be fixed by hotpatch: CVE-2023-1070
  No hot patches marked for install.
  Dependencies resolved.
  Nothing to do.
  Complete!
  ```

- 使用`dnf hotupgrade`进行热补丁全量修复
  - 热补丁未安装时，使用`dnf hotupgrade`命令安装所有可安装热补丁。

  - 当部分热补丁已经安装时，使用`dnf hotupgrade`命令进行全量修复，将保留已安装的热补丁，然后安装其他热补丁

- 使用`--takeover`进行内核热补丁收编

  - 使用`dnf hotupgrade PACKAGE --takeover`安装热补丁，收编相应内核冷补丁；由于目标内核冷补丁kabi检查失败，进行自动卸载；accept热补丁，使热补丁重启后仍旧生效；恢复内核默认引导启动项。

  ```shell
  [root@openEuler ~]# dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 --takeover
  Last metadata expiration check: 2:23:22 ago on 2023年12月29日 星期五 13时49分39秒.
  Gonna takeover kernel cold patch: ['kernel-4.19.90-2206.1.0.0153.oe1.x86_64']
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  xxxx(Install process)
  Complete!
  Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
  Kabi check for kernel-4.19.90-2206.1.0.0153.oe1.x86_64:
  [Fail] Here are 81 loaded kernel modules in this system, 78 pass, 3 fail.
  Failed modules are as follows:
  No. Module      Difference
  1   nf_nat_ipv6 secure_ipv6_port_ephemeral                : 0xe1a4f16a != 0x0209f3a7
  2   nf_nat_ipv4 secure_ipv4_port_ephemeral                : 0x57f70547 != 0xe3840e18
  3   kvm_intel   kvm_lapic_hv_timer_in_use                 : 0x54981db4 != 0xf58e6f1f
  Gonna remove kernel-4.19.90-2206.1.0.0153.oe1.x86_64 due to Kabi check failed.
  Rebuild rpm database succeed.
  Remove package succeed: kernel-4.19.90-2206.1.0.0153.oe1.x86_64.
  Restore the default boot kernel succeed: kernel-4.19.90-2112.8.0.0131.oe1.x86_64.
  No available kernel cold patch for takeover, gonna accept available kernel hot patch.
  Accept hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
  ```

  - 使用`dnf hotupgrade PACKAGE --takeover -f`安装热补丁，如果内核冷补丁kabi检查未通过，使用`-f`强制保留内核冷补丁

  ```shell
  [root@openEuler ~]# dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 --takeover
  Last metadata expiration check: 2:23:22 ago on 2023年12月29日 星期五 13时49分39秒.
  Gonna takeover kernel cold patch: ['kernel-4.19.90-2206.1.0.0153.oe1.x86_64']
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  xxxx(Install process)
  Complete!
  Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
  Kabi check for kernel-4.19.90-2206.1.0.0153.oe1.x86_64:
  [Fail] Here are 81 loaded kernel modules in this system, 78 pass, 3 fail.
  Failed modules are as follows:
  No. Module      Difference
  1   nf_nat_ipv6 secure_ipv6_port_ephemeral                : 0xe1a4f16a != 0x0209f3a7
  2   nf_nat_ipv4 secure_ipv4_port_ephemeral                : 0x57f70547 != 0xe3840e18
  3   kvm_intel   kvm_lapic_hv_timer_in_use                 : 0x54981db4 != 0xf58e6f1f
  ```

## 内核升级前kabi检查

`dnf upgrade-en` 命令支持内核冷补丁升级前kabi检查，命令使用方式如下：

```shell
dnf upgrade-en [PACKAGE] [--cve [cve_id]] 

upgrade with KABI(Kernel Application Binary Interface) check. If the loaded
kernel modules have KABI compatibility with the new version kernel rpm, the
kernel modules can be installed and used in the new version kernel without
recompling.

General DNF options:
  -h, --help, --help-cmd
                        show command help
  --cve CVES, --cves CVES
                        Include packages needed to fix the given CVE, in updates
Upgrade-en command-specific options:                     
  PACKAGE
                        Package to upgrade
```

- 使用`dnf upgrade-en PACKAGE`安装目标冷补丁

  - 使用`dnf upgrade-en`安装目标冷补丁，kabi检查未通过，输出kabi差异性报告，自动卸载目标升级kernel包。

  ```shell
  [root@openEuler ~]# dnf upgrade-en kernel-4.19.90-2206.1.0.0153.oe1.x86_64
  Last metadata expiration check: 1:51:54 ago on 2023年12月29日 星期五 13时49分39秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx(Install process)                                                                                       
  Complete!
  Kabi check for kernel-4.19.90-2206.1.0.0153.oe1.x86_64:
  [Fail] Here are 81 loaded kernel modules in this system, 78 pass, 3 fail.
  Failed modules are as follows:
  No. Module      Difference
  1   nf_nat_ipv6 secure_ipv6_port_ephemeral                : 0xe1a4f16a != 0x0209f3a7
  2   nf_nat_ipv4 secure_ipv4_port_ephemeral                : 0x57f70547 != 0xe3840e18
  3   kvm_intel   kvm_lapic_hv_timer_in_use                 : 0x54981db4 != 0xf58e6f1f
                  kvm_apic_write_nodecode                   : 0x56c989a1 != 0x24c9db31
                  kvm_complete_insn_gp                      : 0x99c2d256 != 0xcd8014bd
  Gonna remove kernel-4.19.90-2206.1.0.0153.oe1.x86_64 due to kabi check failed.
  Rebuild rpm database succeed.
  Remove package succeed: kernel-4.19.90-2206.1.0.0153.oe1.x86_64.
  Restore the default boot kernel succeed: kernel-4.19.90-2112.8.0.0131.oe1.x86_64.
  ```

  - 使用`dnf upgrade-en`安装目标冷补丁，kabi检查通过

  ```shell
  [root@openEuler ~]# dnf upgrade-en kernel-4.19.90-2201.1.0.0132.oe1.x86_64
  Last metadata expiration check: 2:02:10 ago on 2023年12月29日 星期五 13时49分39秒.
  Dependencies resolved.
  xxxx(Install messgaes)
  Is this ok [y/N]: y
  Downloading Packages:
  xxxx(Install process)  
  Complete!
  Kabi check for kernel-4.19.90-2201.1.0.0132.oe1.x86_64:
  [Success] Here are 81 loaded kernel modules in this system, 81 pass, 0 fail.
  ```

- 使用`dnf upgrade-en` 进行全量修复

​    全量修复如果包含目标kernel的升级，输出根据不同的kabi检查情况与`dnf upgrade-en PACKAGE`命令相同。

## 使用场景说明

本段落介绍上述命令的使用场景及顺序介绍，需要提前确认本机的热补丁repo源和相应冷补丁repo源已开启。

- 热补丁修复。

使用热补丁扫描命令查看本机待修复cve。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-1     Important/Sec. redis-6.2.5-2.x86_64                                   patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2021-11    Important/Sec. redis-6.2.5-2.x86_64                                   patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2021-2     Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-22    Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

找到提供热补丁的相应cve，发现CVE-2021-1、CVE-2021-11、CVE-2021-2和CVE-2021-22可用热补丁修复。

在安装补丁前测试功能，基于redis.conf配置文件启动redis服务。

```shell
[root@openEuler ~]# sudo redis-server ./redis.conf &
[1] 285075
[root@openEuler ~]# 285076:C 25 Mar 2023 12:09:51.503 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
285076:C 25 Mar 2023 12:09:51.503 # Redis version=255.255.255, bits=64, commit=00000000, modified=0, pid=285076, just started
285076:C 25 Mar 2023 12:09:51.503 # Configuration loaded
285076:M 25 Mar 2023 12:09:51.504 * Increased maximum number of open files to 10032 (it was originally set to 1024).
285076:M 25 Mar 2023 12:09:51.504 * monotonic clock: POSIX clock_gettime
                _._                                                  
           _.-``__ ''-._                                             
      _.-``    `.  `_.  ''-._           Redis 255.255.255 (00000000/0) 64 bit
  .-`` .-```.  ```\/    _.,_ ''-._                                  
 (    '      ,       .-`  | `,    )     Running in standalone mode
 |`-._`-...-` __...-.``-._|'` _.-'|     Port: 6380
 |    `-._   `._    /     _.-'    |     PID: 285076
  `-._    `-._  `-./  _.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |           https://redis.io       
  `-._    `-._`-.__.-'_.-'    _.-'                                   
 |`-._`-._    `-.__.-'    _.-'_.-'|                                  
 |    `-._`-._        _.-'_.-'    |                                  
  `-._    `-._`-.__.-'_.-'    _.-'                                   
      `-._    `-.__.-'    _.-'                                       
          `-._        _.-'                                           
              `-.__.-'                                               

285076:M 25 Mar 2023 12:09:51.505 # Server initialized
285076:M 25 Mar 2023 12:09:51.505 # WARNING overcommit_memory is set to 0! Background save may fail under low memory condition. To fix this issue add 'vm.overcommit_memory = 1' to /etc/sysctl.conf and then reboot or run the command 'sysctl vm.overcommit_memory=1' for this to take effect.
285076:M 25 Mar 2023 12:09:51.506 * Ready to accept connections

```

安装前测试功能。

```shell
[root@openEuler ~]# telnet 127.0.0.1 6380
Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.

*100

-ERR Protocol error: expected '$', got ' '
Connection closed by foreign host.
```

指定修复CVE-2021-1，确认关联到对应的热补丁包，显示安装成功。

```shell
[root@openEuler ~]# dnf hotupgrade patch-redis-6.2.5-1-ACC-1-1.x86_64
Last metadata expiration check: 0:01:39 ago on 2024年01月02日 星期二 20时16分45秒.
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-benchmark'
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-cli'
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-server'
Package patch-redis-6.2.5-1-ACC-1-1.x86_64 is already installed.
Dependencies resolved.
Nothing to do.
Complete!
```

使用dnf hotpatch --list确认该热补丁是否安装成功，确认Status为ACTIVED。

```shell
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:04:43 ago on 2024年01月02日 星期二 20时16分45秒.
base-pkg/hotpatch                                   status
redis-6.2.5-1/ACC-1-1/redis-benchmark               ACTIVED
redis-6.2.5-1/ACC-1-1/redis-cli                     ACTIVED
redis-6.2.5-1/ACC-1-1/redis-server                  ACTIVED
```

确认该cve是否已被修复，由于CVE-2021-1所使用的热补丁包patch-redis-6.2.5-1-ACC-1-1.x86_64同样修复CVE-2021-11，CVE-2021-1和CVE-2021-11都不予显示。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:08:48 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-1076  Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26607 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-22    Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-2     Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

激活后测试功能，对比激活前回显内容。

```shell
[root@openEuler ~]# telnet 127.0.0.1 6380
Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.

*100

-ERR Protocol error: unauthenticated multibulk length
Connection closed by foreign host.
```

使用dnf hotpatch --remove指定热补丁手动卸载。

```shell
[root@openEuler ~]# dnf hotpatch --remove redis-6.2.5-1
Last metadata expiration check: 0:11:52 ago on 2024年01月02日 星期二 20时16分45秒.
Gonna remove this hot patch: redis-6.2.5-1
remove hot patch 'redis-6.2.5-1' succeed
[root@openEuler ~]# dnf hotpatch --list
Last metadata expiration check: 0:12:00 ago on 2024年01月02日 星期二 20时16分45秒.
base-pkg/hotpatch                                   status
redis-6.2.5-1/ACC-1-1/redis-benchmark               NOT-APPLIED
redis-6.2.5-1/ACC-1-1/redis-cli                     NOT-APPLIED
redis-6.2.5-1/ACC-1-1/redis-server                  NOT-APPLIED
```

使用热补丁扫描命令查看本机待修复cve，确认CVE-2021-1和CVE-2021-11正常显示。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-1     Important/Sec. redis-6.2.5-2.x86_64                                   patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2021-11    Important/Sec. redis-6.2.5-2.x86_64                                   patch-redis-6.2.5-1-ACC-1-1.x86_64
CVE-2021-2     Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-22    Important/Sec. redis-6.2.5-3.x86_64                                   patch-redis-6.2.5-1-ACC-1-2.x86_64
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

- 安装高版本ACC热补丁

指定安装热补丁包patch-redis-6.2.5-1-ACC-1-2.x86_64。

```shell
[root@openEuler ~]# dnf hotupgrade patch-redis-6.2.5-1-ACC-1-2.x86_64
Last metadata expiration check: 0:36:12 ago on 2024年01月02日 星期二 20时16分45秒.
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-benchmark'
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-cli'
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-server'
Package patch-redis-6.2.5-1-ACC-1-2.x86_64 is already installed.
Dependencies resolved.
Nothing to do.
Complete!
```

使用热补丁扫描命令查看本机待修复cve，由于patch-redis-6.2.5-1-ACC-1-2.x86_64比patch-redis-6.2.5-1-ACC-1-1.x86_64的热补丁版本高，低版本热补丁对应的CVE-2021-1和CVE-2021-11，以及高版本热补丁对应的CVE-2021-2和CVE-2021-22都被修复。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

- 热补丁目标软件包版本大于本机安装版本

查看热补丁repo源中repodata目录下的xxx-updateinfo.xml.gz，确认文件中的CVE-2021-33、CVE-2021-3相关信息。

```xml
<update from="openeuler.org" type="security" status="stable">
          <id>openEuler-HotPatchSA-2023-3</id>
          <title>An update for mariadb is now available for openEuler-22.03-LTS</title>
          <severity>Important</severity>
          <release>openEuler</release>
          <issued date="2022-04-16"></issued>
          <references>
                  <reference href="https://nvd.nist.gov/vuln/detail/CVE-2021-3" id="CVE-2021-3" title="CVE-2021-3" type="cve"></reference>
                  <reference href="https://nvd.nist.gov/vuln/detail/CVE-2021-33" id="CVE-2021-33" title="CVE-2021-33" type="cve"></reference>
          </references>
          <description>patch-redis-6.2.5-2-ACC.(CVE-2021-3, CVE-2021-33)</description>
          <pkglist>
               <hot_patch_collection>
                    <name>openEuler</name>
                    <package arch="aarch64" name="patch-redis-6.2.5-2-ACC" release="1" version="1">
                         <filename>patch-redis-6.2.5-2-ACC-1-1.aarch64.rpm</filename>
                    </package>
                    <package arch="x86_64" name="patch-redis-6.2.5-2-ACC" release="1" version="1">
                         <filename>patch-redis-6.2.5-2-ACC-1-1.x86_64.rpm</filename>
                    </package>
               </hot_patch_collection>
          </pkglist>
  </update>
```

package中的name字段"patch-redis-6.2.5-2-ACC"的组成部分为：patch-源码包名-源码包version-源码包release-热补丁patch名，该热补丁包需要本机安装redis-6.2.5-2源码版本，检查本机redis安装版本。

```shell
[root@openEuler ~]# rpm -qa | grep redis
redis-6.2.5-1.x86_64
```

由于本机安装版本不匹配，大于本机安装版本，该热补丁包名不显示，以'-'显示。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

- 热补丁目标软件包版本小于本机安装版本。

查看热补丁repo源中repodata目录下的xxx-updateinfo.xml.gz，确认文件中的CVE-2021-44、CVE-2021-4相关信息。

```xml
<update from="openeuler.org" type="security" status="stable">
          <id>openEuler-HotPatchSA-2023-4</id>
          <title>An update for mariadb is now available for openEuler-22.03-LTS</title>
          <severity>Important</severity>
          <release>openEuler</release>
          <issued date="2022-04-16"></issued>
          <references>
                  <reference href="https://nvd.nist.gov/vuln/detail/CVE-2021-4" id="CVE-2021-4" title="CVE-2021-4" type="cve"></reference>
                  <reference href="https://nvd.nist.gov/vuln/detail/CVE-2021-44" id="CVE-2021-44" title="CVE-2021-44" type="cve"></reference>
          </references>
          <description>patch-redis-6.2.4-1-ACC.(CVE-2021-44, CVE-2021-4)</description>
          <pkglist>
               <hot_patch_collection>
                    <name>openEuler</name>
                    <package arch="aarch64" name="patch-redis-6.2.4-1-ACC" release="1" version="1">
                         <filename>patch-redis-6.2.4-1-ACC-1-1.aarch64.rpm</filename>
                    </package>
                    <package arch="x86_64" name="patch-redis-6.2.4-1-ACC" release="1" version="1">
                         <filename>patch-redis-6.2.4-1-ACC-1-1.x86_64.rpm</filename>
                    </package>
               </hot_patch_collection>
          </pkglist>
  </update>
```

package中的name字段"patch-redis-6.2.4-1-ACC"的组成部分为：patch-源码包名-源码包version-源码包release-热补丁patch名，该热补丁包需要本机安装redis-6.2.4-1源码版本，检查本机redis安装版本。

```shell
[root@openEuler ~]# rpm -qa | grep redis
redis-6.2.5-1.x86_64
```

由于本机安装版本不匹配，小于本机安装版本，该CVE不予显示。

```shell
[root@openEuler ~]# dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on 2023年03月25日 星期六 11时53分46秒.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```
