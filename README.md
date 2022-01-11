# Safety-Driven Deep Reinforcement Learning for Cooperative Highway Ramp Merging
## Description:
1. Designed and trained a deep reinforcement learning model to perform single-agent motion planning for vehicles involved in a highway ramp merging scenario using Ray and SUMO (Simulation of Urban MObility), based on an open source project called FLOW.

2. Designed and implemented safe-driven features for the model by applying an intelligent ramp meter in the merging scenario.


## Flow

[Flow](https://flow-project.github.io/) is a computational framework for deep RL and control experiments for traffic microsimulation.

## Software Setup:
1. Go through the [Flow Installation Instructions](http://flow.readthedocs.io/en/latest/flow_setup.html) to install Flow, SUMO and RLlib.  
2. Test the installation according to the same instruction listed above.

## Training:
1. Go to the `flow/example/` folder and run: `conda activate flow`
2. For training the original highway merging scenario, run `python train.py singleagent_merge --rl_trainer "rllib"`
3. For training the modified highway merging scenario with ramp meter, run `python train.py singleagent_ramp_meter --rl_trainer "rllib"` 
4. The trained results will be stored in `ray_result` which is outside the `flow` directory. It is stored in the form of checkpoints.

## Visualization for original highway merging scenario:
1. Selet the folder inside the `ray_result` mentioned above, e.g. `ray_results/stabilizing_open_network_merges/merge_1`, note: `merge_1` is an arbitrary name here.
2. Within the selected folder, select the checkpoint folder that you want to visualize, e.g. `ray_results/stabilizing_open_network_merges/ramp_meter_1/500`, where 500 is the number of the selected checkpoint.
3. Go to the `flow/flow/visualize/` folder and run: `conda activate flow`
4. Given the example information colleceted above inside the `ray_result` folder, run `python ./visualizer_rllib.py ~/ray_results/stabilizing_open_network_merges/merge_1 500`, where `merge_1` is the folder name selected above, and the `500` is the number of the selected checkpoint. 

## Modifications from the original Flow (how I created the new highway merging with ramp meter scenario):
1. Created `flow/examples/exp_configs/rl/singleagent/singleagent_ramp_meter.py`, which indicates the training parameters, vehicle parameters, and flow parameters.
2. Created `flow/flow/envs/ramp_meter.py`, which determines the Reinforcement Learning functions including States, Actions, Rewards, etc.
3. Added the `'RampMeterPOEnv'` into the file`flow/flow/envs/__init__.py`, under the `__all__ = [` session, so that the system can have access to the file.
4. Created `flow/flow/networks/ramp_meter.py`, which determines the SUMO traffic network as the training environment. 
5. Added the `from flow.networks.ramp_meter import RampMeterNetwork` into the file`flow/flow/networks/__init__.py` so that the system can have access to the file.