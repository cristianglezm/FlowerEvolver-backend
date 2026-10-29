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
    echo "building docker Ubuntu..."
    docker build -t cristianglezm/fe:backend-ubuntu-dev -f dockerfile.ubuntu .
   ;;

   "alpine")
    echo "building docker Alpine..."
    docker build -t docker.io/cristianglezm/fe:backend-alpine-dev -f dockerfile.alpine .
   ;;

   *)
    usage
   ;;

esac
