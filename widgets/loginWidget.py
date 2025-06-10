import os
import os.path as osp
from ui.LoginWindowNew import Ui_LoginForm
from qgis.core import QgsProject
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget,QDialog,QLineEdit,QMessageBox
from qfluentwidgets import MessageBox
from yoyiUtils.yoyiFile import readYamlToDict,saveYamlForDict
from yoyiUtils.yoyiSamRequest import rsdmWeber
from appConfig import yoyiSetting,HomeUrlDict

PROJECT = QgsProject.instance()

class LoginWidgetClass(Ui_LoginForm,QDialog):
    def __init__(self,parent=None):
        super(LoginWidgetClass, self).__init__(parent)
        self.parentWindow = parent
        self.setting = yoyiSetting()
        self.setupUi(self)
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.loginStatus = -1 # -1失败 0游客 1用户
        self.user = None
        self.pswd = None
        self.resultDict = None
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.passwdLE.setEchoMode(QLineEdit.Password)

        preUser = self.setting.configSettingReader.value('user',type=str)
        prePswd = self.setting.configSettingReader.value('pswd', type=str)

        netMode = yoyiSetting().configSettingReader.value('netMode',type=int)
        serverHost = HomeUrlDict[netMode]

        self.hostNameLE.setText(serverHost)

        if preUser != "None" and prePswd != "None":
            self.userLE.setText(preUser)
            self.passwdLE.setText(prePswd)
        
        language = self.setting.configSettingReader.value('appLanguage',type=str)
        if language == "Ch":
            self.ChRb.setChecked(True)
        else:
            self.EnRb.setChecked(True)
        self.changeUILanguage(language)
        
    def changeUILanguage(self,language):
        if language == "Ch":
            self.hostLabel.setText("主机地址")
            self.userNameLabel.setText("账户名")
            self.passwordLabel.setText("密码")
            self.showPswdChBox.setText("显示密码")
            self.rememberMeChBox.setText("记住密码")
            self.loginPB.setText("登录")
        else:
            self.hostLabel.setText("Host")
            self.userNameLabel.setText("Username")
            self.passwordLabel.setText("Password")
            self.showPswdChBox.setText("Show Password")
            self.rememberMeChBox.setText("Remember Password")
            self.loginPB.setText("Login")

    def connectFunc(self):
        # 变动ip时候 触发更新ini的时间
        #self.hostNameLE.textChanged.connect(self.hostNameLETextChanged)
        #
        self.showPswdChBox.clicked.connect(self.changePswdLineStatus)
        self.loginPB.clicked.connect(self.loginClicked)
        #self.visitorLb.clicked.connect(self.visitorClicked)
        self.ChRb.clicked.connect(lambda: self.changeUILanguage("Ch"))
        self.EnRb.clicked.connect(lambda: self.changeUILanguage("En"))

    def hostNameLETextChanged(self):
        self.setting.changeSetting("serverHost",self.hostNameLE.text())
    

    def changePswdLineStatus(self):
        if self.showPswdChBox.isChecked():
            self.passwdLE.setEchoMode(QLineEdit.Normal)
        else:
            self.passwdLE.setEchoMode(QLineEdit.Password)

    def loginClicked(self):
        user = self.userLE.text()
        pswd = self.passwdLE.text()
        print(pswd)
        pgw = rsdmWeber()
        checkInfo,resultDict = pgw.login(user,pswd)
        if checkInfo:
            self.user = user
            self.pswd = pswd
            self.resultDict = resultDict
            self.loginStatus = 1
            if self.rememberMeChBox.isChecked():
                self.setting.changeSetting("user",self.user)
                self.setting.changeSetting("pswd", self.pswd)
            MessageBox('欢迎', f'登录成功，欢迎{user}', self).exec_()
            self.close()
        else:
            MessageBox('警告', f"登录失败。详细原因：\n"
                                           f"{resultDict}", self).exec_()
        
    
    def visitorClicked(self):
        self.loginStatus = 0
        self.close()
