#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: cli.py
# modified: 2020-02-20

from optparse import OptionParser
from threading import Thread
from multiprocessing import Queue
import sys

from . import __version__, __date__


def create_default_parser():

    parser = OptionParser(
        description='PKU Auto-Elective Tool v%s (%s)' % (__version__, __date__),
        version=__version__,
    )

    ## custom input files

    parser.add_option(
        '-c',
        '--config',
        dest='config_ini',
        metavar="FILE",
        help='custom config file encoded with utf8',
    )

    parser.add_option(
        '-a',
        '--apikey',
        dest='apikey_json',
        metavar="FILE",
        help='custom TTShitu API key file encoded with utf8',
    )

    ## boolean (flag) options

    parser.add_option(
        '-m',
        '--with-monitor',
        dest='with_monitor',
        action='store_true',
        default=False,
        help='run the monitor thread simultaneously',
    )

    parser.add_option(
        '--check-config',
        dest='check_config',
        action='store_true',
        default=False,
        help='validate local configuration without logging in or sending requests',
    )

    return parser


def setup_default_environ(options, args, environ):

    environ.config_ini = options.config_ini
    environ.apikey_json = options.apikey_json
    environ.with_monitor = options.with_monitor


def create_default_threads(options, args, environ):

    # import here to ensure the singleton `config` will be init later than parse_args()
    from autoelective.loop import run_iaaa_loop, run_elective_loop
    from autoelective.monitor import run_monitor

    tList = []

    t = Thread(target=run_iaaa_loop, name="IAAA")
    environ.iaaa_loop_thread = t
    tList.append(t)

    t = Thread(target=run_elective_loop, name="Elective")
    environ.elective_loop_thread = t
    tList.append(t)

    if options.with_monitor:
        t = Thread(target=run_monitor, name="Monitor")
        environ.monitor_thread = t
        tList.append(t)

    return tList


def validate_configuration():
    """Validate both private configuration files without making network requests."""
    from .captcha.online import APIConfig
    from .config import AutoElectiveConfig

    config = AutoElectiveConfig()
    config.check_identify(config.identity)
    config.check_supply_cancel_page(config.supply_cancel_page)

    if not config.iaaa_id.strip() or config.iaaa_id.upper().endswith('_HERE'):
        raise ValueError('student_id has not been configured')
    if not config.iaaa_password.strip() or config.iaaa_password.upper().endswith('_HERE'):
        raise ValueError('IAAA password has not been configured')
    if config.refresh_interval <= 0:
        raise ValueError('refresh_interval must be greater than 0')
    if config.iaaa_client_timeout <= 0 or config.elective_client_timeout <= 0:
        raise ValueError('client timeouts must be greater than 0')
    if not 1 <= config.elective_client_pool_size <= 5:
        raise ValueError('elective_client_pool_size must be between 1 and 5')
    if config.elective_client_max_life != -1 and config.elective_client_max_life <= 0:
        raise ValueError('elective_client_max_life must be -1 or greater than 0')
    if config.login_loop_interval < 0:
        raise ValueError('login_loop_interval cannot be negative')
    if config.verbosity not in (1, 2):
        raise ValueError('notification verbosity must be 1 or 2')

    courses = config.courses
    if not courses:
        raise ValueError('no [course:ID] section is configured')

    for mutex_id, mutex in config.mutexes.items():
        if len(mutex.cids) < 2:
            raise ValueError("mutex:%s must contain at least two courses" % mutex_id)
        unknown = [course_id for course_id in mutex.cids if course_id not in courses]
        if unknown:
            raise ValueError("mutex:%s references unknown courses: %s" % (mutex_id, ', '.join(unknown)))

    for delay_id, delay in config.delays.items():
        if delay.cid not in courses:
            raise ValueError("delay:%s references unknown course: %s" % (delay_id, delay.cid))

    api = APIConfig()
    if not api.uname.strip() or api.uname.upper().endswith('_HERE'):
        raise ValueError('TTShitu username has not been configured')
    if not api.pwd.strip() or api.pwd.upper().endswith('_HERE'):
        raise ValueError('TTShitu password has not been configured')
    if api.typeid <= 0:
        raise ValueError('RecognitionTypeid must be greater than 0')
    if api.timeout <= 0:
        raise ValueError('TTShitu Timeout must be greater than 0')

    return len(courses), len(config.mutexes), len(config.delays)


def run():

    from .environ import Environ

    environ = Environ()

    parser = create_default_parser()
    options, args = parser.parse_args()

    setup_default_environ(options, args, environ)

    try:
        course_count, mutex_count, delay_count = validate_configuration()
    except (OSError, ValueError, UserWarning) as exc:
        print('Configuration error: %s' % exc, file=sys.stderr)
        print('Edit config.ini and apikey.json, then run --check-config again.', file=sys.stderr)
        return 2

    print(
        'Configuration OK: %d course(s), %d mutex rule(s), %d delay rule(s).'
        % (course_count, mutex_count, delay_count)
    )

    if options.check_config:
        return 0

    tList = create_default_threads(options, args, environ)

    for t in tList:
        t.daemon = True
        t.start()

    #
    # Don't use join() to block the main thread, or Ctrl + C in Windows can't work.
    #
    # for t in tList:
    #     t.join()
    #
    try:
        Queue().get()
    except KeyboardInterrupt as e:
        pass

    return 0
