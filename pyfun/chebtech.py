# -*- coding: utf-8 -*-
"""
"""
from __future__ import division

from abc import ABCMeta
from abc import abstractmethod

from numpy import finfo
from numpy import array
from numpy import ones
from numpy import arange
from numpy import append
from numpy import pi
from numpy import cos
from numpy import real
from numpy import imag
from numpy import isreal
from numpy import linspace
from numpy import zeros

from numpy.fft import fft
from numpy.fft import ifft

from matplotlib.pyplot import gca

from utilities import ctor_adaptive
from utilities import bary
from utilities import clenshaw

# machine epsilon
eps = finfo(float).eps

class ChebTech(object):
    """Abstract base class serving as the template for ChebTech1 and 
    ChebTech2 subclasses. 
    
    ChebTech objects always work with first-kind coefficients, so much 
    of the core operational functionality is defined this level.
    
    The user will rarely work with these classes directly so we make
    several assumptions regarding input data types.
    """
    __metaclass__ = ABCMeta
    
    def __init__(self, coeffs):
        self._coeffs = coeffs

    @classmethod
    def initfun(cls, fun, n=None):
        if n is None:
            return cls.initfun_adaptive(fun)
        else:
            return cls.initfun_fixedlen(fun, n)

    @classmethod
    def initfun_fixedlen(cls, fun, n):
        points = cls.chebpts(n)
        values = fun(points)
        coeffs = cls._vals2coeffs(values)
        return cls(coeffs)

    @classmethod
    def initfun_adaptive(cls, fun):
        coeffs = ctor_adaptive(cls, fun)
        return cls(coeffs)

    def __call__(self, x, how="clenshaw"):
        method = {
            "clenshaw": self.__call__clenshaw,
            "bary": self.__call__bary,
            }
        try:
            return method[how](x)
        except KeyError:
            raise ValueError(how)

    def __call__clenshaw(self, x):
        return clenshaw(x, self._coeffs)
        
    def __call__bary(self, x):
        fk = self.values()
        xk = self.chebpts(fk.size)
        vk = self.barywts(fk.size)
        return bary(x, fk, xk, vk)

    def __repr__(self):
        out = "{} <{}>".format(self.__class__.__name__, self.size())
        return out

    def coeffs(self):
        """Chebyshev expansion coefficients in the T_k basis"""
        return self._coeffs

    def values(self):
        """Function values at Chebyshev points"""
        return self._coeffs2vals(self._coeffs)

    def size(self):
        """Return the size of the object"""
        return self.coeffs().size

    def isempty(self):
        """Return the shape of the ChebTech2"""
        return self.size() == 0

    def sum(self):
        """Definite integral of a ChebTech on the interval [-1,1]"""
        ak = self.coeffs().copy()
        if ak.size == 0:        # empty
            out = None
        elif ak.size == 1:      # constant
            out = 2*ak
        else:
            ak[1::2] = 0
            kk = arange(2, ak.size)
            ii = append([2,0], 2/(1-kk**2))
            out = (ak*ii).sum()
        return out

    def cumsum(self):
        """Return a ChebTech object representing the indefinite integral
        of a ChebTech on the interval [-1,1]. The constant term is chosen
        such that F(-1) = 0."""
        if self.size() == 0:
            out = self
        else:
            n = self.size()
            ak = append(self.coeffs(), [0, 0])
            bk = zeros(n+1)
            rk = arange(2,n+1)
            bk[2:] = (ak[1:n] - ak[3:n+2]) / (2*rk)
            bk[1] = ak[0] - .5*ak[2]
            vk = ones(n)
            vk[1::2] = -1
            bk[0] = (vk*bk[1:]).sum()
            out = self.__class__(bk)
        return out

    def plot(self, ax=None, *args, **kwargs):
        ax = ax if ax else gca()
        xx = linspace(-1, 1, 2001)
        yy = self(xx)
        ax.plot(xx, yy, *args, **kwargs)
        return ax

    def plotcoeffs(self, ax=None, *args, **kwargs):
        ax = ax if ax else gca()
        abscoeffs = abs(self._coeffs)
        ax.semilogy(abscoeffs, ".", *args, **kwargs)
        ax.set_ylabel("coefficient magnitude")
        ax.set_xlabel("polynomial degree")
        return ax

    # --------------------------------------------------
    #          abstract method declarations
    # --------------------------------------------------
    @abstractmethod
    def chebpts():
        pass

    @abstractmethod
    def barywts():
        pass
    
    @abstractmethod
    def _vals2coeffs():
        pass

    @abstractmethod
    def _coeffs2vals():
        pass
    # --------------------------------------------------


class ChebTech2(ChebTech):
    """Second-Kind Chebyshev technology"""
    
    @staticmethod
    def chebpts(n):
        """Return n Chebyshev points of the second-kind"""
        if n == 1:
            pts = array([0.])
        else:
            nn = arange(n)
            pts = cos( nn[::-1] * pi/(n-1) )
        return pts

    @staticmethod
    def barywts(n):
        """Barycentric weights for Chebyshev points of 2nd kind"""
        if n == 0:
            wts = array([])
        elif n == 1:
            wts = array([1])
        else:
            wts = append( ones(n-1), .5 )
            wts[n-2::-2] = -1
            wts[0] = .5 * wts[0]
        return wts
    
    @staticmethod
    def _vals2coeffs(vals):
        """Map function values at Chebyshev points of 2nd kind to 
        first-kind Chebyshev polynomial coefficients"""        
        n = vals.size
        if n <= 1:
            coeffs = vals
            return coeffs
            
        tmp = append( vals[::-1], vals[1:-1] )    
        
        if isreal(vals).all():
            coeffs = ifft(tmp)
            coeffs = real(coeffs)
      
        elif isreal( 1j*vals ).all():
            coeffs = ifft( imag(tmp) )
            coeffs = 1j * real(coeffs)
            
        else:
            coeffs = ifft(tmp)            
        
        coeffs = coeffs[:n]        
        coeffs[1:n-1] = 2*coeffs[1:n-1]
        return coeffs

    @staticmethod
    def _coeffs2vals(coeffs):
        """Map first-kind Chebyshev polynomial coefficients to 
        function values at Chebyshev points of 2nd kind"""
        n = coeffs.size
        if n <= 1:
            vals = coeffs
            return vals
        
        coeffs = coeffs.copy()
        coeffs[1:n-1] = .5 * coeffs[1:n-1]
        tmp = append( coeffs, coeffs[n-2:0:-1] )
         
        if isreal(coeffs).all():
            vals = fft(tmp)
            vals = real(vals)
            
        elif isreal( 1j*coeffs ).all():
            vals = fft( imag(tmp) )
            vals = 1j * real(vals)
            
        else:
            vals = fft(tmp)    
            
        vals = vals[n-1::-1]
        return vals
