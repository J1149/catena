import matplotlib.pyplot as plt
import numpy as np

class Rule:
    pass


class Environment:
    pass


class Box:

    def __init__(self, env, rules):
        self.env = env
        self.rules = rules


class Generator:

    def __init__(self, seed=0):
        pass

    def next(self):
        pass


if __name__ == '__main__':
    # create a wireframe sphere
    # create a particle that moves along the sphere
    # create a force that moves the particle along the sphere
    # have camera follow particle along the sphere
    # have squares light up as particle goes along them
    # maybe autogenerate mountains and valleys for the particle to go along
    ## make the mountains and valleys fall like water droplets into water
    x = np.arange(0, 100, 1e-3)
    y = np.arange(0, 100, 1e-3)
    z = np.sqrt(x**2+y**2)
    plt.plot(x, y)
    plt.show()
