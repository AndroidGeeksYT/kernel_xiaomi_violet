import os
import sys
import subprocess
import string
import random

# Generate a random temporary bash script name
bashfile=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
bashfile='/tmp/'+bashfile+'.sh'

f = open(bashfile, 'w')
s = """#!/bin/bash

# NOTE: Telegram and Pixeldrain logic removed for cleaner CI integration.
# The GitHub Actions workflow will handle logging and artifact uploads.

# Telegram Config (REMOVED, KEEPING VARS UNUSED FOR SIMPLICITY)
TOKEN=$(/usr/bin/env python -c "import os; print(os.environ.get('TOKEN'))")
CHATID=$(/usr/bin/env python -c "import os; print(os.environ.get('CHATID'))")
API_KEY=$(/usr/bin/env python -c "import os; print(os.environ.get('API_KEY'))")

# Build Machine details (STILL USED FOR LOGGING)
cores=$(lscpu | grep "Core(s) per socket" | awk '{print $NF}')
os=$(cat /etc/issue)
time=$(TZ="Asia/Dhaka" date "+%a %b %d %r")

# Placeholder functions for removed Telegram logic
tg_post_msg() {
  echo "::notice::Build message: $1"
}

tg_post_build()
{
	echo "::notice::Build file upload requested: $1"
}

kernel_dir="${PWD}"
objdir="${kernel_dir}/out"
anykernel=$HOME/anykernel
ZIMAGE=$kernel_dir/out/arch/arm64/boot/Image.gz-dtb
kernel_name="GEEK"
KERVER=$(make kernelversion)
zip_name="$kernel_name-$(date +"%d%m%Y-%H%M")-signed.zip"
export CONFIG_FILE="vendor/violet-perf_defconfig"
export ARCH="arm64"
export SUBARCH="arm64"
export CC="clang"
export LLVM="1"
export LLVM_IAS="1"
export CLANG_TRIPLE="aarch64-linux-gnu-"
export CROSS_COMPILE_ARM32="arm-linux-gnueabi-"
export LD="aarch64-linux-gnu-ld.bfd"
export KBUILD_BUILD_HOST=debian
export KBUILD_BUILD_USER=androidgeeks
LINUX_COMPILE_BY="androidgeeks"
LINUX_COMPILE_HOST="debian"

# Initial log message (using GitHub Actions logging commands for visibility)
echo "::group::Build Setup and Info"
echo "Kernel: $kernel_name"
echo "Upstream Version: $KERVER"
echo "Top Commit: $COMMIT_HEAD"
echo "::endgroup::"

# Colors
NC='\\033[0m'
RED='\\033[0;31m'
LGR='\\033[1;32m'
make_defconfig()
{
    START=$(date +"%s")
    echo -e ${LGR} "########### Generating Defconfig ############${NC}"
    make -s ARCH=${ARCH} O=${objdir} ${CONFIG_FILE} -j$(nproc --all)
}
compile()
{
    cd ${kernel_dir}
    echo -e ${LGR} "######### Compiling kernel #########${NC}"
    # The 'tee' command captures all output to error.log for artifact upload
    make -j$(nproc --all) \\
    O=out \\
    ARCH=${ARCH}\\
    CC="clang" \\
    CLANG_TRIPLE="aarch64-linux-gnu-" \\
    CROSS_COMPILE="aarch64-linux-gnu-" \\
    CROSS_COMPILE_ARM32="arm-linux-gnueabi-" \\
    LLVM=1 \\
    LLVM_IAS=1 \\
    2>&1 | tee error.log
    
    # Check the exit status of the 'make' command
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "::error::Compilation failed. See error.log artifact."
        return 1
    fi
    return 0
}
completion() {
  cd ${objdir}
  COMPILED_IMAGE=arch/arm64/boot/Image.gz-dtb
  COMPILED_DTBO=arch/arm64/boot/dtbo.img
  
  # Check for successful compilation files
  if [[ -f ${COMPILED_IMAGE} && -f ${COMPILED_DTBO} ]]; then
    echo "::group::Packaging Kernel ZIP"
    git clone -q https://github.com/AndroidGeeksYT/AnyKernel3 $anykernel
    mv -f $ZIMAGE ${COMPILED_DTBO} $anykernel
    cd $anykernel
    
    # Clean up old zips and create new one
    find . -name "*.zip" -type f -delete
    zip -r AnyKernel.zip *
    
    # Sign the ZIP file
    curl -sLo zipsigner-3.0.jar https://github.com/Magisk-Modules-Repo/zipsigner/raw/master/bin/zipsigner-3.0-dexed.jar
    if ! command -v java &> /dev/null
    then
        echo "Java not found. Installing OpenJDK..."
        # Install java to run zipsigner.jar
        sudo apt-get install -y openjdk-17-jdk
    fi
    java -jar zipsigner-3.0.jar AnyKernel.zip AnyKernel-signed.zip
    
    # Move and rename the final artifact to the $HOME directory
    mv AnyKernel-signed.zip $zip_name
    mv $anykernel/$zip_name $HOME/$zip_name
    
    # Clean up
    rm -rf $anykernel

    # Calculate and display build time
    END=$(date +"%s")
    DIFF=$(($END - $START))
    file_path="$HOME/$zip_name"
    zip_size=$(du -h $HOME/$zip_name | awk '{print $1}')

    echo "::notice::Kernel packaging successful."
    echo "Final ZIP: $file_path (Size: $zip_size)"
    echo "Build Time: $((DIFF / 60)) minute(s) and $((DIFF % 60)) second(s)"
    echo -e ${LGR} "\n############################################"
    echo -e ${LGR} "############# OkThisIsEpic!  ##############"
    echo -e ${LGR} "############################################${NC}"
    echo "::endgroup::"

  else
    echo "::error::Kernel image or DTBO file not found. Packaging failed."
    exit 1 # Exit with error code so GitHub Actions captures the failure
  fi
}

# --- Execution Flow ---
if make_defconfig; then
  tg_post_msg "<code>Defconfig generated successfully</code>"
  if compile; then
    completion
  else
    # Compile failed, ensure error.log is available
    tg_post_msg "<code>Compilation failed</code>"
    echo -e ${RED} "############################################"
    echo -e ${RED} "##         This Is Not Epic :'(           ##"
    echo -e ${RED} "############################################${NC}"
    exit 1 # Important for GitHub Actions to mark the job as failed
  fi
else
    # Defconfig failed
    echo "::error::Defconfig step failed. Aborting build."
    exit 1
fi

cd ${kernel_dir}
"""
f.write(s)
f.close()
os.chmod(bashfile, 0o755)
bashcmd=bashfile
for arg in sys.argv[1:]:
  bashcmd += ' '+arg
subprocess.call(bashcmd, shell=True)
