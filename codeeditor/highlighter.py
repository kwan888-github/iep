""" Module highlighter

Defines the highlighter class for the base code editor class. It will do
the styling when syntax highlighting is enabled. If it is not, will only 
check out indentation.

"""

import time

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

from . import parsers
from .misc import ustr


class BlockData(QtGui.QTextBlockUserData):
    """ Class to represent the data for a block.
    """
    def __init__(self):
        QtGui.QTextBlockUserData.__init__(self)
        self.indentation = None


# The highlighter should be part of the base class, because 
# some extensions rely on them (e.g. the indent guuides).
class Highlighter(QtGui.QSyntaxHighlighter):
    
    def __init__(self,codeEditor,*args):
        QtGui.QSyntaxHighlighter.__init__(self,*args)
        
        # Store reference to editor
        self._codeEditor = codeEditor
        
        # For timing
        self._cumTime = 0
        self._cumN = 0
    
    
    def getCurrentBlockUserData(self):
        """ getCurrentBlockUserData()
        
        Gets the BlockData object. Creates one if necesary.
        
        """
        bd = self.currentBlockUserData()
        if not isinstance(bd, BlockData):
            bd = BlockData()
            self.setCurrentBlockUserData(bd)
        return bd
    
    
    def highlightBlock(self, line): 
        """ highlightBlock(line)
        
        This method is automatically called when a line must be 
        re-highlighted.
        
        If the code editor has an active parser. This method will use
        it to perform syntax highlighting. If not, it will only 
        check out the indentation.
        
        """
        
        t0 = time.time()
        
        # Make sure this is a Unicode Python string
        line = ustr(line)
        
        # Get previous state
        previousState = self.previousBlockState()
        
        # Get parser
        parser = None
        if hasattr(self._codeEditor, 'parser'):
            parser = self._codeEditor.parser()
        
        # Get function to get format
        nameToFormat = self._codeEditor.getStyleElementFormat
        
        if parser:
            self.setCurrentBlockState(0)
            for token in parser.parseLine(line, previousState):
                # Handle block state
                if isinstance(token, parsers.BlockState):
                    self.setCurrentBlockState(token.state)
                else:
                    # Get format
                    try:
                        format = nameToFormat(token.name).textCharFormat
                    except KeyError:
                        #print(repr(nameToFormat(token.name)))
                        continue
                    # Set format
                    self.setFormat(token.start,token.end-token.start,format)
                
        
        #Get the indentation setting of the editors
        indentUsingSpaces = self._codeEditor.indentUsingSpaces()
        
        # Get user data
        bd = self.getCurrentBlockUserData()
        
        leadingWhitespace=line[:len(line)-len(line.lstrip())]
        if '\t' in leadingWhitespace and ' ' in leadingWhitespace:
            #Mixed whitespace
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.red)
            format.setToolTip('Mixed tabs and spaces')
            self.setFormat(0,len(leadingWhitespace),format)
        elif ('\t' in leadingWhitespace and indentUsingSpaces) or \
            (' ' in leadingWhitespace and not indentUsingSpaces):
            #Whitespace differs from document setting
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.blue)
            format.setToolTip('Whitespace differs from document setting')
            self.setFormat(0,len(leadingWhitespace),format)
        else:
            # Store info for indentation guides
            # amount of tabs or spaces
            bd.indentation = len(leadingWhitespace)
        
        # Timing experiment
        if False:
            t1 = time.time()
            self._cumTime += t1-t0
            self._cumN += 1
            if self._cumTime > 0.1:
                if 'log' not in self.__class__.__name__.lower():
                    print(self._cumN, self._cumTime/self._cumN)
                self._cumTime = 0
                self._cumN = 0
