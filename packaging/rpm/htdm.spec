Name:           htdm
Version:        0.1.0
Release:        1%{?dist}
Summary:        HTPC display manager scaffolding package
License:        MIT
BuildArch:      noarch
Source0:        %{name}-%{version}.tar.gz

# Scaffold for split subpackages.
%global _pkgdocdir %{_docdir}/%{name}

%description
HTDM packaging scaffold that defines core/session scripts, deployment config,
and bootstrap install tooling for multiple distro families.

%package core
Summary: Core HTDM session scripts and policy templates
Requires: bash

%description core
Session wrappers and shared policy scaffolding.

%package config
Summary: HTDM system configuration templates
Requires: coreutils

%description config
PAM, greetd, tmpfiles, sysusers, and systemd preset templates.

%package installer
Summary: HTDM bootstrap installation tooling
Requires: bash

%description installer
Cross-distro bootstrap and defaults application helper scripts.

%prep
%setup -q

%build
# No build step for shell/config-only scaffold.

%install
srcdir="%{_builddir}/%{name}-%{version}"
install -d %{buildroot}%{_datadir}/htdm
cp -a "$srcdir/config" %{buildroot}%{_datadir}/htdm/
cp -a "$srcdir/scripts" %{buildroot}%{_datadir}/htdm/
cp -a "$srcdir/docs" %{buildroot}%{_datadir}/htdm/

%files core
%{_datadir}/htdm/scripts/session
%{_datadir}/htdm/config/policy

%files config
%{_datadir}/htdm/config/pam
%{_datadir}/htdm/config/greetd
%{_datadir}/htdm/config/systemd
%{_datadir}/htdm/config/systemd-preset
%{_datadir}/htdm/config/tmpfiles
%{_datadir}/htdm/config/sysusers

%files installer
%{_datadir}/htdm/scripts/install
%{_datadir}/htdm/docs/deployment

%changelog
* Wed Jun 17 2026 HTDM Team <packaging@example.invalid> - 0.1.0-1
- Add initial RPM scaffold for split HTDM deliverables.
