import numpy as np
from math import exp
from math import log
from gcubed.base_equations import BaseEquations


class Equations(BaseEquations):

    # Equation block 1

    def x1l_0(self):
        self.x1l[0] = self.yxr[0]
    # Equation block 2

    def z1l_0(self):
        self.z1l[0] = self.yxr[0]

# End of G-cubed equations class declaration
