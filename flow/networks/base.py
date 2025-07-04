"""Contains the base network class for traffic simulations."""

from flow.core.params import InitialConfig
from flow.core.params import TrafficLightParams
from flow.core.params import SumoCarFollowingParams
from flow.core.params import SumoLaneChangeParams
import time
import xml.etree.ElementTree as ElementTree
from lxml import etree
from collections import defaultdict

# default sumo probability value  TODO (ak): remove
DEFAULT_PROBABILITY = 0
# default sumo vehicle length value (in meters) TODO (ak): remove
DEFAULT_LENGTH = 5
# default sumo vehicle class class TODO (ak): remove
DEFAULT_VCLASS = 0


class Network(object):
    """Base network class.

    Initializes a new network. Networks are used to specify features of
    a network, including the positions of nodes, properties of the edges
    and junctions connecting these nodes, properties of vehicles and
    traffic lights, and other features as well. These features can later be
    acquired  from this class via a plethora of get methods (see
    documentation).

    This class uses network specific features to generate the necessary network
    configuration files needed to initialize a simulation instance. The methods
    of this class are called by the base network class.

    The network files can be created in one of three ways:

    * Custom networks can be generated by defining the properties of the
      network's directed graph. This is done by defining the nodes and edges
      properties using the ``specify_nodes`` and ``specify_edges`` methods,
      respectively, as well as other properties via methods including
      ``specify_types``, ``specify_connections``, etc... For more on this,
      see the tutorial on creating custom networks or refer to some of the
      available networks.

    * Network data can be collected from an OpenStreetMap (.osm) file. The
      .osm file is specified in the NetParams object. For example:

        >>> from flow.core.params import NetParams
        >>> net_params = NetParams(osm_path='/path/to/osm_file.osm')

      In this case, no ``specify_nodes`` and ``specify_edges`` methods are
      needed. However, a ``specify_routes`` method is still needed to specify
      the appropriate routes vehicles can traverse in the network.

    * Network data can be collected from an sumo-specific network (.net.xml)
      file. This file is specified in the NetParams object. For example:

        >>> from flow.core.params import NetParams
        >>> net_params = NetParams(template='/path/to/template')

      In this case, no ``specify_nodes`` and ``specify_edges`` methods are
      needed. However, a ``specify_routes`` method is still needed to specify
      the appropriate routes vehicles can traverse in the network.

    This class can be instantiated once and reused in multiple experiments.
    Note that this function stores all the relevant parameters. The
    generate() function still needs to be called separately.

    Attributes
    ----------
    orig_name : str
        the variable provided under the `name` parameter to this object upon
        instantiation
    name : str
        the variable provided under the `name` parameter to this object upon
        instantiation, appended with a timestamp variable. This timestamp is
        meant to differentiate generated network files during parallelism
    vehicles : flow.core.params.VehicleParams
        vehicle specific parameters, used to specify the types and number of
        vehicles at the start of a simulation
    net_params : flow.core.params.NetParams
        network specific parameters, used primarily to identify properties of a
        network such as the lengths of edges and the number of lanes in each
        edge. This attribute is very network-specific, and should contain the
        variables denoted by the `ADDITIONAL_NET_PARAMS` dict in each network
        class file
    initial_config : flow.core.params.InitialConfig
        specifies parameters that affect the positioning of vehicle in the
        network at the start of a simulation. For more, see flow/core/params.py
    traffic_lights : flow.core.params.TrafficLightParams
        used to describe the positions and types of traffic lights in the
        network. For more, see flow/core/params.py
    nodes : list of dict or None
        list of nodes that are assigned to the network via the `specify_nodes`
        method. All nodes in this variable are expected to have the following
        properties:

        * **name**: a unique identifier for the node
        * **x**: x-coordinate of the node, in meters
        * **y**: y-coordinate of the node, in meters

        If the network is meant to generate the network from an OpenStreetMap
        or template file, this variable is set to None
    edges : list of dict or None
        edges that are assigned to the network via the `specify_edges` method.
        This include the shape, position, and properties of all edges in the
        network. These properties include the following mandatory properties:

        * **id**: name of the edge
        * **from**: name of the node the edge starts from
        * **to**: the name of the node the edges ends at
        * **length**: length of the edge

        In addition, either the following properties need to be specifically
        defined or a **type** variable property must be defined with equivalent
        attributes in `self.types`:

        * **numLanes**: the number of lanes on the edge
        * **speed**: the speed limit for vehicles on the edge

        Moreover, the following attributes may optionally be available:

        * **shape**: the positions of intermediary nodes used to define the
          shape of an edge. If no shape is specified, then the edge will appear
          as a straight line.

        Note that, if the network is meant to generate the network from an
        OpenStreetMap or template file, this variable is set to None
    types : list of dict or None
        A variable used to ease the definition of the properties of various
        edges. Each element in the list consists of a dict consisting of the
        following property:

        * **id**: name of the edge type. Edges in the `self.edges` attribute
          with a similar value under the "type" key will adopt the properties
          of other components of this list, such as "speed" and "numLanes".

        If the type variable is None, then no types are available within the
        network. Furthermore, a proper example of this variable being used can
        be found under `specify_types` in flow/networks/loop.py.

        Note that, if the network is meant to generate the network from an
        OpenStreetMap or template file, this variable is set to None
    connections : list of dict or None
        A variable used to describe how any specific node's incoming and
        outgoing edges/lane pairs are connected. If no connections are
        specified, sumo generates default connections.

        If the connections attribute is set to None, then the connections
        within the network will be specified by the simulator.

        Note that, if the network is meant to generate the network from an
        OpenStreetMap or template file, this variable is set to None
    routes : dict
        A variable whose keys are the starting edge of a specific route, and
        whose values are the list of edges a vehicle is meant to traverse
        starting from that edge. These are only applied at the start of a
        simulation; vehicles are allowed to reroute within the environment
        immediately afterwards.
    edge_starts : list of (str, float)
        a list of tuples in which the first element of the tuple is the name of
        the edge/intersection/internal_link, and the second value is the
        distance of the link from some global reference, i.e. [(link_0, pos_0),
        (link_1, pos_1), ...]
    internal_edge_starts : list of (str, float)
        A variable similar to `edge_starts` but for junctions within the
        network. If no junctions are available, this variable will return the
        default variable: `[(':', -1)]` needed by sumo simulations.
    intersection_edge_starts : list of (str, float)
        A variable similar to `edge_starts` but for intersections within
        the network. This variable will be deprecated in future releases.

    Example
    -------
    The following examples are derived from the `RingNetwork` Network class
    located in flow/networks/ring.py, and should serve as an example of the
    types of outputs to be expected from the different variables of a network
    class.

    First of all, the ring road network class can be instantiated by running
    the following commands (note if this this unclear please refer to Tutorial
    1):

    >>> from flow.networks import RingNetwork
    >>> from flow.core.params import NetParams, VehicleParams
    >>>
    >>> network = RingNetwork(
    >>>     name='test',
    >>>     vehicles=VehicleParams(),
    >>>     net_params=NetParams(
    >>>         additional_params={
    >>>             'length': 230,
    >>>             'lanes': 1,
    >>>             'speed_limit': 30,
    >>>             'resolution': 40,
    >>>         }
    >>>     )
    >>> )

    The various attributes then look as follows:

    >>> print(network.nodes)
    >>> [{'id': 'bottom', 'x': '0', 'y': '-36.60563691113593'},
    >>>  {'id': 'right', 'x': '36.60563691113593', 'y': '0'},
    >>>  {'id': 'top', 'x': '0', 'y': '36.60563691113593'},
    >>>  {'id': 'left', 'x': '-36.60563691113593', 'y': '0'}]


    >>> print(network.edges)
    >>> [
    >>>     {'id': 'bottom',
    >>>      'type': 'edgeType',
    >>>      'from': 'bottom',
    >>>      'to': 'right',
    >>>      'length': '57.5',
    >>>      'shape': '0.00,-36.61 1.47,-36.58 2.95,-36.49 4.41,-36.34 '
    >>>               '5.87,-36.13 7.32,-35.87 8.76,-35.54 10.18,-35.16 '
    >>>               '11.59,-34.72 12.98,-34.23 14.35,-33.68 15.69,-33.07 '
    >>>               '17.01,-32.41 18.30,-31.70 19.56,-30.94 20.79,-30.13 '
    >>>               '21.99,-29.26 23.15,-28.35 24.27,-27.40 25.36,-26.40 '
    >>>               '26.40,-25.36 27.40,-24.27 28.35,-23.15 29.26,-21.99 '
    >>>               '30.13,-20.79 30.94,-19.56 31.70,-18.30 32.41,-17.01 '
    >>>               '33.07,-15.69 33.68,-14.35 34.23,-12.98 34.72,-11.59 '
    >>>               '35.16,-10.18 35.54,-8.76 35.87,-7.32 36.13,-5.87 '
    >>>               '36.34,-4.41 36.49,-2.95 36.58,-1.47 36.61,0.00'
    >>>     },
    >>>     {'id': 'right',
    >>>      'type': 'edgeType',
    >>>      'from': 'right',
    >>>      'to': 'top',
    >>>      'length': '57.5',
    >>>      'shape': '36.61,0.00 36.58,1.47 36.49,2.95 36.34,4.41 36.13,5.87 '
    >>>               '35.87,7.32 35.54,8.76 35.16,10.18 34.72,11.59 '
    >>>               '34.23,12.98 33.68,14.35 33.07,15.69 32.41,17.01 '
    >>>               '31.70,18.30 30.94,19.56 30.13,20.79 29.26,21.99 '
    >>>               '28.35,23.15 27.40,24.27 26.40,25.36 25.36,26.40 '
    >>>               '24.27,27.40 23.15,28.35 21.99,29.26 20.79,30.13 '
    >>>               '19.56,30.94 18.30,31.70 17.01,32.41 15.69,33.07 '
    >>>               '14.35,33.68 12.98,34.23 11.59,34.72 10.18,35.16 '
    >>>               '8.76,35.54 7.32,35.87 5.87,36.13 4.41,36.34 2.95,36.49 '
    >>>               '1.47,36.58 0.00,36.61'
    >>>     },
    >>>     {'id': 'top',
    >>>      'type': 'edgeType',
    >>>      'from': 'top',
    >>>      'to': 'left',
    >>>      'length': '57.5',
    >>>      'shape': '0.00,36.61 -1.47,36.58 -2.95,36.49 -4.41,36.34 '
    >>>               '-5.87,36.13 -7.32,35.87 -8.76,35.54 -10.18,35.16 '
    >>>               '-11.59,34.72 -12.98,34.23 -14.35,33.68 -15.69,33.07 '
    >>>               '-17.01,32.41 -18.30,31.70 -19.56,30.94 -20.79,30.13 '
    >>>               '-21.99,29.26 -23.15,28.35 -24.27,27.40 -25.36,26.40 '
    >>>               '-26.40,25.36 -27.40,24.27 -28.35,23.15 -29.26,21.99 '
    >>>               '-30.13,20.79 -30.94,19.56 -31.70,18.30 -32.41,17.01 '
    >>>               '-33.07,15.69 -33.68,14.35 -34.23,12.98 -34.72,11.59 '
    >>>               '-35.16,10.18 -35.54,8.76 -35.87,7.32 -36.13,5.87 '
    >>>               '-36.34,4.41 -36.49,2.95 -36.58,1.47 -36.61,0.00'
    >>>     },
    >>>     {'id': 'left',
    >>>      'type': 'edgeType',
    >>>      'from': 'left',
    >>>      'to': 'bottom',
    >>>      'length': '57.5',
    >>>      'shape': '-36.61,0.00 -36.58,-1.47 -36.49,-2.95 -36.34,-4.41 '
    >>>               '-36.13,-5.87 -35.87,-7.32 -35.54,-8.76 -35.16,-10.18 '
    >>>               '-34.72,-11.59 -34.23,-12.98 -33.68,-14.35 '
    >>>               '-33.07,-15.69 -32.41,-17.01 -31.70,-18.30 '
    >>>               '-30.94,-19.56 -30.13,-20.79 -29.26,-21.99 '
    >>>               '-28.35,-23.15 -27.40,-24.27 -26.40,-25.36 '
    >>>               '-25.36,-26.40 -24.27,-27.40 -23.15,-28.35 '
    >>>               '-21.99,-29.26 -20.79,-30.13 -19.56,-30.94 '
    >>>               '-18.30,-31.70 -17.01,-32.41 -15.69,-33.07 '
    >>>               '-14.35,-33.68 -12.98,-34.23 -11.59,-34.72 '
    >>>               '-10.18,-35.16 -8.76,-35.54 -7.32,-35.87 -5.87,-36.13 '
    >>>               '-4.41,-36.34 -2.95,-36.49 -1.47,-36.58 -0.00,-36.61'
    >>>     }
    >>> ]


    >>> print(network.types)
    >>> [{'id': 'edgeType', 'numLanes': '1', 'speed': '30'}]

    >>> print(network.connections)
    >>> None

    >>> print(network.routes)
    >>> {
    >>>     'top': ['top', 'left', 'bottom', 'right'],
    >>>     'left': ['left', 'bottom', 'right', 'top'],
    >>>     'bottom': ['bottom', 'right', 'top', 'left'],
    >>>     'right': ['right', 'top', 'left', 'bottom']
    >>> }


    >>> print(network.edge_starts)
    >>> [('bottom', 0), ('right', 57.5), ('top', 115.0), ('left', 172.5)]

    Finally, the ring network does not contain any junctions or intersections,
    and as a result the `internal_edge_starts` and `intersection_edge_starts`
    attributes are both set to None. For an example of a network with junctions
    and intersections, please refer to: flow/networks/figure_eight.py.

    >>> print(network.internal_edge_starts)
    >>> [(':', -1)]

    >>> print(network.intersection_edge_starts)
    >>> []
    """

    def __init__(self,
                 name,
                 vehicles,
                 net_params,
                 initial_config=InitialConfig(),
                 traffic_lights=TrafficLightParams()):
        """Instantiate the base network class.

        Attributes
        ----------
        name : str
            A tag associated with the network
        vehicles : flow.core.params.VehicleParams
            see flow/core/params.py
        net_params : flow.core.params.NetParams
            see flow/core/params.py
        initial_config : flow.core.params.InitialConfig
            see flow/core/params.py
        traffic_lights : flow.core.params.TrafficLightParams
            see flow/core/params.py
        """
        self.orig_name = name  # To avoid repeated concatenation upon reset
        self.name = name + time.strftime('_%Y%m%d-%H%M%S') + str(time.time())

        self.vehicles = vehicles
        self.net_params = net_params
        self.initial_config = initial_config
        self.traffic_lights = traffic_lights

        # specify routes vehicles can take
        self.routes = self.specify_routes(net_params)

        if net_params.template is None and net_params.osm_path is None:
            # specify the attributes of the nodes
            self.nodes = self.specify_nodes(net_params)
            # collect the attributes of each edge
            self.edges = self.specify_edges(net_params)
            # specify the types attributes (default is None)
            self.types = self.specify_types(net_params)
            # specify the connection attributes (default is None)
            self.connections = self.specify_connections(net_params)

        # this is to be used if file paths other than the the network geometry
        # file is specified
        elif type(net_params.template) is dict:
            if 'rou' in net_params.template:
                veh, rou = self._vehicle_infos(net_params.template['rou'])

                vtypes = self._vehicle_type(net_params.template.get('vtype'))
                cf = self._get_cf_params(vtypes)
                lc = self._get_lc_params(vtypes)

                # add the vehicle types to the VehicleParams object
                for t in vtypes:
                    vehicles.add(veh_id=t, car_following_params=cf[t],
                                 lane_change_params=lc[t], num_vehicles=0)

                # add the routes of the vehicles that will be departed later
                # under the name of the vehicle. This will later be identified
                # by k.vehicles._add_departed
                self.routes = rou

                # vehicles to be added with different departure times
                self.template_vehicles = veh

            self.types = None
            self.nodes = None
            self.edges = None
            self.connections = None

        # osm_path or template as type str
        else:
            self.nodes = None
            self.edges = None
            self.types = None
            self.connections = None

        # optional parameters, used to get positions from some global reference
        self.edge_starts = self.specify_edge_starts()
        self.internal_edge_starts = self.specify_internal_edge_starts()
        self.intersection_edge_starts = []  # this will be deprecated

    # TODO: convert to property
    def specify_edge_starts(self):
        """Define edge starts for road sections in the network.

        This is meant to provide some global reference frame for the road
        edges in the network.

        By default, the edge starts are specified from the network
        configuration file. Note that, the values are arbitrary but do not
        allow the positions of any two edges to overlap, thereby making them
        compatible with all starting position methods for vehicles.

        Returns
        -------
        list of (str, float)
            list of edge names and starting positions,
            ex: [(edge0, pos0), (edge1, pos1), ...]
        """
        return None

    # TODO: convert to property
    def specify_internal_edge_starts(self):
        """Define the edge starts for internal edge nodes.

        This is meant to provide some global reference frame for the internal
        edges in the network.

        These edges are the result of finite-length connections between road
        sections. This methods does not need to be specified if "no-internal-
        links" is set to True in net_params.

        By default, all internal edge starts are given a position of -1. This
        may be overridden; however, in general we do not worry about internal
        edges and junctions in large networks.

        Returns
        -------
        list of (str, float)
            list of internal junction names and starting positions,
            ex: [(internal0, pos0), (internal1, pos1), ...]
        """
        return [(':', -1)]

    # TODO: convert to property
    def specify_nodes(self, net_params):
        """Specify the attributes of nodes in the network.

        Parameters
        ----------
        net_params : flow.core.params.NetParams
            see flow/core/params.py

        Returns
        -------
        list of dict

            A list of node attributes (a separate dict for each node). Nodes
            attributes must include:

            * id {string} -- name of the node
            * x {float} -- x coordinate of the node
            * y {float} -- y coordinate of the node

        Other attributes may also be specified. See:
        http://sumo.dlr.de/wiki/Networks/Building_Networks_from_own_XML-descriptions#Node_Descriptions
        """
        raise NotImplementedError

    # TODO: convert to property
    def specify_edges(self, net_params):
        """Specify the attributes of edges connecting pairs on nodes.

        Parameters
        ----------
        net_params : flow.core.params.NetParams
            see flow/core/params.py

        Returns
        -------
        list of dict

            A list of edges attributes (a separate dict for each edge). Edge
            attributes must include:

            * id {string} -- name of the edge
            * from {string} -- name of node the directed edge starts from
            * to {string} -- name of the node the directed edge ends at

            In addition, the attributes must contain at least one of the
            following:

            * "numLanes" {int} and "speed" {float} -- the number of lanes and
              speed limit of the edge, respectively
            * type {string} -- a type identifier for the edge, which can be
              used if several edges are supposed to possess the same number of
              lanes, speed limits, etc...

        Other attributes may also be specified. See:
        http://sumo.dlr.de/wiki/Networks/Building_Networks_from_own_XML-descriptions#Edge_Descriptions
        """
        raise NotImplementedError

    # TODO: convert to property
    def specify_types(self, net_params):
        """Specify the attributes of various edge types (if any exist).

        Parameters
        ----------
        net_params : flow.core.params.NetParams
            see flow/core/params.py

        Returns
        -------
        list of dict
            A list of type attributes for specific groups of edges. If none are
            specified, no .typ.xml file is created.

        For information on type attributes, see:
        http://sumo.dlr.de/wiki/Networks/Building_Networks_from_own_XML-descriptions#Type_Descriptions
        """
        return None

    # TODO: convert to property
    def specify_connections(self, net_params):
        """Specify the attributes of connections.

        These attributes are used to describe how any specific node's incoming
        and outgoing edges/lane pairs are connected. If no connections are
        specified, sumo generates default connections.

        Parameters
        ----------
        net_params : flow.core.params.NetParams
            see flow/core/params.py

        Returns
        -------
        list of dict
            A list of connection attributes. If none are specified, no .con.xml
            file is created.

        For information on type attributes, see:
        http://sumo.dlr.de/wiki/Networks/Building_Networks_from_own_XML-descriptions#Connection_Descriptions
        """
        return None

    # TODO: convert to property
    def specify_routes(self, net_params):
        """Specify the routes vehicles can take starting from any edge.

        Routes can be specified in one of three ways:

        * In this case of deterministic routes (as is the case in the ring road
          network), the routes can be specified as dictionary where the key
          element represents the starting edge and the element is a single list
          of edges the vehicle must traverse, with the first edge corresponding
          to the edge the vehicle begins on. Note that the edges must be
          connected for the route to be valid.

          For example (from flow/networks/ring.py):

          >>> def specify_routes(self, net_params):
          >>>     return {
          >>>         "top": ["top", "left", "bottom", "right"],
          >>>         "left": ["left", "bottom", "right", "top"],
          >>>         "bottom": ["bottom", "right", "top", "left"],
          >>>         "right": ["right", "top", "left", "bottom"]
          >>>     }

        * Alternatively, if the routes are meant to be stochastic, each element
          can consist of a list of (route, probability) tuples, where the first
          element in the tuple is one of the routes a vehicle can take from a
          specific starting edge, and the second element is the probability
          that vehicles will choose that route. Note that, in this case, the
          sum of probability values for each dictionary key must sum up to one.

          For example, if we were to imagine the edge "right" in the ring road
          examples where split into two edges, "right_0" and "right_1", the
          routes for vehicles in this network in the probabilistic setting can
          be:

          >>> def specify_routes(self, net_params):
          >>>     return {
          >>>         "top": [
          >>>             (["top", "left", "bottom", "right_0"], 0.9),
          >>>             (["top", "left", "bottom", "right_1"], 0.1)
          >>>         ],
          >>>         "left": [
          >>>             (["left", "bottom", "right_0", "top"], 0.3),
          >>>             (["left", "bottom", "right_1", "top"], 0.7)
          >>>         ],
          >>>         "bottom": [
          >>>             (["bottom", "right_0", "top", "left"], 0.5),
          >>>             (["bottom", "right_1", "top", "left"], 0.5)
          >>>         ],
          >>>         "right_0": [
          >>>             (["right_0", "top", "left", "bottom"], 1)
          >>>         ],
          >>>         "right_1": [
          >>>             (["right_1", "top", "left", "bottom"], 1)
          >>>         ]
          >>>     }

        * Finally, if you would like to assign a specific starting edge and
          route to a vehicle with a specific ID, you can do so by adding a
          element into the dictionary whose key is the name of the vehicle and
          whose content is the list of edges the vehicle is meant to traverse
          as soon as it is introduced to the network.

          As an example, assume we have 4 vehicles named 'human_0', 'human_1',
          'human_2', and 'human_3' in the original ring road. Then, an
          appropriate definition of the routes may look something like:

          >>> def specify_routes(self, net_params):
          >>>     return {
          >>>         "human_0": ["top", "left", "bottom", "right"],
          >>>         "human_1": ["left", "bottom", "right", "top"],
          >>>         "human_2": ["bottom", "right", "top", "left"],
          >>>         "human_3": ["right", "top", "left", "bottom"]
          >>>     }

          **Note**: This feature is experimental, and may not always work as
          expected (for example if the starting positions and routes of a
          specific vehicle do not match).

        The `define_routes` method is optional, and need not be defined. If it
        is not implemented, vehicles that enter a network are assigned routes
        consisting solely on their current edges, and exit the network once
        they reach the end of their edge. Routes, however, can be reassigned
        during simulation via a routing controller (see
        flow/controllers/routing_controllers.py).

        Parameters
        ----------
        net_params : flow.core.params.NetParams
            see flow/core/params.py

        Returns
        -------
        dict
            Key = name of the starting edge
            Element = list of edges a vehicle starting from this edge must
            traverse *OR* a list of (route, probability) tuples for each
            starting edge
        """
        return None

    @staticmethod
    def gen_custom_start_pos(cls, net_params, initial_config, num_vehicles):
        """Generate a user defined set of starting positions.

        Parameters
        ----------
        cls : flow.core.kernel.network.BaseKernelNetwork
            flow network kernel, with all the relevant methods implemented
        net_params : flow.core.params.NetParams
            network-specific parameters
        initial_config : flow.core.params.InitialConfig
            see flow/core/params.py
        num_vehicles : int
            number of vehicles to be placed on the network

        Returns
        -------
        list of tuple (float, float)
            list of start positions [(edge0, pos0), (edge1, pos1), ...]
        list of int
            list of start lanes
        list of float
            list of start speeds
        """
        raise NotImplementedError

    @staticmethod
    def _vehicle_infos(file_names):
        """Import of vehicle from a configuration file.

        This is a utility function for computing vehicle information. It
        imports a network configuration file, and returns the information on
        the vehicle and add it into the Vehicle object.

        Parameters
        ----------
        file_names : list of str
            path to the xml file to load

        Returns
        -------
        dict <dict>

            * Key = id of the vehicle
            * Element = dict of departure speed, vehicle type, depart Position,
              depart edges
        """
        # this is meant to deal with the case that there is only one rou file
        if isinstance(file_names, str):
            file_names = [file_names]

        vehicle_data = dict()
        routes_data = dict()
        type_data = defaultdict(int)

        for filename in file_names:
            # import the .net.xml file containing all edge/type data
            parser = etree.XMLParser(recover=True)
            tree = ElementTree.parse(filename, parser=parser)
            root = tree.getroot()

            # collect the departure properties and routes and vehicles whose
            # properties are instantiated within the .rou.xml file. This will
            # only apply if such data is within the file (it is not implemented
            # by networks in Flow).
            for vehicle in root.findall('vehicle'):
                # collect the edges the vehicle is meant to traverse
                route = vehicle.find('route')
                route_edges = route.attrib["edges"].split(' ')

                # collect the names of each vehicle type and number of vehicles
                # of each type
                type_vehicle = vehicle.attrib['type']
                type_data[type_vehicle] += 1

                vehicle_data[vehicle.attrib['id']] = {
                    'departSpeed': vehicle.attrib['departSpeed'],
                    'depart': vehicle.attrib['depart'],
                    'typeID': type_vehicle,
                    'departPos': vehicle.attrib['departPos'],
                }

                routes_data[vehicle.attrib['id']] = route_edges

            # collect the edges the vehicle is meant to traverse for the given
            # sets of routes that are not associated with individual vehicles
            for route in root.findall('route'):
                route_edges = route.attrib["edges"].split(' ')
                routes_data[route.attrib['id']] = route_edges

        return vehicle_data, routes_data

    @staticmethod
    def _vehicle_type(filename):
        """Import vehicle type data from a *.add.xml file.

        This is a utility function for outputting all the type of vehicle.

        Parameters
        ----------
        filename : str
            path to the vtypes.add.xml file to load

        Returns
        -------
        dict or None
            the key is the vehicle_type id and the value is a dict we've type
            of the vehicle, depart edges, depart Speed, departPos. If no
            filename is provided, this method returns None as well.
        """
        if filename is None:
            return None

        parser = etree.XMLParser(recover=True)
        tree = ElementTree.parse(filename, parser=parser)

        root = tree.getroot()
        veh_type = {}

        # this hack is meant to support the LuST network and Flow networks
        root = [root] if len(root.findall('vTypeDistribution')) == 0 \
            else root.findall('vTypeDistribution')

        for r in root:
            for vtype in r.findall('vType'):
                # TODO: make for everything
                veh_type[vtype.attrib['id']] = {
                    'vClass': vtype.attrib.get('vClass', DEFAULT_VCLASS),
                    'accel': vtype.attrib['accel'],
                    'decel': vtype.attrib['decel'],
                    'sigma': vtype.attrib['sigma'],
                    'length': vtype.attrib.get('length', DEFAULT_LENGTH),
                    'minGap': vtype.attrib['minGap'],
                    'maxSpeed': vtype.attrib['maxSpeed'],
                    'probability': vtype.attrib.get(
                        'probability', DEFAULT_PROBABILITY),
                    'speedDev': vtype.attrib['speedDev']
                }

        return veh_type

    @staticmethod
    def _get_cf_params(vtypes):
        """Return the car-following sumo params from vtypes."""
        ret = {}
        for typ in vtypes:
            # TODO: add vClass
            ret[typ] = SumoCarFollowingParams(
                speed_mode='all_checks',
                accel=float(vtypes[typ]['accel']),
                decel=float(vtypes[typ]['decel']),
                sigma=float(vtypes[typ]['sigma']),
                length=float(vtypes[typ]['length']),
                min_gap=float(vtypes[typ]['minGap']),
                max_speed=float(vtypes[typ]['maxSpeed']),
                probability=float(vtypes[typ]['probability']),
                speed_dev=float(vtypes[typ]['speedDev'])
            )

        return ret

    @staticmethod
    def _get_lc_params(vtypes):
        """Return the lane change sumo params from vtypes."""
        ret = {}
        for typ in vtypes:
            ret[typ] = SumoLaneChangeParams(lane_change_mode=1621)

        return ret

    def __str__(self):
        """Return the name of the network and the number of vehicles."""
        return 'Network ' + self.name + ' with ' + \
               str(self.vehicles.num_vehicles) + ' vehicles.'
