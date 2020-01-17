#!/bin/bash

if [[ -x "$(command -v ansible)" ]]; then
    echo "Ansible has already been installed."
fi

echo "================================="
echo "Installing Ansible."
echo "================================="
echo ""

python3 -m pip install ansible
cp -R install/* ~/.ansible/
ln ~/.ansible/ansible.cfg ~/.ansible.cfg

echo ""
echo "================================="
echo "Testing ansible with ansible -v."
echo "================================="
echo ""

ansible -v

echo ""
echo "================================="
echo "Ansible Successfully installed."
echo "================================="
echo ""
