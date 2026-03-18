# -*- coding: utf-8 -*-
"""
程序入口
"""
import models.ui as ui

if __name__ == '__main__':
    # 运行应用
    app_version = '0.3.0'
    app = ui.MainWindow(app_version)
    app.mainloop()