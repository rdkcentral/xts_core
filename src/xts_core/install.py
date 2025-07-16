#!/usr/bin/env python3
#** *****************************************************************************
# *
# * If not stated otherwise in this file or this component's LICENSE file the
# * following copyright and licenses apply:
# *
# * Copyright 2024 RDK Management
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *
# http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *
#* ******************************************************************************

import datetime
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from .utils import info, error, warning

def main():
    if 'Linux' in platform.platform():
        _linux_install()
    else:
        error('Unfortunately XTS does not currently support your OS')

def _linux_install():
    script_path = Path(__file__).absolute()
    script_dir = Path(os.path.dirname(script_path))
    user_home = Path('.').home()
    xts_dir = user_home.joinpath(Path('.xts'))
    bin_dir = xts_dir.joinpath(Path('bin'))
    log_dir = xts_dir.joinpath(Path('logs'))
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_dir_path = Path(tmp_dir.name)
    info(f'Created temporary workspace: {tmp_dir_path}')
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    result = subprocess.run(['pyinstaller',
                    '--onefile',
                    f'{script_dir}/xts.py',
                    '--name',
                    'xts',
                    '--distpath',
                    f'{bin_dir}',
                    '--collect-all',
                    'xts_core',
                    '--workpath',
                    f'{tmp_dir_path}',
                    '--specpath',
                    f'{tmp_dir_path}'
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True)
    info(f'Cleaning up temporary workspace: {tmp_dir_path}')
    try:
        tmp_dir.cleanup()
    except:
        warning(f'Could not cleanup temporary workspace: {tmp_dir_path}')
    log_file = log_dir.joinpath(f'build_{datetime.datetime.now()}.log')
    with open(log_file,'w+') as f:
        f.write(result.stdout)
    if result.returncode != 0:
        error('Something went wrong trying to install xts\n'+
                f'Please check the log for more info: [{log_file}]\n' + 
                'Raise an issue on xts_core for more help:\n'+
                'https://github.com/rdkcentral/xts_core/issues/new?template=01-bugs.yml')
    else:
        info('XTS has been installed successfully.\n'+
                'Please run the following commands:\n' +
                f'\texport PATH="{bin_dir}:$PATH"\n' +
                'To permanently install this, add the export command as a line in your ~/.bashrc file')

if __name__ == '__main__':
    main()