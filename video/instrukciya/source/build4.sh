#!/bin/sh
# usage: build4.sh dev lang workers
set -e
cd /tmp/claude-0/vid/tut
FF=/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2
D=$1; L=$2; W=${3:-2}; S=${L}_${D}
python3 dj.py rec4_$S > /dev/null
python3 prepare4.py $D $L
python3 audio4.py $D $L
node render4.js $D $W $L > render4_$S.log 2>&1
: > list4_$S.txt; i=0; while [ $i -lt $W ]; do echo "file 'seg4_${S}_$i.mp4'" >> list4_$S.txt; i=$((i+1)); done
$FF -loglevel error -y -f concat -safe 0 -i list4_$S.txt -i audio4_$S.wav -map 0:v -map 1:a -c:v copy -af loudnorm=I=-15:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart out4_$S.mp4
echo built $S
