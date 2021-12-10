# Safety-Assured Deep Reinforcement Learning for Cooperative Highway Ramp Merging
## Description:
1. Designed and trained a deep reinforcement learning model to perform single-agent motion planning for vehicles involved in a highway ramp merging scenario using Ray and SUMO (Simulation of Urban MObility), based on an open source project called FLOW.

2. Designed and implemented safe-assured features for the model by applying an intelligent ramp meter in the merging scenario.


## Flow

[Flow](https://flow-project.github.io/) is a computational framework for deep RL and control experiments for traffic microsimulation.

See [our website](https://flow-project.github.io/) for more information on the application of Flow to several mixed-autonomy traffic scenarios. Other [results and videos](https://sites.google.com/view/ieee-tro-flow/home) are available as well.

### More information about FLOW:

- [Documentation](https://flow.readthedocs.org/en/latest/)
- [Installation instructions](http://flow.readthedocs.io/en/latest/flow_setup.html)
- [Tutorials](https://github.com/flow-project/flow/tree/master/tutorials)
- [Binder Build (beta)](https://mybinder.org/v2/gh/flow-project/flow/binder)

## Running the code:
After installing the FLOW environment, go to the `example/` folder and run:
`conda activate flow`  
`python train.py singleagent_ramp_meter --rl_trainer "rllib"` for trainning  

See documents in `flow/visualize` for visualization of the result. 
