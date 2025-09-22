import numpy as np
from math import exp
from math import log
from gcubed.base_equations import BaseEquations


class Equations(BaseEquations):

    # Equation block 1

    def z1l_0(self):
        self.z1l[0] = 0
    # Equation block 2

    def x1l_0(self):
        self.x1l[0] = self.z1r[0]

# End of G-cubed equations class declaration


import numpy as np
from math import exp
from math import log
from gcubed.base_equations import BaseEquations


class Equations(BaseEquations):

    # Equation block 1

    def x1l_0(self):
        self.x1l[0] = 0
    # Equation block 2

    def x1l_1(self):
        self.x1l[1] = self.x1r[0]

# End of G-cubed equations class declaration
