import os
import os.path as osp

from appConfig import WEB_PROJECT_STATUS_DICT,WebDrawQueryType,DRAW_MODE_DICT

from ui.webSampleProjectListDialog import Ui_Dialog


from PyQt5.QtCore import Qt,QStringListModel,QPoint
from PyQt5.QtWidgets import QHeaderView,QTableWidgetItem,QTableView,QFrame, QWidget,QMainWindow,QAbstractItemView,QDialog
from PyQt5.QtGui import QIcon,QCursor

from qfluentwidgets import (RoundMenu, Action,MessageBox,MenuAnimationType,Dialog,PrimaryPushButton)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.yoyiFile import checkChildDirI,deleteDir
from yoyiUtils.yoyiSamRequest import rsdmWeber


class WebSampleProjectListDialogClass(Ui_Dialog,QDialog):
    def __init__(self,userId,queryType:WebDrawQueryType,parent=None):
        super().__init__(parent=parent)
        self.parentWindow = parent
        self.userId = userId
        self.queryType = queryType
        self.selectedProject = None
        self.setupUi(self)
        self.setObjectName("Dialog_ProjectList")
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.rsdmReq = rsdmWeber()
        self.totalPage = None
        self.taskIdList = None
        self.resTaskName = None
        self.resTaskId = None
        self.resTaskTypeId = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.setWindowTitle(f"{self.queryType.value} 项目查询窗口")

        #search page
        self.pageSizeComboBox.addItem(text="10/条页",userData=10)
        self.pageSizeComboBox.addItem(text="20/条页",userData=20)
        self.pageSizeComboBox.addItem(text="50/条页",userData=50)
        self.pageSizeComboBox.setCurrentIndex(0)

        self.statusFilterCb.addItem(text="ALL",userData=None)
        self.statusFilterCb.addItem(text="未开始",userData='501')
        self.statusFilterCb.addItem(text="正在进行",userData='502')
        self.statusFilterCb.addItem(text="已完成",userData='503')
        self.statusFilterCb.setCurrentIndex(0)

        self.searchTb.setIcon(FIF.SEARCH)

        self.projectTableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.projectTableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.projectTableWidget.setWordWrap(True)
        self.projectTableWidget.setColumnCount(5)
        self.projectTableWidget.setHorizontalHeaderLabels(['任务名称','任务类型','创建人','创建时间','状态','勾画模式'])
        self.projectTableWidget.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.projectTableWidget.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        self.projectTableWidget.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        self.projectTableWidget.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        self.projectTableWidget.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
        self.projectTableWidget.doubleClicked.connect(self.on_custom_menu_requested)

        self.refreshProject(1,10)
    
    def connectFunc(self):
        self.statusFilterCb.currentIndexChanged.connect(self.commonChangedFunc)
        self.searchTb.clicked.connect(self.commonChangedFunc)
        self.lastPb.clicked.connect(self.lastPbClicked)
        self.nextPb.clicked.connect(self.nextPbClicked)
        self.jumpPb.clicked.connect(self.jumpPbClicked)
        self.pageSizeComboBox.currentIndexChanged.connect(self.commonChangedFunc)
        
    def refreshProject(self,pageNo,pageSize,taskName=None,taskStatus=None):
        print(taskStatus)
        self.taskIdList = []
        self.taskTypeIdList = []

        reqStatus,reqDict = self.rsdmReq.queryDesktopList(
            userId=self.userId,
            queryType=self.queryType,
            pageNo=pageNo,
            pageSize=pageSize,
            taskName=taskName,
            taskStatus=taskStatus)

        if reqStatus:
            contents = reqDict['contents']
            total = reqDict['total']
            pageSize = reqDict['pageSize']
            currentPage = reqDict['currentPage']
            self.totalPage = (total//pageSize)+1

            # 表外设置
            self.projectsTotalLabel.setText(f"{(currentPage-1)*pageSize+1}-{currentPage*pageSize if currentPage*pageSize<total else total} 共{total}条, 共{self.totalPage}页, 当前第{currentPage}页 ")
            self.pageIndexSpinBox.setValue(currentPage)

            # 表内设置
            self.projectTableWidget.setRowCount(0)
            self.projectTableWidget.setRowCount(pageSize)
            for index,tabelContent in enumerate(contents) :
                self.taskIdList.append(tabelContent['id'])
                self.taskTypeIdList.append(tabelContent['taskTypeId'])
                self.projectTableWidget.setItem(index,0,QTableWidgetItem(tabelContent['taskName']))
                self.projectTableWidget.setItem(index,1,QTableWidgetItem(tabelContent['taskStatus_dictText']))
                self.projectTableWidget.setItem(index,2,QTableWidgetItem(tabelContent['createBy']))
                self.projectTableWidget.setItem(index,3,QTableWidgetItem(tabelContent['createTime']))
                self.projectTableWidget.setItem(index,4,QTableWidgetItem(WEB_PROJECT_STATUS_DICT[tabelContent['taskStatus']] if tabelContent['taskStatus'] in WEB_PROJECT_STATUS_DICT.keys() else tabelContent['taskStatus']))    
        else:
            MessageBox('错误', reqDict, self).exec_()

    def on_custom_menu_requested(self,pos):
        items = self.projectTableWidget.selectedItems()
        if items:
            currentItem = items[0]
            currentProjectName = self.projectTableWidget.item(currentItem.row(),0).text()
            cusMenu = RoundMenu(parent=self)
            cusMenu.setItemHeight(50)
            intoSelected = Action(FIF.PLAY,f"进入{currentProjectName}")
            intoSelected.triggered.connect(lambda : self.intoSelectedTriggered(currentItem.row()))
            cusMenu.addAction(intoSelected)
            curPos : QPoint = QCursor.pos()
            cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def lastPbClicked(self):
        currentPage = self.pageIndexSpinBox.value() - 1
        if currentPage < 1:
            currentPage = 1
        currentPageSize = self.pageSizeComboBox.currentData()
        taskName = self.projectNameFilterLE.text() if self.projectNameFilterLE.text() != "" else None
        taskStatus = self.statusFilterCb.currentData()
        self.refreshProject(currentPage,currentPageSize,taskName,taskStatus)
    
    def nextPbClicked(self):
        currentPage = self.pageIndexSpinBox.value() + 1
        if currentPage > self.totalPage:
            currentPage = self.totalPage
        currentPageSize = self.pageSizeComboBox.currentData()
        taskName = self.projectNameFilterLE.text() if self.projectNameFilterLE.text() != "" else None
        taskStatus = self.statusFilterCb.currentData()
        self.refreshProject(currentPage,currentPageSize,taskName,taskStatus)
    
    def jumpPbClicked(self):
        currentPage = self.pageIndexSpinBox.value()
        if currentPage < 1:
            currentPage = 1
        elif currentPage > self.totalPage:
            currentPage = self.totalPage
        currentPageSize = self.pageSizeComboBox.currentData()
        taskName = self.projectNameFilterLE.text() if self.projectNameFilterLE.text() != "" else None
        taskStatus = self.statusFilterCb.currentData()
        self.refreshProject(currentPage,currentPageSize,taskName,taskStatus)
    
    def commonChangedFunc(self):
        currentPage = 1
        currentPageSize = self.pageSizeComboBox.currentData()
        taskName = self.projectNameFilterLE.text() if self.projectNameFilterLE.text() != "" else None
        taskStatus = self.statusFilterCb.currentData()
        self.refreshProject(currentPage,currentPageSize,taskName,taskStatus)
    
    def intoSelectedTriggered(self,row):
        self.resTaskName = self.projectTableWidget.item(row,0).text()
        self.resTaskId = self.taskIdList[row]
        self.resTaskTypeId = self.taskTypeIdList[row]
        self.close()


