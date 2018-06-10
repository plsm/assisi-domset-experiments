The DOMSET controller domset_interspecies.pt controller creates a CSV file containing data computed every cycle by the DomsetController object.
The first field in each row is an acronym describing the data.
The second field is the timestamp when the row was written.
The remaining fields contain the data.
The acronyms are:

* CT CASU temperature set at every update cycle. The third value contains
  the temperature.

* CAF CASU airflow setpoint.  The third value is 1 if the airflow is on,
  and zero if the airflow is off.

* CAC CASU average activity.  This is computed every update cycle
  immediately after reading infra-red sensor values.  The third value
  contains the average activity.

* NAC Node average activity.  This is computed every update cycle after the
  master CASU received and processed one message from its neighbours.

* CAS CASU active sensors.  This is computed in every iteration of the run
  method while loop.  Values from the third to the eight contain the active
  sensors.

* NT Node temperature reference.  This is the value computed by the master
  CASU.  This is written before sending the message to the neighbouring
  CASUS.
