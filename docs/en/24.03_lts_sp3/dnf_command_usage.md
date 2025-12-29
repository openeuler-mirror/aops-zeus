# DNF Command Usage

Af ter installing dnf-hotpatch-plugin, you can run `dnf` commands to use Ceres functions related to hot/cold patches, such as hot patch scanning (`dnf hot-updateinfo`), setting and querying (`dnf hotpatch`), applying (`dnf hotupgrade`), and kabi check before kernel upgrade (`dnf upgrade-en`). This document describes the usage of the commands.

> Hot patches include ACC (accumulate) and SGL (single) types.
>
> - ACC: A hot patch of the higher version fixes all problems that can be fixed by lower-version hot patches.
> - SGL_xxx: A hot patch fixes the problems related to issue _xxx_. Multiple issue IDs are concatenated by underscores (\_).

## Hot Patch Scanning

`dnf hot-updateinfo` can scan hot patches and query hot patches for specified CVEs.

```shell
$ dnf hot-updateinfo list cves [--available(default) | --installed] [--cve [cve_id]] 
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

    1. Query the CVEs on the host that can be fixed and their related cold and hot patches.

        ```shell
        $ dnf hot-updateinfo list cves
        # cve-id   level    cold-patch   hot-patch
        Last metadata expiration check: 2:39:04 ago on Fri 29 Dec 2023 07:45:02.
        CVE-2022-30594  Important/Sec. kernel-4.19.90-2206.1.0.0153.oe1.x86_64                        patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
        CVE-2023-1111   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-ACC-1-1.x86_64
        CVE-2023-1112   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-ACC-1-1.x86_64
        CVE-2023-1111   Important/Sec. redis-6.2.5-2.x86_64                                           patch-redis-6.2.5-1-SGL_CVE_2023_1111_CVE_2023_1112-1-1.x86_64
        ```

    2. Query hot and cold patches corresponding to fixed CVEs.

        ```shell
        $ dnf hot-updateinfo list cves --installed
        # cve-id   level    cold-patch   hot-patch
        Last metadata expiration check: 2:39:04 ago on Fri 29 Dec 2023 07:45:02.
        CVE-2022-36298  Important/Sec. -      patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_36298-1-1.x86_64
        ```

    3. Query hot and cold patches for specified CVEs.

        ```shell
        $ dnf hot-updateinfo list cves --cve CVE-2022-30594
        # cve-id   level    cold-patch   hot-patch
        Last metadata expiration check: 2:39:04 ago on Fri 29 Dec 2023 07:45:02.
        CVE-2022-30594 Important/Sec. kernel-4.19.90-2206.1.0.0153.oe1.x86_64       patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
        ```

    4. An empty list will be displayed if the CVE does not exist.

        ```shell
        $ dnf hot-updateinfo list cves --cve CVE-2022-3089
        # cve-id   level    cold-patch   hot-patch
        Last metadata expiration check: 2:39:04 ago on Fri 29 Dec 2023 07:45:02.
        ```

## Hot Patch Statuses

- A hot patch can be in the following statuses:

    - NOT-APPLIED: The hot patch is not applied.

    - DEACTIVED: The hot patch is not activated.

    - ACTIVED: The hot patch is activated.

    - ACCEPT: The hot patch has been activated and will be applied after a reboot.

    ![Hot patch statuses](./figures/syscare_hot_patch_statuses.png)

## Querying and Changing Hot Patch Statuses

`dnf hotpatch` can be used to query and convert hot patch statuses.

```shell
$ dnf hotpatch 
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

- Using `dnf hotpatch` to query hot patch statuses.

    - `dnf hotpatch --list` lists available hot patches in the system.

        ```shell
        $ dnf hotpatch --list
        Last metadata expiration check: 0:09:25 ago on Fri 29 Dec 2023 10:26:45.
        base-pkg/hotpatch                                               status
        kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
        ```

    - `dnf hotpatch --list cves` queries hot patches related to CVEs.

        ```shell
        $ dnf hotpatch --list cves
        Last metadata expiration check: 0:09:25 ago on Fri 29 Dec 2023 10:26:45.
        CVE-id         base-pkg/hotpatch                                               status
        CVE-2022-30594 kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
        ```

    - `dnf hotpatch --list cves --cve <CVE-id>` queries hot patches for specified CVEs.

        ```shell
        $ dnf hotpatch --list cves --cve CVE-2022-30594
        Last metadata expiration check: 0:09:25 ago on Fri 29 Dec 2023 10:26:45.
        CVE-id         base-pkg/hotpatch                                               status
        CVE-2022-30594 kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
        ```

    - An empty list will be displayed if the specified CVE does not exist when running `dnf hotpatch --list cves --cve <CVE-id>`.

        ```shell
        $ dnf hotpatch --list cves --cve CVE-2023-1
        Last metadata expiration check: 0:09:25 ago on Fri 29 Dec 2023 10:26:45.
        ```

- `dnf hotpatch --apply <patch name>` applies a hot patch. You can run `dnf hotpatch --list` to query the hot patch status after applying the hot patch. For details about hot patch statuses, see the previous section.

    ```shell
    $ dnf hotpatch --list
    Last metadata expiration check: 0:13:55 ago on Fri 29 Dec 2023 10:26:45.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
    $ dnf hotpatch --apply kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    Last metadata expiration check: 0:15:37 ago on Fri 29 Dec 2023 10:26:45.
    Gonna apply this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    apply hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
    $ dnf hotpatch --list
    Last metadata expiration check: 0:16:20 ago on Fri 29 Dec 2023 10:26:45.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACTIVED
    ```

- `dnf hotpatch --deactive <patch name>` deactivates a hot patch. You can run `dnf hotpatch --` to query the hot patch status after deactivating the hot patch. For details about hot patch statuses, see the previous section.

    ```shell
    $ dnf hotpatch --deactive kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    Last metadata expiration check: 0:19:00 ago on Fri 29 Dec 2023 10:26:45.
    Gonna deactive this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    deactive hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
    $ dnf hotpatch --list
    Last metadata expiration check: 0:19:12 ago on Fri 29 Dec 2023 10:26:45.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux DEACTIVED
    ```

- `dnf hotpatch --remove <patch name>` removes a hot patch. You can run `dnf hotpatch --list` to query the hot patch status after removing the hot patch. For details about hot patch statuses, see the previous section.

    ```shell
    $ dnf hotpatch --remove kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    Last metadata expiration check: 0:20:12 ago on Fri 29 Dec 2023 10:26:45.
    Gonna remove this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    remove hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
    $ dnf hotpatch --list
    Last metadata expiration check: 0:20:23 ago on Fri 29 Dec 2023 10:26:45.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux NOT-APPLIED
    ```

- `dnf hotpatch --active <patch name>` activating a hot patch.You can run `dnf hotpatch --list` to query the hot patch status after activating the hot patch. For details about hot patch statuses, see the previous section.

    ```shell
    $ dnf hotpatch --active kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    Last metadata expiration check: 0:15:37 ago on Fri 29 Dec 2023 10:26:45.
    Gonna active this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    active hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
    $ dnf hotpatch --list
    Last metadata expiration check: 0:16:20 ago on Fri 29 Dec 2023 10:26:45.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACTIVED
    ```

- `dnf hotpatch --accept <patch name>` accepts a hot patch. You can run `dnf hotpatch --list` to query the hot patch status after accepting the hot patch. For details about hot patch statuses, see the previous section.

    ```shell
    $ dnf hotpatch --accept kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    Last metadata expiration check: 0:14:19 ago on Fri 29 Dec 2023 10:47:38.
    Gonna accept this hot patch: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1
    accept hot patch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' succeed
    $ dnf hotpatch --list
    Last metadata expiration check: 0:14:34 ago on Fri 29 Dec 2023 10:47:38.
    base-pkg/hotpatch                                               status
    kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1/vmlinux ACCEPTED
    ```

## Applying Hot Patches

The `hotupgrade` command is used to apply hot patches to fix specified or all CVEs.

```shell
$ dnf hotupgrade [--cve [cve_id]] [PACKAGE ...] [--takeover] [-f]


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

- Using `dnf hotupgrade PACKAGE` to install target hot patches.

    - Using `dnf hotupgrade PACKAGE` to install target hot patches.

    ```shell
    $ dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
    Last metadata expiration check: 0:26:25 ago on Fri 29 Dec 2023 10:47:38.
    Dependencies resolved.
    xxxx(Install messgaes)
    Is this ok [y/N]: y
    Downloading Packages:
    xxxx(Install process)
    Complete!
    Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
    ```

    - Using `dnf hotupgrade PACKAGE` to install target hot patches when target hot patches have been activated.

    ```shell
    $ dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64
    Last metadata expiration check: 0:28:35 ago on Fri 29 Dec 2023 10:47:38.
    The hotpatch 'kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'vmlinux'
    Package patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 is already installed.
    Dependencies resolved.
    Nothing to do.
    Complete!
    ```

    - Using `dnf hotupgrade PACKAGE` to install target hot patches and automatically uninstall hot patches that fail to be activated.

    ```shell
    $ dnf hotupgrade patch-redis-6.2.5-1-ACC-1-1.x86_64
    Last metadata expiration check: 0:30:30 ago on Fri 29 Dec 2023 10:47:38.
    Dependencies resolved.
    xxxx(Install messgaes)
    Is this ok [y/N]: y
    Downloading Packages:
    xxxx(Install process)
    Complete!
    Apply hot patch failed: redis-6.2.5-1/ACC-1-1.
    Error: Operation failed

    Caused by:
        1. Transaction "Apply patch 'redis-6.2.5-1/ACC-1-1'" failed

        Caused by:
            Cannot match any patch named "redis-6.2.5-1/ACC-1-1"

    Gonna remove unsuccessfully activated hotpatch rpm.
    Remove package succeed: patch-redis-6.2.5-1-ACC-1-1.x86_64.
    ```

- Using `--cve <cve_id>` to install hot patches for a CVE.

    - Using `--cve <cve_id>` to install hot patches for a CVE.

    ```shell
    $ dnf hotupgrade --cve CVE-2022-30594
    Last metadata expiration check: 0:26:25 ago on Fri 29 Dec 2023 10:47:38.
    Dependencies resolved.
    xxxx(Install messgaes)
    Is this ok [y/N]: y
    Downloading Packages:
    xxxx(Install process)
    Complete!
    Apply hot patch succeed: kernel-4.19.90-2112.8.0.0131.oe1/SGL_CVE_2022_30594-1-1.
    ```

    - Using `dnf hotupgrade --cve CVE-2022-2021` to install hot patches for the CVE, which does not exist.

    ```shell
    $ dnf hotupgrade --cve CVE-2022-2021
    Last metadata expiration check: 1:37:44 ago on Fri 29 Dec 2023 13:49:39.
    The cve doesn't exist or cannot be fixed by hotpatch: CVE-2022-2021
    No hot patches marked for install.
    Dependencies resolved.
    Nothing to do.
    Complete!
    ```

    - Using `dnf hotupgrade --cve <cve_id>`  to install and apply a hot patch of a higher version for a CVE that has an ACC hot patch of a lower version. The hot patch of the lower version is uninstalled.

    ```shell
    $ dnf hotupgrade --cve CVE-2023-1070
    Last metadata expiration check: 0:00:48 ago on Tue 02 Jan 2024 11:21:55.
    Dependencies resolved.
    xxxx(Install messgaes)
    Is this ok [y/N]: y
    Downloading Packages:
    xxxx (Install messages and process upgrade)
    Complete!
    Apply hot patch succeed: kernel-5.10.0-153.12.0.92.oe2203sp2/ACC-1-3.
    $ 
    ```

    - Installing and applying a hot patch for a CVE that already has the latest hot patch.

    ```shell
    $ dnf hotupgrade --cve CVE-2023-1070
    Last metadata expiration check: 1:37:44 ago on Fri 29 Dec 2023 13:49:39.
    The cve doesn't exist or cannot be fixed by hotpatch: CVE-2023-1070
    No hot patches marked for install.
    Dependencies resolved.
    Nothing to do.
    Complete!
    ```

- Using `dnf hotupgrade` to install all hot patches.
    - When no hot patch is installed, running `dnf hotupgrade` will install all available hot patches.
   
    - When some of the hot patches are installed, running `dnf hotupgrade` will install the remaining hot patches.
   
- Using `--takeover` to take over kernel hot patches.

    - Using `dnf hotupgrade PACKAGE --takeover` to install hot patches and take over the related kernel hot patches. If a target kernel cold patch fails to pass the kabi check, it will be automatically uninstalled. The hot patches will be accepted and remain in effect after a reboot. The default kernel boot options will be restored.

    ```shell
    $ dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 --takeover
    Last metadata expiration check: 2:23:22 ago on Fri 29 Dec 2023 13:49:39.
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

    - Using `dnf hotupgrade PACKAGE --takeover -f` to install hot patches. If a kernel cold patch fails to pass the kabi check, the `-f` option forcibly keeps the cold patch.

    ```shell
    $ dnf hotupgrade patch-kernel-4.19.90-2112.8.0.0131.oe1-SGL_CVE_2022_30594-1-1.x86_64 --takeover
    Last metadata expiration check: 2:23:22 ago on Fri 29 Dec 2023 13:49:39.
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

## kabi Check before Kernel Upgrade

`dnf upgrade-en` supports the kabi check before kernel cold patch upgrade.

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

- Using `dnf upgrade-en PACKAGE` to install target cold patches.

    - Using `dnf upgrade-en` to install target cold patches. If the kabi check is not passed, the kabi difference report will be generated, and the target kernel upgrade package will be uninstalled.

    ```shell
    $ dnf upgrade-en kernel-4.19.90-2206.1.0.0153.oe1.x86_64
    Last metadata expiration check: 1:51:54 ago on Fri 29 Dec 2023 13:49:39.
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

    - Using `dnf upgrade-en` to install target cold patches and the kabi check is passed.

    ```shell
    $ dnf upgrade-en kernel-4.19.90-2201.1.0.0132.oe1.x86_64
    Last metadata expiration check: 2:02:10 ago on Fri 29 Dec 2023 13:49:39.
    Dependencies resolved.
    xxxx(Install messgaes)
    Is this ok [y/N]: y
    Downloading Packages:
    xxxx(Install process)  
    Complete!
    Kabi check for kernel-4.19.90-2201.1.0.0132.oe1.x86_64:
    [Success] Here are 81 loaded kernel modules in this system, 81 pass, 0 fail.
    ```

- Using `dnf upgrade-en` to install all cold patches.

    If the target kernel upgrade is included in the cold patches, the output is the same as `dnf upgrade-en PACKAGE` according to the kabi check result.

## Usage Example

Assume that the repositories of hot and cold patches on this host have been enabled.

- Hot patches

Scan CVEs that can be fixed on the host.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on Sat 25 Mar 2023 11:53:46.
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

CVE-2021-1, CVE-2021-11, CVE-2021-2, and CVE-2021-22 can be fixed by hot patches.

Start the Redis service based on the **redis.conf** configuration file.

```shell
$ sudo redis-server ./redis.conf &
[1] 285075
$ 285076:C 25 Mar 2023 12:09:51.503 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
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

Test the function before applying the hot patch.

```shell
$ telnet 127.0.0.1 6380
Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.

*100

-ERR Protocol error: expected '$', got ' '
Connection closed by foreign host.
```

Specify CVE-2021-1 and ensure that the related hot patch is associated and applied.

```shell
$ dnf hotupgrade patch-redis-6.2.5-1-ACC-1-1.x86_64
Last metadata expiration check: 0:01:39 ago on Tue 02 Jan 2024 20:16:45.
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-benchmark'
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-cli'
The hotpatch 'redis-6.2.5-1/ACC-1-1' already has a 'ACTIVED' sub hotpatch of binary file 'redis-server'
Package patch-redis-6.2.5-1-ACC-1-1.x86_64 is already installed.
Dependencies resolved.
Nothing to do.
Complete!
```

Run `dnf hotpatch --list` to check whether the hot patch has been applied (the status is **ACTIVED**).

```shell
$ dnf hotpatch --list
Last metadata expiration check: 0:04:43 ago on Tue 02 Jan 2024 20:16:45.
base-pkg/hotpatch                                   status
redis-6.2.5-1/ACC-1-1/redis-benchmark               ACTIVED
redis-6.2.5-1/ACC-1-1/redis-cli                     ACTIVED
redis-6.2.5-1/ACC-1-1/redis-server                  ACTIVED
```

Check whether the CVE has been fixed. Because the **patch-redis-6.2.5-1-ACC-1-1.x86_64** hot patch also fixes CVE-2021-11, CVE-2021-1 and CVE-2021-11 no longer exists.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:08:48 ago on Sat 25 Mar 2023 11:53:46.
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

Test the function after applying the hot patch.

```shell
$ telnet 127.0.0.1 6380
Trying 127.0.0.1...
Connected to 127.0.0.1.
Escape character is '^]'.

*100

-ERR Protocol error: unauthenticated multibulk length
Connection closed by foreign host.
```

Run `dnf hotpatch --remove` and specify the patch name to manually remove the hot patch.

```shell
$ dnf hotpatch --remove redis-6.2.5-1
Last metadata expiration check: 0:11:52 ago on Tue 02 Jan 2024 20:16:45.
Gonna remove this hot patch: redis-6.2.5-1
remove hot patch 'redis-6.2.5-1' succeed
$ dnf hotpatch --list
Last metadata expiration check: 0:12:00 ago on Tue 02 Jan 2024 20:16:45.
base-pkg/hotpatch                                   status
redis-6.2.5-1/ACC-1-1/redis-benchmark               NOT-APPLIED
redis-6.2.5-1/ACC-1-1/redis-cli                     NOT-APPLIED
redis-6.2.5-1/ACC-1-1/redis-server                  NOT-APPLIED
```

Scan the CVEs to be fixed on the host. CVE-2021-1 and CVE-2021-11 are displayed.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on Sat 25 Mar 2023 11:53:46.
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

- installing an ACC patch of a higher version.

Apply hot patch **patch-redis-6.2.5-1-HP002-1-1.x86_64**.

```shell
$ dnf hotupgrade patch-redis-6.2.5-1-ACC-1-2.x86_64
Last metadata expiration check: 0:36:12 ago on Tue 02 Jan 2024 20:16:45.
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-benchmark'
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-cli'
The hotpatch 'redis-6.2.5-1/ACC-1-2' already has a 'ACTIVED' sub hotpatch of binary file 'redis-server'
Package patch-redis-6.2.5-1-ACC-1-2.x86_64 is already installed.
Dependencies resolved.
Nothing to do.
Complete!
```

Scan the CVEs to be fixed on the host. Because **patch-redis-6.2.5-1-ACC-1-2.x86_64** is of a higher version than **patch-redis-6.2.5-1-ACC-1-1.x86_64**, **patch-redis-6.2.5-1-ACC-1-2.x86_64** also fixes CVE-2021-1, CVE-2021-11, CVE-2021-2, and CVE-2021-22.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on Sat Mar 25 11:53:46 2023.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

- Version of the software package fixed by the hot patch higher than that of the installed one.

Open the **xxx-updateinfo.xml.gz** file in the **repodata** directory of the hot patch repository. Check the information related to CVE-2021-33 and CVE-2021-3.

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

The format of the **name** field of **package** (**patch-redis-6.2.5-2-ACC**) is **patch-\<source package name>-\<source package version>-\<source package release>-\<hot patch name>**. In the example, **patch-redis-6.2.5-2-ACC** requires the source code version of redis-6.2.5-2 to be installed. Check the version of Redis on the host.

```shell
$ rpm -qa | grep redis
redis-6.2.5-1.x86_64
```

The installed Redis version is lower than 6.2.5-2. Therefore, the hot patch will not be displayed.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on Sat 25 Mar 2023 11:53:46.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```

- Version of the software package fixed by the hot patch lower than that of the installed one.

Open the **xxx-updateinfo.xml.gz** file in the **repodata** directory of the hot patch repository. Check the information related to CVE-2021-44 and CVE-2021-4.

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

The format of the **name** field of **package** (**patch-redis-6.2.4-1-ACC**) is **patch-\<source package name>-\<source package version>-\<source package release>-\<hot patch name>**. In the example, **patch-redis-6.2.4-1-ACC** requires the source code version of redis-6.2.4-1 to be installed. Check the version of Redis on the host.

```shell
$ rpm -qa | grep redis
redis-6.2.5-1.x86_64
```

The installed Redis version is higher than 6.2.4-1. Therefore, the CVE will not be displayed.

```shell
$ dnf hot-updateinfo list cves
Last metadata expiration check: 0:00:38 ago on Sat 25 Mar 2023 11:53:46.
CVE-2023-22995 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2023-26545 Important/Sec. python3-perf-5.10.0-136.22.0.98.oe2203sp1.x86_64       -
CVE-2022-40897 Important/Sec. python3-setuptools-59.4.0-5.oe2203sp1.noarch           -
CVE-2021-33    Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2021-3     Important/Sec. redis-6.2.5-4.x86_64                                   -
CVE-2022-38023 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
CVE-2022-37966 Important/Sec. samba-client-4.17.2-5.oe2203sp1.x86_64                 -
```
