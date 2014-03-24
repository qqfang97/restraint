
# Got Systemd?
%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
%global with_systemd 1
%else
%global with_systemd 0
%endif

Name:		restraint
Version:	0.1.8
Release:	1%{?dist}
Summary:	Simple test harness which can be used with beaker

Group:		Applications/Internet
License:	GPLv3+
URL:		https://github.com/p3ck/%{name}
Source0:	https://github.com/p3ck/%{name}/%{name}-%{version}.tar.gz

BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	pkgconfig
BuildRequires:	gettext
BuildRequires:	perl-XML-Parser
BuildRequires:	openssl-devel
BuildRequires:	libselinux-devel
BuildRequires:	glibc-devel
%if 0%{?rhel}%{?fedora} > 4
BuildRequires: selinux-policy-devel
%endif
%if %{with_systemd}
BuildRequires:          systemd-units
Requires(post):         systemd
Requires(pre):          systemd
Requires(postun):       systemd
%else
Requires(post): chkconfig
Requires(preun): chkconfig
# This is for /sbin/service
Requires(preun): initscripts
Requires(postun): initscripts
%endif

#if not static build
BuildRequires:	zlib-devel
# If static build...
%if 0%{?rhel} >= 6
BuildRequires:	libselinux-static
BuildRequires:	openssl-static
BuildRequires:	glibc-static
%endif

%description
restraint harness which can run standalone or with beaker.  when provided a recipe xml it will execute
each task listed in the recipe until done.

%package rhts
Summary:	Allow unmodified rhts tests to run under restraint
Group:		Applications/Internet
Requires:	restraint = %{version}
Provides:	rhts-test-env
Obsoletes:	rhts-test-env

%description rhts
Legacy package to allow older rhts tests to run under restraint

%prep
%setup -q


%build
%ifarch i386
export CFLAGS="-march=i486"
%endif
%if 0%{?rhel} == 4
%ifarch ppc64
export CFLAGS="-mminimal-toc"
%endif
%endif

pushd third-party
make
popd
pushd src
PKG_CONFIG_PATH=../third-party/tree/lib/pkgconfig make STATIC=1
popd


%install
%{__rm} -rf %{buildroot}

pushd third-party
make clean
popd
make DESTDIR=%{buildroot} install

# Legacy support.
ln -s rhts-environment.sh $RPM_BUILD_ROOT/usr/bin/rhts_environment.sh
ln -s rstrnt-report-log $RPM_BUILD_ROOT/usr/bin/rhts-submit-log
ln -s rstrnt-report-log $RPM_BUILD_ROOT/usr/bin/rhts_submit_log
ln -s rstrnt-report-result $RPM_BUILD_ROOT/usr/bin/rhts-report-result
ln -s rstrnt-backup $RPM_BUILD_ROOT/usr/bin/rhts-backup
ln -s rstrnt-restore $RPM_BUILD_ROOT/usr/bin/rhts-restore
ln -s rstrnt-reboot $RPM_BUILD_ROOT/usr/bin/rhts-reboot
mkdir -p $RPM_BUILD_ROOT/mnt/scratchspace
mkdir -p $RPM_BUILD_ROOT/mnt/testarea

%if 0%{?rhel}%{?fedora} > 4
# Build RHTS Selinux Testing Policy 
pushd legacy/selinux
# If dist specific selinux module is present use that.
# Why:
#  newer releases may introduce new selinux macros which are not present in
#  older releases.  This means that a module built under the newer release
#  will no longer load on an older release.  
# How:
#  Simply issue the else statement on the older release and commit the 
#  policy to git with the appropriate dist tag.
if [ -e "rhts%{?dist}.pp" ]; then
    install -p -m 644 -D rhts%{?dist}.pp $RPM_BUILD_ROOT%{_datadir}/selinux/packages/%{name}/rhts.pp
else
    make -f %{_datadir}/selinux/devel/Makefile
    install -p -m 644 -D rhts.pp $RPM_BUILD_ROOT%{_datadir}/selinux/packages/%{name}/rhts.pp
fi
popd
%endif

%post rhts
if [ "$1" -le "1" ] ; then # First install
%if %{with_systemd}
%systemd_post restraintd
# Enable restraintd by default
/bin/systemctl enable restraintd.service >/dev/null 2>&1 || :
%else
chkconfig --level 345 restraintd on
%endif
%if 0%{?rhel}%{?fedora} > 4
semodule -i %{_datadir}/selinux/packages/%{name}/rhts.pp || :
%endif
fi

%preun rhts
if [ "$1" -lt "1" ] ; then # Final removal
%if %{with_systemd}
%systemd_preun %{_services}
%else
chkconfig --del restraintd || :
%endif
%if 0%{?rhel}%{?fedora} > 4
semodule -r rhts || :
%endif
fi

%postun rhts
if [ "$1" -ge "1" ] ; then # Upgrade
%if %{with_systemd}
%systemd_postun_with_restart %{_services_restart}
%else
service restraintd condrestart >/dev/null 2>&1 || :
%endif
%if 0%{?rhel}%{?fedora} > 4
semodule -i %{_datadir}/selinux/packages/%{name}/rhts.pp || :
%endif
fi

%files
%defattr(-,root,root,-)
%if %{with_systemd}
%attr(0755, root, root)%{_unitdir}/%{name}d.service
%exclude %{_sysconfdir}/init.d
%else
%exclude /usr/lib/systemd
%attr(0755, root, root)%{_sysconfdir}/init.d/%{name}d
%endif
%attr(0755, root, root)%{_bindir}/%{name}
%attr(0755, root, root)%{_bindir}/%{name}d
%attr(0755, root, root)%{_bindir}/rstrnt-report-result
%attr(0755, root, root)%{_bindir}/rstrnt-report-log
%attr(0755, root, root)%{_bindir}/rstrnt-backup
%attr(0755, root, root)%{_bindir}/rstrnt-restore
%attr(0755, root, root)%{_bindir}/rstrnt-reboot
%attr(0755, root, root)%{_bindir}/check_beaker
/usr/share/%{name}
/usr/share/%{name}/plugins/run_plugins
/usr/share/%{name}/plugins/run_task_plugins
/usr/share/%{name}/plugins/localwatchdog.d
/usr/share/%{name}/plugins/completed.d
/usr/share/%{name}/plugins/report_result.d
/usr/share/%{name}/plugins/task_run.d
/var/lib/%{name}

%files rhts
%defattr(-,root,root,-)
%attr(0755, root, root)%{_bindir}/rhts-environment.sh
%attr(0755, root, root)%{_bindir}/rhts_environment.sh
%attr(0755, root, root)%{_bindir}/rhts-reboot
%attr(0755, root, root)%{_bindir}/rhts-report-result
%attr(0755, root, root)%{_bindir}/rhts-submit-log
%attr(0755, root, root)%{_bindir}/rhts_submit_log
%attr(0755, root, root)%{_bindir}/rhts-run-simple-test
%attr(0755, root, root)%{_bindir}/rhts-backup
%attr(0755, root, root)%{_bindir}/rhts-restore
%{_datadir}/rhts/lib/rhts-make.include
/mnt/scratchspace
%attr(1777,root,root)/mnt/testarea
%if 0%{?rhel}%{?fedora} > 4
%{_datadir}/selinux/packages/%{name}/rhts.pp
%endif

%clean
%{__rm} -rf %{buildroot}

%changelog
* Thu Mar 20 2014 Bill Peck <bpeck@redhat.com> 0.1.8-1
- allow client.c to compile on rhel4 and exclude /usr/lib/systemd on none-
  systemd systems (bpeck@redhat.com)

* Thu Mar 20 2014 Bill Peck <bpeck@redhat.com> 0.1.7-1
- fixes for systemd (bpeck@redhat.com)
- use /var/lib/restraint for running state config. also record logs in
  standalone job xml. (bpeck@redhat.com)
- fix comment (bpeck@redhat.com)
- Log errors to /dev/console and all messages to /var/log/restraintd.log
  (bpeck@redhat.com)
- Changes to support running stand alone better (bpeck@redhat.com)
- disable g_io_channel decoding which can barf on binary data.
  (bpeck@redhat.com)

* Thu Jan 23 2014 Bill Peck <bpeck@redhat.com> 0.1.6-1
- revert spec file changes so tito doesn't get confused. (bpeck@redhat.com)
- fix legacy report_result.  Was not passing args with quotes
  (bpeck@redhat.com)
- patch to fix /usr/lib64 to /usr/lib for libffi (jbastian@redhat.com)
- build libxml2 without python support (jbastian@redhat.com)
- also update libxml2-2.9.1 for aarch64 (jbastian@redhat.com)
- update third-party to libffi-3.0.13 (jbastian@redhat.com)
- Add IPV6 to TODO list (bpeck@redhat.com)
- Add TODO list. (bpeck@redhat.com)

* Tue Jan 21 2014 Bill Peck <bpeck@redhat.com> 0.1.5-1
- fix make clean targets (bpeck@redhat.com)
- fix fd leak (bpeck@redhat.com)
- fix path for backup/restore (bpeck@redhat.com)
- More legacy variables (bpeck@redhat.com)
- fix reporting of which plugins are in use. (bpeck@redhat.com)
- Fix entry_point to be an array of strings to pass into process
  (bpeck@redhat.com)
- Introduced task runner plugins (bpeck@redhat.com)
- Fix running plugins (both localwatchdog and report_result) (bpeck@redhat.com)
- use NULL term value (bpeck@redhat.com)

* Thu Jan 09 2014 Bill Peck <bpeck@redhat.com> 0.1.4-1
- Move localwatchdog plugins to a more generic plugins model.
  (bpeck@redhat.com)
- Provide TESTNAME and TESTPATH for legacy rhts (bpeck@redhat.com)
- Update build instructions (bpeck@redhat.com)
- ignore whitespace in scan. (bpeck@redhat.com)
- Look for a guestrecipe if we fail to find a regular recipe.
  (bpeck@redhat.com)
- Include rhts-run-simple-test from rhts. (bpeck@redhat.com)
- Update ignore to restrnt names (bpeck@redhat.com)
- Remember localwatchdog state, the plugins may reboot the system.
  (bpeck@redhat.com)
- disable requeueing messages for now. (bpeck@redhat.com)
- use guint64 (bpeck@redhat.com)
- Move rhts legacy into a sub-package (bpeck@redhat.com)
- Activate service after install (bpeck@redhat.com)
- fix buildroot (bpeck@redhat.com)
- Install localwatchdog plugins (bpeck@redhat.com)

* Wed Dec 18 2013 Bill Peck <bpeck@redhat.com> 0.1.3-1
- Added localwatchdog plugins (bpeck@redhat.com)
- ignore pyc file from tito (bpeck@redhat.com)
- hack to tito build to add the third-party tarballs into the release.
  (bpeck@redhat.com)
- Updates to allow restraint to build from rhel4-rhel7 on all arches we care
  about. (bpeck@redhat.com)
- few more places to switch from guint64 to gulong. (bpeck@redhat.com)
- Use unsigned long. (bpeck@redhat.com)
- Add missing BuildRequies to spec (bpeck@redhat.com)
- link process.o into restraintd fix install to create dirs really simple spec
  file (bpeck@redhat.com)
- Make it easy to grab all the tarballs needed for static linking.
  (bpeck@redhat.com)

* Tue Dec 17 2013 Bill Peck <bpeck@redhat.com> 0.1.2-1
- new package built with tito

