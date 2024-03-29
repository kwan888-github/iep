# -*- coding: utf-8 -*-
# Copyright (C) 2012, the codeeditor development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

import re
from . import tokens, Parser, BlockState
from .tokens import ALPHANUM


# Import tokens in module namespace
from .tokens import (CommentToken, StringToken, 
    UnterminatedStringToken, IdentifierToken, NonIdentifierToken,
    KeywordToken, NumberToken, FunctionNameToken, ClassNameToken,
    TodoCommentToken)

from .python_parser import (  PythonParser,
                                                MultilineStringToken,
                                                CellCommentToken,
                                                pythonKeywords)

# Set keywords
cythonExtraKeywords = set(['cdef', 'cpdef', 'ctypedef', 'cimport',
                    'float', 'double', 'int', 'long'])


class CythonParser(PythonParser):
    """ Parser for Cython/Pyrex.
    """
    _extensions = ['pyi', '.pyx' , '.pxd']
    
    _keywords = pythonKeywords | cythonExtraKeywords
    
    
    def _identifierState(self, identifier=None):
        """ Given an identifier returs the identifier state:
        3 means the current identifier can be a function.
        4 means the current identifier can be a class.
        0 otherwise.
        
        This method enables storing the state during the line,
        and helps the Cython parser to reuse the Python parser's code.
        
        This implementation keeps a counter. If the counter is 0, the
        state is zero.
        """
        if identifier is None:
            # Explicit get and reset
            state = 0
            try:
                if self._idsCounter>0:
                    state = self._idsState
            except Exception:
                pass            
            self._idsState = 0
            self._idsCounter = 0
            return state
        elif identifier in ['def', 'cdef', 'cpdef']:
            # Set function state
            self._idsState = 3
            self._idsCounter = 2
            return 3
        elif identifier == 'class':
            # Set class state
            self._idsState = 4
            self._idsCounter = 1
            return 4
        elif self._idsCounter>0:
            self._idsCounter -= 1
            return self._idsState
        else:
            # This one can be func or class, next one can't
            return 0
