# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Motofit.ui'
#
# Created: Thu Feb 20 18:42:58 2014
#      by: pyside-uic 0.2.15 running on PySide 1.2.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(928, 725)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(600, 462))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.WindowText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.BrightText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.ButtonText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.AlternateBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.ToolTipBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Active,
            QtGui.QPalette.ToolTipText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.WindowText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.Midlight,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.BrightText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.ButtonText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.AlternateBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.ToolTipBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Inactive,
            QtGui.QPalette.ToolTipText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.WindowText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.Midlight,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.BrightText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.ButtonText,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.AlternateBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.ToolTipBase,
            brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(
            QtGui.QPalette.Disabled,
            QtGui.QPalette.ToolTipText,
            brush)
        MainWindow.setPalette(palette)
        MainWindow.setAcceptDrops(True)
        MainWindow.setDocumentMode(False)
        MainWindow.setTabShape(QtGui.QTabWidget.Rounded)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setMinimumSize(QtCore.QSize(400, 0))
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_3 = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.graphs = QtGui.QTabWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.graphs.sizePolicy().hasHeightForWidth())
        self.graphs.setSizePolicy(sizePolicy)
        self.graphs.setMinimumSize(QtCore.QSize(0, 350))
        self.graphs.setObjectName("graphs")
        self.reflectivity = QtGui.QWidget()
        self.reflectivity.setObjectName("reflectivity")
        self.gridLayout_5 = QtGui.QGridLayout(self.reflectivity)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.graphs.addTab(self.reflectivity, "")
        self.sld = QtGui.QWidget()
        self.sld.setObjectName("sld")
        self.gridLayout_4 = QtGui.QGridLayout(self.sld)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.graphs.addTab(self.sld, "")
        self.gridLayout_3.addWidget(self.graphs, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar()
        self.menubar.setGeometry(QtCore.QRect(0, 0, 928, 22))
        self.menubar.setObjectName("menubar")
        self.menuData = QtGui.QMenu(self.menubar)
        self.menuData.setObjectName("menuData")
        self.menuModel = QtGui.QMenu(self.menubar)
        self.menuModel.setObjectName("menuModel")
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuPlot_type = QtGui.QMenu(self.menubar)
        self.menuPlot_type.setObjectName("menuPlot_type")
        self.menuAlgorithm = QtGui.QMenu(self.menuPlot_type)
        self.menuAlgorithm.setObjectName("menuAlgorithm")
        self.menuFit_as = QtGui.QMenu(self.menuPlot_type)
        self.menuFit_as.setObjectName("menuFit_as")
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuSettings = QtGui.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        self.menuMisc = QtGui.QMenu(self.menubar)
        self.menuMisc.setObjectName("menuMisc")
        MainWindow.setMenuBar(self.menubar)
        self.dockWidget = QtGui.QDockWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.dockWidget.sizePolicy().hasHeightForWidth())
        self.dockWidget.setSizePolicy(sizePolicy)
        self.dockWidget.setMinimumSize(QtCore.QSize(600, 350))
        self.dockWidget.setFeatures(
            QtGui.QDockWidget.DockWidgetFloatable | QtGui.QDockWidget.DockWidgetMovable)
        self.dockWidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.dockWidget.setWindowTitle("")
        self.dockWidget.setObjectName("dockWidget")
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtGui.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.tabWidget = QtGui.QTabWidget(self.dockWidgetContents)
        self.tabWidget.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy)
        self.tabWidget.setMinimumSize(QtCore.QSize(300, 200))
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtGui.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_2 = QtGui.QGridLayout(self.tab)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.baseModelView = QtGui.QTableView(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.baseModelView.sizePolicy().hasHeightForWidth())
        self.baseModelView.setSizePolicy(sizePolicy)
        self.baseModelView.setMinimumSize(QtCore.QSize(300, 70))
        self.baseModelView.setMaximumSize(QtCore.QSize(16777215, 70))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setWeight(50)
        font.setBold(False)
        self.baseModelView.setFont(font)
        self.baseModelView.setObjectName("baseModelView")
        self.baseModelView.horizontalHeader().setStretchLastSection(True)
        self.gridLayout_2.addWidget(self.baseModelView, 0, 0, 2, 1)
        self.chi2 = QtGui.QLineEdit(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.chi2.sizePolicy().hasHeightForWidth())
        self.chi2.setSizePolicy(sizePolicy)
        self.chi2.setMaximumSize(QtCore.QSize(100, 25))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.chi2.setFont(font)
        self.chi2.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.chi2.setReadOnly(True)
        self.chi2.setObjectName("chi2")
        self.gridLayout_2.addWidget(self.chi2, 0, 1, 1, 1)
        self.dataset_comboBox = QtGui.QComboBox(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.dataset_comboBox.sizePolicy().hasHeightForWidth())
        self.dataset_comboBox.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(50)
        font.setBold(False)
        self.dataset_comboBox.setFont(font)
        self.dataset_comboBox.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.dataset_comboBox.setObjectName("dataset_comboBox")
        self.gridLayout_2.addWidget(self.dataset_comboBox, 0, 2, 1, 1)
        self.res_SpinBox = QtGui.QDoubleSpinBox(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.res_SpinBox.sizePolicy().hasHeightForWidth())
        self.res_SpinBox.setSizePolicy(sizePolicy)
        self.res_SpinBox.setMinimumSize(QtCore.QSize(60, 0))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(50)
        font.setBold(False)
        self.res_SpinBox.setFont(font)
        self.res_SpinBox.setWrapping(False)
        self.res_SpinBox.setFrame(True)
        self.res_SpinBox.setReadOnly(False)
        self.res_SpinBox.setDecimals(1)
        self.res_SpinBox.setMaximum(10.0)
        self.res_SpinBox.setSingleStep(0.1)
        self.res_SpinBox.setProperty("value", 5.0)
        self.res_SpinBox.setObjectName("res_SpinBox")
        self.gridLayout_2.addWidget(self.res_SpinBox, 0, 3, 1, 1)
        self.do_fit_button = QtGui.QPushButton(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum,
            QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.do_fit_button.sizePolicy().hasHeightForWidth())
        self.do_fit_button.setSizePolicy(sizePolicy)
        self.do_fit_button.setMinimumSize(QtCore.QSize(40, 50))
        self.do_fit_button.setMaximumSize(QtCore.QSize(60, 75))
        self.do_fit_button.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap("icons/go.png"),
            QtGui.QIcon.Active,
            QtGui.QIcon.On)
        self.do_fit_button.setIcon(icon)
        self.do_fit_button.setIconSize(QtCore.QSize(60, 75))
        self.do_fit_button.setObjectName("do_fit_button")
        self.gridLayout_2.addWidget(self.do_fit_button, 0, 4, 1, 1)
        self.model_comboBox = QtGui.QComboBox(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.model_comboBox.sizePolicy().hasHeightForWidth())
        self.model_comboBox.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.model_comboBox.setFont(font)
        self.model_comboBox.setWhatsThis("")
        self.model_comboBox.setObjectName("model_comboBox")
        self.gridLayout_2.addWidget(self.model_comboBox, 1, 2, 1, 1)
        self.use_dqwave_checkbox = QtGui.QCheckBox(self.tab)
        self.use_dqwave_checkbox.setChecked(True)
        self.use_dqwave_checkbox.setObjectName("use_dqwave_checkbox")
        self.gridLayout_2.addWidget(self.use_dqwave_checkbox, 1, 3, 1, 1)
        self.use_errors_checkbox = QtGui.QCheckBox(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.use_errors_checkbox.sizePolicy().hasHeightForWidth())
        self.use_errors_checkbox.setSizePolicy(sizePolicy)
        self.use_errors_checkbox.setObjectName("use_errors_checkbox")
        self.gridLayout_2.addWidget(self.use_errors_checkbox, 1, 4, 1, 1)
        self.layerModelView = QtGui.QTableView(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.layerModelView.sizePolicy().hasHeightForWidth())
        self.layerModelView.setSizePolicy(sizePolicy)
        self.layerModelView.setMinimumSize(QtCore.QSize(300, 0))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.layerModelView.setFont(font)
        self.layerModelView.setObjectName("layerModelView")
        self.layerModelView.horizontalHeader().setStretchLastSection(True)
        self.gridLayout_2.addWidget(self.layerModelView, 2, 0, 1, 5)
        self.horizontalSlider = QtGui.QSlider(self.tab)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.horizontalSlider.sizePolicy().hasHeightForWidth())
        self.horizontalSlider.setSizePolicy(sizePolicy)
        self.horizontalSlider.setMaximumSize(QtCore.QSize(16777215, 22))
        self.horizontalSlider.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.horizontalSlider.setMaximum(999)
        self.horizontalSlider.setProperty("value", 499)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setInvertedAppearance(False)
        self.horizontalSlider.setInvertedControls(False)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.gridLayout_2.addWidget(self.horizontalSlider, 3, 0, 1, 5)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_6 = QtGui.QGridLayout(self.tab_2)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.dataOptions_tableView = QtGui.QTableView(self.tab_2)
        self.dataOptions_tableView.setObjectName("dataOptions_tableView")
        self.dataOptions_tableView.horizontalHeader(
        ).setCascadingSectionResizes(
            True)
        self.dataOptions_tableView.horizontalHeader(
        ).setStretchLastSection(
            True)
        self.gridLayout_6.addWidget(self.dataOptions_tableView, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QtGui.QWidget()
        self.tab_3.setObjectName("tab_3")
        self.gridLayout_7 = QtGui.QGridLayout(self.tab_3)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.do_UDFfit_button = QtGui.QPushButton(self.tab_3)
        self.do_UDFfit_button.setObjectName("do_UDFfit_button")
        self.gridLayout_7.addWidget(self.do_UDFfit_button, 0, 1, 1, 1)
        self.UDFloadPlugin = QtGui.QPushButton(self.tab_3)
        self.UDFloadPlugin.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.UDFloadPlugin.setObjectName("UDFloadPlugin")
        self.gridLayout_7.addWidget(self.UDFloadPlugin, 1, 1, 1, 1)
        self.UDFplugin_comboBox = QtGui.QComboBox(self.tab_3)
        self.UDFplugin_comboBox.setObjectName("UDFplugin_comboBox")
        self.gridLayout_7.addWidget(self.UDFplugin_comboBox, 2, 1, 1, 1)
        self.UDFdataset_comboBox = QtGui.QComboBox(self.tab_3)
        self.UDFdataset_comboBox.setObjectName("UDFdataset_comboBox")
        self.gridLayout_7.addWidget(self.UDFdataset_comboBox, 3, 1, 1, 1)
        self.UDFmodel_comboBox = QtGui.QComboBox(self.tab_3)
        self.UDFmodel_comboBox.setObjectName("UDFmodel_comboBox")
        self.gridLayout_7.addWidget(self.UDFmodel_comboBox, 4, 1, 1, 1)
        self.chi2UDF = QtGui.QLineEdit(self.tab_3)
        self.chi2UDF.setObjectName("chi2UDF")
        self.gridLayout_7.addWidget(self.chi2UDF, 5, 1, 1, 1)
        self.UDFmodelView = QtGui.QTableView(self.tab_3)
        self.UDFmodelView.setEnabled(True)
        self.UDFmodelView.setMinimumSize(QtCore.QSize(600, 0))
        self.UDFmodelView.setObjectName("UDFmodelView")
        self.gridLayout_7.addWidget(self.UDFmodelView, 0, 0, 6, 1)
        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QtGui.QWidget()
        self.tab_4.setObjectName("tab_4")
        self.gridLayout_8 = QtGui.QGridLayout(self.tab_4)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.plainTextEdit = QtGui.QPlainTextEdit(self.tab_4)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.plainTextEdit.setFont(font)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.gridLayout_8.addWidget(self.plainTextEdit, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_4, "")
        self.tab_5 = QtGui.QWidget()
        self.tab_5.setObjectName("tab_5")
        self.gridLayout_9 = QtGui.QGridLayout(self.tab_5)
        self.gridLayout_9.setObjectName("gridLayout_9")
        self.tabWidget_2 = QtGui.QTabWidget(self.tab_5)
        self.tabWidget_2.setObjectName("tabWidget_2")
        self.tab_6 = QtGui.QWidget()
        self.tab_6.setObjectName("tab_6")
        self.gridLayout_11 = QtGui.QGridLayout(self.tab_6)
        self.gridLayout_11.setObjectName("gridLayout_11")
        self.pushButton_3 = QtGui.QPushButton(self.tab_6)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.pushButton_3.sizePolicy().hasHeightForWidth())
        self.pushButton_3.setSizePolicy(sizePolicy)
        self.pushButton_3.setObjectName("pushButton_3")
        self.gridLayout_11.addWidget(self.pushButton_3, 1, 2, 1, 1)
        self.addGFDataSet = QtGui.QPushButton(self.tab_6)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.addGFDataSet.sizePolicy().hasHeightForWidth())
        self.addGFDataSet.setSizePolicy(sizePolicy)
        self.addGFDataSet.setObjectName("addGFDataSet")
        self.gridLayout_11.addWidget(self.addGFDataSet, 0, 2, 1, 1)
        self.globalfitting_DataView = QtGui.QTableView(self.tab_6)
        self.globalfitting_DataView.setObjectName("globalfitting_DataView")
        self.gridLayout_11.addWidget(self.globalfitting_DataView, 0, 0, 5, 1)
        self.linkGFparam = QtGui.QPushButton(self.tab_6)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.linkGFparam.sizePolicy().hasHeightForWidth())
        self.linkGFparam.setSizePolicy(sizePolicy)
        self.linkGFparam.setObjectName("linkGFparam")
        self.gridLayout_11.addWidget(self.linkGFparam, 2, 2, 1, 1)
        self.unlinkGFparam = QtGui.QPushButton(self.tab_6)
        sizePolicy = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Minimum,
            QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.unlinkGFparam.sizePolicy().hasHeightForWidth())
        self.unlinkGFparam.setSizePolicy(sizePolicy)
        self.unlinkGFparam.setObjectName("unlinkGFparam")
        self.gridLayout_11.addWidget(self.unlinkGFparam, 3, 2, 1, 1)
        self.tabWidget_2.addTab(self.tab_6, "")
        self.tab_7 = QtGui.QWidget()
        self.tab_7.setObjectName("tab_7")
        self.gridLayout_10 = QtGui.QGridLayout(self.tab_7)
        self.gridLayout_10.setObjectName("gridLayout_10")
        self.do_gf_fit = QtGui.QPushButton(self.tab_7)
        self.do_gf_fit.setMinimumSize(QtCore.QSize(50, 70))
        self.do_gf_fit.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap("icons/go.jpeg"),
            QtGui.QIcon.Active,
            QtGui.QIcon.On)
        self.do_gf_fit.setIcon(icon1)
        self.do_gf_fit.setIconSize(QtCore.QSize(70, 70))
        self.do_gf_fit.setObjectName("do_gf_fit")
        self.gridLayout_10.addWidget(self.do_gf_fit, 0, 1, 1, 1)
        self.globalParamsSlider = QtGui.QSlider(self.tab_7)
        self.globalParamsSlider.setMaximumSize(QtCore.QSize(16777215, 40))
        self.globalParamsSlider.setOrientation(QtCore.Qt.Horizontal)
        self.globalParamsSlider.setObjectName("globalParamsSlider")
        self.gridLayout_10.addWidget(self.globalParamsSlider, 1, 0, 1, 1)
        self.gfparams_tableView = QtGui.QTableView(self.tab_7)
        self.gfparams_tableView.setObjectName("gfparams_tableView")
        self.gridLayout_10.addWidget(self.gfparams_tableView, 0, 0, 1, 1)
        self.tabWidget_2.addTab(self.tab_7, "")
        self.gridLayout_9.addWidget(self.tabWidget_2, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_5, "")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.dockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(8), self.dockWidget)
        self.actionLoad_Data = QtGui.QAction(MainWindow)
        self.actionLoad_Data.setCheckable(False)
        self.actionLoad_Data.setChecked(False)
        self.actionLoad_Data.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionLoad_Data.setObjectName("actionLoad_Data")
        self.actionSave_Fit = QtGui.QAction(MainWindow)
        self.actionSave_Fit.setObjectName("actionSave_Fit")
        self.actionSave_Model = QtGui.QAction(MainWindow)
        self.actionSave_Model.setObjectName("actionSave_Model")
        self.actionLoad_Model = QtGui.QAction(MainWindow)
        self.actionLoad_Model.setObjectName("actionLoad_Model")
        self.actionLogR_vs_Q = QtGui.QAction(MainWindow)
        self.actionLogR_vs_Q.setCheckable(True)
        self.actionLogR_vs_Q.setChecked(True)
        self.actionLogR_vs_Q.setObjectName("actionLogR_vs_Q")
        self.actionR_vs_Q = QtGui.QAction(MainWindow)
        self.actionR_vs_Q.setCheckable(True)
        self.actionR_vs_Q.setObjectName("actionR_vs_Q")
        self.actionRQ4_vs_Q = QtGui.QAction(MainWindow)
        self.actionRQ4_vs_Q.setCheckable(True)
        self.actionRQ4_vs_Q.setObjectName("actionRQ4_vs_Q")
        self.actionRefresh_Data = QtGui.QAction(MainWindow)
        self.actionRefresh_Data.setObjectName("actionRefresh_Data")
        self.actionLoad_experiment = QtGui.QAction(MainWindow)
        self.actionLoad_experiment.setObjectName("actionLoad_experiment")
        self.actionSave_experiment = QtGui.QAction(MainWindow)
        self.actionSave_experiment.setObjectName("actionSave_experiment")
        self.actionLoad_Plugin = QtGui.QAction(MainWindow)
        self.actionLoad_Plugin.setObjectName("actionLoad_Plugin")
        self.actionSave_File = QtGui.QAction(MainWindow)
        self.actionSave_File.setWhatsThis("")
        self.actionSave_File.setObjectName("actionSave_File")
        self.actionLoad_File = QtGui.QAction(MainWindow)
        self.actionLoad_File.setObjectName("actionLoad_File")
        self.actionBatch_Fit = QtGui.QAction(MainWindow)
        self.actionBatch_Fit.setObjectName("actionBatch_Fit")
        self.actionRemove_Data = QtGui.QAction(MainWindow)
        self.actionRemove_Data.setObjectName("actionRemove_Data")
        self.actionAbout = QtGui.QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.actionDifferential_Evolution = QtGui.QAction(MainWindow)
        self.actionDifferential_Evolution.setCheckable(True)
        self.actionDifferential_Evolution.setChecked(True)
        self.actionDifferential_Evolution.setObjectName(
            "actionDifferential_Evolution")
        self.actionLevenberg_Marquardt = QtGui.QAction(MainWindow)
        self.actionLevenberg_Marquardt.setCheckable(True)
        self.actionLevenberg_Marquardt.setChecked(False)
        self.actionLevenberg_Marquardt.setObjectName(
            "actionLevenberg_Marquardt")
        self.actionY_vs_X = QtGui.QAction(MainWindow)
        self.actionY_vs_X.setCheckable(True)
        self.actionY_vs_X.setChecked(False)
        self.actionY_vs_X.setObjectName("actionY_vs_X")
        self.actionlogY_vs_X = QtGui.QAction(MainWindow)
        self.actionlogY_vs_X.setCheckable(True)
        self.actionlogY_vs_X.setChecked(True)
        self.actionlogY_vs_X.setObjectName("actionlogY_vs_X")
        self.actionYX4_vs_X = QtGui.QAction(MainWindow)
        self.actionYX4_vs_X.setCheckable(True)
        self.actionYX4_vs_X.setObjectName("actionYX4_vs_X")
        self.actionYX2_vs_X = QtGui.QAction(MainWindow)
        self.actionYX2_vs_X.setCheckable(True)
        self.actionYX2_vs_X.setObjectName("actionYX2_vs_X")
        self.actionChange_Q_range = QtGui.QAction(MainWindow)
        self.actionChange_Q_range.setObjectName("actionChange_Q_range")
        self.actionTake_Snapshot = QtGui.QAction(MainWindow)
        self.actionTake_Snapshot.setObjectName("actionTake_Snapshot")
        self.actionResolution_smearing = QtGui.QAction(MainWindow)
        self.actionResolution_smearing.setObjectName(
            "actionResolution_smearing")
        self.actionSLD_calculator = QtGui.QAction(MainWindow)
        self.actionSLD_calculator.setObjectName("actionSLD_calculator")
        self.menuData.addAction(self.actionLoad_Data)
        self.menuData.addAction(self.actionRefresh_Data)
        self.menuData.addAction(self.actionRemove_Data)
        self.menuData.addSeparator()
        self.menuData.addAction(self.actionSave_Fit)
        self.menuModel.addAction(self.actionSave_Model)
        self.menuModel.addAction(self.actionLoad_Model)
        self.menuModel.addSeparator()
        self.menuModel.addAction(self.actionTake_Snapshot)
        self.menuModel.addSeparator()
        self.menuModel.addAction(self.actionLoad_Plugin)
        self.menuHelp.addAction(self.actionAbout)
        self.menuAlgorithm.addAction(self.actionDifferential_Evolution)
        self.menuAlgorithm.addAction(self.actionLevenberg_Marquardt)
        self.menuFit_as.addAction(self.actionY_vs_X)
        self.menuFit_as.addAction(self.actionlogY_vs_X)
        self.menuFit_as.addAction(self.actionYX4_vs_X)
        self.menuFit_as.addAction(self.actionYX2_vs_X)
        self.menuPlot_type.addAction(self.menuFit_as.menuAction())
        self.menuPlot_type.addSeparator()
        self.menuPlot_type.addAction(self.menuAlgorithm.menuAction())
        self.menuPlot_type.addSeparator()
        self.menuPlot_type.addAction(self.actionBatch_Fit)
        self.menuFile.addAction(self.actionSave_File)
        self.menuFile.addAction(self.actionLoad_File)
        self.menuSettings.addAction(self.actionChange_Q_range)
        self.menuSettings.addAction(self.actionResolution_smearing)
        self.menuMisc.addAction(self.actionSLD_calculator)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuData.menuAction())
        self.menubar.addAction(self.menuModel.menuAction())
        self.menubar.addAction(self.menuPlot_type.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menubar.addAction(self.menuMisc.menuAction())

        self.retranslateUi(MainWindow)
        self.graphs.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)
        self.dataset_comboBox.setCurrentIndex(-1)
        self.tabWidget_2.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Motofit",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.graphs.setTabText(
            self.graphs.indexOf(self.reflectivity),
            QtGui.QApplication.translate("MainWindow",
                                         "reflectivity",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.graphs.setTabText(
            self.graphs.indexOf(self.sld),
            QtGui.QApplication.translate("MainWindow",
                                         "sld",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.menuData.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Data",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuModel.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Model",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuHelp.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Help",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuPlot_type.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Fitting",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuAlgorithm.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Algorithm",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuFit_as.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Fit as",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuFile.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "File",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuSettings.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Settings",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.menuMisc.setTitle(
            QtGui.QApplication.translate(
                "MainWindow",
                "Misc",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.chi2.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "0",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.res_SpinBox.setPrefix(
            QtGui.QApplication.translate(
                "MainWindow",
                "dq/q(%) : ",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.do_fit_button.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+F",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.use_dqwave_checkbox.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Use dq wave?",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.use_errors_checkbox.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Use errors?",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab),
            QtGui.QApplication.translate("MainWindow",
                                         "Model",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_2),
            QtGui.QApplication.translate("MainWindow",
                                         "Data",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.do_UDFfit_button.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Do Fit",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.UDFloadPlugin.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load Function",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_3),
            QtGui.QApplication.translate("MainWindow",
                                         "User defined models",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_4),
            QtGui.QApplication.translate("MainWindow",
                                         "Console",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.pushButton_3.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Remove dataset",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.addGFDataSet.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Add dataset",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.linkGFparam.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Link selection",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.unlinkGFparam.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Unlink selection",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.tabWidget_2.setTabText(
            self.tabWidget_2.indexOf(self.tab_6),
            QtGui.QApplication.translate("MainWindow",
                                         "datasets",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.tabWidget_2.setTabText(
            self.tabWidget_2.indexOf(self.tab_7),
            QtGui.QApplication.translate("MainWindow",
                                         "parameters",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_5),
            QtGui.QApplication.translate("MainWindow",
                                         "Global fit",
                                         None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Data.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load Data",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Data.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+L",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_Fit.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Save Fit",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_Model.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Save Model",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Model.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load Model",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLogR_vs_Q.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "logR vs Q",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionR_vs_Q.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "R vs Q",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionRQ4_vs_Q.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "RQ4 vs Q",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionRefresh_Data.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Refresh Data",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionRefresh_Data.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+R",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_experiment.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_experiment.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+N",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_experiment.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Save",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_experiment.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+M",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Plugin.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load Fitting Plugin",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_File.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Save",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSave_File.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+S",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_File.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Load",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_File.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow",
                "Meta+O",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionBatch_Fit.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Batch Fit",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionRemove_Data.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Remove Data",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionAbout.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "About",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionDifferential_Evolution.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Differential Evolution",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionLevenberg_Marquardt.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Levenberg Marquardt",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionY_vs_X.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "lin(Y) vs X",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionlogY_vs_X.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "log(Y) vs X",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionYX4_vs_X.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "YX**4 vs X",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionYX2_vs_X.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "YX**2 vs X",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionChange_Q_range.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Change Q Range",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionTake_Snapshot.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Take Snapshot",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionResolution_smearing.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "Resolution Smearing",
                None,
                QtGui.QApplication.UnicodeUTF8))
        self.actionSLD_calculator.setText(
            QtGui.QApplication.translate(
                "MainWindow",
                "SLD calculator",
                None,
                QtGui.QApplication.UnicodeUTF8))
