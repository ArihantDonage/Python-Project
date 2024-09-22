# Import necessary PyQt5 modules for GUI development
from PyQt5 import Qt, QtCore, QtGui, QtSql, QtWidgets, uic
import sys
import psutil  # Library to retrieve system and process information
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from collections import deque  # For working with lists efficiently
import matplotlib.style as style

# Use 'ggplot' style for plots
style.use('ggplot')

# Global variables for storing network statistics
oldSendBytes = 0
oldRecvBytes = 0
plotSend = []
plotRecv = []
itemQW = None  # This variable stores the selected item from listWidget

# Define main Widget class which extends QtWidgets.QWidget
class Widget(QtWidgets.QWidget):
    def __init__(self):
        # Initialize QWidget
        QtWidgets.QWidget.__init__(self)
        # Load the UI design from a file
        self.ui = uic.loadUi('ui/main.ui', self)

        # Create instances of child windows (process info and process statistics)
        self.showProcessInfoWidget = processInfoWidget()
        self.showProcessInfoWidget.setParent(self, QtCore.Qt.Sheet)

        self.showProcessStatistick = processStatistickWidget()
        self.showProcessStatistick.setParent(self, QtCore.Qt.Sheet)

        # Set up context menu for listWidget_3 and connect right-click signal to a function
        self.listWidget_3.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget_3.customContextMenuRequested[QtCore.QPoint].connect(self.listWidget_3ItemRightClicked)

        # Timer to refresh tableWidget and network statistics
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)  # Interval of 2 seconds
        self.timer.timeout.connect(self.ontimer)
        self.timer.timeout.connect(self.networkStatisticksProcessForlistWidget_3)
        self.timer.start()

        # Timer for graph updates
        self.timefForGraph = QtCore.QTimer()
        self.timefForGraph.setInterval(1000)  # Interval of 1 second
        self.timefForGraph.timeout.connect(self.graph)

        # Add widgets to a splitter for better layout
        self.splitterH = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitterH.addWidget(self.stackedWidget)
        self.splitterH.addWidget(self.tableWidget)
        self.verticalLayout_3.addWidget(self.splitterH)

        # Display list of network interfaces
        self.interfacesListSet()
        self.networkStatistickProcess()

        # Connect interface listWidget items to functions for click events
        self.listWidget.itemClicked.connect(lambda item: self.listWidgetItemOnClick(item))
        self.listWidget_3.itemClicked.connect(lambda item: self.findItemIntableWidget(listWidgetItem=item))
        self.listWidget.itemClicked.connect(lambda item: self.ontimerGraphTimer(listWidgetItem=item))

        # Setup graph for byte send/receive data
        self.figureSend = plt.figure()
        self.canvasSend = FigureCanvas(self.figureSend)
        self.axSend = self.figureSend.add_subplot(111)
        self.gridLayout.addWidget(self.canvasSend)

    # Display context menu when right-clicking on items in listWidget_3
    def listWidget_3ItemRightClicked(self, QPos):
        self.listMenu = QtWidgets.QMenu()
        # Add actions to the context menu
        menu_item = self.listMenu.addAction("Show process info")
        menu_item2 = self.listMenu.addAction("Show process statistick")
        # Connect menu actions to their respective functions
        menu_item.triggered.connect(self.menuItemClicked)
        menu_item2.triggered.connect(self.menuItem2Clicked)

        # Show the context menu
        parentPosition = self.listWidget_3.mapToGlobal(QtCore.QPoint(0, 0))
        self.listMenu.move(parentPosition + QPos)
        self.listMenu.show()

    # Handle 'Show process statistick' menu action
    def menuItem2Clicked(self):
        try:
            currentItemName = str(self.listWidget_3.currentItem().text())  # Get selected item name
            ps = int(currentItemName.split(" Pid:")[1])  # Extract process ID (PID)
            process = psutil.Process(ps)  # Get process info
            self.showProcessStatistick.ps = ps  # Set process ID in stats window
            self.showProcessStatistick.process = process  # Set process in stats window
            self.showProcessStatistick.timer.start()  # Start timer for process stats updates
            self.showProcessStatistick.show()  # Show the stats window
        except:
            pass

    # Handle 'Show process info' menu action
    def menuItemClicked(self):
        currentItemName = str(self.listWidget_3.currentItem().text())  # Get selected item name
        ps = int(currentItemName.split(" Pid:")[1])  # Extract PID
        try:
            process = psutil.Process(ps)  # Get process info
        except:
            return

        # Fill the process info widget with details about the process
        self.showProcessInfoWidget.label.setText(currentItemName)
        try:
            self.showProcessInfoWidget.label_9.setText(str(process.cwd()))  # Get current working directory
        except:
            self.showProcessInfoWidget.label_9.setText("None")
        try:
            status = str(process.status())  # Get process status
            if status == "running":
                self.showProcessInfoWidget.label_10.setStyleSheet("color: green")
            else:
                self.showProcessInfoWidget.label_10.setStyleSheet("color: red")
            self.showProcessInfoWidget.label_10.setText(status)
        except:
            self.showProcessInfoWidget.label_10.setText("None")
        try:
            self.showProcessInfoWidget.label_11.setText(str(process.exe()))  # Get executable path
        except:
            self.showProcessInfoWidget.label_11.setText("None")
        try:
            self.showProcessInfoWidget.label_12.setText(str(process.cmdline()))  # Get command line
        except:
            self.showProcessInfoWidget.label_12.setText("None")
        try:
            self.showProcessInfoWidget.label_13.setText(str(process.create_time()))  # Get creation time
        except:
            self.showProcessInfoWidget.label_13.setText("None")
        try:
            self.showProcessInfoWidget.label_14.setText(str(process.parent()))  # Get parent process
        except:
            self.showProcessInfoWidget.label_14.setText("None")

        # Display a list of open files by the process
        self.showProcessInfoWidget.listWidget.clear()
        for i in process.open_files():
            item = QtWidgets.QListWidgetItem()
            item.setText(str(i[0]))
            self.showProcessInfoWidget.listWidget.addItem(item)

        # Show the process info widget
        self.showProcessInfoWidget.show()

    # Handle click event on listWidget to display network stats and graphs
    def listWidgetItemOnClick(self, item):
        global oldRecvBytes, oldSendBytes
        # Clear the listWidget_2 and display interface information
        color = 0
        self.listWidget_2.clear()
        ipaddressInterface = psutil.net_if_addrs().get(item.text())
        if ipaddressInterface is not None and ipaddressInterface[0][1] is not None:
            for data in ipaddressInterface[0]:
                try:
                    listWidget_2Item = QtWidgets.QListWidgetItem()
                    listWidget_2Item.setText(str(data))
                    # Alternate row color for better readability
                    if color == 0:
                        listWidget_2Item.setBackground(QtGui.QColor("white"))
                        color = 1
                    elif color == 1:
                        listWidget_2Item.setBackground(QtGui.QColor("gray"))
                        color = 0
                    self.listWidget_2.addItem(listWidget_2Item)
                except:
                    return
            try:
                listWidget_2Item = QtWidgets.QListWidgetItem()
                listWidget_2Item.setBackground(QtGui.QColor("gray"))
                listWidget_2Item.setText("Duplex: " + str(psutil.net_if_stats().get(item.text())[1]))
                self.listWidget_2.addItem(listWidget_2Item)

                listWidget_2Item = QtWidgets.QListWidgetItem()
                listWidget_2Item.setBackground(QtGui.QColor("white"))
                listWidget_2Item.setText("Speed: " + str(psutil.net_if_stats().get(item.text())[2]))
                self.listWidget_2.addItem(listWidget_2Item)

                listWidget_2Item = QtWidgets.QListWidgetItem()
                listWidget_2Item.setBackground(QtGui.QColor("gray"))
                listWidget_2Item.setText("Mtu: " + str(psutil.net_if_stats().get(item.text())[3]))
                self.listWidget_2.addItem(listWidget_2Item)
            except:
                return

    # Function to populate the listWidget with network interfaces
    def interfacesListSet(self):
        for interface in psutil.net_io_counters(pernic=True):
            listWidgetItem = QtWidgets.QListWidgetItem()
            listWidgetItem.setText(interface)
            listWidgetItem.setIcon(QtGui.QIcon("icons/network_card_thumb.png"))
            self.list