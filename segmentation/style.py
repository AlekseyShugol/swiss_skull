STYLE = """
            QDialog {
                background-color: #2D2D2D;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLineEdit {
                background-color: #3D3D3D;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                color: #00ff41;
                font-family: monospace;
            }
            QLineEdit:focus {
                border: 1px solid #00ff41;
            }
            QPushButton {
                background-color: #3D3D3D;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px 15px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #4D4D4D;
                border: 1px solid #00ff41;
            }
            QPushButton:pressed {
                background-color: #00ff41;
                color: #000000;
            }
            QMainWindow {
               background-color: #121212;
           }
           QWidget {
               background-color: #121212;
               color: #E0E0E0; 
               font-family: 'Segoe UI', sans-serif;
           }
           QLabel#StatusLabel { 
               color: #00ff41;
               font-family: 'Consolas', monospace;
               font-size: 11px;
           }
           QSlider::handle:horizontal {
               background: #00ff41;
               width: 18px;
               margin: -5px 0;
               border-radius: 9px;
           }
           QProgressBar {
               border: 1px solid #333;
               border-radius: 5px; 
               text-align: center;
               height: 15px;
           }
           QProgressBar::chunk {
               background-color: #00ff41; 
           }
           QToolBar {
               background-color: #1A1A1A;
               border-bottom: 2px solid #333;
               spacing: 5px;
               padding: 5px;
           }
           QToolBar QToolButton {
               background-color: #2D2D2D;
               border: 1px solid #444;
               border-radius: 4px;
               padding: 8px 15px;
               color: #E0E0E0;
               font-weight: bold;
               margin: 2px;
           }
           QToolBar QToolButton:hover {
               background-color: #3D3D3D;
               border: 1px solid #00ff41;
           }
           QToolBar QToolButton:pressed {
               background-color: #00ff41;
               color: #000;
           }
           QToolBar QToolButton:disabled {
               color: #555;
               background-color: #1A1A1A;
               border: 1px solid #222;
           }
           QMenuBar {
               background-color: #1A1A1A;
               color: #E0E0E0;
               border-bottom: 1px solid #333;
           }
           QMenuBar::item:selected {
               background-color: #333;
           }
           QMenu {
               background-color: #1E1E1E;
               color: #E0E0E0;
               border: 1px solid #333;
           }
           QMenu::item:selected {
               background-color: #333;
          
       """