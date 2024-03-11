Name:		aops-zeus
Version:	v1.2.0
Release:	1
Summary:	A host and user manager service which is the foundation of aops.
License:	MulanPSL2
URL:		https://gitee.com/openeuler/%{name}
Source0:	%{name}-%{version}.tar.gz


BuildRequires:  python3-setuptools
Requires:   aops-vulcanus >= v1.2.0
Requires:   python3-marshmallow >= 3.13.0 python3-flask python3-flask-restful python3-gevent
Requires:   python3-requests python3-uWSGI python3-sqlalchemy python3-werkzeug python3-PyMySQL
Requires:   python3-paramiko >= 2.11.0 python3-redis python3-prometheus-api-client python3-retrying
Provides:   aops-zeus
Conflicts:  aops-manager


%description
A host and user manager service which is the foundation of aops.


%prep
%autosetup -n %{name}-%{version}


# build for aops-zeus
%py3_build


# install for aops-zeus
%py3_install
mkdir -p %{buildroot}/opt/aops/
cp -r database %{buildroot}/opt/aops/


%files
%doc README.*
%attr(0644,root,root) %{_sysconfdir}/aops/zeus.ini
%attr(0755,root,root) %{_bindir}/aops-zeus
%attr(0755,root,root) %{_unitdir}/aops-zeus.service
%{python3_sitelib}/aops_zeus*.egg-info
%{python3_sitelib}/zeus/*
%attr(0755, root, root) /opt/aops/database/*


%changelog
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
