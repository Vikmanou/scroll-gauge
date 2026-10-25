Name:           scrollgauge
Version:        0.1.1
Release:        1%{?dist}
Summary:        Set global and per-app touchpad scroll speed on GNOME Wayland

License:        MIT
URL:            https://github.com/Vikmanou/scroll-gauge
Source0:        %{url}/archive/v%{version}/scroll-gauge-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pytest
BuildRequires:  desktop-file-utils

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Recommends:     wayland-scroll-factor

%description
Scroll Gauge is a GNOME app for setting touchpad scroll speed on Wayland. It
sets one global speed through Wayland Scroll Factor (WSF), per-app speeds
through the Touchpad Speed Control extension, and has a demo page to feel the
speed while you adjust it.

%prep
%autosetup -n scroll-gauge-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l scrollgauge

%check
%pyproject_check_import -e scrollgauge.app
%pytest
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.vikmanou.ScrollGauge.desktop

%files -f %{pyproject_files}
%doc README.md
%{_bindir}/scrollgauge
%{_datadir}/applications/io.github.vikmanou.ScrollGauge.desktop

%changelog
* Sun Oct 25 2026 Viken <68619882+Vikmanou@users.noreply.github.com> - 0.1.1-1
- First package
