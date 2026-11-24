#include <QApplication>
#include <QIcon>
#include "ui/MainWindow.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);
    app.setWindowIcon(QIcon("D:/Projects file/CLionProjects/Asistant_AZIMUT_II/Azimut-logo.png"));
    MainWindow w;
    w.show();
    return app.exec();
}