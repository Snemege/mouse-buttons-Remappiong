%global app_id io.github.snemege.MouseButtons

Name:           mouse-buttons
Version:        0.1.0
Release:        1%{?dist}
Summary:        Assign actions to mouse buttons on Linux (GNOME, Wayland)

License:        GPL-3.0-or-later
URL:            https://github.com/Snemege/mouse-buttons
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  appstream
BuildRequires:  desktop-file-utils
BuildRequires:  python3
BuildRequires:  python3-evdev
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-evdev
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       glib2
Requires:       systemd
Requires:       hicolor-icon-theme

%description
Mouse Buttons lets you assign actions to your mouse buttons: switch between
workspaces with the side buttons, launch installed applications, send custom
keyboard shortcuts or run commands. It includes a live button test, an English
and Turkish interface, and recovers automatically when a mouse is unplugged
(for example when a KVM switch changes computers).

It works on Wayland. A background service reads the mouse devices, intercepts
only the buttons you assigned and forwards every other event unchanged.

%prep
%autosetup

%build
# nothing to build

%install
install -Dpm 0755 mouse_buttons.py %{buildroot}%{_bindir}/%{name}
install -Dpm 0644 data/70-mouse-buttons.rules %{buildroot}%{_udevrulesdir}/70-%{name}.rules
install -Dpm 0644 data/70-mouse-buttons.preset %{buildroot}%{_userpresetdir}/70-%{name}.preset
install -Dpm 0644 data/%{app_id}.metainfo.xml %{buildroot}%{_metainfodir}/%{app_id}.metainfo.xml
install -d %{buildroot}%{_userunitdir}
sed 's|@PYTHON@ @SCRIPT@|%{_bindir}/%{name}|' data/mouse-buttons.service.in \
    > %{buildroot}%{_userunitdir}/%{name}.service
sed 's|@PYTHON@ @SCRIPT@|%{name}|' data/%{app_id}.desktop.in > %{app_id}.desktop
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{app_id}.desktop
for size in 48x48 64x64 128x128 256x256 512x512; do
    install -Dpm 0644 data/icons/hicolor/$size/apps/%{app_id}.png \
        %{buildroot}%{_datadir}/icons/hicolor/$size/apps/%{app_id}.png
done

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/%{app_id}.metainfo.xml
%{buildroot}%{_bindir}/%{name} --version

%post
%systemd_user_post %{name}.service
# apply the udev rule to mice that are already plugged in
/usr/bin/udevadm control --reload >/dev/null 2>&1 || :
/usr/bin/udevadm trigger --subsystem-match=input --action=change >/dev/null 2>&1 || :

%preun
%systemd_user_preun %{name}.service

%files
%license LICENSE
%doc README.md README.tr.md
%{_bindir}/%{name}
%{_udevrulesdir}/70-%{name}.rules
%{_userunitdir}/%{name}.service
%{_userpresetdir}/70-%{name}.preset
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/*/apps/%{app_id}.png
%{_metainfodir}/%{app_id}.metainfo.xml

%changelog
* Mon Sep 21 2026 Snemege <86289361+Snemege@users.noreply.github.com> - 0.1.0-1
- Initial package
