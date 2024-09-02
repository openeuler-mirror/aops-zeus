Name:		aops-zeus
Version:	v2.0.0
Release:	1
Summary:	A service which is the foundation of aops.
License:	MulanPSL2
URL:		https://gitee.com/openeuler/%{name}
Source0:	%{name}-%{version}.tar.gz


BuildRequires:  python3-setuptools
Requires:   python3-pyyaml python3-PyMySQL python3-kazoo python3-click


%description
Provide one-click aops deployment, service start and stop, hot loading of 
configuration files, and database initialization.
Provides:   aops-zeus

%package -n zeus-host-information
Summary: A host manager service which is the foundation of aops.
Requires:  aops-vulcanus >= v2.0.0
Requires:  python3-gevent python3-uWSGI python3-paramiko

%description -n zeus-host-information
A host manager service which is the foundation of aops.

%package -n zeus-user-access
Summary: A user manager service which is the foundation of aops.
Requires:   aops-vulcanus >= v2.0.0
Requires:   python3-celery python3-uWSGI

%description -n zeus-user-access
A user manager service which is the foundation of aops.

%package -n async-task
Summary: A async task of aops.
Requires:   aops-vulcanus >= v2.0.0 python3-celery python3-paramiko


%description -n async-task
A async task of aops.

%package -n zeus-distribute
Summary: A distributed service of aops.
Requires:   aops-vulcanus >= v2.0.0
Requires:   python3-uWSGI python3-gevent
%description -n zeus-distribute
A distributed service of aops.

%prep
%autosetup -n %{name}-%{version}


# build for aops-zeus
%py3_build

# build for zeus-host-information
pushd host-information-service
%py3_build
popd

# build for zeus-user-access
pushd user-access-service
%py3_build
popd

# build for async-task
pushd async-task
%py3_build
popd

# build for zeus-distribute
pushd distribute-service
%py3_build
popd

# install for aops-zeus
%py3_install

# install for zeus-host-information
pushd host-information-service
%py3_install
mkdir -p %{buildroot}/opt/aops/database/
cp zeus/host_information_service/database/*.sql %{buildroot}/opt/aops/database/
popd

# install for zeus-user-access
pushd user-access-service
%py3_install
mkdir -p %{buildroot}/opt/aops/database/
cp zeus/user_access_service/database/*.sql %{buildroot}/opt/aops/database/
popd

# install for async-task
pushd async-task
%py3_install
mkdir -p %{buildroot}/opt/aops/celery
mkdir -p %{_sysconfdir}/aops/sync-conf.d/rdb
cp async_task/tasks/synchronize_conf/instance.properties %{_sysconfdir}/aops/sync-conf.d
cp async_task/tasks/synchronize_conf/rdb_conf/* %{_sysconfdir}/aops/sync-conf.d/rdb
popd

# install for zeus-distribute
pushd distribute-service
%py3_install
popd

%files
%doc README.*
%{python3_sitelib}/aops_zeus*.egg-info
%{python3_sitelib}/zeus/*
%attr(0755,root,root) %{_bindir}/aops-cli

%files -n zeus-host-information
%attr(0644,root,root) %{_sysconfdir}/aops/conf.d/zeus-host-information.yml
%attr(0755,root,root) %{_unitdir}/zeus-host-information.service
%{python3_sitelib}/zeus_host_information*.egg-info/*
%{python3_sitelib}/zeus/host_information_service/*
%attr(0755, root, root) /opt/aops/database/*

%files -n zeus-user-access
%attr(0644,root,root) %{_sysconfdir}/aops/conf.d/zeus-user-access.yml
%attr(0755,root,root) %{_unitdir}/zeus-user-access.service
%{python3_sitelib}/zeus_user_access*.egg-info/*
%{python3_sitelib}/zeus/user_access_service/*
%attr(0755, root, root) /opt/aops/database/*

%files -n async-task
%attr(0644,root,root) %{_sysconfdir}/aops/crontab.yml
%attr(0644,root,root) %{_sysconfdir}/aops/sync-conf.d/instance.properties
%attr(0644,root,root) %{_sysconfdir}/aops/sync-conf.d/rdb/*
%attr(0755,root,root) %{_unitdir}/async-task.service
%{python3_sitelib}/async_task*.egg-info/*
%{python3_sitelib}/async_task/*
%attr(0755,root,root) %{_bindir}/async-task
%dir %attr(0644,root,root) /opt/aops/celery

%files -n zeus-distribute
%attr(0644,root,root) %{_sysconfdir}/aops/conf.d/zeus-distribute.yml
%attr(0755,root,root) %{_unitdir}/zeus-distribute.service
%{python3_sitelib}/zeus_distribute*.egg-info/*
%{python3_sitelib}/zeus/distribute_service/*

%changelog
* Thu Jul 16 2024 luxuexian<luxuexian@huawei.com> - v2.0.0-1
- Update to v2.0.0
- Add microservice split, cluster management and user management

* Wed May 29 2024 wangguangge<wangguangge@huawei.com> - v1.4.0-2
- add the user access service

* Tue May 28 2024 gongzhengtang<gong_zhengtang@163.com> - v1.4.0-1
- microservice splitting
- scheduled task and asynchronous task
- command line tool

* Tue Apr 9 2024 gongzt<gong_zhengtang@163.com> - v1.3.0-1
- add the function of host information

* Fri Mar 24 2023 wenixn<shusheng.wen@outlook.com> - v1.2.0-1
- update the call method of ceres; add function how to add host from web

* Tue Dec 27 2022 wenxin<shusheng.wen@outlook.com> - v1.1.1-4
- Modify uwsgi configuration file fields

* Wed Dec 21 2022 gongzhengtang<gong_zhengtang@163.com> - v1.1.1-3
- disabled mysql installed checked

* Tue Dec 06 2022 wenxin<shusheng.wen@outlook.com> - v1.1.1-2
- update delete host, remove the judgment about the workflow

* Fri Dec 02 2022 wenxin<shusheng.wen@outlook.com> - v1.1.1-1
- set timeout for cve scan,cve fix ,repo set

* Fri Nov 25 2022 wenxin<shusheng.wen@outlook.com> - v1.1.0-1
- remove test cases that use the responses module
- remove check_es_installed
- add cve cve fix, add cve cve scan

* Tue Nov 22 2022 zhuyuncheng<zhuyuncheng@huawei.com> - v1.0.0-1
- Package init
