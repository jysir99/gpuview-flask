
![Screenshot of gpuview](imgs/image.png)


gpuview-flask: 
---------------------

gpuview-flask is a lightweight web dashboard for monitoring GPU status across multiple servers. It eliminates the need to SSH into machines to check GPU usage, temperature, memory, and active users. Instead, it provides a real-time, user-friendly interface accessible from a web browser.

This version of [gpuview](https://github.com/fgaim/gpuview) has been refactored using Flask, making it more scalable and efficient. It also introduces Vue.js for a responsive frontend, integrates Flask-Caching for optimized performance, and includes an auto-refresh feature to ensure up-to-date GPU information without manual intervention.

Key Features
---------------------

- **Real-time GPU Monitoring** – View GPU usage, temperature, memory consumption, and active users.
- **Color-Coded Visualization**
  - Upper Section: Displays GPU temperature with different colors for intuitive monitoring.
  - Lower Section: Shows GPU memory usage with distinct colors for quick assessment.
- **Auto-Refresh** – Continuously updates GPU stats without manual refresh.
- **Lightweight & Scalable** – Built with Flask and Vue.js for efficiency and responsiveness.


Setup
-----

Install directly from repo:

```
$ pip install git+https://github.com/bei9/gpuview-flask.git
```

> `gpuview` installs the latest version of `gpustat` from `pypi`, therefore, its commands are available
> from the terminal.

Usage
-----

`gpuview` can be used in two modes as a temporary process or as a background service.

### Run gpuview

Once `gpuview` is installed, it can be started as follows:

```
$ gpuview run --safe-zone
```

This will start the dasboard at `http://0.0.0.0:9988`.

By default, `gpuview` runs at `0.0.0.0` and port `9988`, but these can be changed using `--host` and `--port`. The `safe-zone` option means report all detials including usernames, but it can be turned off for security reasons.

### Run as a Service

To permanently run `gpuview` it needs to be deployed as a background service.
This will require a `sudo` privilege authentication.
The following command needs to be executed only once:

```
$ gpuview service [--safe-zone] [--exlude-self]
```

If successful, the `gpuview` service is run immediately and will also autostart at boot time. It can be controlled using `supervisorctl start|stop|restart gpuview`.

### Runtime options

There a few important options in `gpuview`, use `-h` to see them all.

```
$ gpuview -h
```

* `run`                : Start `gpuview` dashboard server
  * `--host`           : URL or IP address of host (default: 0.0.0.0)
  * `--port`           : Port number to listen to (default: 9988)
  * `--safe-zone`      : Safe to report all details, eg. usernames
  * `--exclude-self`   : Don't report to others but to self-dashboard
  * `-d`, `--debug`    : Run server in debug mode (for developers)
* `add`                : Add a GPU host to dashboard
  * `--url`            : URL of host [IP:Port], eg. X.X.X.X:9988
  * `--name`           : Optional readable name for the host, eg. Node101
* `remove`             : Remove a registered host from dashboard
  * `--url`            : URL of host to remove, eg. X.X.X.X:9988
* `hosts`              : Print out all registered hosts
* `service`            : Install `gpuview` as system service
  * `--host`           : URL or IP address of host (default: 0.0.0.0)
  * `--port`           : Port number to listen to (default: 9988)
  * `--safe-zone`      : Safe to report all details, eg. usernames
  * `--exclude-self`   : Don't report to others but to self-dashboard
* `-v`, `--version`    : Print versions of `gpuview` and `gpustat`
* `-h`, `--help`       : Print help for command-line options

### Monitoring multiple hosts

To aggregate the stats of multiple machines, they can be registered to one dashboard using their address and the port number running `gpustat`.

Register a host to monitor as follows:

```
$ gpuview add --url <ip:port> --name <name>
```

Remove a registered host as follows:

```
$ gpuview remove --url <ip:port> --name <name>
```

Display all registered hosts as follows:

```
$ gpuview hosts
```

> Note: the `gpuview` service needs to run in all hosts that will be monitored.

> Tip: `gpuview` can be setup on a none GPU machine, such as laptops, to monitor remote GPU servers.

etc
---

Helpful tips related to the underlying performance are available at the  repo.

For the sake of simplicity, `gpuview` does not have a user authentication in place. As a security measure,
it does not report sensitive details such as user names by default. This can be changed if the service is
running in a trusted network, using the `--safe-zone` option to report all details.

The `--exclude-self` option of the run command can be used to prevent other dashboards from getting stats of the current machine. This way the stats are shown only on the host's own dashboard.

Detailed view of GPUs across multiple servers.

![Screenshot of gpuview](imgs/dash-2.png)

License
-------

[MIT License](LICENSE)

[repo_gpustat]: https://github.com/wookayin/gpustat
[pypi_gpuview]: https://pypi.python.org/pypi/gpuview
