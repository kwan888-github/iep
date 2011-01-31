import sys
from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

import keyword
if __name__ == '__main__':
    import python_syntax
else:
    from . import python_syntax

class BlockData(QtGui.QTextBlockUserData):
    def __init__(self):
        QtGui.QTextBlockUserData.__init__(self)
        self.indentation = None

    
class Highlighter(QtGui.QSyntaxHighlighter):
    formats=(
        (python_syntax.StringToken,(0x7F007F,'')), 
        (python_syntax.CommentToken,(0x007F00,'')),
        (python_syntax.UnterminatedToken,(0,'')),
        (python_syntax.KeywordToken,(0x00007F,'B')),
        (python_syntax.NumberToken,(0x007F7F,'')),
        (python_syntax.MethodNameToken,(0x007F7F,'B')),
        (python_syntax.ClassNameToken,(0x0000FF,'B'))
        )
    def __init__(self,*args):
        QtGui.QSyntaxHighlighter.__init__(self,*args)
        #Init properties
        self.indentation = False
    ## Properties
    @property
    def indentation(self):
        """
        The number of spaces for each indentation level, or
        0 when tabs are used for indentation
        """
        return self._indentation
    
    @indentation.setter
    def indentation(self,value):
        if (not value):
            value = 0
        self._indentation = int(value)
        self.rehighlight()
    
    @property
    def spaceTabs(self):
        """ 
        True when spaces are used and False when tabs are used
        """
        return bool(self.indentation)
    
    def getCurrentBlockUserData(self):
        """ getCurrentBlockUserData()
        
        Gets the BlockData object. Creates one if necesary.
        
        """
        bd = self.currentBlockUserData()
        if not isinstance(bd, BlockData):
            bd = BlockData()
            self.setCurrentBlockUserData(bd)
        return bd
    
    ## Methods
    def highlightBlock(self,line):
        previousState=self.previousBlockState()
        
        self.setCurrentBlockState(0)
        for token in python_syntax.tokenizeLine(line,previousState):
            for tokenType,format in self.formats:
                if isinstance(token,tokenType):
                    color,style=format
                    format=QtGui.QTextCharFormat()
                    format.setForeground(QtGui.QColor(color))
                    if 'B' in style:
                        format.setFontWeight(QtGui.QFont.Bold)
                    #format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
                    #format.setUnderlineColor(QtCore.Qt.red)
                    self.setFormat(token.start,token.end-token.start,format)
                    
            #Handle line or string continuation
            if isinstance(token,python_syntax.ContinuationToken):
                self.setCurrentBlockState(token.state)
        
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
        elif ('\t' in leadingWhitespace and self.spaceTabs) or \
            (' ' in leadingWhitespace and not self.spaceTabs):
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


class LineNumberArea(QtGui.QWidget):
    """ This is the widget reponsible for drawing the line numbers.
    """
    
    def __init__(self, codeEditor):
        QtGui.QWidget.__init__(self, codeEditor)
    
    def codeEditor(self): 
        """ codeEditor()
        
        Get the associated code editor.
        
        """
        return self.parent()
    
    
    def paintEvent(self, event):
        # The paint method is implemented at the code editor, near
        # the paint methods for indent guides and long line indicator.
        self.codeEditor()._paintLineNumbers(event)


class CalltipLabel(QtGui.QLabel):
    
    def __init__(self):
        QtGui.QLabel.__init__(self)
        
        # Start hidden
        self.hide()
        # Accept rich text
        self.setTextFormat(QtCore.Qt.RichText)
        # Set appearance
        self.setStyleSheet("QLabel { background:#ff9; border:1px solid #000; }")
        # Show as tooltip
        self.setWindowFlags(QtCore.Qt.ToolTip)
    
    def enterEvent(self, event):
        # Act a bit like a tooltip
        self.hide()


class CodeEditor(QtGui.QPlainTextEdit):
    def __init__(self,*args,**kwds):
        QtGui.QPlainTextEdit.__init__(self,*args,**kwds)
        
        # Set font (always monospace)
        self.setFont()
        
        # Create highlighter class
        # todo: attribute is not private
        self.highlighter = Highlighter(self.document())
        
        # Create widget that draws the line numbers
        self._lineNumberArea = LineNumberArea(self)
        
        # Autocompleter
        self._completerModel=QtGui.QStringListModel(keyword.kwlist)
        self._completer=QtGui.QCompleter(self._completerModel, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setWidget(self)
        self._completerNames=[]
        self._recentCompletions=[] #List of recently selected completions
        
        # Text position corresponding to first charcter of the word being completed
        self._autocompleteStart=None
        
        # Create label for call tips
        self._calltipLabel = CalltipLabel()
        
        
        #Default options
        option=self.document().defaultTextOption()
        option.setFlags(option.IncludeTrailingSpaces|option.AddSpaceForLineAndParagraphSeparators)
        self.document().setDefaultTextOption(option)
        
        #Init properties
        self.wrap = True
        self.showWhitespace = False
        self.showLineEndings = False
        self.showLineNumbers = False
        self.showIndentationGuides = True
        self.highlightCurrentLine = False
        self.indentation = 4
        self.tabWidth = 4
        self.longLineIndicator = 80

        #Connect signals
        self.connect(self._completer,QtCore.SIGNAL("activated(QString)"),self.onAutoComplete)
        self.cursorPositionChanged.connect(self.update)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
    
    
    
    def focusOutEvent(self, event):
        QtGui.QPlainTextEdit.focusOutEvent(self, event)
        self._calltipLabel.hide()
    
    ## Font
    
    def fontNames(self):
        """ fontNames()
        
        Get a list of all monospace fonts available on this system.
        
        """
        db = QtGui.QFontDatabase()
        QFont, QFontInfo = QtGui.QFont, QtGui.QFontInfo
        # fn = font_name (str)
        return [fn for fn in db.families() if QFontInfo(QFont(fn)).fixedPitch()]
    
    
    def defaultFont(self):
        """ defaultFont()
        
        Get the default (monospace font) for this system. Returns a QFont
        object. 
        
        """
        
        # Get font size
        f = QtGui.QFont()
        size = f.pointSize()
        
        # Get font family
        f = QtGui.QFont('this_font_name_must_not exist')
        f.setStyleHint(f.TypeWriter, f.PreferDefault)
        fi = QtGui.QFontInfo(f)
        family = fi.family()
        
        # The default family seems to be Courier new on Mac
        if sys.platform == 'darwin':            
            family = 'Monaco'
        
        # Done
        return QtGui.QFont(family, size)
    
    
    def setFont(self, font=None):
        """ setFont(font=None)
        
        Set the font for the editor. Should be a monospace font. If not,
        Qt will select the best matching monospace font.
        
        """
        
        # Check
        if font is None:
            font = self.defaultFont()
        elif isinstance(font, QtGui.QFont):
            pass
        elif isinstance(font, str):
            font = QtGui.QFont(font, self.defaultFont().pointSize())
        else:
            raise ValueError("setFont accepts None, QFont or string.")
        
        # Make sure it's monospace
        font.setStyleHint(font.TypeWriter, font.PreferDefault)
        # todo: can be done smarter, return resulting font, implement zooming
        
        # Set
        QtGui.QPlainTextEdit.setFont(self, font)
    
    
    ## Properties

    #wrap
    @property
    def wrap(self):
        option=self.document().defaultTextOption()
        return not bool(option.wrapMode() == option.NoWrap)
        
    @wrap.setter
    def wrap(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setWrapMode(option.WrapAtWordBoundaryOrAnywhere)
        else:
            option.setWrapMode(option.NoWrap)
        self.document().setDefaultTextOption(option)
    
    
    #show line numbers
    @property
    def showLineNumbers(self):
        return self._showLineNumbers
    
    @showLineNumbers.setter
    def showLineNumbers(self,value):
        self._showLineNumbers = bool(value)
        if self._showLineNumbers:
            self.updateLineNumberAreaWidth()
            self._lineNumberArea.show()
        else:
            self.setViewportMargins(0,0,0,0)
            self._lineNumberArea.hide()
    
    
    #show indentation guides
    @property
    def showIndentationGuides(self):
        return self._showIndentationGuides
    
    @showIndentationGuides.setter
    def showIndentationGuides(self,value):
        self._showIndentationGuides = bool(value)
        self.hide(); self.show()
    
    
    #show whitespace
    @property
    def showWhitespace(self):
        """Show or hide whitespace markers"""
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowTabsAndSpaces)
        
    @showWhitespace.setter
    def showWhitespace(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~option.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(option)
    
    #show line endings
    @property
    def showLineEndings(self):
        """Show or hide line ending markers"""
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowLineAndParagraphSeparators)
        
    @showLineEndings.setter
    def showLineEndings(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowLineAndParagraphSeparators)
        else:
            option.setFlags(option.flags() & ~option.ShowLineAndParagraphSeparators)
        self.document().setDefaultTextOption(option)
    
    
    @property
    def longLineIndicator(self):
        """ The position of the long line indicator 
        (0 or False means not visible). 
        """
        return self._longLineIndicator
    
    @longLineIndicator.setter
    def longLineIndicator(self,value):
        if not isinstance(value, int):
            raise ValueError('Long line indicator must be an int.')
        if value < 0:
            value = 0
        self._longLineIndicator = int(value)
        self.hide(); self.show()
    
    #NEW PROPERTY NAMES: indentWidth and indentUsingSpaces
    
    #tab size
    @property
    def tabWidth(self):
        """Size of a tab stop in characters"""
        return self._tabWidth
        
    @tabWidth.setter
    def tabWidth(self,value):
        self._tabWidth = int(value)
        self.setTabStopWidth(self.fontMetrics().width('i')*self._tabWidth)
        
    @property
    def spaceTabs(self):
        """
        True when spaces are used and False when tabs are used
        """
        return bool(self.indentation)
    #indentation
    @property
    def indentation(self):
        """
        Number of spaces to insert when the tab key is pressed, or 
        0 to insert tabs
        """
        return self._indentation
    
    @indentation.setter
    def indentation(self,value):
        if (not value): #Also support assignment by None or False etc
            value = 0
        self._indentation = int(value)
        self.highlighter.indentation = self._indentation
    
    #highlight current line
    @property
    def highlightCurrentLine(self):
        return self._highlightCurrentLine
    
    @highlightCurrentLine.setter
    def highlightCurrentLine(self,value):
        self._highlightCurrentLine = bool(value)
        #self.update()
    
    #Completer
    @property
    def completer(self):
        return self._completer
    
    #Recent completions
    @property
    def recentCompletions(self):
        """ 
        The list of recent auto-completions. This property may be set to a
        list that is shared among several editors, in order to share the notion
        of recent auto-completions
        """
        return self._recentCompletions
    
    @recentCompletions.setter
    def recentCompletions(self,value):
        self._recentCompletions = value
        
    ## MISC
        
    def gotoLine(self,lineNumber):
        """
        Move the cursor to the block given by the line number (first line is line number 1) and show that line
        """
        cursor = self.textCursor()
        block = self.document().findBlockByNumber( lineNumber + 1)
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        
    def _cursorIsInLeadingWhitespace(self,cursor = None):
        """
        Checks wether the given cursor is in the leading whitespace of a block, i.e.
        before the first non-whitespace character. The cursor is not modified.
        If the cursor is not given or is None, the current textCursor is used
        """
        if cursor is None:
            cursor = self.textCursor()
        
        # Get the text of the current block up to the cursor
        textBeforeCursor = cursor.block().text()[:cursor.positionInBlock()]
        return textBeforeCursor.lstrip() == '' #If we trim it and it is empty, it's all whitespace
        
    def doForSelectedBlocks(self,function):
        """
        Call the given function(cursor) for all blocks in the current selection
        A block is considered to be in the current selection if a part of it is in
        the current selection 
        
        The supplied cursor will be located at the beginning of each block. This
        cursor may be modified by the function as required
        """
        
        #Note: a 'TextCursor' does not represent the actual on-screen cursor, so
        #movements do not move the on-screen cursor
        
        #Note 2: when the text is changed, the cursor and selection start/end
        #positions of all cursors are updated accordingly, so the screenCursor
        #stays in place even if characters are inserted at the editCursor
        
        screenCursor = self.textCursor() #For maintaining which region is selected
        editCursor = self.textCursor()   #For inserting the comment marks
    
        #Use beginEditBlock / endEditBlock to make this one undo/redo operation
        editCursor.beginEditBlock()
            
        editCursor.setPosition(screenCursor.selectionStart())
        editCursor.movePosition(editCursor.StartOfBlock)
        # < : if selection end is at beginning of the block, don't include that one
        while editCursor.position()<screenCursor.selectionEnd(): 
            #Create a copy of the editCursor and call the user-supplied function
            editCursorCopy = QtGui.QTextCursor(editCursor)
            function(editCursorCopy)
            
            #Move to the next block
            if not editCursor.block().next().isValid():
                break #We reached the end of the document
            editCursor.movePosition(editCursor.NextBlock)
            
        editCursor.endEditBlock()
    
    def indentBlock(self,cursor,amount = 1):
        """
        Indent the block given by cursor
        The cursor specified is used to do the indentation; it is positioned
        at the beginning of the first non-whitespace position after completion
        May be overridden to customize indentation
        """
        text = cursor.block().text()
        leadingWhitespace = text[:len(text)-len(text.lstrip())]
        
        #Select the leading whitespace
        cursor.movePosition(cursor.StartOfBlock)
        cursor.movePosition(cursor.Right,cursor.KeepAnchor,len(leadingWhitespace))
        
        #Compute the new indentation length, expanding any existing tabs
        indent = len(leadingWhitespace.expandtabs(self.tabWidth))
        if self.spaceTabs:            
            # Determine correction, so we can round to multiples of indentation
            correction = indent % self.indentation
            if correction and amount<0:
                correction = - (self.indentation - correction) # Flip
            # Add the indentation tabs
            indent += (self.indentation * amount) - correction
            cursor.insertText(' '*max(indent,0))
        else:
            # Convert indentation to number of tabs, and add one
            indent = (indent // self.tabWidth) + amount
            cursor.insertText('\t' * max(indent,0))
            
    def dedentBlock(self,cursor):
        """
        Dedent the block given by cursor
        Calls indentBlock with amount = -1
        May be overridden to customize indentation
        """
        self.indentBlock(cursor, amount = -1)
        
    def indentSelection(self):
        """
        Called when the current line/selection is to be indented.
        Calls indentLine(cursor) for each line in the selection
        May be overridden to customize indentation
        
        See also doForSelectedBlocks and indentBlock
        """
        
        self.doForSelectedBlocks(self.indentBlock)
    def dedentSelection(self):
        """
        Called when the current line/selection is to be dedented.
        Calls dedentLine(cursor) for each line in the selection
        May be overridden to customize indentation
        
        See also doForSelectedBlocks and dedentBlock
        """
        
        self.doForSelectedBlocks(self.dedentBlock)
        
    def setStyle(self,style):
        #TODO: to be implemented
        pass
        
#     def _lineNumberAreaPaintEvent(self,event):
#         painter = QtGui.QPainter(self._lineNumberArea)
#         cursor = self.cursorForPosition(self.viewport().pos())
#         
#         #Draw the background
#         painter.fillRect(event.rect(),Qt.lightGray)
#         
#         # Init painter
#         painter.setPen(Qt.black)
#         painter.setFont(self.font())
#         
#         #Repainting always starts at the first block in the viewport,
#         #regardless of the event.rect().y(). Just to keep it simple
#         while True:
#             blockNumber=cursor.block().blockNumber()
#             
#             y=self.cursorRect(cursor).y()+self.viewport().pos().y()+1 #Why +1?
#             painter.drawText(0,y,self.getLineNumberAreaWidth()-2,50,
#                 Qt.AlignRight,str(blockNumber+1))
#             
#             if y>event.rect().bottom():
#                 break #Reached end of the repaint area
#             if not cursor.block().next().isValid():
#                 break #Reached end of the text
# 
#             cursor.movePosition(cursor.NextBlock)
    
    def getLineNumberAreaWidth(self):
        """
        Count the number of lines, compute the length of the longest line number
        (in pixels)
        """
        if not self.showLineNumbers:
            return 0
        lastLineNumber = self.blockCount() 
        return self.fontMetrics().width(str(lastLineNumber)) + 6 # margin

        
    ##Custom signal handlers
    def updateCurrentLineHighlight(self):
        """Create a selection region that shows the current line"""
        #Taken from the codeeditor.cpp example
        if not self.highlightCurrentLine:
            return
        
        selection = QtGui.QTextEdit.ExtraSelection()
        lineColor = QtGui.QColor(Qt.yellow).lighter(160);

        selection.format.setBackground(lineColor);
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor();
        selection.cursor.clearSelection();
        self.setExtraSelections([selection])
    
    
    def updateLineNumberAreaWidth(self,count=None):
        """ updateLineNumberAreaWidth()
        
        Update the line number area width. This requires to set the 
        viewport margins, so there is space to draw the linenumber area
        widget.
        
        """
        if self.showLineNumbers:
            self.setViewportMargins(self.getLineNumberAreaWidth(),0,0,0)
    
    
    ## Autocompletion
    def autocompleteShow(self,offset = 0,names = None):
        """
        Pop-up the autocompleter (if not already visible) and position it at current
        cursor position minus offset. If names is given and not None, it is set
        as the list of possible completions.
        """
        #Pop-up the autocompleteList
        startcursor=self.textCursor()
        startcursor.movePosition(startcursor.Left, n=offset)
        
        if not self.autocompleteActive() or \
            startcursor.position() != self._autocompleteStart:

            self._autocompleteStart=startcursor.position()

            #Popup the autocompleter. Don't use .complete() since we want to
            #position the popup manually
            self._positionAutocompleter()
            self._updateAutocompleterPrefix()
            self._completer.popup().show()
        

        if names is not None:
            #TODO: a more intelligent implementation that adds new items and removes
            #old ones
            if names != self._completerNames:
                self._completerModel.setStringList(names)
                self._completerNames = names

        self._updateAutocompleterPrefix()
    def autocompleteAccept(self):
        pass
    def autocompleteCancel(self):
        self._completer.popup().hide()
        self._autocompleteStart = None
        
    def onAutoComplete(self,text):
        #Select the text from autocompleteStart until the current cursor
        cursor=self.textCursor()
        cursor.setPosition(self._autocompleteStart,cursor.KeepAnchor)
        #Replace it with the selected text 
        cursor.insertText(text)
        self._autocompleteStart=None
        self.autocompleteCancel() #Reset the completer
        
        #Update the recent completions list
        if text in self._recentCompletions:
            self._recentCompletions.remove(text)
        self._recentCompletions.append(text)
        
    def autocompleteActive(self):
        """ Returns whether an autocompletion list is currently shown. 
        """
        return self._autocompleteStart is not None
    
        
    def _positionAutocompleter(self):
        """Move the autocompleter list to a proper position"""
        #Find the start of the autocompletion and move the completer popup there
        cur=self.textCursor()
        cur.setPosition(self._autocompleteStart)
        position = self.cursorRect(cur).bottomLeft() + \
            self.viewport().pos() #self.geometry().topLeft() +
        self._completer.popup().move(self.mapToGlobal(position))
        
        #Set size
        geometry = self._completer.popup().geometry()
        geometry.setWidth(200)
        geometry.setHeight(100)
        self._completer.popup().setGeometry(geometry)
    
    def _updateAutocompleterPrefix(self):
        """
        Find the autocompletion prefix (the part of the word that has been 
        entered) and send it to the completer
        """
        prefix=self.toPlainText()[self._autocompleteStart:
        self.textCursor().position()]

        self._completer.setCompletionPrefix(prefix)
        model = self._completer.completionModel()
        if model.rowCount():
            #Iterate over the matches, find the one that was most recently used
            #print (self._recentCompletions)
            recentFound = -1
            recentFoundRow = 0 #If no recent match, just select the first match
            
            for row in range(model.rowCount()):
                data = model.data(model.index(row,0),self._completer.completionRole())
                if not data in self._recentCompletions:
                    continue
                
                index = self._recentCompletions.index(data)
                if index > recentFound: #Later in the list = more recent
                    recentFound, recentFoundRow = index, row

            
            self._completer.popup().setCurrentIndex(model.index(recentFoundRow,0));

                
        else:
            #No match, just hide
            self.autocompleteCancel()
    
    
    ## Calltips
    
    def calltipShow(self, offset=0, richText='', highlightFunctionName=True):
        """ calltipShow(offset=0, richText='', highlightFunctionName=True)
        
        Shows the given calltip.
        
        """
        
        # Process calltip text?
        if highlightFunctionName:
            i = richText.find('(')
            if i>0:
                richText = '<b>{}</b>{}'.format(richText[:i], richText[i:])
        
        # Get a cursor to establish the position to show the calltip
        startcursor=self.textCursor()
        startcursor.movePosition(startcursor.Left, n=offset)
        
        # Get position in pixel coordinates
        rect = self.cursorRect(startcursor)
        pos = rect.topLeft()
        pos.setY( pos.y() - rect.height() )
        #pos.setX( pos.x() + self.viewport().pos().x() + 1 )
        pos = self.viewport().mapToGlobal(pos)
        
        # Set text and update font
        self._calltipLabel.setText(richText)
        self._calltipLabel.setFont(self.font())
        
        # Use a qt tooltip to show the calltip
        if richText:
            self._calltipLabel.move(pos)
            self._calltipLabel.show()
        else:
            self._calltipLabel.hide()
    
    
    def calltipCancel(self):
        """ calltipCancel()
        
        Hides the calltip.
        
        """
        self._calltipLabel.hide()
    
    def calltipActive(self):
        """ calltipActive()
        
        Get whether the calltip is currently active.
        
        """
        return self._calltipLabel.isVisible()
    
    
    ##Overridden Event Handlers
    def resizeEvent(self,event):
        QtGui.QPlainTextEdit.resizeEvent(self,event)
        rect=self.contentsRect()
        #On resize, resize the lineNumberArea, too
        self._lineNumberArea.setGeometry(rect.x(),rect.y(),
            self.getLineNumberAreaWidth(),rect.height())
    
    
    def paintEvent(self,event):
        

        
        # Draw guides
        self._paintCurrentLineHighlighter(event)
        self._paintIndentationGuides(event)
        self._paintLongLineIndicator(event)
        
        #Draw the default QTextEdit, then update the lineNumberArea 
        QtGui.QPlainTextEdit.paintEvent(self,event)
        self._lineNumberArea.update(0, 0, 
                self.getLineNumberAreaWidth(), self.height() )
                
    def _paintCurrentLineHighlighter(self,event):
        """ _paintCurrentLineHighlighter(event)
        
        Paints a rectangle spanning the current block (in case of line wrapping, this
        measns multiple lines)
        """
        if not self.highlightCurrentLine:
            return
        
        #Find the top of the current block, and the height
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfBlock)
        top = self.cursorRect(cursor).top()
        cursor.movePosition(cursor.EndOfBlock)
        height = self.cursorRect(cursor).bottom() - top + 1
        
        margin = self.document().documentMargin()
        painter = QtGui.QPainter()
        painter.begin(self.viewport())
        painter.fillRect(QtCore.QRect(margin, top, 
            self.viewport().width() - 2*margin, height),
            QtGui.QColor(Qt.yellow).lighter(160))
        painter.end()
        
    def _paintLineNumbers(self, event):
        """ _paintLineNumbers(event)
        
        Paint the line numbers in the document margin.
        Called by the LineNumberArea widget, but placed here because
        it so much resembles the other paint handlers.
        
        """ 
        
        if not self.showLineNumbers:
            return
        
        # Get doc and viewport
        doc = self.document()
        viewport = self.viewport()
        
        # Init painter
        painter = QtGui.QPainter()
        painter.begin(self._lineNumberArea)
        
        # Get which part to paint. Just do all to avoid glitches
        w = self.getLineNumberAreaWidth()
        y1, y2 = 0, self.height()
        #y1, y2 = event.rect().top()-10, event.rect().bottom()+10

        # Get offset        
        tmp = self._lineNumberArea.mapToGlobal(QtCore.QPoint(0,0))
        offset = viewport.mapFromGlobal(tmp).y()
        
        #Draw the background        
        painter.fillRect(QtCore.QRect(0, y1, w, y2), QtGui.QColor('#DDD'))
        
        # Get cursor
        cursor = self.cursorForPosition(QtCore.QPoint(0,y1))
        
        # Init painter
        painter.setPen(QtGui.QColor('#222'))
        painter.setFont(self.font())
        
        #Repainting always starts at the first block in the viewport,
        #regardless of the event.rect().y(). Just to keep it simple
        while True:
            blockNumber=cursor.block().blockNumber()
            
            y=self.cursorRect(cursor).y()#+self.viewport().pos().y()+1 #Why +1?
            painter.drawText(0,y-offset,self.getLineNumberAreaWidth()-3,50,
                Qt.AlignRight,str(blockNumber+1))
            
            if y>y2:
                break #Reached end of the repaint area
            if not cursor.block().next().isValid():
                break #Reached end of the text
            
            cursor.movePosition(cursor.NextBlock)
        
        # Done
        painter.end()
    
    
    def _paintIndentationGuides(self, event):
        """ _paintIndentationGuides(event)
        
        Paint the indentation guides, using the indentation info calculated
        by the highlighter.
        
        """ 
        if not self.showIndentationGuides:
            return
        
        # Get doc and viewport
        doc = self.document()
        viewport = self.viewport()
        
        # Get which part to paint. Just do all to avoid glitches
        w = self.getLineNumberAreaWidth()
        y1, y2 = 0, self.height()
        #y1, y2 = event.rect().top()-10, event.rect().bottom()+10
        
        # Get cursor
        cursor = self.cursorForPosition(QtCore.QPoint(0,y1))
        
        # Get multiplication factor and indent width
        if self.spaceTabs:
            indentWidth = self.indentation
            factor = 1 
        else:
            indentWidth = self.tabWidth
            factor = indentWidth
        
        # Init painter
        painter = QtGui.QPainter()
        painter.begin(viewport)
        painter.setPen(QtGui.QColor('#DDF'))
        
        #Repainting always starts at the first block in the viewport,
        #regardless of the event.rect().y(). Just to keep it simple
        while True:
            blockNumber=cursor.block().blockNumber()
            y3=self.cursorRect(cursor).top()
            y4=self.cursorRect(cursor).bottom()            
            
            bd = cursor.block().userData()            
            if bd.indentation:
                for x in range(indentWidth, bd.indentation * factor, indentWidth):
                    w = self.fontMetrics().width('i'*x) + doc.documentMargin()
                    w += 1 # Put it more under the block

                    painter.drawLine(QtCore.QLine(w, y3, w, y4))
 
            if y4>y2:
                break #Reached end of the repaint area
            if not cursor.block().next().isValid():
                break #Reached end of the text
            
            cursor.movePosition(cursor.NextBlock)
        
        # Done
        painter.end()
    
    
    
    def _paintLongLineIndicator(self, event):
        """ _paintLongLineIndicator()
        
        Paint the long line indicator.
        
        """
        if not self.longLineIndicator:
            return
            
        # Get doc and viewport
        doc = self.document()
        viewport = self.viewport()

        # Get position of long line
        fm = self.fontMetrics()
        # width of ('i'*length) not length * (width of 'i') b/c of
        # font kerning and rounding
        x = fm.width('i' * self.longLineIndicator) + doc.documentMargin()
        x += 1 # Otherwise it will hide the cursor (at least on Windows)
        
        # Draw long line indicator
        painter = QtGui.QPainter()
        painter.begin(viewport)                
        painter.setPen(QtGui.QColor('#bbb'))
        painter.drawLine(QtCore.QLine(x, 0, x, self.height()) )
        painter.end()
    

    def keyPressEvent(self,event):
        #TODO: backspacing over tabs
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Escape and modifiers == Qt.NoModifier:
            self.autocompleteCancel()
            self._calltipLabel.hide()
            return
        
        #Tab key
        if key == Qt.Key_Tab:
            if modifiers == Qt.NoModifier:
                if self.autocompleteActive():
                    #Let the completer handle this one!
                    event.ignore()
                    return
                    
                elif self.textCursor().hasSelection(): #Tab pressed while some area was selected
                    self.indentSelection()
                    return
                elif self._cursorIsInLeadingWhitespace():
                    #If the cursor is in the leading whitespace, indent and move cursor to end of whitespace
                    cursor = self.textCursor()
                    self.indentBlock(cursor)
                    self.setTextCursor(cursor)
                    return
                    
                elif self.indentation:
                    #Insert space-tabs
                    cursor=self.textCursor()
                    cursor.insertText(' '*(self.indentation-((cursor.columnNumber() + self.indentation )%self.indentation)))
                    return
                #else: default behaviour, insert tab character
            else: #Some other modifiers + Tab: ignore
                return

        # If backspace is pressed in the leading whitespace, (except for at the first 
        # position of the line), and there is no selection
        # dedent that line and move cursor to end of whitespace
        if key == Qt.Key_Backspace and modifiers == Qt.NoModifier and \
                self._cursorIsInLeadingWhitespace() and not self.textCursor().atBlockStart() \
                and not self.textCursor().hasSelection():
            # Create a cursor, dedent the block and move screen cursor to the end of the whitespace
            cursor = self.textCursor()
            self.dedentBlock(cursor)
            self.setTextCursor(cursor)
            return
        
        # todo: Same for delete, I think not (what to do with the cursor?)
    
        
        # Home
        if key == Qt.Key_Home and modifiers in [Qt.NoModifier, Qt.ShiftModifier]:
            # Prepare
            cursor = self.textCursor()
            shiftDown = modifiers == Qt.ShiftModifier
            # Get leading whitespace
            text = cursor.block().text()            
            leadingWhitespace = text[:len(text)-len(text.lstrip())]
            # Get current position and move to start of whitespace
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.StartOfBlock, shiftDown)
            cursor.movePosition(cursor.Right, shiftDown, len(leadingWhitespace))
            # If we were alread there, move to start of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.StartOfBlock, shiftDown)
            # Done
            self.setTextCursor(cursor)
            event.accept()
            return                             
                
        
        # End
        if key == Qt.Key_End and modifiers in [Qt.NoModifier, Qt.ShiftModifier]:
            # Prepare
            cursor = self.textCursor()
            shiftDown = modifiers == Qt.ShiftModifier
            # Get current position and move to end of line
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.EndOfLine, shiftDown)
            # If alread at end of line, move to end of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.EndOfBlock, shiftDown)
            # Done
            self.setTextCursor(cursor)
            event.accept()
            return
        
        #Allowed keys that do not close the autocompleteList:
        # alphanumeric and _ ans shift
        # Backspace (until start of autocomplete word)
        if self.autocompleteActive() and \
            not event.text().isalnum() and event.text != '_' and \
            event.key() != Qt.Key_Shift and not (
            (key==Qt.Key_Backspace) and self.textCursor().position()>self._autocompleteStart):
            self.autocompleteCancel()
            
        #Apply the key
        QtGui.QPlainTextEdit.keyPressEvent(self,event)

        #Auto-indent
        if key in (Qt.Key_Enter,Qt.Key_Return):
            cursor=self.textCursor()
            previousBlock=cursor.block().previous()
            if previousBlock.isValid():
                line=previousBlock.text()
                indent=line[:len(line)-len(line.lstrip())]
                if line.endswith(':'): #TODO: (multi-line) strings, comments
                    #TODO: check correct identation (no mixed space/tabs)
                    if self.spaceTabs:
                        indent+=' '*self.tabWidth
                    else:
                        indent+='\t'
                cursor.insertText(indent)
                
        if self.autocompleteActive():
            #While we type, the start of the autocompletion may move due to line
            #wrapping, so reposition after every key stroke
            self._positionAutocompleter()
            self._updateAutocompleterPrefix()



if __name__=='__main__':
    app=QtGui.QApplication([])
    class TestEditor(CodeEditor):
        def keyPressEvent(self,event):
            key = event.key()
            if key == Qt.Key_F1:
                self.autocompleteShow()
                return
            elif key == Qt.Key_F2:
                self.autocompleteCancel()
                return
            elif key == Qt.Key_Backtab: #Shift + Tab
                self.dedentSelection()
           
            CodeEditor.keyPressEvent(self,event)
            self.calltipShow(0, 'test(foo, bar)')
        
    e=TestEditor()
    e.showLineNumbers = True
    e.showWhitespace = True
    e.show()
    s=QtGui.QSplitter()
    s.addWidget(e)
    s.addWidget(QtGui.QLabel('test'))
    s.show()
    app.exec_()
