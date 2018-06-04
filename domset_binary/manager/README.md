Description
===========

This folder provides a set of modules to automatically deploy and run code in the beaglebones, do a video recording, and collect data.
The overall system is a distributed application with a manager running on the workstation and the CASU controllers running in the beagle bones.

* On top of the CASU controller there is a server that waits for commands from the manager.
The implemented commands are start the DOMSET algorithm and terminate the CASU controller.

* The manager handles the deployment and running of the CASU controllers.
Video recording and sending the start command are done at the same time.
After the provided experiment duration has passed, the manager terminates the CASU controllers.

In order to use this, you have to provide two text files, one describing the graph topology and video recording parameters, and a second file describing the CASUs that are going to be used.
To run enter:
`python manager.py --config CONFIG_FILENAME --workers WORKERS_FILENAME`
 
Parameter `--config` provides the file containing the graph topology and video recording parameters.
Below is an example of such file:


    graph:
       edges: [['n1', 'n2'], ['n2', 'n3'], ['n3', 'n1']
       node_CASUs: {
          'n1': [21, 22],
          'n2': [23, 24],
          'n3': [25, 26]
       }
    
    experiment_duration: 20
    
    video:
       crop_left : 100
       crop_right : 110
       crop_top : 200
       crop_bottom : 300
       frames_per_second : 10

The first block describes the graph and the CASUs assigned to each node.
The last block contains the parameters for the video recording.

Parameter  `--workers` provides the file containing the description of the CASUs to be used.
Below is an example of such file:

    workers: [
       {
        'casu_number' : 1,
        'wrk_addr' : 'tcp://localhost:3001',
        'pub_addr' : 'tcp://127.0.0.1:5556',
        'sub_addr' : 'tcp://127.0.0.1:5555',
        'msg_addr' : 'tcp://127.0.0.1:20001'
       },
       {
        'casu_number' : 2,
        'wrk_addr' : 'tcp://localhost:3002',
        'pub_addr' : 'tcp://127.0.0.1:5556',
        'sub_addr' : 'tcp://127.0.0.1:5555',
        'msg_addr' : 'tcp://127.0.0.1:20002'
       },
       {
        'casu_number' : 3,
        'wrk_addr' : 'tcp://localhost:3003',
        'pub_addr' : 'tcp://127.0.0.1:5556',
        'sub_addr' : 'tcp://127.0.0.1:5555',
        'msg_addr' : 'tcp://127.0.0.1:20003',
       },
       {
        'casu_number' : 4,
        'wrk_addr' : 'tcp://localhost:3004',
        'pub_addr' : 'tcp://127.0.0.1:5556',
        'sub_addr' : 'tcp://127.0.0.1:5555',
        'msg_addr' : 'tcp://127.0.0.1:20004'
       }
    ]

For each CASU, besides the publish and subscribe socket addresses and the socket used for communication with other CASUs, the attribute `wrk_addr` contains a socket where the code running in the beagle bones waits for commands from the workstation.
