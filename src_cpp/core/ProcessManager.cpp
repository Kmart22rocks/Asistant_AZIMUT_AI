#include "ProcessManager.h"
#include <QCoreApplication>
#include <QDir>

ProcessManager::ProcessManager(QObject *parent)
    : QObject(parent),
      m_pythonProcess(new QProcess(this)),
      m_ollamaProcess(new QProcess(this)) {

    connect(m_pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
        QString out = QString::fromUtf8(m_pythonProcess->readAllStandardOutput());
        if (out.contains("8765")) {
            emit pythonServerReady();
        }
    });
}

ProcessManager::~ProcessManager() {
    stopServices();
}

void ProcessManager::startServices() {
    QString projectRoot = "D:/Projects file/CLionProjects/Asistant_AZIMUT_II";
    QString pythonExe = projectRoot + "/.venv/Scripts/python.exe";
    QString serverScript = projectRoot + "/src_python/server.py";

    m_pythonProcess->setWorkingDirectory(projectRoot + "/src_python");
    m_pythonProcess->start(pythonExe, QStringList() << serverScript);

    m_ollamaProcess->start("ollama", QStringList() << "serve");
}

void ProcessManager::stopServices() {
    QProcess::execute("ollama", QStringList() << "stop" << "qwen2.5-coder:7b");

    if (m_pythonProcess->state() != QProcess::NotRunning) {
        m_pythonProcess->kill();
        m_pythonProcess->waitForFinished(2000);
    }
    if (m_ollamaProcess->state() != QProcess::NotRunning) {
        m_ollamaProcess->kill();
        m_ollamaProcess->waitForFinished(2000);
    }
}