Name:		aops-zeus
Version:	v2.0.0
Release:	1
Summary:	A host and user manager service which is the foundation of aops.
License:	MulanPSL2
URL:		https://gitee.com/openeuler/%{name}
Source0:	%{name}-%{version}.tar.gz


BuildRequires:  python3-setuptools
Requires:   aops-vulcanus = %{version}-%{release}
Requires:   python3-marshmallow >= 3.13.0 python3-flask python3-flask-restful
Requires:   python3-requests python3-uWSGI python3-sqlalchemy python3-werkzeug python3-PyMySQL
Requires:   python3-paramiko
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


%files
%doc README.*
%attr(0644,root,root) %{_sysconfdir}/aops/zeus.ini
%attr(0755,root,root) %{_bindir}/aops-zeus
%attr(0755,root,root) %{_unitdir}/aops-zeus.service
%{python3_sitelib}/aops_zeus*.egg-info
%{python3_sitelib}/zeus/*


%changelog
* Sun Oct 9 2022 zhuyuncheng<zhuyuncheng@huawei.com> - v2.0.0-1
- Package init
