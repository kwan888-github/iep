from PyQt4 import QtCore, QtGui,uic
import iep
import os
import sys
import ssdf
import fnmatch
import iepcore.menu
from iep import translate
import subprocess

tool_name = "Project manager"
tool_summary = "Manage project directories."

# todo: desired changes:
# - Search using separate search tool
# - Popup menu with usefull actions

# Load classes for configuration dialog and tabs
ProjectsCfgDlg, ProjectsCfgDlgBase = uic.loadUiType(iep.iepDir + "/gui/projects_dialog.ui")

      
class ProjectsConfigDialog(ProjectsCfgDlg, ProjectsCfgDlgBase):
    def __init__(self, projectManager, *args, **kwds):
        ProjectsCfgDlgBase.__init__(self, *args, **kwds)
        self.setupUi(self)
        self._projectManager = projectManager
        self._projectsModel = projectManager.projectsModel
        self._activeProject = None
        self.lstProjects.setModel(self._projectsModel)
        
        self.lstProjects.selectionModel().currentChanged.connect(self.onProjectChanged)
        
        # Update description label when project name is changed
        self.lstProjects.model().dataChanged.connect(
            lambda i1,i2: self.txtDescription.setText(self._activeProject.name))
        
        self.txtDescription.textEdited.connect(self.onDescriptionChanged)
        self.chkAddToPath.stateChanged.connect(self.onAddToPathChanged)
        
    def onProjectChanged(self,current,previous):
        if not current.isValid():
            self.projectChanged(-1)
        else:
            self.projectChanged(current.row())
    def onDescriptionChanged(self):
        """Handler for when the description lineEdit is changed"""
        if not self.lstProjects.currentIndex().isValid():
            return
        
        projectIndex=self.lstProjects.currentIndex()
        self._projectsModel.setData(
            projectIndex,self.txtDescription.text(),QtCore.Qt.EditRole)
    
    def onAddToPathChanged(self):
        """Handler for when the 'Add project path to Python path' checkmark
        is changed"""
        if self._activeProject is not None:
            self._activeProject.addToPath = self.chkAddToPath.isChecked()
        
    def projectChanged(self, projectIndex):
        """Handler for when the project is changed
        projectIndex: -1 or None for no project or 0..len(projects)
        """
        #Sync projectmanager project selection
        self._projectManager.projectChanged(projectIndex)
        
        valid = not (projectIndex==-1 or projectIndex is None)
        
        self.txtDescription.setEnabled(valid)
        self.chkAddToPath.setEnabled(valid)
        
        if not valid:
            self._activeProject = None
            self.txtDescription.setText('')
            self.txtPath.setText('')
            self.chkAddToPath.setChecked(False)
            return
        
        # If projectChanged is called from e.g. removeProject, we need to
        # update the list selection to match the newly selected project
        self.lstProjects.selectionModel().setCurrentIndex(
                self._projectsModel.index(projectIndex), 
                QtGui.QItemSelectionModel.ClearAndSelect)
                
        project=self._projectsModel.projectFromRow(projectIndex)
        self._activeProject = project
        
        # Update the info fields to the right of the dialog
        self.txtDescription.setText(project.name)
        self.txtPath.setText(project.path)
        self.chkAddToPath.setChecked(project.addToPath)
     
        
    def addProject(self):
        
        dir=QtGui.QFileDialog.getExistingDirectory(None,'Select project directory')
        if dir=='':
            return #Cancel was pressed
        _,projectName=os.path.split(dir)
        index=self._projectsModel.add(Project(projectName,dir))
        self.projectChanged(index)
    def removeProject(self):
        if not self.lstProjects.currentIndex().isValid():
            return
        
        projectIndex=self.lstProjects.currentIndex()
        projectRow=projectIndex.row()
        project=self._projectsModel.projectFromIndex(projectIndex)
  
        confirm=QtGui.QMessageBox(QtGui.QMessageBox.Warning,
            "Remove project?",
            "Remove project '%s'?" % project.name)
            
        confirm.addButton("Remove",QtGui.QMessageBox.DestructiveRole)
        cancel=confirm.addButton("Cancel",QtGui.QMessageBox.RejectRole)
        confirm.setDefaultButton(cancel)
        confirm.setEscapeButton(cancel)
        
        confirm.setInformativeText("The project contents will not be removed.")
        confirm.exec_()
        
        if confirm.result()!=0: #Cancel button pressed
            return
        
        
        self._projectsModel.remove(project)

        #Select another project (try the one before)
        if projectRow>0:
            projectRow-=1
            
        if self._projectsModel.projectFromRow(projectRow) is None:
            #If we deleted the last project
            projectRow=-1

        self.projectChanged(projectRow)
        
    

class Project(ssdf.Struct):
    def __init__(self,name,path):
        self.name=name
        self.path=path
        self.addToPath=False
    def __repr__(self):
        return "Project %s at %s" % (self.name,self.path)
    

class ProjectsModel(QtCore.QAbstractListModel):
    def __init__(self,config):
        QtCore.QAbstractListModel.__init__(self)
        self.config=config
    def rowCount(self,parent):
        return len(self.config.projects)
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.projectFromIndex(index).name
        elif role == QtCore.Qt.UserRole:
            return self.projectFromIndex(index)
    
    def setData(self,index,value,role):
        """Change the name of a project"""
        if not index.isValid():
            return False
        elif role == QtCore.Qt.EditRole:
            self.projectFromIndex(index).name=value
            self.dataChanged.emit(index,index)
            return True
        return False
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction
    def flags(self,index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | \
                QtCore.Qt.ItemIsDropEnabled
                
    def add(self,project):
        self.config.projects.append(project)
        self.reset()
        return self.config.projects.index(project)
    def remove(self,project):
        self.config.projects.remove(project)
        self.reset()
    def projectFromIndex(self,index):
        return self.config.projects[index.row()]
    def projectFromRow(self,row):
        if row<0 or row>=len(self.config.projects):
            return None
        return self.config.projects[row]
    def swapRows(self,row1,row2):
        if row1==row2:
            return
            
        #Ensure row1<row2
        if row2>row1:
            row1,row2=row2,row1
            
        self.beginMoveRows(QtCore.QModelIndex(),row1,row1,QtCore.QModelIndex(),row2)
        project1=self.config.projects[row1]
        self.config.projects[row1]=self.config.projects[row2]
        self.config.projects[row2]=project1
        self.endMoveRows()






class DirSortAndFilter(QtGui.QSortFilterProxyModel):
    """
    Proxy model to filter a directory tree based on filename patterns,
    sort directories before files and sort dirs/files on name, case-insensitive 
    """
    def __init__(self):
        QtGui.QSortFilterProxyModel.__init__(self)
        self.filter=''
        
        # Specify sorting behaviour when comparing of two dirs or two files
        # Sorting dirs before files is none in the lessThan function 
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.sort(0)
        self.setDynamicSortFilter(True)
    
    def lessThan(self,left,right):
        if self.sourceModel().isDir(left) == self.sourceModel().isDir(right):
            # Comparing two dirs or two files: default behaviour
            return QtGui.QSortFilterProxyModel.lessThan(self,left,right)
                
        # Comparing a dir and a file
        return self.sourceModel().isDir(left)           
        
    def filterAcceptsRow(self,sourceRow,sourceParent):
        #Overridden method to determine wether a row should be
        #shown or not. Check wether the item matches the filter
        
        #Get the fileinfo of the item
        item=self.sourceModel().index(sourceRow,0,sourceParent)
        fileInfo=self.sourceModel().fileInfo(item)
        fileName=fileInfo.fileName()
        
        # Explicitlty hide files/dirs starting with a dot.
        if fileName.startswith('.'):
            return False
        
        #Show everything that's not a file
        if not fileInfo.isFile():
            return True
        
        #'default' is the return value when no filter matches. A 'hide' filter
        #(i.e. starting with '!') sets the default to 'show', a 'show' filter
        #(i.e. not starting with '!') sets the default to 'hide'
        
        default=True #Return True if there are no filters
        
        #Get the current filter spec and split it into separate filters
        filters=self.filter.replace(',',' ').split()          
        for filter in filters:
            #Process filters in order
            if filter.startswith('!'):
                #If the filename matches a filter starting with !, hide it
                if fnmatch.fnmatch(fileName,filter[1:]):
                    return False
                default=True
            else:
                #If the file name matches a filter not starting with!, show it
                if fnmatch.fnmatch(fileName,filter):
                    return True
                default=False
                    
        #No filter matched, return True
        return default
        
    def setFilter(self,filter):
        """Set and apply the filter"""
        self.filter=filter
        self.invalidateFilter()
        


class IconProviderWindows(QtGui.QFileIconProvider):
    """ IconProvider that will give icons for files without any overlays.
    (Because the overlays will be wrong)
    It does this by creating dummy files with a corresponding extension and
    obtaining the icon for that file.
    """
    def icon(self, type_or_info):
        class MyFileInfo(QtCore.QFileInfo):
            def __getattr__(self,attr):
                print (attr)
                return getattr(QtCore.QFileInfo,attr)
        if isinstance(type_or_info, QtCore.QFileInfo):
            if type_or_info.isDir():
                # Use folder icon
                icon = QtGui.QFileIconProvider.icon(self, self.Folder)
                # Add overlay?
                path = type_or_info.absoluteFilePath()
                if os.path.isdir(os.path.join(path, '.hg')):
                    icon = self._addOverlays(icon, iep.icons.overlay_hg)
                elif os.path.isdir(os.path.join(path, '.svn')):
                    icon = self._addOverlays(icon, iep.icons.overlay_svn)
                # Done
                return icon
            else:
                # Get extension
                root, ext = os.path.splitext(type_or_info.fileName())
                # Create dummy file in iep user dir
                dir = os.path.join(iep.appDataDir, 'dummyFiles')
                path = os.path.join(dir, 'dummy' + ext)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                f = open(path, 'wb')
                f.close()
                # Use that file
                type_or_info = QtCore.QFileInfo(path)
        
        # Call base method
        return QtGui.QFileIconProvider.icon(self, type_or_info)
    
    
    def _addOverlays(self, icon, *overlays):
        
        # Get pixmap
        pm0 = icon.pixmap(16,16)
        
        # Create painter
        painter = QtGui.QPainter()
        painter.begin(pm0)
        
        for overlay in overlays:
            pm1 = overlay.pixmap(16,16)
            painter.drawPixmap(0,0, pm1)
        
        # Finish
        painter.end()
        
        # Done (return resulting icon)
        return QtGui.QIcon(pm0)


class IepProjectManager(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self.config = iep.config.tools[toolId]
        if not hasattr(self.config, 'projects'):
            self.config.projects=[]
        if not hasattr(self.config,'activeproject'):
            self.config.activeproject=-1
        if not hasattr(self.config,'filter'):
            self.config.filter='!*.pyc'
        if not hasattr(self.config,'listdisclosed'):
            self.config.listdisclosed=True
        
        #Init projects model
        self.projectsModel=ProjectsModel(self.config)

        #Init dir model and filtered dir model
        self.dirModel=QtGui.QFileSystemModel()
        #TODO: using the default IconProvider bugs on mac, restoring window state fails
        
        self.dirModel.setIconProvider(IconProviderWindows())

        #TODO: self.dirModel.setSorting(QtCore.QDir.DirsFirst)
        # todo: huh? QFileSystemModel.setSorting Does not exist
        self.filteredDirModel=DirSortAndFilter()
        self.filteredDirModel.setSourceModel(self.dirModel)
                
        #Init widgets and layout
        self.buttonLayout=QtGui.QVBoxLayout()
        self.configButton = QtGui.QPushButton(self)
        self.configButton.setIcon(iep.icons.wrench)
        self.configButton.setIconSize(QtCore.QSize(16,16))

        self.buttonLayout.addWidget(self.configButton,0)
        self.buttonLayout.addStretch(1)

        self.projectsCombo=QtGui.QComboBox()
        self.projectsCombo.setModel(self.projectsModel)
        
        self.hLayout=QtGui.QHBoxLayout()
        self.hLayout.addWidget(self.projectsCombo,1)
        self.hLayout.addLayout(self.buttonLayout,0)
  
        self.dirList=QtGui.QTreeView()
        
        # The lessThan function in DirSortAndFilter ensures dirs are before files
        self.dirList.sortByColumn(0)
        self.filterCombo=QtGui.QComboBox()

        self.layout=QtGui.QVBoxLayout()
        self.layout.addLayout(self.hLayout)
        self.layout.addWidget(self.dirList,10)
        self.layout.addWidget(self.filterCombo)
        
        self.setLayout(self.layout)
        
        #Load projects in the list
        self.projectsCombo.show()
        
        #Load default filters
        self.filterCombo.setEditable(True)
        self.filterCombo.setCompleter(None)
        self.filterCombo.setInsertPolicy(self.filterCombo.NoInsert)
        for pattern in ['*', '!*.pyc','*.py *.pyw *.pyx *.pxd', '*.h *.c *.cpp']:
            self.filterCombo.addItem(pattern)
        self.filterCombo.editTextChanged.connect(self.filterChanged)
        
        # Set file pattern line edit (in combobox)
        self.filterPattern = self.filterCombo.lineEdit()
        self.filterPattern.setText(self.config.filter)
        self.filterPattern.setToolTip('File filter pattern')        

        #Connect signals
        self.projectsCombo.currentIndexChanged.connect(self.comboChangedEvent)
        self.dirList.doubleClicked.connect(self.itemDoubleClicked)
        self.configButton.clicked.connect(self.showConfigDialog)

        #Apply previous selected project
        self.activeProject = None
        self.projectChanged(self.config.activeproject)
        
        #Attach the context menu
        self.dirList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.dirList.customContextMenuRequested.connect(self.contextMenuTriggered)  
        

    ## Methods
    def showConfigDialog(self):
        configDialog = ProjectsConfigDialog(self)
        index = self.projectsModel.index(self.projectsCombo.currentIndex())
        if index.isValid():
            configDialog.lstProjects.selectionModel().setCurrentIndex(index,
                    QtGui.QItemSelectionModel.ClearAndSelect)
                    
        configDialog.exec()
        
    def getAddToPythonPath(self):
        """
        Returns the path to be added to the Python path when starting a shell
        If a project is selected, which has the addToPath checkbox selected,
        returns the path of the project. Otherwise, returns None
        """
        if self.activeProject and self.activeProject.addToPath:
            return self.activeProject.path
        else:
            return None
    
    def getDefaultSavePath(self):
        """
        Returns the path to be used as default when saving a new file in iep
        
        Returns '' if the path cannot be determined (e.g. no current project)
        """
        if not self.activeProject:
            return ''
            
        # Get the index of the selected item in the dir list
        idx = self.dirList.selectionModel().currentIndex()
        if not idx.isValid():
            return self.activeProject.path
        
        # Transform to the source model
        idx = self.dirList.model().mapToSource(idx)
        if not idx.isValid():
            return self.activeProject.path


        if self.dirModel.isDir(idx):
            # If it is a dir, return its path
            return self.dirModel.filePath(idx)
        else:
            # If it is not a dir, return the path of its parent
            idx = self.dirModel.parent(idx)
            if idx.isValid():
                return self.dirModel.filePath(idx)
            else:
                return self.activeProject.path
                
    ## Context menu handler
        
    def contextMenuTriggered(self, p):
        """ Called when context menu is clicked """
        idx = self.dirList.indexAt(p)
        if not idx.isValid():
            return
        idx = self.dirList.model().mapToSource(idx)
        if not idx.isValid():
            return
        path = self.dirModel.filePath(idx)
        
        PopupMenu(path, self).exec_(self.dirList.mapToGlobal(p))
        
        
        
    ## Project changed handlers
    def comboChangedEvent(self,newIndex):
        self.projectChanged(newIndex)
            
        
    def projectChanged(self,projectIndex):
        """Handler for when the project is changed
        projectIndex: -1 or None for no project or 0..len(projects)
        """
        if projectIndex==-1 or projectIndex is None:
            #This happens when the model is reset
            self.dirList.setModel(None)
            self.activeProject = None
            return
        
        #Remember the previous selected project
        self.config.activeproject=projectIndex
    
        #Set the combobox index
        self.projectsCombo.setCurrentIndex(projectIndex)
    
        #Sync the dirList
        project=self.projectsModel.projectFromRow(projectIndex)
        if project is None:
            return #Invalid project index
        self.activeProject = project
        
        path=project.path
    
        self.dirList.setModel(self.filteredDirModel)
        self.dirList.setColumnHidden(1,True)
        self.dirList.setColumnHidden(2,True)
        self.dirList.setColumnHidden(3,True)
        
        self.dirModel.setRootPath(path)
        self.dirList.setRootIndex(self.filteredDirModel.mapFromSource(self.dirModel.index(path)))
        
        #Clear the selected item (which is still from the previous project)
        self.dirList.selectionModel().clear() 
        
        
    
    def filterChanged(self):
        """Handler for when the filter is changed"""
        filter=self.filterCombo.lineEdit().text()
        self.config.filter=filter
        self.filteredDirModel.setFilter(filter)
        
   
    def itemDoubleClicked(self,item):
        """Handler for if an item is double-clicked"""
        info=self.dirModel.fileInfo(self.filteredDirModel.mapToSource(item))
        if info.isFile():
            # todo: maybe open the file, read some bytes and see if there
            # is an encoding tag or if it correctly decodes with utf-8.
            # we could even do that in the filter, and simply not list binary
            # files.
            
            # The user should be able to read in any reabable file. We can
            # never specify all extension of readable files beforehand. So
            # better specify reading the files of which we know to be binary.
            #if info.suffix() in ['py','c','pyw','pyx','pxd','h','cpp','hpp']:
            if info.suffix() not in ['pyc','pyo','png','jpg','ico']:
                iep.editors.loadFile(info.absoluteFilePath())
                
class PopupMenu(iepcore.menu.Menu):
    def __init__(self, path, parent):
        iepcore.menu.Menu.__init__(self, parent, " ")
        self._path = path
    def build(self):
        #TODO: implement 'open outside iep' on linux
        
        if sys.platform == 'darwin':
            self.addItem(translate("menu", "Open outside iep"), self._openOutsideMac)
            self.addItem(translate("menu", "Reveal in Finder"), self._showInFinder)
        if sys.platform.startswith('win'):
            self.addItem(translate("menu", "Open outside iep"), self._openOutsideWin)
        self.addItem(translate("menu", "Copy path"), self._copyPath)
            
    def _openOutsideMac(self):
        subprocess.call(('open', self._path))
    def _showInFinder(self):
        subprocess.call(('open', '-R', self._path))
    def _openOutsideWin(self):
        subprocess.call(('start', self._path), shell=True)
    def _copyPath(self):
        QtGui.qApp.clipboard().setText(self._path)
        
