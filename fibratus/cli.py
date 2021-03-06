# Copyright 2015 by Nedim Sabic (RabbitStack)
# All Rights Reserved.
# http://rabbitstack.github.io

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Usage:
    fibratus run ([--filament=<filament>] | [--filters <kevents>...]) [--no-enum-handles] [--cswitch]
    fibratus list-kevents
    fibratus list-filaments
    fibratus -h | --help
    fibratus --version

Options:
    -h --help                 Show this screen.
    --filament=<filament>     Specify the filament to execute.
    --no-enum-handles         Avoids enumerating the system handles.
    --cswitch                 Enables context switch kernel events.
    --version                 Show version.
"""
import sys

from docopt import docopt

from fibratus.apidefs.sys import set_console_ctrl_handler, PHANDLER_ROUTINE
from fibratus.asciiart.tabular import Tabular
from fibratus.common import IO
from fibratus.errors import FilamentError
from fibratus.fibratus_entrypoint import Fibratus
from fibratus.filament import Filament
from fibratus.kevent import KEvents
from fibratus.version import VERSION

args = docopt(__doc__, version=VERSION)

kevent_filters = args['<kevents>']
filament_name = args['--filament'] if args['--filament'] else None


def _check_kevent(kevent):
    if kevent not in KEvents.all():
        IO.write_console('fibratus run: ERROR - %s is not a valid kernel event. Run list-kevents to see'
                         ' the available kernel events' % kevent)
        sys.exit()


def main():
    if args['run']:
        if len(kevent_filters) > 0 and not filament_name:
            for kfilter in kevent_filters:
                _check_kevent(kfilter)

        enum_handles = False if args['--no-enum-handles'] else True
        cswitch = True if args['--cswitch'] else False

        filament = None
        filament_filters = []

        if not filament_name:
            IO.write_console('Starting fibratus...', False)
        else:
            if not Filament.exists(filament_name):
                IO.write_console('fibratus run: ERROR - %s filament does not exist. Run list-filaments to see '
                                 'the availble filaments' % filament_name)
                sys.exit()
            filament = Filament()
            try:
                filament.load_filament(filament_name)
            except FilamentError as e:
                IO.write_console('fibratus run: ERROR - %s' % e)
                sys.exit()

            filament_filters = filament.filters

            if len(filament_filters) > 0:
                for kfilter in filament_filters:
                    _check_kevent(kfilter)

            filament.render_tabular()

        try:
            fibratus = Fibratus(filament, enum_handles=enum_handles, cswitch=cswitch)
        except KeyboardInterrupt:
            # the user has stopped command execution
            # before opening the kernel event stream
            sys.exit(0)

        @PHANDLER_ROUTINE
        def handle_ctrl_c(event):
            if event == 0:
                fibratus.stop_ktrace()
            return 0
        set_console_ctrl_handler(handle_ctrl_c, True)

        if not filament:
            if len(kevent_filters) > 0:
                fibratus.add_filters(kevent_filters)
        else:
            if len(filament_filters) > 0:
                fibratus.add_filters(filament_filters)
            else:
                fibratus.add_filters([])
        try:
            fibratus.run()
        except KeyboardInterrupt:
            set_console_ctrl_handler(handle_ctrl_c, False)

    elif args['list-filaments']:
        filaments = Tabular(['Filament', 'Description'], 'Description',
                            sort_by='Filament')
        for filament, desc in Filament.list_filaments().items():
            filaments.add_row([filament, desc])
        filaments.draw()

    elif args['list-kevents']:
        kevents = Tabular(['KEvent', 'Category', 'Description'], 'Description',
                          sort_by='Category')
        for kevent, meta in KEvents.meta_info().items():
            kevents.add_row([kevent, meta[0].name, meta[1]])
        kevents.draw()
