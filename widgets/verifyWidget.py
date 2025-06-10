

from ui.VerifyDialog import Ui_Dialog
from PyQt5.QtWidgets import QDialog,QLineEdit,QMessageBox
from yoyiUtils.yoyiLs import Verfication
from qfluentwidgets import MessageBox

class VerifyWidgetClass(Ui_Dialog,QDialog):
    def __init__(self,parent=None):
        super(VerifyWidgetClass, self).__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.isSuccess = False

        self.verify = Verfication()

        self.question = self.verify.generateQuestion()

        self.questionLE.setText(self.question)
    
    def connectFunc(self):
        self.okPb.clicked.connect(self.okPbClicked)
    
    def okPbClicked(self):
        
        answer = self.answerLE.text()

        success = self.verify.checkVerf(answer)

        if success:
            MessageBox('欢迎(Welcome)', f'欢迎使用使用本软件！（Welcome ！）', self).exec_()
            self.verify.writeVerfFile(answer)
            self.isSuccess = True
            self.close()
        else:
            MessageBox('警告(Warning)', f'序列码错误（the serial number is wrong）', self).exec_()

