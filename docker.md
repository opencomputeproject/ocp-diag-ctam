# Docker Set-up
Packaging for CTAM requires the following things:

- Docker
- A docker compatible container run time
- Docker's cross platform build plugin: buildx

## Ubuntu Set-up
Requires Ubuntu 20.04 or newer.

- Install per dockers official documentation: https://docs.docker.com/engine/install/ubuntu/
- Make sure to follow the instructions to allow non-root usage: https://docs.docker.com/engine/install/linux-postinstall/
- Run 'docker buildx ls' and confirm both the linux/amd64 and linux/arm64 targets are available
    - if not, install qemu: 'sudo apt-get install -y qemu qemu-user-static'