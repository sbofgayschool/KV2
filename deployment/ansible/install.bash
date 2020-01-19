#!/bin/bash

if [[ -x "$(command -v ansible)" ]]; then
    echo "============================"
    echo "Ansible has already been installed."
    echo "============================"
    echo ""
    exit 0
fi

echo "============================"
echo "Installing Ansible."
echo "============================"
echo ""

python3 -m pip install --upgrade pip
python3 -m pip install --user ansible
mkdir ~/.ansible
cp -R install/* ~/.ansible/
ln ~/.ansible/ansible.cfg ~/.ansible.cfg

echo ""
echo "============================"
echo "Testing ansible with ansible --version."
echo "============================"
echo ""

ansible --version

echo ""
echo "============================"
echo "Ansible Successfully installed."
echo "============================"
echo ""
