FROM ocrd/core:latest
VOLUME ["/data"]
ENV VERSION="Di 2. Apr 17:50:22 CEST 2019"
ENV GITURL="https://github.com/cisocrgroup"
ENV DATA="/data/ocrd-cis-post-correction"

# deps
COPY data/docker/deps.txt ${DATA}/deps.txt
RUN apt-get update && \
	apt-get -y install --no-install-recommends $(cat ${DATA}/deps.txt)

# cis-ocrd scripts and configuration
COPY bashlib/ocrd-cis-lib.sh /apps/
COPY bashlib/ocrd-cis-docker-train.sh /apps/
COPY bashlib/ocrd-cis-post-correct.sh /apps/
# COPY data/docker/train.json /${DATA}/
# COPY data/docker/train.json /${DATA}/
# COPY data/docker/train.json /${DATA}/

# install the profiler
RUN	git clone ${GITURL}/Profiler --branch devel --single-branch /tmp/profiler &&\
	cd /tmp/profiler &&\
	mkdir build &&\
	cd build &&\
	cmake -DCMAKE_BUILD_TYPE=release .. &&\
	make compileFBDic trainFrequencyList profiler &&\
	cp bin/compileFBDic bin/trainFrequencyList bin/profiler /apps/ &&\
	cd / &&\
    rm -rf /tmp/profiler

# install the profiler's language backend
RUN	git clone ${GITURL}/Resources --branch master --single-branch /tmp/resources &&\
	cd /tmp/resources/lexica &&\
	make FBDIC=/apps/compileFBDic TRAIN=/apps/trainFrequencyList &&\
	mkdir -p /${DATA}/languages &&\
	cp -r german latin greek german.ini latin.ini greek.ini /${DATA}/languages &&\
	cd / &&\
	rm -rf /tmp/resources

# install cis-ocrd-py
RUN git clone ${GITURL}/cis-ocrd-py --branch dev --single-branch /tmp/cis-ocrd-py &&\
	cd /tmp/cis-ocrd-py &&\
	pip install --upgrade pip &&\
	pip install --upgrade . &&\
	cd / &&\
	rm -rf /tmp/cis-ocrd-py

# install cis-ocrd-py
RUN git clone ${GITURL}/ocrd-postcorrection --branch dev --single-branch /tmp/ocrd-postcorrection &&\
	cd /tmp/ocrd-postcorrection &&\
	mvn -DskipTests package &&\
	cp target/ocrd-0.1-cli.jar /apps/ocrd-cis.jar &&\
	cd / &&\
	rm -rf /tmp/ocrd-postcorrection

# download ocr models and pre-trainded post-correction model
RUN cd /data &&\
	wget cis.lmu.de/~finkf/model.zip &&\
	wget cis.lmu.de/~finkf/fraktur1-00085000.pyrnn.gz &&\
	wget cis.lmu.de/~finkf/fraktur2-00062000.pyrnn.gz

# TODOS:
# - add configuration files
# - add ocr-models
# - implement/adjust training script
# - implement helper post-correction script
ENTRYPOINT ["/bin/sh", "-c"]
