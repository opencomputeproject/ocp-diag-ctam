# Copyright (c) NVIDIA CORPORATION
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#
# Makes a executable build of the ctam directory
#

DOCKER_IMAGE_TAG=pyinstaller-ctam
DOCKER_CONTAINER_NAME=build-ctam

build_image:
	docker build --tag $(DOCKER_IMAGE_TAG) --build-arg LOCAL_DIR=$(PWD) .
	docker run -it --name $(DOCKER_CONTAINER_NAME) $(DOCKER_IMAGE_TAG)
	docker cp $(DOCKER_CONTAINER_NAME):/app/dist ./dist
	docker rm -f $(DOCKER_CONTAINER_NAME)
	docker rmi $(DOCKER_IMAGE_TAG) --force

clean:
	rm -rf build ctam.spec dist
	docker rm -f $(DOCKER_CONTAINER_NAME)
	docker rmi $(DOCKER_IMAGE_TAG) --force
