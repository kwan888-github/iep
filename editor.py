
import iep
import time
from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui
sci = Qsci


class InteractiveAPI(sci.QsciAPIs):
    """ API that will query introspection information
    from the current session.
    """
    def __init__(self, lexer):
        sci.QsciAPIs.__init__(self, lexer)
        
        self.add("foo(lala)")
        self.add("bar")
        #self.prepare()


class IepTextCtrl(sci.QsciScintilla):
    """ The base text control class.
    Inherited by the shell class and the IEP editor.
    The class implements autocompletion, calltips, and auto-help.
    """
    
    def __init__(self, parent):
        sci.QsciScintilla.__init__(self,parent)
        
        # SET PREFERENCES
        # Inherited classes may override some of these settings. Indentation
        # guides are not nice in shells for instance...
        
        # things I might want to make optional/settable
        #
        
        # edge indicator
        self.setEdgeColumn(iep.config.edgeColumn) 
        self.setEdgeMode(self.EdgeLine)
        # indentation  
        self.setIndentationWidth(iep.config.indentWidth)        
        self.setTabWidth(iep.config.indentWidth)        
        self.setIndentationGuides(iep.config.showIndentGuides)
        tmp = {0:self.WsInvisible, 1:self.WsVisible}
        self.setWhitespaceVisibility(tmp[iep.config.showWhiteSpace])        
        # line numbers
        self.setMarginLineNumbers(1,True)        
        self.setMarginWidth(1, 30)
        # wrapping
        if iep.config.wrapText:
            self.setWrapMode(self.WrapCharacter)
        else:
            self.setWrapMode(self.WrapNone)            
        self.setWrapVisualFlags(self.WrapFlagNone)
        # line endings
        self.setEolMode(self.EolUnix) # lf is default
        
        # things I'm pretty sure about...        
        #
        
        # tab stuff        
        self.setIndentationsUseTabs(False)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)     
        self.setAutoIndent(True) # indents if previous line is indented
           
        # In QT, the vertical scroller is always shown        
        
        # set brace matchin on
        self.setBraceMatching(self.SloppyBraceMatch)
        
        # calltips, I dont know what this exactly does
        self.setCallTipsStyle(self.CallTipsNoContext)
        
        # autocompletion setting
        self.setAutoCompletionThreshold(1) # 0 means disabled
        self.setAutoCompletionReplaceWord(False)
        self.setAutoCompletionShowSingle(False)
        #self.setAutoCompletionCaseSensitivity(False) # but is overriden in lexer
        # there are more settings, but these are all overriden by the lexer
        
        # set lexer and attach custom API
        self._lexer = lexer = sci.QsciLexerPython()
        self.setLexer(lexer) 
        lexer.setAPIs(InteractiveAPI(lexer))
        
        # do autocomple automagically
        #self.setAutoCompletionSource(self.AcsAPIs)
        # or determine when this happens... 
        # (so I can determine when to call callTip)
        self.connect(self, QtCore.SIGNAL('textChanged()'), self.onTextChanged)
        
        # calltip colours...
        self.setCallTipsBackgroundColor(qt.QColor('#FFFFB8'))
        self.setCallTipsForegroundColor(qt.QColor('#404040'))
        self.setCallTipsHighlightColor(qt.QColor('#0000FF'))
        
        # selection colours...
        self.setSelectionBackgroundColor(qt.QColor('#333366'))
        self.setSelectionForegroundColor(qt.QColor('#CCCCCC'))
    
    def onTextChanged(self):        
        self.autoCompleteFromAPIs()        
        #self.callTip()
        
    def getCurrentPos(self):
        """ Get the position (as an int) of the cursor. 
        getCursorPosition() returns a (line, index) tuple.
        """        
        return self.SendScintilla(self.SCI_GETCURRENTPOS)
        
    def styleAt(self, pos):
        """ Get the style at the given position."""
        return self.SendScintilla(self.SCI_GETSTYLEAT,pos)
        
    def charAt(self,pos):
        char = self.SendScintilla(self.SCI_GETCHARAT, pos)
        if char == 0:
            return ""
            elif char < 0:
                return chr(char + 256)
            else:
                return chr(char)
    
    def positionFromLineIndex(self, line, index):
        """ Method to convert line and index to an absolute position.
        """
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
        # Allow for multi-byte characters
        for i in range(index):
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONAFTER, pos)
        return pos
        
    def Introspect_isValidPython(self):
        """ Check if the code at the cursor is valid python:
        - the active lexer is the python lexer
        - the style at the cursor is "default"
        """
        
        # only complete if lexer is python
        if ~isinstance(self.lexer(), sci.QsciLexerPython):
            return False
        
        # the style must be "default"
        curstyle = self.styleAt(self.getCurrentPos())
        if curstyle not in [self._lexer.Default, self._lexer.Operator]:
            return False
        
        # all good
        return True  


if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepTextCtrl(None)
    win.show()
    app.exec_()
    
    