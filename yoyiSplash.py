from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout,QWidget,QLabel,QSplashScreen
from PyQt5.QtGui import QPixmap,QFont
import yoyirs_rc

class YoyiSplashScreen(QSplashScreen):
    def __init__(self,mode="common"):
        super(YoyiSplashScreen, self).__init__()
        self.setPixmap(QPixmap(":/img/resources/loading.png"))
        #self.setWindowFlag(Qt.WindowStaysOnTopHint,True)
        tempFont = QFont()
        tempFont.setPointSize(15)
        tempFont.setBold(True)
        self.setFont(tempFont)
        #.scaledToWidth(800))
        #self.setPixmap(QPixmap('./images/cgwxBlack.png').scaledToWidth(600))

    def setInfo(self,message):
        self.showMessage(message, Qt.AlignHCenter | Qt.AlignBottom, Qt.white)

    def mousePressEvent(self, event):
        pass