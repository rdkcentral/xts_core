#!/usr/bin/env bash

MY_PATH="$(realpath ${BASH_SOURCE[0]})"
MY_DIR="$(dirname ${MY_PATH})"
BIN_DIR="${MY_DIR}/bin"

echo "Please run the following commands:" 1>&2
echo ""
echo "pip install -r ${MY_DIR}/requirement.txt"
echo "export PATH=\"${BIN_DIR}:\$PATH\""
echo ""
echo "To permanently install this, add the export command as a line in your ~/.bashrc file" 1>&2