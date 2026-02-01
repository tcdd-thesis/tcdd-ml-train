#!/bin/bash -e
ENV_FILE=".env.hef-conversion-hyperv"

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Missing env file, creating..."
    echo "Edit $ENV_FILE and set all required variables, then try again."
    touch "$ENV_FILE"
    echo "VM_NAME=" >> "$ENV_FILE"
    echo "WSL2_BRANCH=linux-msft-wsl-5.15.y" >> "$ENV_FILE"
    exit
fi

# Get BRANCH from .env file
BRANCH=$(grep -oP 'WSL2_BRANCH=\K.*' "$ENV_FILE")

if [ "$EUID" -ne 0 ]; then
    echo "Swithing to root..."
    exec sudo $0 "$@"
fi

sudo apt install dwarves
cp /sys/kernel/btf/vmlinux /usr/lib/modules/$(uname -r)/build/

apt-get install -y git dkms

git clone -b $BRANCH --depth=1 https://github.com/microsoft/WSL2-Linux-Kernel
cd WSL2-Linux-Kernel
VERSION=$(git rev-parse --short HEAD)

cp -r drivers/hv/dxgkrnl /usr/src/dxgkrnl-$VERSION
mkdir -p /usr/src/dxgkrnl-$VERSION/inc/{uapi/misc,linux}
cp include/uapi/misc/d3dkmthk.h /usr/src/dxgkrnl-$VERSION/inc/uapi/misc/d3dkmthk.h
cp include/linux/hyperv.h /usr/src/dxgkrnl-$VERSION/inc/linux/hyperv_dxgkrnl.h
sed -i 's/\$(CONFIG_DXGKRNL)/m/' /usr/src/dxgkrnl-$VERSION/Makefile
sed -i 's#linux/hyperv.h#linux/hyperv_dxgkrnl.h#' /usr/src/dxgkrnl-$VERSION/dxgmodule.c
echo "EXTRA_CFLAGS=-I\$(PWD)/inc" >> /usr/src/dxgkrnl-$VERSION/Makefile

cat > /usr/src/dxgkrnl-$VERSION/dkms.conf <<EOF
PACKAGE_NAME="dxgkrnl"
PACKAGE_VERSION="$VERSION"
BUILT_MODULE_NAME="dxgkrnl"
DEST_MODULE_LOCATION="/kernel/drivers/hv/dxgkrnl/"
AUTOINSTALL="yes"
EOF

dkms add dxgkrnl/$VERSION
dkms build dxgkrnl/$VERSION
dkms install dxgkrnl/$VERSION
