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
import importlib_resources
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import xts_core

from .utils import info, error, warning

SCRIPT_PATH = Path(__file__).absolute()
SCRIPT_DIR = Path(os.path.dirname(SCRIPT_PATH))

def main():
    if 'Linux' in platform.platform():
        _linux_install()
    else:
        error('Unfortunately XTS does not currently support your OS')

def _linux_install():
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
                    f'{SCRIPT_DIR}/xts.py',
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
        shell = os.environ.get('SHELL','')
        match shell:
            case '/bin/bash':
                _install_bash(user_home)
                info('XTS has been installed successfully.\n')
            case _:
                warning('XTS has been installed successfully, but we could not automatically add xts to your PATH.\n' +
                        'Please add the following line to your shell config file:\n' +
                        f'export PATH="{user_home.joinpath(Path(".xts/bin"))}:$PATH"\n')

def _install_bash(user_home: Path):
    if (bashrc:=user_home.joinpath(Path('.bashrc'))).exists():
        with open(user_home.joinpath(Path('.bashrc')), 'a') as f:
            f.write('\n# XTS PATH\n')
            f.write(f'export PATH="{user_home.joinpath(Path(".xts/bin"))}:$PATH"\n')
            _install_bash_completion(bashrc)
    elif (bash_profile:=user_home.joinpath(Path('.bash_profile'))).exists():
        with open(user_home.joinpath(Path('.bash_profile')), 'a') as f:
            f.write('\n# XTS PATH\n')
            f.write(f'export PATH="{user_home.joinpath(Path(".xts/bin"))}:$PATH"\n')
            _install_bash_completion(bash_profile)
    else:
        warning('Could not find .bashrc or .bash_profile to add xts to PATH. Please add the following line to your shell config file:\n' +
                f'export PATH="{user_home.joinpath(Path(".xts/bin"))}:$PATH"\n')

def _install_bash_completion(rc_file: Path):
    user_home = rc_file.parent
    bash_completion_dir = user_home.joinpath(Path('.bash_completion.d'))
    if not bash_completion_dir.exists():
        os.makedirs(bash_completion_dir)
    bash_completion_script = bash_completion_dir.joinpath(Path('xts_bash_completion.sh'))
    with importlib_resources.open_text(xts_core,'data/xts_bash_completion.sh', encoding='utf-8') as src, \
         open(bash_completion_script, 'w') as dst:
        dst.write(src.read())
    rc_content = rc_file.read_text(encoding='utf-8')
    if 'xts_bash_completion.sh' not in rc_content:
        with open(rc_file, 'a', encoding='utf-8') as f:
            f.write('\n# XTS bash completion\n')
            f.write(f'source {bash_completion_dir}/xts_bash_completion.sh\n')

if __name__ == '__main__':
    main()