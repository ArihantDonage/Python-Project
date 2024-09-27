# Import necessary PyQt5 modules for GUI development
from PyQt5 import Qt, QtCore, QtGui, QtSql, QtWidgets, uic
import sys
# Library to retrieve system and process information
import psutil
# Library to create graphical plots with PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# Library to create navigation toolbar for matplotlib plots    
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt 
# Library to create deque for storing data
from collections import deque
# Library to apply a specific style to matplotlib plots
import matplotlib.style as style
# Apply a specific style to matplotlib plots    
style.use('ggplot')
# Global variables to store old send and receive bytes
oldSendBytes = 0
oldRecvBytes = 0
plotSend = []
plotRecv = []
# This variable stores the selected item from listWidget
itemQW = None

class Widget(QtWidgets.QWidget):
    def __init__(self):
        
        QtWidgets.QWidget.__init__(self)
        
        # Load the main UI file 
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
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.ontimer)
        self.timer.timeout.connect(self.networkStatisticksProcessForlistWidget_3)
        self.timer.start()

       # Timer for graph updates
        self.timefForGraph = QtCore.QTimer()
        self.timefForGraph.setInterval(1000)  
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
    def listWidget_3ItemRightClicked(self,QPos):
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

    # Handle 'Show process info' menu action
    def menuItem2Clicked(self):
        try:
            currentItemName = str(self.listWidget_3.currentItem().text())# Get selected item name
            ps = int(currentItemName.split(" Pid:")[1]) # Extract process ID (PID)
            process = psutil.Process(ps) # Get process info
            self.showProcessStatistick.ps = ps # Set process ID in stats window
            self.showProcessStatistick.process = process # Set process in stats window
            self.showProcessStatistick.timer.start()# Start timer for process stats updates
            self.showProcessStatistick.show()# Show the stats window
        except:
            pass

    # Handle 'Show process info' menu action
    def menuItemClicked(self):
        currentItemName = str(self.listWidget_3.currentItem().text())
        ps = int(currentItemName.split(" Pid:")[1])
        try:
            process = psutil.Process(ps)
        except:
            return

        # Fill the process info widget with details about the process
        self.showProcessInfoWidget.label.setText(currentItemName)
        # cwd
        try:
            self.showProcessInfoWidget.label_9.setText(str(process.cwd()))
        except:
            self.showProcessInfoWidget.label_9.setText("None")
        # Status
        try:
            status = str(process.status())
            if status == "running":
                self.showProcessInfoWidget.label_10.setStyleSheet("color: green")
            else:
                self.showProcessInfoWidget.label_10.setStyleSheet("color: red")
            self.showProcessInfoWidget.label_10.setText(status)
        except:
            self.showProcessInfoWidget.label_10.setText("None")
        # exe
        try:
            self.showProcessInfoWidget.label_11.setText(str(process.exe()))
        except:
            self.showProcessInfoWidget.label_11.setText("None")
        # cmdline
        try:
            self.showProcessInfoWidget.label_12.setText(str(process.cmdline()))
        except:
            self.showProcessInfoWidget.label_12.setText("None")
        # create time
        try:
            self.showProcessInfoWidget.label_13.setText(str(process.create_time()))
        except:
            self.showProcessInfoWidget.label_13.setText("None")
        # parent
        try:
            self.showProcessInfoWidget.label_14.setText(str(process.parent()))
        except:
            self.showProcessInfoWidget.label_14.setText("None")

        # Clear the list widget and add file details
        self.showProcessInfoWidget.listWidget.clear()
        for i in process.open_files():
            item = QtWidgets.QListWidgetItem()
            item.setText(str(i[0]))
            self.showProcessInfoWidget.listWidget.addItem(item)

        # Show widget
        self.showProcessInfoWidget.show()

    # Function called on click on item listWidget (displays graphs)
    def listWidgetItemOnClick(self,item):
        global oldRecvBytes, oldSendBytes
        # Clear listWidget_2 and add interface details
        color = 0
        self.listWidget_2.clear()
        ipaddressInterface = psutil.net_if_addrs().get(item.text())
        if ipaddressInterface != None and ipaddressInterface[0][1] != None:
            for data in ipaddressInterface[0]:
                try:
                    listWidget_2Item = QtWidgets.QListWidgetItem()
                    listWidget_2Item.setText(str(data))
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


# Function displays all available network interfaces in listWidget
    def interfacesListSet(self):
        for interface in psutil.net_io_counters(pernic=True):
            listWidgetItem = QtWidgets.QListWidgetItem()
            listWidgetItem.setText(interface)
            listWidgetItem.setIcon(QtGui.QIcon("icons/network_card_thumb.png"))
            self.listWidget.addItem(listWidgetItem)


# Get network activity statistics for running processes
    def networkStatistickProcess(self):
        rowCount = 0
        row = 0
        collumn = 0
# Count the number of needed rows
        for ps in psutil.pids():
            try:
                proc = psutil.Process(ps)
                if "pconn" in str(proc.connections()):
                    for Pcon in proc.connections():
                        rowCount += 1
            except:
                pass
        self.tableWidget.setRowCount(rowCount)
# Insert data into tableWidget
        for ps in psutil.pids():
            try:
                proc = psutil.Process(ps)
                if "pconn" in str(proc.connections()):
                    for Pcon in proc.connections(kind="inet"):
                        item = QtWidgets.QTableWidgetItem()
                        item.setText(proc.name())
                        self.tableWidget.setItem(row, 0, item)
                        collumn += 1
                        for i in Pcon:
                            item = QtWidgets.QTableWidgetItem()
                            item.setText(str(i))
                            self.tableWidget.setItem(row, collumn, item)
                            collumn += 1
                        row += 1
                        collumn = 0
            except:
                pass
            # Set the header labels for the tableWidget
        self.tableWidget.setHorizontalHeaderLabels(["Process name","Fd", "Famili", "Type", "Local addr", "Remote addr", "Status"])
    
# Automatically extend tableWidget to full window width
        header = self.tableWidget.horizontalHeader()
        header.setStretchLastSection(True)



# Function triggered by timer
    def ontimer(self):
        self.tableWidget.clear()
        self.networkStatistickProcess()

# Get list of processes with network activity and insert into listWidhet_3
    def networkStatisticksProcessForlistWidget_3(self):
        global ForPlotByteSend, ForPlotByteRecv
        for ps in psutil.pids():
            try:
                # Get process info  
                proc = psutil.Process(ps)
                if "pconn" in str(proc.connections()):

                    # Insert items into listWidget containing the process name and pid
                    item = QtWidgets.QListWidgetItem()
                    item.setText("Process: " + proc.name() + " Pid: " + str(ps))
                    item.setIcon(QtGui.QIcon("icons/exe-icon.png"))
                    # On each update check if the newly created item already exists, if so, make the background white, if it's new (new process)
                    # then color it green
                    items = self.listWidget_3.findItems(item.text(), QtCore.Qt.MatchExactly)
                    if len(items) > 0:
                        for iTem in items:
                            iTem.setBackground(QtGui.QColor("white"))
                    else:
                        item.setBackground(QtGui.QColor("green"))
                        self.listWidget_3.addItem(item)
                     # Call function to clear ListWidget_3 from items of completed processes
                self.listWidgetClearItem()
# Check if the process exists, if not, color it red and remove the item from listWidget
            except:
                return

# Function to clear ListWidget_3 from items of completed processes
    def listWidgetClearItem(self):
        # Get list of all items
        items = []
        for index in range(self.listWidget_3.count()):
            items.append(self.listWidget_3.item(index))
        # Check if the process exists
        for Item in items:
            process = Item.text().split("Pid:")
            rezult = psutil.pid_exists(int(process[1]))
            # If the process does not exist, color it red and remove the item from listWidget
            if rezult == False:
                items = self.listWidget_3.findItems(Item.text(), QtCore.Qt.MatchExactly)
                for i in items:
                    i.setBackground(QtGui.QColor("red"))
                    self.listWidget_3.takeItem(self.listWidget_3.row(i))
            else:
                try:
                    proc = psutil.Process(int(Item.text().split("Pid:")[1]))
                except:
                    pass

    # Function to find item in tableWidget and scroll to it
    def findItemIntableWidget(self,listWidgetItem):
        itemText = listWidgetItem.text().split("Process: ")
        itemText = itemText[1]
        itemText = itemText.split(" Pid: ")
        itemText = itemText[0]
        
        # Find item in tableWidget and scroll to it
        item = self.tableWidget.findItems(itemText, QtCore.Qt.MatchExactly)
        self.tableWidget.scrollToItem(item[0])

# Function to start timer and assign value to global variable that stores the selected item in listWidget
    def ontimerGraphTimer(self,listWidgetItem):
        global itemQW , selectedInterface, plotRecv, plotSend
        self.timefForGraph.start()
        # when a new interface is selected, the data is reset
        if itemQW != listWidgetItem:
            plotRecv = []
            plotSend = []
        itemQW = listWidgetItem
        self.graph()

# Build graphs
    def graph(self):
        global oldRecvBytes, oldSendBytes, plotRecv, plotSend

        self.axSend.cla()
        # Byte send
        new_value = psutil.net_io_counters(pernic=True).get(itemQW.text())[0]
        plotSend.append(new_value - oldSendBytes)
        oldSendBytes = new_value
        if int(len(plotSend)) >= 60:
            self.axSend.plot(plotSend[-60:], label="Byte send (TX)")
        else:
            self.axSend.plot(plotSend[1:], label="Byte send (TX)")
        self.axSend.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
                           ncol=2, mode="expand", borderaxespad=0.)
        self.canvasSend.draw()

        # Byte recv
        new_value = psutil.net_io_counters(pernic=True).get(itemQW.text())[1]
        plotRecv.append(new_value - oldRecvBytes)
        oldRecvBytes = new_value
        if int(len(plotRecv)) >= 60 :
            self.axSend.plot(plotRecv[-60:], label="Byte recv (RX)")
        else:
            self.axSend.plot(plotRecv[1:], label="Byte recv (RX)")
        self.axSend.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
                ncol=2, mode="expand", borderaxespad=0.)
        self.canvasSend.draw()

# Class of widget for processInfo
class processInfoWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.ui = uic.loadUi('ui/showProcessInfo.ui', self)
        self.pushButton.clicked.connect(self.closeWidget)
        self.pushButton_2.clicked.connect(self.suspendProcess)
        self.pushButton_3.clicked.connect(self.killingProcess)
# Killing process
    def killingProcess(self):
        if self.pushButton_3.text() == "Kill":
            messageBox = QtWidgets.QMessageBox()
            messageBox.addButton(QtWidgets.QMessageBox.Yes)
            messageBox.addButton(QtWidgets.QMessageBox.No)
            messageBox.setText("Kill this process?")
            rezult = messageBox.exec_()
            if rezult == QtWidgets.QMessageBox.No:
                pass
            # Killing process
            elif rezult == QtWidgets.QMessageBox.Yes:
                try:
                    # Getting process ID
                    process = psutil.Process(int(self.label.text().split("Pid: ")[1]))
                    process.kill()
                    # Displaying message about killing process
                    QtWidgets.QMessageBox.information(None, "Process killed", "Process killed")
                    # Changing color and text of label
                    self.label_10.setStyleSheet("color: red")
                    self.label_10.setText("Killed")
                except:
                    pass


# Closing widget
    def closeWidget(self):
        self.close()
    # Suspending process    
    def suspendProcess(self):
        # If button text is "Suspend"
        if self.pushButton_2.text() == "Suspend":
            # Displaying message about suspending process
            messageBox = QtWidgets.QMessageBox()
            # Adding buttons to message box
            messageBox.addButton(QtWidgets.QMessageBox.Yes)
            # Adding button "No"
            messageBox.addButton(QtWidgets.QMessageBox.No)
            
            messageBox.setText("Susped this process?")
            rezult = messageBox.exec_()
            if rezult == QtWidgets.QMessageBox.No:
                pass
            # Suspending process    
            elif rezult == QtWidgets.QMessageBox.Yes:
                try:
                    # Getting process ID
                    process = psutil.Process(int(self.label.text().split("Pid: ")[1]))
                    process.suspend()
                    # Changing text on button
                    self.pushButton_2.setText("Resume")
                    # Getting process status
                    status = str(process.status())
                    # If process status is running, changing color and text of label
                    if status == "running":
                        self.label_10.setStyleSheet("color: green")
                    else:
                        self.label_10.setStyleSheet("color: red")
                    self.label_10.setText(status)
                except:
                    # Displaying message about error    
                    self.label_10.setText("None")

        # If button text is "Resume"
        elif self.pushButton_2.text() == "Resume":
            try:
                # Getting process ID
                process = psutil.Process(int(self.label.text().split("Pid: ")[1]))
                process.resume()
                # Changing text on button
                self.pushButton_2.setText("Suspend")
                # Getting process status
                status = str(process.status())
                # If process status is running, changing color and text of label
                if status == "running":
                    self.label_10.setStyleSheet("color: green")
                else:
                    self.showProcessInfoWidget.label_10.setStyleSheet("color: red")
                self.label_10.setText(status)
            except:
                # Displaying message about error
                self.label_10.setText("None")




# Class of widget for processStatistick
class processStatistickWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.spForCpu = []
        self.spForMem = []
        self.ps = None
        self.process = None
# Load UI
        self.ui = uic.loadUi('ui/procesStatistick.ui', self)
        self.pushButton.clicked.connect(self.closeWidget)

# memory statistics
        self.figureMem = plt.figure()
        self.canvasMem = FigureCanvas(self.figureMem)
        self.axMem = self.figureMem.add_subplot(111)
        self.labelMem = QtWidgets.QLabel()
        self.labelMem.setText("Memory statistick")
        self.verticalLayout.addWidget(self.labelMem)
        self.verticalLayout.addWidget(self.canvasMem)

# CPU statistick
        self.figureCPU = plt.figure()
        self.canvasCPU = FigureCanvas(self.figureCPU)
        self.axCPU = self.figureCPU.add_subplot(111)
        self.labeCPU = QtWidgets.QLabel()
        self.labeCPU.setText("CPU statistick")
        self.verticalLayout.addWidget(self.labeCPU)
        self.verticalLayout.addWidget(self.canvasCPU)

        # Timer to update statistics    
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.timeout)

    def timeout(self):
        # CPU
        self.axCPU.cla()
        self.spForCpu.append(self.process.cpu_percent())
        for_x = [x for x in range(0, int(len(self.spForCpu)), 1)]
        if int(len(self.spForCpu)) >=60:
            self.axCPU.fill_between(range(0,60,1), self.spForCpu[-60:])
        else:
            self.axCPU.fill_between(for_x, self.spForCpu[-60:])
        self.canvasCPU.draw()

        # Memory
        self.axMem.cla()
        self.spForMem.append(self.process.memory_percent())
        for_x2 = [x for x in range(0, int(len(self.spForMem)), 1)]
        if int(len(self.spForMem)) >= 60:
            self.axMem.fill_between(range(0,60,1), self.spForMem[-60:])
        else:
            self.axMem.fill_between(for_x2, self.spForMem[-60:])
        self.canvasMem.draw()

# Closing widget
    def closeWidget(self):
        self.axCPU.cla()
        self.axMem.cla()
        self.timer.stop()
        self.ps = None
        self.process = None
        self.spForCpu = []
        self.spForMem = []
        self.close()

# Run application   
app = QtWidgets.QApplication(sys.argv)
Form = Widget()
Form.show()
sys.exit(app.exec())
