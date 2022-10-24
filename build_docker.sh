#!/bin/bash

# script to build images for FlowerEvolver-backend
#
# $1 OS to build "ubuntu" or "alpine"
# sh build_docker.sh "alpine"
function usage(){
    echo "usage:"
    echo "     sh build_docker.sh \"alpine\""
    echo "     sh build_docker.sh \"ubuntu\""
}
case $1 in

   "ubuntu")
# we dont need to compile, bin has ubuntu binaries
    echo "building docker Ubuntu..."
    docker build -t cristianglezm/fe:backend-ubuntu-dev -f dockerfile.ubuntu .
   ;;

   "alpine")
    echo "building docker Alpine..."
    echo "cloning required repositories..."
# download repositories into tmp
    if [ ! -d "tmp" ]
    then
     mkdir tmp
    fi
    cd tmp
    if [ -d "JsonBox" ]
    then
        cd JsonBox && git pull && cd ..
    else
        git clone https://github.com/cristianglezm/JsonBox.git
    fi
    if [ -d "SPPAR" ]
    then
        cd SPPAR && git pull && cd ..
    else
        git clone https://github.com/cristianglezm/SPPAR.git
    fi
    if [ -d "EvoAI" ]
    then
        cd EvoAI && git checkout refactor-activations && git pull && cd ..
    else
        git clone https://github.com/cristianglezm/EvoAI.git
        cd EvoAI && git checkout refactor-activations && cd ..
    fi
    if [ -d "EcoSystem" ]
    then
        cd EcoSystem && git pull && cd ..
    else
        git clone https://github.com/cristianglezm/EcoSystem.git
    fi
    cd ..
    pwd
    docker build -t cristianglezm/fe:backend-alpine-dev -f dockerfile.alpine .
    #rm -R tmp
   ;;

   *)
    usage
   ;;

esac
