Description
===========

This folder contains a set of utility programs to help manage inter-species DOMSET experiments.

generate_config
---------------

This program takes as input
 
 * a GraphViz file representing a logical graph;
 * an arena file with the physical location of CASUs (and their network addresses);
 * an ISI configuration file with common parameters;
 * number of physical graphs to test.
 
 It produces a set of files:
 * a bee DOMSET manager configuration file (check the `domset_binary/manager/README.md` file)
 * an ISI configuration file
 * an ISI graph yaml file
 * an ISI nodemasters file
 * a HTML file with the location of the physical file.
 
 The DOMSET manager configuration file can be processed by the DARC manager (check the `assisipy-utils` repository)
 to produce a set of `assisi`, `arena`, `nbg` and `dep` files.
 
 Bellow is an example of a shell script to process the above input
 
    PROJECT=$1
    COPY=$2
    ARENA=CASUs-center-bottom.arena
    ISI_CONFIG=ISI-common-parameters.conf
    
    python {PATH TO assisi-domset-experiments}/domset_binary/util/generate_config.py \
        --copy ${COPY} \
        --graph ${PROJECT}.gv \
        --arena ${ARENA} \
        --ISI-config ${ISI_CONFIG}
    
    python {PATH TO assisipy-utils}/assisipy_utils/darc/manager.py \
        --arena ${ARENA} \
        --config ${PROJECT}.config \
        --project ${PROJECT}
    
    python {PATH TO assisipy-utils}/assisipy_utils/validate/draw_casu_graph.py \
        ${PROJECT}.assisi
    
    neato -Tpdf -O ${PROJECT}.nbg.layout
