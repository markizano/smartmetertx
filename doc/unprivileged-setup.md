I don't like scripts running as root or as myself which has unrestricted `sudo` access.
So I often times will create an account specifically for that script and even sometimes a `venv` for it as well.

This document helps describe how you can set this up for yourself.

**Assume all commands are run as root.**

First I create a group for my apps using:

```bash
groupadd --gid=200 apps
```

Then I can create a system account for the smartmeter tx app like so:

```bash
adduser --home=/home/smartmetertx --gid=200 smartmetertx
```

This will also ensure the `gid` for the user account is already set to the `apps` group. In this way, apps can share a group if needed.

Next, I create a virtual environment for this user account to have its software installed to its home directory:

```bash
apt-get install -y python3-venv
sudo -H -usmartmetertx -gapps python3 -m venv /home/smartmetertx
```

Finally, I use the virtual environment to install the app:

```bash
sudo -H -usmartmetertx bash -c 'source ~/bin/activate && pip install smartmetertx2mongo'
```

The parenthesis are significant in that it puts this command in a [subshell](https://linux.die.net/man/1/bash#:~:text=The%20shell%20has%20an%20execution%20environment,%20which%20consists%20of%20the%20following).
If you omit them, it may glob into your current working shell. If that's intended, you can omit them.

In this way, the script can run as an unprivileged user and in its own virtual environment to avoid clashing with the package manager and the main parts of the system.

If you get a response like this (which you should not in a virtual environment):

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
    
    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.
    
    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.
    
    See /usr/share/doc/python3.11/README.venv for more information.

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
```

Double-check to make sure your virtual environment is active (you may have to run `. ~/bin/activate` since I think `source` is a bashism whereas dot `.` is a universal shell inclusion).

Personally, I only install enough python to get the basics installed and use `pip` for anything beyond that, but maybe I'm legacy like that or pro -- I can't tell the difference anymore.
