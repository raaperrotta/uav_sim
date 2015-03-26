import random
import numpy as n
import simpy

print_events = True

class Environment(simpy.Environment):
    """
    Inherits simpy.Environment for all discreet simulation management functions.
    Also contains all objects in the simulation and all environmental parameters.
    Should be the sole owner of all "Truth" information in the simulation.
    """
    def __init__(self):
        super(Environment, self).__init__()
        self.uavs = []
        self.ships = []
        self.radars = []
        self.weapons = []
        self.sea_state = 0
        self.visibility = random.betavariate(0.5, 1.) # should be changed to match ExtendSim (0.5, 1, -0.7, 1)

        self.end_sim = self.event();

    def gen_uavs(self, num_uavs, distance):
        for ii in range(num_uavs):
            """
            There is no sense simulating the uavs before they are detected
            Save time by starting the simulation with the uavs on the edge
            of the detection region
            """
            # distance = random.uniform(20000., 30000.)
            angle = random.uniform(-60., -30.) * n.pi / 180. # from ExtendSim model
            x = distance * n.cos(angle)
            y = distance * n.sin(angle)
            pos = n.array([x, y])
            speed = random.uniform(169., 228.) # from ExtendSim model
            lethality = 0.85 # from ExtendSim model
            target = random.choice(self.ships)
            self.uavs.append(Uav(self, pos, speed, lethality, target))


    def add_weapon(self, type, ship):
        weapons = {
        'CWIS': (1., 0.72),
        'MGS': (1., 0.20),
        '5-inch Gun': (1., 0.45),
        }
        if type in weapons:
            parameters = weapons[type]
        else:
            raise ValueError('Did not understand weapon type "{type}."'.format(type=type))

        rate = weapons[type][0]
        lethality = weapons[type][1]
        self.weapons.append(Weapon(self, rate, lethality, ship))


class Uav(object):

    def __init__(self, env, pos, speed, lethality, target):
        self.env = env
        self.pos = pos
        self.speed = speed
        self.lethality = lethality
        self.target = target

        # Still need to correct for non-zero ship speed
        time_to_ship = self.range_to_target(0)/self.speed

        self.reached_ship = env.timeout(time_to_ship)
        self.shot_down = env.event();

        self.action = env.process(self.attack())

    def __str__(self):
        return "Uav_" + str(id(self))

    def range_to_target(self,time):
        impact_distance = 570. # from ExtendSim model
        dist_to_ship = n.linalg.norm(self.pos-self.target.pos)
        return dist_to_ship - impact_distance - time*self.speed

    def attack(self):
        result = yield self.reached_ship | self.shot_down
        if self.reached_ship in result:
            # Ship casualty is binary here. We sould consider a damage/cost counter instead.
            if random.random() <= self.lethality:
                if print_events: print "%s hit %s at %.2f" % (self, self.target, self.env.now)
                self.target.health = 0
                self.env.end_sim.succeed()
            else:
                if print_events: print "%s was a dud at %.2f" % (self, self.env.now)

        else: # self.shot_down in result
            pass
            # print "%s was shot down at %.2f" % (self, self.env.now)


class Weapon(object):
    def __init__(self, env, rate, lethality, ship):
        self.env = env
        self.rate = rate
        self.lethality = lethality
        self.resource = simpy.Resource(env, capacity=1)
        self.ship = ship
        ship.weapons.append(self)

        self.destroyed = env.event()


    def __str__(self):
        return "Wpn_" + str(id(self))

    def shoot_uav(self, uav, request):
        period = 1./self.rate
        time_to_kill = period
        while random.random() > self.lethality:
            time_to_kill += period

        if print_events: print "%s engaged %s at %.2f" % (self, uav, self.env.now)
        result = yield self.env.timeout(time_to_kill) | uav.reached_ship
        if uav.reached_ship in result:
            pass
            # the UAV object will handle this case
        else:
            uav.shot_down.succeed()
            if print_events: print "%s shot-down %s at %.2f" % (self, uav, self.env.now)
            self.env.uavs.remove(uav)
            if not self.env.uavs: # the last of the uavs are gone
                self.env.end_sim.succeed()


        if print_events: print "%s is available to shoot again at %.2f" % (self, self.env.now)
        self.resource.release(request)


class Radar(object):
    def __init__(self, env, period, ranges, p_detect, ship):
        self.env = env
        self.period = period
        self.ranges = ranges
        self.p_detect = p_detect
        self.ship = ship
        ship.radars.append(self)

        self.destroyed = env.event()

        self.action = []
        for uav in self.env.uavs:
            self.action.append(env.process(self.search(uav)))

    def __str__(self):
        return "Rdr_" + str(id(self))

    def search(self,uav):
        """
        ExtendSim model uses 0% beyond 55440, otherwise
        0.916062716 - 0.0000147197 * distance
        """
        time_to_detect = 0
        detected_uav = self.env.timeout(time_to_detect)
        result = yield self.destroyed | uav.reached_ship | detected_uav
        if detected_uav in result:
            if print_events: print "%s spotted %s at %.2f" % (self, uav, self.env.now)
            yield self.env.timeout(90.) # the "human reaction time" from ExtendSim
            self.env.process(self.ship.alert(uav))


class Ship(object):
    def __init__(self, env, pos, speed=10.):
        self.env = env
        self.pos = pos
        self.speed = speed
        self.health = 1
        self.weapons = []
        self.radars = []

    def __str__(self):
        return "Shp_" + str(id(self))

    def alert(self, uav):
        # print "%s is aware of %s at %.2f" % (self, uav, self.env.now)
        events = [uav.reached_ship, uav.shot_down]
        requests = [] # to iterate over only these events later
        weaponId = {} # to tell which request goes with which weapon
        for weapon in self.weapons:
            request = weapon.resource.request()
            requests.append(request)
            weaponId[request] = weapon

        events += requests
        result = yield simpy.events.AnyOf(self.env, events)
        if uav.reached_ship in result or uav.shot_down in result:
            pass # the uav controls these cases
        else:
            # assign first weapon only to shoot at the uav
            is_first = True
            for request in requests:
                if is_first and request in result:
                    if print_events: print "%s assigned %s to %s at %.2f" % (self, uav, weaponId[request], self.env.now)
                    first_request = request
                    is_first = False
                else:
                    weaponId[request].resource.release(request)

            self.env.process(weaponId[first_request].shoot_uav(uav, first_request))
