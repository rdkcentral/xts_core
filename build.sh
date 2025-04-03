#!/usr/bin/env bash
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

MY_PATH="$(realpath ${BASH_SOURCE[0]})"
MY_DIR="$(dirname ${MY_PATH})"

NO_COLOR="\e[0m"
RED="\e[0;31m"
CYAN="\e[0;36m"
YELLOW="\e[1;33m"
GREEN="\e[0;32m"
RED_BOLD="\e[1;31m"
BLUE_BOLD="\e[1;34m"
YELLOW_BOLD="\e[1;33m"

DEBUG_FLAG=0
function ECHO()
{
	echo -e "$*"
}

function DEBUG()
{
	# if set -x is in use debug messages are useless as whole stript will be shown
	if [[ "$-" =~ "x" ]]; then
		return
	fi
  if [[ "${DEBUG_FLAG}" == "1" ]];then
  	ECHO "${BLUE_BOLD}DEBUG: ${CYAN}$*${NO_COLOR}" > /dev/stderr
  fi
}

function INFO()
{
	ECHO "${GREEN}$*${NO_COLOR}"
}

function WARNING()
{
	ECHO "${YELLOW_BOLD}Warning: ${YELLOW}$*${NO_COLOR}" > /dev/stderr
}

function ERROR()
{
	ECHO "${RED_BOLD}ERROR: ${RED}$*${NO_COLOR}"
	exit 1
}

function version_check()
{
# Check if a version is correct or not
# Arguments:
#   $1: Version to check
#   $2: Required version
#         +: as the last character can be used to signify any version over the given number.
#         -: as the last character can be used to signify any version below the given number.
#
    DEBUG "${FUNCNAME} $*"
    local check_version="$1"
    local required_version="$2"
    local check_version_split=(${check_version//\./" "})
    local req_version_split=(${required_version//\./" "})
    local stop=$(("${#req_version_split[@]}"-1))
    for i in $(seq 0 ${stop})
    do
        local req_version_section="${req_version_split[$i]}"
        DEBUG "Req Version Sect: [${req_version_section}]"
        local check_version_section="${check_version_split[$i]}"
        DEBUG "Check Version Sect: [${check_version_section}]"
        case "${req_version_section}" in
            *"+")
                # Remove the + from the end of the string
                req_version_section="${req_version_section%+}"
                if [[ "$check_version_section" -ge "${req_version_section}" ]];then
                    return 1
                fi
                return 0
                ;;
            *"-")
                # Remove the - from end of the string
                req_version_section="${req_version_section%-}"
                if [[ "$check_version_section" -le "${req_version_section}" ]];then
                    return 1
                fi
                return 0
                ;;
            *)
                if [[ "${check_version_section}" != "${req_version_section}" ]];then
                    return 0
                fi
                ;;
        esac
    done
    return 1
}

function check_python_env()
{
    local installed=()
    local required=()
    readarray -t installed < <(python3 -m pip list | tail -n +3)
    readarray -t required < <(cat ${MY_DIR}/requirements.txt | sed 's/[<>=]/ /g')
    for req_pkg in "${required[@]}"
    do
        local match=""
        local req_pkg_array=($(echo "${req_pkg}" | awk '{print $1" "$NF}'))
        for installed_pkg in "${installed[@]}"
        do
            local installed_name="$(echo ${installed_pkg}| awk '{print $1}')"
            if [[ "${req_pkg_array[0]}" == "${installed_name}" ]];then
                match=${installed_pkg}
                break
            fi
        done
        if [[ -n "${match}" ]]; then
            #Package is installed, check the version
            match_version="$(echo ${match} | awk '{print $NF}')"
            if (version_check "${match_version}" "${req_pkg_array[1]}+");then
                WARNING "Package [${req_pkg_array[0]}] is required to be at verison [${req_pkg_array[1]}+] but is at [${match_version}]"
                return 0
            fi
        else
            WARNING "Package [${req_pkg_array[0]}] is not installed"
            return 0
        fi
    done
    return 1
}

function create_python_venv()
{
    local venv_dir="${MY_DIR}/python_venv"
    local create_env=1
    if [[ -e "${venv_dir}" ]];then
        if [[ -e "${venv_dir}/bin/activate" ]];then
            create_env=0
        else
            ERROR "${venv_dir} already exists but is not a python virtual environment.\n \
                    please rename or delete it"
        fi
    fi
    if [[ "${create_env}" ]];then
        mkdir -p "${venv_dir}"
        python3 -m venv "${venv_dir}"
    fi
    source "${venv_dir}/bin/activate"
    pip install -qr "${MY_DIR}/requirements.txt" 2>&1 >/dev/null
}


### MAIN ###
# Check the python3 version is correct
python_version="$(python3 --version | awk '{print $NF}')"
if [[ -n "${python_version}" ]];then
    if (version_check "${python_version}" "3.10+");then
        ERROR "Installed python3 version is [${python_version}], but version 3.10+ is required"
    fi
else
    ERROR "python3 is not installed. python 3.10+ is required"
fi

# Check the python environment has the packages required
if (check_python_env);then
    WARNING "Python environment incorrect, creating virtual environment"
    create_python_venv
fi

# Build the xts_core binary
pyinstaller -F "${MY_DIR}/src/xts.py" --distpath "${MY_DIR}/bin/" > "${MY_DIR}"/build.log 2>&1

INFO "Please run the following commands:\n"
ECHO "export PATH=\"${MY_DIR}/bin:\$PATH\""
INFO "\nTo permanently install this, add the export command as a line in your ~/.bashrc file"
