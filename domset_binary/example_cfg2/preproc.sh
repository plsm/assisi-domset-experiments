#!/bin/bash

mv beearena/* ./
rm -rf beearena
for f in casu-0*; do cd "$f"; rm *domset.csv; mv 20* ../; cd ..; rm -rf "$f"; done
rename 's/201.*-casu/casu/' 2018*
for c in casu-0* ; do sed -i '1s/1.0;1.0;1.0;1.0;1.0;1.0/1.0;1.0;1.0;1.0;1.0;1.0;0.0;0.0/' "$c"; done
sed -i '$d' casu-0*

