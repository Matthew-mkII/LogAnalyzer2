import os

# ★ 完全安定設定
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu --disable-software-rasterizer --disable-gpu-compositing"
)
os.environ["QT_OPENGL"] = "software"
os.environ["QT_XCB_GL_INTEGRATION"] = "none"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import plotly.express as px
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Plotly OK")

        fig = px.line(x=[1, 2, 3], y=[4, 5, 6])

        # ★ HTMLファイルとして保存
        path = os.path.abspath("temp.html")
        fig.write_html(path, include_plotlyjs=True)

        self.browser = QWebEngineView()
        self.browser.load(QUrl.fromLocalFile(path))

        self.setCentralWidget(self.browser)

app = QApplication(sys.argv)
window = MainWindow()
window.resize(800, 600)
window.show()
sys.exit(app.exec())